import React, { createContext, useContext, useState, useEffect, useCallback, ReactNode } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import { authApi, setToken, getToken, removeToken, AUTH_EXPIRED_EVENT } from '../services/api';
import type { User, AuthContextType } from '../types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setTokenState] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);
    const navigate = useNavigate();

    // Listen for 401 session-expired events (from axios interceptor)
    const handleSessionExpired = useCallback(() => {
        setTokenState(null);
        setUser(null);
        toast.error('Session expired. Please login again.');
        navigate('/login', { replace: true });
    }, [navigate]);

    useEffect(() => {
        window.addEventListener(AUTH_EXPIRED_EVENT, handleSessionExpired);
        return () => window.removeEventListener(AUTH_EXPIRED_EVENT, handleSessionExpired);
    }, [handleSessionExpired]);

    // Initialize auth state from localStorage
    useEffect(() => {
        const initAuth = async () => {
            const savedToken = getToken();
            if (savedToken) {
                try {
                    // Verify token and get user info
                    const isValid = await authApi.verifyToken(savedToken);
                    if (isValid) {
                        const userData = await authApi.getCurrentUser(savedToken);
                        setUser(userData);
                        setTokenState(savedToken);
                    } else {
                        // Token invalid, clear it
                        removeToken();
                    }
                } catch (error) {
                    console.error('Failed to restore auth session:', error);
                    removeToken();
                }
            }
            setLoading(false);
        };

        initAuth();
    }, []);

    const signin = async (email: string, password: string) => {
        try {
            const response = await authApi.signin({ email, password });
            setToken(response.access_token);
            setTokenState(response.access_token);
            setUser(response.user);
        } catch (error: any) {
            // Don't log full error object — it contains request config with credentials
            console.error('Signin failed:', error.response?.data?.detail || error.message);
            throw new Error(error.response?.data?.detail || 'Signin failed');
        }
    };

    const signup = async (username: string, email: string, password: string) => {
        try {
            const response = await authApi.signup({ username, email, password });
            // Don't set token/user immediately - wait for email verification
            // Return verification message
            return response.message || 'Account created successfully! Please verify your email.';
        } catch (error: any) {
            // Don't log full error object — it contains request config with credentials
            console.error('Signup failed:', error.response?.data?.detail || error.message);
            throw new Error(error.response?.data?.detail || 'Signup failed');
        }
    };

    const logout = () => {
        removeToken();
        setTokenState(null);
        setUser(null);
    };

    const updateUser = (updated: User) => {
        setUser(updated);
    };

    const value: AuthContextType = {
        user,
        token,
        signin,
        signup,
        logout,
        updateUser,
        isAuthenticated: !!user && !!token,
        isAdmin: user?.role === 'admin',
        loading,
    };

    return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = (): AuthContextType => {
    const context = useContext(AuthContext);
    if (context === undefined) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};
