"""
YOLOv8 垃圾分类检测模型训练脚本
================================
用法:
  python train_detection.py --epochs 50 --img-size 640 --batch-size 16
  python train_detection.py --pretrained --epochs 100 --model yolov8s
  python train_detection.py --resume   # 从上次中断处继续
"""

import argparse
import shutil
import sys
import time
from pathlib import Path

# 路径配置
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data" / "detection"
MODEL_DIR = BACKEND_DIR / "model"
DATA_YAML = DATA_DIR / "data.yaml"


def check_data():
    """检查数据集是否准备好"""
    if not DATA_YAML.exists():
        print(f"[ERROR] 数据配置文件不存在: {DATA_YAML}")
        return False

    train_imgs = DATA_DIR / "images" / "train"
    if not train_imgs.exists():
        print(f"[ERROR] 训练图片目录不存在: {train_imgs}")
        return False

    images = (
        list(train_imgs.glob("*.jpg"))
        + list(train_imgs.glob("*.png"))
        + list(train_imgs.glob("*.jpeg"))
    )
    if len(images) == 0:
        print(f"[ERROR] 训练图片目录为空: {train_imgs}")
        print("请先运行 data/download_datasets.py 准备数据集")
        return False

    train_labels = DATA_DIR / "labels" / "train"
    labels = list(train_labels.glob("*.txt")) if train_labels.exists() else []

    print(f"  训练图片: {len(images)} 张")
    print(f"  训练标注: {len(labels)} 个")

    if len(labels) == 0:
        print("[WARN] 没有标注文件，检测训练可能无法正常工作")

    # 检查验证集
    val_imgs = DATA_DIR / "images" / "val"
    if not val_imgs.exists() or len(list(val_imgs.glob("*"))) == 0:
        print("[WARN] 验证集为空，YOLOv8 会从训练集自动划分")

    return True


def main():
    parser = argparse.ArgumentParser(description="YOLOv8 垃圾分类检测训练")
    parser.add_argument("--epochs", type=int, default=50, help="训练轮数")
    parser.add_argument("--img-size", type=int, default=640, help="输入图片尺寸")
    parser.add_argument("--batch-size", type=int, default=16, help="批大小")
    parser.add_argument("--lr", type=float, default=0.01, help="初始学习率")
    parser.add_argument("--pretrained", action="store_true", default=True,
                        help="使用预训练权重（默认）")
    parser.add_argument("--no-pretrained", action="store_false", dest="pretrained")
    parser.add_argument("--model", type=str, default="yolov8n",
                        choices=["yolov8n", "yolov8s", "yolov8m", "yolov8l"],
                        help="模型大小 (n=nano, s=small, m=medium, l=large)")
    parser.add_argument("--data-yaml", type=str, default=str(DATA_YAML),
                        help="数据配置 YAML 路径")
    parser.add_argument("--output", type=str, default=str(MODEL_DIR), help="输出目录")
    parser.add_argument("--device", type=str, default="auto",
                        help="设备 (auto/cpu/0/0,1)")
    parser.add_argument("--workers", type=int, default=4, help="数据加载线程数")
    parser.add_argument("--patience", type=int, default=15,
                        help="早停耐心值（多少轮无改善后停止）")
    parser.add_argument("--resume", action="store_true",
                        help="从上次中断处继续训练")
    args = parser.parse_args()

    # 导入 ultralytics
    try:
        from ultralytics import YOLO
    except ImportError:
        print("[ERROR] ultralytics 未安装! 请运行: pip install ultralytics")
        sys.exit(1)

    print(f"\n{'=' * 50}")
    print(f"  YOLOv8 垃圾分类检测训练")
    print(f"{'=' * 50}")
    print(f"  模型: {args.model}")
    print(f"  Epochs: {args.epochs}")
    print(f"  图片尺寸: {args.img_size}")
    print(f"  Batch Size: {args.batch_size}")
    print(f"  学习率: {args.lr}")
    print(f"  预训练: {args.pretrained}")
    print(f"  早停耐心: {args.patience}")
    print()

    # 检查数据
    print("检查数据集...")
    if not check_data():
        sys.exit(1)
    print()

    # 设备
    if args.device == "auto":
        import torch
        device = "0" if torch.cuda.is_available() else "cpu"
    else:
        device = args.device
    print(f"  设备: {device}")

    # 加载模型
    if args.resume:
        last_pt = Path(args.output) / "runs" / "detect" / "train" / "weights" / "last.pt"
        if not last_pt.exists():
            print(f"[ERROR] 未找到上次训练的权重: {last_pt}")
            sys.exit(1)
        model = YOLO(str(last_pt))
        print(f"  继续训练: {last_pt}")
    elif args.pretrained:
        model_name = f"{args.model}.pt"
        print(f"  加载预训练模型: {model_name}")
        model = YOLO(model_name)
    else:
        model = YOLO(f"{args.model}.yaml")
        print(f"  从头构建模型: {args.model}")

    # 开始训练
    print("\n开始训练...")
    start_time = time.time()

    results = model.train(
        data=args.data_yaml,
        epochs=args.epochs,
        imgsz=args.img_size,
        batch=args.batch_size,
        lr0=args.lr,
        device=device,
        workers=args.workers,
        patience=args.patience,
        project=str(Path(args.output) / "runs" / "detect"),
        name="train",
        exist_ok=True,
        save=True,
        save_period=10,
        plots=True,
        verbose=True,
        # 数据增强参数
        hsv_h=0.015,
        hsv_s=0.5,
        hsv_v=0.3,
        degrees=10,
        translate=0.1,
        scale=0.3,
        fliplr=0.5,
        mosaic=1.0,
        mixup=0.1,
    )

    elapsed = time.time() - start_time
    print(f"\n训练完成! 总耗时: {elapsed / 60:.1f} 分钟")

    # 复制最佳权重到目标位置
    best_pt = Path(args.output) / "runs" / "detect" / "train" / "weights" / "best.pt"
    target_pt = Path(args.output) / "best_multi.pt"
    if best_pt.exists():
        target_pt.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(best_pt), str(target_pt))
        print(f"最佳权重已复制到: {target_pt}")
    else:
        print(f"[WARN] 未找到最佳权重文件: {best_pt}")

    # 打印结果摘要
    runs_dir = Path(args.output) / "runs" / "detect" / "train"
    print(f"\n结果文件:")
    print(f"  权重目录: {runs_dir / 'weights'}")
    print(f"  训练图表: {runs_dir}")
    print(f"  最终模型: {target_pt}")


if __name__ == "__main__":
    main()
