import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { authApi, setToken, getToken, removeToken } from '../services/api';
import type { User, AuthContextType } from '../types';

const AuthContext = createContext<AuthContextType | undefined>(undefined);

interface AuthProviderProps {
    children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setTokenState] = useState<string | null>(null);
    const [loading, setLoading] = useState(true);

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
            console.error('Signin failed:', error);
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
            console.error('Signup failed:', error);
            throw new Error(error.response?.data?.detail || 'Signup failed');
        }
    };

    const logout = () => {
        removeToken();
        setTokenState(null);
        setUser(null);
    };

    const value: AuthContextType = {
        user,
        token,
        signin,
        signup,
        logout,
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
