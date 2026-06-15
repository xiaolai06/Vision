"""
识别记录数据库模块
使用 SQLite 存储每次识别的结果，用于积累训练数据
"""

import sqlite3
import os
import json
from datetime import datetime

DB_PATH = "data/records.db"
IMAGE_DIR = "data/images"


def init_db():
    """初始化数据库和数据目录"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    os.makedirs(IMAGE_DIR, exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT NOT NULL,
            predicted_category TEXT NOT NULL,
            predicted_label TEXT NOT NULL,
            confidence REAL NOT NULL,
            corrected_category TEXT,
            corrected_label TEXT,
            is_corrected INTEGER DEFAULT 0,
            tip TEXT DEFAULT '',
            items TEXT DEFAULT '[]',
            created_at TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()
    migrate()


def migrate():
    """幂等数据库迁移：新增列和表"""
    conn = sqlite3.connect(DB_PATH)
    cols = [row[1] for row in conn.execute("PRAGMA table_info(records)").fetchall()]

    new_columns = [
        ("model_name", "TEXT DEFAULT 'mobilenet_v2'"),
        ("model_type", "TEXT DEFAULT 'classification'"),
        ("detections", "TEXT DEFAULT NULL"),
        ("image_width", "INTEGER DEFAULT NULL"),
        ("image_height", "INTEGER DEFAULT NULL"),
    ]
    for col_name, col_type in new_columns:
        if col_name not in cols:
            conn.execute(f"ALTER TABLE records ADD COLUMN {col_name} {col_type}")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS image_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            record_id INTEGER NOT NULL,
            category TEXT NOT NULL,
            label TEXT NOT NULL,
            x1 REAL NOT NULL,
            y1 REAL NOT NULL,
            x2 REAL NOT NULL,
            y2 REAL NOT NULL,
            source TEXT DEFAULT 'manual',
            created_at TEXT NOT NULL,
            FOREIGN KEY (record_id) REFERENCES records(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def save_image(image_bytes: bytes, ext: str = ".jpg") -> str:
    """保存图片到 data/images/，返回相对路径"""
    filename = f"{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}{ext}"
    filepath = os.path.join(IMAGE_DIR, filename)
    with open(filepath, "wb") as f:
        f.write(image_bytes)
    return filepath


def add_record(
    image_path: str,
    predicted_category: str,
    predicted_label: str,
    confidence: float,
    tip: str = "",
    items: list = None,
    model_name: str = "mobilenet_v2",
    model_type: str = "classification",
    detections: list = None,
    image_width: int = None,
    image_height: int = None,
) -> int:
    """添加一条识别记录，返回记录 ID"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.execute(
        """INSERT INTO records
           (image_path, predicted_category, predicted_label, confidence, tip, items,
            model_name, model_type, detections, image_width, image_height, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            image_path,
            predicted_category,
            predicted_label,
            confidence,
            tip,
            json.dumps(items or [], ensure_ascii=False),
            model_name,
            model_type,
            json.dumps(detections, ensure_ascii=False) if detections else None,
            image_width,
            image_height,
            datetime.now().isoformat(),
        ),
    )
    record_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return record_id


def get_records(
    category: str = None,
    corrected: int = None,
    offset: int = 0,
    limit: int = 50,
    start_date: str = None,
    end_date: str = None,
    keyword: str = None,
    model_type: str = None,
) -> list:
    """查询记录列表，支持按类别、修正状态、日期范围、关键词、模型类型筛选"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    query = "SELECT * FROM records WHERE 1=1"
    params = []

    if category:
        query += " AND COALESCE(corrected_category, predicted_category) = ?"
        params.append(category)
    if corrected is not None:
        query += " AND is_corrected = ?"
        params.append(corrected)
    if start_date:
        query += " AND created_at >= ?"
        params.append(start_date)
    if end_date:
        query += " AND created_at <= ?"
        params.append(end_date + "T23:59:59")
    if keyword:
        query += " AND (predicted_label LIKE ? OR corrected_label LIKE ? OR items LIKE ?)"
        like_kw = f"%{keyword}%"
        params.extend([like_kw, like_kw, like_kw])
    if model_type:
        query += " AND model_type = ?"
        params.append(model_type)

    query += " ORDER BY created_at DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_record_by_id(record_id: int) -> dict | None:
    """按 ID 查询单条记录"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM records WHERE id = ?", (record_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def correct_record(record_id: int, category: str, label: str, confidence: float = None):
    """手动修正某条记录的分类标签和置信度"""
    conn = sqlite3.connect(DB_PATH)
    if confidence is not None:
        conn.execute(
            """UPDATE records
               SET corrected_category = ?, corrected_label = ?, is_corrected = 1, confidence = ?
               WHERE id = ?""",
            (category, label, confidence, record_id),
        )
    else:
        conn.execute(
            """UPDATE records
               SET corrected_category = ?, corrected_label = ?, is_corrected = 1
               WHERE id = ?""",
            (category, label, record_id),
        )
    conn.commit()
    conn.close()


def delete_record(record_id: int):
    """删除某条记录及其图片"""
    record = get_record_by_id(record_id)
    if record and os.path.exists(record["image_path"]):
        os.remove(record["image_path"])

    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM records WHERE id = ?", (record_id,))
    conn.commit()
    conn.close()


def batch_delete_records(record_ids: list) -> int:
    """批量删除记录，返回删除数量"""
    deleted = 0
    for rid in record_ids:
        record = get_record_by_id(rid)
        if record and os.path.exists(record["image_path"]):
            try:
                os.remove(record["image_path"])
            except OSError:
                pass
        conn = sqlite3.connect(DB_PATH)
        conn.execute("DELETE FROM records WHERE id = ?", (rid,))
        conn.commit()
        conn.close()
        deleted += 1
    return deleted


def batch_correct_records(record_ids: list, category: str, label: str, confidence: float = None) -> int:
    """批量修正记录分类，返回修正数量"""
    conn = sqlite3.connect(DB_PATH)
    if confidence is not None:
        conn.executemany(
            """UPDATE records
               SET corrected_category = ?, corrected_label = ?, is_corrected = 1, confidence = ?
               WHERE id = ?""",
            [(category, label, confidence, rid) for rid in record_ids],
        )
    else:
        conn.executemany(
            """UPDATE records
               SET corrected_category = ?, corrected_label = ?, is_corrected = 1
               WHERE id = ?""",
            [(category, label, rid) for rid in record_ids],
        )
    count = conn.execute("SELECT changes()").fetchone()[0]
    conn.commit()
    conn.close()
    return count


def get_stats() -> dict:
    """获取记录统计信息"""
    conn = sqlite3.connect(DB_PATH)
    total = conn.execute("SELECT COUNT(*) FROM records").fetchone()[0]
    corrected = conn.execute("SELECT COUNT(*) FROM records WHERE is_corrected = 1").fetchone()[0]

    categories = {}
    rows = conn.execute(
        """SELECT COALESCE(corrected_category, predicted_category) as cat,
                  COUNT(*) as cnt
           FROM records GROUP BY cat"""
    ).fetchall()
    for row in rows:
        categories[row[0]] = row[1]

    by_model_type = {}
    mt_rows = conn.execute(
        "SELECT model_type, COUNT(*) as cnt FROM records GROUP BY model_type"
    ).fetchall()
    for row in mt_rows:
        by_model_type[row[0] or "classification"] = row[1]

    conn.close()
    return {
        "total": total,
        "corrected": corrected,
        "uncorrected": total - corrected,
        "by_category": categories,
        "by_model_type": by_model_type,
    }


def get_chart_data(category: str = None, days: int = 30) -> dict:
    """获取图表可视化所需的聚合数据"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    where = ""
    params: list = []
    if category:
        where = "WHERE COALESCE(corrected_category, predicted_category) = ?"
        params.append(category)

    # 1. 分类分布
    cat_rows = conn.execute(
        f"""SELECT COALESCE(corrected_category, predicted_category) AS cat,
                   COUNT(*) AS cnt
            FROM records {where}
            GROUP BY cat""",
        params,
    ).fetchall()
    category_distribution = [{"category": r["cat"], "count": r["cnt"]} for r in cat_rows]

    # 2. 置信度分布（10 个区间）
    conf_rows = conn.execute(
        f"SELECT confidence FROM records {where}", params
    ).fetchall()
    buckets = [0] * 10
    for r in conf_rows:
        idx = min(int(r["confidence"] * 10), 9)
        buckets[idx] += 1
    confidence_histogram = [
        {"range": f"{i / 10:.1f}-{(i + 1) / 10:.1f}", "count": buckets[i]}
        for i in range(10)
    ]

    # 3. 每日识别趋势
    from datetime import datetime as _dt, timedelta as _td

    start = (_dt.now() - _td(days=days)).isoformat()
    trend_where = (where + " AND ") if where else "WHERE "
    trend_rows = conn.execute(
        f"""SELECT DATE(created_at) AS day, COUNT(*) AS cnt
            FROM records {trend_where} created_at >= ?
            GROUP BY day ORDER BY day""",
        params + [start],
    ).fetchall()
    daily_trend = [{"date": r["day"], "count": r["cnt"]} for r in trend_rows]

    conn.close()
    return {
        "category_distribution": category_distribution,
        "confidence_histogram": confidence_histogram,
        "daily_trend": daily_trend,
    }


def export_records(format: str = "csv", category: str = None) -> bytes:
    """
    导出训练数据
    - csv: 简单 CSV 格式
    - coco: COCO JSON 格式（分类，全图 bbox）
    - yolo: YOLO txt 格式（分类，全图 bbox）
    - yolo_det: YOLO 检测格式（真实 bbox，ZIP 含 images/ + labels/ + data.yaml）
    - coco_det: COCO 检测格式（真实 bbox）
    """
    records = get_records(category=category, limit=100000)

    if format == "csv":
        return _export_csv(records)
    elif format == "coco":
        return _export_coco(records)
    elif format == "yolo":
        return _export_yolo(records)
    elif format == "yolo_det":
        return _export_yolo_det(records)
    elif format == "coco_det":
        return _export_coco_det(records)
    else:
        raise ValueError(f"不支持的导出格式: {format}")


def _export_csv(records: list) -> bytes:
    """导出 CSV 格式"""
    import csv
    import io
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "image_path", "category", "label", "confidence",
                     "corrected_category", "corrected_label", "is_corrected", "created_at"])
    for r in records:
        cat = r["corrected_category"] or r["predicted_category"]
        label = r["corrected_label"] or r["predicted_label"]
        writer.writerow([
            r["id"], r["image_path"], cat, label, r["confidence"],
            r["corrected_category"] or "", r["corrected_label"] or "",
            r["is_corrected"], r["created_at"]
        ])
    return output.getvalue().encode("utf-8-sig")


def _export_coco(records: list) -> bytes:
    """导出 COCO JSON 格式"""
    categories_list = [
        {"id": 0, "name": "recyclable"},
        {"id": 1, "name": "kitchen"},
        {"id": 2, "name": "hazardous"},
        {"id": 3, "name": "other"},
    ]
    cat_name_to_id = {c["name"]: c["id"] for c in categories_list}

    images = []
    annotations = []
    for i, r in enumerate(records):
        cat = r["corrected_category"] or r["predicted_category"]
        images.append({
            "id": i + 1,
            "file_name": os.path.basename(r["image_path"]),
        })
        annotations.append({
            "id": i + 1,
            "image_id": i + 1,
            "category_id": cat_name_to_id.get(cat, 3),
            "bbox": [0, 0, 224, 224],  # 分类任务用全图 bbox
            "area": 224 * 224,
            "iscrowd": 0,
        })

    coco = {
        "info": {"description": "Garbage Classification Dataset", "version": "1.0"},
        "images": images,
        "annotations": annotations,
        "categories": categories_list,
    }
    return json.dumps(coco, ensure_ascii=False, indent=2).encode("utf-8")


def _export_yolo(records: list) -> bytes:
    """导出 YOLO 格式（每行: category_id image_path）"""
    cat_map = {"recyclable": 0, "kitchen": 1, "hazardous": 2, "other": 3}
    lines = []
    for r in records:
        cat = r["corrected_category"] or r["predicted_category"]
        cid = cat_map.get(cat, 3)
        # YOLO 格式: class_id center_x center_y width height (归一化)
        # 分类任务用全图中心点
        lines.append(f"{cid} 0.5 0.5 1.0 1.0  # {os.path.basename(r['image_path'])}")
    return "\n".join(lines).encode("utf-8")


def _get_record_bboxes(record: dict) -> list:
    """
    获取一条记录的所有真实 bbox。
    优先使用 image_annotations 表（人工标注），
    其次使用 detections JSON 列（模型预测）。
    返回: [{category, label, x1, y1, x2, y2}]
    """
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    ann_rows = conn.execute(
        "SELECT category, label, x1, y1, x2, y2 FROM image_annotations WHERE record_id = ?",
        (record["id"],),
    ).fetchall()
    conn.close()

    if ann_rows:
        return [dict(r) for r in ann_rows]

    # 回退到 detections JSON
    det_raw = record.get("detections")
    if det_raw:
        try:
            dets = json.loads(det_raw) if isinstance(det_raw, str) else det_raw
            return [
                {
                    "category": d.get("category", "other"),
                    "label": d.get("label", "其他垃圾"),
                    "x1": d["bbox"][0], "y1": d["bbox"][1],
                    "x2": d["bbox"][2], "y2": d["bbox"][3],
                }
                for d in dets if "bbox" in d
            ]
        except (json.JSONDecodeError, KeyError, TypeError):
            pass
    return []


def _export_yolo_det(records: list) -> bytes:
    """
    导出 YOLO 检测格式 ZIP:
      images/*.jpg
      labels/*.txt    (每张图片一个文件，每行: class_id cx cy w h 归一化)
      data.yaml
    """
    import zipfile
    import io as _io

    cat_map = {"recyclable": 0, "kitchen": 1, "hazardous": 2, "other": 3}
    buf = _io.BytesIO()

    exported = 0
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in records:
            bboxes = _get_record_bboxes(r)
            if not bboxes:
                continue

            img_path = r["image_path"]
            filename = os.path.basename(img_path)
            base = os.path.splitext(filename)[0]

            # 复制图片
            if os.path.exists(img_path):
                zf.write(img_path, f"images/{filename}")

            # 获取图片尺寸用于归一化
            img_w = r.get("image_width") or 224
            img_h = r.get("image_height") or 224
            if img_w == 0:
                img_w = 224
            if img_h == 0:
                img_h = 224

            # 生成标签文件
            lines = []
            for bbox in bboxes:
                cid = cat_map.get(bbox["category"], 3)
                # 转为 YOLO 归一化格式: cx cy w h
                cx = ((bbox["x1"] + bbox["x2"]) / 2) / img_w
                cy = ((bbox["y1"] + bbox["y2"]) / 2) / img_h
                w = abs(bbox["x2"] - bbox["x1"]) / img_w
                h = abs(bbox["y2"] - bbox["y1"]) / img_h
                lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")

            zf.writestr(f"labels/{base}.txt", "\n".join(lines))
            exported += 1

        # data.yaml
        yaml_lines = [
            "names:",
            "  0: recyclable",
            "  1: kitchen",
            "  2: hazardous",
            "  3: other",
            "nc: 4",
            f"image_count: {exported}",
            "",
            "# 使用方式:",
            "# from ultralytics import YOLO",
            "# model = YOLO('yolov8n.pt')",
            "# model.train(data='data.yaml', epochs=100)",
        ]
        zf.writestr("data.yaml", "\n".join(yaml_lines))

    return buf.getvalue()


def _export_coco_det(records: list) -> bytes:
    """
    导出 COCO 检测 JSON 格式（使用真实 bbox）。
    """
    cat_map = {"recyclable": 0, "kitchen": 1, "hazardous": 2, "other": 3}
    categories_list = [
        {"id": 0, "name": "recyclable"},
        {"id": 1, "name": "kitchen"},
        {"id": 2, "name": "hazardous"},
        {"id": 3, "name": "other"},
    ]

    images = []
    annotations = []
    ann_id = 1

    for i, r in enumerate(records):
        bboxes = _get_record_bboxes(r)
        if not bboxes:
            continue

        img_w = r.get("image_width") or 224
        img_h = r.get("image_height") or 224

        images.append({
            "id": i + 1,
            "file_name": os.path.basename(r["image_path"]),
            "width": img_w,
            "height": img_h,
        })

        for bbox in bboxes:
            x, y, x2, y2 = bbox["x1"], bbox["y1"], bbox["x2"], bbox["y2"]
            w = abs(x2 - x)
            h = abs(y2 - y)
            annotations.append({
                "id": ann_id,
                "image_id": i + 1,
                "category_id": cat_map.get(bbox["category"], 3),
                "bbox": [round(x, 1), round(y, 1), round(w, 1), round(h, 1)],
                "area": round(w * h, 1),
                "iscrowd": 0,
            })
            ann_id += 1

    coco = {
        "info": {
            "description": "Garbage Detection Dataset (real bboxes)",
            "version": "1.0",
        },
        "images": images,
        "annotations": annotations,
        "categories": categories_list,
    }
    return json.dumps(coco, ensure_ascii=False, indent=2).encode("utf-8")


def export_split(
    train_ratio: float = 0.8,
    val_ratio: float = 0.1,
    test_ratio: float = 0.1,
    category: str = None,
) -> bytes:
    """
    将记录按比例随机划分为 train/val/test，导出为 ZIP。
    ZIP 内目录结构: dataset/{train,val,test}/{category}/*.jpg
    附带 dataset.yaml 和 labels.csv
    """
    import random
    import zipfile
    import io as _io

    records = get_records(category=category, limit=100000)
    if not records:
        raise ValueError("没有可导出的记录")

    random.shuffle(records)

    total = train_ratio + val_ratio + test_ratio
    train_ratio /= total
    val_ratio /= total
    test_ratio /= total

    n = len(records)
    train_end = int(n * train_ratio)
    val_end = train_end + int(n * val_ratio)

    splits = {
        "train": records[:train_end],
        "val": records[train_end:val_end],
        "test": records[val_end:],
    }

    buf = _io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for split_name, split_records in splits.items():
            for r in split_records:
                cat = r["corrected_category"] or r["predicted_category"]
                img_path = r["image_path"]
                if os.path.exists(img_path):
                    arcname = f"dataset/{split_name}/{cat}/{os.path.basename(img_path)}"
                    zf.write(img_path, arcname)

        # dataset.yaml
        yaml_lines = [
            "names:",
            "  0: recyclable",
            "  1: kitchen",
            "  2: hazardous",
            "  3: other",
            "nc: 4",
            f"train_count: {len(splits['train'])}",
            f"val_count: {len(splits['val'])}",
            f"test_count: {len(splits['test'])}",
        ]
        zf.writestr("dataset/dataset.yaml", "\n".join(yaml_lines))

        # labels.csv
        csv_lines = ["split,filename,category,label,confidence"]
        for split_name, split_records in splits.items():
            for r in split_records:
                cat = r["corrected_category"] or r["predicted_category"]
                label = r["corrected_label"] or r["predicted_label"]
                csv_lines.append(
                    f"{split_name},{os.path.basename(r['image_path'])},"
                    f"{cat},{label},{r['confidence']}"
                )
        zf.writestr("dataset/labels.csv", "\n".join(csv_lines))

    return buf.getvalue()


# ═══════════════════════════════════════
#  标注管理
# ═══════════════════════════════════════

def get_annotations(record_id: int) -> list:
    """获取某条记录的所有标注"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM image_annotations WHERE record_id = ? ORDER BY id",
        (record_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_annotations(record_id: int, annotations: list) -> list:
    """批量添加标注，返回新建标注的 ID 列表"""
    conn = sqlite3.connect(DB_PATH)
    ids = []
    now = datetime.now().isoformat()
    for ann in annotations:
        cursor = conn.execute(
            """INSERT INTO image_annotations
               (record_id, category, label, x1, y1, x2, y2, source, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record_id,
                ann["category"],
                ann["label"],
                ann["x1"],
                ann["y1"],
                ann["x2"],
                ann["y2"],
                ann.get("source", "manual"),
                now,
            ),
        )
        ids.append(cursor.lastrowid)
    conn.commit()
    conn.close()
    return ids


def update_annotation(annotation_id: int, data: dict):
    """更新单个标注"""
    conn = sqlite3.connect(DB_PATH)
    sets = []
    params = []
    for key in ("category", "label", "x1", "y1", "x2", "y2"):
        if key in data:
            sets.append(f"{key} = ?")
            params.append(data[key])
    if sets:
        params.append(annotation_id)
        conn.execute(
            f"UPDATE image_annotations SET {', '.join(sets)} WHERE id = ?",
            params,
        )
        conn.commit()
    conn.close()


def delete_annotation(annotation_id: int):
    """删除单个标注"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM image_annotations WHERE id = ?", (annotation_id,))
    conn.commit()
    conn.close()


def get_image_dimensions(image_path: str) -> tuple:
    """读取图片宽高，返回 (width, height)。文件不存在返回 (None, None)"""
    try:
        from PIL import Image as _Img
        with _Img.open(image_path) as img:
            return img.size
    except Exception:
        return None, None
