const TOKEN_KEY = 'watchfy_token';
const REFRESH_KEY = 'watchfy_refresh';
const USER_KEY = 'watchfy_user';

export interface User {
  id: number;
  email: string;
  username: string;
  is_active: boolean;
  is_admin: boolean;
  created_at: string;
}

let _refreshPromise: Promise<string | null> | null = null;

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  return localStorage.getItem(REFRESH_KEY);
}

export function getUser(): User | null {
  try {
    const raw = localStorage.getItem(USER_KEY);
    return raw ? JSON.parse(raw) : null;
  } catch {
    return null;
  }
}

export function isAuthenticated(): boolean {
  return !!getToken();
}

function setSession(access: string, refresh: string, user?: User) {
  localStorage.setItem(TOKEN_KEY, access);
  localStorage.setItem(REFRESH_KEY, refresh);
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user));
  dispatchAuthChange();
}

function clearSession() {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem('access_token');
  dispatchAuthChange();
}

function dispatchAuthChange() {
  window.dispatchEvent(new CustomEvent('watchfy:auth-change', {
    detail: { authenticated: isAuthenticated(), user: getUser() },
  }));
}

export async function login(username: string, password: string): Promise<User> {
  const res = await fetch('/api/auth/token', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Invalid email or password');
  }

  const data = await res.json();
  const access = data.access_token as string;
  const refresh = data.refresh_token as string;

  const user = await fetchUser(access);
  setSession(access, refresh, user);
  return user;
}

export async function register(username: string, email: string, password: string): Promise<User> {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, email, password }),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Could not create account');
  }

  const data = await res.json();
  const access = data.access_token as string;
  const refresh = data.refresh_token as string;
  const user = (data.user as User) || await fetchUser(access);

  setSession(access, refresh, user);
  return user;
}

export async function refreshAccessToken(): Promise<string | null> {
  if (_refreshPromise) return _refreshPromise;

  _refreshPromise = (async () => {
    try {
      const rt = getRefreshToken();
      if (!rt) return null;

      const res = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh_token: rt }),
      });

      if (!res.ok) {
        clearSession();
        return null;
      }

      const data = await res.json();
      const access = data.access_token as string;
      const newRefresh = data.refresh_token as string;
      localLogin(access, newRefresh);
      return access;
    } catch {
      clearSession();
      return null;
    } finally {
      _refreshPromise = null;
    }
  })();

  return _refreshPromise;
}

export function logout() {
  clearSession();
}

export async function fetchUser(token?: string): Promise<User> {
  const t = token || getToken();
  if (!t) throw new Error('Not authenticated');

  const res = await fetch('/api/auth/me', {
    headers: { Authorization: `Bearer ${t}` },
  });

  if (!res.ok) throw new Error('Failed to fetch user');
  return res.json();
}

export async function updateProfile(updates: { username?: string; email?: string }): Promise<User> {
  const res = await authFetch('/api/auth/me', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(updates),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || 'Failed to update profile');
  }

  const user = await res.json();
  localStorage.setItem(USER_KEY, JSON.stringify(user));
  dispatchAuthChange();
  return user;
}

export async function authFetch(path: string, options: RequestInit = {}): Promise<Response> {
  let token = getToken();

  const headers = new Headers(options.headers || {});
  if (token) headers.set('Authorization', `Bearer ${token}`);
  if (!headers.has('Content-Type') && options.body) {
    headers.set('Content-Type', 'application/json');
  }

  let res = await fetch(path, { ...options, headers });

  if (res.status === 401 && token) {
    const newToken = await refreshAccessToken();
    if (newToken) {
      headers.set('Authorization', `Bearer ${newToken}`);
      res = await fetch(path, { ...options, headers });
    }
  }

  return res;
}

export function localLogin(access: string, refresh?: string) {
  localStorage.setItem(TOKEN_KEY, access);
  if (refresh) localStorage.setItem(REFRESH_KEY, refresh);
  localStorage.removeItem('access_token');
}

export function onAuthChange(callback: (authenticated: boolean, user: User | null) => void): () => void {
  const handler = (e: Event) => {
    const { authenticated, user } = (e as CustomEvent).detail;
    callback(authenticated, user);
  };
  window.addEventListener('watchfy:auth-change', handler);
  callback(isAuthenticated(), getUser());
  return () => window.removeEventListener('watchfy:auth-change', handler);
}