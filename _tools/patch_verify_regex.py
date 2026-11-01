"""验证脚本 rangeOf() 不认 `computed<T>(...)` 的泛型写法，补上。

之前 `const glyphItems = computed<GlyphItem[]>(() => {...})` 匹配不到，
导致 glyphItems 整段源码不在覆盖范围内，它读的字段全被判成"未覆盖"。
这类误报比漏报更麻烦：会让人以为功能坏了，其实是检查器不认新语法。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/preview/verify-map-repaint.mjs"
s = io.open(P, encoding="utf-8").read()

OLD = (
    "  const re = new RegExp(\n"
    "    `(?:const\\\\s+${name}\\\\s*=\\\\s*(?:computed\\\\(|ref\\\\()|"
    "function\\\\s+${name}\\\\s*\\\\()`, 'g')"
)
NEW = (
    "  // 允许泛型参数：computed<Foo[]>(...)、ref<number>(...)\n"
    "  const re = new RegExp(\n"
    "    `(?:const\\\\s+${name}\\\\s*=\\\\s*(?:computed|ref)(?:<[^>]*>)?\\\\(|"
    "function\\\\s+${name}\\\\s*\\\\()`, 'g')"
)

if OLD in s:
    s = s.replace(OLD, NEW, 1)
    print("  ok   rangeOf 支持泛型")
else:
    # 换一种更稳的做法：直接替换那两行正则
    lines = s.splitlines()
    for i, ln in enumerate(lines):
        if "const re = new RegExp(" in ln:
            lines[i + 1] = (
                "    `(?:const\\s+${name}\\s*=\\s*(?:computed|ref)(?:<[^>]*>)?\\(|"
                "function\\s+${name}\\s*\\()`, 'g')"
            )
            print("  ok   按行改写 rangeOf 正则")
            break
    else:
        print("  MISS 没找到 rangeOf 的正则，请人工确认")
    s = "\n".join(lines)

io.open(P, "w", encoding="utf-8").write(s)
