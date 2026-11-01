<script setup lang="ts">
/**
 * 语言体检单 —— 把选中语言的六个维度拉成**百分位**横条。
 *
 * 为什么用百分位而不是原值：原值没法比较（"月阅读 3,412 次"算多还是少？）。
 * 百分位把它变成"在 2,662 门语言里排第几成"，读者立刻知道位置。
 *
 * 这个组件真正的用途是**暴露反差**：单独看每个维度都还行，
 * 并排放在一起才会发现"被研究得很透，却几乎没人读"——
 * 那正是本项目"双重缺席"的反面证据。
 */
import { computed } from 'vue'
import { useDataset } from '@/stores/dataset'

const store = useDataset()

const T = {
  zh: {
    title: '语言体检单', sub: '每一维在本库中的百分位（越高越靠前）',
    feat: 'WALS 记录特征', depth: '描写深度', works: '描写文献数',
    views: '月阅读量', proj: '其他维基项目', aes: '濒危程度',
    noData: '无数据', pct: (p: number) => `第 ${Math.round(p * 100)} 百分位`,
    tension: '反差',
    tResearch: (a: string, b: string) => `被研究得比 ${b}% 的语言更完整，`
      + `但阅读量只排在 ${a}% —— 这是"双重缺席"最典型的形状。`,
    tInverse: '注意：这一维越高表示越濒危，与其他维度方向相反。',
  },
  en: {
    title: 'Language check-up', sub: 'percentile within the dataset (higher = further ahead)',
    feat: 'WALS features', depth: 'Description depth', works: 'Descriptive works',
    views: 'Monthly views', proj: 'Other wiki projects', aes: 'Endangerment',
    noData: 'no data', pct: (p: number) => `${Math.round(p * 100)}th pct`,
    tension: 'Contrast',
    tResearch: (a: string, b: string) => `Better documented than ${b}% of languages, `
      + `but read less than ${a}% — the classic shape of double absence.`,
    tInverse: 'Note: higher here means more endangered — the opposite direction.',
  },
} as const
const t = computed(() => T[store.lang === 'zh' ? 'zh' : 'en'])

/** 取一个数组，返回 v 在其中的百分位（0..1）；样本太小或 v 缺失时返回 null */
function pctOf(vals: number[], v: number | null | undefined): number | null {
  if (v == null || !vals.length) return null
  let below = 0
  for (const x of vals) if (x < v) below++
  return below / vals.length
}

const rows = computed(() => {
  const id = store.selected
  if (!id) return []
  const l = store.langs.find((x) => x.wals_id === id)
  if (!l) return []

  const all = store.langs
  const feat = store.featureCount
  const depth = store.descDepth
  const works = store.docWorks
  const proj = store.wikiProjects

  // 每个维度都只在"有该数据的语言"里算百分位，否则会被大量缺失值稀释
  const pop = <T,>(get: (x: (typeof all)[number]) => T | null | undefined) => {
    const out: number[] = []
    for (const x of all) {
      const v = get(x)
      if (typeof v === 'number' && Number.isFinite(v)) out.push(v)
    }
    return out
  }

  const defs = [
    {
      key: 'feat', label: t.value.feat, inverse: false,
      pop: pop((x) => feat[x.wals_id]), v: feat[l.wals_id],
      fmt: (n: number) => `${n}`,
    },
    {
      key: 'depth', label: t.value.depth, inverse: false,
      pop: pop((x) => depth[x.wals_id]?.depth), v: depth[l.wals_id]?.depth,
      fmt: (n: number) => `${n} / 5`,
    },
    {
      key: 'works', label: t.value.works, inverse: false,
      pop: pop((x) => works[x.wals_id]?.works), v: works[l.wals_id]?.works,
      fmt: (n: number) => `${n}`,
    },
    {
      key: 'views', label: t.value.views, inverse: false,
      pop: pop((x) => x.views_recent), v: l.views_recent ?? null,
      fmt: (n: number) => n.toLocaleString('en-US'),
    },
    {
      key: 'proj', label: t.value.proj, inverse: false,
      pop: pop((x) => proj[x.wals_id]?.n_extra), v: proj[l.wals_id]?.n_extra,
      fmt: (n: number) => `${n}`,
    },
  ]
  return defs.map((d) => ({
    key: d.key,
    label: d.label,
    text: d.v == null ? t.value.noData : d.fmt(Number(d.v)),
    pct: pctOf(d.pop, d.v as number | null),
    inverse: d.inverse,
  }))
})

/** 反差提示：被研究得深（前 25%）却几乎没人读（后 25% 或没有浏览量） */
const tension = computed(() => {
  const r = rows.value
  if (r.length < 4) return null
  const works = r.find((x) => x.key === 'works')?.pct
  const feat = r.find((x) => x.key === 'feat')?.pct
  const views = r.find((x) => x.key === 'views')?.pct
  const research = Math.max(works ?? 0, feat ?? 0)
  if (research < 0.75) return null
  if (views != null && views > 0.25) return null
  return {
    hi: Math.round(research * 100),
    lo: views == null ? 0 : Math.round(views * 100),
  }
})
</script>

<template>
  <section v-if="rows.length" class="health">
    <header>
      <h4>{{ t.title }}</h4>
      <span class="sub">{{ t.sub }}</span>
    </header>

    <div v-for="r in rows" :key="r.key" class="row">
      <span class="lab">{{ r.label }}</span>
      <span class="track">
        <i :style="{ width: r.pct == null ? '0%' : (r.pct * 100).toFixed(1) + '%' }" />
      </span>
      <span class="val num">{{ r.text }}</span>
      <span class="pc num">{{ r.pct == null ? '—' : t.pct(r.pct) }}</span>
    </div>

    <p v-if="tension" class="tension">
      <b>{{ t.tension }}</b>
      {{ t.tResearch(String(tension.lo), String(tension.hi)) }}
    </p>
  </section>
</template>

<style scoped>
.health {
  flex: none; margin-top: var(--sp-3);
  background: var(--bg-surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: var(--sp-3);
}
header { display: flex; align-items: baseline; gap: 8px; margin-bottom: 9px; }
h4 { margin: 0; font-size: var(--fs-small); font-weight: 700; }
.sub { font-size: 10px; color: var(--text-muted); line-height: 1.4; }

.row { display: flex; align-items: center; gap: 7px; margin-bottom: 5px; }
.lab {
  flex: none; width: 76px; font-size: var(--fs-micro); color: var(--text-secondary);
  white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.track {
  flex: 1; height: 8px; border-radius: 5px; background: var(--bg-subtle);
  overflow: hidden;
}
.track i {
  display: block; height: 100%; border-radius: 5px;
  background: var(--accent); opacity: .62;
  transition: width 320ms cubic-bezier(.22,.61,.36,1);
}
.val {
  flex: none; width: 58px; text-align: right;
  font-size: var(--fs-micro); color: var(--text-secondary);
}
.pc {
  flex: none; width: 62px; text-align: right;
  font-size: 10px; color: var(--text-muted);
}

.tension {
  margin: 9px 0 0; padding: 8px 10px;
  background: var(--bg-canvas); border-left: 2px solid var(--accent);
  border-radius: 4px; font-size: var(--fs-micro); color: var(--text-secondary);
  line-height: 1.65;
}
.tension b { color: var(--accent); margin-right: 3px; }
</style>
