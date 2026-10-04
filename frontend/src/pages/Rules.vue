<template>
  <div class="wall">
    <h1 class="serif">规则</h1>
    <ul>
      <li v-for="(v,k) in texts" :key="k"><strong>{{ k }}</strong>：{{ v }}</li>
    </ul>
    <h3 class="serif">当前依赖边</h3>
    <p v-if="!edges.length" class="tag">暂无依赖</p>
    <ul>
      <li v-for="e in edges" :key="e.wish">
        愿望 #{{ e.wish }} → 前置 #{{ e.depends_on }} · {{ STATE[e.state] || e.state }}
      </li>
    </ul>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const STATE = { blocked: '等前置（灰态不可领）', broken: '依赖破裂（锁保持）', ok: '前置已核销（可认领）' }
const texts = ref({})
const edges = ref([])
onMounted(async () => {
  const r = await api('/rules')
  edges.value = r.dep_edges || []
  delete r.dep_edges
  texts.value = r
})
</script>
