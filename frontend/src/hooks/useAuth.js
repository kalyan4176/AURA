import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../services/api';
import { useEffect, useState } from 'react';

export function useAuth() {
  const queryClient = useQueryClient();
  const [authState, setAuthState] = useState(!!localStorage.getItem('aura_token'));

  useEffect(() => {
    const handleStateChange = () => {
      setAuthState(!!localStorage.getItem('aura_token'));
      queryClient.invalidateQueries({ queryKey: ['auth_user'] });
    };

    window.addEventListener('aura_auth_state_change', handleStateChange);
    return () => window.removeEventListener('aura_auth_state_change', handleStateChange);
  }, [queryClient]);

  // Query user profile
  const { data: user, isLoading, isError } = useQuery({
    queryKey: ['auth_user'],
    queryFn: async () => {
      if (!localStorage.getItem('aura_token')) return null;
      try {
        return await api.get('/auth/me');
      } catch (e) {
        localStorage.removeItem('aura_token');
        setAuthState(false);
        return null;
      }
    },
    enabled: authState,
    retry: false,
  });

  // Login mutation
  const loginMutation = useMutation({
    mutationFn: async (credentials) => {
      const response = await api.post('/auth/login', credentials);
      localStorage.setItem('aura_token', response.access_token);
      window.dispatchEvent(new Event('aura_auth_state_change'));
      return response;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['auth_user'] });
    },
  });

  // Register mutation
  const registerMutation = useMutation({
    mutationFn: async (userData) => {
      return await api.post('/auth/register', userData);
    },
  });

  const logout = () => {
    localStorage.removeItem('aura_token');
    window.dispatchEvent(new Event('aura_auth_state_change'));
    queryClient.setQueryData(['auth_user'], null);
  };

  return {
    user,
    isAuthenticated: authState && !!user,
    isLoading: authState && isLoading,
    isError,
    login: loginMutation.mutateAsync,
    isLoggingIn: loginMutation.isPending,
    register: registerMutation.mutateAsync,
    isRegistering: registerMutation.isPending,
    logout,
  };
}
