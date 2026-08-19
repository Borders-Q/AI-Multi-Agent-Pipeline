const nativeFetch = window.fetch.bind(window);

export async function apiFetch(input, init = {}) {
  const { timeoutMs, ...requestInit } = init;
  const controller = timeoutMs ? new AbortController() : null;
  const timeout = controller ? window.setTimeout(() => controller.abort(), timeoutMs) : null;
  const response = await nativeFetch(input, {
    credentials: 'include',
    ...requestInit,
    ...(controller ? { signal: requestInit.signal || controller.signal } : {}),
  });
  if (timeout) window.clearTimeout(timeout);
  if (response.status === 401) {
    window.dispatchEvent(new CustomEvent('skyt:auth-required'));
  }
  return response;
}

export async function readApiError(response, fallback = '请求失败') {
  try {
    const data = await response.clone().json();
    return data.detail || data.message || fallback;
  } catch {
    return fallback;
  }
}

export function installApiClient() {
  if (window.fetch.__skytApiClient) return;
  const wrappedFetch = (input, init) => apiFetch(input, init);
  wrappedFetch.__skytApiClient = true;
  window.fetch = wrappedFetch;
}
