import test from 'node:test'
import assert from 'node:assert/strict'
import { isProposalAcceptable } from './evidenceProposal.js'
test('only ready proposals without structural blockers are acceptable', () => {
  for (const state of ['queued', 'running', 'failed', 'blocked', 'rejected', 'stale', 'accepted']) {
    assert.equal(isProposalAcceptable({ state, proposal_digest: 'digest', findings: [] }), false)
  }
  assert.equal(isProposalAcceptable(null), false)
  assert.equal(isProposalAcceptable({ state: 'ready', findings: [] }), false)
  assert.equal(isProposalAcceptable({ state: 'ready', proposal_digest: 'd', findings: [{ blocking: true }] }), false)
  assert.equal(isProposalAcceptable({ state: 'ready', proposal_digest: 'd', findings: [{ blocking: false }] }), true)
})
