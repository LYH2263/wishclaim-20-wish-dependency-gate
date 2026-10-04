<template>
  <div class="wall">
    <h1 class="serif">愿望墙</h1>
    <p class="tag">无顶栏 · 瀑布流 · 点卡片认领</p>
    <div class="masonry">
      <article v-for="w in rows" :key="w.id" class="card"
               :class="{ 'dep-dim': dim(w) }" @click="$router.push('/wishes/'+w.id)">
        <h3>{{ w.title || '（无标题）' }}</h3>
        <p>{{ w.note }}</p>
        <span class="tag">{{ w.status }} · {{ w.data_quality }}</span>
        <span v-if="w.dep_broken" class="dep-badge broken">⚠ 依赖破裂 · 前置 #{{ w.depends_on }}</span>
        <span v-else-if="dim(w)" class="dep-badge">⛓ 前置 #{{ w.depends_on }} 未核销</span>
      </article>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const rows = ref([])
// 灰态：门禁关闭（前置未核销）且本人尚未持锁
const dim = (w) => w.dep_blocked && (w.status === 'open' || w.status === 'released')
onMounted(async () => { rows.value = await api('/wishes') })
</script>
