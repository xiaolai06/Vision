<script setup>
import { ref, onBeforeUnmount } from 'vue'

const emit = defineEmits(['capture'])

const videoRef = ref(null)
const canvasRef = ref(null)
const isActive = ref(false)
const isLoading = ref(false)
const error = ref('')
let stream = null

async function startCamera() {
  error.value = ''
  isLoading.value = true
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } }
    })
    videoRef.value.srcObject = stream
    isActive.value = true
  } catch (e) {
    error.value = e.name === 'NotAllowedError'
      ? '摄像头权限被拒绝，请在浏览器中允许访问'
      : '无法访问摄像头'
  } finally {
    isLoading.value = false
  }
}

function stopCamera() {
  if (stream) { stream.getTracks().forEach(t => t.stop()); stream = null }
  if (videoRef.value) videoRef.value.srcObject = null
  isActive.value = false
}

function capture() {
  const video = videoRef.value
  const canvas = canvasRef.value
  if (!video || !canvas) return
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  canvas.getContext('2d').drawImage(video, 0, 0)
  canvas.toBlob(blob => {
    if (blob) emit('capture', { blob, url: URL.createObjectURL(blob) })
  }, 'image/jpeg', 0.92)
}

onBeforeUnmount(stopCamera)
</script>

<template>
  <div class="camera">
    <!-- 取景框 -->
    <div class="viewport">
      <video v-show="isActive" ref="videoRef" autoplay playsinline muted />
      <canvas ref="canvasRef" style="display:none" />

      <div v-if="!isActive && !error" class="placeholder">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round"><path d="M23 19a2 2 0 01-2 2H3a2 2 0 01-2-2V8a2 2 0 012-2h4l2-3h6l2 3h4a2 2 0 012 2z"/><circle cx="12" cy="13" r="4"/></svg>
        <p>点击「开启摄像头」开始</p>
      </div>

      <div v-if="error" class="placeholder err">
        <p>{{ error }}</p>
      </div>

      <div v-if="isLoading" class="placeholder">
        <div class="spin"></div>
        <p>启动中...</p>
      </div>
    </div>

    <!-- 操作栏 -->
    <div class="controls">
      <template v-if="!isActive">
        <button class="btn primary" :disabled="isLoading" @click="startCamera">开启摄像头</button>
      </template>
      <template v-else>
        <button class="btn primary capture-btn" @click="capture">拍照识别</button>
        <button class="btn ghost" @click="stopCamera">关闭</button>
      </template>
    </div>
  </div>
</template>

<style scoped>
.camera {
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

.placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .6rem;
  color: #666;
  font-size: .85rem;
}
.placeholder.err p { color: #e53e3e; }

.spin {
  width: 28px; height: 28px;
  border: 2.5px solid #333;
  border-top-color: var(--green-400);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

.controls {
  display: flex;
  gap: .5rem;
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
.btn.capture-btn { flex: 2; }
.btn.ghost {
  background: var(--gray-100);
  color: var(--text-secondary);
}
.btn.ghost:hover { background: var(--gray-200); }
</style>
