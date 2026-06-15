"""
模型注册中心
管理分类模型（MobileNetV2）和检测模型（YOLOv8）的加载、切换与推理
"""

import io
import json
import random
import time
import os
from PIL import Image
from typing import Optional

# 4 个垃圾分类类别
CATEGORIES = {
    0: {
        "category": "recyclable",
        "label": "可回收物",
        "tip": "请保持清洁干燥后投放，去除残留液体和食物。",
        "items": ["塑料瓶", "纸盒", "金属罐", "玻璃瓶", "旧衣物", "易拉罐", "书本报纸", "快递纸箱"],
    },
    1: {
        "category": "kitchen",
        "label": "厨余垃圾",
        "tip": "沥干水分后投放。大骨头属于其他垃圾，小骨头和果皮才是厨余。",
        "items": ["果皮", "骨头", "剩饭剩菜", "茶叶渣", "蛋壳", "菜叶", "豆渣", "过期食品"],
    },
    2: {
        "category": "hazardous",
        "label": "有害垃圾",
        "tip": "轻拿轻放避免破损。电池请勿拆解，药品连带包装一起投放。",
        "items": ["电池", "灯泡", "过期药品", "油漆桶", "水银温度计", "指甲油", "杀虫剂", "X光片"],
    },
    3: {
        "category": "other",
        "label": "其他垃圾",
        "tip": "尽量沥干水分后投放。无法辨认或受污染的纸张都归入此类。",
        "items": ["纸巾", "陶瓷碎片", "烟蒂", "尘土", "一次性餐具", "污损纸张", "宠物粪便", "干燥剂"],
    },
}

CAT_NAME_TO_IDX = {v["category"]: k for k, v in CATEGORIES.items()}


class ModelRegistry:
    """模型注册中心，管理多个 ML 模型的加载与推理"""

    def __init__(self):
        self._models: dict[str, dict] = {}
        self._active_model_id: str = "mobilenet_v2"

    def register(self, model_id: str, model_type: str, model_obj, display_name: str):
        """注册一个模型"""
        self._models[model_id] = {
            "id": model_id,
            "type": model_type,
            "display_name": display_name,
            "model": model_obj,
            "is_mock": model_obj is None,
            "loaded_at": time.time() if model_obj else None,
        }

    def list_models(self) -> list[dict]:
        """列出所有已注册模型（不含 model 对象）"""
        result = []
        for m in self._models.values():
            result.append({
                "id": m["id"],
                "type": m["type"],
                "display_name": m["display_name"],
                "is_mock": m["is_mock"],
                "is_active": m["id"] == self._active_model_id,
            })
        return result

    def get_active(self) -> tuple[str, dict]:
        """返回当前活跃模型的 (model_id, model_info)"""
        info = self._models.get(self._active_model_id)
        return self._active_model_id, info

    def set_active(self, model_id: str) -> bool:
        """切换活跃模型，成功返回 True"""
        if model_id in self._models:
            self._active_model_id = model_id
            return True
        return False

    def predict(self, image_bytes: bytes, model_id: str = None) -> dict:
        """
        执行推理，返回结果字典。
        分类模型: {model_name, model_type, category, label, confidence, tip, items}
        检测模型: {model_name, model_type, count, detections: [{category, label, confidence, bbox, tip}]}
        """
        mid = model_id or self._active_model_id
        info = self._models.get(mid)
        if not info:
            raise ValueError(f"Unknown model: {mid}")

        model_obj = info["model"]
        model_type = info["type"]

        # 获取图片尺寸
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        img_w, img_h = img.size

        if model_type == "classification":
            return self._predict_classification(model_obj, image_bytes, mid, img_w, img_h)
        else:
            return self._predict_detection(model_obj, image_bytes, img, mid, img_w, img_h)

    def _predict_classification(self, model_obj, image_bytes: bytes, model_id: str, img_w: int, img_h: int) -> dict:
        """单物体分类推理"""
        if model_obj is not None:
            import torch
            transform = self._get_classification_transform()
            img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
            tensor = transform(img).unsqueeze(0)
            with torch.no_grad():
                output = model_obj(tensor)
                probs = torch.softmax(output, dim=1)[0]
                pred_idx = probs.argmax().item()
                confidence = probs[pred_idx].item()
        else:
            pred_idx = random.randint(0, 3)
            confidence = random.uniform(0.85, 0.98)

        cat = CATEGORIES[pred_idx]
        return {
            "model_name": model_id,
            "model_type": "classification",
            "category": cat["category"],
            "label": cat["label"],
            "confidence": round(confidence, 4),
            "tip": cat["tip"],
            "items": cat["items"],
            "image_width": img_w,
            "image_height": img_h,
        }

    def _predict_detection(self, model_obj, image_bytes: bytes, img: Image.Image, model_id: str, img_w: int, img_h: int) -> dict:
        """多物体检测推理"""
        if model_obj is not None:
            results = model_obj(img, verbose=False)
            detections = []
            for r in results:
                boxes = r.boxes
                if boxes is None:
                    continue
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    conf = float(boxes.conf[i].item())
                    bbox = boxes.xyxy[i].tolist()  # [x1, y1, x2, y2]
                    # 将 ultralytics 的类别映射到我们的 4 分类
                    if cls_id < 4:
                        cat = CATEGORIES[cls_id]
                    else:
                        cat = CATEGORIES[3]  # 默认为其他垃圾
                    detections.append({
                        "category": cat["category"],
                        "label": cat["label"],
                        "confidence": round(conf, 4),
                        "bbox": [round(v, 1) for v in bbox],
                        "tip": cat["tip"],
                    })
        else:
            # 模拟模式：随机生成 1-4 个检测框
            n = random.randint(1, 4)
            detections = []
            for _ in range(n):
                pred_idx = random.randint(0, 3)
                cat = CATEGORIES[pred_idx]
                w = random.uniform(40, min(180, img_w * 0.6))
                h = random.uniform(40, min(180, img_h * 0.6))
                x1 = random.uniform(0, img_w - w)
                y1 = random.uniform(0, img_h - h)
                detections.append({
                    "category": cat["category"],
                    "label": cat["label"],
                    "confidence": round(random.uniform(0.65, 0.98), 4),
                    "bbox": [round(x1, 1), round(y1, 1), round(x1 + w, 1), round(y1 + h, 1)],
                    "tip": cat["tip"],
                })

        return {
            "model_name": model_id,
            "model_type": "detection",
            "count": len(detections),
            "detections": detections,
            "image_width": img_w,
            "image_height": img_h,
        }

    def _get_classification_transform(self):
        """获取分类模型的预处理 transform"""
        import torchvision.transforms as T
        import torch
        return T.Compose([
            T.Resize((224, 224)),
            T.ToTensor(),
            T.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ])


# ─── 全局单例 ───
registry = ModelRegistry()


def load_all_models():
    """加载所有模型到注册中心"""
    import torch
    device = torch.device("cpu")

    # 1. MobileNetV2 分类模型
    model_path = "model/best.pt"
    try:
        model_obj = torch.load(model_path, map_location=device, weights_only=False)
        model_obj.eval()
        registry.register("mobilenet_v2", "classification", model_obj, "MobileNetV2 分类模型")
        print(f"MobileNetV2 loaded: {model_path}")
    except FileNotFoundError:
        registry.register("mobilenet_v2", "classification", None, "MobileNetV2 (mock)")
        print(f"Model not found: {model_path}, using mock mode")

    # 2. YOLOv8 检测模型
    yolo_path = "model/best_multi.pt"
    try:
        from ultralytics import YOLO
        yolo_model = YOLO(yolo_path)
        registry.register("yolov8", "detection", yolo_model, "YOLOv8 检测模型")
        print(f"YOLOv8 loaded: {yolo_path}")
    except FileNotFoundError:
        registry.register("yolov8", "detection", None, "YOLOv8 (mock)")
        print(f"Model not found: {yolo_path}, using mock mode")
    except ImportError:
        registry.register("yolov8", "detection", None, "YOLOv8 (mock - ultralytics not installed)")
        print("ultralytics not installed, YOLOv8 in mock mode")
    except Exception as e:
        registry.register("yolov8", "detection", None, f"YOLOv8 (mock - {e})")
        print(f"YOLOv8 load failed: {e}, using mock mode")


# 启动时加载
load_all_models()
