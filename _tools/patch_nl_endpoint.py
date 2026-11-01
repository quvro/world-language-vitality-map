"""在 vite.config.ts 里加 /api/nl/answer：把前端检索出的证据交给大模型措辞。

注意顺序：`server.middlewares.use(path, fn)` 是**前缀匹配**，
所以 `/api/nl` 会把 `/api/nl/answer` 也吃掉。必须把更具体的路径注册在前面。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/vite.config.ts"
s = io.open(P, encoding="utf-8").read()

ANCHOR = "      server.middlewares.use('/api/nl', (req, res, next) => {"
if ANCHOR not in s:
    print("  MISS 找不到 /api/nl 注册点")
    raise SystemExit(1)

BLOCK = '''      // ---- 第二段：把「检索到的证据」交给大模型措辞 ----
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
          const key = process.env.DEEPSEEK_API_KEY || process.env.LLM_API_KEY
          if (!key) return json({ ok: false, reason: 'no-key' })

          const base = (process.env.LLM_BASE_URL || 'https://api.deepseek.com')
            .replace(/\\/+$/, '')
          const model = process.env.LLM_MODEL || 'deepseek-chat'
          const zh = (body.lang ?? 'zh') !== 'en'
          const sys = zh
            ? [
              '你是数据可视化系统的解说员。用户会给：一个提问、一组筛选条件、',
              '以及从数据集里**算好的**证据（JSON）。',
              '请**只依据证据**写答案：不要编造数字，不要引入证据之外的常识或外部知识。',
              '如果证据显示命中数为 0，就直说没有命中，并建议放宽哪个条件。',
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

'''

s = s.replace(ANCHOR, BLOCK + ANCHOR, 1)
io.open(P, "w", encoding="utf-8").write(s)
print("  已插入 /api/nl/answer（注册在 /api/nl 之前）")
