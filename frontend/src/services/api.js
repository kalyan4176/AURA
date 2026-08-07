const BASE_URL = '/api';

/**
 * Enterprise client fetch wrapper.
 * Automatically injects authorization headers, parses JSON, and logs API exceptions.
 */
async function request(endpoint, options = {}) {
  const url = `${BASE_URL}${endpoint}`;
  
  // Set default headers
  const headers = {
    ...options.headers,
  };

  // If payload is not FormData, default to JSON content type
  if (!(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  }

  // Retrieve token from storage
  const token = localStorage.getItem('aura_token');
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }

  const config = {
    ...options,
    headers,
  };

  try {
    const response = await fetch(url, config);
    
    // Auto-logout on token expiration
    if (response.status === 401 && !endpoint.includes('/auth/login')) {
      localStorage.removeItem('aura_token');
      window.dispatchEvent(new Event('aura_auth_state_change'));
    }

    if (!response.ok) {
      const errorText = await response.text();
      let errorJson;
      try {
        errorJson = JSON.parse(errorText);
      } catch (e) {
        errorJson = { detail: errorText || 'An unexpected error occurred.' };
      }
      throw new Error(errorJson.detail || 'Request failed.');
    }

    // Return json if content exists
    const text = await response.text();
    return text ? JSON.parse(text) : {};
  } catch (error) {
    console.error(`AURA API Error [${url}]:`, error);
    throw error;
  }
}

export const api = {
  get: (endpoint, options) => request(endpoint, { ...options, method: 'GET' }),
  post: (endpoint, body, options) => request(endpoint, { ...options, method: 'POST', body: body instanceof FormData ? body : JSON.stringify(body) }),
  put: (endpoint, body, options) => request(endpoint, { ...options, method: 'PUT', body: body instanceof FormData ? body : JSON.stringify(body) }),
  delete: (endpoint, options) => request(endpoint, { ...options, method: 'DELETE' }),
};
