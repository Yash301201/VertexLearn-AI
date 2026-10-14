const API_ROOT = import.meta.env.VITE_API_URL ?? ''
const TOKEN_KEY = 'vertexlearn_token'
const USER_KEY = 'vertexlearn_user'
const REMEMBERED_EMAIL_KEY = 'vertexlearn_remembered_email'

export function getSession() {
  try {
    return {
      token: localStorage.getItem(TOKEN_KEY),
      user: JSON.parse(localStorage.getItem(USER_KEY) ?? 'null'),
    }
  } catch {
    return { token: null, user: null }
  }
}

export function saveSession(token, user) {
  localStorage.setItem(TOKEN_KEY, token)
  localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearSession() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getRememberedEmail() {
  try {
    return localStorage.getItem(REMEMBERED_EMAIL_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setRememberedEmail(email, remember) {
  try {
    if (remember && email) {
      localStorage.setItem(REMEMBERED_EMAIL_KEY, email)
    } else {
      localStorage.removeItem(REMEMBERED_EMAIL_KEY)
    }
  } catch {
    // Email remembering is optional when browser storage is unavailable.
  }
}

export async function api(path, options = {}) {
  const { token } = getSession()
  let response
  try {
    response = await fetch(`${API_ROOT}${path}`, {
      ...options,
      headers: {
        ...(options.body ? { 'Content-Type': 'application/json' } : {}),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...options.headers,
      },
    })
  } catch {
    throw new Error('Cannot reach VertexLearn. Check that the API server is running and the frontend proxy is configured.')
  }

  const data = response.status === 204 ? null : await response.json().catch(() => null)
  if (!response.ok) {
    const detail = data?.detail
    if (response.status === 401 && detail === 'Invalid or expired token') {
      clearSession()
      window.dispatchEvent(new Event('vertexlearn:session-expired'))
    }
    throw new Error(typeof detail === 'string' ? detail : 'Something went wrong. Please try again.')
  }
  return data
}