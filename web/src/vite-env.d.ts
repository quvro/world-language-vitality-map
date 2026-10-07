/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<Record<string, unknown>, Record<string, unknown>, unknown>
  export default component
}

/** echarts-theme.js 是纯 JS（为了让零构建预览页也能复用），这里给出最小签名。 */
declare module '*/echarts-theme.js' {
  export const THEME_NAME: string
  export function token(name: string, fallback: string): string
  export function categoryPalette(): string[]
  export function sequentialScale(): string[]
  export function vitalityScale(): string[]
  export function semanticColors(): {
    accent: string; positive: string; negative: string; neutral: string
    textPrimary: string; textSecondary: string; textMuted: string
    border: string; surface: string; subtle: string; canvas: string
  }
  export function buildTheme(): Record<string, unknown>
  export function registerVitalityTheme(echarts: {
    registerTheme: (name: string, theme: unknown) => void
  }): void
}
