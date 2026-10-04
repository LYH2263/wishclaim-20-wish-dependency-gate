<template>
  <div class="wall">
    <h1 class="serif">发愿望</h1>
    <input v-model="title" placeholder="标题" />
    <textarea v-model="note" rows="4" placeholder="备注" />
    <input v-model="dep" placeholder="前置愿望 ID（可选，前置核销后才可认领）" />
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
  const depends_on = dep.value === '' ? null : Number(dep.value)
  try {
    const r = await api('/wishes', { method: 'POST', body: JSON.stringify({ title: title.value, note: note.value, depends_on }) })
    router.push('/wishes/' + r.id)
  } catch (e) { err.value = e.message }
}
</script>
