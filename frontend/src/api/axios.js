import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
  headers: {
    'Content-Type': 'application/json',
    'Accept': 'application/json'
  },
  withCredentials: true
});

// Add a request interceptor
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add a response interceptor
api.interceptors.response.use(
  (response) => {
    return response;
  },
  async (error) => {
    const originalRequest = error.config;
    
    // Don't retry if it's already a retry or a login request
    if (originalRequest._retry || originalRequest.url.includes('/token')) {
      return Promise.reject(error);
    }
    
    // If the error status is 401, try to refresh the token
    if (error.response?.status === 401) {
      originalRequest._retry = true;
      
      try {
        // Try to refresh the token
        const response = await axios.post(
          'http://localhost:8000/token/refresh',
          {},
          {
            withCredentials: true,
            headers: {
              'Content-Type': 'application/json',
            }
          }
        );
        
        const { access_token } = response.data;
        
        if (access_token) {
          // Store the new token
          localStorage.setItem('token', access_token);
          
          // Update the authorization header for the original request
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          
          // Update the default authorization header
          api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
          
          // Retry the original request with the new token
          return api(originalRequest);
        }
      } catch (refreshError) {
        console.error('Error refreshing token:', refreshError);
        // If refresh token is invalid or expired, log the user out
        if (refreshError.response?.status === 401) {
          localStorage.removeItem('token');
          delete api.defaults.headers.common['Authorization'];
          window.location.href = '/login';
        }
        return Promise.reject(refreshError);
      }
    }
    
    // For other errors, just reject with the original error
    return Promise.reject(error);
  }
);

export default api;