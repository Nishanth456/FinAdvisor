import { createContext, useContext, useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/axios';

// Create and export the context
export const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token'));
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    const verifyToken = async () => {
      const token = localStorage.getItem('token');
      if (!token) {
        setLoading(false);
        return;
      }

      // Set the token in the axios defaults
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      setToken(token);

      try {
        const response = await api.get('/users/me');
        setUser(response.data);
        
        // On initial load, redirect based on profile status
        if (response.data?.has_profile) {
          if (window.location.pathname === '/profile') {
            navigate('/dashboard');
          }
        } else if (window.location.pathname !== '/profile') {
          navigate('/profile');
        }
      } catch (error) {
        console.error('Token verification failed:', error);
        // Only clear token if it's an auth error
        if (error.response?.status === 401) {
          localStorage.removeItem('token');
          delete api.defaults.headers.common['Authorization'];
          setToken(null);
          setUser(null);
          navigate('/login');
        }
      } finally {
        setLoading(false);
      }
    };

    verifyToken();
  }, [token, navigate]);

  const clearError = () => {
    setError(null);
  };

  const login = async (email, password) => {
    setLoading(true);
    setError(null);
    try {
      // First check if user exists
      const checkUser = await api.get(`/users/check-email?email=${encodeURIComponent(email)}`);
      
      if (!checkUser.data.exists) {
        const errorMsg = 'No account found with this email. Please sign up.';
        setError(errorMsg);
        return { success: false, error: errorMsg, shouldSignup: true };
      }

      // If user exists, try to log in
      const response = await api.post('/token', 
        `username=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      const { access_token } = response.data;
      if (!access_token) {
        throw new Error('No access token received');
      }

      // Store the token
      localStorage.setItem('token', access_token);
      
      // Set the default authorization header
      api.defaults.headers.common['Authorization'] = `Bearer ${access_token}`;
      setToken(access_token);
      
      // Get user data
      const userResponse = await api.get('/users/me');
      setUser(userResponse.data);
      
      // Navigate based on profile status
      if (userResponse.data.has_profile) {
        navigate('/dashboard');
      } else {
        navigate('/profile');
      }
      
      return { 
        success: true,
        hasProfile: userResponse.data.has_profile 
      };
      
    } catch (err) {
      console.error('Login error:', err);
      let errorMsg = 'Login failed. Please check your credentials.';
      
      if (err.response) {
        // The request was made and the server responded with a status code
        console.error('Response data:', err.response.data);
        console.error('Response status:', err.response.status);
        
        if (err.response.status === 401) {
          errorMsg = 'Invalid email or password. Please try again.';
        } else if (err.response.data?.detail) {
          errorMsg = err.response.data.detail;
        }
      } else if (err.request) {
        // The request was made but no response was received
        console.error('No response received:', err.request);
        errorMsg = 'No response from server. Please check your connection.';
      } else {
        // Something happened in setting up the request
        console.error('Error setting up request:', err.message);
        errorMsg = err.message || 'Error setting up the request';
      }
      
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  // In AuthContext.jsx
  const signup = async (userData) => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.post('/signup', {
        name: userData.name,
        email: userData.email,
        password: userData.password
      });
      
      const { access_token } = response.data;
      if (access_token) {
        localStorage.setItem('token', access_token);
        setToken(access_token);
        
        // Get user data
        const userResponse = await api.get('/users/me');
        setUser(userResponse.data);
        
        // Redirect to profile page after successful signup
        navigate('/profile');
        return { success: true };
      }
      
      throw new Error('No access token received');
    } catch (error) {
      console.error('Signup error:', error);
      const errorMsg = error.response?.data?.detail || 'Signup failed. Please try again.';
      setError(errorMsg);
      return { success: false, error: errorMsg };
    } finally {
      setLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    navigate('/login');
  };

  const updateProfile = async (profileData) => {
    setLoading(true);
    setError(null);
    try {
      // Ensure risk_appetite is properly capitalized and has a default value
      const riskAppetite = profileData.risk_appetite?.trim() || 'Medium';
      const formattedRiskAppetite = riskAppetite.charAt(0).toUpperCase() + riskAppetite.slice(1).toLowerCase();
      
      const formattedData = {
        ...profileData,
        risk_appetite: formattedRiskAppetite
      };
      
      console.log('Sending profile data to server:', JSON.stringify(formattedData, null, 2));
      const response = await api.post('/users/me/profile', formattedData);
      
      // Update the user data with the new profile information
      setUser(prev => ({
        ...prev,
        has_profile: true,
        profile: {
          ...prev?.profile,
          ...formattedData
        }
      }));
      
      return { 
        ...response.data, 
        success: true,
        profile_updated: true
      };
    } catch (error) {
      console.error('Update profile error:', error);
      
      // Extract error details from the response
      const errorData = error.response?.data || {};
      const errorMsg = errorData.detail || errorData.message || 'Failed to update profile';
      
      console.error('Error details:', errorData);
      setError(errorMsg);
      
      // Return the full error object for better debugging
      return { 
        success: false, 
        error: errorMsg,
        status: error.response?.status,
        data: errorData
      };
    } finally {
      setLoading(false);
    }
  };

  const value = {
    user,
    token,
    loading,
    error,
    login,
    signup,
    logout,
    updateProfile,
    clearError,
  };

  return (
    <AuthContext.Provider value={value}>
      {!loading && children}
    </AuthContext.Provider>
  );
};

// Custom hook to use the auth context
export const useAuth = () => {
  return useContext(AuthContext);
};