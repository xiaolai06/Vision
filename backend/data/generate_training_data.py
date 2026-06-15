"""
生成充足的增强训练数据 + 从 Wikimedia Commons 下载真实图片
"""
import io
import os
import random
import time
import urllib.request
from pathlib import Path

from PIL import Image, ImageEnhance, ImageFilter

base = Path(__file__).resolve().parent.parent / "data" / "classification"

# ────────────────────────────────────────
# Part 1: Wikimedia Commons 免费图片 URL
# ────────────────────────────────────────
WIKI_IMAGES = {
    "recyclable": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4e/Plastic_bottles.jpg/320px-Plastic_bottles.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/34/Cardboard_boxes.jpg/320px-Cardboard_boxes.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e5/Glass_bottles.jpg/320px-Glass_bottles.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c7/Newspaper.jpg/320px-Newspaper.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/74/Aluminium_cans.jpg/320px-Aluminium_cans.jpg",
    ],
    "kitchen": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/0/01/Banana_peel.jpg/320px-Banana_peel.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4c/Eggshell.jpg/320px-Eggshell.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/a/a4/Apple_core.jpg/320px-Apple_core.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9e/Compost_Heap.jpg/320px-Compost_Heap.jpg",
    ],
    "hazardous": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/c/c3/AA_batteries.jpg/320px-AA_batteries.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Light_bulb.jpg/320px-Light_bulb.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/9/90/Medicine_bottles.jpg/320px-Medicine_bottles.jpg",
    ],
    "other": [
        "https://upload.wikimedia.org/wikipedia/commons/thumb/3/36/Cigarette_butt.jpg/320px-Cigarette_butt.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/f/f7/Tissue_paper.jpg/320px-Tissue_paper.jpg",
        "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Broken_glass.jpg/320px-Broken_glass.jpg",
    ],
}


def download_wiki_images():
    print("=== Part 1: 从 Wikimedia Commons 下载真实图片 ===")
    downloaded = {}
    for cat, urls in WIKI_IMAGES.items():
        dst = base / "raw" / "wiki" / cat
        dst.mkdir(parents=True, exist_ok=True)
        count = 0
        for i, url in enumerate(urls):
            fname = f"wiki_{cat}_{i:02d}.jpg"
            fpath = dst / fname
            if fpath.exists():
                count += 1
                continue
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "GarbageClassifier/1.0"})
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    img = Image.open(io.BytesIO(data)).convert("RGB")
                    img.save(str(fpath), quality=90)
                    count += 1
                    print(f"  OK: {fname}")
            except Exception as e:
                print(f"  FAIL: {fname} ({e})")
        downloaded[cat] = count
        print(f"  {cat}: {count} 张\n")
    return downloaded


def collect_sources():
    print("=== Part 2: 收集所有可用图片源 ===")
    source_images = {}

    # 从已有数据中读取
    for split in ["train", "val", "test"]:
        sp = base / split
        if not sp.exists():
            continue
        for cat_dir in sp.iterdir():
            if not cat_dir.is_dir():
                continue
            cat = cat_dir.name
            if cat not in source_images:
                source_images[cat] = []
            for img_file in cat_dir.iterdir():
                if img_file.is_file():
                    try:
                        img = Image.open(img_file).convert("RGB")
                        source_images[cat].append(img)
                    except Exception:
                        pass

    # 从 wiki 下载中读取
    wiki_dir = base / "raw" / "wiki"
    if wiki_dir.exists():
        for cat_dir in wiki_dir.iterdir():
            if not cat_dir.is_dir():
                continue
            cat = cat_dir.name
            if cat not in source_images:
                source_images[cat] = []
            for img_file in cat_dir.iterdir():
                if img_file.is_file():
                    try:
                        img = Image.open(img_file).convert("RGB")
                        source_images[cat].append(img)
                    except Exception:
                        pass

    for cat, imgs in sorted(source_images.items()):
        print(f"  {cat}: {len(imgs)} 张源图片")
    return source_images


def augment(img):
    aug = img.copy()
    w, h = aug.size

    # 随机裁剪
    margin = min(w, h) // 5
    if margin > 0:
        cx = random.randint(0, margin)
        cy = random.randint(0, margin)
        cw = random.randint(w - margin, w)
        ch = random.randint(h - margin, h)
        aug = aug.crop((cx, cy, cx + cw, cy + ch))

    aug = aug.resize((224, 224), Image.LANCZOS)

    if random.random() > 0.5:
        aug = aug.transpose(Image.FLIP_LEFT_RIGHT)
    if random.random() > 0.85:
        aug = aug.transpose(Image.FLIP_TOP_BOTTOM)

    aug = ImageEnhance.Brightness(aug).enhance(random.uniform(0.6, 1.4))
    aug = ImageEnhance.Contrast(aug).enhance(random.uniform(0.6, 1.4))
    aug = ImageEnhance.Color(aug).enhance(random.uniform(0.5, 1.5))
    aug = ImageEnhance.Sharpness(aug).enhance(random.uniform(0.5, 2.0))

    angle = random.uniform(-20, 20)
    fill = (random.randint(0, 50), random.randint(0, 50), random.randint(0, 50))
    aug = aug.rotate(angle, fillcolor=fill)

    if random.random() > 0.7:
        aug = aug.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 2.0)))

    if random.random() > 0.8:
        pixels = aug.load()
        for _ in range(100):
            x, y = random.randint(0, 223), random.randint(0, 223)
            r, g, b = pixels[x, y][:3]
            noise = random.randint(-30, 30)
            pixels[x, y] = (
                max(0, min(255, r + noise)),
                max(0, min(255, g + noise)),
                max(0, min(255, b + noise)),
            )

    return aug


def generate_data(source_images):
    print("\n=== Part 3: 生成增强训练数据 ===")
    TARGET = {"train": 150, "val": 40, "test": 40}

    # 先清除旧的增强数据（保留 wiki 原图）
    for split in ["train", "val", "test"]:
        for cat in ["recyclable", "kitchen", "hazardous", "other"]:
            dst = base / split / cat
            for f in dst.glob("aug_*.jpg"):
                try:
                    os.remove(str(f))
                except Exception:
                    pass

    total_generated = 0
    for split, target in TARGET.items():
        for cat in ["recyclable", "kitchen", "hazardous", "other"]:
            dst = base / split / cat
            dst.mkdir(parents=True, exist_ok=True)

            sources = source_images.get(cat, [])
            if not sources:
                print(f"  [WARN] {cat} 无源图片，创建占位数据")
                for i in range(target):
                    color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
                    img = Image.new("RGB", (224, 224), color)
                    img.save(str(dst / f"placeholder_{i:04d}.jpg"), quality=85)
                    total_generated += 1
                continue

            existing = list(dst.glob("wiki_*.jpg"))
            count = len(existing)

            for i in range(target - count):
                src_img = random.choice(sources)
                aug = augment(src_img)
                fname = f"aug_{cat}_{i:04d}.jpg"
                aug.save(str(dst / fname), quality=85)
                count += 1
                total_generated += 1

            print(f"  {split}/{cat}: {count}")

    print(f"\n共生成 {total_generated} 张增强图片!")


def print_stats():
    print("\n最终数据统计:")
    for split in ["train", "val", "test"]:
        sp = base / split
        total = 0
        for cat in sorted(sp.iterdir()):
            if cat.is_dir():
                n = len(list(cat.glob("*.jpg")))
                total += n
                print(f"  {split}/{cat.name}: {n}")
        print(f"  => {split}: {total}")
        print()


if __name__ == "__main__":
    print("=" * 50)
    print("  垃圾分类训练数据生成工具")
    print("=" * 50)
    print()

    download_wiki_images()
    sources = collect_sources()
    generate_data(sources)
    print_stats()
