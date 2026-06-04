import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const API_TARGET = 'http://127.0.0.1:8000'

function skytApiRedirect() {
  return {
    name: 'skyt-api-redirect',
    configureServer(server) {
      server.middlewares.use('/api', (req, res) => {
        res.statusCode = 307
        res.setHeader('Location', `${API_TARGET}/api${req.url || ''}`)
        res.setHeader('Cache-Control', 'no-store')
        res.end()
      })
    }
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [skytApiRedirect(), react()]
})
