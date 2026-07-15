import { apiPost, apiGet } from './api.js';

export function getToken() {
  return localStorage.getItem('studymate-token');
}

export function getUser() {
  const data = localStorage.getItem('studymate-user');
  return data ? JSON.parse(data) : null;
}

export function isAuthenticated() {
  return !!getToken();
}

export function requireAuth() {
  if (!isAuthenticated()) {
    window.location.href = '/login';
    return false;
  }
  return true;
}

export async function login(email, password) {
  const res = await apiPost('/auth/login', { email, password });
  if (!res.ok) throw await res.json();
  const data = await res.json();
  localStorage.setItem('studymate-token', data.access_token);
  localStorage.setItem('studymate-user', JSON.stringify(data.user));
  return data;
}

export async function register(name, email, password) {
  const res = await apiPost('/auth/register', { name, email, password });
  if (!res.ok) throw await res.json();
  const data = await res.json();
  localStorage.setItem('studymate-token', data.access_token);
  localStorage.setItem('studymate-user', JSON.stringify(data.user));
  return data;
}

export function logout() {
  localStorage.removeItem('studymate-token');
  localStorage.removeItem('studymate-user');
  window.location.href = '/login';
}

export async function forgotPassword(email) {
  const res = await apiPost('/auth/forgot-password', { email });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function verifyOtp(email, otp) {
  const res = await apiPost('/auth/verify-otp', { email, otp });
  if (!res.ok) throw await res.json();
  return res.json();
}

export async function resetPassword(resetToken, newPassword) {
  const res = await apiPost('/auth/reset-password', { resetToken, newPassword });
  if (!res.ok) throw await res.json();
  return res.json();
}

export function redirectIfAuthenticated() {
  if (isAuthenticated()) {
    window.location.href = '/feature/notes';
  }
}
