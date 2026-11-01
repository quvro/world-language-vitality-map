"""检查 mapMode 是否是响应式属性，以及 URL 应用后 computed 是否会失效。"""

import sys

from pptx import Presentation  # noqa: F401  (仅为确认依赖可用，实际不使用)

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import io  # noqa: E402

io.open("_tools/_probe_react.mjs", "w", encoding="utf-8").write(
    """
import { computed } from 'vue'
import { createHarness } from '../web/preview/_harness.mjs'

const h = await createHarness()
try {
  const s = await h.freshStore()
  const c = computed(() => s.mapMode)
  const trail = [c.value]
  s.mapMode = 'glyph'
  trail.push(c.value)
  s.mapMode = 'dots'
  trail.push(c.value)
  console.log('  computed 轨迹 =', JSON.stringify(trail))
  console.log('  glyphChannels 响应式：')
  const g = computed(() => s.glyphChannels.ring)
  const t2 = [g.value]
  s.glyphChannels.ring = false
  t2.push(g.value)
  console.log('   轨迹 =', JSON.stringify(t2))

  // 直接套用 URL 参数，看 computed 是否跟着变
  const { applyQuery } = await h.load('urlState.ts')
  const c2 = computed(() => s.mapMode)
  const before = c2.value
  applyQuery(s, '?mm=glyph')
  console.log('  applyQuery 之后：before =', before, ' after =', c2.value)
} finally {
  h.cleanup()
}
"""
)
print("  已写 _tools/_probe_react.mjs")
