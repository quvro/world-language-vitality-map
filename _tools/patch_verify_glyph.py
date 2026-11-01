"""验证脚本：把新增的数据层（字形 / 语系连线 / 轮廓 / 底圈）纳入覆盖检查。"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/preview/verify-map-repaint.mjs"
s = io.open(P, encoding="utf-8").read()

OLD_WATCHED = "const WATCHED = ['contextData', 'vitalityData', 'haloData']"
NEW_WATCHED = (
    "// 复合字形（glyphItems）以及语系星群的三层也是被监听的数据源，\n"
    "// 它们读到的 store 字段同样会触发重绘，必须算进覆盖范围。\n"
    "const WATCHED = ['contextData', 'vitalityData', 'haloData', 'glyphItems',\n"
    "  'famStar', 'famHull', 'famGlow']"
)

OLD_CHK = (
    "check('三层（连线 / 轮廓 / 浅强调底圈）都在重绘监听里',\n"
    "  /watch\\(\\[contextData, vitalityData, haloData, famStar, famHull, famGlow\\]/.test(src))"
)
NEW_CHK = (
    "check('所有数据层（底图 / 活力 / 底圈 / 连线 / 轮廓 / 字形）都在同一条重绘监听里',\n"
    "  /watch\\(\\[contextData, vitalityData, haloData, famStar, famHull, famGlow, glyphItems\\]/\n"
    "    .test(src))"
)

for old, new, label in ((OLD_WATCHED, NEW_WATCHED, "WATCHED"),
                        (OLD_CHK, NEW_CHK, "监听断言")):
    if old in s:
        s = s.replace(old, new, 1)
        print(f"  ok   {label}")
    else:
        print(f"  MISS {label}（需要人工确认）")

io.open(P, "w", encoding="utf-8").write(s)
