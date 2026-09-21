<template>
  <details v-if="checks.length" class="claim-evidence">
    <summary>Source checks · {{ checks.length }} claims/passages · {{ reviewCount }} need review</summary>
    <p class="explanation">Model judgments on retrieved source excerpts, not a complete factual audit. Shadow checks do not change the report. Expand a claim to inspect its original text and source locations.</p>
    <details v-for="(check, index) in checks" :key="check.claim_id || index" class="claim">
      <summary><strong :class="check.outcome === 'supported' ? 'supported' : 'review'">{{ label(check.outcome) }}</strong> — {{ check.claim_text || 'Unreviewed passage; no reliable claim extracted' }}</summary>
      <p v-if="check.reason">Review reason: {{ check.reason }}</p>
      <p v-if="check.retrieval_limited">The source search reached its size limit. Additional documents may contain relevant context.</p>
      <p v-if="!check.sources?.length">No original source linked. This statement remains unverified.</p>
      <article v-for="source in check.sources || []" :key="source.evidence_id" class="source">
        <p><strong>{{ source.filename || source.document_id }}</strong> · page {{ source.locator?.page ?? 'not recorded' }} · chunk {{ source.locator?.chunk_index ?? source.episode_id }}</p>
        <p>{{ source.judgment ? label(source.judgment.choice) : 'Not evaluated' }}<span v-if="source.precheck"> · {{ source.precheck }}</span></p>
        <blockquote>{{ source.excerpt }}</blockquote>
        <small>Document {{ source.document_id }} · {{ source.evidence_id }} · SHA-256 {{ source.source_hash }}</small>
      </article>
    </details>
  </details>
</template>

<script setup>
import { computed } from 'vue'
const props = defineProps({ checks: { type: Array, default: () => [] } })
const reviewCount = computed(() => props.checks.filter(c => c.outcome !== 'supported').length)
const label = value => ({ supported: 'Supported by retrieved source', contradicted: 'Contradicted — review', conflicting: 'Conflicting sources — review', insufficient: 'Insufficient source support', unverified: 'Unverified — review' })[value] || 'Unverified — review'
</script>

<style scoped>
.claim-evidence { margin: 1rem 0; padding: 1rem; border: 1px solid #ccd4df; border-radius: 6px; background: #f8fafc; color: #25334a; }
summary { cursor: pointer; line-height: 1.6; overflow-wrap: anywhere; }
.explanation, small { color: #526078; }
.claim { padding: .75rem 0; border-top: 1px solid #dce2eb; }
.supported { color: #276449; } .review { color: #854b12; }
.source { margin: .75rem 0; padding: .75rem; background: white; border-left: 3px solid #9aa9bc; }
blockquote { white-space: pre-wrap; overflow-wrap: anywhere; margin: .75rem 0; line-height: 1.6; max-height: 24rem; overflow: auto; }
small { overflow-wrap: anywhere; }
</style>
