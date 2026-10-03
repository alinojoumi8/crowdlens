import { shallowMount } from '@vue/test-utils'
import { afterEach, expect, it } from 'vitest'
import GraphPanel from './GraphPanel.vue'

let wrapper
afterEach(() => wrapper?.unmount())

it('does not infer memory work from the simulation running flag', async () => {
  wrapper = shallowMount(GraphPanel, {
    props: { graphData: { nodes: [], edges: [] }, currentPhase: 3, isSimulating: true },
  })
  expect(wrapper.get('.graph-building-hint').text()).toContain('Simulation running')
  expect(wrapper.text()).not.toContain('memory updating')
  await wrapper.setProps({ isSimulating: false })
  expect(wrapper.get('.finished-hint').text()).toContain('Simulation activity ended')
  expect(wrapper.text()).not.toContain('still being processed')
})
