/**
 * 验证脚本的共享脚手架：把**真实 TS 源码**转成 JS 再加载。
 *
 * 为什么不用 Vite 的 `ssrLoadModule`：它加载 `vite.config.ts` 时要 esbuild 起子进程，
 * 沙箱直接 `spawn EPERM`（既定边界，不该反复重试）。
 * TypeScript 的 `transpileModule` 在本进程内运行、不起子进程，正好合适。
 *
 * 用法：
 *   const h = await createHarness()
 *   const { toQuery } = await h.load('urlState.ts')
 *   h.cleanup()   // 删掉临时目录
 */
import { mkdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'
import { pathToFileURL } from 'node:url'

const require = createRequire(import.meta.url)
const ts = require('typescript')

const WEB = path.resolve('web')
const SRC = path.join(WEB, 'src')
const DATA = path.resolve('data/processed')
const TMP = path.join(WEB, '.verify-tmp')

/** 这些文件是所有验证脚本共同的依赖；按需转译，转过的复用 */
const DEPS = {
  'terms.ts': ['terms.ts', 'terms.js', 0],
  'types.ts': ['types.ts', 'types.js', 0],
  'story.ts': ['story.ts', 'story.js', 0],
  'urlState.ts': ['urlState.ts', 'urlState.js', 0],
  'hull.ts': ['hull.ts', 'hull.js', 0],
  'stores/dataset.ts': ['stores/dataset.ts', 'stores/dataset.js', 1],
}

function emit(rel, outName, depth) {
  const out = ts.transpileModule(readFileSync(path.join(SRC, rel), 'utf8'), {
    compilerOptions: {
      module: ts.ModuleKind.ESNext,
      target: ts.ScriptTarget.ES2022,
      verbatimModuleSyntax: false,
    },
  }).outputText
  const up = depth > 0 ? '../'.repeat(depth) : './'
  // @/ 别名改写成相对路径（Node 不认识 tsconfig 的 paths）
  const fixed = out.replace(/from ['"]@\/([\w./-]+)['"]/g, (_m, p) => `from '${up}${p}.js'`)
  writeFileSync(path.join(TMP, outName), fixed)
}

export async function createHarness() {
  rmSync(TMP, { recursive: true, force: true })
  mkdirSync(path.join(TMP, 'stores'), { recursive: true })

  // store 的 loadJson 会 fetch('/data/processed/xxx.json')，改成读磁盘
  const realFetch = globalThis.fetch
  globalThis.fetch = async (url) => {
    try {
      const text = readFileSync(path.join(DATA, String(url).replace(/^\/data\/processed\//, '')), 'utf8')
      return { ok: true, status: 200, json: async () => JSON.parse(text) }
    } catch {
      return { ok: false, status: 404 }
    }
  }
  // urlState 的 shareUrl / startUrlSync 会读 location
  const realLocation = globalThis.location
  globalThis.location = { origin: 'http://127.0.0.1:5173', pathname: '/', search: '' }

  // pinia 必须与 store 模块走**同一条** ESM 路径。
  // 一边 require(CJS) 一边 import(ESM) 会拿到两个模块实例，setActivePinia 就不生效。
  const { createPinia, setActivePinia } = await import('pinia')

  /** 加载 src 下的某个 TS 文件（只支持 DEPS 里列过的依赖图） */
  async function load(rel) {
    const key = rel.replace(/\\/g, '/')
    if (!DEPS[key]) throw new Error(`${rel} 不在 DEPS 里，请先登记`)
    for (const dep of Object.values(DEPS)) emit(...dep)
    // 带上时间戳避免 Node 的模块缓存（同一进程里反复 load 同一路径）
    return import(`${pathToFileURL(path.join(TMP, DEPS[key][1])).href}?t=${loadSeq++}`)
  }
  let loadSeq = 0

  /** 每调用一次就得到一个全新的、已加载好数据的 store */
  async function freshStore() {
    setActivePinia(createPinia())
    const { useDataset } = await load('stores/dataset.ts')
    const s = useDataset()
    await s.load()
    return s
  }

  function cleanup() {
    rmSync(TMP, { recursive: true, force: true })
    globalThis.fetch = realFetch
    globalThis.location = realLocation
  }

  return { load, freshStore, cleanup }
}
