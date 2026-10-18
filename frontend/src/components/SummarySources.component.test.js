import { mount } from '@vue/test-utils'
import { expect, it } from 'vitest'
import SummarySources from './SummarySources.vue'

it('opens and focuses the frozen excerpt without interpreting source markup', async () => {
  const wrapper = mount(SummarySources, { attachTo: document.body, props: { passages: [{
    text: 'Alex could support the plan if it changes.', sources: [{ evidence_id: 'source:1', document_id: 'doc1',
      filename: '<img src=x onerror=alert(1)>.pdf', locator: { page: 2, page_end: 3 },
      window: '<script>untrusted</script> Conditional account.', source_hash: 'frozenhash' }]
  }] } })
  try {
    const link = wrapper.get('a')
    expect(link.text()).toContain('page 2–3')
    await link.trigger('click')
    expect(wrapper.get('article details').element.open).toBe(true)
    expect(document.activeElement).toBe(wrapper.get('blockquote').element)
    expect(wrapper.get('blockquote').text()).toContain('<script>untrusted</script>')
    expect(wrapper.find('script').exists()).toBe(false)
    expect(wrapper.find('img').exists()).toBe(false)
  } finally { wrapper.unmount() }
})

it('does not imply that unchanged summaries have new source links', () => {
  const wrapper = mount(SummarySources)
  expect(wrapper.find('details').exists()).toBe(false)
})
