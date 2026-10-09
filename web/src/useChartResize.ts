import { onBeforeUnmount, onMounted, type Ref } from 'vue'

/**
 * 让 ECharts 跟随**容器**尺寸变化。
 *
 * 为什么不能只监听 window.resize：
 * ECharts 必须显式调用 `resize()` 重算画布尺寸。而侧栏折叠、切换选项卡、
 * 拖分隔条这类操作会让容器变宽变窄，**窗口尺寸却没变** —— window.resize
 * 根本不会触发，画布于是保持旧宽度，与相邻区域重叠。
 * 这正是「切到条件对比再切回来，右栏开合会压住地图」的原因。
 *
 * 用 ResizeObserver 直接盯住容器；折叠动画期间尺寸逐帧变化，
 * 再用 requestAnimationFrame 合并，避免每帧都触发一次昂贵的 resize。
 */
export function useChartResize(host: Ref<HTMLElement | null>, chart: Ref<any>) {
  let ro: ResizeObserver | null = null
  let raf = 0

  const schedule = () => {
    cancelAnimationFrame(raf)
    raf = requestAnimationFrame(() => {
      const c = chart.value
      if (!c) return
      // 容器可能暂时不可见（display:none / 尺寸为 0），此时 resize 会报错或得到 0×0
      const el = host.value
      if (!el || el.clientWidth === 0 || el.clientHeight === 0) return
      c.resize()
    })
  }

  onMounted(() => {
    if (!host.value || typeof ResizeObserver === 'undefined') return
    ro = new ResizeObserver(schedule)
    ro.observe(host.value)
    // 初次挂载时容器尺寸可能刚确定，补一次
    schedule()
  })

  onBeforeUnmount(() => {
    cancelAnimationFrame(raf)
    ro?.disconnect()
    ro = null
  })

  return { schedule }
}
