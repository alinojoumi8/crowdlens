import { expect, it } from 'vitest'
import service from '../index'
it('preserves the HTTP response while surfacing its error reason', async () => {
  const failure = Object.assign(new Error('Request failed with status code 400'), {response:{status:400,data:{error:'invalid_document'}}})
  await expect(service.interceptors.response.handlers[0].rejected(failure)).rejects.toMatchObject({message:'invalid_document',response:{status:400}})
})
