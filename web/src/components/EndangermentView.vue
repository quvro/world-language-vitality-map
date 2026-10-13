<script setup lang="ts">
/**
 * 活力之辨：把**两个独立的活力维度**摆在一起对照。
 *
 * 起因是一个必须回答的问题 ——「活力到底是什么？」
 *
 * 在此之前，项目里所有叫"活力"的指标都来自同一个原始量：某语言的维基百科版本
 * 被读了多少次。那是**数字关注度**，不是语言学意义上的语言活力。
 * 语言学里的语言活力核心是**代际传承与实际使用**（UNESCO 的 9 项指标），
 * 而维基浏览量 ≈ 使用者数 × 识字率 × 上网率 × 用维基的习惯 ——
 * 四项相乘会系统性放大差距，并系统性低估无文字传统的语言。
 *
 * 接入 UNESCO 濒危等级（Wikidata P1999）后，两个维度可以对照了：
 *
 *      一门语言在语言学上还活着，但在数字空间里已经死了吗？反过来呢？
 *
 * 实测结论：两者高度一致。safe 75.6% 有维基版本，critically 只有 2.0%，
 * 已灭绝的 51 种一个都没有。
 *
 * ⚠️ 口径必须写清楚：UNESCO 名录**只收濒危语言**（全名录 2,593 条里
 * 只有 82 条是 safe）。所以"未被名录收录"≠"安全"，绝不能反推。
 * 本项目 2,662 门语言里有 1,546 门未匹配，它们不代表安全。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'
import { useDisplayNames } from '@/display'
import { endangermentScale } from '@/theme/echarts-theme.js'

const store = useDataset()
const { language: langLabel } = useDisplayNames()
const RAMP = endangermentScale()

const T = {
  zh: {
    title: '活力之辨',
    sub: '两个独立的活力维度对照 · 数字关注度 ≠ 语言活力',
    existenceTitle: '① 存在性：语言学濒危等级 × 是否有维基百科版本',
    existenceSub: '这是信号最强的一个维度 —— 严格单调',
    strengthTitle: '② 强度：已拥有维基版本的语言里，阅读量中位数',
    strengthSub: '样本很小，谨慎解读',
    level: '等级', langs: '语言', withWiki: '有维基版本', median: '阅读量中位数',
    clickHint: '点一行按该濒危等级筛选全站',
    selected: '已选中',
    caveatTitle: '口径说明（务必注意）',
    caveat1: 'UNESCO 名录**只收濒危语言**：全名录 2,593 条里只有 82 条是「安全」。所以「未被名录收录」不等于「安全」，不能反推。',
    caveat2: (n: string, m: string) => `本项目 2,662 门语言中有 ${n} 门未匹配到名录，其中 ${m} 门没有维基版本 —— 这只是"没被收录"，不代表它们安全。`,
    caveat3: (a: string, b: string) => `严重濒危与极度濒危两组分别只有 ${a} 门和 ${b} 门有维基版本，样本不足以支撑"强度"上的结论，第②块仅供参考。`,
    finding: '语言学上越濒危的语言，在数字空间里越可能根本不存在。已灭绝的 51 种语言，一个有维基百科版本的都没有。',
    noData: '未跑 pipeline/05_fetch_endangerment.py，没有濒危等级数据。',
    unmatched: '未收录',
  },
  en: {
    title: 'Two kinds of vitality',
    sub: 'two independent dimensions · digital attention ≠ language vitality',
    existenceTitle: '① Existence: UNESCO endangerment × has a Wikipedia edition',
    existenceSub: 'the strongest signal — strictly monotonic',
    strengthTitle: '② Intensity: median views among those that do have a Wikipedia',
    strengthSub: 'very small samples — read with caution',
    level: 'Level', langs: 'Langs', withWiki: 'has Wikipedia', median: 'median views',
    clickHint: 'click a row to filter the whole dashboard by that level',
    selected: 'selected',
    caveatTitle: 'Scope caveats (important)',
    caveat1: 'The UNESCO Atlas **only lists endangered languages**: of its 2,593 entries only 82 are “safe”. So “not listed” does not mean “safe” — the inference does not run that way.',
    caveat2: (n: string, m: string) => `Of this project’s 2,662 languages, ${n} are not in the Atlas and ${m} of those have no Wikipedia edition — that is absence from the list, not evidence of safety.`,
    caveat3: (a: string, b: string) => `Only ${a} and ${b} languages in the severely / critically endangered bands have a Wikipedia edition, too few to support any conclusion about intensity; panel ② is indicative only.`,
    finding: 'The more endangered a language is linguistically, the more likely it is to be entirely absent digitally. Of the 51 extinct languages, not one has a Wikipedia edition.',
    noData: 'pipeline/05_fetch_endangerment.py has not been run — no endangerment data.',
    unmatched: 'not listed',
  },
} as const
const t = computed(() => T[store.lang])

const LEVEL_LABEL = (lv: number): string => {
  const l = store.endangerment?.levels?.[String(lv)]
  if (!l) return String(lv)
  return store.lang === 'zh' ? l.zh : l.en
}

const ebw = computed(() => store.endangermentByWals)

/** 存在性：每一级的语言数、其中有维基版本的数量与比例 */
const existence = computed(() =>
  [1, 2, 3, 4, 5, 6].map((lv) => {
    const rows = store.langs.filter((l) => ebw.value[l.wals_id] === lv)
    const wiki = rows.filter((l) => l.wiki_code).length
    return {
      lv,
      label: LEVEL_LABEL(lv),
      color: RAMP[lv - 1],
      n: rows.length,
      wiki,
      rate: rows.length ? wiki / rows.length : 0,
    }
  }).filter((d) => d.n > 0)
)

/** 强度：在**有维基版本**的语言里，各级的阅读量中位数 */
const strength = computed(() =>
  [1, 2, 3, 4, 5, 6].map((lv) => {
    const v = store.langs
      .filter((l) => ebw.value[l.wals_id] === lv && l.wiki_code && l.views_recent != null)
      .map((l) => l.views_recent!)
      .sort((a, b) => a - b)
    const med = v.length ? (v.length % 2
      ? v[(v.length - 1) / 2]
      : (v[v.length / 2 - 1] + v[v.length / 2]) / 2) : 0
    return { lv, label: LEVEL_LABEL(lv), color: RAMP[lv - 1], n: v.length, med }
  }).filter((d) => d.n > 0)
)

const strengthMax = computed(() => Math.max(...strength.value.map((d) => d.med), 1))
const covered = computed(() => store.langs.filter((l) => ebw.value[l.wals_id]).length)
const unmatched = computed(() => store.langs.length - covered.value)
const unmatchedNoWiki = computed(() =>
  store.langs.filter((l) => !ebw.value[l.wals_id] && !l.wiki_code).length)
const severeN = computed(() => strength.value.find((d) => d.lv === 4)?.n ?? 0)
const criticalN = computed(() => strength.value.find((d) => d.lv === 5)?.n ?? 0)

function toggle(lv: number) {
  const cur = store.endangermentLevels
  store.endangermentLevels = cur.includes(lv)
    ? cur.filter((x) => x !== lv)
    : [...cur, lv]
}

const fmt = (n: number) => n.toLocaleString('en-US')
const pct = (r: number) => `${(r * 100).toFixed(1)}%`
</script>

<template>
  <section class="card">
    <header>
      <div>
        <h2>{{ t.title }}</h2>
        <p class="hint">{{ t.sub }}</p>
      </div>
      <span v-if="store.endangerment" class="cover num">
        UNESCO {{ covered.toLocaleString('en-US') }} / {{ store.langs.length.toLocaleString('en-US') }}
      </span>
    </header>

    <div v-if="!store.endangerment" class="empty">{{ t.noData }}</div>

    <template v-else>
      <div class="panels">
        <!-- ① 存在性：信号最强，严格单调 -->
        <section class="panel">
          <div class="ph">
            <h3>{{ t.existenceTitle }}</h3>
            <span class="sub">{{ t.existenceSub }}</span>
          </div>
          <ul class="rows">
            <li
              v-for="d in existence"
              :key="d.lv"
              :class="{ on: store.endangermentLevels.includes(d.lv) }"
              :title="t.clickHint"
              @click="toggle(d.lv)"
            >
              <span class="dot" :style="{ background: d.color }" />
              <span class="lbl">{{ d.label }}</span>
              <span class="track">
                <i :style="{ width: pct(d.rate), background: d.color }" />
              </span>
              <span class="rate num" :style="{ color: d.color }">{{ pct(d.rate) }}</span>
              <span class="n num">{{ d.wiki }}/{{ d.n }}</span>
            </li>
          </ul>
        </section>

        <!-- ② 强度：样本小，明确标注 -->
        <section class="panel">
          <div class="ph">
            <h3>{{ t.strengthTitle }}</h3>
            <span class="sub warn">{{ t.strengthSub }}</span>
          </div>
          <ul class="rows">
            <li v-for="d in strength" :key="d.lv" class="static"
                :class="{ thin: d.n < 10 }">
              <span class="dot" :style="{ background: d.color }" />
              <span class="lbl">{{ d.label }}</span>
              <span class="track">
                <i :style="{ width: (d.med / strengthMax) * 100 + '%', background: d.color }" />
              </span>
              <span class="rate num">{{ fmt(Math.round(d.med)) }}</span>
              <span class="n num" :class="{ warn: d.n < 10 }">n={{ d.n }}</span>
            </li>
          </ul>
        </section>
      </div>

      <p class="finding">{{ t.finding }}</p>

      <div class="caveat">
        <h4>{{ t.caveatTitle }}</h4>
        <ul>
          <li>{{ t.caveat1 }}</li>
          <li>{{ t.caveat2(fmt(unmatched), fmt(unmatchedNoWiki)) }}</li>
          <li>{{ t.caveat3(String(severeN), String(criticalN)) }}</li>
        </ul>
      </div>
    </template>
  </section>
</template>

<style scoped>
.card {
  background: var(--bg-surface); border: 1px solid var(--border);
  border-radius: var(--radius-lg); box-shadow: var(--shadow-sm);
  padding: var(--sp-4); display: flex; flex-direction: column; gap: var(--sp-3);
  min-height: 0; height: 100%; overflow: hidden auto;
}
header { display: flex; align-items: flex-start; justify-content: space-between; gap: var(--sp-3); flex: none; }
h2 { margin: 0; font-size: var(--fs-h2); font-weight: 600; }
.hint { margin: 2px 0 0; font-size: var(--fs-small); color: var(--text-muted); }
.cover { font-size: var(--fs-micro); color: var(--text-muted); white-space: nowrap; padding-top: 4px; }
.empty { color: var(--text-muted); font-size: var(--fs-small); padding: var(--sp-5) 0; text-align: center; }

.panels { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-5); }
@media (max-width: 1000px) { .panels { grid-template-columns: 1fr; } }
.panel { min-width: 0; }
.ph { margin-bottom: var(--sp-2); }
.ph h3 { margin: 0; font-size: var(--fs-small); font-weight: 600; }
.ph .sub { font-size: var(--fs-micro); color: var(--text-muted); }
.ph .sub.warn { color: var(--accent); }

.rows { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: 3px; }
.rows li {
  display: grid;
  grid-template-columns: 8px 92px minmax(40px, 1fr) 62px 62px;
  align-items: center; gap: var(--sp-2);
  padding: 3px 5px; border-radius: var(--radius-sm);
  cursor: pointer; transition: background var(--dur-fast) var(--ease-out);
}
.rows li:hover { background: var(--bg-subtle); }
.rows li.on { background: var(--accent-soft); box-shadow: inset 0 0 0 1px var(--accent); }
.rows li.static { cursor: default; }
.rows li.static:hover { background: transparent; }
.rows li.thin { opacity: 0.55; }
.dot { width: 8px; height: 8px; border-radius: 50%; }
.lbl { font-size: var(--fs-micro); color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.track { height: 11px; background: var(--bg-subtle); border-radius: 6px; overflow: hidden; }
.track i { display: block; height: 100%; border-radius: 6px; transition: width var(--dur-base) var(--ease-out); }
.rate { font-size: var(--fs-micro); font-weight: 500; text-align: right; }
.rows li.static .rate { color: var(--text-secondary); }
.n { font-size: var(--fs-micro); color: var(--text-muted); text-align: right; }
.n.warn { color: var(--accent); }

.finding {
  margin: 0; padding: var(--sp-3);
  background: var(--accent-soft); border-radius: var(--radius-md);
  font-size: var(--fs-small); color: var(--text-primary); line-height: 1.6;
}

.caveat {
  border: 1px solid var(--border); border-top: 3px solid var(--neutral);
  border-radius: var(--radius-md); padding: var(--sp-3);
  background: var(--bg-canvas);
}
.caveat h4 {
  margin: 0 0 var(--sp-2); font-size: var(--fs-micro); font-weight: 600;
  text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-muted);
}
.caveat ul { margin: 0; padding-left: 1.1em; }
.caveat li { font-size: var(--fs-micro); color: var(--text-muted); line-height: 1.75; }
</style>
