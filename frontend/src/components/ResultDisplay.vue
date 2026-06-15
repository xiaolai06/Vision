<script setup>
const props = defineProps({
  result: { type: Object, default: null },
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const meta = {
  recyclable:  { label: '可回收物', icon: '♻️',  bin: '蓝色垃圾桶', binDot: '#3182ce', color: 'var(--cat-recycle)', bg: 'var(--cat-recycle-bg)' },
  kitchen:     { label: '厨余垃圾', icon: '🥬',  bin: '绿色垃圾桶', binDot: '#38a169', color: 'var(--cat-kitchen)', bg: 'var(--cat-kitchen-bg)' },
  hazardous:   { label: '有害垃圾', icon: '⚠️',  bin: '红色垃圾桶', binDot: '#e53e3e', color: 'var(--cat-hazard)', bg: 'var(--cat-hazard-bg)' },
  other:       { label: '其他垃圾', icon: '🗑️',  bin: '灰色垃圾桶', binDot: '#718096', color: 'var(--cat-other)', bg: 'var(--cat-other-bg)' },
}
function m(k) { return meta[k] || meta.other }

function isDetection() {
  return props.result && props.result.model_type === 'detection'
}
</script>

<template>
  <div class="result">

    <!-- 空状态 -->
    <div v-if="!result && !loading && !error" class="state">
      <div class="state-icon">🔍</div>
      <p class="state-title">等待识别</p>
      <p class="state-hint">上传图片或拍照后结果将显示在这里</p>
    </div>

    <!-- 加载 -->
    <div v-if="loading" class="state">
      <div class="spin"></div>
      <p class="state-title">识别中...</p>
    </div>

    <!-- 错误 -->
    <div v-if="error" class="state">
      <p style="color:var(--cat-hazard)">{{ error }}</p>
    </div>

    <!-- 分类结果 -->
    <div v-if="result && !loading && !isDetection()" class="content fade-in">
      <div class="model-badge">
        <span class="model-type-tag classification">分类</span>
        <span class="model-name">{{ result.model_name || 'mobilenet_v2' }}</span>
      </div>

      <div class="cat-row">
        <div class="cat-badge" :style="{ background: m(result.category).bg, color: m(result.category).color }">
          <span>{{ m(result.category).icon }}</span>
          <strong>{{ m(result.category).label }}</strong>
        </div>
        <span class="confidence" :style="{ color: m(result.category).color }">
          {{ (result.confidence * 100).toFixed(1) }}%
        </span>
      </div>

      <div class="bar-track">
        <div class="bar-fill" :style="{ width: (result.confidence * 100) + '%', background: m(result.category).color }" />
      </div>

      <div class="tip" :style="{ borderLeftColor: m(result.category).binDot }">
        <div class="tip-main">
          <span class="tip-dot" :style="{ background: m(result.category).binDot }"></span>
          请投入 <strong>{{ m(result.category).bin }}</strong>
        </div>
        <p v-if="result.tip" class="tip-detail">{{ result.tip }}</p>
      </div>

      <div v-if="result.items?.length" class="items">
        <span class="items-label">同类常见物品</span>
        <div class="items-list">
          <span v-for="i in result.items" :key="i" class="tag">{{ i }}</span>
        </div>
      </div>
    </div>

    <!-- 检测结果 -->
    <div v-if="result && !loading && isDetection()" class="content fade-in">
      <div class="model-badge">
        <span class="model-type-tag detection">检测</span>
        <span class="model-name">{{ result.model_name || 'yolov8' }}</span>
        <span class="det-count">{{ result.count }} 个物体</span>
      </div>

      <div class="det-list">
        <div
          v-for="(det, idx) in result.detections"
          :key="idx"
          class="det-item"
        >
          <div class="det-head">
            <div class="cat-badge sm" :style="{ background: m(det.category).bg, color: m(det.category).color }">
              <span>{{ m(det.category).icon }}</span>
              <strong>{{ m(det.category).label }}</strong>
            </div>
            <span class="confidence sm" :style="{ color: m(det.category).color }">
              {{ (det.confidence * 100).toFixed(1) }}%
            </span>
          </div>
          <div class="det-bar">
            <div class="det-bar-fill" :style="{ width: (det.confidence * 100) + '%', background: m(det.category).color }" />
          </div>
          <div v-if="det.tip" class="det-tip">
            <span class="tip-dot" :style="{ background: m(det.category).binDot }"></span>
            请投入 <strong>{{ m(det.category).bin }}</strong>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.result {
  min-height: 300px;
  flex: 1;
  display: flex;
  flex-direction: column;
}

.state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .4rem;
  color: var(--text-muted);
}
.state-icon { font-size: 2.5rem; opacity: .3; }
.state-title { font-weight: 500; color: var(--text-secondary); }
.state-hint { font-size: .82rem; }

.spin {
  width: 32px; height: 32px;
  border: 3px solid var(--gray-200);
  border-top-color: var(--green-500);
  border-radius: 50%;
  animation: spin .7s linear infinite;
  margin-bottom: .25rem;
}

.content {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

/* ─── 模型徽章 ─── */
.model-badge {
  display: flex;
  align-items: center;
  gap: .5rem;
}
.model-type-tag {
  display: inline-block;
  padding: .15rem .55rem;
  border-radius: 6px;
  font-size: .72rem;
  font-weight: 600;
  letter-spacing: .03em;
}
.model-type-tag.classification {
  background: #dbeafe;
  color: #1e40af;
}
.model-type-tag.detection {
  background: #fce7f3;
  color: #9d174d;
}
.model-name {
  font-size: .75rem;
  color: var(--text-muted);
  font-family: monospace;
}
.det-count {
  margin-left: auto;
  font-size: .8rem;
  font-weight: 600;
  color: var(--text-secondary);
  background: var(--gray-100);
  padding: .15rem .6rem;
  border-radius: 100px;
}

/* ─── 分类结果 ─── */
.cat-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cat-badge {
  display: inline-flex;
  align-items: center;
  gap: .45rem;
  padding: .45rem 1rem;
  border-radius: 100px;
  font-size: .95rem;
}
.cat-badge.sm {
  padding: .3rem .75rem;
  font-size: .82rem;
}
.confidence {
  font-size: 1.3rem;
  font-weight: 700;
}
.confidence.sm {
  font-size: 1rem;
}

.bar-track {
  height: 6px;
  background: var(--gray-200);
  border-radius: 100px;
  overflow: hidden;
}
.bar-fill {
  height: 100%;
  border-radius: 100px;
  transition: width .7s cubic-bezier(.4,0,.2,1);
}

.tip {
  padding: .85rem 1rem;
  background: var(--gray-100);
  border-left: 3px solid var(--gray-400);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
}
.tip-main {
  font-size: .9rem;
  display: flex;
  align-items: center;
  gap: .35rem;
}
.tip-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.tip-detail {
  font-size: .82rem;
  color: var(--text-secondary);
  margin-top: .3rem;
  line-height: 1.5;
}

.items { margin-top: .25rem; }
.items-label {
  font-size: .78rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: .04em;
  display: block;
  margin-bottom: .5rem;
}
.items-list { display: flex; flex-wrap: wrap; gap: .35rem; }
.tag {
  padding: .25rem .6rem;
  border-radius: 100px;
  font-size: .78rem;
  background: var(--gray-100);
  color: var(--text-secondary);
}

/* ─── 检测结果列表 ─── */
.det-list {
  display: flex;
  flex-direction: column;
  gap: .65rem;
  max-height: 400px;
  overflow-y: auto;
}
.det-item {
  padding: .75rem .85rem;
  background: var(--gray-100);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  gap: .45rem;
}
.det-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.det-bar {
  height: 4px;
  background: var(--gray-200);
  border-radius: 100px;
  overflow: hidden;
}
.det-bar-fill {
  height: 100%;
  border-radius: 100px;
  transition: width .5s ease;
}
.det-tip {
  font-size: .78rem;
  color: var(--text-secondary);
  display: flex;
  align-items: center;
  gap: .3rem;
}
</style>
