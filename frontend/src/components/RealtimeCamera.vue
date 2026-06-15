<script setup>
import { ref, onBeforeUnmount, watch } from 'vue'

const props = defineProps({
  modelId: { type: String, default: null },
})
const emit = defineEmits(['result', 'error'])

const videoRef = ref(null)
const canvasRef = ref(null)
const isActive = ref(false)
const isLoading = ref(false)
const wsConnected = ref(false)
const currentResult = ref(null)
const errorMsg = ref('')
const intervalMs = ref(500)
const autoSave = ref(false)
const dedupeSeconds = ref(5)
const savedCount = ref(0)
const fps = ref(0)

let stream = null
let ws = null
let captureTimer = null
let pendingFrame = false
let frameCount = 0
let fpsTimer = null

const categoryMeta = {
  recyclable: { label: '可回收物', color: '#3182ce', bg: '#ebf8ff', icon: '♻️' },
  kitchen:    { label: '厨余垃圾', color: '#38a169', bg: '#f0fff4', icon: '🥬' },
  hazardous:  { label: '有害垃圾', color: '#e53e3e', bg: '#fff5f5', icon: '⚠️' },
  other:      { label: '其他垃圾', color: '#718096', bg: '#f7fafc', icon: '🗑️' },
}

function connectWs() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const wsUrl = `${protocol}//${window.location.host}/api/ws/predict`
  ws = new WebSocket(wsUrl)

  ws.onopen = () => { wsConnected.value = true }
  ws.onclose = () => {
    wsConnected.value = false
    if (isActive.value) {
      setTimeout(() => { if (isActive.value) connectWs() }, 2000)
    }
  }
  ws.onerror = () => { errorMsg.value = 'WebSocket 连接失败，请检查后端服务' }
  ws.onmessage = (event) => {
    pendingFrame = false
    try {
      const data = JSON.parse(event.data)
      if (data.error) {
        errorMsg.value = data.error
        return
      }
      currentResult.value = data
      emit('result', data)
      frameCount++
      // 统计实际保存数量
      if (data.id !== null && data.id !== undefined) {
        savedCount.value++
      }
    } catch (e) {
      console.error('WS parse error', e)
    }
  }
}

async function start() {
  errorMsg.value = ''
  isLoading.value = true
  currentResult.value = null
  savedCount.value = 0
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 640 }, height: { ideal: 480 } }
    })
    if (!videoRef.value) return
    videoRef.value.srcObject = stream
    isActive.value = true
    connectWs()
    startCaptureLoop()
    startFpsCounter()
  } catch (e) {
    errorMsg.value = e.name === 'NotAllowedError'
      ? '摄像头权限被拒绝，请在浏览器中允许访问'
      : '无法访问摄像头'
    emit('error', errorMsg.value)
  } finally {
    isLoading.value = false
  }
}

function startCaptureLoop() {
  if (captureTimer) clearInterval(captureTimer)
  captureTimer = setInterval(() => {
    if (pendingFrame || !wsConnected.value) return
    captureAndSend()
  }, intervalMs.value)
}

function captureAndSend() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas || video.videoWidth === 0) return

  canvas.width = 224
  canvas.height = 224
  const ctx = canvas.getContext('2d')
  ctx.drawImage(video, 0, 0, 224, 224)

  canvas.toBlob((blob) => {
    if (!blob || !ws || ws.readyState !== WebSocket.OPEN) return
    const reader = new FileReader()
    reader.onload = () => {
      pendingFrame = true
      const msg = {
        image: reader.result,
        save: autoSave.value,
        dedupe_seconds: dedupeSeconds.value,
      }
      if (props.modelId) msg.model_id = props.modelId
      ws.send(JSON.stringify(msg))
    }
    reader.readAsDataURL(blob)
  }, 'image/jpeg', 0.7)
}

function startFpsCounter() {
  fpsTimer = setInterval(() => {
    fps.value = frameCount
    frameCount = 0
  }, 1000)
}

function stop() {
  if (captureTimer) { clearInterval(captureTimer); captureTimer = null }
  if (fpsTimer) { clearInterval(fpsTimer); fpsTimer = null }
  if (ws) { ws.close(); ws = null }
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null }
  if (videoRef.value) videoRef.value.srcObject = null
  isActive.value = false
  wsConnected.value = false
  currentResult.value = null
  pendingFrame = false
}

watch(intervalMs, () => {
  if (isActive.value) startCaptureLoop()
})

onBeforeUnmount(stop)
</script>

<template>
  <div class="realtime-camera">
    <!-- 取景框 -->
    <div class="viewport">
      <video v-show="isActive" ref="videoRef" autoplay playsinline muted />
      <canvas ref="canvasRef" style="display:none" />

      <!-- 结果叠加层 -->
      <div v-if="currentResult && isActive" class="overlay"
           :style="{ borderLeftColor: categoryMeta[currentResult.category]?.color }">
        <div class="overlay-badge"
             :style="{ background: categoryMeta[currentResult.category]?.bg,
                       color: categoryMeta[currentResult.category]?.color }">
          <span class="overlay-icon">{{ categoryMeta[currentResult.category]?.icon }}</span>
          <strong>{{ categoryMeta[currentResult.category]?.label }}</strong>
        </div>
        <span class="overlay-conf"
              :style="{ color: categoryMeta[currentResult.category]?.color }">
          {{ (currentResult.confidence * 100).toFixed(1) }}%
        </span>
      </div>

      <!-- WebSocket 连接状态 -->
      <div v-if="isActive" class="ws-indicator" :class="{ connected: wsConnected }">
        <span class="ws-dot"></span>
        {{ wsConnected ? '实时连接' : '重连中...' }}
      </div>

      <!-- FPS -->
      <div v-if="isActive" class="fps-counter">{{ fps }} FPS</div>

      <!-- 已保存计数 -->
      <div v-if="isActive && autoSave" class="save-counter">
        已保存 {{ savedCount }} 条
      </div>

      <!-- 占位状态 -->
      <div v-if="!isActive && !errorMsg" class="placeholder">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
          <polygon points="23 7 16 12 23 17 23 7"/>
          <rect x="1" y="5" width="15" height="14" rx="2" ry="2"/>
        </svg>
        <p>点击「开始实时识别」启动摄像头</p>
        <p class="placeholder-hint">系统将连续截取画面帧并通过 WebSocket 实时推理</p>
      </div>

      <div v-if="errorMsg" class="placeholder err">
        <p>{{ errorMsg }}</p>
      </div>

      <div v-if="isLoading" class="placeholder">
        <div class="spin"></div>
        <p>启动中...</p>
      </div>
    </div>

    <!-- 控制栏 -->
    <div class="controls">
      <template v-if="!isActive">
        <button class="btn primary" :disabled="isLoading" @click="start">开始实时识别</button>
      </template>
      <template v-else>
        <button class="btn danger" @click="stop">停止</button>
        <div class="interval-control">
          <label>间隔 {{ intervalMs }}ms</label>
          <input type="range" v-model.number="intervalMs" min="200" max="2000" step="100" />
        </div>
        <label class="save-toggle">
          <input type="checkbox" v-model="autoSave" />
          <span>自动保存</span>
        </label>
        <div v-if="autoSave" class="dedupe-control">
          <label>去重 {{ dedupeSeconds }}s</label>
          <input type="range" v-model.number="dedupeSeconds" min="1" max="30" step="1" />
        </div>
      </template>
    </div>
  </div>
</template>

<style scoped>
.realtime-camera {
  display: flex;
  flex-direction: column;
  gap: .75rem;
  flex: 1;
}

.viewport {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #111;
  border-radius: var(--radius-sm);
  overflow: hidden;
}
.viewport video {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

/* 结果叠加 */
.overlay {
  position: absolute;
  bottom: .75rem;
  left: .75rem;
  display: flex;
  align-items: center;
  gap: .6rem;
  background: rgba(0, 0, 0, .65);
  backdrop-filter: blur(6px);
  padding: .5rem .85rem;
  border-radius: 8px;
  border-left: 3px solid #999;
}
.overlay-badge {
  display: flex;
  align-items: center;
  gap: .3rem;
  padding: .15rem .5rem;
  border-radius: 100px;
  font-size: .82rem;
}
.overlay-icon { font-size: 1rem; }
.overlay-conf {
  font-size: .95rem;
  font-weight: 700;
}

/* 连接状态 */
.ws-indicator {
  position: absolute;
  top: .5rem;
  right: .5rem;
  display: flex;
  align-items: center;
  gap: .3rem;
  font-size: .7rem;
  color: #aaa;
  background: rgba(0, 0, 0, .5);
  padding: .2rem .5rem;
  border-radius: 100px;
}
.ws-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
  background: #e53e3e;
}
.ws-indicator.connected .ws-dot {
  background: #48bb78;
  box-shadow: 0 0 4px #48bb78;
}

/* FPS */
.fps-counter {
  position: absolute;
  top: .5rem;
  left: .5rem;
  font-size: .7rem;
  font-weight: 600;
  color: #48bb78;
  background: rgba(0, 0, 0, .5);
  padding: .15rem .45rem;
  border-radius: 4px;
}

/* 已保存计数 */
.save-counter {
  position: absolute;
  top: .5rem;
  left: 5rem;
  font-size: .7rem;
  font-weight: 600;
  color: #f6e05e;
  background: rgba(0, 0, 0, .5);
  padding: .15rem .45rem;
  border-radius: 4px;
}

/* 占位 */
.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  color: #666;
  font-size: .85rem;
}
.placeholder-hint {
  font-size: .78rem;
  color: #555;
}
.placeholder.err p { color: #e53e3e; }

.spin {
  width: 28px; height: 28px;
  border: 2.5px solid #333;
  border-top-color: var(--green-400);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

/* 控制栏 */
.controls {
  display: flex;
  gap: .75rem;
  align-items: center;
  flex-wrap: wrap;
}
.btn {
  padding: .65rem 1.2rem;
  border-radius: var(--radius-sm);
  font-size: .88rem;
  font-weight: 500;
  border: none;
  transition: all .2s;
}
.btn:disabled { opacity: .5; cursor: not-allowed; }
.btn.primary {
  background: var(--green-600);
  color: #fff;
  flex: 1;
  text-align: center;
}
.btn.primary:hover:not(:disabled) { background: var(--green-700); }
.btn.danger {
  background: var(--cat-hazard);
  color: #fff;
}
.btn.danger:hover { background: #c53030; }

.interval-control,
.dedupe-control {
  display: flex;
  align-items: center;
  gap: .4rem;
  flex: 1;
  min-width: 100px;
}
.interval-control label,
.dedupe-control label {
  font-size: .78rem;
  color: var(--text-muted);
  white-space: nowrap;
}
.interval-control input[type="range"],
.dedupe-control input[type="range"] {
  flex: 1;
  min-width: 60px;
  accent-color: var(--green-600);
}

.save-toggle {
  display: flex;
  align-items: center;
  gap: .3rem;
  font-size: .82rem;
  color: var(--text-secondary);
  cursor: pointer;
  white-space: nowrap;
}
.save-toggle input { accent-color: var(--green-600); }
</style>
