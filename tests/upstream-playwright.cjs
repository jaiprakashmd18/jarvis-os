const path = require('path');
const source = process.env.JARVIS_SOURCE;
if (!source || !path.isAbsolute(source)) throw new Error('Set JARVIS_SOURCE to the pinned checkout');
module.exports = {
  testDir: path.join(source, 'apps/web/e2e'),
  testIgnore: ['deployed.spec.ts'],
  timeout: 30000, workers: 1,
  outputDir: path.resolve(__dirname, '../build/playwright-results'),
  use: { baseURL: 'http://localhost:3100', trace: 'retain-on-failure',
    launchOptions: { executablePath: '/usr/bin/chromium', args: ['--no-sandbox','--use-fake-ui-for-media-stream','--use-fake-device-for-media-stream'] },
    permissions: ['microphone'] },
  webServer: [
    { command: '.venv/bin/uvicorn jarvis_api.main:create_app --factory --host 127.0.0.1 --port 8000',
      cwd: source, url: 'http://localhost:8000/api/system/ping', reuseExistingServer: false,
      env: { JARVIS_DATABASE_URL: 'sqlite:///'+path.resolve(__dirname,'../build/e2e.db'),
        JARVIS_SECRET_KEY_FILE: path.resolve(__dirname,'../build/e2e-secret.key'),
        JARVIS_ENABLE_DIAGNOSTIC_PROVIDER: 'true', JARVIS_DEFAULT_CHAT_PROVIDER: 'diagnostic',
        JARVIS_OLLAMA_URL: 'http://127.0.0.1:9', JARVIS_STT_ENGINE: 'diagnostic',
        JARVIS_TTS_ENGINE: process.env.E2E_TTS || 'diagnostic', JARVIS_ALLOWED_ORIGINS: '["http://localhost:3100"]' } },
    { command: 'npm exec -- next start -H 127.0.0.1 -p 3100', cwd: path.join(source,'apps/web'),
      url: 'http://localhost:3100/login', reuseExistingServer: false }
  ]
};
