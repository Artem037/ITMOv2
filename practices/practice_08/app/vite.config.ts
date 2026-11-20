import { fileURLToPath, URL } from 'node:url';
import type { IncomingMessage, ServerResponse } from 'node:http';
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv, type Plugin, type ProxyOptions } from 'vite';

function issuePublicationGuard(configured: boolean): Plugin {
  function guard(request: IncomingMessage, response: ServerResponse, next: () => void) {
    if (request.url !== '/api/issues') return next();

    function reject(status: number, code: string) {
      response.writeHead(status, { 'Content-Type': 'application/json', 'Cache-Control': 'no-store' });
      response.end(JSON.stringify({ code }));
    }

    if (request.method !== 'POST') {
      response.setHeader('Allow', 'POST');
      return reject(405, 'method_not_allowed');
    }
    if (request.headers.origin && request.headers.origin !== `http://${request.headers.host}`) {
      return reject(403, 'origin_not_allowed');
    }
    const contentType = request.headers['content-type']?.split(';')[0].trim();
    if (contentType !== 'application/json') return reject(415, 'expected_json');
    if (!configured) return reject(503, 'publication_not_configured');

    next();
  }

  return {
    name: 'issue-publication-guard',
    configureServer(server) {
      server.middlewares.use(guard);
    },
    configurePreviewServer(server) {
      server.middlewares.use(guard);
    },
  };
}

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '');
  const webhook = new URL(
    env.N8N_WEBHOOK_URL || 'https://n8n-itmo.cyrweb.ru/webhook/practice-08-issue-review',
  );
  const proxy: Record<string, ProxyOptions> = {
    '/api/issue-review': {
      target: webhook.origin,
      changeOrigin: true,
      rewrite: () => webhook.pathname + webhook.search,
      headers: env.N8N_WEBHOOK_KEY ? { 'X-Issue-Review-Key': env.N8N_WEBHOOK_KEY } : undefined,
    },
  };
  const createWebhook = env.N8N_CREATE_ISSUE_URL && env.N8N_CREATE_ISSUE_KEY?.trim()
    ? new URL(env.N8N_CREATE_ISSUE_URL)
    : null;
  if (createWebhook) {
    proxy['^/api/issues$'] = {
      target: createWebhook.origin,
      changeOrigin: true,
      rewrite: () => createWebhook.pathname + createWebhook.search,
      headers: { 'X-Issue-Create-Key': env.N8N_CREATE_ISSUE_KEY },
    };
  }

  return {
    plugins: [react(), tailwindcss(), issuePublicationGuard(Boolean(createWebhook))],
    resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
    server: { host: '127.0.0.1', proxy },
    preview: { host: '127.0.0.1', proxy },
  };
});
