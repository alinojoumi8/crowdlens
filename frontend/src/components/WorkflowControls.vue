<template>
  <section class="workflow-controls" aria-label="Workflow allowance">
    <template v-if="authorize">
      <p>Provider: <strong>{{ configuration?.provider || 'Loading' }}</strong> · Model: <strong>{{ configuration?.model || 'Loading' }}</strong></p>
      <p>Authorize generation for: {{ inputDescription || 'Select the fictional input and describe the scenario first.' }}</p>
      <div class="allowance-inputs">
        <label>Maximum requests <input v-model.number="maxRequests" type="number" min="1" max="100000" /></label>
        <label>Maximum minutes <input v-model.number="maxMinutes" type="number" min="1" max="1440" /></label>
        <button :aria-describedby="authorizationHelpId" :disabled="busy || !inputDescription || !inputFingerprint || !configuration?.controls_available || !configuration?.configured || !!configuration?.authorization_blocker || !!workflowId" @click="confirmAuthorization">Authorize this workflow</button>
      </div>
      <p :id="authorizationHelpId" role="status">{{ authorizationHelp }}</p>
      <p>These are total limits across all generation stages and retries. Authorization may incur provider charges. Token usage and unknown attempts will be recorded; a request limit is not a monetary ceiling.</p>
    </template>
    <template v-if="status">
      <p><strong>{{ status.state }}</strong> · {{ status.admitted }}/{{ status.max_requests }} requests · {{ status.in_flight }} in flight or delivery unknown · {{ Math.round(status.elapsed_seconds) }} seconds elapsed</p>
      <p v-if="status.admission_closed" role="status">New calls are blocked: {{ status.reason }}. Partial output is retained. Recovery requires an explicit allowance authorization and a manual action.</p>
      <div v-if="status.admission_closed" class="allowance-inputs">
        <p>Renew for {{ status.provider }} · {{ status.model }}. Existing output is retained; renewal does not start or retry any generation.</p>
        <label>Total request ceiling <input v-model.number="renewRequests" type="number" :min="status.admitted + 1" max="100000" /></label>
        <label>Minutes from renewal <input v-model.number="renewMinutes" type="number" min="1" max="1440" /></label>
        <label v-if="status.in_flight"><input v-model="acknowledgeUnknown" type="checkbox" /> I acknowledge that outstanding requests may still finish and be billed.</label>
        <button :disabled="busy || renewRequests <= status.admitted || (status.in_flight > 0 && !acknowledgeUnknown)" @click="renew">Renew workflow allowance</button>
        <p>These totals include {{ status.admitted }} requests already used. Renewal may incur provider charges; the request ceiling is not a monetary ceiling.</p>
      </div>
      <button class="workflow-stop" :disabled="busy || status.state === 'stopped' || status.state === 'runtime_limit'" @click="stop">Stop workflow</button>
      <p>Stop blocks new calls. In-flight provider requests may still finish and be billed.</p>
    </template>
    <p v-else-if="!authorize && resource">No workflow allowance is attached. Viewing artifacts does not authorize generation.</p>
    <p v-if="error" role="alert">{{ error }}</p>
  </section>
</template>

<script setup>
import { ref, computed, useId, watch, onMounted, onUnmounted } from 'vue'
import { getExecutionConfiguration, authorizeWorkflow, resolveWorkflow, getWorkflow, stopWorkflow, reauthorizeWorkflow } from '../api/execution'
const props = defineProps({ authorize: Boolean, inputDescription: String, inputFingerprint: String, resource: String, pendingId: String })
const authorizationHelpId = useId()
const emit = defineEmits(['authorized', 'stopped'])
const configuration = ref(null), status = ref(null), workflowId = ref(null), error = ref(''), busy = ref(false)
const maxRequests = ref(60), maxMinutes = ref(30)
const renewRequests = ref(60), renewMinutes = ref(30), acknowledgeUnknown = ref(false)
let renewalKey = crypto.randomUUID()
let timer, generation = 0, authorizationKey = crypto.randomUUID()
const readableError = code => ({
  secondary_provider_allowance_unsupported: 'Authorization is blocked because optional Jev provider modes are enabled. Turn off JEV_INTERVIEW_MODE, JEV_RERANK_MODE and JEV_EVIDENCE_MODE in the server configuration and restart the server.',
  remote_embedding_allowance_unsupported: 'Authorization requires local Ollama embeddings. Configure the embedding provider and address on the server, then restart it.',
  provider_identity_changed: 'The AI provider changed. Refresh the page and review the current provider before authorizing.'
}[code] || code)
const errorMessage = exc => readableError(exc.response?.data?.error || exc.message)
const authorizationHelp = computed(() => {
  if (busy.value) return 'Submitting your request…'
  if (workflowId.value) return 'Workflow authorized.'
  if (!configuration.value) return error.value ? 'Provider settings could not be loaded. Try refreshing the page.' : 'Loading provider settings…'
  if (!configuration.value.controls_available || !configuration.value.configured) return 'Authorization is unavailable until the AI provider and workflow controls are configured.'
  if (configuration.value.authorization_blocker) return readableError(configuration.value.authorization_blocker)
  if (!props.inputDescription) return 'Add sources and describe your scenario before authorizing.'
  if (!props.inputFingerprint) return 'Preparing your sources for authorization…'
  return 'Review the provider and limits, then authorize this workflow.'
})
const refresh = async () => {
  const token = generation
  try {
    if (!workflowId.value) {
      if (props.pendingId) workflowId.value = props.pendingId
      else if (props.resource) {
        const response = await resolveWorkflow(props.resource)
        if (token !== generation) return
        workflowId.value = response.data.workflow_id
      }
    }
    if (workflowId.value) {
      const response = await getWorkflow(workflowId.value)
      if (token !== generation) return
      if (!status.value?.admission_closed && response.data.admission_closed) renewRequests.value = Math.max(response.data.max_requests, response.data.admitted + 1)
      status.value = response.data
    }
  } catch (exc) { if (token === generation) error.value = errorMessage(exc) }
}
const confirmAuthorization = async () => {
  if (busy.value || workflowId.value) return
  const token = generation
  const terms = { ...configuration.value,
      request_key: authorizationKey, input_description: props.inputDescription, input_fingerprint:props.inputFingerprint,
      max_requests: maxRequests.value, max_seconds: maxMinutes.value * 60, confirmed: true }
  busy.value = true; error.value = ''
  try {
    const response = await authorizeWorkflow(terms)
    if (token !== generation) return
    workflowId.value = response.data.workflow_id; status.value = response.data
    emit('authorized', workflowId.value)
  } catch (exc) { if(token === generation) error.value = errorMessage(exc) } finally { busy.value = false }
}
const renew = async () => {
  if (busy.value || !status.value?.admission_closed) return
  const token = ++generation, id = workflowId.value
  busy.value = true; error.value = ''
  try {
    const response = await reauthorizeWorkflow(id, {
      max_requests: renewRequests.value, max_seconds: renewMinutes.value * 60,
      confirmed: true, acknowledge_unknown: acknowledgeUnknown.value, request_key: renewalKey
    })
    if (token !== generation) return
    status.value = response.data; renewalKey = crypto.randomUUID(); acknowledgeUnknown.value = false
  } catch (exc) { if (token === generation) error.value = errorMessage(exc) }
  finally { busy.value = false }
}
const stop = async () => {
  const token = generation, id = workflowId.value
  busy.value = true; error.value = ''
  try { const response = await stopWorkflow(id); if(token !== generation) return; status.value = response.data; emit('stopped') }
  catch (exc) { if(token === generation) error.value = errorMessage(exc) } finally { busy.value = false }
}
watch([renewRequests, renewMinutes, acknowledgeUnknown], () => { renewalKey = crypto.randomUUID() })
watch(() => props.resource, () => { generation++; workflowId.value = null; status.value = null; renewalKey = crypto.randomUUID(); acknowledgeUnknown.value = false; refresh() })
watch(() => [props.inputDescription,props.inputFingerprint], () => {
  generation++; workflowId.value = null; status.value = null; authorizationKey = crypto.randomUUID(); emit('authorized', null)
})
onMounted(async () => {
  try { configuration.value = (await getExecutionConfiguration()).data } catch (exc) { error.value = errorMessage(exc) }
  await refresh(); timer = setInterval(refresh, 2000)
})
onUnmounted(() => { generation++; clearInterval(timer) })
</script>

<style scoped>
.workflow-controls { padding: .8rem 1.2rem; border: 1px solid #bbc6d2; background: #f6f8fb; color: #1f2a36; font: 13px/1.6 system-ui, sans-serif; overflow-wrap: anywhere; }
.allowance-inputs { display: flex; flex-wrap: wrap; gap: .8rem; align-items: end; }
.allowance-inputs label { display: grid; gap: .2rem; }
input { width: 9rem; padding: .3rem; }
button { min-height: 44px; padding: .4rem .8rem; cursor: pointer; }
button:disabled { cursor: default; opacity: .6; }
.workflow-stop { background: #772b24; border: 1px solid #772b24; color: white; }
</style>
