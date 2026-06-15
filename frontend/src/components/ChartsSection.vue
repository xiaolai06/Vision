<script setup>
import { ref, watch, onBeforeUnmount } from 'vue'
import {
  Chart,
  DoughnutController,
  BarController,
  LineController,
  ArcElement,
  BarElement,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
} from 'chart.js'

Chart.register(
  DoughnutController,
  BarController,
  LineController,
  ArcElement,
  BarElement,
  LineElement,
  PointElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  Filler,
)

const props = defineProps({
  chartData: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const pieCanvas = ref(null)
const histCanvas = ref(null)
const trendCanvas = ref(null)

let pieChart = null
let histChart = null
let trendChart = null

const CAT_COLORS = {
  recyclable: '#3182ce',
  kitchen: '#38a169',
  hazardous: '#e53e3e',
  other: '#718096',
}
const CAT_LABELS = {
  recyclable: '可回收物',
  kitchen: '厨余垃圾',
  hazardous: '有害垃圾',
  other: '其他垃圾',
}

function destroyCharts() {
  pieChart?.destroy(); pieChart = null
  histChart?.destroy(); histChart = null
  trendChart?.destroy(); trendChart = null
}

function buildCharts(data) {
  destroyCharts()
  if (!data) return

  // 1. 分类分布 - 环形图
  const catDist = data.category_distribution || []
  if (catDist.length > 0 && pieCanvas.value) {
    pieChart = new Chart(pieCanvas.value, {
      type: 'doughnut',
      data: {
        labels: catDist.map(d => CAT_LABELS[d.category] || d.category),
        datasets: [{
          data: catDist.map(d => d.count),
          backgroundColor: catDist.map(d => CAT_COLORS[d.category] || '#999'),
          borderWidth: 0,
          hoverOffset: 6,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '60%',
        plugins: {
          legend: { position: 'bottom', labels: { padding: 12, usePointStyle: true, pointStyle: 'circle' } },
          tooltip: { callbacks: { label: (ctx) => `${ctx.label}: ${ctx.parsed} 条` } },
        },
      },
    })
  }

  // 2. 置信度分布 - 柱状图
  const histData = data.confidence_histogram || []
  if (histData.length > 0 && histCanvas.value) {
    histChart = new Chart(histCanvas.value, {
      type: 'bar',
      data: {
        labels: histData.map(d => d.range),
        datasets: [{
          data: histData.map(d => d.count),
          backgroundColor: '#48bb78',
          borderRadius: 4,
          barPercentage: 0.7,
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 } } },
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
        },
        plugins: { legend: { display: false } },
      },
    })
  }

  // 3. 每日趋势 - 折线图
  const trendData = data.daily_trend || []
  if (trendData.length > 0 && trendCanvas.value) {
    const ctx = trendCanvas.value.getContext('2d')
    const gradient = ctx.createLinearGradient(0, 0, 0, 200)
    gradient.addColorStop(0, 'rgba(72, 187, 120, 0.3)')
    gradient.addColorStop(1, 'rgba(72, 187, 120, 0.02)')

    trendChart = new Chart(trendCanvas.value, {
      type: 'line',
      data: {
        labels: trendData.map(d => d.date.slice(5)),
        datasets: [{
          data: trendData.map(d => d.count),
          borderColor: '#48bb78',
          backgroundColor: gradient,
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          pointBackgroundColor: '#48bb78',
        }],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          x: { grid: { display: false }, ticks: { font: { size: 10 }, maxRotation: 45 } },
          y: { beginAtZero: true, ticks: { stepSize: 1 } },
        },
        plugins: { legend: { display: false } },
      },
    })
  }
}

watch(() => props.chartData, (val) => {
  if (val) setTimeout(() => buildCharts(val), 50)
}, { immediate: true })

onBeforeUnmount(destroyCharts)
</script>

<template>
  <div class="charts-section">
    <div v-if="loading" class="charts-loading">加载图表中...</div>
    <div v-else-if="!chartData" class="charts-empty">暂无数据</div>
    <div v-else class="charts-grid">
      <div class="chart-card">
        <h3>分类分布</h3>
        <div class="chart-wrap">
          <canvas ref="pieCanvas"></canvas>
        </div>
      </div>
      <div class="chart-card">
        <h3>置信度分布</h3>
        <div class="chart-wrap">
          <canvas ref="histCanvas"></canvas>
        </div>
      </div>
      <div class="chart-card wide">
        <h3>识别趋势（近30天）</h3>
        <div class="chart-wrap">
          <canvas ref="trendCanvas"></canvas>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.charts-section {
  margin-bottom: 1.5rem;
}
.charts-loading,
.charts-empty {
  text-align: center;
  padding: 2rem;
  color: var(--text-muted);
  font-size: .85rem;
}
.charts-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}
.chart-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1rem 1.25rem;
}
.chart-card h3 {
  font-size: .82rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: .75rem;
}
.chart-card.wide {
  grid-column: 1 / -1;
}
.chart-wrap {
  height: 200px;
  position: relative;
}

@media (max-width: 768px) {
  .charts-grid { grid-template-columns: 1fr; }
  .chart-wrap { height: 180px; }
}
</style>
