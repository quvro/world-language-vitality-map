"""把 URL 状态的应用推迟到首次渲染之后。

现象：`?mm=glyph` 时 ECharts 画出了字形（说明 store 里的值是对的），
但模板仍显示密度态（三态按钮、开关面板、副标题都没更新）。
用 setTimeout 在挂载后 3 秒改同一个值，模板却能正常更新。
=> 不是响应性问题（单测确认 mapMode 是响应式的），而是**应用时机太早**：
   它紧跟在 `await store.load()` 之后，落在首屏渲染与各子组件挂载之间的空档里。

修法：先让首屏渲染完成（nextTick），再应用 URL 状态，然后再 nextTick 才回写 URL。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/src/App.vue"
s = io.open(P, encoding="utf-8").read()

OLD = """  await store.load()
  // 先按 URL 恢复状态，**再**开始回写 ——
  // 顺序反了的话，初始的空状态会先把 URL 覆盖掉，分享链接就失效了。
  applyQuery(store, location.search)
  startUrlSync(store)"""

NEW = """  await store.load()
  // 等首屏渲染落定再应用 URL 状态。
  //
  // 踩过：直接跟在 `await store.load()` 后面调用时，`?mm=glyph` 能让 ECharts
  // 画出字形（说明 store 的值确实改了），但模板仍停在密度态 ——
  // 三态按钮、开关面板、副标题都没更新。而在挂载后 3 秒改同一个值却一切正常。
  // 单测确认 mapMode 是响应式的，所以问题不在响应性，在**时机**：
  // 这一步落在了首屏渲染与子组件挂载之间的空档里。
  await nextTick()
  applyQuery(store, location.search)
  // 再等一帧才回写 URL —— 顺序反了的话，初始的空状态会先把 URL 覆盖掉，
  // 分享链接就失效了。
  await nextTick()
  startUrlSync(store)"""

if OLD in s:
    s = s.replace(OLD, NEW, 1)
    print("  ok   onMounted 时序已调整")
else:
    print("  MISS onMounted 片段未匹配")

if "nextTick" not in s.split("</script>")[0].split("<script")[1]:
    s = s.replace("import { computed, onMounted, ref } from 'vue'",
                  "import { computed, nextTick, onMounted, ref } from 'vue'", 1)
    print("  ok   已导入 nextTick")
else:
    print("  ok   nextTick 已在导入里" if "nextTick" in s else "  ?? nextTick 未导入")

io.open(P, "w", encoding="utf-8").write(s)
