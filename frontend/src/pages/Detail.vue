<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>
    <p v-if="w.depends_on" class="tag">前置 #{{ w.depends_on }}（{{ w.dep_status || '缺失' }}）</p>
    <p v-if="w.dep_blocked" class="err">不可认领：前置 #{{ w.depends_on }} 未核销</p>
    <p v-if="w.dep_broken" class="err">依赖破裂：前置 #{{ w.depends_on }} 已撤销核销；锁保持不自动释放，待前置重新核销或手动释放</p>
    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim" :disabled="w.dep_blocked">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill" :disabled="w.dep_broken">核销完成</button>
      <button v-if="w.status==='fulfilled'" class="ghost" @click="revoke">撤销核销</button>
    </div>
    <div style="margin-top:20px">
      <input v-model="dep" placeholder="前置愿望 id（留空清除依赖）" />
      <button class="ghost" @click="saveDep">保存前置</button>
    </div>
  </div>
</template>
<script setup>
import { ref, onMounted } from 'vue'
import { api } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const dep = ref('')
const err = ref('')
const CODE_TEXT = {
  dep_blocked: d => `不可认领：前置 #${d.depends_on} 未核销`,
  dep_missing: d => `前置 #${d.depends_on} 不存在`,
  dep_broken: d => `依赖破裂：前置 #${d.depends_on} 未核销，禁止核销`,
  self_dep: () => '不能自依赖',
  dep_cycle: () => '环依赖，已拒保存',
}
function showErr(e) {
  const d = e.detail
  err.value = d && d.code && CODE_TEXT[d.code] ? CODE_TEXT[d.code](d) : e.message
}
function depId() {
  if (dep.value === '' || dep.value === null) return null
  const n = Number(dep.value)
  if (!Number.isInteger(n) || n <= 0) throw new Error('前置 id 需为正整数')
  return n
}
async function load() {
  w.value = await api('/wishes/' + props.id)
  dep.value = w.value.depends_on ?? ''
}
async function claim() {
  err.value=''; try { await api('/wishes/'+props.id+'/claim',{method:'POST',body:JSON.stringify({claimer:claimer.value})}); await load() } catch(e){ showErr(e) }
}
async function release() {
  err.value=''; try { await api('/wishes/'+props.id+'/release',{method:'POST',body:'{}'}); await load() } catch(e){ showErr(e) }
}
async function fulfill() {
  err.value=''; try { await api('/wishes/'+props.id+'/fulfill',{method:'POST',body:'{}'}); await load() } catch(e){ showErr(e) }
}
async function revoke() {
  err.value=''; try { await api('/wishes/'+props.id+'/revoke',{method:'POST',body:'{}'}); await load() } catch(e){ showErr(e) }
}
async function saveDep() {
  err.value=''
  let n
  try { n = depId() } catch(e){ err.value = e.message; return }
  try { await api('/wishes/'+props.id+'/dep',{method:'PUT',body:JSON.stringify({depends_on:n})}); await load() } catch(e){ showErr(e) }
}
onMounted(load)
</script>
