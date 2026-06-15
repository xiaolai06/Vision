<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import CameraCapture from '../components/CameraCapture.vue'
import ImageUpload from '../components/ImageUpload.vue'
import ResultDisplay from '../components/ResultDisplay.vue'
import RealtimeCamera from '../components/RealtimeCamera.vue'
import { predictImage, checkHealth } from '../api/predict.js'
import { fetchModels, activateModel } from '../api/models.js'

const activeTab = ref('upload')
const previewUrl = ref('')
const result = ref(null)
const loading = ref(false)
const error = ref('')
const serverOnline = ref(null)
const mounted = ref(true)

// ─── 模型管理 ───
const models = ref([])
const activeModelId = ref('mobilenet_v2')

const activeModel = computed(() =>
  models.value.find(m => m.id === activeModelId.value)
)

onMounted(async () => {
  checkHealth().then(online => { if (mounted.value) serverOnline.value = online })
  try {
    const data = await fetchModels()
    if (mounted.value) {
      models.value = data.models
      activeModelId.value = data.active_model_id
    }
  } catch {
    // 模型 API 不可用时静默处理
  }
})

async function switchModel(modelId) {
  if (modelId === activeModelId.value) return
  activeModelId.value = modelId
  try {
    await activateModel(modelId)
    // 更新 models 列表的 is_active 状态
    models.value = models.value.map(m => ({
      ...m,
      is_active: m.id === modelId,
    }))
  } catch (e) {
    error.value = '模型切换失败: ' + e.message
  }
}

onUnmounted(() => {
  mounted.value = false
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})

function onFileSelect({ file, url }) {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = url
  result.value = null
  error.value = ''
  doPredict(file)
}

function onCameraCapture({ blob, url }) {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = url
  result.value = null
  error.value = ''
  doPredict(blob)
}

async function doPredict(imageBlob) {
  loading.value = true
  error.value = ''
  try {
    const data = await predictImage(imageBlob, activeModelId.value)
    if (!mounted.value) return
    result.value = data
  } catch (e) {
    if (!mounted.value) return
    error.value = e.message || '识别失败，请检查后端服务是否启动'
  } finally {
    if (mounted.value) loading.value = false
  }
}

function onRealtimeResult(data) {
  if (!mounted.value) return
  result.value = data
}

function clearPreview() {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  previewUrl.value = ''
  result.value = null
  error.value = ''
}

// ─── 检测框 SVG 叠加 ───
const catColors = {
  recyclable: '#3182ce',
  kitchen: '#38a169',
  hazardous: '#e53e3e',
  other: '#718096',
}
const isDetection = computed(() =>
  result.value && result.value.model_type === 'detection'
)
</script>

<template>
  <div class="page">
    <div class="workspace">

      <!-- 左栏：输入 -->
      <div class="card">
        <div class="card-head">
          <div class="tab-group">
            <button
              class="tab" :class="{ active: activeTab === 'upload' }"
              @click="activeTab = 'upload'"
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M21 15v4a2 2 0 01-2 2H5a2 2 0 01-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
              上传图片
            </button>
            <button
              class="tab" :class="{ active: activeTab === 'camera' }"
              @click="activeTab = 'camera'"
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
              摄像头
            </button>
            <button
              class="tab" :class="{ active: activeTab === 'realtime' }"
              @click="activeTab = 'realtime'"
            >
              <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><polygon points="23 7 16 12 23 17 23 7"/><rect x="1" y="5" width="15" height="14" rx="2" ry="2"/></svg>
              实时识别
            </button>
          </div>

          <div class="server-status" :class="serverOnline ? 'on' : 'off'">
            <span class="dot"></span>
            {{ serverOnline === null ? '检测中' : serverOnline ? '在线' : '离线' }}
          </div>
        </div>

        <!-- 模型选择器 -->
        <div class="model-bar" v-if="models.length > 1">
          <button
            v-for="mdl in models" :key="mdl.id"
            class="model-btn"
            :class="{ active: activeModelId === mdl.id }"
            @click="switchModel(mdl.id)"
          >
            <span class="model-icon">{{ mdl.type === 'detection' ? '🎯' : '🏷️' }}</span>
            {{ mdl.display_name }}
            <span v-if="mdl.is_mock" class="mock-tag">模拟</span>
          </button>
        </div>

        <div class="card-body input-body">
          <transition name="tab-fade" mode="out-in">
            <ImageUpload v-if="activeTab === 'upload'" key="upload" @select="onFileSelect" />
            <CameraCapture v-else-if="activeTab === 'camera'" key="camera" @capture="onCameraCapture" />
            <RealtimeCamera
              v-else-if="activeTab === 'realtime'"
              key="realtime"
              :model-id="activeModelId"
              @result="onRealtimeResult"
            />
          </transition>
        </div>

        <!-- 缩略预览 + 检测框叠加 -->
        <div v-if="previewUrl" class="preview-strip" :class="{ 'has-bbox': isDetection }">
          <div class="preview-wrap">
            <img :src="previewUrl" alt="preview" class="preview-img" />
            <!-- 检测框 SVG 叠加 -->
            <svg
              v-if="isDetection && result.detections"
              class="bbox-svg"
              :viewBox="`0 0 ${result.image_width || 224} ${result.image_height || 224}`"
              preserveAspectRatio="none"
            >
              <g v-for="(det, i) in result.detections" :key="i">
                <rect
                  :x="det.bbox[0]" :y="det.bbox[1]"
                  :width="det.bbox[2] - det.bbox[0]"
                  :height="det.bbox[3] - det.bbox[1]"
                  :stroke="catColors[det.category] || '#718096'"
                  fill="none" stroke-width="3" rx="2"
                />
                <text
                  :x="det.bbox[0]" :y="det.bbox[1] - 5"
                  :fill="catColors[det.category] || '#718096'"
                  font-size="14" font-weight="600"
                >{{ det.label }} {{ (det.confidence * 100).toFixed(0) }}%</text>
              </g>
            </svg>
          </div>
          <button class="clear-btn" @click="clearPreview">清除</button>
        </div>
      </div>

      <!-- 右栏：结果 -->
      <div class="card">
        <div class="card-head">
          <span class="card-title">识别结果</span>
        </div>
        <div class="card-body">
          <ResultDisplay :result="result" :loading="loading" :error="error" />
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 2rem 3rem 3rem;
  height: calc(100vh - 57px);
  display: flex;
  align-items: center;
}

/* 两栏等高布局 */
.workspace {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1.75rem;
  width: 100%;
  align-items: stretch;
  max-height: 100%;
}

/* 通用卡片 */
.card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.card-head {
  padding: .85rem 1.25rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  align-items: center;
  justify-content: space-between;
  min-height: 56px;
}
.card-title {
  font-size: .9rem;
  font-weight: 600;
}
.card-body {
  padding: 1.5rem;
  flex: 1;
  display: flex;
  flex-direction: column;
}

/* ─── 模型选择器 ─── */
.model-bar {
  padding: .6rem 1.25rem;
  border-bottom: 1px solid var(--border);
  display: flex;
  gap: .4rem;
  background: var(--gray-50);
}
.model-btn {
  display: inline-flex;
  align-items: center;
  gap: .35rem;
  padding: .4rem .85rem;
  border-radius: 8px;
  font-size: .8rem;
  font-weight: 500;
  border: 1.5px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  transition: all .25s ease;
}
.model-btn:hover {
  border-color: var(--green-300);
  color: var(--green-700);
}
.model-btn.active {
  border-color: var(--green-500);
  background: var(--green-50);
  color: var(--green-700);
  box-shadow: 0 0 0 1px var(--green-200);
}
.model-icon { font-size: .9rem; }
.mock-tag {
  font-size: .65rem;
  padding: .05rem .35rem;
  border-radius: 4px;
  background: var(--gray-200);
  color: var(--text-muted);
}

/* Tab 切换 */
.tab-group {
  display: flex;
  gap: .3rem;
  background: var(--gray-100);
  border-radius: 10px;
  padding: 4px;
}
.tab {
  padding: .5rem 1.15rem;
  border-radius: 8px;
  font-size: .88rem;
  font-weight: 500;
  border: none;
  background: transparent;
  color: var(--text-muted);
  transition: all .25s cubic-bezier(.4,0,.2,1);
  display: flex;
  align-items: center;
  gap: .4rem;
  white-space: nowrap;
}
.tab:hover { color: var(--text-secondary); }
.tab.active {
  background: var(--bg-card);
  color: var(--green-700);
  box-shadow: 0 1px 4px rgba(0,0,0,.08);
}

/* 服务状态 */
.server-status {
  font-size: .75rem;
  display: flex;
  align-items: center;
  gap: .3rem;
  color: var(--text-muted);
}
.dot {
  width: 7px; height: 7px;
  border-radius: 50%;
  display: inline-block;
}
.server-status.on .dot { background: var(--green-500); box-shadow: 0 0 5px var(--green-400); }
.server-status.off .dot { background: var(--cat-hazard); }

/* 输入区 */
.input-body { justify-content: center; }

/* ─── 预览 + BBox 叠加 ─── */
.preview-strip {
  border-top: 1px solid var(--border);
  padding: .75rem 1.25rem;
  display: flex;
  align-items: center;
  gap: .75rem;
}
.preview-strip.has-bbox {
  padding: .75rem 1.25rem 1rem;
}
.preview-wrap {
  position: relative;
  flex-shrink: 0;
}
.preview-img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
  background: var(--gray-100);
  display: block;
}
.has-bbox .preview-img {
  width: 200px;
  height: 150px;
}
.bbox-svg {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  border-radius: 6px;
}
.clear-btn {
  font-size: .78rem;
  color: var(--text-muted);
  background: none;
  border: none;
  transition: color .2s;
  align-self: flex-start;
}
.clear-btn:hover { color: var(--cat-hazard); }

/* Tab 内容切换动画 */
.tab-fade-enter-active,
.tab-fade-leave-active {
  transition: opacity .2s ease, transform .2s ease;
}
.tab-fade-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.tab-fade-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}

/* 响应式 */
@media (max-width: 768px) {
  .workspace { grid-template-columns: 1fr; }
  .page { padding: 1.25rem 1rem 2rem; }
}
</style>
