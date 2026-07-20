import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'
import fs from 'fs'
import path from 'path'

const certDir = path.resolve(__dirname, '../certs')

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      devOptions: { enabled: true },
      // Only precache the app shell — there's no meaningful offline mode
      // since this tool is useless without the LAN server.
      workbox: {
        globPatterns: ['**/*.{js,css,html}'],
      },
      manifest: {
        name: 'מעקב לקוחות',
        short_name: 'מעקב לקוחות',
        description: 'מעקב שעות וחיוב לקוחות למשרד',
        lang: 'he',
        dir: 'rtl',
        start_url: '/',
        display: 'standalone',
        background_color: '#f6f7f9',
        theme_color: '#f2660c',
        icons: [
          { src: '/icons/icon-192.png', sizes: '192x192', type: 'image/png' },
          { src: '/icons/icon-512.png', sizes: '512x512', type: 'image/png' },
        ],
      },
    }),
  ],
  server: {
    host: true,
    https: {
      cert: fs.readFileSync(path.join(certDir, 'cert.pem')),
      key: fs.readFileSync(path.join(certDir, 'key.pem')),
    },
  },
  preview: {
    host: true,
    https: {
      cert: fs.readFileSync(path.join(certDir, 'cert.pem')),
      key: fs.readFileSync(path.join(certDir, 'key.pem')),
    },
  },
})
