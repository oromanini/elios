import axios from 'axios';

import { getBackendBaseUrl } from '../config/apiBaseUrl';

const API_URL = getBackendBaseUrl();
export const AUTH_UNAUTHORIZED_EVENT = 'elios:auth-unauthorized';
axios.defaults.withCredentials = true;

const api = axios.create({
  baseURL: `${API_URL}/api`,
  withCredentials: true,
  headers: {
    'Content-Type': 'application/json'
  }
});

// Handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      window.dispatchEvent(new CustomEvent(AUTH_UNAUTHORIZED_EVENT));
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  logout: () => api.post('/auth/logout'),
  register: (data) => api.post('/auth/register', data),
  getMe: () => api.get('/auth/me'),
  changePassword: (data) => api.post('/auth/change-password', data),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  resetPassword: (token, new_password) => api.post('/auth/reset-password', { token, new_password })
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
  createUser: (data) => api.post('/admin/users', data),
  getUsersFormResponses: (params = {}) => api.get('/admin/users/form-responses', { params }),
  updateUserGoal: (userId, goalId, data) => api.put(`/admin/users/${userId}/goals/${goalId}`, data),
  updateUser: (id, data) => api.put(`/admin/users/${id}`, data),
  uploadUserPhoto: (id, formData) => api.post(`/admin/users/${id}/profile-photo`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  }),
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
