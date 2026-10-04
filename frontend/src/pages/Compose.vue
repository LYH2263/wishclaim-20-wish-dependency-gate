<template>
  <div class="wall">
    <h1 class="serif">发愿望</h1>
    <input v-model="title" placeholder="标题" />
    <textarea v-model="note" rows="4" placeholder="备注" />
    <input v-model="dep" placeholder="前置愿望 id（可选，前置核销后本愿望才可认领）" />
    <p v-if="err" class="err">{{ err }}</p>
    <button @click="submit">发布</button>
  </div>
</template>
<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { api } from '../api'
const router = useRouter()
const title = ref('')
const note = ref('')
const dep = ref('')
const err = ref('')
async function submit() {
  err.value = ''
  let n = null
  if (dep.value !== '') {
    n = Number(dep.value)
    if (!Number.isInteger(n) || n <= 0) { err.value = '前置 id 需为正整数'; return }
  }
  try {
    const r = await api('/wishes', { method: 'POST', body: JSON.stringify({ title: title.value, note: note.value, depends_on: n }) })
    router.push('/wishes/' + r.id)
  } catch (e) {
    err.value = e.detail?.code === 'dep_missing' ? `前置 #${e.detail.depends_on} 不存在` : e.message
  }
}
</script>
