import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],

  server: {
    // Bind to 127.0.0.1 so the dev server and the API (also on 127.0.0.1)
    // share a host. Browsers decide SameSite by host, ignoring the port, so
    // serving this on "localhost" while calling the API on "127.0.0.1" would
    // be cross-site and the httpOnly session cookie would be dropped.
    host: '127.0.0.1',
  },
})
