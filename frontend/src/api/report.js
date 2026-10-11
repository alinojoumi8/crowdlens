import service, { requestWithRetry } from './index'

/**
 * Start report generation
 * @param {Object} data - { simulation_id, force_regenerate?, request_key? }
 */
export const generateReport = (data) => {
  // One logical request survives transport retries. A new manual invocation gets a new key.
  const payload = { ...data, request_key: data.request_key ?? crypto.randomUUID() }
  return requestWithRetry(() => service.post('/api/report/generate', payload), 3, 1000)
}

/**
 * Get report generation status
 * @param {Object} data - { task_id?, simulation_id? }
 */
export const getReportStatus = (data) => {
  return service.post('/api/report/generate/status', data)
}

/**
 * Get persisted report progress by report id
 * @param {string} reportId
 */
export const getReportProgress = (reportId) => {
  return service.get(`/api/report/${reportId}/progress`)
}

/**
 * Get Agent log (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start from which line
 */
export const getAgentLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/agent-log`, { params: { from_line: fromLine } })
}

/**
 * Get console log (incremental)
 * @param {string} reportId
 * @param {number} fromLine - Start from which line
 */
export const getConsoleLog = (reportId, fromLine = 0) => {
  return service.get(`/api/report/${reportId}/console-log`, { params: { from_line: fromLine } })
}

/**
 * Get report details
 * @param {string} reportId
 */
export const getReport = (reportId) => {
  return service.get(`/api/report/${reportId}`)
}

/**
 * Regenerate one report section
 * @param {string} reportId
 * @param {number} sectionIndex
 * @param {Object} data - { disable_interviews?, strict_antirepetition? }
 */
export const regenerateReportSection = (reportId, sectionIndex, data = {}) => {
  return service.post(`/api/report/${reportId}/section/${sectionIndex}/regenerate`, data)
}

/**
 * Resume a failed or partial report from the first missing section
 * @param {string} reportId
 * @param {Object} data - { disable_interviews?, strict_antirepetition? }
 */
export const resumeReport = (reportId, data = {}) => {
  return service.post(`/api/report/${reportId}/resume`, data)
}

/**
 * Chat with Report Agent
 * @param {Object} data - { simulation_id, message, chat_history? }
 */
export const chatWithReport = (data) => {
  return service.post('/api/report/chat', data)
}

// Explicit retries preserve the creation key and the displayed proposal digest.
const proposalPath = (reportId, proposalId) => `/api/report/${encodeURIComponent(reportId)}/evidence-proposals${proposalId ? `/${encodeURIComponent(proposalId)}` : ''}`
export const createEvidenceProposal = (reportId, data) => service.post(proposalPath(reportId), data)
export const getEvidenceProposal = (reportId, proposalId) => service.get(proposalPath(reportId, proposalId))
export const listEvidenceProposals = reportId => service.get(proposalPath(reportId))
export const acceptEvidenceProposal = (reportId, proposalId, proposalDigest) => service.post(`${proposalPath(reportId, proposalId)}/accept`, { proposal_digest: proposalDigest })
export const rejectEvidenceProposal = (reportId, proposalId) => service.post(`${proposalPath(reportId, proposalId)}/reject`, {})
export const getReportRevisions = reportId => service.get(`/api/report/${encodeURIComponent(reportId)}/revisions`)
