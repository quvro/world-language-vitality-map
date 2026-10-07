/**
 * ECharts 自定义亮色主题
 * ----------------------------------------------------------------------------
 * 为什么要自己写主题：ECharts 的默认配色（那套蓝紫）是国内"数据大屏"模板感的
 * 头号来源。直接用它，作品一眼就像现成模板。
 *
 * 做法：所有颜色都从 tokens.css 的 CSS 变量读取 —— token 是唯一真源，
 * 换肤只改 tokens.css，这里不用动。
 *
 * 写成纯 ES module（不是 .ts）是为了让「零构建预览页」和「Vite 工程」
 * 共用同一份代码，避免两处主题定义漂移。
 */

/** 从 :root 读一个 CSS 变量，读不到就退回默认值。 */
export function token(name, fallback) {
  if (typeof window === 'undefined') return fallback
  const v = getComputedStyle(document.documentElement)
    .getPropertyValue(name)
    .trim()
  return v || fallback
}

/** 12 色语系分类色板（色盲友好）。 */
export function categoryPalette() {
  return Array.from({ length: 12 }, (_, i) =>
    token(`--cat-${i + 1}`, '#888888')
  )
}

/** 顺序色阶（暖色递增），用于规模 / 体量。 */
export function sequentialScale() {
  return [
    token('--seq-0', '#f7f4ec'),
    token('--seq-1', '#fde68a'),
    token('--seq-2', '#fb923c'),
    token('--seq-3', '#dc2626'),
  ]
}

/** 活力色阶（冷色递增），用于健康度这类正向指标。 */
export function vitalityScale() {
  return [
    token('--vital-0', '#f0f7f7'),
    token('--vital-1', '#b7e4e0'),
    token('--vital-2', '#5fb8ae'),
    token('--vital-3', '#1f6f66'),
  ]
}

/** 语义色。 */
export function semanticColors() {
  return {
    accent: token('--accent', '#e4572e'),
    positive: token('--positive', '#2a9d8f'),
    negative: token('--negative', '#e4572e'),
    neutral: token('--neutral', '#c9c4ba'),
    textPrimary: token('--text-primary', '#23201c'),
    textSecondary: token('--text-secondary', '#6e6a62'),
    textMuted: token('--text-muted', '#a39d91'),
    border: token('--border', '#e9e4da'),
    surface: token('--bg-surface', '#ffffff'),
    subtle: token('--bg-subtle', '#f4f1ea'),
    canvas: token('--bg-canvas', '#fbfaf7'),
  }
}

export const THEME_NAME = 'vitality-light'

/**
 * 构建主题对象。必须在 CSS 变量可用之后（即 DOM ready 之后）调用，
 * 否则读到的是空值、会全部退回 fallback。
 */
export function buildTheme() {
  const c = semanticColors()
  const palette = categoryPalette()
  const fontSans = token(
    '--font-sans',
    '"Source Han Sans SC", "PingFang SC", "Microsoft YaHei", sans-serif'
  )
  const fontMono = token(
    '--font-mono',
    '"JetBrains Mono", "SF Mono", Consolas, monospace'
  )

  const axisCommon = {
    axisLine: { show: true, lineStyle: { color: c.border, width: 1 } },
    // 默认的虚线网格太"系统图"，换成极浅实线
    splitLine: {
      show: true,
      lineStyle: { color: c.border, width: 1, type: 'solid', opacity: 0.7 },
    },
    axisTick: { show: false },
    axisLabel: { color: c.textSecondary, fontFamily: fontSans, fontSize: 12 },
    nameTextStyle: { color: c.textMuted, fontFamily: fontSans, fontSize: 11 },
  }

  return {
    color: palette,
    backgroundColor: 'transparent',
    textStyle: { fontFamily: fontSans, color: c.textPrimary },

    title: {
      textStyle: { color: c.textPrimary, fontFamily: fontSans, fontWeight: 600 },
      subtextStyle: { color: c.textMuted, fontFamily: fontSans },
      left: 0,
    },

    animation: true,
    animationDuration: 260,
    animationDurationUpdate: 480,
    animationEasing: 'cubicOut',
    animationEasingUpdate: 'cubicInOut',

    grid: {
      left: 48,
      right: 24,
      top: 40,
      bottom: 40,
      containLabel: true,
      borderColor: c.border,
    },

    categoryAxis: { ...axisCommon, splitLine: { show: false } },
    valueAxis: axisCommon,
    logAxis: axisCommon,
    timeAxis: axisCommon,

    legend: {
      textStyle: { color: c.textSecondary, fontFamily: fontSans, fontSize: 12 },
      icon: 'roundRect',
      itemWidth: 10,
      itemHeight: 10,
      itemGap: 14,
    },

    tooltip: {
      backgroundColor: c.surface,
      borderColor: c.border,
      borderWidth: 1,
      padding: [8, 12],
      textStyle: { color: c.textPrimary, fontFamily: fontSans, fontSize: 12 },
      extraCssText:
        'box-shadow: 0 2px 8px rgba(35,32,28,0.06); border-radius: 8px;',
      axisPointer: {
        lineStyle: { color: c.border },
        crossStyle: { color: c.border },
        label: { backgroundColor: c.textPrimary },
      },
    },

    // 大屏上的数字用等宽，列才对得齐
    label: { color: c.textPrimary, fontFamily: fontMono, fontSize: 12 },

    geo: {
      itemStyle: { areaColor: c.subtle, borderColor: c.border, borderWidth: 0.6 },
      emphasis: {
        itemStyle: { areaColor: c.border },
        label: { show: false },
      },
      label: { show: false },
      select: { itemStyle: { areaColor: c.border } },
    },

    visualMap: {
      textStyle: { color: c.textSecondary, fontFamily: fontSans, fontSize: 11 },
      inRange: { color: sequentialScale() },
    },

    tree: {
      itemStyle: { borderColor: c.border },
      lineStyle: { color: c.border, width: 1, curveness: 0.5 },
      label: { color: c.textPrimary, fontFamily: fontSans, fontSize: 12 },
    },
    graph: {
      itemStyle: { borderColor: c.surface },
      lineStyle: { color: c.border, opacity: 0.7 },
      label: { color: c.textPrimary, fontFamily: fontSans, fontSize: 11 },
    },

    sankey: {
      itemStyle: { borderWidth: 0 },
      lineStyle: { color: 'gradient', opacity: 0.35, curveness: 0.5 },
      label: { color: c.textPrimary, fontFamily: fontSans, fontSize: 11 },
    },
    themeRiver: {
      label: { color: c.textPrimary, fontFamily: fontSans, fontSize: 11 },
    },

    parallel: {
      lineStyle: { width: 1, opacity: 0.35 },
      axisLine: { lineStyle: { color: c.border } },
      axisLabel: { color: c.textSecondary, fontFamily: fontSans, fontSize: 10 },
    },
    parallelAxis: {
      axisLine: { lineStyle: { color: c.border } },
      axisTick: { lineStyle: { color: c.border } },
      axisLabel: { color: c.textSecondary, fontFamily: fontSans, fontSize: 10 },
      nameTextStyle: { color: c.textMuted, fontFamily: fontSans, fontSize: 11 },
    },
  }
}

/** 一行接入：注册主题。应在 DOM ready 后调用一次。 */
export function registerVitalityTheme(echarts) {
  echarts.registerTheme(THEME_NAME, buildTheme())
}
