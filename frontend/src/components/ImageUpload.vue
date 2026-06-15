<script setup>
import { ref } from 'vue'

const emit = defineEmits(['select'])

const isDragging = ref(false)
const fileInput = ref(null)

function onDragOver(e) { e.preventDefault(); isDragging.value = true }
function onDragLeave() { isDragging.value = false }
function onDrop(e) {
  e.preventDefault()
  isDragging.value = false
  const file = e.dataTransfer.files[0]
  if (file && file.type.startsWith('image/')) processFile(file)
}
function onFileChange(e) {
  const file = e.target.files[0]
  if (file) processFile(file)
  e.target.value = ''
}
function processFile(file) {
  const url = URL.createObjectURL(file)
  emit('select', { file, url, name: file.name })
}
</script>

<template>
  <div
    class="drop-zone"
    :class="{ dragging: isDragging }"
    @dragover="onDragOver"
    @dragleave="onDragLeave"
    @drop="onDrop"
    @click="fileInput?.click()"
  >
    <input
      ref="fileInput"
      type="file"
      accept="image/*"
      style="display:none"
      @change="onFileChange"
    />

    <div class="drop-icon">
      <svg width="44" height="44" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"/>
        <circle cx="8.5" cy="8.5" r="1.5"/>
        <polyline points="21 15 16 10 5 21"/>
      </svg>
    </div>
    <p class="drop-text">拖放图片到此处，或点击选择文件</p>
    <p class="drop-hint">支持 JPG / PNG 格式，最大 10MB</p>
  </div>
</template>

<style scoped>
.drop-zone {
  border: 2px dashed var(--border);
  border-radius: var(--radius);
  padding: 4rem 2rem;
  text-align: center;
  cursor: pointer;
  transition: all .2s;
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .6rem;
  min-height: 420px;
}
.drop-zone:hover {
  border-color: var(--green-400);
  background: var(--green-50);
}
.drop-zone.dragging {
  border-color: var(--green-500);
  background: var(--green-100);
}

.drop-icon {
  width: 72px; height: 72px;
  border-radius: 50%;
  background: var(--gray-100);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--gray-500);
  margin-bottom: .6rem;
  transition: all .2s;
}
.drop-zone:hover .drop-icon {
  background: var(--green-100);
  color: var(--green-600);
}

.drop-text {
  font-size: .95rem;
  color: var(--text-secondary);
}
.drop-hint {
  font-size: .82rem;
  color: var(--text-muted);
}
</style>
