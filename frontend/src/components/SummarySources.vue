<template>
  <details v-if="passages.length" class="summary-sources">
    <summary>Sources for revised summary passages</summary>
    <p>These links cover the revised passages only. AI checks may come from an earlier revision and still require human verification.</p>
    <article v-for="(passage, passageIndex) in passages" :key="passageIndex">
      <p>{{ passage.text }}</p>
      <nav aria-label="Revised summary sources">
        <a v-for="(source, index) in passage.sources" :key="source.evidence_id" :href="`#${anchor(passageIndex, index)}`" @click.prevent="reveal($event, passageIndex, index)">
          Source {{ index + 1 }} · {{ source.filename || source.document_id }} · page {{ source.locator?.page ?? 'not recorded' }}<template v-if="source.locator?.page_end > source.locator?.page">–{{ source.locator.page_end }}</template>
        </a>
      </nav>
      <details v-for="(source, index) in passage.sources" :key="source.evidence_id" :id="anchor(passageIndex, index)">
        <summary>Source {{ index + 1 }} excerpt</summary>
        <blockquote tabindex="0" :aria-label="`Summary source excerpt ${index + 1}`">{{ source.window || source.excerpt }}</blockquote>
        <p class="provenance">Document {{ source.document_id }} · SHA-256 {{ source.source_hash }}</p>
      </details>
    </article>
  </details>
</template>

<script setup>
import { useId } from 'vue'
defineProps({ passages: { type: Array, default: () => [] } })
const id = useId()
const anchor = (passage, source) => `${id}-summary-${passage}-${source}`
function reveal(event, passage, source) {
  const target = event.currentTarget.ownerDocument.getElementById(anchor(passage, source))
  if (!target) return
  target.open = true
  target.querySelector('blockquote')?.focus()
}
</script>

<style scoped>
.summary-sources { margin: 12px 0 20px; padding: 12px; border: 1px solid #d3d0c8; border-radius: 6px; font-size: 14px; }
summary { cursor: pointer; padding: 8px 0; }
p, blockquote { line-height: 1.6; white-space: pre-wrap; overflow-wrap: anywhere; }
nav { display: flex; flex-wrap: wrap; gap: 12px; margin-bottom: 12px; }
a { color: #375d78; overflow-wrap: anywhere; }
blockquote { border-left: 3px solid #b0bdc5; margin: 12px 0; padding: 8px 12px; }
.provenance { font-size: 12px; }
a:focus-visible, summary:focus-visible, blockquote:focus-visible { outline: 3px solid #d89522; outline-offset: 3px; }
</style>
