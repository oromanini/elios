const trimTrailingSlash = (value) => value.replace(/\/+$/, '');

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
  const configuredUrl = process.env.REACT_APP_BACKEND_URL?.trim();

  if (configuredUrl) {
    return trimTrailingSlash(configuredUrl);
  }

  const fallbackUrl = getBackendUrlFromBrowserHost();
  console.warn(
    `[ELIOS] REACT_APP_BACKEND_URL não configurada. Usando fallback: ${fallbackUrl}`
  );

  return fallbackUrl;
};
