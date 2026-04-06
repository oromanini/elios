import axios from 'axios';

import { getBackendBaseUrl } from '../config/apiBaseUrl';

const API_URL = getBackendBaseUrl();
export const AUTH_UNAUTHORIZED_EVENT = 'elios:auth-unauthorized';

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('elios_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('elios_token');
      localStorage.removeItem('elios_user');
      window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data)
};

// Questions API
export const questionsAPI = {
  getAll: () => api.get('/questions'),
  getAllAdmin: () => api.get('/admin/questions'),
  create: (data) => api.post('/admin/questions', data),
  update: (id, data) => api.put(`/admin/questions/${id}`, data),
  delete: (id) => api.delete(`/admin/questions/${id}`)
};

// Form API
export const formAPI = {
  submit: (data) => api.post('/form/submit', data, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }),
  getResponses: () => api.get('/form/responses'),
  updateResponse: (id, data) => api.put(`/form/responses/${id}`, data)
};

// Goals API
export const goalsAPI = {
  getAll: () => api.get('/goals'),
  getByPillar: (pillar) => api.get(`/goals/pillar/${pillar}`),
  create: (data) => api.post('/goals', data),
  update: (id, data) => api.put(`/goals/${id}`, data),
  delete: (id) => api.delete(`/goals/${id}`),
  getHistory: (id) => api.get(`/goals/${id}/history`)
};

// AI API
export const aiAPI = {
  analyze: (data) => api.post('/ai/analyze', data),
  chat: (data) => api.post('/ai/chat', data),
  getChatHistory: () => api.get('/ai/chat/history'),
  clearChatHistory: () => api.delete('/ai/chat/history')
};

// Admin API
export const adminAPI = {
  getUsers: () => api.get('/admin/users'),
  updateUser: (id, data) => api.put(`/admin/users/${id}`, data),
  deleteUser: (id) => api.delete(`/admin/users/${id}`),
  getAIKnowledge: () => api.get('/admin/ai/knowledge'),
  addAIKnowledge: (data) => api.post('/admin/ai/knowledge', data),
  deleteAIKnowledge: (id) => api.delete(`/admin/ai/knowledge/${id}`)
};

// Dashboard API
export const dashboardAPI = {
  getStats: () => api.get('/dashboard/stats')
};

// Init API (run once)
export const initAPI = {
  initQuestions: () => api.post('/init/questions'),
  initAdmin: () => api.post('/init/admin')
};

export default api;
