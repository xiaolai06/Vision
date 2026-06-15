"""
将 HuggingFace 下载的 Garbage_Classification_YOLO 数据集
映射到项目 4 分类结构 (recyclable/kitchen/hazardous/other)
"""

import shutil
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
CLS_DIR = BACKEND_DIR / "data" / "classification"

# 10 类到 4 类的映射
CATEGORY_MAP = {
    # recyclable (可回收物)
    "cardboard": "recyclable",
    "glass": "recyclable",
    "metal": "recyclable",
    "paper": "recyclable",
    "plastic": "recyclable",
    "clothes": "recyclable",
    "shoes": "recyclable",
    # kitchen (厨余垃圾)
    "biological": "kitchen",
    # hazardous (有害垃圾)
    "battery": "hazardous",
    # other (其他垃圾)
    "trash": "other",
}


def organize_hf_dataset(hf_dir: Path):
    """整理 HuggingFace 数据集到 4 分类目录"""
    print(f"\n=== 整理 HuggingFace 数据集 ===")
    print(f"  来源: {hf_dir}")

    for split in ["train", "val", "test"]:
        src_split = hf_dir / "classify" / split
        if not src_split.exists():
            print(f"  [WARN] 不存在: {src_split}")
            continue

        dst_split = CLS_DIR / split
        dst_split.mkdir(parents=True, exist_ok=True)

        stats = {}
        for cat_dir in sorted(src_split.iterdir()):
            if not cat_dir.is_dir():
                continue

            orig_name = cat_dir.name
            target_cat = CATEGORY_MAP.get(orig_name)
            if not target_cat:
                print(f"  [WARN] 无法映射类别: {orig_name}")
                continue

            dst_cat = dst_split / target_cat
            dst_cat.mkdir(parents=True, exist_ok=True)

            images = (
                list(cat_dir.glob("*.jpg"))
                + list(cat_dir.glob("*.png"))
                + list(cat_dir.glob("*.jpeg"))
                + list(cat_dir.glob("*.JPG"))
            )

            count = 0
            for img in images:
                dst_path = dst_cat / f"{orig_name}_{img.name}"
                if not dst_path.exists():
                    shutil.copy2(str(img), str(dst_path))
                count += 1

            key = f"{target_cat}"
            stats[key] = stats.get(key, 0) + count

        print(f"\n  {split}:")
        total = 0
        for cat in ["recyclable", "kitchen", "hazardous", "other"]:
            n = stats.get(cat, 0)
            total += n
            print(f"    {cat}: {n}")
        print(f"    总计: {total}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        # 自动查找 HF 缓存目录
        cache_dir = CLS_DIR / "raw" / "hf_cache"
        if cache_dir.exists():
            # 找到最新的 snapshot 目录
            snapshots = list(cache_dir.glob("datasets--khoaliamle--Garbage_Classification_YOLO/snapshots/*"))
            if snapshots:
                hf_dir = sorted(snapshots)[-1]
                print(f"自动找到: {hf_dir}")
            else:
                print("[ERROR] 未找到已下载的快照目录")
                sys.exit(1)
        else:
            print("用法: python organize_hf_dataset.py /path/to/downloaded/dataset")
            sys.exit(1)
    else:
        hf_dir = Path(sys.argv[1])

    organize_hf_dataset(hf_dir)
    print("\n整理完成!")
