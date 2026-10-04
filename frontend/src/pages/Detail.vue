<template>
  <div class="wall">
    <h1 class="serif">{{ w.title }}</h1>
    <p>{{ w.note }}</p>
    <p class="tag">状态 {{ w.status }} · 认领人 {{ w.claimer || '—' }}</p>
    <template v-if="w.depends_on">
      <p class="dep-note">依赖前置 #{{ w.depends_on }} · 前置状态 {{ w.dep_status }}</p>
      <p v-if="w.dep_broken" class="err">
        ⚠ 依赖破裂：前置 #{{ w.depends_on }} 的核销已被撤销；本认领保持有效，待前置重新核销后自动恢复
      </p>
      <p v-else-if="blocked" class="err">
        不可认领：前置 #{{ w.depends_on }} 尚未核销（当前 {{ w.dep_status }}）
      </p>
    </template>
    <p v-if="err" class="err">{{ err }}</p>
    <input v-model="claimer" placeholder="你的名字" />
    <div style="display:flex;gap:8px;flex-wrap:wrap">
      <button @click="claim" :disabled="blocked">认领锁定</button>
      <button class="ghost" @click="release">释放</button>
      <button class="ghost" @click="fulfill">核销完成</button>
      <button v-if="w.status === 'fulfilled'" class="ghost" @click="unfulfill">撤销核销</button>
    </div>
    <h3 class="serif">依赖设置</h3>
    <input v-model="depEdit" placeholder="前置愿望 ID（留空清除）" />
    <button class="ghost" @click="saveDep">保存依赖</button>
  </div>
</template>
<script setup>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
const props = defineProps({ id: String })
const w = ref({})
const claimer = ref('访客')
const depEdit = ref('')
const err = ref('')
// 门禁关闭且本人未持锁时禁止认领（与墙卡灰态同口径，钉同一前置 id）
const blocked = computed(() => w.value.dep_blocked && (w.value.status === 'open' || w.value.status === 'released'))
async function load() {
  w.value = await api('/wishes/' + props.id)
  depEdit.value = w.value.depends_on ?? ''
}
async function run(path, body) {
  err.value = ''
  try { await api(path, { method: 'POST', body: JSON.stringify(body || {}) }); await load() }
  catch (e) { err.value = e.message }
}
const claim = () => run('/wishes/' + props.id + '/claim', { claimer: claimer.value })
const release = () => run('/wishes/' + props.id + '/release')
const fulfill = () => run('/wishes/' + props.id + '/fulfill')
const unfulfill = () => run('/wishes/' + props.id + '/unfulfill')
async function saveDep() {
  err.value = ''
  const dep = depEdit.value === '' || depEdit.value == null ? null : Number(depEdit.value)
  try {
    await api('/wishes/' + props.id, { method: 'PATCH', body: JSON.stringify({ depends_on: dep }) })
    await load()
  } catch (e) { err.value = e.message }
}
onMounted(load)
</script>
