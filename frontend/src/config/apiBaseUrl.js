const trimTrailingSlash = (value) => value.replace(/\/+$/, '');

const DEFAULT_API_URL = 'https://elios-api-513240742946.us-central1.run.app';

export const API_BASE_URL =
  import.meta.env.VITE_API_URL ||
  process.env.REACT_APP_BACKEND_URL ||
  DEFAULT_API_URL;

export const getBackendBaseUrl = () => trimTrailingSlash(API_BASE_URL);
