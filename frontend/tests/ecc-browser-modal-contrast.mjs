// Supplemental check for plain modal text that axe can mark incomplete.
// The fixture uses solid backgrounds. Decorative icons repeat adjacent labels.
export function inspectModalContrast() {
  const rgba = value => {
    const channels = value.match(/[\d.]+/g).map(Number)
    return [...channels.slice(0, 3), channels[3] ?? 1]
  }
  const over = (front, back) => front.slice(0, 3).map((value, index) => value * front[3] + back[index] * (1 - front[3]))
  const luminance = color => color.map(value => value / 255)
    .map(value => value <= .04045 ? value / 12.92 : ((value + .055) / 1.055) ** 2.4)
    .reduce((sum, value, index) => sum + value * [.2126, .7152, .0722][index], 0)
  const root = document.querySelector('[role="dialog"]')
  const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT)
  const result = []
  for (let node; (node = walker.nextNode());) {
    const text = node.textContent.trim()
    const element = node.parentElement
    if (!text || element.closest('.btn-icon, .status-dot')) continue
    const range = document.createRange()
    range.selectNodeContents(node)
    if (![...range.getClientRects()].some(rect => rect.width && rect.height && rect.bottom > 0 && rect.top < innerHeight)) continue
    const backgrounds = []
    for (let ancestor = element; ancestor; ancestor = ancestor.parentElement) backgrounds.unshift(rgba(getComputedStyle(ancestor).backgroundColor))
    const background = backgrounds.reduce((color, layer) => over(layer, color), [255, 255, 255])
    const style = getComputedStyle(element)
    const foreground = over(rgba(style.color), background)
    const light = [luminance(foreground), luminance(background)].sort((a, b) => b - a)
    const ratio = (light[0] + .05) / (light[1] + .05)
    const large = parseFloat(style.fontSize) >= 24 || (parseFloat(style.fontSize) >= 18.66 && parseInt(style.fontWeight) >= 700)
    result.push({ text, selector: element.className, foreground: style.color, background,
      fontSize: style.fontSize, ratio, minimum: large ? 3 : 4.5 })
  }
  return result
}
