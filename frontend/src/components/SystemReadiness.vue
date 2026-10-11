<template>
  <section class="readiness" aria-label="System readiness">
    <h2>{{ headline }}</h2>
    <p v-if="error" role="alert">Status unavailable. Check the backend and refresh; readiness is unknown.</p>
    <template v-else-if="data">
      <p>These checks do not generate content or test inference.</p>
      <dl>
        <dt>Generation · {{ data.llm?.model || 'No model' }}</dt>
        <dd>{{ words(data.llm?.state) }} — {{ data.llm?.message }}</dd>
        <dt>Embeddings · {{ data.embedding?.model || 'No model' }}</dt>
        <dd>{{ words(data.embedding?.state) }} — {{ data.embedding?.message || data.embedding?.error }}</dd>
        <dt>Source graph / Saved data</dt>
        <dd>{{ data.neo4j?.healthy ? 'Available' : 'Unavailable' }} / {{ data.control_db?.healthy ? 'Available' : 'Unavailable' }}</dd>
        <template v-for="area in data.disk?.areas || []" :key="area.name">
          <dt>{{ words(area.name) }}</dt>
          <dd>{{ area.free_bytes == null ? 'Free space unknown' : `${(area.free_bytes / 1024**3).toFixed(1)} GiB free` }} — {{ area.message }}</dd>
        </template>
      </dl>
      <p class="hint">Checked {{ checkedAt }}. Provider and storage results are cached for up to one minute.</p>
    </template>
    <button :disabled="busy" @click="refresh">{{ busy ? 'Checking…' : 'Refresh status' }}</button>
  </section>
</template>
<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import service from '../api'
const data = ref(null), error = ref(false), busy = ref(false), checkedAt = ref('')
let active = true, timer
function schedule() { timer = setTimeout(() => { if (!active) return; if (!document.hidden) refresh(); else schedule() }, 60000) }
const words = value => String(value || 'unverified').replaceAll('_', ' ')
const headline = computed(() => error.value ? 'Readiness unknown' : !data.value ? 'Checking readiness' : ({ready:'Checks passed', warning:'Storage warning', unverified:'Readiness unverified', checking:'Checking readiness'}[data.value.readiness] || 'Needs attention'))
async function refresh() {
  if (busy.value) return
  busy.value = true
  clearTimeout(timer)
  try {
    const response = await service.get('/api/status', { timeout: 15000 })
    if (active) { data.value = response.data; error.value = false; checkedAt.value = new Date().toLocaleTimeString() }
  } catch { if (active) { error.value = true; data.value = null } }
  finally { if (active) { busy.value = false; schedule() } }
}
onMounted(refresh)
onUnmounted(() => { active = false; clearTimeout(timer) })
</script>
<style scoped>
.readiness { margin: 1rem 0 1.5rem; padding: 1rem; border: 1px solid #b9bec3; border-radius: 6px; background: #fff; }
h2 { font-size: 1.25rem; margin-bottom: .75rem; }
p, dd { line-height: 1.5; overflow-wrap: anywhere; }
dt { margin-top: .8rem; font-weight: 600; }
dd { margin: .2rem 0 0; }
.hint { margin-top: .9rem; color: #535b65; font-size: .8rem; }
button { margin-top: .8rem; padding: .6rem .8rem; min-height: 44px; background: #f3f7fa; color: #254b73; border: 1px solid #254b73; border-radius: 4px; cursor: pointer; }
button:focus-visible { outline: 3px solid #d89522; outline-offset: 3px; }
</style>
