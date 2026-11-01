"""让服务端能从 web/.env.local 读密钥（现在只认系统环境变量）。

不这么做的话，用户每次都得在 shell 里 export，重启终端就忘；
而 .env.local 是前端圈的标准做法，且已被 .gitignore 挡住。
"""

import io
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

P = "web/vite.config.ts"
s = io.open(P, encoding="utf-8").read()

if "loadEnv" in s:
    print("  已支持 loadEnv，跳过")
    raise SystemExit(0)

# 1) 扩展 vite 的导入
import re
m = re.search(r"import \{([^}]*)\} from 'vite'", s)
if m:
    names = [x.strip() for x in m.group(1).split(",") if x.strip()]
    if "loadEnv" not in names:
        names.append("loadEnv")
    s = s[:m.start()] + "import { " + ", ".join(names) + " } from 'vite'" + s[m.end():]
    print("  ok   import 已加 loadEnv")
else:
    s = "import { loadEnv } from 'vite'\n" + s
    print("  ok   已补 import 行")

# 2) 在 nlPlugin 里加载文件环境变量，并提供一个统一的取值函数
OLD = "function nlPlugin(): Plugin {\n  return {"
NEW = '''function nlPlugin(): Plugin {
  // 密钥可以放在 web/.env.local（已被 .gitignore 挡住），不必每次设系统环境变量。
  // 第三个参数传 '' 表示不限定前缀 —— 否则只有 VITE_ 开头的变量才会被加载，
  // 而密钥恰恰不该带 VITE_ 前缀（那会被打进前端产物）。
  const fileEnv = loadEnv(process.env.NODE_ENV || 'development', process.cwd(), '')
  /** 先看系统环境变量，再看 .env 文件 */
  const env = (k: string): string | undefined => process.env[k] ?? fileEnv[k]

  return {'''
if OLD in s:
    s = s.replace(OLD, NEW, 1)
    print("  ok   nlPlugin 已加载 fileEnv")
else:
    print("  MISS nlPlugin 入口")

# 3) 把 6 处 process.env.X 换成 env('X')
for k in ("DEEPSEEK_API_KEY", "LLM_API_KEY", "LLM_BASE_URL", "LLM_MODEL"):
    s = s.replace(f"process.env.{k}", f"env('{k}')")
print("  ok   process.env.* → env('*')")

io.open(P, "w", encoding="utf-8").write(s)
