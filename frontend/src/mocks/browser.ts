import { worker } from './handlers';

export async function enableMocking() {
  if (process.env.NODE_ENV !== 'development') {
    return;
  }

  // Check if mock mode is enabled via Vite env
  if (import.meta.env.VITE_MOCK_MODE !== 'true') {
    return;
  }

  try {
    await worker.start({
      onUnhandledRequest: 'bypass',
      serviceWorker: {
        url: '/mockServiceWorker.js',
      },
    });
    console.log('[MSW] Mocking enabled');
  } catch (error) {
    console.error('[MSW] Failed to start mocking:', error);
  }
}
