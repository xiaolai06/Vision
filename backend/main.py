"""
智能垃圾分类 - FastAPI 后端
启动: python -m uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel
from PIL import Image
from typing import Optional
import base64
import io
import os
import json
import time
import database as db
import model_manager as mm

app = FastAPI(title="智能垃圾分类 API", version="2.0.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── 初始化数据库 ───
db.init_db()

# ─── 分类定义（来自 model_manager） ───
CATEGORIES = mm.CATEGORIES
CATEGORY_LABELS = {
    "recyclable": "可回收物",
    "kitchen": "厨余垃圾",
    "hazardous": "有害垃圾",
    "other": "其他垃圾",
}


# ═══════════════════════════════════════
#  模型管理 API
# ═══════════════════════════════════════

@app.get("/api/models")
async def list_models():
    models = mm.registry.list_models()
    active_id, _ = mm.registry.get_active()
    return {"models": models, "active_model_id": active_id}


@app.put("/api/models/{model_id}/activate")
async def activate_model(model_id: str):
    if not mm.registry.set_active(model_id):
        raise HTTPException(status_code=404, detail="模型不存在")
    return {"ok": True, "active_model_id": model_id}


# ═══════════════════════════════════════
#  识别 API
# ═══════════════════════════════════════

@app.get("/api/health")
async def health():
    stats = db.get_stats()
    active_id, active_info = mm.registry.get_active()
    return {
        "status": "ok",
        "model_loaded": active_info and not active_info["is_mock"] if active_info else False,
        "active_model": active_id,
        "models": mm.registry.list_models(),
        "records": stats,
    }


@app.post("/api/predict")
async def predict(
    file: UploadFile = File(...),
    model_id: Optional[str] = Form(None),
):
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="请上传图片文件")

    image_bytes = await file.read()
    if len(image_bytes) > 10 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="图片大小不能超过 10MB")

    result = mm.registry.predict(image_bytes, model_id)

    # 保存图片并记录到数据库
    ext = ".png" if file.content_type == "image/png" else ".jpg"
    image_path = db.save_image(image_bytes, ext)

    if result["model_type"] == "classification":
        record_id = db.add_record(
            image_path=image_path,
            predicted_category=result["category"],
            predicted_label=result["label"],
            confidence=result["confidence"],
            tip=result["tip"],
            items=result["items"],
            model_name=result["model_name"],
            model_type="classification",
            image_width=result["image_width"],
            image_height=result["image_height"],
        )
        result["id"] = record_id
        return result
    else:
        # 检测模型：主分类取最高置信度的检测
        primary = max(result["detections"], key=lambda d: d["confidence"]) if result["detections"] else {
            "category": "other", "label": "其他垃圾", "confidence": 0,
            "tip": CATEGORIES[3]["tip"], "items": CATEGORIES[3]["items"],
        }
        record_id = db.add_record(
            image_path=image_path,
            predicted_category=primary["category"],
            predicted_label=primary["label"],
            confidence=primary["confidence"],
            tip=primary["tip"],
            items=primary.get("items", []),
            model_name=result["model_name"],
            model_type="detection",
            detections=result["detections"],
            image_width=result["image_width"],
            image_height=result["image_height"],
        )
        result["id"] = record_id
        # 为主检测结果补充 items
        for det in result["detections"]:
            cat_info = CATEGORIES.get(mm.CAT_NAME_TO_IDX.get(det["category"], 3), {})
            det["items"] = cat_info.get("items", [])
        return result


class Base64Request(BaseModel):
    image: str
    model_id: Optional[str] = None

@app.post("/api/predict_base64")
async def predict_base64(req: Base64Request):
    try:
        data = req.image
        if "," in data:
            data = data.split(",", 1)[1]
        image_bytes = base64.b64decode(data)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 base64 图片数据")

    result = mm.registry.predict(image_bytes, req.model_id)

    image_path = db.save_image(image_bytes, ".jpg")

    if result["model_type"] == "classification":
        record_id = db.add_record(
            image_path=image_path,
            predicted_category=result["category"],
            predicted_label=result["label"],
            confidence=result["confidence"],
            tip=result["tip"],
            items=result["items"],
            model_name=result["model_name"],
            model_type="classification",
            image_width=result["image_width"],
            image_height=result["image_height"],
        )
        result["id"] = record_id
        return result
    else:
        primary = max(result["detections"], key=lambda d: d["confidence"]) if result["detections"] else {
            "category": "other", "label": "其他垃圾", "confidence": 0,
            "tip": CATEGORIES[3]["tip"], "items": CATEGORIES[3]["items"],
        }
        record_id = db.add_record(
            image_path=image_path,
            predicted_category=primary["category"],
            predicted_label=primary["label"],
            confidence=primary["confidence"],
            tip=primary["tip"],
            items=primary.get("items", []),
            model_name=result["model_name"],
            model_type="detection",
            detections=result["detections"],
            image_width=result["image_width"],
            image_height=result["image_height"],
        )
        result["id"] = record_id
        for det in result["detections"]:
            cat_info = CATEGORIES.get(mm.CAT_NAME_TO_IDX.get(det["category"], 3), {})
            det["items"] = cat_info.get("items", [])
        return result


# ═══════════════════════════════════════
#  图片访问
# ═══════════════════════════════════════

@app.get("/api/images/{filename}")
async def get_image(filename: str):
    filepath = os.path.join(db.IMAGE_DIR, filename)
    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="图片不存在")
    return FileResponse(filepath, media_type="image/jpeg")


# ═══════════════════════════════════════
#  记录管理 API
# ═══════════════════════════════════════

@app.get("/api/records")
async def list_records(
    category: Optional[str] = Query(None),
    corrected: Optional[int] = Query(None),
    offset: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    keyword: Optional[str] = Query(None),
    model_type: Optional[str] = Query(None),
):
    records = db.get_records(
        category=category, corrected=corrected, offset=offset, limit=limit,
        start_date=start_date, end_date=end_date, keyword=keyword,
        model_type=model_type,
    )
    stats = db.get_stats()
    return {"records": records, "stats": stats, "offset": offset, "limit": limit}


@app.get("/api/records/stats")
async def record_stats():
    return db.get_stats()


@app.get("/api/records/chart-data")
async def chart_data(
    category: Optional[str] = Query(None),
    days: int = Query(30, ge=1, le=365),
):
    return db.get_chart_data(category=category, days=days)


@app.get("/api/records/{record_id}")
async def get_record(record_id: int):
    record = db.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    # 解析 detections JSON
    if record.get("detections"):
        try:
            record["detections"] = json.loads(record["detections"])
        except (json.JSONDecodeError, TypeError):
            record["detections"] = None
    # 附带标注数据
    record["annotations"] = db.get_annotations(record_id)
    return record


@app.delete("/api/records/{record_id}")
async def remove_record(record_id: int):
    record = db.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    db.delete_record(record_id)
    return {"ok": True}


class CorrectRequest(BaseModel):
    category: str  # recyclable / kitchen / hazardous / other
    label: str     # 中文标签
    confidence: Optional[float] = None  # 修正后的置信度（0.0-1.0）

@app.put("/api/records/{record_id}/correct")
async def correct_record(record_id: int, req: CorrectRequest):
    record = db.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")

    if req.category not in CATEGORY_LABELS:
        raise HTTPException(status_code=400, detail="无效的分类类别")

    if req.confidence is not None and not (0.0 <= req.confidence <= 1.0):
        raise HTTPException(status_code=400, detail="置信度必须在 0.0 到 1.0 之间")

    label = req.label or CATEGORY_LABELS[req.category]
    db.correct_record(record_id, req.category, label, req.confidence)
    return {"ok": True, "category": req.category, "label": label, "confidence": req.confidence}


class BatchCorrectRequest(BaseModel):
    ids: list[int]
    category: str
    label: str
    confidence: Optional[float] = None

@app.put("/api/records/batch/correct")
async def batch_correct(req: BatchCorrectRequest):
    if not req.ids:
        raise HTTPException(status_code=400, detail="请选择要修正的记录")
    if req.category not in CATEGORY_LABELS:
        raise HTTPException(status_code=400, detail="无效的分类类别")
    if req.confidence is not None and not (0.0 <= req.confidence <= 1.0):
        raise HTTPException(status_code=400, detail="置信度必须在 0.0 到 1.0 之间")
    label = req.label or CATEGORY_LABELS[req.category]
    count = db.batch_correct_records(req.ids, req.category, label, req.confidence)
    return {"ok": True, "count": count}


class BatchDeleteRequest(BaseModel):
    ids: list[int]

@app.post("/api/records/batch/delete")
async def batch_delete(req: BatchDeleteRequest):
    if not req.ids:
        raise HTTPException(status_code=400, detail="请选择要删除的记录")
    count = db.batch_delete_records(req.ids)
    return {"ok": True, "count": count}


# ═══════════════════════════════════════
#  导出 API
# ═══════════════════════════════════════

@app.get("/api/export")
async def export_data(
    format: str = Query("csv", pattern="^(csv|coco|yolo|yolo_det|coco_det)$"),
    category: Optional[str] = Query(None),
):
    content = db.export_records(format=format, category=category)

    if format == "csv":
        return Response(
            content=content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=garbage_dataset.csv"},
        )
    elif format in ("coco", "coco_det"):
        return Response(
            content=content,
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=garbage_coco.json"},
        )
    elif format == "yolo":
        return Response(
            content=content,
            media_type="text/plain",
            headers={"Content-Disposition": "attachment; filename=garbage_yolo.txt"},
        )
    elif format == "yolo_det":
        return Response(
            content=content,
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=garbage_yolo_det.zip"},
        )


@app.get("/api/export/split")
async def export_split(
    train_ratio: float = Query(0.8, ge=0.01, le=0.98),
    val_ratio: float = Query(0.1, ge=0.01, le=0.89),
    test_ratio: float = Query(0.1, ge=0.01, le=0.89),
    category: Optional[str] = Query(None),
):
    try:
        zip_bytes = db.export_split(train_ratio, val_ratio, test_ratio, category)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=garbage_dataset_split.zip"},
    )


# ═══════════════════════════════════════
#  WebSocket 实时识别（带去重计数）
# ═══════════════════════════════════════

@app.websocket("/api/ws/predict")
async def ws_predict(websocket: WebSocket):
    await websocket.accept()
    # 去重状态：跟踪每个类别的上次保存时间
    last_saved: dict[str, float] = {}

    try:
        while True:
            data = await websocket.receive_json()
            raw = data.get("image", "")
            if "," in raw:
                raw = raw.split(",", 1)[1]
            try:
                image_bytes = base64.b64decode(raw)
            except Exception:
                await websocket.send_json({"error": "invalid base64 image"})
                continue

            model_id = data.get("model_id", None)
            result = mm.registry.predict(image_bytes, model_id)

            # 可选存库（客户端控制 + 智能去重）
            record_id = None
            should_save = data.get("save", False)

            if should_save:
                dedupe_seconds = data.get("dedupe_seconds", 5)
                now = time.time()

                if result["model_type"] == "classification":
                    cat = result["category"]
                else:
                    # 检测模型取主分类（最高置信度）
                    primary = max(result["detections"], key=lambda d: d["confidence"]) if result["detections"] else None
                    cat = primary["category"] if primary else "other"

                # 去重逻辑：同类别在窗口内不保存
                if cat in last_saved and (now - last_saved[cat]) < dedupe_seconds:
                    should_save = False
                else:
                    last_saved[cat] = now

            if should_save:
                image_path = db.save_image(image_bytes, ".jpg")
                if result["model_type"] == "classification":
                    record_id = db.add_record(
                        image_path=image_path,
                        predicted_category=result["category"],
                        predicted_label=result["label"],
                        confidence=result["confidence"],
                        tip=result["tip"],
                        items=result["items"],
                        model_name=result["model_name"],
                        model_type="classification",
                        image_width=result["image_width"],
                        image_height=result["image_height"],
                    )
                else:
                    primary = max(result["detections"], key=lambda d: d["confidence"]) if result["detections"] else {
                        "category": "other", "label": "其他垃圾", "confidence": 0, "tip": "",
                    }
                    record_id = db.add_record(
                        image_path=image_path,
                        predicted_category=primary["category"],
                        predicted_label=primary["label"],
                        confidence=primary["confidence"],
                        tip=primary["tip"],
                        items=primary.get("items", []),
                        model_name=result["model_name"],
                        model_type="detection",
                        detections=result["detections"],
                        image_width=result["image_width"],
                        image_height=result["image_height"],
                    )

            # 发送结果给客户端
            response = {**result, "id": record_id}
            await websocket.send_json(response)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_json({"error": str(e)})
        except Exception:
            pass


# ═══════════════════════════════════════
#  标注管理 API
# ═══════════════════════════════════════

class AnnotationItem(BaseModel):
    category: str
    label: str
    x1: float
    y1: float
    x2: float
    y2: float
    source: str = "manual"

class AnnotationSaveRequest(BaseModel):
    annotations: list[AnnotationItem]

@app.get("/api/annotations/{record_id}")
async def get_annotations(record_id: int):
    record = db.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    return {"record_id": record_id, "annotations": db.get_annotations(record_id)}


@app.post("/api/annotations/{record_id}")
async def save_annotations(record_id: int, req: AnnotationSaveRequest):
    record = db.get_record_by_id(record_id)
    if not record:
        raise HTTPException(status_code=404, detail="记录不存在")
    if not req.annotations:
        raise HTTPException(status_code=400, detail="标注列表不能为空")
    ann_data = [a.model_dump() for a in req.annotations]
    ids = db.add_annotations(record_id, ann_data)
    return {"ok": True, "ids": ids}


@app.put("/api/annotations/{annotation_id}")
async def update_annotation(annotation_id: int, req: AnnotationItem):
    db.update_annotation(annotation_id, req.model_dump())
    return {"ok": True}


@app.delete("/api/annotations/{annotation_id}")
async def remove_annotation(annotation_id: int):
    db.delete_annotation(annotation_id)
    return {"ok": True}
