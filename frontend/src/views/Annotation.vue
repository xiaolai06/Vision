<script setup>
import { ref, computed, onMounted, onUnmounted, nextTick } from 'vue'
import BboxCanvas from '../components/BboxCanvas.vue'
import { fetchRecords } from '../api/records.js'
import { fetchAnnotations, saveAnnotations, deleteAnnotation } from '../api/annotations.js'

const mounted = ref(true)
const loading = ref(false)
const saving = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

// 图片列表
const records = ref([])
const currentIndex = ref(0)
const currentRecord = ref(null)
const annotations = ref([])
const showAllRecords = ref(false)  // false = 只显示检测模型记录

// 当前绘制状态
const selectedCategory = ref('recyclable')
const pendingBox = ref(null)  // 新画的矩形，等待分配类别

// 类别选项
const categoryOptions = [
  { value: 'recyclable', label: '可回收物', color: '#3182ce', bg: '#ebf8ff' },
  { value: 'kitchen', label: '厨余垃圾', color: '#38a169', bg: '#f0fff4' },
  { value: 'hazardous', label: '有害垃圾', color: '#e53e3e', bg: '#fff5f5' },
  { value: 'other', label: '其他垃圾', color: '#718096', bg: '#f7fafc' },
]

const categoryMeta = Object.fromEntries(categoryOptions.map(o => [o.value, o]))

const imageUrl = computed(() => {
  if (!currentRecord.value) return ''
  const path = currentRecord.value.image_path
  if (!path) return ''
  const filename = path.split('/').pop().split('\\').pop()
  return `/api/images/${filename}`
})

const progress = computed(() => {
  if (records.value.length === 0) return '0 / 0'
  return `${currentIndex.value + 1} / ${records.value.length}`
})

const bboxRef = ref(null)

onUnmounted(() => { mounted.value = false })

onMounted(async () => {
  await loadImageList()
})

async function loadImageList() {
  loading.value = true
  errorMsg.value = ''
  try {
    const params = { limit: 200 }
    if (!showAllRecords.value) {
      params.model_type = 'detection'
    }
    const data = await fetchRecords(params)
    if (!mounted.value) return
    records.value = data.records
    currentIndex.value = 0
    if (records.value.length > 0) {
      await loadCurrentImage()
    } else {
      currentRecord.value = null
      errorMsg.value = showAllRecords.value
        ? '暂无可标注的图片'
        : '暂无检测模型的记录。请先在「识别」页面使用检测模型进行识别。'
    }
  } catch (e) {
    errorMsg.value = '加载图片列表失败: ' + e.message
  } finally {
    if (mounted.value) loading.value = false
  }
}

async function loadCurrentImage() {
  if (currentIndex.value < 0 || currentIndex.value >= records.value.length) return
  const rec = records.value[currentIndex.value]
  currentRecord.value = rec
  pendingBox.value = null

  try {
    const data = await fetchAnnotations(rec.id)
    annotations.value = data.annotations || []
  } catch {
    annotations.value = []
  }

  await nextTick()
  bboxRef.value?.refresh()
}

function goPrev() {
  if (currentIndex.value > 0) {
    currentIndex.value--
    loadCurrentImage()
  }
}

function goNext() {
  if (currentIndex.value < records.value.length - 1) {
    currentIndex.value++
    loadCurrentImage()
  }
}

// 画完一个矩形后触发
function onBoxAdded(box) {
  // 用当前选中的类别直接添加
  const cat = categoryMeta[selectedCategory.value] || categoryMeta.other
  const ann = {
    id: null,  // 临时的
    category: selectedCategory.value,
    label: cat.label,
    x1: box.x1,
    y1: box.y1,
    x2: box.x2,
    y2: box.y2,
    _temp: true,  // 标记为临时，未保存
  }
  annotations.value.push(ann)
  nextTick(() => bboxRef.value?.refresh())
}

// 选中某个标注
function onAnnotationSelect(id) {
  // 高亮效果由 BboxCanvas 内部处理
}

// 更改选中标注的类别
function changeSelectedCategory(cat) {
  const selected = annotations.value.find(a => a.id === null && a._temp)
  // 简单处理：更改最后一个临时标注的类别
  const tempAnns = annotations.value.filter(a => a._temp)
  if (tempAnns.length > 0) {
    const last = tempAnns[tempAnns.length - 1]
    last.category = cat
    last.label = categoryMeta[cat]?.label || cat
    nextTick(() => bboxRef.value?.refresh())
  }
}

// 删除标注
async function removeAnnotation(ann) {
  if (ann._temp) {
    // 未保存的，直接从数组中移除
    const idx = annotations.value.indexOf(ann)
    if (idx >= 0) annotations.value.splice(idx, 1)
    nextTick(() => bboxRef.value?.refresh())
    return
  }
  // 已保存的，调用 API
  try {
    await deleteAnnotation(ann.id)
    annotations.value = annotations.value.filter(a => a.id !== ann.id)
    nextTick(() => bboxRef.value?.refresh())
    showSuccess('标注已删除')
  } catch (e) {
    errorMsg.value = '删除失败: ' + e.message
  }
}

// 保存所有标注
async function handleSave() {
  if (!currentRecord.value) return
  saving.value = true
  errorMsg.value = ''

  try {
    const newAnns = annotations.value.filter(a => a._temp)
    if (newAnns.length > 0) {
      const toSave = newAnns.map(a => ({
        category: a.category,
        label: a.label,
        x1: a.x1,
        y1: a.y1,
        x2: a.x2,
        y2: a.y2,
      }))
      const result = await saveAnnotations(currentRecord.value.id, toSave)
      // 将临时标注替换为服务器返回的标注
      const ids = result.ids || []
      let idIdx = 0
      for (let i = annotations.value.length - 1; i >= 0; i--) {
        if (annotations.value[i]._temp && idIdx < ids.length) {
          annotations.value[i].id = ids[idIdx]
          annotations.value[i]._temp = false
          idIdx++
        }
      }
    }
    showSuccess(`已保存 ${newAnns.length} 条标注`)
    nextTick(() => bboxRef.value?.refresh())
  } catch (e) {
    errorMsg.value = '保存失败: ' + e.message
  } finally {
    saving.value = false
  }
}

function showSuccess(msg) {
  successMsg.value = msg
  setTimeout(() => { successMsg.value = '' }, 2500)
}

function toggleAllRecords() {
  showAllRecords.value = !showAllRecords.value
  loadImageList()
}

// 键盘快捷键
function onKeyDown(e) {
  if (e.key === 'ArrowLeft') goPrev()
  else if (e.key === 'ArrowRight') goNext()
  else if (e.key === 's' && (e.ctrlKey || e.metaKey)) {
    e.preventDefault()
    handleSave()
  }
  else if (e.key === 'Delete' || e.key === 'Backspace') {
    // 删除最后一个临时标注
    const tempAnns = annotations.value.filter(a => a._temp)
    if (tempAnns.length > 0) {
      removeAnnotation(tempAnns[tempAnns.length - 1])
    }
  }
  // 数字键 1-4 快速选择类别
  else if (e.key >= '1' && e.key <= '4') {
    const idx = parseInt(e.key) - 1
    if (categoryOptions[idx]) {
      selectedCategory.value = categoryOptions[idx].value
      changeSelectedCategory(categoryOptions[idx].value)
    }
  }
}

onMounted(() => {
  window.addEventListener('keydown', onKeyDown)
})
onUnmounted(() => {
  window.removeEventListener('keydown', onKeyDown)
})
</script>

<template>
  <div class="page">
    <div class="annotation-layout">

      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="toolbar-left">
          <h2 class="page-title">数据标注</h2>
          <div class="nav-group">
            <button class="btn-nav" :disabled="currentIndex <= 0" @click="goPrev">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="15 18 9 12 15 6"/></svg>
            </button>
            <span class="progress">{{ progress }}</span>
            <button class="btn-nav" :disabled="currentIndex >= records.length - 1" @click="goNext">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
          <label class="toggle-all">
            <input type="checkbox" v-model="showAllRecords" @change="toggleAllRecords" />
            <span>显示全部记录</span>
          </label>
        </div>
        <div class="toolbar-right">
          <button class="btn-save" :disabled="saving || annotations.filter(a => a._temp).length === 0" @click="handleSave">
            {{ saving ? '保存中...' : '保存标注' }}
          </button>
        </div>
      </div>

      <!-- 提示消息 -->
      <div v-if="errorMsg" class="msg error">{{ errorMsg }}</div>
      <div v-if="successMsg" class="msg success">{{ successMsg }}</div>

      <!-- 主体区域 -->
      <div class="main-area" v-if="currentRecord">
        <!-- 图片 + Canvas -->
        <div class="canvas-panel">
          <BboxCanvas
            ref="bboxRef"
            :image-url="imageUrl"
            :annotations="annotations"
            :image-width="currentRecord.image_width || 0"
            :image-height="currentRecord.image_height || 0"
            @add="onBoxAdded"
            @select="onAnnotationSelect"
          />
          <div v-if="!imageUrl" class="no-image">
            <p>无图片</p>
          </div>
        </div>

        <!-- 右侧面板 -->
        <div class="side-panel">
          <!-- 类别选择 -->
          <div class="panel-section">
            <h3 class="section-title">选择类别</h3>
            <p class="section-hint">在图片上拖拽绘制矩形 (快捷键 1-4)</p>
            <div class="cat-grid">
              <button
                v-for="cat in categoryOptions"
                :key="cat.value"
                class="cat-btn"
                :class="{ active: selectedCategory === cat.value }"
                :style="{ borderColor: selectedCategory === cat.value ? cat.color : '', background: selectedCategory === cat.value ? cat.bg : '' }"
                @click="selectedCategory = cat.value; changeSelectedCategory(cat.value)"
              >
                <span class="cat-dot" :style="{ background: cat.color }"></span>
                {{ cat.label }}
              </button>
            </div>
          </div>

          <!-- 标注列表 -->
          <div class="panel-section flex-1">
            <h3 class="section-title">
              标注列表
              <span class="count-badge">{{ annotations.length }}</span>
            </h3>
            <div class="ann-list">
              <div
                v-for="(ann, idx) in annotations"
                :key="idx"
                class="ann-item"
              >
                <div class="ann-info">
                  <span class="ann-cat" :style="{ background: categoryMeta[ann.category]?.bg, color: categoryMeta[ann.category]?.color }">
                    {{ categoryMeta[ann.category]?.label || ann.category }}
                  </span>
                  <span class="ann-dims">
                    {{ Math.round(ann.x2 - ann.x1) }}x{{ Math.round(ann.y2 - ann.y1) }}
                  </span>
                  <span v-if="!ann._temp" class="ann-source" :class="ann.source || 'manual'">
                    {{ (ann.source === 'predicted') ? '预测' : '人工' }}
                  </span>
                </div>
                <div class="ann-actions">
                  <button class="ann-del" @click="removeAnnotation(ann)" title="删除">
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                  </button>
                </div>
              </div>
              <div v-if="annotations.length === 0" class="ann-empty">
                在图片上绘制矩形开始标注
              </div>
            </div>
          </div>

          <!-- 快捷键提示 -->
          <div class="panel-section shortcuts">
            <div class="shortcut"><kbd>&larr;</kbd><kbd>&rarr;</kbd> 切换图片</div>
            <div class="shortcut"><kbd>1</kbd>-<kbd>4</kbd> 选择类别</div>
            <div class="shortcut"><kbd>Ctrl+S</kbd> 保存</div>
            <div class="shortcut"><kbd>Del</kbd> 撤销上一个</div>
          </div>
        </div>
      </div>

      <!-- 空状态 -->
      <div v-else-if="!loading" class="empty-state">
        <div class="empty-icon">📋</div>
        <p>暂无可标注的图片</p>
        <p class="empty-hint">先在「识别」页面上传图片，记录会保存在这里供标注</p>
      </div>

      <!-- 加载状态 -->
      <div v-if="loading" class="loading-state">
        <div class="spin"></div>
        <p>加载图片列表...</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 1.25rem 2rem 2rem;
  height: calc(100vh - 57px);
  display: flex;
  flex-direction: column;
}

.annotation-layout {
  display: flex;
  flex-direction: column;
  gap: .75rem;
  flex: 1;
  min-height: 0;
}

/* ─── 工具栏 ─── */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.toolbar-left {
  display: flex;
  align-items: center;
  gap: 1.25rem;
}
.page-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin: 0;
}
.nav-group {
  display: flex;
  align-items: center;
  gap: .3rem;
}
.btn-nav {
  width: 32px;
  height: 32px;
  border-radius: 8px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--text-secondary);
  transition: all .2s;
}
.btn-nav:hover:not(:disabled) { background: var(--gray-100); }
.btn-nav:disabled { opacity: .3; cursor: not-allowed; }
.progress {
  font-size: .85rem;
  font-weight: 600;
  color: var(--text-secondary);
  min-width: 60px;
  text-align: center;
}
.toggle-all {
  display: flex;
  align-items: center;
  gap: .3rem;
  font-size: .78rem;
  color: var(--text-muted);
  cursor: pointer;
  margin-left: .75rem;
  padding-left: .75rem;
  border-left: 1px solid var(--border);
}
.toggle-all input { accent-color: var(--green-600); }
.btn-save {
  padding: .55rem 1.25rem;
  border-radius: 8px;
  font-size: .88rem;
  font-weight: 600;
  border: none;
  background: var(--green-600);
  color: #fff;
  cursor: pointer;
  transition: all .2s;
}
.btn-save:hover:not(:disabled) { background: var(--green-700); }
.btn-save:disabled { opacity: .5; cursor: not-allowed; }

/* 消息 */
.msg {
  padding: .5rem .85rem;
  border-radius: 8px;
  font-size: .84rem;
  font-weight: 500;
}
.msg.error { background: #fff5f5; color: #c53030; }
.msg.success { background: #f0fff4; color: #276749; }

/* ─── 主体 ─── */
.main-area {
  display: grid;
  grid-template-columns: 1fr 280px;
  gap: 1rem;
  flex: 1;
  min-height: 0;
}

.canvas-panel {
  background: #1a1a2e;
  border-radius: var(--radius);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  min-height: 300px;
}
.no-image { color: #666; }

/* ─── 侧边面板 ─── */
.side-panel {
  display: flex;
  flex-direction: column;
  gap: .75rem;
  overflow-y: auto;
}
.panel-section {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: .85rem 1rem;
}
.panel-section.flex-1 {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.section-title {
  font-size: .82rem;
  font-weight: 600;
  margin: 0 0 .4rem;
  display: flex;
  align-items: center;
  gap: .4rem;
}
.section-hint {
  font-size: .72rem;
  color: var(--text-muted);
  margin: 0 0 .6rem;
}
.count-badge {
  font-size: .7rem;
  padding: .05rem .4rem;
  border-radius: 100px;
  background: var(--gray-200);
  color: var(--text-muted);
}

/* 类别选择 */
.cat-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .35rem;
}
.cat-btn {
  display: flex;
  align-items: center;
  gap: .35rem;
  padding: .45rem .65rem;
  border-radius: 8px;
  font-size: .78rem;
  font-weight: 500;
  border: 1.5px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all .2s;
}
.cat-btn:hover { border-color: var(--gray-400); }
.cat-btn.active {
  border-width: 2px;
  font-weight: 600;
}
.cat-dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

/* 标注列表 */
.ann-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: .3rem;
}
.ann-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: .4rem .5rem;
  border-radius: 6px;
  background: var(--gray-50);
  border: 1px solid var(--border);
  font-size: .78rem;
}
.ann-info {
  display: flex;
  align-items: center;
  gap: .4rem;
}
.ann-cat {
  display: inline-block;
  padding: .1rem .45rem;
  border-radius: 4px;
  font-size: .72rem;
  font-weight: 600;
}
.ann-dims {
  color: var(--text-muted);
  font-size: .7rem;
  font-family: monospace;
}
.ann-source {
  display: inline-block;
  padding: .05rem .35rem;
  border-radius: 3px;
  font-size: .65rem;
  font-weight: 600;
}
.ann-source.manual {
  background: #dbeafe;
  color: #1e40af;
}
.ann-source.predicted {
  background: #fce7f3;
  color: #9d174d;
}
.ann-del {
  width: 24px;
  height: 24px;
  border-radius: 4px;
  border: none;
  background: none;
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all .15s;
}
.ann-del:hover { background: #fee2e2; color: #c53030; }
.ann-empty {
  text-align: center;
  color: var(--text-muted);
  font-size: .8rem;
  padding: 1.5rem 0;
}

/* 快捷键 */
.shortcuts {
  display: flex;
  flex-wrap: wrap;
  gap: .5rem .75rem;
}
.shortcut {
  font-size: .72rem;
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: .25rem;
}
kbd {
  display: inline-block;
  padding: .05rem .3rem;
  border-radius: 3px;
  font-size: .68rem;
  font-family: monospace;
  background: var(--gray-100);
  border: 1px solid var(--gray-300);
  color: var(--text-secondary);
}

/* 状态 */
.empty-state, .loading-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: .5rem;
  color: var(--text-muted);
}
.empty-icon { font-size: 3rem; opacity: .3; }
.empty-hint { font-size: .82rem; }

.spin {
  width: 32px; height: 32px;
  border: 3px solid var(--gray-200);
  border-top-color: var(--green-500);
  border-radius: 50%;
  animation: spin .7s linear infinite;
}

@media (max-width: 900px) {
  .main-area { grid-template-columns: 1fr; }
  .side-panel { flex-direction: row; flex-wrap: wrap; }
  .panel-section { flex: 1; min-width: 200px; }
}
</style>
