import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Categories from '../views/Categories.vue'
import Records from '../views/Records.vue'
import Annotation from '../views/Annotation.vue'
import About from '../views/About.vue'

const routes = [
  { path: '/', name: 'home', component: Home, meta: { title: '智能识别' } },
  { path: '/records', name: 'records', component: Records, meta: { title: '数据记录' } },
  { path: '/annotation', name: 'annotation', component: Annotation, meta: { title: '数据标注' } },
  { path: '/categories', name: 'categories', component: Categories, meta: { title: '分类标准' } },
  { path: '/about', name: 'about', component: About, meta: { title: '关于项目' } },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  document.title = `${to.meta.title} - 智能垃圾分类助手`
})

export default router
