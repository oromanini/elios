const trimTrailingSlash = (value) => value.replace(/\/+$/, '');

const readViteEnv = () => {
  try {
    return import.meta.env?.VITE_API_URL?.trim();
  } catch (error) {
    return '';
  }
};

const getBackendUrlFromBrowserHost = () => {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000';
  }

  const { protocol, hostname } = window.location;

  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return 'http://localhost:8000';
  }

  return `${protocol}//${hostname}:8000`;
};

export const getBackendBaseUrl = () => {
  const configuredUrl = readViteEnv() || process.env.REACT_APP_BACKEND_URL?.trim();

  if (configuredUrl) {
    return trimTrailingSlash(configuredUrl);
  }

  const fallbackUrl = getBackendUrlFromBrowserHost();
  console.warn(
    `[ELIOS] VITE_API_URL não configurada. Usando fallback: ${fallbackUrl}`
  );

  return fallbackUrl;
};
