import { createApp } from 'vue'
import { createPinia } from 'pinia'
import * as echarts from 'echarts'
import App from './App.vue'
import { registerVitalityTheme } from './theme/echarts-theme.js'

// 主题必须在 DOM ready 之后注册：它从 :root 读 CSS 变量，
// 早于样式生效会读到空值并全部退回 fallback。
registerVitalityTheme(echarts)

// ECharts 全局实例挂到 window，供各组件复用（避免重复打包）
;(window as unknown as { echarts: typeof echarts }).echarts = echarts

createApp(App).use(createPinia()).mount('#app')
