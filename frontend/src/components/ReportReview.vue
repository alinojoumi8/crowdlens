<template>
  <section v-if="assessment" class="current-review" aria-label="Current report review">
    <strong>{{ assessment.requires_review ? 'Current assessment · Needs review' : 'Current assessment · Limited checks' }}</strong>
    <p>Saved status: {{ assessment.saved_status }}. This assessment does not change the saved report.</p>
    <ul v-if="assessment.issues?.length">
      <li v-for="(issue, index) in assessment.issues" :key="index">
        <strong>{{ issue.message }}</strong>
        <p v-if="issue.claim_text" class="passage">{{ issue.claim_text }}</p>
        <p v-if="issue.origin === 'proposal_model_audit'">Unresolved model audit finding · {{ issue.claim_id }}. Requires source review; not an independent truth judgment.</p>
        <ul v-if="issue.evidence?.length">
          <li v-for="row in issue.evidence" :key="row.reference">
            Recorded: {{ row.reference }} · {{ row.agent_name }} · Round {{ row.round_num }} · {{ row.origin }}
          </li>
        </ul>
      </li>
    </ul>
    <details>
      <summary>Coverage and limits</summary>
      <p>{{ assessment.coverage?.matched_assertions || 0 }} explicit assertions checked. No general truth or completeness certification.</p>
      <ul><li v-for="limit in assessment.limitations" :key="limit">{{ limit }}</li></ul>
    </details>
  </section>
</template>

<script setup>
defineProps({ assessment: { type: Object, default: null } })
</script>

<style scoped>
.current-review { border: 1px solid #9a6700; background: #fff8e8; color: #382800; padding: 16px; margin: 20px 0; border-radius: 8px; overflow-wrap: anywhere; }
.current-review p { margin: 8px 0; }
.current-review li { margin: 10px 0; }
.passage { border-left: 3px solid #9a6700; padding-left: 10px; white-space: pre-wrap; }
summary { cursor: pointer; }
</style>
