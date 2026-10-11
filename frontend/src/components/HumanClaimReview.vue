<template>
  <details class="human-review" open>
    <summary>Record your review</summary>
    <p>Your judgments apply to this saved proposal and its source excerpts. Saving a review keeps the report and model checks unchanged. Reviewer names are self-reported.</p>
    <p v-if="error" role="alert">{{ error }}</p>
    <p v-if="notice" role="status">{{ notice }}</p>
    <div v-if="data" class="review-controls">
      <label>Reviewer name
        <input v-model="reviewerName" maxlength="120" :disabled="busy || !!form" placeholder="Name or consistent reviewer ID" />
      </label>
      <button v-if="!form" :disabled="busy || !reviewerName.trim()" @click="openReview(reviewerName)">Open review</button>
      <button v-if="form" :disabled="busy" @click="closeReview">Close review</button>
      <button :disabled="busy" @click="download">Export packet and reviews</button>
    </div>
    <ul v-if="data?.reviews.length" aria-label="Saved reviewers">
      <li v-for="entry in data.reviews" :key="entry.form.reviewer_id">
        <button :disabled="busy || !!form" @click="openReview(entry.form.reviewer_id)">{{ entry.form.reviewer_id }} · version {{ entry.version }}</button>
        <span> {{ new Date(entry.form.reviewed_at).toLocaleString() }}</span>
      </li>
    </ul>
    <form v-if="form" @submit.prevent="save">
      <p>Editing {{ form.reviewer_id }} · {{ version ? `saved version ${version}` : 'new review' }}</p>
      <label>Reviewer role
        <select v-model="form.reviewer_kind" :disabled="busy"><option value="human">Human reviewer</option><option value="expert_human">Expert human reviewer</option></select>
      </label>
      <div class="time-controls">
        <button type="button" :disabled="busy" @click="toggleTimer">{{ timing ? 'Pause review timer' : 'Start review timer' }}</button>
        <span>Measured review time: {{ form.review_seconds == null ? 'not measured' : `${form.review_seconds.toFixed(1)} seconds` }}{{ timing ? ' · running' : '' }}</span>
      </div>
      <p class="hint">The timer starts only when you choose it and pauses when this window loses focus. Saving also pauses it.</p>
      <fieldset v-for="(claim, index) in form.claims" :key="claim.claim_id" :disabled="busy">
        <legend>Claim {{ index + 1 }} · {{ claim.claim_id }}</legend>
        <p>{{ data.packet.claims[index].text }}</p>
        <p class="hint">Citations: {{ data.packet.claims[index].citation_ids?.join(', ') || 'See linked premises' }}</p>
        <label>Source support
          <select v-model="claim.support"><option :value="null">Unassessed</option><option value="supported">Supported</option><option value="unsupported">Unsupported</option><option value="ambiguous">Ambiguous</option><option value="conflicting">Conflicting</option></select>
        </label>
        <label>Attribution is correct
          <select v-model="claim.attribution_correct"><option :value="null">Unassessed</option><option :value="true">Yes</option><option :value="false">No</option></select>
        </label>
        <label>Citations support the claim
          <select v-model="claim.citation_support_correct"><option :value="null">Unassessed</option><option :value="true">Yes</option><option :value="false">No</option></select>
        </label>
        <label>Reason and source reference
          <textarea v-model="claim.rationale" maxlength="8000" :required="hasLabel(claim)" placeholder="Explain the judgment and identify the source or page." />
        </label>
      </fieldset>
      <fieldset :disabled="busy">
        <legend>Omissions and conflicts</legend>
        <label><input v-model="assessOmissions" type="checkbox" /> I assessed which reference facts should be included</label>
        <template v-if="assessOmissions">
          <div v-for="fact in facts" :key="fact.fact_id" class="reference-fact">
            <label>Reference fact and source<textarea v-model="fact.text" required maxlength="8000" /></label>
            <label><input v-model="fact.omitted" type="checkbox" /> Missing from the proposal</label>
            <button type="button" @click="facts = facts.filter(f => f.fact_id !== fact.fact_id)">Remove fact</button>
          </div>
          <button type="button" @click="facts.push({fact_id: cryptoId(), text:'', omitted:false})">Add reference fact</button>
          <p class="hint">An empty assessed list records zero reference facts; it does not establish completeness.</p>
        </template>
        <label>Conflicting evidence is handled
          <select v-model="form.conflicts_handled"><option :value="null">Unassessed</option><option :value="true">Yes</option><option :value="false">No</option></select>
        </label>
        <label>Review notes<textarea v-model="form.notes" maxlength="16000" /></label>
      </fieldset>
      <button type="submit" :disabled="busy">{{ busy ? 'Saving…' : 'Save review' }}</button>
      <p class="hint">Partial reviews are welcome. Empty fields remain unassessed; each save retains the previous version.</p>
    </form>
    <section v-if="data?.assessment.disagreements.length" aria-label="Reviewer disagreements">
      <h5>Reviewer disagreements</h5>
      <ul><li v-for="row in data.assessment.disagreements" :key="`${row.claim_id}:${row.field}`">{{ row.claim_id }} · {{ words(row.field) }}: {{ row.judgments.map(j => `${j.reviewer_id}: ${j.value}`).join('; ') }}</li></ul>
      <p>These judgments remain separate until people resolve them.</p>
    </section>
    <details v-if="data?.history.length"><summary>Saved review history · {{ data.history.length }} versions</summary>
      <ul><li v-for="row in data.history" :key="`${row.reviewer_id}:${row.version}`">{{ row.reviewer_id }} · version {{ row.version }} · {{ new Date(row.reviewed_at).toLocaleString() }}</li></ul>
    </details>
  </details>
</template>

<script setup>
import { onUnmounted, ref, watch } from 'vue'
import { getHumanReviews, saveHumanReview, exportHumanReviews } from '../api/humanReviews'
const props = defineProps({ reportId: String, proposalId: String, proposalDigest: String })
const data = ref(null), form = ref(null), busy = ref(false), error = ref(''), notice = ref('')
const reviewerName = ref(''), version = ref(0), facts = ref([]), assessOmissions = ref(false), timing = ref(false)
let generation = 0, started = null, interval = null
const words = value => String(value).replaceAll('_', ' ')
const cryptoId = () => `fact_${crypto.randomUUID()}`
const hasLabel = claim => ['support', 'attribution_correct', 'citation_support_correct'].some(k => claim[k] != null)
function tick() {
  if (started != null && form.value) {
    const current = performance.now()
    form.value.review_seconds = (form.value.review_seconds ?? 0) + (current - started) / 1000
    started = current
  }
}
function pause() { tick(); started = null; timing.value = false; clearInterval(interval); interval = null }
function toggleTimer() { if (timing.value) pause(); else { started = performance.now(); timing.value = true; interval = setInterval(tick, 250) } }
const visibility = () => { if (document.hidden) pause() }
window.addEventListener('blur', pause)
document.addEventListener('visibilitychange', visibility)
function openReview(name) {
  pause(); reviewerName.value = name.trim(); error.value = ''; notice.value = ''
  const saved = data.value.reviews.find(row => row.form.reviewer_id === reviewerName.value)
  form.value = JSON.parse(JSON.stringify(saved?.form || data.value.blank_form))
  form.value.reviewer_id = reviewerName.value; form.value.reviewer_kind ||= 'human'
  version.value = saved?.version || 0
  assessOmissions.value = form.value.reference_facts != null
  facts.value = (form.value.reference_facts || []).map(f => ({ ...f, omitted: form.value.omitted_reference_fact_ids.includes(f.fact_id) }))
}
function closeReview() { pause(); form.value = null; notice.value = 'Review closed. Only saved changes are retained.' }
async function load() {
  const token = ++generation
  pause(); data.value = null; form.value = null; busy.value = true; error.value = ''; notice.value = ''
  try { const response = await getHumanReviews(props.reportId, props.proposalId); if (token === generation) data.value = response.data }
  catch (exc) { if (token === generation) error.value = words(exc.message) }
  finally { if (token === generation) busy.value = false }
}
async function save() {
  if (busy.value || !form.value) return
  pause(); const token = generation; busy.value = true; error.value = ''; notice.value = ''
  const payload = JSON.parse(JSON.stringify(form.value))
  payload.reference_facts = assessOmissions.value ? facts.value.map(({ fact_id, text }) => ({fact_id, text})) : null
  payload.omitted_reference_fact_ids = assessOmissions.value ? facts.value.filter(f => f.omitted).map(f => f.fact_id) : null
  try {
    const response = await saveHumanReview(props.reportId, props.proposalId, payload, version.value)
    if (token !== generation) return
    data.value = response.data; openReview(payload.reviewer_id); notice.value = 'Review saved. Unassessed fields remain unassessed.'
  } catch (exc) {
    if (token === generation) error.value = exc.message === 'review_version_conflict'
      ? 'Another edit was saved first. Copy your unsaved notes, close this review and reload the page before editing again.'
      : words(exc.message)
  } finally { if (token === generation) busy.value = false }
}
async function download() {
  const token = generation; busy.value = true; error.value = ''
  try {
    const blob = await exportHumanReviews(props.reportId, props.proposalId)
    if (token !== generation) return
    const url = URL.createObjectURL(blob), link = document.createElement('a')
    link.href = url; link.download = `review-${props.proposalId}.zip`; link.click()
    setTimeout(() => URL.revokeObjectURL(url), 1000)
    notice.value = 'Export contains saved reviews only, plus the frozen source packet and version history.'
  } catch (exc) { if (token === generation) error.value = words(exc.message) }
  finally { if (token === generation) busy.value = false }
}
watch(() => [props.reportId, props.proposalId, props.proposalDigest], load, { immediate: true })
onUnmounted(() => { generation++; pause(); window.removeEventListener('blur', pause); document.removeEventListener('visibilitychange', visibility) })
</script>

<style scoped>
.human-review { margin: 1.2rem 0; padding: 1rem; border: 1px solid #9caec1; border-radius: 6px; background: #fff; }
summary { cursor: pointer; font-weight: 600; min-height: 40px; }
p { line-height: 1.6; }
label { display: flex; flex-direction: column; gap: .35rem; margin: .75rem 0; }
label:has(input[type=checkbox]) { flex-direction: row; align-items: center; }
input:not([type=checkbox]), select, textarea { font: inherit; padding: .6rem; max-width: 100%; box-sizing: border-box; border: 1px solid #a9b6c5; border-radius: 4px; }
textarea { width: 100%; min-height: 5rem; }
fieldset { border: 1px solid #d6e0eb; border-radius: 4px; margin: 1rem 0; min-width: 0; }
legend { font-weight: 600; }
button { font: inherit; min-height: 44px; padding: .6rem .85rem; border-radius: 4px; border: 1px solid #254b73; color: #254b73; background: #f3f7fa; cursor: pointer; }
button:disabled { opacity: .5; cursor: not-allowed; }
button:focus-visible, input:focus-visible, select:focus-visible, textarea:focus-visible, summary:focus-visible { outline: 3px solid #d89522; outline-offset: 3px; }
.review-controls, .time-controls { display: flex; gap: .75rem; align-items: center; flex-wrap: wrap; }
.hint { color: #52647a; font-size: 13px; }
[role=alert] { color: #873e1c; }
.reference-fact { border-top: 1px solid #d6e0eb; padding: .5rem 0; }
</style>
