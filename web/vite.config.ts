import { fileURLToPath, URL } from 'node:url'
import fs from 'node:fs'
import path from 'node:path'
import { defineConfig, type Plugin } from 'vite'
import vue from '@vitejs/plugin-vue'

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

export default defineConfig({
  plugins: [vue(), dataPlugin()],
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
