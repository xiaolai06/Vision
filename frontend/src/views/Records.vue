<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { fetchRecords, deleteRecord, batchDeleteRecords, correctRecord, batchCorrectRecords, exportUrl, fetchChartData, splitExportUrl } from '../api/records.js'
import ChartsSection from '../components/ChartsSection.vue'

const records = ref([])
const stats = ref({ total: 0, corrected: 0, uncorrected: 0, by_category: {} })
const loading = ref(false)
const filterCategory = ref('')
const filterCorrected = ref('')
const filterStartDate = ref('')
const filterEndDate = ref('')
const filterKeyword = ref('')
const filterModelType = ref('')
const currentPage = ref(0)
const pageSize = 40
const mounted = ref(true)

// 批量操作
const selectedIds = ref(new Set())

// 图表
const chartData = ref(null)
const chartLoading = ref(false)
const showCharts = ref(true)

// 修正弹窗
const showCorrectModal = ref(false)
const correctingId = ref(null)
const correctCategory = ref('recyclable')
const correctConfidence = ref(1.0)

// 批量修正弹窗
const showBatchCorrectModal = ref(false)
const batchCorrectCat = ref('recyclable')
const batchCorrectConf = ref(1.0)

// 划分导出弹窗
const showSplitModal = ref(false)
const trainRatio = ref(0.8)
const valRatio = ref(0.1)
const testRatio = ref(0.1)

const categoryOptions = [
  { value: 'recyclable', label: '可回收物', color: 'var(--cat-recycle)' },
  { value: 'kitchen', label: '厨余垃圾', color: 'var(--cat-kitchen)' },
  { value: 'hazardous', label: '有害垃圾', color: 'var(--cat-hazard)' },
  { value: 'other', label: '其他垃圾', color: 'var(--cat-other)' },
]

const categoryMeta = {
  recyclable: { label: '可回收物', color: 'var(--cat-recycle)', bg: 'var(--cat-recycle-bg)' },
  kitchen: { label: '厨余垃圾', color: 'var(--cat-kitchen)', bg: 'var(--cat-kitchen-bg)' },
  hazardous: { label: '有害垃圾', color: 'var(--cat-hazard)', bg: 'var(--cat-hazard-bg)' },
  other: { label: '其他垃圾', color: 'var(--cat-other)', bg: 'var(--cat-other-bg)' },
}

// 计算属性
const allSelected = computed(() => records.value.length > 0 && selectedIds.value.size === records.value.length)
const someSelected = computed(() => selectedIds.value.size > 0 && selectedIds.value.size < records.value.length)

async function loadRecords() {
  loading.value = true
  try {
    const params = { offset: currentPage.value * pageSize, limit: pageSize }
    if (filterCategory.value) params.category = filterCategory.value
    if (filterCorrected.value !== '') params.corrected = Number(filterCorrected.value)
    if (filterStartDate.value) params.start_date = filterStartDate.value
    if (filterEndDate.value) params.end_date = filterEndDate.value
    if (filterKeyword.value) params.keyword = filterKeyword.value
    if (filterModelType.value) params.model_type = filterModelType.value
    const data = await fetchRecords(params)
    if (!mounted.value) return
    records.value = data.records
    stats.value = data.stats
    selectedIds.value.clear()
  } catch (e) {
    if (!mounted.value) return
    console.error(e)
  } finally {
    if (mounted.value) loading.value = false
  }
}

async function loadChartData() {
  chartLoading.value = true
  try {
    const params = {}
    if (filterCategory.value) params.category = filterCategory.value
    chartData.value = await fetchChartData(params)
  } catch (e) {
    if (!mounted.value) return
    console.error(e)
  } finally {
    if (mounted.value) chartLoading.value = false
  }
}

function getImageUrl(path) {
  if (!path) return ''
  const filename = path.split('/').pop().split('\\').pop()
  return `/api/images/${filename}`
}

function getCategory(cat) {
  return categoryMeta[cat] || categoryMeta.other
}

function getEffectiveCategory(record) {
  return record.corrected_category || record.predicted_category
}

function formatDate(iso) {
  const d = new Date(iso)
  return `${d.getMonth()+1}/${d.getDate()} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`
}

// 全选/取消全选
function toggleSelectAll() {
  if (allSelected.value) {
    selectedIds.value.clear()
  } else {
    records.value.forEach(r => selectedIds.value.add(r.id))
  }
}

// 单选
function toggleSelect(id) {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id)
  } else {
    selectedIds.value.add(id)
  }
}

// 删除单条
async function handleDelete(id) {
  if (!confirm('确定删除这条记录？')) return
  try {
    await deleteRecord(id)
    await Promise.all([loadRecords(), loadChartData()])
  } catch (e) { alert(e.message) }
}

// 批量删除
async function handleBatchDelete() {
  if (selectedIds.value.size === 0) return
  if (!confirm(`确定删除选中的 ${selectedIds.value.size} 条记录？`)) return
  try {
    await batchDeleteRecords([...selectedIds.value])
    selectedIds.value.clear()
    await Promise.all([loadRecords(), loadChartData()])
  } catch (e) { alert(e.message) }
}

// 单条修正
function openCorrect(record) {
  correctingId.value = record.id
  correctCategory.value = getEffectiveCategory(record)
  correctConfidence.value = record.confidence || 1.0
  showCorrectModal.value = true
}

async function submitCorrect() {
  const opt = categoryOptions.find(o => o.value === correctCategory.value)
  try {
    await correctRecord(correctingId.value, correctCategory.value, opt?.label || '', correctConfidence.value)
    showCorrectModal.value = false
    await Promise.all([loadRecords(), loadChartData()])
  } catch (e) { alert(e.message) }
}

// 批量修正
function openBatchCorrect() {
  if (selectedIds.value.size === 0) return
  showBatchCorrectModal.value = true
}

async function submitBatchCorrect() {
  const opt = categoryOptions.find(o => o.value === batchCorrectCat.value)
  try {
    await batchCorrectRecords([...selectedIds.value], batchCorrectCat.value, opt?.label || '', batchCorrectConf.value)
    showBatchCorrectModal.value = false
    selectedIds.value.clear()
    await Promise.all([loadRecords(), loadChartData()])
  } catch (e) { alert(e.message) }
}

// 导出
function handleExport(format) {
  const url = exportUrl(format, filterCategory.value || undefined)
  window.open(url, '_blank')
}

// 划分导出
function handleSplitExport() {
  const url = splitExportUrl(
    trainRatio.value, valRatio.value, testRatio.value,
    filterCategory.value || undefined
  )
  window.open(url, '_blank')
  showSplitModal.value = false
}

// 筛选
function onFilterChange() {
  currentPage.value = 0
  loadRecords()
  loadChartData()
}

onMounted(() => {
  loadRecords()
  loadChartData()
})
onUnmounted(() => {
  mounted.value = false
  showCorrectModal.value = false
  showBatchCorrectModal.value = false
  showSplitModal.value = false
})
</script>

<template>
  <div class="page">
    <div class="page-head">
      <h1>识别记录</h1>

      <!-- 统计卡片 -->
      <div class="stats-row">
        <div class="stat-chip">
          <span class="stat-num">{{ stats.total }}</span>
          <span class="stat-label">总记录</span>
        </div>
        <div class="stat-chip">
          <span class="stat-num green">{{ stats.corrected }}</span>
          <span class="stat-label">已修正</span>
        </div>
        <div class="stat-chip">
          <span class="stat-num gray">{{ stats.uncorrected }}</span>
          <span class="stat-label">待修正</span>
        </div>
        <div class="stat-chip" v-if="stats.by_category">
          <span class="stat-num blue">{{ stats.by_category.recyclable || 0 }}</span>
          <span class="stat-label">可回收物</span>
        </div>
        <div class="stat-chip" v-if="stats.by_category">
          <span class="stat-num kitchen">{{ stats.by_category.kitchen || 0 }}</span>
          <span class="stat-label">厨余垃圾</span>
        </div>
        <div class="stat-chip" v-if="stats.by_category">
          <span class="stat-num hazard">{{ stats.by_category.hazardous || 0 }}</span>
          <span class="stat-label">有害垃圾</span>
        </div>
        <div class="stat-chip" v-if="stats.by_category">
          <span class="stat-num other">{{ stats.by_category.other || 0 }}</span>
          <span class="stat-label">其他垃圾</span>
        </div>
      </div>
    </div>

    <!-- 图表区 -->
    <div class="charts-toggle">
      <button class="charts-toggle-btn" @click="showCharts = !showCharts">
        {{ showCharts ? '收起图表' : '展开图表' }}
        <span class="arrow" :class="{ up: showCharts }">▼</span>
      </button>
    </div>
    <ChartsSection v-if="showCharts" :chartData="chartData" :loading="chartLoading" />

    <!-- 工具栏 -->
    <div class="toolbar">
      <div class="toolbar-filters">
        <input v-model="filterKeyword" type="text" placeholder="搜索物品名称..." class="search-input" @keyup.enter="onFilterChange" />
        <input v-model="filterStartDate" type="date" class="date-input" @change="onFilterChange" title="起始日期" />
        <span class="date-sep">至</span>
        <input v-model="filterEndDate" type="date" class="date-input" @change="onFilterChange" title="结束日期" />
        <select v-model="filterCategory" @change="onFilterChange" class="select">
          <option value="">全部分类</option>
          <option v-for="o in categoryOptions" :key="o.value" :value="o.value">{{ o.label }}</option>
        </select>
        <select v-model="filterCorrected" @change="onFilterChange" class="select">
          <option value="">全部状态</option>
          <option value="1">已修正</option>
          <option value="0">未修正</option>
        </select>
        <select v-model="filterModelType" @change="onFilterChange" class="select">
          <option value="">全部模型</option>
          <option value="classification">分类模型</option>
          <option value="detection">检测模型</option>
        </select>
        <button class="btn-ghost" @click="loadRecords(); loadChartData()">刷新</button>
      </div>
      <div class="toolbar-actions">
        <template v-if="selectedIds.size > 0">
          <span class="selected-count">已选 {{ selectedIds.size }} 条</span>
          <button class="btn-batch" @click="openBatchCorrect">批量修正</button>
          <button class="btn-batch danger" @click="handleBatchDelete">批量删除</button>
        </template>
        <div class="export-group">
          <span class="export-label">导出：</span>
          <button class="btn-export" @click="handleExport('csv')">CSV</button>
          <button class="btn-export" @click="handleExport('coco')">COCO</button>
          <button class="btn-export" @click="handleExport('yolo')">YOLO</button>
          <button class="btn-export det" @click="handleExport('yolo_det')" title="含真实 bbox 的 YOLO 检测格式 ZIP">YOLO检测</button>
          <button class="btn-export det" @click="handleExport('coco_det')" title="含真实 bbox 的 COCO 检测 JSON">COCO检测</button>
          <button class="btn-export split" @click="showSplitModal = true">划分</button>
        </div>
      </div>
    </div>

    <!-- 加载状态 -->
    <div v-if="loading" class="loading-state">加载中...</div>

    <!-- 空状态 -->
    <div v-else-if="!records || records.length === 0" class="empty-state">
      <div class="empty-icon">📋</div>
      <p>暂无识别记录</p>
      <p class="empty-hint">在「识别」页面上传图片后，记录会自动保存在这里</p>
    </div>

    <!-- 数据表格 -->
    <div v-else class="table-wrap">
      <table class="data-table">
        <thead>
          <tr>
            <th class="col-check">
              <input type="checkbox" :checked="allSelected" :indeterminate.prop="someSelected" @change="toggleSelectAll" />
            </th>
            <th class="col-thumb">缩略图</th>
            <th class="col-category">预测分类</th>
            <th class="col-model">模型</th>
            <th class="col-confidence">置信度</th>
            <th class="col-status">状态</th>
            <th class="col-date">时间</th>
            <th class="col-actions">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in records" :key="r.id" :class="{ selected: selectedIds.has(r.id) }">
            <td class="col-check">
              <input type="checkbox" :checked="selectedIds.has(r.id)" @change="toggleSelect(r.id)" />
            </td>
            <td class="col-thumb">
              <img :src="getImageUrl(r.image_path)" alt="" loading="lazy" />
            </td>
            <td class="col-category">
              <span
                class="cat-badge"
                :style="{ background: getCategory(getEffectiveCategory(r)).bg, color: getCategory(getEffectiveCategory(r)).color }"
              >
                {{ getCategory(getEffectiveCategory(r)).label }}
              </span>
            </td>
            <td class="col-model">
              <span class="model-type-tag" :class="r.model_type || 'classification'">
                {{ (r.model_type || 'classification') === 'detection' ? '检测' : '分类' }}
              </span>
              <span class="model-name-text">{{ r.model_name || 'mobilenet_v2' }}</span>
            </td>
            <td class="col-confidence">
              <div class="conf-cell">
                <div class="conf-bar-wrap">
                  <div class="conf-bar-fill" :style="{ width: (r.confidence * 100) + '%' }"></div>
                </div>
                <span class="conf-text">{{ (r.confidence * 100).toFixed(1) }}%</span>
              </div>
            </td>
            <td class="col-status">
              <span :class="r.is_corrected ? 'status-corrected' : 'status-pending'">
                {{ r.is_corrected ? '已修正' : '待修正' }}
              </span>
            </td>
            <td class="col-date">{{ formatDate(r.created_at) }}</td>
            <td class="col-actions">
              <button class="act-btn" @click="openCorrect(r)" title="修正">✏️</button>
              <button class="act-btn" @click="handleDelete(r.id)" title="删除">🗑️</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- 分页 -->
    <div v-if="records.length >= pageSize" class="pagination">
      <button class="btn-ghost" :disabled="currentPage === 0" @click="currentPage--; loadRecords()">上一页</button>
      <span class="page-info">第 {{ currentPage + 1 }} 页</span>
      <button class="btn-ghost" @click="currentPage++; loadRecords()">下一页</button>
    </div>
  </div>

  <!-- 修正弹窗 -->
  <div v-if="showCorrectModal" class="modal-overlay" @click.self="showCorrectModal = false">
    <div class="modal">
      <h3>修正分类标签</h3>
      <p class="modal-desc">如果识别结果不正确，请手动选择正确的分类和置信度</p>

      <div class="modal-section">
        <label class="modal-label">分类类别</label>
        <div class="modal-options">
          <button
            v-for="o in categoryOptions"
            :key="o.value"
            class="modal-opt"
            :class="{ selected: correctCategory === o.value }"
            :style="correctCategory === o.value ? { borderColor: o.color, background: categoryMeta[o.value].bg } : {}"
            @click="correctCategory = o.value"
          >
            {{ o.label }}
          </button>
        </div>
      </div>

      <div class="modal-section">
        <label class="modal-label">置信度（0.0 - 1.0）</label>
        <input v-model.number="correctConfidence" type="range" min="0" max="1" step="0.05" class="confidence-slider" />
        <div class="confidence-value">{{ (correctConfidence * 100).toFixed(0) }}%</div>
      </div>

      <div class="modal-actions">
        <button class="btn-ghost" @click="showCorrectModal = false">取消</button>
        <button class="btn-primary" @click="submitCorrect">确认修正</button>
      </div>
    </div>
  </div>

  <!-- 批量修正弹窗 -->
  <div v-if="showBatchCorrectModal" class="modal-overlay" @click.self="showBatchCorrectModal = false">
    <div class="modal">
      <h3>批量修正分类</h3>
      <p class="modal-desc">将选中的 {{ selectedIds.size }} 条记录统一修正为指定分类</p>

      <div class="modal-section">
        <label class="modal-label">分类类别</label>
        <div class="modal-options">
          <button
            v-for="o in categoryOptions"
            :key="o.value"
            class="modal-opt"
            :class="{ selected: batchCorrectCat === o.value }"
            :style="batchCorrectCat === o.value ? { borderColor: o.color, background: categoryMeta[o.value].bg } : {}"
            @click="batchCorrectCat = o.value"
          >
            {{ o.label }}
          </button>
        </div>
      </div>

      <div class="modal-section">
        <label class="modal-label">置信度（0.0 - 1.0）</label>
        <input v-model.number="batchCorrectConf" type="range" min="0" max="1" step="0.05" class="confidence-slider" />
        <div class="confidence-value">{{ (batchCorrectConf * 100).toFixed(0) }}%</div>
      </div>

      <div class="modal-actions">
        <button class="btn-ghost" @click="showBatchCorrectModal = false">取消</button>
        <button class="btn-primary" @click="submitBatchCorrect">确认批量修正</button>
      </div>
    </div>
  </div>

  <!-- 划分导出弹窗 -->
  <div v-if="showSplitModal" class="modal-overlay" @click.self="showSplitModal = false">
    <div class="modal">
      <h3>训练集划分导出</h3>
      <p class="modal-desc">按比例随机划分所有记录，导出为包含目录结构的 ZIP 文件，可直接用于模型训练</p>

      <div class="split-controls">
        <div class="split-row">
          <label class="split-label">训练集</label>
          <input type="range" v-model.number="trainRatio" min="0.1" max="0.98" step="0.05" class="confidence-slider" />
          <span class="split-value">{{ (trainRatio * 100).toFixed(0) }}%</span>
        </div>
        <div class="split-row">
          <label class="split-label">验证集</label>
          <input type="range" v-model.number="valRatio" min="0.01" max="0.5" step="0.05" class="confidence-slider" />
          <span class="split-value">{{ (valRatio * 100).toFixed(0) }}%</span>
        </div>
        <div class="split-row">
          <label class="split-label">测试集</label>
          <input type="range" v-model.number="testRatio" min="0.01" max="0.5" step="0.05" class="confidence-slider" />
          <span class="split-value">{{ (testRatio * 100).toFixed(0) }}%</span>
        </div>
      </div>
      <p class="split-note">比例会自动归一化为 100%。ZIP 内按 train/val/test 分目录组织，附带 dataset.yaml 和 labels.csv</p>

      <div class="modal-actions">
        <button class="btn-ghost" @click="showSplitModal = false">取消</button>
        <button class="btn-primary" @click="handleSplitExport">导出 ZIP</button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 2rem 3rem 3rem;
}

.page-head {
  margin-bottom: 1.25rem;
}
.page-head h1 {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: .75rem;
}

.stats-row {
  display: flex;
  gap: .6rem;
  flex-wrap: wrap;
}
.stat-chip {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  padding: .5rem .9rem;
  text-align: center;
  min-width: 70px;
  flex: 1 1 auto;
}
.stat-num {
  display: block;
  font-size: 1.25rem;
  font-weight: 700;
  color: var(--text);
}
.stat-num.green { color: var(--green-600); }
.stat-num.gray { color: var(--text-muted); }
.stat-num.blue { color: var(--cat-recycle); }
.stat-num.kitchen { color: var(--cat-kitchen); }
.stat-num.hazard { color: var(--cat-hazard); }
.stat-num.other { color: var(--cat-other); }
.stat-label {
  font-size: .72rem;
  color: var(--text-muted);
  white-space: nowrap;
}

/* 图表折叠 */
.charts-toggle {
  margin-bottom: .75rem;
}
.charts-toggle-btn {
  font-size: .82rem;
  color: var(--text-muted);
  background: none;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: .3rem;
  padding: .3rem 0;
}
.charts-toggle-btn:hover { color: var(--text-secondary); }
.arrow {
  font-size: .65rem;
  transition: transform .2s;
  display: inline-block;
}
.arrow.up { transform: rotate(180deg); }

/* 工具栏 */
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.25rem;
  flex-wrap: wrap;
  gap: .75rem;
}
.toolbar-filters {
  display: flex;
  align-items: center;
  gap: .4rem;
  flex-wrap: wrap;
  flex: 1;
}
.search-input {
  padding: .45rem .75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: .84rem;
  background: var(--bg-card);
  color: var(--text);
  min-width: 140px;
}
.search-input::placeholder { color: var(--text-muted); }
.date-input {
  padding: .4rem .5rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: .82rem;
  background: var(--bg-card);
  color: var(--text);
}
.date-sep {
  font-size: .78rem;
  color: var(--text-muted);
}
.select {
  padding: .45rem .75rem;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: .84rem;
  background: var(--bg-card);
  color: var(--text);
  cursor: pointer;
}
.btn-ghost {
  padding: .45rem .85rem;
  border-radius: var(--radius-sm);
  font-size: .84rem;
  font-weight: 500;
  border: 1px solid var(--border);
  background: var(--bg-card);
  color: var(--text-secondary);
  cursor: pointer;
  transition: all .2s;
}
.btn-ghost:hover { background: var(--gray-100); }
.btn-ghost:disabled { opacity: .4; cursor: not-allowed; }

.toolbar-actions {
  display: flex;
  align-items: center;
  gap: .75rem;
  flex-shrink: 0;
}
.selected-count {
  font-size: .82rem;
  color: var(--green-700);
  font-weight: 600;
}
.btn-batch {
  padding: .4rem .75rem;
  border-radius: var(--radius-sm);
  font-size: .8rem;
  font-weight: 600;
  border: 1px solid #9f7aea;
  background: #faf5ff;
  color: #6b46c1;
  cursor: pointer;
  transition: all .2s;
}
.btn-batch:hover { background: #e9d8fd; }
.btn-batch.danger {
  border-color: var(--cat-hazard);
  background: var(--cat-hazard-bg);
  color: var(--cat-hazard);
}
.btn-batch.danger:hover { background: #fed7d7; }

.export-group {
  display: flex;
  align-items: center;
  gap: .35rem;
}
.export-label {
  font-size: .82rem;
  color: var(--text-muted);
}
.btn-export {
  padding: .4rem .75rem;
  border-radius: var(--radius-sm);
  font-size: .8rem;
  font-weight: 600;
  border: 1px solid var(--green-200);
  background: var(--green-50);
  color: var(--green-700);
  cursor: pointer;
  transition: all .2s;
}
.btn-export:hover { background: var(--green-100); }
.btn-export.split {
  border-color: #9f7aea;
  background: #faf5ff;
  color: #6b46c1;
}
.btn-export.split:hover { background: #e9d8fd; }
.btn-export.det {
  border-color: #ed8936;
  background: #fffaf0;
  color: #c05621;
}
.btn-export.det:hover { background: #feebc8; }

/* 数据表格 */
.table-wrap {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  overflow-x: auto;
}
.data-table {
  width: 100%;
  border-collapse: collapse;
}
.data-table th {
  padding: .7rem 1rem;
  text-align: left;
  font-size: .78rem;
  font-weight: 600;
  color: var(--text-muted);
  text-transform: uppercase;
  letter-spacing: .03em;
  border-bottom: 1px solid var(--border);
  background: var(--gray-100);
  white-space: nowrap;
}
.data-table td {
  padding: .6rem 1rem;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
  font-size: .86rem;
}
.col-check {
  width: 40px;
  text-align: center;
}
.col-check input[type="checkbox"] {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: var(--green-600);
}
.data-table tbody tr.selected {
  background: #f0fff4;
}
.data-table tr:last-child td { border-bottom: none; }
.data-table tbody tr:hover { background: var(--gray-50, #fafafa); }

.col-thumb img {
  width: 48px;
  height: 48px;
  object-fit: cover;
  border-radius: 6px;
  background: var(--gray-100);
}

.cat-badge {
  display: inline-block;
  padding: .2rem .7rem;
  border-radius: 100px;
  font-size: .8rem;
  font-weight: 600;
  white-space: nowrap;
}

.col-model {
  display: flex;
  flex-direction: column;
  gap: .15rem;
}
.model-type-tag {
  display: inline-block;
  padding: .1rem .45rem;
  border-radius: 4px;
  font-size: .7rem;
  font-weight: 600;
  width: fit-content;
}
.model-type-tag.classification {
  background: #dbeafe;
  color: #1e40af;
}
.model-type-tag.detection {
  background: #fce7f3;
  color: #9d174d;
}
.model-name-text {
  font-size: .7rem;
  color: var(--text-muted);
  font-family: monospace;
}

.conf-cell {
  display: flex;
  align-items: center;
  gap: .5rem;
}
.conf-bar-wrap {
  width: 80px;
  height: 5px;
  background: var(--gray-200);
  border-radius: 100px;
  overflow: hidden;
  flex-shrink: 0;
}
.conf-bar-fill {
  height: 100%;
  background: var(--green-500);
  border-radius: 100px;
  transition: width .3s;
}
.conf-text {
  font-size: .82rem;
  font-weight: 600;
  white-space: nowrap;
}

.status-corrected {
  color: var(--green-600);
  font-size: .8rem;
  font-weight: 600;
}
.status-pending {
  color: var(--text-muted);
  font-size: .8rem;
}

.col-date {
  font-size: .82rem;
  color: var(--text-secondary);
  white-space: nowrap;
}

.col-actions {
  white-space: nowrap;
}
.act-btn {
  width: 30px;
  height: 30px;
  border-radius: 6px;
  border: 1px solid var(--border);
  background: var(--bg-card);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: .8rem;
  cursor: pointer;
  transition: all .2s;
  margin-right: .25rem;
}
.act-btn:hover { background: var(--gray-100); }
.act-btn:last-child:hover { background: var(--cat-hazard-bg); }

/* 分页 */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}
.page-info {
  font-size: .85rem;
  color: var(--text-muted);
}

/* 空状态 */
.empty-state, .loading-state {
  text-align: center;
  padding: 4rem 1rem;
  color: var(--text-muted);
}
.empty-icon { font-size: 3rem; opacity: .3; margin-bottom: .5rem; }
.empty-hint { font-size: .82rem; margin-top: .3rem; }

/* 修正弹窗 */
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,.4);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 100;
}
.modal {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  padding: 1.75rem;
  width: 440px;
  max-width: 90%;
  box-shadow: var(--shadow-lg);
}
.modal h3 {
  font-size: 1.1rem;
  font-weight: 700;
  margin-bottom: .3rem;
}
.modal-desc {
  font-size: .85rem;
  color: var(--text-muted);
  margin-bottom: 1.25rem;
  line-height: 1.5;
}

.modal-section {
  margin-bottom: 1.25rem;
}
.modal-label {
  display: block;
  font-size: .82rem;
  font-weight: 600;
  color: var(--text-secondary);
  margin-bottom: .5rem;
}

.modal-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .5rem;
}
.modal-opt {
  padding: .65rem .75rem;
  border-radius: var(--radius-sm);
  border: 2px solid var(--border);
  background: var(--bg-card);
  font-size: .88rem;
  font-weight: 500;
  cursor: pointer;
  transition: all .2s;
  text-align: center;
}
.modal-opt:hover { border-color: var(--gray-400); }
.modal-opt.selected {
  font-weight: 600;
  border-width: 2px;
}

/* 置信度滑块 */
.confidence-slider {
  width: 100%;
  margin-bottom: .5rem;
  accent-color: var(--green-600);
}
.confidence-value {
  font-size: .9rem;
  font-weight: 600;
  color: var(--green-700);
  text-align: center;
}

/* 划分导出弹窗 */
.split-controls {
  display: flex;
  flex-direction: column;
  gap: .75rem;
  margin-bottom: 1rem;
}
.split-row {
  display: flex;
  align-items: center;
  gap: .75rem;
}
.split-label {
  width: 50px;
  font-size: .85rem;
  font-weight: 600;
  color: var(--text-secondary);
  flex-shrink: 0;
}
.split-row .confidence-slider {
  flex: 1;
  margin-bottom: 0;
}
.split-value {
  width: 40px;
  text-align: right;
  font-size: .88rem;
  font-weight: 600;
  color: var(--green-700);
  flex-shrink: 0;
}
.split-note {
  font-size: .78rem;
  color: var(--text-muted);
  line-height: 1.5;
  margin-bottom: .5rem;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: .5rem;
  margin-top: 1.5rem;
}
.btn-primary {
  padding: .5rem 1.2rem;
  border-radius: var(--radius-sm);
  font-size: .88rem;
  font-weight: 600;
  border: none;
  background: var(--green-600);
  color: #fff;
  cursor: pointer;
  transition: all .2s;
}
.btn-primary:hover { background: var(--green-700); }

@media (max-width: 768px) {
  .page-head { flex-direction: column; }
  .toolbar { flex-direction: column; align-items: flex-start; }
  .col-thumb img { width: 36px; height: 36px; }
  .conf-bar-wrap { width: 50px; }
}
</style>
