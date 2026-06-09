/** 可选时区（IANA）；配置页添加用 */

export interface WorldClockPreset {
  tz: string
  label: string
}

export const WORLD_CLOCK_PRESETS: WorldClockPreset[] = [
  { tz: 'Asia/Shanghai', label: '北京' },
  { tz: 'Asia/Hong_Kong', label: '香港' },
  { tz: 'Asia/Tokyo', label: '东京' },
  { tz: 'Asia/Singapore', label: '新加坡' },
  { tz: 'Europe/London', label: '伦敦' },
  { tz: 'Europe/Berlin', label: '柏林' },
  { tz: 'Europe/Paris', label: '巴黎' },
  { tz: 'America/New_York', label: '纽约' },
  { tz: 'America/Chicago', label: '芝加哥' },
  { tz: 'America/Los_Angeles', label: '洛杉矶' },
  { tz: 'America/Vancouver', label: '温哥华' },
  { tz: 'Australia/Sydney', label: '悉尼' },
]

export const MAX_WORLD_CLOCK_ZONES = 6

/** 与后端 world_clocks_settings.DEFAULT_ZONES 一致 */
export const DEFAULT_WORLD_CLOCK_ZONES: WorldClockPreset[] = [
  { tz: 'Asia/Shanghai', label: '北京' },
  { tz: 'America/Los_Angeles', label: '洛杉矶' },
  { tz: 'America/New_York', label: '纽约' },
  { tz: 'Europe/London', label: '伦敦' },
]
