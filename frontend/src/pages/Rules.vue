<template>
  <div class="wall">
    <h1 class="serif">规则</h1>
    <ul>
      <li v-for="(v,k) in textRules" :key="k"><strong>{{ k }}</strong>：{{ v }}</li>
    </ul>
    <h3 class="serif">依赖链</h3>
    <p v-if="!edges.length" class="tag">当前没有声明依赖的愿望</p>
    <ul>
      <li v-for="e in edges" :key="e.wish_id">
        愿望 #{{ e.wish_id }} ← 前置 #{{ e.depends_on }}
        <span v-if="e.dep_broken" class="dep-badge broken">⚠ 依赖破裂</span>
        <span v-else-if="e.dep_blocked" class="dep-badge">⛓ 前置未核销（{{ e.dep_status }}）</span>
        <span v-else class="tag">已核销，可认领</span>
      </li>
    </ul>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
const rules = ref({})
const textRules = computed(() =>
  Object.fromEntries(Object.entries(rules.value).filter(([k]) => k !== 'dep_edges')))
const edges = computed(() => rules.value.dep_edges || [])
onMounted(async () => { rules.value = await api('/rules') })
</script>
