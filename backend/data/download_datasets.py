"""
数据集下载与准备脚本
===================
支持以下数据集来源：

1. 天池/华为云 垃圾分类数据集（4类40小类，推荐）
   - 下载: https://tianchi.aliyun.com/dataset/175980
   - 约 645MB，包含可回收/厨余/有害/其他四大类

2. Kaggle TrashNet（6类，需映射）
   - glass/paper/cardboard/plastic/metal/trash

3. 百度飞桨 垃圾分类数据集（4大类40小类）
   - 下载: https://aistudio.baidu.com/datasetdetail/239490

用法:
  python download_datasets.py --source tianchi --tianchi-path /path/to/downloaded.zip
  python download_datasets.py --source trashnet --trashnet-path /path/to/trashnet/
  python download_datasets.py --source custom --custom-path /path/to/images/
  python download_datasets.py --source detect_from_cls
"""

import argparse
import os
import shutil
import zipfile
import random
from pathlib import Path
from PIL import Image

# 项目路径
BACKEND_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BACKEND_DIR / "data"
CLS_DIR = DATA_DIR / "classification"
DET_DIR = DATA_DIR / "detection"

# TrashNet 到 4 分类的映射
TRASHNET_MAP = {
    "glass": "recyclable",
    "paper": "recyclable",
    "cardboard": "recyclable",
    "plastic": "recyclable",
    "metal": "recyclable",
    "trash": "other",
}

# 天池数据集 40 小类到 4 大类的映射
# 0-9: 其他垃圾, 10-19: 厨余垃圾, 20-29: 可回收物, 30-39: 有害垃圾
TIANCHI_SUBCATEGORY_MAP = {}
for i in range(0, 10):
    TIANCHI_SUBCATEGORY_MAP[i] = "other"
for i in range(10, 20):
    TIANCHI_SUBCATEGORY_MAP[i] = "kitchen"
for i in range(20, 30):
    TIANCHI_SUBCATEGORY_MAP[i] = "recyclable"
for i in range(30, 40):
    TIANCHI_SUBCATEGORY_MAP[i] = "hazardous"


def split_dataset(src_dir: Path, train_ratio=0.7, val_ratio=0.15, test_ratio=0.15):
    """将按类别组织的图片目录划分为 train/val/test"""
    categories = [d.name for d in src_dir.iterdir() if d.is_dir()]
    if not categories:
        print(f"  [WARN] 没有找到类别子目录: {src_dir}")
        return

    for cat in sorted(categories):
        cat_dir = src_dir / cat
        images = (
            list(cat_dir.glob("*.jpg"))
            + list(cat_dir.glob("*.png"))
            + list(cat_dir.glob("*.jpeg"))
            + list(cat_dir.glob("*.JPG"))
            + list(cat_dir.glob("*.PNG"))
        )
        if not images:
            print(f"  [WARN] {cat}: 无图片")
            continue

        random.shuffle(images)
        n = len(images)
        n_train = int(n * train_ratio)
        n_val = int(n * val_ratio)

        splits = {
            "train": images[:n_train],
            "val": images[n_train:n_train + int(n * val_ratio)],
            "test": images[n_train + int(n * val_ratio):],
        }

        for split_name, split_images in splits.items():
            dst = CLS_DIR / split_name / cat
            dst.mkdir(parents=True, exist_ok=True)
            for img_path in split_images:
                shutil.copy2(str(img_path), str(dst / img_path.name))
            print(f"  {cat}/{split_name}: {len(split_images)} 张")


def prepare_tianchi(zip_path: str):
    """准备天池/华为云垃圾分类数据集"""
    print("\n=== 准备天池垃圾分类数据集 ===")
    raw_dir = CLS_DIR / "raw" / "tianchi"
    raw_dir.mkdir(parents=True, exist_ok=True)

    # 解压
    print(f"  解压: {zip_path}")
    with zipfile.ZipFile(zip_path, "r") as zf:
        zf.extractall(str(raw_dir))

    # 查找解压后的图片
    all_images = list(raw_dir.rglob("*.jpg")) + list(raw_dir.rglob("*.png")) + list(raw_dir.rglob("*.jpeg"))
    if not all_images:
        print("  [ERROR] 解压后未找到图片文件")
        return

    print(f"  找到 {len(all_images)} 张图片")

    # 按目录结构分类
    staging = CLS_DIR / "raw" / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    for img_path in all_images:
        parent_name = img_path.parent.name
        mapped_cat = None

        # 尝试数字编号映射（天池常用编号）
        try:
            sub_id = int(parent_name)
            mapped_cat = TIANCHI_SUBCATEGORY_MAP.get(sub_id, "other")
        except ValueError:
            pass

        # 尝试从目录名匹配
        if not mapped_cat:
            name_lower = parent_name.lower()
            if any(k in name_lower for k in ["recyclable", "recycle", "recycl"]):
                mapped_cat = "recyclable"
            elif any(k in name_lower for k in ["kitchen", "food", "organic", "wet"]):
                mapped_cat = "kitchen"
            elif any(k in name_lower for k in ["hazardous", "hazard", "dangerous"]):
                mapped_cat = "hazardous"
            else:
                mapped_cat = "other"

        dst = staging / mapped_cat
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(str(img_path), str(dst / img_path.name))

    print("\n  划分 train/val/test...")
    split_dataset(staging)
    print("  天池数据集准备完成!")


def prepare_trashnet(trashnet_dir: str):
    """准备 TrashNet 数据集（映射到4分类）"""
    print("\n=== 准备 TrashNet 数据集 ===")
    src = Path(trashnet_dir)

    staging = CLS_DIR / "raw" / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    for orig_cat, target_cat in TRASHNET_MAP.items():
        cat_dir = src / orig_cat
        if not cat_dir.exists():
            print(f"  [WARN] 目录不存在: {cat_dir}")
            continue
        dst = staging / target_cat
        dst.mkdir(parents=True, exist_ok=True)
        images = list(cat_dir.glob("*.jpg")) + list(cat_dir.glob("*.png"))
        for img in images:
            shutil.copy2(str(img), str(dst / f"{orig_cat}_{img.name}"))
        print(f"  {orig_cat} -> {target_cat}: {len(images)} 张")

    print("\n  划分 train/val/test...")
    split_dataset(staging)
    print("  TrashNet 数据集准备完成!")


def prepare_custom(custom_dir: str):
    """准备自定义数据集（按类别文件夹组织）"""
    print("\n=== 准备自定义数据集 ===")
    src = Path(custom_dir)

    subdirs = [d.name for d in src.iterdir() if d.is_dir()]
    print(f"  找到类别目录: {subdirs}")

    staging = CLS_DIR / "raw" / "staging"
    staging.mkdir(parents=True, exist_ok=True)

    for subdir in subdirs:
        src_cat = src / subdir
        name_lower = subdir.lower()

        # 智能映射
        if any(k in name_lower for k in ["recyclable", "recycle", "recycl"]):
            target = "recyclable"
        elif any(k in name_lower for k in ["kitchen", "food", "organic", "wet"]):
            target = "kitchen"
        elif any(k in name_lower for k in ["hazardous", "hazard", "dangerous"]):
            target = "hazardous"
        elif any(k in name_lower for k in ["other", "general", "dry"]):
            target = "other"
        else:
            target = subdir
            print(f"  [WARN] 无法映射 {subdir}，保持原名")

        dst = staging / target
        dst.mkdir(parents=True, exist_ok=True)
        images = (
            list(src_cat.glob("*.jpg"))
            + list(src_cat.glob("*.png"))
            + list(src_cat.glob("*.jpeg"))
            + list(src_cat.glob("*.JPG"))
        )
        for img in images:
            shutil.copy2(str(img), str(dst / img.name))
        print(f"  {subdir} -> {target}: {len(images)} 张")

    print("\n  划分 train/val/test...")
    split_dataset(staging)
    print("  自定义数据集准备完成!")


def prepare_detection_from_classification():
    """
    从分类数据集生成检测数据集（全图作为 bounding box）
    这是一个基线方案，后续可以用标注页面创建更精确的检测标注
    """
    print("\n=== 从分类数据生成检测训练数据 ===")

    cat_to_id = {"recyclable": 0, "kitchen": 1, "hazardous": 2, "other": 3}

    for split in ["train", "val", "test"]:
        split_cls_dir = CLS_DIR / split
        if not split_cls_dir.exists():
            continue

        img_dst = DET_DIR / "images" / split
        lbl_dst = DET_DIR / "labels" / split
        img_dst.mkdir(parents=True, exist_ok=True)
        lbl_dst.mkdir(parents=True, exist_ok=True)

        count = 0
        for cat_dir in split_cls_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            cat_name = cat_dir.name
            cls_id = cat_to_id.get(cat_name, 3)

            for img_path in (
                list(cat_dir.glob("*.jpg"))
                + list(cat_dir.glob("*.png"))
                + list(cat_dir.glob("*.jpeg"))
            ):
                # 复制图片
                dst_name = f"{cat_name}_{img_path.name}"
                dst_img = img_dst / dst_name
                shutil.copy2(str(img_path), str(dst_img))

                # 获取图片尺寸
                try:
                    with Image.open(img_path) as im:
                        w, h = im.size
                except Exception:
                    continue

                # YOLO 格式: class_id center_x center_y width height (归一化)
                # 全图作为 bounding box: center=(0.5, 0.5), size=(1.0, 1.0)
                label_file = lbl_dst / f"{cat_name}_{img_path.stem}.txt"
                with open(label_file, "w") as f:
                    f.write(f"{cls_id} 0.5000 0.5000 1.0000 1.0000\n")
                count += 1

        print(f"  {split}: {count} 张图片+标注")

    print("  检测数据生成完成! (全图 bounding box 基线方案)")
    print("  提示: 使用标注页面可以创建更精确的多目标检测标注")


def print_dataset_stats():
    """打印当前数据集统计"""
    print("\n=== 当前数据集统计 ===")

    # 分类数据
    print("\n分类数据集:")
    for split in ["train", "val", "test"]:
        split_dir = CLS_DIR / split
        if not split_dir.exists():
            continue
        total = 0
        for cat_dir in sorted(split_dir.iterdir()):
            if not cat_dir.is_dir():
                continue
            n = len(list(cat_dir.glob("*")))
            if n > 0:
                print(f"  {split}/{cat_dir.name}: {n} 张")
                total += n
        print(f"  {split} 总计: {total} 张")

    # 检测数据
    print("\n检测数据集:")
    for split in ["train", "val", "test"]:
        img_dir = DET_DIR / "images" / split
        if not img_dir.exists():
            continue
        n_imgs = len(list(img_dir.glob("*")))
        lbl_dir = DET_DIR / "labels" / split
        n_lbls = len(list(lbl_dir.glob("*.txt"))) if lbl_dir.exists() else 0
        print(f"  {split}: {n_imgs} 图片, {n_lbls} 标注")


def main():
    parser = argparse.ArgumentParser(description="垃圾分类数据集准备工具")
    parser.add_argument(
        "--source",
        choices=["tianchi", "trashnet", "custom", "detect_from_cls", "stats"],
        help="数据来源",
    )
    parser.add_argument("--tianchi-path", help="天池数据集 ZIP 路径")
    parser.add_argument("--trashnet-path", help="TrashNet 解压目录路径")
    parser.add_argument("--custom-path", help="自定义数据集目录（按类别子文件夹组织）")
    parser.add_argument("--train-ratio", type=float, default=0.7)
    parser.add_argument("--val-ratio", type=float, default=0.15)
    parser.add_argument("--test-ratio", type=float, default=0.15)
    parser.add_argument("--gen-detect", action="store_true", help="同时生成检测数据集")

    args = parser.parse_args()

    print("=" * 50)
    print("  垃圾分类数据集准备工具")
    print("=" * 50)
    print(f"  数据目录: {DATA_DIR}")
    print(f"  分类目录: {CLS_DIR}")
    print(f"  检测目录: {DET_DIR}")
    print()

    if args.source == "tianchi":
        if not args.tianchi_path:
            print("[ERROR] 请指定 --tianchi-path 天池数据集 ZIP 文件路径")
            print("  下载地址: https://tianchi.aliyun.com/dataset/175980")
            return
        prepare_tianchi(args.tianchi_path)

    elif args.source == "trashnet":
        if not args.trashnet_path:
            print("[ERROR] 请指定 --trashnet-path TrashNet 解压目录")
            print("  下载: kaggle datasets download -d garythung/trashnet")
            return
        prepare_trashnet(args.trashnet_path)

    elif args.source == "custom":
        if not args.custom_path:
            print("[ERROR] 请指定 --custom-path 自定义数据集目录")
            return
        prepare_custom(args.custom_path)

    elif args.source == "detect_from_cls":
        prepare_detection_from_classification()
        return

    elif args.source == "stats":
        print_dataset_stats()
        return

    else:
        print("用法示例:")
        print()
        print("  1. 天池数据集（推荐，4大类40小类）:")
        print("     python download_datasets.py --source tianchi --tianchi-path garbage.zip")
        print()
        print("  2. 自定义数据集（按类别文件夹组织）:")
        print("     python download_datasets.py --source custom --custom-path /path/to/images/")
        print()
        print("  3. 从分类数据生成检测数据:")
        print("     python download_datasets.py --source detect_from_cls")
        print()
        print("  4. 完整流程（分类+检测）:")
        print("     python download_datasets.py --source tianchi --tianchi-path xxx.zip --gen-detect")
        print()
        print("  5. 查看当前数据集统计:")
        print("     python download_datasets.py --source stats")
        print()
        print("推荐数据集来源:")
        print("  - 天池/华为云: https://tianchi.aliyun.com/dataset/175980  (4类, ~645MB)")
        print("  - 百度飞桨:   https://aistudio.baidu.com/datasetdetail/239490  (4类40小类)")
        print("  - Kaggle:     kaggle datasets download -d garythung/trashnet   (6类, 需映射)")
        return

    if args.gen_detect:
        prepare_detection_from_classification()

    print_dataset_stats()


if __name__ == "__main__":
    main()
