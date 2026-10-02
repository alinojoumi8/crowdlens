// Current-source loopback preview only. See the Milestone 4 audit for substitutes.
// ECC_BROWSER_TOOLS points to separately installed, pinned playwright-core/axe-core.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, writeFile } from 'node:fs/promises'
const require = createRequire(`${process.env.ECC_BROWSER_TOOLS || '/tmp/crowdlens-ecc-browser-tools'}/package.json`)
const { chromium } = require('playwright-core')
const base = process.env.ECC_BROWSER_URL || 'http://127.0.0.1:18742'
assert(['127.0.0.1', 'localhost'].includes(new URL(base).hostname), 'Disposable loopback preview required')
const output = process.env.ECC_BROWSER_OUTPUT || '/tmp/crowdlens-ecc-browser-regressions'
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ executablePath: process.env.ECC_CHROME || '/usr/bin/google-chrome', headless: true, args: ['--no-sandbox'] })
const page = await browser.newPage({ viewport: { width: 375, height: 1000 } })
// No nonlocal page requests. Fonts are fulfilled empty to keep failure receipts specific to application APIs.
await page.route('**/*', route => new URL(route.request().url()).origin === base
  ? route.continue() : route.fulfill({ body: '', contentType: 'text/css' }))
const checks = []
const consoleMessages = [], networkErrors = [], pageErrors = []
page.on('console', message => { if (['warning', 'error'].includes(message.type())) consoleMessages.push({ type: message.type(), text: message.text() }) })
page.on('response', response => { if (response.status() >= 400) networkErrors.push({ url: response.url(), status: response.status() }) })
page.on('pageerror', error => pageErrors.push(error.message))
async function check(name, run) {
  try { await run(); checks.push({ name, passed: true }) }
  catch (error) { checks.push({ name, passed: false, error: error.message }) }
}
await page.goto(base)
await page.waitForSelector('.history-database .project-card')
await check('upload chooser is keyboard reachable and named', async () => {
  assert.equal(await page.getByRole('button', { name: 'Choose source files' }).count(), 1)
  await page.getByRole('button', { name: 'Choose source files' }).focus()
  const chooser = page.waitForEvent('filechooser', { timeout: 1500 })
  await page.keyboard.press('Enter')
  await (await chooser).setFiles([])
})
await check('simulation prompt and website fields have explicit names', async () => {
  assert.equal(await page.getByLabel('Simulation prompt', { exact: true }).count(), 1)
  assert.equal(await page.getByLabel('Website links', { exact: true }).count(), 1)
})
await check('history dialog traps focus, closes with Escape and restores trigger', async () => {
  const card = page.getByRole('button', { name: /Open simulation/ }).first()
  assert.equal(await card.count(), 1)
  await card.focus(); await page.keyboard.press('Enter')
  const dialog = page.getByRole('dialog', { name: 'Simulation details' })
  await dialog.waitFor({ timeout: 1500 })
  assert(await dialog.evaluate(el => el.contains(document.activeElement)))
  for (let index = 0; index < 12; index++) {
    await page.keyboard.press('Tab')
    assert(await dialog.evaluate(el => el.contains(document.activeElement)))
  }
  await page.keyboard.press('Escape')
  await dialog.waitFor({ state: 'detached', timeout: 1500 })
  assert.equal(await dialog.count(), 0)
  assert(await card.evaluate(el => el === document.activeElement))
})
await page.goto(base + '/report/report_synthetic')
await page.getByRole('button', { name: 'Draft with sources' }).first().waitFor()
await page.getByRole('button', { name: 'Draft with sources' }).first().click()
await page.getByText('Ready for your review', { exact: true }).waitFor()
await page.screenshot({ path: output + '/report-375.png', fullPage: true })
await check('375px report panels and header controls fit the viewport', async () => {
  const data = await page.evaluate(() => {
    const controls = [...document.querySelectorAll('.report-panel button,.app-header button')]
      .filter(el => el.getBoundingClientRect().width && !el.closest('[inert]'))
    return controls.filter(el => el.getBoundingClientRect().right > innerWidth + 1 || el.getBoundingClientRect().left < -1)
      .map(el => el.textContent.trim())
  })
  assert.deepEqual(data, [])
  const brand = await page.locator('.brand').boundingBox()
  const switcher = await page.locator('.view-switcher').boundingBox()
  assert(brand.y + brand.height <= switcher.y || switcher.x >= brand.x + brand.width, 'Header overlaps the home link')
})
await check('hidden graph panel cannot receive keyboard focus', async () => {
  assert(await page.locator('.panel-wrapper.left').evaluate(el => el.inert || getComputedStyle(el).display === 'none'))
})
await check('missing report and graph metrics explicitly remain unknown', async () => {
  assert.match(await page.locator('.report-panel').innerText(), /Quality Unknown/)
  assert.match(await page.locator('.report-panel').innerText(), /Graph Unknown/)
  assert.match(await page.locator('.report-panel').innerText(), /Graph readiness has not been established/)
})
await page.getByRole('button', { name: 'Keep original', exact: true }).click()
await page.getByText('Original retained', { exact: true }).waitFor()
await check('interrupted root report exposes manual resume controls', async () => {
  // Presentation fixture only; actual abandoned graph ownership is exercised below.
  await page.route('**/api/report/report_synthetic', async route => {
    const response = await route.fetch()
    const body = await response.json()
    body.data.status = 'interrupted'
    body.data.effective_status = 'interrupted'
    await route.fulfill({ json: body })
  })
  await page.route('**/api/report/report_synthetic/progress', async route => {
    const response = await route.fetch()
    const body = await response.json()
    body.data.status = 'interrupted'
    body.data.effective_status = 'interrupted'
    await route.fulfill({ json: body })
  })
  await page.reload()
  await page.getByRole('button', { name: 'Resume failed section', exact: true }).waitFor()
  assert(await page.getByRole('button', { name: 'Resume failed section', exact: true }).isEnabled())
  assert.match(await page.locator('.report-panel').innerText(), /interrupted/i)
  await page.unroute('**/api/report/report_synthetic')
  await page.unroute('**/api/report/report_synthetic/progress')
})
const abandoned = (await (await page.request.post(base + '/__synthetic/abandon-task')).json()).data
await page.goto(base + '/process/' + abandoned.project_id)
await page.waitForTimeout(1000)
await page.screenshot({ path: output + '/recovering-375.png', fullPage: true })
let task
const deadline = Date.now() + 42000
do {
  task = (await (await page.request.get(base + '/api/graph/task/' + abandoned.task_id)).json()).data
  if (task.status === 'failed') break
  await page.waitForTimeout(500)
} while (Date.now() < deadline)
await page.waitForTimeout(2200)
await check('actual abandoned owner recovers in durable API state', async () => {
  assert.equal(task.status, 'failed')
  assert.equal(task.recovery.reason, 'ownership_lease_expired')
})
await check('recovered failure is visible and has a permitted manual retry', async () => {
  const alert = page.getByRole('alert')
  assert.match(await alert.innerText({ timeout: 1000 }), /ownership.*expired|ownership_lease_expired/i)
  await page.getByRole('button', { name: 'Retry graph build', exact: true }).click({ timeout: 1000 })
  await page.getByText('Ready', { exact: true }).first().waitFor({ timeout: 10000 })
  const project = (await (await page.request.get(base + '/api/graph/project/' + abandoned.project_id)).json()).data
  assert.equal(project.status, 'graph_completed')
  assert.notEqual(project.graph_build_task_id, abandoned.task_id)
})
await page.screenshot({ path: output + '/recovery-result-375.png', fullPage: true })
await check('recovery has no uncaught browser errors', async () => assert.deepEqual(pageErrors, []))
await writeFile(output + '/results.json', JSON.stringify({ browser: browser.version(), checks, abandoned, task, consoleMessages, networkErrors, pageErrors, substitutes: ['Harness synthetic adapters', 'Interrupted report presentation intercepted; graph recovery uses actual exited owner and durable task APIs'] }, null, 2))
await browser.close()
console.log(JSON.stringify(checks, null, 2))
if (checks.some(check => !check.passed)) process.exitCode = 1
