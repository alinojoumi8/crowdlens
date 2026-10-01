export function isProposalAcceptable(proposal) {
  return proposal?.state === 'ready' && typeof proposal.proposal_digest === 'string' &&
    proposal.proposal_digest.length > 0 && Array.isArray(proposal.findings) &&
    !proposal.findings.some(finding => finding.blocking)
}
