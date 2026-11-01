import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, type Plugin, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'
// 与前端共用同一份意图定义，避免字段漂移
import { INTENT_SCHEMA } from './shared/intent.js'

const here = path.dirname(fileURLToPath(import.meta.url))
/** 数据管道产出在 web/ 之外，需要显式挂载到 /data 下。 */
const DATA_DIR = path.resolve(here, '../data')

/**
 * 把 ../data 以 /data 前缀暴露给前端。
 * dev 走中间件（改数据不用重启），build 时复制进 dist，保证产物可独立部署。
 */
function dataPlugin(): Plugin {
  return {
    name: 'serve-project-data',
    configureServer(server) {
      server.middlewares.use('/data', (req, res, next) => {
        const rel = decodeURIComponent((req.url || '').split('?')[0])
        const file = path.join(DATA_DIR, rel)
        // 防目录穿越：解析后必须仍在 DATA_DIR 内
        if (!path.resolve(file).startsWith(DATA_DIR)) return next()
        if (!fs.existsSync(file) || !fs.statSync(file).isFile()) return next()
        res.setHeader('Content-Type', 'application/json; charset=utf-8')
        res.setHeader('Cache-Control', 'no-store')
        fs.createReadStream(file).pipe(res)
      })
    },
    closeBundle() {
      // 数据可独立部署：拷进 dist。vendor 放在 public/ 下，
      // Vite 会自动原样复制（放 public 之外的 .js 会被当模块转换，破坏传统脚本）
      const src = path.join(DATA_DIR, 'processed')
      const dest = path.resolve(here, 'dist/data/processed')
      if (!fs.existsSync(src)) return
      fs.mkdirSync(dest, { recursive: true })
      for (const f of fs.readdirSync(src)) {
        if (f.endsWith('.json')) fs.copyFileSync(path.join(src, f), path.join(dest, f))
      }
    },
  }
}

/**
 * 自然语言查询代理。
 *
 * 为什么要在服务端转发而不是浏览器直连大模型：
 *   1. API Key 不能进浏览器（会被抓包 / 打包进产物）
 *   2. 大模型接口一般不开放浏览器 CORS
 *
 * 没有配置 Key 时返回 reason='no-key'，前端自动退回本地规则解析器 ——
 * 课程演示不能因为没配密钥就整个废掉。
 *
 * 环境变量（都可选）：
 *   DEEPSEEK_API_KEY / LLM_API_KEY   密钥
 *   LLM_BASE_URL                     默认 https://api.deepseek.com
 *   LLM_MODEL                        默认 deepseek-chat
 */
const SYSTEM_PROMPT = [
  '你是「世界语言赛博活力图谱」的查询解析器，把用户的自然语言问题翻译成筛选条件。',
  '规则：',
  '- featureId 必须来自我给出的特征列表，families 必须来自我给出的语系列表，不要自创。',
  '- 只填用户明确表达的意图，不要臆测。没提到的字段留空。',
  '- 增长率的单位是百分数：用户说「在增长」→ growthMin=0；「在衰退」→ growthMax=0。',
  '- explanation 用与用户提问相同的语言，一句话复述你理解到的筛选意图。',
  '注意：你只负责翻译成条件，不要计算任何统计数字。',
].join('\n')

function nlPlugin(): Plugin {
  // 密钥可以放在 web/.env.local（已被 .gitignore 挡住），不必每次设系统环境变量。
  // 第三个参数传 '' 表示不限定前缀 —— 否则只有 VITE_ 开头的变量才会被加载，
  // 而密钥恰恰不该带 VITE_ 前缀（那会被打进前端产物）。
  const fileEnv = loadEnv(process.env.NODE_ENV || 'development', process.cwd(), '')
  /** 先看系统环境变量，再看 .env 文件 */
  const env = (k: string): string | undefined => process.env[k] ?? fileEnv[k]

  return {
    name: 'nl-query-proxy',
    configureServer(server) {
      // ---- 第二段：把「检索到的证据」交给大模型措辞 ----
      //
      // 刻意只让模型做措辞，不让它算数：数字全部由前端在真实数据上算出，
      // 这里只是把它们写成人话。所以即使模型出错，也不会出现"编造的数字"。
      //
      // ⚠️ 必须注册在 '/api/nl' **之前** —— use(path, fn) 是前缀匹配，
      // 否则 /api/nl/answer 的请求会先落到 /api/nl 那个处理器上。
      server.middlewares.use('/api/nl/answer', (req, res, next) => {
        if (req.method !== 'POST') return next()
        const chunks: Buffer[] = []
        req.on('data', (c: Buffer) => chunks.push(c))
        req.on('end', async () => {
          const json = (obj: unknown, code = 200) => {
            res.statusCode = code
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(JSON.stringify(obj))
          }
          let body: {
            question?: string
            intent?: unknown
            evidence?: unknown
            lang?: string
          } = {}
          try {
            body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')
          } catch {
            return json({ ok: false, reason: 'bad-request' }, 400)
          }
          const key = env('DEEPSEEK_API_KEY') || env('LLM_API_KEY')
          if (!key) return json({ ok: false, reason: 'no-key' })

          const base = (env('LLM_BASE_URL') || 'https://api.deepseek.com')
            .replace(/\/+$/, '')
          const model = env('LLM_MODEL') || 'deepseek-chat'
          const zh = (body.lang ?? 'zh') !== 'en'
          const sys = zh
            ? [
              '你是数据可视化系统的解说员。用户会给：一个提问、一组筛选条件、',
              '以及从数据集里**算好的**证据（JSON）。',
              '请**只依据证据**写答案：不要编造数字，不要引入证据之外的常识或外部知识。',
              '如果证据显示命中数为 0，就直说没有命中，并建议放宽哪个条件。',
              '证据里带 Pct / Text 后缀的字段**已经是格式化好的**（例如 medianPct="+133.7%"、'
              'viewsText="645,562"），直接引用，不要再做任何换算；'
              '带 label 的字段也直接引用 label，不要输出 lv 这类内部字段名。',
              '输出严格 JSON：{"title": string, "lead": string, "bullets": string[],',
              '"caveats": string[]}。',
              'title 不超过 20 字；lead 一句话结论；bullets 3–5 条，每条以 **加粗关键词** 开头；',
              'caveats 0–2 条，写口径说明或局限（例如"这批语言都没有维基版本，',
              '所以时间序列里是缺席而不是 0"）。用中文。',
            ].join('')
            : [
              'You are the narrator of a data-visualisation system. The user sends a question, ',
              'the filters used, and evidence computed from the dataset. ',
              'Write the answer from the evidence ONLY: never invent numbers, never add outside knowledge. ',
              'Respond with strict JSON: {"title","lead","bullets":[],"caveats":[]}. ',
              'bullets 3–5 items, each starting with a **bold keyword**. Answer in English.',
            ].join('')

          // 证据包本身不大，但仍截断一下，避免异常输入把上下文撑爆
          const payload = JSON.stringify({
            question: body.question,
            filters: body.intent,
            evidence: body.evidence,
          }).slice(0, 6000)

          try {
            const upstream = await fetch(`${base}/chat/completions`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${key}`,
              },
              body: JSON.stringify({
                model,
                temperature: 0.2,
                response_format: { type: 'json_object' },
                messages: [
                  { role: 'system', content: sys },
                  { role: 'user', content: payload },
                ],
              }),
              signal: AbortSignal.timeout(40_000),
            })
            if (!upstream.ok) {
              const detail = (await upstream.text()).slice(0, 200)
              return json({ ok: false, reason: `upstream-${upstream.status}`, detail })
            }
            const data: any = await upstream.json()
            const text = data?.choices?.[0]?.message?.content ?? ''
            let answer: any = null
            try {
              answer = JSON.parse(text)
            } catch {
              return json({ ok: false, reason: 'bad-json' })
            }
            if (!answer || typeof answer.title !== 'string'
              || typeof answer.lead !== 'string'
              || !Array.isArray(answer.bullets)) {
              return json({ ok: false, reason: 'bad-shape' })
            }
            return json({
              ok: true,
              model,
              answer: {
                title: String(answer.title).slice(0, 80),
                lead: String(answer.lead).slice(0, 400),
                bullets: answer.bullets.filter((x: unknown) => typeof x === 'string')
                  .slice(0, 6).map((x: string) => x.slice(0, 300)),
                caveats: Array.isArray(answer.caveats)
                  ? answer.caveats.filter((x: unknown) => typeof x === 'string')
                    .slice(0, 3).map((x: string) => x.slice(0, 300))
                  : [],
              },
            })
          } catch (e: any) {
            return json({ ok: false, reason: 'upstream-error', detail: String(e?.message ?? e) })
          }
        })
      })

      server.middlewares.use('/api/nl', (req, res, next) => {
        if (req.method !== 'POST') return next()
        const chunks: Buffer[] = []
        req.on('data', (c: Buffer) => chunks.push(c))
        req.on('end', async () => {
          const json = (obj: unknown, code = 200) => {
            res.statusCode = code
            res.setHeader('Content-Type', 'application/json; charset=utf-8')
            res.end(JSON.stringify(obj))
          }
          let payload: { question?: string; context?: Record<string, unknown> } = {}
          try {
            payload = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}')
          } catch {
            return json({ ok: false, reason: 'bad-request' }, 400)
          }

          const key = env('DEEPSEEK_API_KEY') || env('LLM_API_KEY')
          if (!key) return json({ ok: false, reason: 'no-key' })

          const base = (env('LLM_BASE_URL') || 'https://api.deepseek.com')
            .replace(/\/+$/, '')
          const model = env('LLM_MODEL') || 'deepseek-chat'
          const ctx = payload.context || {}
          const userMsg = [
            `可用语系（families 只能取自这里）：${JSON.stringify(ctx.families ?? [])}`,
            `可选特征（featureId 只能取自这里，格式为 "ID 名称"）：`,
            JSON.stringify(ctx.features ?? []),
            '',
            `用户问题：${payload.question ?? ''}`,
          ].join('\n')

          try {
            const upstream = await fetch(`${base}/chat/completions`, {
              method: 'POST',
              headers: {
                'Content-Type': 'application/json',
                Authorization: `Bearer ${key}`,
              },
              body: JSON.stringify({
                model,
                temperature: 0,
                messages: [
                  { role: 'system', content: SYSTEM_PROMPT },
                  { role: 'user', content: userMsg },
                ],
                tools: [{
                  type: 'function',
                  function: {
                    name: 'set_filters',
                    description: '设置可视化看板的筛选条件',
                    parameters: INTENT_SCHEMA,
                  },
                }],
                tool_choice: { type: 'function', function: { name: 'set_filters' } },
              }),
              signal: AbortSignal.timeout(30_000),
            })
            if (!upstream.ok) {
              const detail = (await upstream.text()).slice(0, 300)
              return json({ ok: false, reason: `upstream-${upstream.status}`, detail })
            }
            const data: any = await upstream.json()
            const call = data?.choices?.[0]?.message?.tool_calls?.[0]
            let args: Record<string, unknown> = {}
            try {
              args = JSON.parse(call?.function?.arguments || '{}')
            } catch {
              return json({ ok: false, reason: 'bad-arguments' })
            }
            return json({ ok: true, intent: args, source: 'llm', model })
          } catch (err) {
            const msg = err instanceof Error ? err.message : String(err)
            return json({ ok: false, reason: 'request-failed', detail: msg.slice(0, 200) })
          }
        })
      })
    },
  }
}

export default defineConfig({
  plugins: [vue(), dataPlugin(), nlPlugin()],
  resolve: {
    alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) },
  },
  server: {
    host: '127.0.0.1',
    port: 5173,
    // 编辑器的原子写在 web/ 下会短暂生成 .*.tmpdir 临时目录，
    // Vite 的监听器去 watch 它会撞上 EBUSY 而整个崩掉 —— 必须忽略。
    // preview/ 是零构建的静态预览页，也不需要监听。
    watch: {
      ignored: [
        '**/*.tmpdir/**', '**/preview/**', '**/dist/**',
        // Windows 在资源管理器里复制文件会自动加「- 副本」，
        // 这类文件若恰好叫 .env* 就会被 Vite 监听，一旦被占用
        // 就抛 EBUSY 把整个开发服务器带崩（实测踩过一次）。
        '**/*副本*',
      ],
    },
  },
})
