import { apiPost, apiGet } from './api.js';
import { showToast } from './utils.js';

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
    window.location.href = '/';
  }
}

// Consume a JWT delivered via ?token= (Google OAuth callback lands here).
// Stores the token + a minimal user object, then redirects to the home page.
export function handleOAuthCallback() {
  const params = new URLSearchParams(window.location.search);
  const token = params.get('token');
  if (!token) return false;

  params.delete('token');
  const cleanUrl = window.location.pathname + (params.toString() ? `?${params.toString()}` : '');

  try {
    localStorage.setItem('studymate-token', token);
    const payload = JSON.parse(atob(token.split('.')[1]));
    localStorage.setItem(
      'studymate-user',
      JSON.stringify({
        id: payload.sub,
        name: payload.name || '',
        email: payload.email || '',
        image: payload.image || '',
      })
    );
    showToast('Signed in with Google', 'success');
    setTimeout(() => { window.location.replace('/'); }, 400);
    history.replaceState(null, '', cleanUrl);
    return true;
  } catch (e) {
    localStorage.removeItem('studymate-token');
    localStorage.removeItem('studymate-user');
    history.replaceState(null, '', cleanUrl);
    return false;
  }
}
