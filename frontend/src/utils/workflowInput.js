export const sha256 = async bytes => Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)))
  .map(byte => byte.toString(16).padStart(2,'0')).join('')
export const workflowInputFingerprint = async (files, requirement, urls = []) => {
  const entries = await Promise.all(files.map(async file => ({ name:file.name, sha256:await sha256(await file.arrayBuffer()) })))
  return sha256(new TextEncoder().encode(JSON.stringify({ files:entries, requirement, urls })))
}
