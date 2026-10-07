<template>
  <div class="evidence-draft">
    <p v-if="!proposal" class="draft-intro">Create a separate proposal for this section using its sources. Your original report is preserved.</p>
    <button v-if="!proposal" data-test="create-proposal" :disabled="busy" @click="create">
      {{ busy ? 'Starting draft…' : error ? 'Retry request' : 'Draft with sources' }}
    </button>
    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <section v-if="proposal" aria-label="Evidence draft review" class="review-panel">
      <div class="review-heading">
        <h4>Review proposed changes</h4>
        <span class="status" role="status" aria-live="polite">{{ statusLabel }}</span>
      </div>
      <p class="review-note">Compare the wording and inspect its sources. Saving creates a separate report that remains Needs review. Model checks can miss errors.</p>
      <ol class="review-guide" aria-label="Proposal review steps"><li>Compare the wording</li><li>Check claims against sources</li><li>Save a revision or keep the original</li></ol>
      <h5 class="review-step">1 / Compare the wording</h5>
      <div v-if="proposal.before?.section" class="comparison" aria-label="Section comparison">
        <article><h5>Original section</h5><SafeMarkdown :content="proposal.before.section" /></article>
        <article><h5>Proposed section</h5><SafeMarkdown :content="proposal.after?.section || (active ? 'Draft in progress…' : 'No proposed section available.')" /></article>
      </div>
      <details v-if="proposal.before?.summary" class="summary-comparison" open>
        <summary>Compare summaries{{ proposal.summary_unchanged ? ' · unchanged' : '' }}</summary>
        <div class="comparison" aria-label="Summary comparison">
          <article><h5>Original summary</h5><p>{{ proposal.before.summary }}</p></article>
          <article><h5>Proposed summary</h5><p>{{ proposal.after?.summary || (active ? 'Draft in progress…' : 'No proposed summary available.') }}</p></article>
        </div>
      </details>
      <ul v-if="proposal.findings?.length" class="findings" aria-label="Review findings">
        <li v-for="(finding, index) in proposal.findings" :key="index">
          <strong>{{ finding.blocking ? 'Blocks saving' : 'Review needed' }}:</strong>
          {{ words(finding.code) }}<span v-if="Number.isInteger(finding.paragraph_index)"> (paragraph {{ finding.paragraph_index + 1 }})</span><span v-if="finding.detail"> — {{ finding.detail }}</span>
        </li>
      </ul>
      <details v-if="proposal.ledger?.length" class="ledger" open>
        <summary>2 / Check claims · {{ proposal.ledger.length }} statements</summary>
        <details v-for="claim in proposal.ledger" :key="claim.claim_id" class="claim">
          <summary>{{ words(claim.kind) }} — {{ claim.text }}</summary>
          <p v-if="claim.attribution">Attributed to {{ claim.attribution }}</p>
          <p v-if="claim.premise_claim_ids?.length">Analysis based on: {{ claim.premise_claim_ids.join(', ') }}. Unresolved premises still require review.</p>
          <p v-if="!claim.checks?.length">Source support has not been independently established.</p>
          <ClaimEvidence :checks="claim.checks || []" />
          <p class="identifier">{{ claim.claim_id }} · sources: {{ claim.citation_ids?.join(', ') || 'See linked premises' }}</p>
        </details>
      </details>
      <details v-if="proposal.sources?.length" open>
        <summary>Read original sources · {{ proposal.sources.length }}</summary>
        <article v-for="source in proposal.sources" :key="source.evidence_id" class="source">
          <strong>{{ citationNumber(source.evidence_id) ? `Source ${citationNumber(source.evidence_id)} · ` : 'Retrieved context · ' }}{{ source.filename || source.document_id }}</strong>
          <span> · page {{ source.locator?.page ?? 'not recorded' }}</span>
          <span v-if="source.locator?.chunk_index != null"> · chunk {{ source.locator.chunk_index }}</span>
          <blockquote>{{ source.window }}</blockquote>
          <details><summary>Source provenance</summary><p class="identifier">{{ source.evidence_id }} · document {{ source.document_id }} · case version {{ source.case_version_id }}<br>Original SHA-256 {{ source.source_hash }}<br>Excerpt SHA-256 {{ source.window_hash }} · offsets {{ source.window_start }}–{{ source.window_end }}</p></details>
        </article>
      </details>
      <details v-if="proposal.limitations?.length" class="limitations" open>
        <summary>Search and review limits</summary>
        <ul><li v-for="(limit, index) in proposal.limitations" :key="index">{{ words(limit) }}</li></ul>
      </details>
      <p v-if="proposal.state === 'failed'" role="status">This draft could not finish. {{ words(proposal.error_code || '') }}. You can start a new proposal.</p>
      <p v-if="proposal.state === 'stale'" role="status">The report or its sources changed. Start a new proposal to review current material.</p>
      <p v-if="proposal.state === 'accepting'" role="status">Saving was interrupted. Retry to finish saving or open the revision if it was already saved.</p>
      <h5 class="review-step">3 / Decide what to keep</h5>
      <p :id="saveHelpId" class="save-help" role="status">{{ saveHelp }}</p>
      <div class="actions">
        <button :aria-describedby="saveHelpId" :disabled="busy || !canSave" @click="accept">{{ proposal.state === 'accepting' ? 'Retry saving revision' : 'Save as new revision' }}</button>
        <button v-if="canReject" class="secondary" :disabled="busy" @click="reject">Keep original</button>
        <button v-if="!active && !busy" class="secondary" @click="fresh">New proposal</button>
        <button v-if="error" class="secondary" :disabled="busy" @click="refresh()">Refresh status</button>
        <a v-if="proposal.accepted_report_id" :href="`/report/${encodeURIComponent(proposal.accepted_report_id)}`">Open saved revision</a>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, useId, onUnmounted, ref, watch } from 'vue'
import { createEvidenceProposal, getEvidenceProposal, acceptEvidenceProposal, rejectEvidenceProposal } from '../api/report'
import { isProposalAcceptable } from '../utils/evidenceProposal'
import SafeMarkdown from './SafeMarkdown.vue'
import ClaimEvidence from './ClaimEvidence.vue'
const props = defineProps({ reportId: String, sectionIndex: Number, initialProposalId: String })
const saveHelpId = useId()
const emit = defineEmits(['revision-created', 'close'])
const proposal = ref(null), busy = ref(false), error = ref('')
let generation = 0, timer = null, requestKey = null
const active = computed(() => ['queued', 'running'].includes(proposal.value?.state))
const canReject = computed(() => ['queued', 'running', 'ready', 'blocked', 'stale', 'accepting'].includes(proposal.value?.state))
const canSave = computed(() => isProposalAcceptable(proposal.value) ||
  (proposal.value?.state === 'accepting' && isProposalAcceptable({ ...proposal.value, state: 'ready' })))
const saveHelp = computed(() => {
  if (busy.value) return 'Your request is being processed. Please wait.'
  if (active.value) return 'Saving is unavailable while the draft is being prepared.'
  if (proposal.value?.state === 'accepted') return 'This proposal has been saved as a separate revision.'
  if (proposal.value?.state === 'rejected') return 'The original report was retained.'
  if (canSave.value) return 'After reviewing the wording and sources, save a separate revision. It will still need review.'
  if (proposal.value?.findings?.some(f => f.blocking)) return 'Saving is blocked by the findings above. Review them before creating a new proposal.'
  if (proposal.value?.state === 'stale') return 'Saving is unavailable because the report or sources changed. Create a new proposal.'
  if (proposal.value?.state === 'failed') return 'Saving is unavailable because the draft failed. Create a new proposal.'
  return 'Saving is unavailable until the proposal is ready and its checks allow a revision.'
})
const citationNumber = id => [...new Set((proposal.value?.ledger || []).flatMap(c => c.citation_ids || []))].indexOf(id) + 1
const words = text => String(text).replaceAll('_', ' ')
const statusLabel = computed(() => ({ queued: 'Waiting', running: words(proposal.value.phase), ready: 'Ready for your review', blocked: 'Changes required', accepted: 'Revision saved', rejected: 'Original retained', failed: 'Draft failed', stale: 'Sources changed', accepting: 'Save needs recovery' })[proposal.value?.state] || '')
const cacheKey = () => `evidence-proposal:${props.reportId}:${props.sectionIndex}`
const remember = () => { try { sessionStorage.setItem(cacheKey(), JSON.stringify({ requestKey, proposalId: proposal.value?.proposal_id })) } catch { /* private browsing may disable storage */ } }
const stop = () => { clearTimeout(timer); timer = null }
const message = err => {
  const code = err.response?.data?.error || err.message || 'Request failed'
  return ({ report_busy: 'Another operation is using this report. Retry when it finishes.', capacity: 'Two drafts are already running. Retry when one finishes.', stale_parent: 'The original report changed. Start a new proposal.', stale_sources: 'The source documents changed. Start a new proposal.', revision_deleted: 'The saved revision was deleted and cannot be restored by retrying.', source_revalidation_unavailable: 'Sources are unavailable. Your proposal is saved; retry saving when the source service is available.' })[code] || words(code)
}
function schedule(token) {
  stop()
  if (token === generation && active.value) timer = setTimeout(() => refresh(token), 1000)
}
async function refresh(token = generation) {
  if (!proposal.value?.proposal_id || token !== generation) return
  try {
    const result = await getEvidenceProposal(props.reportId, proposal.value.proposal_id)
    if (token !== generation) return
    proposal.value = result.data; error.value = ''; remember(); schedule(token)
  } catch (err) { if (token === generation) error.value = message(err) }
}
async function create() {
  if (busy.value) return
  const token = generation
  requestKey ||= crypto.randomUUID()
  remember(); busy.value = true; error.value = ''
  try {
    const result = await createEvidenceProposal(props.reportId, { section_index: props.sectionIndex, request_key: requestKey })
    if (token !== generation) return
    proposal.value = result.data; remember(); schedule(token)
  } catch (err) { if (token === generation) error.value = message(err) }
  finally { if (token === generation) busy.value = false }
}
async function accept() {
  if (busy.value || !canSave.value) return
  const token = ++generation
  stop()
  busy.value = true; error.value = ''
  try {
    const result = await acceptEvidenceProposal(props.reportId, proposal.value.proposal_id, proposal.value.proposal_digest)
    if (token !== generation) return
    proposal.value = { ...proposal.value, state: 'accepted', accepted_report_id: result.data.report_id }
    remember(); stop(); emit('revision-created', result.data.report_id)
  } catch (err) {
    if (token === generation) {
      error.value = message(err)
      const code = err.response?.data?.error
      if (['stale_parent', 'stale_sources'].includes(code)) proposal.value = { ...proposal.value, state: 'stale' }
      if (err.response?.status === 410) proposal.value = { ...proposal.value, state: 'failed', error_code: 'revision_deleted' }
    }
  }
  finally { if (token === generation) { busy.value = false; schedule(token) } }
}
async function reject() {
  if (busy.value) return
  const token = ++generation
  stop()
  busy.value = true; error.value = ''
  try {
    const result = await rejectEvidenceProposal(props.reportId, proposal.value.proposal_id)
    if (token !== generation) return
    proposal.value = result.data; remember(); stop(); emit('close')
  } catch (err) { if (token === generation) error.value = message(err) }
  finally { if (token === generation) { busy.value = false; schedule(token) } }
}
function fresh() { generation++; stop(); proposal.value = null; requestKey = null; error.value = ''; remember(); create() }
watch(() => [props.reportId, props.sectionIndex, props.initialProposalId], () => {
  generation++; stop(); proposal.value = null; busy.value = false; error.value = ''; requestKey = null
  let saved = {}
  try { saved = JSON.parse(sessionStorage.getItem(cacheKey()) || '{}') } catch { /* no saved request */ }
  requestKey = saved.requestKey || null
  const identifier = props.initialProposalId || saved.proposalId
  if (identifier) { proposal.value = { proposal_id: identifier }; refresh(generation) }
}, { immediate: true })
onUnmounted(() => { generation++; stop() })
</script>

<style scoped>
.evidence-draft { margin: 1rem 0; color: #25334a; font-size: 14px; }
button { min-height: 44px; border: 1px solid #254b73; border-radius: 5px; background: #254b73; color: white; padding: .6rem .9rem; cursor: pointer; font: inherit; }
button:disabled { opacity: .5; cursor: not-allowed; }
button:focus-visible, summary:focus-visible, a:focus-visible { outline: 3px solid #d89522; outline-offset: 3px; }
.secondary { background: white; color: #254b73; }
.review-panel { border: 1px solid #cad6e2; border-radius: 8px; padding: 1.2rem; background: #f6f9fc; }
.review-heading { display: flex; align-items: baseline; gap: 1rem; justify-content: space-between; flex-wrap: wrap; }
h4 { font-size: 18px; margin: 0; } h5 { margin: 0 0 .6rem; font-size: 13px; text-transform: uppercase; letter-spacing: .05em; color: #52647a; }
.status { font-size: 12px; background: #e3ebf3; padding: .3rem .6rem; border-radius: 20px; }
.review-note { color: #52647a; line-height: 1.6; }
.comparison { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin: 1rem 0; }
.comparison article { min-width: 0; background: white; border: 1px solid #dde4ec; border-radius: 4px; padding: 1rem; overflow-wrap: anywhere; }
p, blockquote { line-height: 1.65; white-space: pre-wrap; } summary { cursor: pointer; line-height: 1.6; }
details { margin: .75rem 0; } .claim { border-top: 1px solid #d6e0eb; padding: .6rem 0; }
.source { padding: 1rem; background: white; border-left: 3px solid #8ba4bd; margin: .7rem 0; }
blockquote { margin: .6rem 0; max-height: 20rem; overflow: auto; overflow-wrap: anywhere; }
.identifier { font-size: 11px; color: #596b80; overflow-wrap: anywhere; }
.error, .findings { color: #873e1c; } .error { padding: .6rem; background: #fff4ed; }
.actions { display: flex; flex-wrap: wrap; gap: .6rem; align-items: center; margin-top: 1rem; }
.limitations { color: #52647a; } li { margin: .4rem 0; }
@media (max-width: 900px) { .comparison { grid-template-columns: 1fr; } .review-panel { padding: .8rem; } }
.review-guide { display: flex; flex-wrap: wrap; gap: .5rem 1.8rem; padding: .8rem .8rem .8rem 2rem; background: #eaf0f6; line-height: 1.5; }
.review-step { margin-top: 1.5rem; color: #25334a; }
.save-help, .draft-intro { line-height: 1.6; color: #52647a; }
.review-panel { overflow-wrap: anywhere; }
summary { min-height: 40px; }
@media (max-width: 600px) { .comparison article, .source { padding: .75rem; } .actions { align-items: stretch; } .actions button { flex: 1 1 100%; } }
</style>
