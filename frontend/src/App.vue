<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const mobileMenuOpen = ref(false)
const now = ref(new Date())
let timer = null

onMounted(() => {
  timer = setInterval(() => { now.value = new Date() }, 1000)
})
onUnmounted(() => { clearInterval(timer) })

const timeStr = computed(() => {
  const d = now.value
  const h = String(d.getHours()).padStart(2, '0')
  const m = String(d.getMinutes()).padStart(2, '0')
  const s = String(d.getSeconds()).padStart(2, '0')
  return `${h}:${m}:${s}`
})

const dateStr = computed(() => {
  const d = now.value
  const weekdays = ['日', '一', '二', '三', '四', '五', '六']
  return `${d.getMonth() + 1}月${d.getDate()}日 周${weekdays[d.getDay()]}`
})

const greeting = computed(() => {
  const h = now.value.getHours()
  if (h < 6) return '夜深了，注意休息'
  if (h < 9) return '早上好，新的一天开始了'
  if (h < 12) return '上午好，工作顺利'
  if (h < 14) return '中午好，记得吃饭'
  if (h < 18) return '下午好，继续加油'
  if (h < 22) return '晚上好，辛苦了'
  return '夜深了，早点休息'
})

const navItems = [
  { path: '/', label: '识别' },
  { path: '/records', label: '数据记录' },
  { path: '/annotation', label: '标注' },
  { path: '/categories', label: '分类标准' },
  { path: '/about', label: '关于' },
]
</script>

<template>
  <div class="app-layout">
    <header class="app-header">
      <div class="header-inner">

        <!-- Logo 靠左 -->
        <router-link to="/" class="logo">
          <span class="logo-icon">♻</span>
          <span class="logo-text">EcoSort</span>
        </router-link>

        <!-- 中间：时间 + 祝福 -->
        <div class="header-center">
          <span class="center-clock">{{ timeStr }}</span>
          <span class="center-date">{{ dateStr }}</span>
          <span class="center-divider"></span>
          <span class="center-greeting">{{ greeting }}</span>
        </div>

        <!-- Tabs 靠右 -->
        <nav class="nav-tabs">
          <router-link
            v-for="item in navItems"
            :key="item.path"
            :to="item.path"
            class="nav-tab"
            :class="{ active: route.path === item.path }"
          >{{ item.label }}</router-link>
        </nav>

        <button class="menu-toggle" @click="mobileMenuOpen = !mobileMenuOpen">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>
      </div>

      <!-- 移动端 -->
      <div v-if="mobileMenuOpen" class="nav-mobile">
        <router-link
          v-for="item in navItems"
          :key="item.path"
          :to="item.path"
          class="nav-mobile-item"
          :class="{ active: route.path === item.path }"
          @click="mobileMenuOpen = false"
        >{{ item.label }}</router-link>
      </div>
    </header>

    <main class="app-main">
      <router-view v-slot="{ Component }">
        <component :is="Component" :key="$route.fullPath" />
      </router-view>
    </main>
  </div>
</template>

<style>
.app-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.app-header {
  position: sticky;
  top: 0;
  z-index: 50;
  background: rgba(255,255,255,.95);
  backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--border);
}

.header-inner {
  padding: 0 3rem;
  height: 56px;
  display: flex;
  align-items: center;
  gap: 1rem;
}

/* ─── Logo 左 ─── */
.logo {
  display: flex;
  align-items: center;
  gap: .5rem;
  font-weight: 700;
  font-size: 1.1rem;
  color: var(--green-700);
  flex-shrink: 0;
  margin-right: auto;
}
.logo-icon {
  width: 30px; height: 30px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--green-600), var(--green-400));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .85rem;
  color: #fff;
  box-shadow: 0 2px 6px rgba(45,138,78,.25);
}

/* ─── 中间时间和祝福 ─── */
.header-center {
  display: flex;
  align-items: center;
  gap: .75rem;
  flex-shrink: 1;
  min-width: 0;
}
.center-clock {
  font-family: 'SF Mono', 'Cascadia Code', Consolas, monospace;
  font-size: 1.15rem;
  font-weight: 600;
  color: var(--text);
  letter-spacing: .03em;
}
.center-date {
  font-size: .95rem;
  color: var(--text-secondary);
  font-weight: 500;
}
.center-divider {
  width: 1px;
  height: 18px;
  background: var(--border);
  flex-shrink: 0;
}
.center-greeting {
  font-size: .95rem;
  color: var(--green-600);
  font-weight: 600;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* ─── Tabs 右 ─── */
.nav-tabs {
  display: flex;
  gap: 3px;
  background: var(--gray-100);
  border-radius: 12px;
  padding: 4px;
  flex-shrink: 0;
  margin-left: auto;
  border: 1px solid var(--border);
}
.nav-tab {
  padding: .45rem 1.2rem;
  border-radius: 9px;
  font-size: .87rem;
  font-weight: 500;
  color: var(--text-muted);
  transition: all .3s cubic-bezier(.4,0,.2,1);
  white-space: nowrap;
  position: relative;
}
.nav-tab:hover {
  color: var(--text-secondary);
  background: rgba(0,0,0,.02);
}
.nav-tab.active {
  background: var(--bg-card);
  color: var(--green-700);
  font-weight: 600;
  box-shadow: 0 1px 4px rgba(0,0,0,.06), 0 0 0 1px rgba(45,138,78,.08);
}

.menu-toggle {
  display: none;
  background: none;
  border: none;
  color: var(--text-secondary);
  padding: .25rem;
}

.nav-mobile {
  padding: .5rem 1.5rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.nav-mobile-item {
  padding: .6rem 1rem;
  border-radius: var(--radius-sm);
  font-size: .88rem;
  color: var(--text-secondary);
  transition: all .2s;
}
.nav-mobile-item:hover,
.nav-mobile-item.active {
  background: var(--green-100);
  color: var(--green-700);
}

.app-main { flex: 1; }

.page-enter-active,
.page-leave-active { transition: opacity .2s ease, transform .2s ease; }
.page-enter-from { opacity: 0; transform: translateY(4px); }
.page-leave-to { opacity: 0; transform: translateY(-4px); }

@media (max-width: 768px) {
  .header-center { display: none; }
  .nav-tabs { display: none; }
  .menu-toggle { display: block; }
}
</style>
