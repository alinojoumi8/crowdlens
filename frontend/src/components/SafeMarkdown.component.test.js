import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SafeMarkdown from './SafeMarkdown.vue'


describe('SafeMarkdown', () => {
  it('mounts attacker-controlled HTML as inert text while retaining Markdown', () => {
    const wrapper = mount(SafeMarkdown, {
      props: {
        content: '<img src=x onerror="globalThis.pwned=true"> **trusted formatting**',
      },
    })

    expect(wrapper.find('img').exists()).toBe(false)
    expect(wrapper.text()).toContain('<img src=x onerror="globalThis.pwned=true">')
    expect(wrapper.find('strong').text()).toBe('trusted formatting')
    expect(globalThis.pwned).toBeUndefined()
  })
})

it.each([
  '<svg><animate onbegin="globalThis.pwned=true"/></svg>',
  '<iframe srcdoc="<script>globalThis.pwned=true</script>"></iframe>',
  '<math><mtext><img src=x onerror=alert(1)></mtext></math>',
  '[click](javascript:alert(1)) ![track](https://attacker.example/pixel)',
  '&lt;img src=x onerror=alert(1)&gt; <script>location="https://attacker.example"</script>',
  '```html\n</code><img src=x onerror=alert(1)>\n```',
  { response: { answer: '<img src=x onerror=alert(1)>' } }
])('keeps hostile generated output inert: %s', content => {
  const wrapper = mount(SafeMarkdown, { props: { content } })
  expect(wrapper.find('script,iframe,img,svg,math,object,a').exists()).toBe(false)
  expect(wrapper.findAll('*').some(node => [...node.element.attributes].some(attr => /^on/i.test(attr.name)))).toBe(false)
  expect(globalThis.pwned).toBeUndefined()
})

it('bounds display work and explains that retained content is unchanged', () => {
  const wrapper = mount(SafeMarkdown, { props: { content: 'x'.repeat(200001) } })
  expect(wrapper.text()).toContain('Display limited to 200,000 characters')
  expect(wrapper.text().length).toBeLessThan(201000)
})

it('does not treat preceding blank lines as list indentation', () => {
  const wrapper = mount(SafeMarkdown, { props: { content: '\n'.repeat(50000) + '- Fictional item' } })
  expect(wrapper.find('li').attributes('data-level')).toBe('0')
})
