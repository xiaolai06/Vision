<script setup>
import { ref, watch, nextTick } from 'vue'

const props = defineProps({
  imageUrl: { type: String, required: true },
  annotations: { type: Array, default: () => [] },
  imageWidth: { type: Number, default: 0 },
  imageHeight: { type: Number, default: 0 },
})

const emit = defineEmits(['add', 'update', 'delete', 'select'])

const canvasRef = ref(null)
const imgRef = ref(null)
const containerRef = ref(null)

// 绘制状态
const isDrawing = ref(false)
const startX = ref(0)
const startY = ref(0)
const selectedId = ref(null)

const catColors = {
  recyclable: '#3182ce',
  kitchen: '#38a169',
  hazardous: '#e53e3e',
  other: '#718096',
}

// 图片加载后重绘
function onImgLoad() {
  nextTick(() => drawAll())
}

// 获取缩放比例
function getScale() {
  const img = imgRef.value
  if (!img || !img.naturalWidth) return { scaleX: 1, scaleY: 1, displayW: 0, displayH: 0 }
  const displayW = img.clientWidth
  const displayH = img.clientHeight
  return {
    scaleX: (props.imageWidth || img.naturalWidth) / displayW,
    scaleY: (props.imageHeight || img.naturalHeight) / displayH,
    displayW,
    displayH,
  }
}

// 鼠标坐标 → 图片像素坐标
function toImageCoords(e) {
  const canvas = canvasRef.value
  if (!canvas) return { x: 0, y: 0 }
  const rect = canvas.getBoundingClientRect()
  const { scaleX, scaleY } = getScale()
  return {
    x: (e.clientX - rect.left) * scaleX,
    y: (e.clientY - rect.top) * scaleY,
  }
}

// 图片像素坐标 → 显示坐标
function toDisplayCoords(bbox) {
  const { scaleX, scaleY } = getScale()
  return {
    x: bbox.x1 / scaleX,
    y: bbox.y1 / scaleY,
    w: (bbox.x2 - bbox.x1) / scaleX,
    h: (bbox.y2 - bbox.y1) / scaleY,
  }
}

// 绘制所有标注 + 当前正在画的矩形
function drawAll(drawingRect = null) {
  const canvas = canvasRef.value
  const img = imgRef.value
  if (!canvas || !img) return

  const dpr = window.devicePixelRatio || 1
  const displayW = img.clientWidth
  const displayH = img.clientHeight

  canvas.width = displayW * dpr
  canvas.height = displayH * dpr
  canvas.style.width = displayW + 'px'
  canvas.style.height = displayH + 'px'

  const ctx = canvas.getContext('2d')
  ctx.scale(dpr, dpr)
  ctx.clearRect(0, 0, displayW, displayH)

  // 绘制已有标注
  for (const ann of props.annotations) {
    const { x, y, w, h } = toDisplayCoords(ann)
    const color = catColors[ann.category] || '#718096'
    const isSelected = ann.id === selectedId.value

    ctx.strokeStyle = color
    ctx.lineWidth = isSelected ? 3 : 2
    ctx.strokeRect(x, y, w, h)

    if (isSelected) {
      ctx.fillStyle = color + '18'
      ctx.fillRect(x, y, w, h)
    }

    // 标签背景
    const label = `${ann.label} ${(ann.id ? '' : '(新)')}`
    ctx.font = '12px system-ui, sans-serif'
    const textW = ctx.measureText(label).width + 8
    ctx.fillStyle = color
    ctx.fillRect(x, y - 18, textW, 18)
    ctx.fillStyle = '#fff'
    ctx.fillText(label, x + 4, y - 5)
  }

  // 绘制正在画的矩形
  if (drawingRect) {
    ctx.strokeStyle = '#f6e05e'
    ctx.lineWidth = 2
    ctx.setLineDash([6, 3])
    ctx.strokeRect(drawingRect.x, drawingRect.y, drawingRect.w, drawingRect.h)
    ctx.setLineDash([])
  }
}

// 鼠标事件
function onMouseDown(e) {
  if (e.button !== 0) return
  const pos = toImageCoords(e)
  startX.value = pos.x
  startY.value = pos.y
  isDrawing.value = true
  selectedId.value = null
}

function onMouseMove(e) {
  if (!isDrawing.value) return
  const pos = toImageCoords(e)
  const { scaleX, scaleY } = getScale()

  const dx = pos.x - startX.value
  const dy = pos.y - startY.value
  const rect = {
    x: Math.min(startX.value, pos.x) / scaleX,
    y: Math.min(startY.value, pos.y) / scaleY,
    w: Math.abs(dx) / scaleX,
    h: Math.abs(dy) / scaleY,
  }
  drawAll(rect)
}

function onMouseUp(e) {
  if (!isDrawing.value) return
  isDrawing.value = false

  const pos = toImageCoords(e)
  const x1 = Math.min(startX.value, pos.x)
  const y1 = Math.min(startY.value, pos.y)
  const x2 = Math.max(startX.value, pos.x)
  const y2 = Math.max(startY.value, pos.y)

  // 最小尺寸检查 (10x10 像素)
  if (x2 - x1 < 10 || y2 - y1 < 10) {
    drawAll()
    return
  }

  emit('add', { x1: Math.round(x1), y1: Math.round(y1), x2: Math.round(x2), y2: Math.round(y2) })
  drawAll()
}

// 点击选中已有标注
function onCanvasClick(e) {
  if (isDrawing.value) return
  const pos = toImageCoords(e)

  // 从后往前检查（后画的在上面）
  for (let i = props.annotations.length - 1; i >= 0; i--) {
    const ann = props.annotations[i]
    if (pos.x >= ann.x1 && pos.x <= ann.x2 && pos.y >= ann.y1 && pos.y <= ann.y2) {
      selectedId.value = ann.id
      emit('select', ann.id)
      drawAll()
      return
    }
  }
  selectedId.value = null
  drawAll()
}

// 窗口大小变化时重绘
function onResize() {
  nextTick(() => drawAll())
}

// 监听标注变化重绘
watch(() => props.annotations, () => nextTick(() => drawAll()), { deep: true })
watch(selectedId, () => nextTick(() => drawAll()))

// 暴露方法
function refresh() {
  nextTick(() => drawAll())
}

defineExpose({ refresh })

// 生命周期
if (typeof window !== 'undefined') {
  window.addEventListener('resize', onResize)
}
</script>

<template>
  <div class="bbox-container" ref="containerRef">
    <img
      ref="imgRef"
      :src="imageUrl"
      class="bbox-image"
      @load="onImgLoad"
      draggable="false"
    />
    <canvas
      ref="canvasRef"
      class="bbox-canvas"
      @mousedown="onMouseDown"
      @mousemove="onMouseMove"
      @mouseup="onMouseUp"
      @click="onCanvasClick"
    />
  </div>
</template>

<style scoped>
.bbox-container {
  position: relative;
  display: inline-block;
  cursor: crosshair;
  max-width: 100%;
}
.bbox-image {
  display: block;
  max-width: 100%;
  max-height: 65vh;
  border-radius: var(--radius-sm);
}
.bbox-canvas {
  position: absolute;
  top: 0;
  left: 0;
  pointer-events: auto;
}
</style>
