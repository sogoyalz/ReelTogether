import { expect, type Locator } from '@playwright/test'

export async function expectReadableText(locator: Locator) {
  const ratio = await locator.evaluate(element => {
    const channels = (value: string) => (value.match(/[\d.]+/g) || []).slice(0, 3).map(Number)
    const luminance = (rgb: number[]) => rgb.map(value => {
      const channel = value / 255
      return channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4
    }).reduce((total, channel, index) => total + channel * [0.2126, 0.7152, 0.0722][index], 0)
    const foreground = luminance(channels(getComputedStyle(element).color))
    let surface: Element | null = element
    while (surface && ['rgba(0, 0, 0, 0)', 'transparent'].includes(getComputedStyle(surface).backgroundColor)) surface = surface.parentElement
    if (!surface) throw new Error('No opaque text background found')
    const background = luminance(channels(getComputedStyle(surface).backgroundColor))
    return (Math.max(foreground, background) + 0.05) / (Math.min(foreground, background) + 0.05)
  })
  expect(ratio).toBeGreaterThanOrEqual(4.5)
}
