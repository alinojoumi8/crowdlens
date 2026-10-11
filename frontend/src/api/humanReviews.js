import service from './index'

const path = (reportId, proposalId) => `/api/report/${encodeURIComponent(reportId)}/evidence-proposals/${encodeURIComponent(proposalId)}/human-reviews`
export const getHumanReviews = (reportId, proposalId) => service.get(path(reportId, proposalId))
export const saveHumanReview = (reportId, proposalId, form, expectedVersion) => service.post(path(reportId, proposalId), { form, expected_version: expectedVersion })
export const exportHumanReviews = (reportId, proposalId) => service.get(`${path(reportId, proposalId)}/export`, { responseType: 'blob' })
