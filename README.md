# 垃圾分类智能识别系统

基于深度学习的垃圾分类识别系统，支持**单物体分类**（MobileNetV2）和**多物体检测**（YOLOv8）两种模式。提供图片上传、摄像头拍照、实时视频流识别，以及数据标注、训练数据导出、模型在线切换等功能。

## 技术栈

| 层面 | 技术 |
|------|------|
| 前端 | Vue 3 (Composition API) + Vite + Chart.js + Vue Router |
| 后端 | FastAPI + SQLite + WebSocket |
| 模型 | PyTorch (MobileNetV2) + Ultralytics (YOLOv8) |
| 标注 | Canvas API (支持 HiDPI) |

## 快速开始

### 环境要求

- Python 3.10+
- Node.js 18+
- Git

### 1. 克隆项目

```bash
git clone https://github.com/xiaolai06/Vision.git
cd Vision
```

### 2. 启动后端

```bash
cd backend

# 创建虚拟环境（推荐）
python -m venv venv

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt

# 启动后端服务（默认 http://localhost:8000）
python -X utf8 main.py
```

> **注意**：Windows 用户务必加 `-X utf8` 参数，否则中文路径可能导致编码错误。

首次启动时，后端会自动：
- 创建 SQLite 数据库（`data/records.db`）
- 加载 `model/best.pt`（MobileNetV2 分类模型）
- 加载 `model/best_multi.pt`（YOLOv8 检测模型）

如果模型文件不存在，会自动进入 **mock 模式**（随机生成识别结果），不影响前端功能体验。

### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器（默认 http://localhost:5173）
npm run dev
```

浏览器打开 `http://localhost:5173` 即可使用。

## 功能页面

| 页面 | 路径 | 说明 |
|------|------|------|
| 识别 | `/` | 上传图片 / 摄像头拍照 / 实时视频流识别，支持切换分类/检测模型 |
| 记录 | `/records` | 查看识别历史记录，表格 + Chart.js 图表，支持多格式导出 |
| 标注 | `/annotation` | Canvas 标注页面，对检测结果的 bbox 进行人工修正 |
| 分类 | `/categories` | 四分类详情展示 |
| 关于 | `/about` | 项目介绍 |

## 训练模型

项目已包含训练脚本和训练数据（增强生成，约 1000 张图片）。

### 训练分类模型（MobileNetV2）

```bash
cd backend
python -X utf8 training/train_classification.py --epochs 30 --batch-size 32
```

训练完成后模型自动保存到 `model/best.pt`，重启后端即可使用。

### 训练检测模型（YOLOv8）

```bash
cd backend
python -X utf8 training/train_detection.py --epochs 50 --batch-size 16
```

训练完成后最佳权重自动保存到 `model/best_multi.pt`。

### 获取更好的训练数据

当前训练数据是基于少量图片增强生成的。要获得更高精度，建议下载真实数据集：

| 数据源 | 规模 | 下载地址 |
|--------|------|----------|
| 天池/华为云（推荐） | 4大类40小类，~645MB | https://tianchi.aliyun.com/dataset/175980 |
| 百度飞桨 | 4大类40小类 | https://aistudio.baidu.com/datasetdetail/239490 |

下载后运行：

```bash
# 导入天池数据集（自动解压 + 4分类映射 + 划分 train/val/test）
python -X utf8 data/download_datasets.py --source tianchi --tianchi-path 你的zip路径 --gen-detect

# 然后重新训练
python -X utf8 training/train_classification.py --epochs 50 --batch-size 32
python -X utf8 training/train_detection.py --epochs 100 --batch-size 16
```

## 项目结构

```
Vision/
├── backend/
│   ├── main.py                   # FastAPI 主程序（25 个 API 路由）
│   ├── model_manager.py          # 模型注册中心（加载/切换/推理）
│   ├── database.py               # SQLite 数据库 + 迁移 + 导出
│   ├── requirements.txt          # Python 依赖
│   ├── data/
│   │   ├── classification/       # 分类训练数据（ImageFolder 格式）
│   │   │   ├── train/            # recyclable / kitchen / hazardous / other
│   │   │   ├── val/
│   │   │   └── test/
│   │   ├── detection/            # 检测训练数据（YOLO 格式）
│   │   │   ├── data.yaml         # YOLOv8 配置
│   │   │   ├── images/           # train / val / test 图片
│   │   │   └── labels/           # train / val / test 标注
│   │   ├── download_datasets.py  # 数据集下载/准备脚本
│   │   └── generate_training_data.py
│   ├── model/                    # 模型权重（需自行训练，不纳入 Git）
│   │   ├── best.pt               # MobileNetV2
│   │   └── best_multi.pt         # YOLOv8
│   └── training/
│       ├── train_classification.py  # 分类训练脚本
│       └── train_detection.py       # 检测训练脚本
│
├── frontend/
│   ├── src/
│   │   ├── api/                  # 后端 API 封装
│   │   ├── components/           # 可复用组件
│   │   │   ├── BboxCanvas.vue    # Canvas bbox 标注
│   │   │   ├── RealtimeCamera.vue# 实时摄像头 + WebSocket
│   │   │   └── ResultDisplay.vue # 分类/检测双模式展示
│   │   ├── views/                # 页面视图
│   │   └── router/               # Vue Router 配置
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
├── README.md
└── 项目指南.md                    # 详细说明文档
```

## API 接口

后端运行在 `http://localhost:8000`，主要接口：

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/models` | 获取模型列表 |
| PUT | `/api/models/{id}/activate` | 切换活跃模型 |
| POST | `/api/predict` | 图片推理（multipart） |
| POST | `/api/predict_base64` | 图片推理（base64） |
| WS | `/ws/realtime` | 实时视频流推理 |
| GET | `/api/records` | 获取识别记录 |
| DELETE | `/api/records/{id}` | 删除记录 |
| GET | `/api/records/export/{format}` | 导出数据（csv/coco/yolo/yolo_det/coco_det） |
| GET | `/api/annotations/{id}` | 获取标注 |
| POST | `/api/annotations/{id}` | 保存标注 |
| PUT | `/api/annotations/{id}` | 更新标注 |
| DELETE | `/api/annotations/{id}` | 删除标注 |

## 常见问题

**Q: 后端启动报错 `ModuleNotFoundError`？**
确保在 `backend/` 目录下执行了 `pip install -r requirements.txt`。

**Q: 前端 `npm install` 报错？**
确保 Node.js 版本 >= 18，尝试删除 `node_modules/` 和 `package-lock.json` 后重新安装。

**Q: 识别结果一直是随机的？**
说明模型文件（`model/best.pt` / `model/best_multi.pt`）不存在，系统处于 mock 模式。运行训练脚本生成模型即可。

**Q: Windows 下中文路径报错？**
所有 Python 命令加上 `-X utf8` 参数：`python -X utf8 main.py`。

**Q: CUDA / GPU 相关？**
系统会自动检测 GPU，无 GPU 时使用 CPU 推理和训练（速度较慢但功能完整）。

## License

MIT
