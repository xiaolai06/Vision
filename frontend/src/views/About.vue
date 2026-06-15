<script setup>
const techStack = [
  { label: '前端框架', value: 'Vue 3 + Vite' },
  { label: '后端框架', value: 'FastAPI (Python)' },
  { label: '模型框架', value: 'PyTorch / torchvision' },
  { label: '模型架构', value: 'MobileNetV2 (迁移学习)' },
  { label: '推理加速', value: 'ONNX Runtime (可选)' },
  { label: '图像预处理', value: 'Pillow (PIL)' },
]

const metrics = [
  { label: '测试集准确率', value: '95.2%', detail: '2000+ 张测试图片 Top-1' },
  { label: '推理延迟', value: '< 0.3s', detail: 'CPU 单张推理耗时' },
  { label: '模型体积', value: '4.2 MB', detail: '可运行于边缘设备' },
]

const dataSources = [
  { icon: '🌐', title: '网络采集', desc: '搜索引擎公开图片，每类 50-100 张基础数据' },
  { icon: '📱', title: '实拍数据', desc: '手机/摄像头拍摄，多角度多光线' },
  { icon: '📦', title: '开源数据集', desc: 'Kaggle garbage_classification 现成数据集' },
]
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="page-head">
        <h1>关于项目</h1>
        <p>技术方案与实现细节</p>
      </div>

      <!-- 技术栈 -->
      <section class="section">
        <h2 class="section-title">技术栈</h2>
        <div class="tech-card">
          <div v-for="(item, i) in techStack" :key="item.label" class="tech-row" :class="{ 'no-border': i === techStack.length - 1 }">
            <span class="tech-label">{{ item.label }}</span>
            <span class="tech-value">{{ item.value }}</span>
          </div>
        </div>
      </section>

      <!-- 性能 + 数据来源并排 -->
      <section class="section">
        <h2 class="section-title">模型性能</h2>
        <div class="metrics-grid">
          <div v-for="m in metrics" :key="m.label" class="metric-card">
            <div class="metric-value">{{ m.value }}</div>
            <div class="metric-label">{{ m.label }}</div>
            <div class="metric-detail">{{ m.detail }}</div>
          </div>
        </div>
      </section>

      <section class="section">
        <h2 class="section-title">训练数据</h2>
        <div class="sources-grid">
          <div v-for="s in dataSources" :key="s.title" class="source-card">
            <span class="source-icon">{{ s.icon }}</span>
            <h3>{{ s.title }}</h3>
            <p>{{ s.desc }}</p>
          </div>
        </div>
      </section>

      <!-- 部署 -->
      <section class="section">
        <h2 class="section-title">部署方式</h2>
        <div class="deploy-list">
          <div class="deploy-item">
            <span class="deploy-num">1</span>
            <div>
              <strong>开发环境</strong>
              <p>前端 <code>npm run dev</code>（:5173）+ 后端 <code>python -m uvicorn main:app --reload</code>（:8000），Vite proxy 自动转发 API</p>
            </div>
          </div>
          <div class="deploy-item">
            <span class="deploy-num">2</span>
            <div>
              <strong>生产部署</strong>
              <p>前端 <code>npm run build</code> 打包静态文件，Nginx 反代 API 到 uvicorn</p>
            </div>
          </div>
          <div class="deploy-item">
            <span class="deploy-num">3</span>
            <div>
              <strong>边缘设备</strong>
              <p>树莓派 / Jetson Nano 运行 ONNX Runtime + FastAPI，模型 4.2MB，CPU 实时推理</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 2rem 3rem 3rem;
}

.page-head {
  margin-bottom: 1.75rem;
}
.page-head h1 {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: .2rem;
}
.page-head p {
  font-size: .88rem;
  color: var(--text-muted);
}

.section {
  margin-bottom: 2rem;
}
.section-title {
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: .85rem;
  padding-bottom: .45rem;
  border-bottom: 1px solid var(--border);
}

/* 技术栈表格 */
.tech-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow: hidden;
}
.tech-row {
  display: flex;
  padding: .65rem 1.15rem;
  border-bottom: 1px solid var(--border);
}
.tech-row.no-border { border-bottom: none; }
.tech-label {
  width: 130px;
  flex-shrink: 0;
  font-size: .86rem;
  color: var(--text-muted);
}
.tech-value {
  font-size: .86rem;
  font-weight: 500;
}

/* 性能指标 */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
.metric-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
  text-align: center;
}
.metric-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--green-600);
  margin-bottom: .15rem;
}
.metric-label {
  font-size: .85rem;
  color: var(--text-secondary);
  margin-bottom: .2rem;
}
.metric-detail {
  font-size: .78rem;
  color: var(--text-muted);
}

/* 数据来源 */
.sources-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}
.source-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.25rem;
}
.source-icon {
  font-size: 1.5rem;
  display: block;
  margin-bottom: .6rem;
}
.source-card h3 {
  font-size: .9rem;
  font-weight: 600;
  margin-bottom: .3rem;
}
.source-card p {
  font-size: .82rem;
  color: var(--text-secondary);
  line-height: 1.5;
}

/* 部署步骤 */
.deploy-list {
  display: flex;
  flex-direction: column;
  gap: .75rem;
}
.deploy-item {
  display: flex;
  gap: .85rem;
  align-items: flex-start;
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.15rem;
}
.deploy-num {
  width: 28px; height: 28px;
  border-radius: 50%;
  background: var(--green-100);
  color: var(--green-700);
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: .82rem;
  flex-shrink: 0;
}
.deploy-item strong {
  display: block;
  font-size: .9rem;
  margin-bottom: .15rem;
}
.deploy-item p {
  font-size: .82rem;
  color: var(--text-secondary);
  line-height: 1.5;
}
.deploy-item code {
  background: var(--gray-200);
  padding: .1rem .35rem;
  border-radius: 3px;
  font-size: .8rem;
  font-family: 'SF Mono', Consolas, monospace;
}

@media (max-width: 768px) {
  .metrics-grid,
  .sources-grid { grid-template-columns: 1fr; }
  .tech-label { width: 100px; }
}
</style>
