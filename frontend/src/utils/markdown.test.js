import assert from 'node:assert/strict'
import { describe, it } from 'node:test'

import { renderSafeMarkdown } from './markdown.js'

describe('renderSafeMarkdown', () => {
  it('renders raw HTML and event handlers as inert text', () => {
    const rendered = renderSafeMarkdown('<img src=x onerror="globalThis.pwned=true"> **safe**')

    assert.doesNotMatch(rendered, /<img\b/i)
    assert.match(rendered, /&lt;img src=x onerror=&quot;globalThis\.pwned=true&quot;&gt;/)
    assert.match(rendered, /<strong>safe<\/strong>/)
  })

  it('escapes HTML inside code blocks while preserving Markdown formatting', () => {
    const rendered = renderSafeMarkdown('```html\n<script>alert(1)</script>\n```\n\n# Heading')

    assert.doesNotMatch(rendered, /<script\b/i)
    assert.match(rendered, /&lt;script&gt;alert\(1\)&lt;\/script&gt;/)
    assert.match(rendered, /<h2 class="md-h2">Heading<\/h2>/)
  })

  it('keeps underscores inside file names and identifiers', () => {
    const rendered = renderSafeMarkdown('See annual_report_2024.pdf and agent_id, then _really_ read it.')

    assert.match(rendered, /annual_report_2024\.pdf and agent_id,/)
    assert.match(rendered, /<em>really<\/em>/)
  })

  it('renders many unmatched underscores in linear time', () => {
    const started = performance.now()
    renderSafeMarkdown(' _x'.repeat(60000))

    assert.ok(performance.now() - started < 2000)
  })
})
