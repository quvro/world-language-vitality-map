import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, type Plugin } from 'vite'
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
  return {
    name: 'nl-query-proxy',
    configureServer(server) {
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

          const key = process.env.DEEPSEEK_API_KEY || process.env.LLM_API_KEY
          if (!key) return json({ ok: false, reason: 'no-key' })

          const base = (process.env.LLM_BASE_URL || 'https://api.deepseek.com')
            .replace(/\/+$/, '')
          const model = process.env.LLM_MODEL || 'deepseek-chat'
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
      ignored: ['**/*.tmpdir/**', '**/preview/**', '**/dist/**'],
    },
  },
})
