import service from './index'
export const getExecutionConfiguration = () => service.get('/api/execution/configuration')
export const authorizeWorkflow = data => service.post('/api/execution/authorize', data)
export const resolveWorkflow = resource => service.get('/api/execution/resolve', { params: { resource } })
export const getWorkflow = id => service.get(`/api/execution/${id}`)
export const stopWorkflow = id => service.post(`/api/execution/${id}/stop`, {})

export const reauthorizeWorkflow = (id, data) => service.post(`/api/execution/${id}/reauthorize`, data)
