// Real built UI + disposable API, with every intentional substitute in the receipt.
import assert from 'node:assert/strict'
import { createRequire } from 'node:module'
import { mkdir, writeFile, readFile } from 'node:fs/promises'
const require = createRequire(`${process.env.ECC_BROWSER_TOOLS || '/tmp/crowdlens-ecc-browser-tools'}/package.json`)
const { chromium } = require('playwright-core')
const axe = await readFile(require.resolve('axe-core/axe.min.js'), 'utf8')
const base = process.env.ECC_BROWSER_URL || 'http://127.0.0.1:18742'
assert(['127.0.0.1', 'localhost'].includes(new URL(base).hostname))
const output = process.env.ECC_BROWSER_OUTPUT || '/tmp/crowdlens-ecc-browser-workflow'
await mkdir(output, { recursive: true })
const browser = await chromium.launch({ executablePath: process.env.ECC_CHROME || '/usr/bin/google-chrome', headless: true, chromiumSandbox: true })
const cdp = await browser.newBrowserCDPSession()
const browserLaunch = await cdp.send('Browser.getBrowserCommandLine')
assert(!browserLaunch.arguments.includes('--no-sandbox'), 'Chromium sandbox must remain enabled')
const sandboxPage = await browser.newPage()
await sandboxPage.goto('chrome://sandbox')
browserLaunch.sandboxStatus = await sandboxPage.locator('body').innerText()
assert.match(browserLaunch.sandboxStatus, /Seccomp-BPF sandbox\s+Yes/)
assert.match(browserLaunch.sandboxStatus, /adequately sandboxed/)
await sandboxPage.close()
const page = await browser.newPage({ viewport: { width: 1440, height: 1000 } })
const receipt = { browser: browser.version(), browserLaunch, checks: [], snapshots: [], console: [], pageErrors: [], network: [],
  substitutes: ['Harness ontology, graph builder/storage, simulation endpoints, drafting model; no provider calls',
    'Root generation response intercepted to open an explicitly seeded report',
    'One acceptance response deliberately lost after its real HTTP publication',
    'External font CSS fulfilled empty; no external browser requests'], performance: {} }
let scenario = 'startup'
page.on('console', message => { if (['error', 'warning'].includes(message.type())) receipt.console.push({ scenario, type: message.type(), text: message.text() }) })
page.on('pageerror', error => receipt.pageErrors.push({ scenario, message: error.message }))
page.on('response', response => { if (response.url().startsWith(base + '/api/')) receipt.network.push({ scenario, method: response.request().method(), path: new URL(response.url()).pathname, status: response.status() }) })
await page.addInitScript(() => {
  window.qaVitals = { lcp: null, cls: 0, interactionDurations: [] }
  new PerformanceObserver(list => { for (const entry of list.getEntries()) window.qaVitals.lcp = entry.startTime }).observe({ type: 'largest-contentful-paint', buffered: true })
  new PerformanceObserver(list => { for (const entry of list.getEntries()) if (!entry.hadRecentInput) window.qaVitals.cls += entry.value }).observe({ type: 'layout-shift', buffered: true })
  new PerformanceObserver(list => { for (const entry of list.getEntries()) if (entry.interactionId) window.qaVitals.interactionDurations.push(entry.duration) }).observe({ type: 'event', durationThreshold: 16, buffered: true })
})
await page.route('**/*', route => new URL(route.request().url()).origin === base ? route.continue() : route.fulfill({ body: '', contentType: 'text/css' }))
async function check(name, action) {
  scenario = name
  try { await action(); receipt.checks.push({ name, passed: true }) }
  catch (error) { receipt.checks.push({ name, passed: false, error: error.message }); throw error }
}
async function snapshot(name, widths = [375, 768, 1440]) {
  for (const width of widths) {
    await page.setViewportSize({ width, height: 1000 })
    await page.waitForTimeout(400)
    await page.screenshot({ path: `${output}/${name}-${width}.png`, fullPage: true })
    if (name === 'simulation-completed') {
      const waiting = await page.locator('.waiting-state').boundingBox()
      const control = await page.locator('.control-bar').boundingBox()
      const log = await page.locator('.system-logs').boundingBox()
      assert(waiting.y >= control.y + control.height && waiting.y + waiting.height <= log.y,
        `Simulation activity overlaps controls or logs at ${width}px`)
    }
    await page.addScriptTag({ content: axe })
    const a11y = await page.evaluate(() => axe.run(document, { runOnly: { type: 'tag', values: ['wcag2a', 'wcag2aa', 'wcag21aa', 'wcag22aa'] } }))
    const layout = await page.evaluate(() => ({ width: innerWidth, scrollWidth: document.documentElement.scrollWidth,
      clipped: [...document.querySelectorAll('button,a,textarea,input,select,summary')].filter(element => {
        const r = element.getBoundingClientRect()
        return r.width > 0 && r.height > 0 && !element.closest('[inert]') && (r.left < -1 || r.right > innerWidth + 1)
      }).map(element => ({ tag: element.tagName, text: (element.innerText || element.getAttribute('aria-label') || element.getAttribute('title') || '').slice(0, 80) })) }))
    receipt.snapshots.push({ name, width, layout, a11y: a11y.violations.map(item => ({ id: item.id, impact: item.impact,
      nodes: item.nodes.map(node => ({ target: node.target, summary: node.failureSummary })) })) })
  }
}
const json = async path => (await (await page.request.get(base + path)).json())
try {
  await check('home empty input cannot submit; source picker works from keyboard', async () => {
    await page.goto(base)
    assert(await page.getByRole('button', { name: 'Explore Scenario' }).isDisabled())
    await snapshot('home')
    await page.getByRole('button', { name: 'Choose source files' }).focus()
    assert.notEqual(await page.evaluate(() => getComputedStyle(document.activeElement).outlineStyle), 'none')
    const chooser = page.waitForEvent('filechooser')
    await page.keyboard.press('Enter')
    await (await chooser).setFiles({ name: 'synthetic-record.txt', mimeType: 'text/plain', buffer: Buffer.from('Alex states that the hearing was postponed until Friday.') })
    await page.getByLabel('Simulation prompt', { exact: true }).fill('Explore the synthetic hearing record.')
    assert(await page.getByRole('button', { name: 'Explore Scenario' }).isEnabled())
  })
  await check('real upload/project/task APIs with explicit ontology and graph substitutes', async () => {
    await page.getByRole('button', { name: 'Explore Scenario' }).click()
    await page.waitForURL(url => url.pathname.startsWith('/process/proj_'))
    await page.getByText('Ready', { exact: true }).first().waitFor({ timeout: 10000 })
    const projectId = new URL(page.url()).pathname.split('/').at(-1)
    const project = (await json('/api/graph/project/' + projectId)).data
    assert.equal(project.status, 'graph_completed')
    assert.equal(project.files[0].filename, 'synthetic-record.txt')
    receipt.uploadedProject = projectId
    await snapshot('graph-ready')
    await page.getByRole('button', { name: /Enter Environment Setup/ }).click()
    await page.waitForURL('**/simulation/sim_synthetic')
  })
  await check('scenario configuration with seeded persona and simulation substitutes', async () => {
    await page.getByRole('button', { name: /Prepare environment/ }).click()
    await page.getByText('Ready', { exact: true }).first().waitFor({ timeout: 10000 })
    await snapshot('scenario-ready')
    await page.getByRole('button', { name: /Start dual world parallel simulation/ }).click()
    await page.waitForURL('**/simulation/sim_synthetic/start**')
    await page.waitForTimeout(2500)
    await snapshot('simulation-completed')
    const emptyTimeline = await page.locator('.waiting-state').boundingBox()
    const log = await page.locator('.system-logs').boundingBox()
    assert(emptyTimeline.y + emptyTimeline.height <= log.y, 'Simulation activity is obscured by its log')
  })
  await check('report navigation from seeded simulation; root generation explicitly intercepted', async () => {
    await page.route('**/api/report/generate', route => route.fulfill({ json: { success: true, data: { report_id: 'report_synthetic', task_id: 'seeded-not-generated' } } }))
    const buttons = await page.getByRole('button').allTextContents()
    receipt.simulationButtons = buttons
    const generate = page.getByRole('button', { name: /Start Generating Report/i }).first()
    await generate.click({ timeout: 3000 })
    await page.waitForURL('**/report/report_synthetic')
    await page.unroute('**/api/report/generate')
    await page.getByRole('button', { name: 'Draft with sources' }).first().waitFor()
    assert.match(await page.locator('body').innerText(), /Synthetic source-only example; no simulation has run/)
  })
  await check('source review and keyboard provenance inspection', async () => {
    await page.getByRole('button', { name: 'Draft with sources' }).first().click()
    await page.getByText('Ready for your review', { exact: true }).waitFor({ timeout: 10000 })
    const panel = page.getByRole('region', { name: 'Evidence draft review' }).first()
    assert.match(await panel.innerText(), /Alex states that the hearing was postponed until Friday/)
    assert.match(await panel.innerText(), /Model checks can miss errors/)
    const claim = panel.locator('.claim > summary').first()
    await claim.focus(); await page.keyboard.press('Enter')
    assert.match(await panel.innerText(), /Attributed to Alex/)
    const provenance = panel.locator('.source summary').first()
    await provenance.focus(); await page.keyboard.press('Enter')
    assert.match(await panel.innerText(), /Original SHA-256/)
    await snapshot('proposal-review')
    for (const width of [375, 768, 1440]) {
      await page.setViewportSize({ width, height: 1000 })
      await panel.locator('.source').first().scrollIntoViewIfNeeded()
      await page.screenshot({ path: `${output}/source-inspection-${width}.png` })
    }
  })
  await check('changed source produces an honest 409 conflict and disables save', async () => {
    await page.request.post(base + '/__synthetic/change-source')
    await page.getByRole('button', { name: 'Save as new revision', exact: true }).first().click()
    await page.getByText('Sources changed', { exact: true }).waitFor()
    assert(await page.getByRole('button', { name: 'Save as new revision', exact: true }).first().isDisabled())
    await page.getByRole('alert').first().scrollIntoViewIfNeeded()
    await page.screenshot({ path: output + '/stale-conflict.png' })
    await page.getByRole('button', { name: 'Keep original', exact: true }).first().click()
    await page.getByText('Original retained', { exact: true }).waitFor()
    await page.request.post(base + '/__synthetic/change-source')
  })
  await check('unrelated unsupported proposal blocks saving', async () => {
    await page.getByRole('button', { name: 'Draft with sources', exact: true }).click()
    await page.getByText('Changes required', { exact: true }).waitFor({ timeout: 10000 })
    const panel = page.getByRole('region', { name: 'Evidence draft review' }).nth(1)
    assert(await panel.getByRole('button', { name: 'Save as new revision', exact: true }).isDisabled())
    assert.match(await panel.innerText(), /Blocks saving/)
    await panel.scrollIntoViewIfNeeded()
    await page.screenshot({ path: output + '/unsupported-blocked.png' })
    await panel.getByRole('button', { name: 'Keep original', exact: true }).click()
  })
  await check('duplicate clicks plus response-loss retry create one immutable child', async () => {
    const first = page.getByRole('region', { name: 'Evidence draft review' }).first()
    await first.getByRole('button', { name: 'New proposal', exact: true }).click()
    await page.getByText('Ready for your review', { exact: true }).waitFor()
    let acceptRequests = 0
    await page.route('**/evidence-proposals/*/accept', async route => {
      acceptRequests++
      const response = await route.fetch()
      receipt.acceptance = { status: response.status(), body: await response.json() }
      await new Promise(resolve => setTimeout(resolve, 250))
      await route.abort('failed')
    })
    const save = first.getByRole('button', { name: 'Save as new revision', exact: true })
    await save.evaluate(button => { button.click(); button.click() })
    await page.getByRole('alert').first().waitFor({ timeout: 10000 })
    assert.equal(acceptRequests, 1)
    assert.equal(receipt.acceptance.status, 200)
    await page.screenshot({ path: output + '/lost-save-response.png' })
    await page.unroute('**/evidence-proposals/*/accept')
    await save.click()
    await page.waitForURL(url => url.pathname.startsWith('/report/') && !url.pathname.endsWith('report_synthetic'))
    receipt.revisionId = new URL(page.url()).pathname.split('/').at(-1)
    await page.getByText('Saved revision · Needs review', { exact: true }).waitFor()
    const revision = (await json('/api/report/' + receipt.revisionId)).data
    assert.equal(revision.status, 'needs_review')
    assert.equal(revision.revision.immutable, true)
    assert.equal(revision.revision.parent_report_id, 'report_synthetic')
    assert.equal(receipt.revisionId, receipt.acceptance.body.data.report_id)
    const evidence = await json('/__synthetic/evidence')
    assert.equal(evidence.parent_unchanged, true)
    assert.equal(evidence.reports.filter(report => report.revision?.parent_report_id === 'report_synthetic').length, 1)
    receipt.persisted = { parentUnchanged: evidence.parent_unchanged, reportCount: evidence.reports.length,
      parentDigests: evidence.parent_digests, source: evidence.source, gitHead: evidence.git_head }
  })
  await check('saved revision reload, inherited section and source ledger remain reviewable', async () => {
    await page.reload()
    await page.getByText('Saved revision · Needs review', { exact: true }).waitFor()
    assert.match(await page.locator('body').innerText(), /Unrelated contracts remain unresolved/)
    await page.getByText('Saved claim ledger · 1 statements', { exact: true }).click()
    await page.locator('.saved-ledger > details > summary').first().click()
    assert.match(await page.locator('.saved-ledger').innerText(), /synthetic-record.txt/)
    assert.match(await page.locator('.saved-ledger').innerText(), /Source support remains unverified/)
    await snapshot('saved-revision')
    await page.getByRole('link', { name: 'Original report', exact: true }).click()
    await page.waitForURL('**/report/report_synthetic')
    await page.getByRole('link', { name: 'CrowdLens', exact: true }).click()
    await page.waitForURL(base + '/')
    await page.getByRole('link', { name: 'Cases', exact: true }).click()
    await page.waitForURL('**/cases')
    await page.waitForTimeout(300)
  })
  await check('history loading, error, explicit retry and empty states', async () => {
    receipt.substitutes.push('History list response held, then 503, then empty 200 for state testing')
    let release
    const held = new Promise(resolve => { release = resolve })
    let fail = true
    await page.route('**/api/simulation/history*', async route => {
      await held
      await route.fulfill(fail ? { status: 503, json: { success: false, error: 'synthetic unavailable' } }
        : { json: { success: true, data: [] } })
    })
    await page.goto(base)
    await page.locator('.history-database .loading-text').waitFor()
    await page.locator('.history-database').scrollIntoViewIfNeeded()
    await page.screenshot({ path: output + '/history-loading.png' })
    release()
    await page.getByRole('alert').waitFor()
    assert.match(await page.getByRole('alert').innerText(), /Unable to load simulation records/)
    await page.screenshot({ path: output + '/history-error.png' })
    fail = false
    await page.getByRole('button', { name: 'Retry history', exact: true }).click()
    await page.getByText(/No simulation records yet/).waitFor()
    await page.screenshot({ path: output + '/history-empty.png' })
    await page.unroute('**/api/simulation/history*')
  })
  receipt.performance = await page.evaluate(() => window.qaVitals)
  receipt.performance.note = 'Laboratory browser samples only; no field Core Web Vitals or representative INP conclusion.'
  assert.deepEqual(receipt.pageErrors, [])
  for (const item of receipt.snapshots) {
    assert.deepEqual(item.layout.clipped, [], `${item.name} at ${item.width}px has offscreen controls`)
    assert.equal(item.layout.scrollWidth, item.width, `${item.name} at ${item.width}px overflows horizontally`)
    assert.deepEqual(item.a11y, [], `${item.name} at ${item.width}px has automated accessibility findings`)
  }
} catch (error) {
  receipt.fatal = error.message
  await page.screenshot({ path: output + '/failure.png', fullPage: true }).catch(() => {})
  process.exitCode = 1
} finally {
  await writeFile(output + '/results.json', JSON.stringify(receipt, null, 2))
  await browser.close()
}
console.log(JSON.stringify({ checks: receipt.checks, fatal: receipt.fatal,
  snapshots: receipt.snapshots.map(item => ({ name: item.name, width: item.width,
    clipped: item.layout.clipped, a11y: item.a11y.map(item => item.id) })) }, null, 2))
