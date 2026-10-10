<template>
  <div v-if="summary" class="activity-accounting" role="status" aria-label="Activity accounting">
    <p>{{ summary.model_actions }} model actions · {{ summary.unique_posts }} unique posts ({{ summary.initial_posts }} initial, {{ summary.scheduled_posts }} scheduled) · {{ summary.logged_entries }} logged entries · {{ summary.unknown_origin_actions }} unknown-origin actions</p>
    <p v-if="summary.model_written_actions !== undefined">Successful model activity: {{ summary.model_written_actions }} written posts/comments · {{ summary.model_reactions }} other actions (including likes). {{ summary.model_noops }} no-ops · {{ summary.model_failed_actions }} failed actions.</p>
    <p v-if="summary.scheduled_events !== undefined">{{ summary.scheduled_posts }} scheduled posts and {{ summary.scheduled_events }} scheduled-event records are separate log entries for planned inputs, not additional model responses. Logged entries include duplicates; unique posts and model actions are deduplicated. Lifecycle and round markers are excluded.</p>
  </div>
</template>
<script setup>
defineProps({ summary: { type: Object, default: null } })
</script>
<style scoped>
.activity-accounting { padding: 8px 16px; font-size: 12px; color: #374151; }
p { margin: 4px 0; }
</style>
