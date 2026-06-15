"""
MobileNetV2 垃圾分类分类模型训练脚本
===================================
用法:
  python train_classification.py --epochs 30 --batch-size 32 --lr 0.001
  python train_classification.py --epochs 50 --batch-size 64 --pretrained
  python train_classification.py --data-dir /path/to/classification --epochs 30
"""

import argparse
import copy
import json
import sys
import time
from pathlib import Path

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader
from torchvision import datasets, models, transforms

# 路径配置
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data" / "classification"
MODEL_DIR = BACKEND_DIR / "model"

# 类别标签（与 model_manager.py 保持一致）
LABELS_ZH = ["可回收物", "厨余垃圾", "有害垃圾", "其他垃圾"]

# 数据增强与预处理
TRAIN_TRANSFORM = transforms.Compose([
    transforms.RandomResizedCrop(224, scale=(0.7, 1.0)),
    transforms.RandomHorizontalFlip(),
    transforms.RandomVerticalFlip(),
    transforms.ColorJitter(brightness=0.3, contrast=0.3, saturation=0.2, hue=0.1),
    transforms.RandomRotation(15),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

VAL_TRANSFORM = transforms.Compose([
    transforms.Resize(256),
    transforms.CenterCrop(224),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])


def create_model(num_classes: int, pretrained: bool = True) -> nn.Module:
    """创建 MobileNetV2 模型，替换分类头"""
    if pretrained:
        weights = models.MobileNet_V2_Weights.IMAGENET1K_V1
        model = models.mobilenet_v2(weights=weights)
    else:
        model = models.mobilenet_v2(weights=None)

    # 替换分类头
    in_features = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3),
        nn.Linear(in_features, 256),
        nn.ReLU(),
        nn.Dropout(p=0.2),
        nn.Linear(256, num_classes),
    )
    return model


def get_data_loaders(batch_size: int, data_dir: Path):
    """创建数据加载器"""
    train_dir = data_dir / "train"
    val_dir = data_dir / "val"

    if not train_dir.exists():
        print(f"[ERROR] 训练数据目录不存在: {train_dir}")
        print("请先运行 data/download_datasets.py 准备数据集")
        sys.exit(1)

    train_dataset = datasets.ImageFolder(str(train_dir), transform=TRAIN_TRANSFORM)
    val_dataset = datasets.ImageFolder(str(val_dir), transform=VAL_TRANSFORM)

    print(f"  训练集类别: {train_dataset.classes}")
    print(f"  训练集样本数: {len(train_dataset)}")
    print(f"  验证集样本数: {len(val_dataset)}")

    if len(train_dataset) == 0:
        print("[ERROR] 训练集为空! 请先准备数据集")
        sys.exit(1)

    train_loader = DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=True,
        num_workers=2,
        pin_memory=True,
        drop_last=True,
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=2,
        pin_memory=True,
    )
    return train_loader, val_loader, train_dataset.classes


def train_one_epoch(model, loader, criterion, optimizer, device):
    """训练一个 epoch"""
    model.train()
    running_loss = 0.0
    correct = 0
    total = 0

    for batch_idx, (images, labels) in enumerate(loader):
        images, labels = images.to(device), labels.to(device)

        optimizer.zero_grad()
        outputs = model(images)
        loss = criterion(outputs, labels)
        loss.backward()
        optimizer.step()

        running_loss += loss.item() * images.size(0)
        _, predicted = outputs.max(1)
        total += labels.size(0)
        correct += predicted.eq(labels).sum().item()

        if (batch_idx + 1) % 10 == 0:
            print(
                f"    Batch {batch_idx + 1}/{len(loader)}: "
                f"loss={loss.item():.4f}, acc={100.0 * correct / total:.1f}%"
            )

    epoch_loss = running_loss / max(total, 1)
    epoch_acc = 100.0 * correct / max(total, 1)
    return epoch_loss, epoch_acc


def validate(model, loader, criterion, device):
    """验证"""
    model.eval()
    running_loss = 0.0
    correct = 0
    total = 0

    with torch.no_grad():
        for images, labels in loader:
            images, labels = images.to(device), labels.to(device)
            outputs = model(images)
            loss = criterion(outputs, labels)

            running_loss += loss.item() * images.size(0)
            _, predicted = outputs.max(1)
            total += labels.size(0)
            correct += predicted.eq(labels).sum().item()

    epoch_loss = running_loss / max(total, 1)
    epoch_acc = 100.0 * correct / max(total, 1)
    return epoch_loss, epoch_acc


def main():
    parser = argparse.ArgumentParser(description="MobileNetV2 垃圾分类训练")
    parser.add_argument("--epochs", type=int, default=30, help="训练轮数")
    parser.add_argument("--batch-size", type=int, default=32, help="批大小")
    parser.add_argument("--lr", type=float, default=0.001, help="学习率")
    parser.add_argument("--weight-decay", type=float, default=1e-4, help="权重衰减")
    parser.add_argument("--pretrained", action="store_true", default=True,
                        help="使用 ImageNet 预训练权重（默认）")
    parser.add_argument("--no-pretrained", action="store_false", dest="pretrained",
                        help="不使用预训练权重")
    parser.add_argument("--data-dir", type=str, default=str(DATA_DIR), help="数据目录")
    parser.add_argument("--output", type=str, default=str(MODEL_DIR / "best.pt"),
                        help="模型输出路径")
    parser.add_argument("--device", type=str, default="auto", help="设备 (auto/cpu/cuda)")
    args = parser.parse_args()

    # 设备选择
    if args.device == "auto":
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    else:
        device = torch.device(args.device)

    print(f"\n{'=' * 50}")
    print(f"  MobileNetV2 垃圾分类训练")
    print(f"{'=' * 50}")
    print(f"  设备: {device}")
    print(f"  Epochs: {args.epochs}")
    print(f"  Batch Size: {args.batch_size}")
    print(f"  学习率: {args.lr}")
    print(f"  预训练: {args.pretrained}")
    print(f"  数据目录: {args.data_dir}")
    print(f"  输出路径: {args.output}")
    print()

    # 数据
    data_dir = Path(args.data_dir)
    train_loader, val_loader, class_names = get_data_loaders(args.batch_size, data_dir)
    num_classes = len(class_names)
    print(f"  类别数: {num_classes}")
    print(f"  类别映射: {dict(enumerate(class_names))}")
    print()

    # 模型
    model = create_model(num_classes, pretrained=args.pretrained).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=args.epochs, eta_min=1e-6)

    # 训练循环
    best_acc = 0.0
    best_model_wts = None
    start_time = time.time()

    for epoch in range(1, args.epochs + 1):
        print(f"Epoch {epoch}/{args.epochs} (lr={scheduler.get_last_lr()[0]:.6f})")

        train_loss, train_acc = train_one_epoch(
            model, train_loader, criterion, optimizer, device
        )
        val_loss, val_acc = validate(model, val_loader, criterion, device)
        scheduler.step()

        print(f"  Train: loss={train_loss:.4f}, acc={train_acc:.1f}%")
        print(f"  Val:   loss={val_loss:.4f}, acc={val_acc:.1f}%")

        if val_acc > best_acc:
            best_acc = val_acc
            best_model_wts = copy.deepcopy(model.state_dict())
            print(f"  >> 新最佳模型! acc={best_acc:.1f}%")
        print()

    # 保存结果
    elapsed = time.time() - start_time
    print(f"\n训练完成! 总耗时: {elapsed / 60:.1f} 分钟")
    print(f"最佳验证准确率: {best_acc:.1f}%")

    if best_model_wts is not None:
        model.load_state_dict(best_model_wts)

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(model, str(output_path))
    print(f"模型已保存: {output_path}")

    # 保存类别映射
    class_map_path = output_path.parent / "class_map.json"
    class_map = {
        "classes": class_names,
        "labels": LABELS_ZH[:num_classes],
        "num_classes": num_classes,
    }
    with open(class_map_path, "w", encoding="utf-8") as f:
        json.dump(class_map, f, ensure_ascii=False, indent=2)
    print(f"类别映射已保存: {class_map_path}")


if __name__ == "__main__":
    main()
