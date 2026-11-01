"""修右栏两处：卡片不再只剩一半；体检单可以滚。

上一版的错误：
  .right-stack > :first-child { flex: 0 1 auto; }   ← grow=0，卡片只按内容撑开
  .right-stack > :last-child  { flex: none; }       ← 不能被压缩，内容超出就裁掉

修法：
  卡片  flex: 1 1 auto  占满剩余空间，内容多时自己滚
  体检单 flex: 0 1 auto + max-height，被压缩时自己滚
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

A = "web/src/App.vue"
s = io.open(A, encoding="utf-8").read()

OLD = """/* 关键：让详情卡自己滚动、并把高度让出来，体检单永远留在可视区。
   之前卡片把高度占满，体检单被挤到滚动区外，窗口矮一点就"完全看不到"。 */
.right-stack > :first-child {
  flex: 0 1 auto;
  min-height: 0;
  overflow-y: auto;
}
.right-stack > :last-child { flex: none; }"""

NEW = """/* 右栏高度分配：
   卡片占满剩余空间（grow=1，否则只按内容撑开、只剩一半高），
   体检单保留自己的高度但允许被压缩，压缩后自己滚动（否则超出就被裁掉）。
   两者都 min-height:0，否则 flex 子项不会真正收缩。 */
.right-stack > :first-child {
  flex: 1 1 auto;
  min-height: 0;
  overflow-y: auto;
}
.right-stack > :last-child {
  flex: 0 1 auto;
  min-height: 0;
  max-height: 46%;
  overflow-y: auto;
}"""

if OLD in s:
    io.open(A, "w", encoding="utf-8").write(s.replace(OLD, NEW, 1))
    print("  ok   右栏高度分配已修正")
else:
    print("  MISS 未匹配到上一版的规则")
