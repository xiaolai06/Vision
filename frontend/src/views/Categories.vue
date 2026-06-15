<script setup>
const categories = [
  {
    key: 'recyclable',
    name: '可回收物',
    icon: '♻️',
    color: 'var(--cat-recycle)',
    bg: 'var(--cat-recycle-bg)',
    bin: '蓝色垃圾桶',
    desc: '适宜回收和资源化利用的生活废弃物。主要包括废纸、废塑料、废金属、废玻璃、废织物等，经过分拣后可重新进入生产环节，减少资源浪费。',
    items: ['塑料瓶', '纸盒', '金属罐', '玻璃瓶', '旧衣物', '易拉罐', '书本报纸', '快递纸箱', '泡沫塑料', '塑料玩具', '铁钉螺丝', '不锈钢餐具', '铝合金窗框', '旧床单被套'],
    tips: '瓶罐类请倒空内容物并压扁减小体积。纸类保持平整不要揉团。玻璃制品用报纸包好防止碎片伤人。',
    mistakes: [
      '被污染的纸巾和餐纸不可回收（属于其他垃圾）',
      '碎玻璃不是可回收物，容易伤人（属于其他垃圾）',
      '一次性纸杯内层有塑料膜，一般不可回收',
    ],
    process: '回收后经过分拣、清洗、破碎、熔融或打浆，重新制成原材料。1 吨废纸可再造 800 公斤好纸。',
  },
  {
    key: 'kitchen',
    name: '厨余垃圾',
    icon: '🥬',
    color: 'var(--cat-kitchen)',
    bg: 'var(--cat-kitchen-bg)',
    bin: '绿色垃圾桶',
    desc: '易腐烂的有机废弃物，包括家庭厨房产生的食材废料和餐后残余。这类垃圾含水率高、易腐败发臭，但可以通过生物技术转化为有用的资源。',
    items: ['果皮', '骨头', '剩饭剩菜', '茶叶渣', '蛋壳', '菜叶', '豆渣', '过期食品', '花卉绿植', '中药药渣', '瓜子壳', '鱼骨虾壳', '玉米棒', '面包糕点'],
    tips: '沥干水分后投放。大骨头（猪腿骨、牛骨等硬质骨）属于其他垃圾，小骨头和鱼骨才是厨余。过期食品需要去除包装后投放。',
    mistakes: [
      '大骨头（猪腿骨）是其他垃圾，不是厨余',
      '榴莲壳、椰子壳质地坚硬，属于其他垃圾',
      '外卖盒沾满油污不可回收，属于其他垃圾',
    ],
    process: '通过厌氧发酵产生沼气用于发电，或好氧堆肥制成有机肥料。1 吨厨余垃圾可产约 100 立方米沼气。',
  },
  {
    key: 'hazardous',
    name: '有害垃圾',
    icon: '⚠️',
    color: 'var(--cat-hazard)',
    bg: 'var(--cat-hazard-bg)',
    bin: '红色垃圾桶',
    desc: '对人体健康或自然环境造成直接或潜在危害的废弃物。这类垃圾虽然量少，但危害性大，必须单独收集、专业处理，不可混入其他垃圾。',
    items: ['电池', '灯泡/灯管', '过期药品', '油漆桶', '水银温度计', '指甲油', '杀虫剂', 'X光片', '硒鼓墨盒', '含汞器械', '废机油', '消毒剂', '农药瓶', '胶片'],
    tips: '轻拿轻放避免破损。电池请勿拆解，药品连带包装投放。灯管用纸包好再投。投放时注意密封，防止液体泄漏。',
    mistakes: [
      '无汞干电池（5号/7号碱性电池）已属于其他垃圾',
      'LED 灯不含汞，属于可回收物而非有害垃圾',
      '普通干电池不需要按有害垃圾处理（但充电电池属于有害垃圾）',
    ],
    process: '由专业机构进行安全处置，包括高温焚烧、化学处理、固化填埋等。电池中的重金属可提炼回收再利用。',
  },
  {
    key: 'other',
    name: '其他垃圾',
    icon: '🗑️',
    color: 'var(--cat-other)',
    bg: 'var(--cat-other-bg)',
    bin: '灰色垃圾桶',
    desc: '除可回收物、厨余垃圾、有害垃圾之外的其他生活废弃物。这类垃圾通常难以回收利用，但可以通过现代化焚烧技术转化为电能和热能。',
    items: ['纸巾', '陶瓷碎片', '烟蒂', '尘土', '一次性餐具', '污损纸张', '宠物粪便', '干燥剂', '创可贴', '一次性尿布', '旧毛巾', '保鲜膜', '编织袋', '复合材质包装'],
    tips: '尽量沥干水分后投放。受污染的纸张、塑料都归入此类。难以判断类别时，投入其他垃圾桶是最安全的选择。',
    mistakes: [
      '外卖盒虽然脏但不是厨余垃圾（属于其他垃圾）',
      '用过的卫生巾、尿布不是可回收物',
      '破碎的镜子、陶瓷不属于可回收的玻璃类',
    ],
    process: '运往垃圾焚烧发电厂，经高温焚烧减容约 90%，产生的热能转化为电能，残渣用于制作建材或填埋。',
  },
]
</script>

<template>
  <div class="page">
    <div class="container">
      <div class="page-head">
        <h1>垃圾分类标准</h1>
        <p>按国家标准，生活垃圾分为以下四类。了解每类的详细规则，正确投放每一件垃圾。</p>
      </div>

      <div class="cat-list">
        <article v-for="cat in categories" :key="cat.key" class="cat-card">
          <!-- 头部 -->
          <div class="cat-head" :style="{ borderLeftColor: cat.color }">
            <div class="cat-icon" :style="{ background: cat.bg, color: cat.color }">
              {{ cat.icon }}
            </div>
            <div class="cat-meta">
              <h2>{{ cat.name }}</h2>
              <span class="cat-bin" :style="{ color: cat.color }">{{ cat.bin }}</span>
            </div>
          </div>

          <!-- 说明 -->
          <p class="cat-desc">{{ cat.desc }}</p>

          <!-- 常见物品 -->
          <div class="cat-section">
            <h3 class="cat-section-title">常见物品</h3>
            <div class="cat-items">
              <span v-for="item in cat.items" :key="item" class="cat-tag">{{ item }}</span>
            </div>
          </div>

          <!-- 投放提示 -->
          <div class="cat-section">
            <h3 class="cat-section-title">投放提示</h3>
            <p class="cat-tips-text">{{ cat.tips }}</p>
          </div>

          <!-- 常见误区 -->
          <div class="cat-section">
            <h3 class="cat-section-title">常见误区</h3>
            <ul class="cat-mistakes">
              <li v-for="(m, i) in cat.mistakes" :key="i">{{ m }}</li>
            </ul>
          </div>

          <!-- 处理方式 -->
          <div class="cat-section">
            <h3 class="cat-section-title">处理方式</h3>
            <p class="cat-process">{{ cat.process }}</p>
          </div>
        </article>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  padding: 2rem 3rem 3rem;
}

.page-head {
  margin-bottom: 1.75rem;
}
.page-head h1 {
  font-size: 1.3rem;
  font-weight: 700;
  margin-bottom: .2rem;
}
.page-head p {
  font-size: .88rem;
  color: var(--text-muted);
  max-width: 600px;
  line-height: 1.5;
}

.cat-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.cat-card {
  background: var(--bg-card);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 1.75rem;
}

/* 头部 */
.cat-head {
  display: flex;
  align-items: center;
  gap: 1rem;
  border-left: 4px solid var(--gray-400);
  padding-left: 1rem;
  margin-bottom: 1.25rem;
}
.cat-icon {
  width: 48px; height: 48px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  flex-shrink: 0;
}
.cat-meta h2 {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: .05rem;
}
.cat-bin {
  font-size: .85rem;
  font-weight: 500;
}

/* 描述 */
.cat-desc {
  font-size: .9rem;
  color: var(--text-secondary);
  line-height: 1.7;
  margin-bottom: 1.5rem;
}

/* 各小节 */
.cat-section {
  margin-bottom: 1.25rem;
}
.cat-section:last-child { margin-bottom: 0; }
.cat-section-title {
  font-size: .82rem;
  font-weight: 600;
  color: var(--text-muted);
  margin-bottom: .5rem;
  text-transform: uppercase;
  letter-spacing: .03em;
}

/* 常见物品标签 */
.cat-items { display: flex; flex-wrap: wrap; gap: .4rem; }
.cat-tag {
  padding: .28rem .65rem;
  border-radius: 100px;
  font-size: .8rem;
  background: var(--gray-100);
  color: var(--text-secondary);
}

/* 投放提示 */
.cat-tips-text {
  font-size: .88rem;
  color: var(--text-secondary);
  line-height: 1.6;
  background: var(--gray-100);
  padding: .75rem 1rem;
  border-radius: var(--radius-sm);
}

/* 常见误区 */
.cat-mistakes {
  list-style: none;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: .4rem;
}
.cat-mistakes li {
  font-size: .86rem;
  color: var(--text-secondary);
  line-height: 1.5;
  padding-left: 1.2rem;
  position: relative;
}
.cat-mistakes li::before {
  content: '✕';
  position: absolute;
  left: 0;
  color: var(--cat-hazard);
  font-size: .75rem;
  font-weight: 700;
  top: .15rem;
}

/* 处理方式 */
.cat-process {
  font-size: .86rem;
  color: var(--text-secondary);
  line-height: 1.6;
}

@media (max-width: 768px) {
  .cat-card { padding: 1.25rem; }
}
</style>
