import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { authApi } from '../services/api';
import { Mail, Lock, User, Eye, EyeOff, Check, X } from 'lucide-react';
import usePageTitle from '../hooks/usePageTitle';

interface PasswordStrength {
    minLength: boolean;
    hasUpperCase: boolean;
    hasLowerCase: boolean;
    hasNumber: boolean;
    hasSpecialChar: boolean;
}

const SignupPage: React.FC = () => {
  usePageTitle('Sign Up');
    const [username, setUsername] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [showConfirmPassword, setShowConfirmPassword] = useState(false);
    const [error, setError] = useState('');
    const [success, setSuccess] = useState('');
    const [loading, setLoading] = useState(false);
    const [resendLoading, setResendLoading] = useState(false);
    const [resendCooldown, setResendCooldown] = useState(0);
    const [passwordStrength, setPasswordStrength] = useState<PasswordStrength>({
        minLength: false,
        hasUpperCase: false,
        hasLowerCase: false,
        hasNumber: false,
        hasSpecialChar: false,
    });
    
    const { signup } = useAuth();

    // Resend cooldown timer
    useEffect(() => {
        if (resendCooldown > 0) {
            const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
            return () => clearTimeout(timer);
        }
    }, [resendCooldown]);

    const handleResendVerification = async () => {
        if (!email || resendCooldown > 0) return;
        setResendLoading(true);
        try {
            await authApi.resendVerification(email);
            setSuccess('New verification email sent! Please check your inbox and click the link within 1 minute.');
            setResendCooldown(60); // 60 second cooldown
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to resend verification email');
        } finally {
            setResendLoading(false);
        }
    };

    // Check password strength
    useEffect(() => {
        setPasswordStrength({
            minLength: password.length >= 8,
            hasUpperCase: /[A-Z]/.test(password),
            hasLowerCase: /[a-z]/.test(password),
            hasNumber: /[0-9]/.test(password),
            hasSpecialChar: /[!@#$%^&*(),.?":{}|<>]/.test(password),
        });
    }, [password]);

    const isPasswordValid = Object.values(passwordStrength).every(Boolean);

    const getPasswordStrengthColor = () => {
        const count = Object.values(passwordStrength).filter(Boolean).length;
        if (count <= 2) return 'text-red-400';
        if (count <= 3) return 'text-yellow-400';
        if (count <= 4) return 'text-blue-400';
        return 'text-green-400';
    };

    const getPasswordStrengthText = () => {
        const count = Object.values(passwordStrength).filter(Boolean).length;
        if (count <= 2) return 'Weak';
        if (count <= 3) return 'Fair';
        if (count <= 4) return 'Good';
        return 'Strong';
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setError('');
        setSuccess('');

        // Validation
        if (password !== confirmPassword) {
            setError('Passwords do not match');
            return;
        }

        if (!isPasswordValid) {
            setError('Password does not meet all requirements');
            return;
        }

        if (username.length < 3) {
            setError('Username must be at least 3 characters long');
            return;
        }

        setLoading(true);

        try {
            const message = await signup(username, email, password);
            setSuccess(message);
        } catch (err: any) {
            setError(err.message || 'Signup failed. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-[calc(100vh-64px)] bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center px-4 py-8">
            <div className="max-w-md w-full">
                {/* Card */}
                <div className="bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl p-8">
                    {/* Header inside card */}
                    <div className="text-center mb-8">
                        <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-purple-500 to-pink-600 rounded-2xl mb-4">
                            <span className="text-3xl">🚀</span>
                        </div>
                        <h2 className="text-3xl font-bold text-white mb-2">
                            Create Account
                        </h2>
                        <p className="text-gray-400">
                            Join BiasFree News today
                        </p>
                    </div>

                    <form onSubmit={handleSubmit} className="space-y-4">
                        {/* Error Message */}
                        {error && (
                            <div className="bg-red-500/20 border border-red-500/50 text-red-300 px-4 py-3 rounded-xl text-sm">
                                {error}
                            </div>
                        )}

                        {/* Success Message */}
                        {success && (
                            <div className="bg-green-500/20 border border-green-500/50 text-green-300 px-4 py-3 rounded-xl text-sm">
                                <p className="font-semibold mb-2">✅ Account created successfully!</p>
                                <p className="text-xs leading-relaxed">
                                    A verification email has been sent to <span className="font-semibold">{email}</span>. 
                                    Please check your inbox and click the verification link to activate your account.
                                </p>
                                <p className="text-xs mt-2 text-amber-400">
                                    ⏱️ The verification link expires in <strong>1 minute</strong>. If it expires, you can resend it.
                                </p>
                                <div className="mt-3 flex items-center gap-3">
                                    <button
                                        type="button"
                                        onClick={handleResendVerification}
                                        disabled={resendLoading || resendCooldown > 0}
                                        className="text-xs bg-blue-500/20 border border-blue-500/40 text-blue-400 hover:bg-blue-500/30 px-3 py-1.5 rounded-lg transition disabled:opacity-50"
                                    >
                                        {resendLoading ? 'Sending...' : resendCooldown > 0 ? `Resend in ${resendCooldown}s` : 'Resend Verification Email'}
                                    </button>
                                    <Link to="/login" className="text-xs text-purple-400 hover:text-purple-300 underline">
                                        Go to Login
                                    </Link>
                                </div>
                                <p className="text-xs mt-3 text-green-400">
                                    💡 Tip: If you don't see the email, check your spam folder.
                                </p>
                            </div>
                        )}

                        {/* Username Field */}
                        <div>
                            <label htmlFor="username" className="block text-sm font-medium text-gray-300 mb-2">
                                Username
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <User className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    id="username"
                                    type="text"
                                    required
                                    value={username}
                                    onChange={(e) => setUsername(e.target.value)}
                                    className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                                    placeholder="Enter your username"
                                    minLength={3}
                                    maxLength={50}
                                />
                            </div>
                        </div>

                        {/* Email Field */}
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                                Email Address
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Mail className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    id="email"
                                    type="email"
                                    required
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    className="w-full pl-12 pr-4 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                                    placeholder="Enter your email"
                                />
                            </div>
                        </div>

                        {/* Password Field */}
                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                                Password
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    id="password"
                                    type={showPassword ? 'text' : 'password'}
                                    required
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="w-full pl-12 pr-12 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                                    placeholder="Enter your password"
                                    minLength={8}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-white transition"
                                >
                                    {showPassword ? (
                                        <EyeOff className="h-5 w-5" />
                                    ) : (
                                        <Eye className="h-5 w-5" />
                                    )}
                                </button>
                            </div>
                            
                            {/* Password Strength Indicator */}
                            {password && (
                                <div className="mt-3 space-y-2">
                                    <div className="flex items-center justify-between">
                                        <span className="text-xs text-gray-400">Password Strength:</span>
                                        <span className={`text-xs font-semibold ${getPasswordStrengthColor()}`}>
                                            {getPasswordStrengthText()}
                                        </span>
                                    </div>
                                    <div className="space-y-1">
                                        <PasswordRequirement met={passwordStrength.minLength} text="At least 8 characters" />
                                        <PasswordRequirement met={passwordStrength.hasUpperCase} text="One uppercase letter" />
                                        <PasswordRequirement met={passwordStrength.hasLowerCase} text="One lowercase letter" />
                                        <PasswordRequirement met={passwordStrength.hasNumber} text="One number" />
                                        <PasswordRequirement met={passwordStrength.hasSpecialChar} text="One special character" />
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Confirm Password Field */}
                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
                                Confirm Password
                            </label>
                            <div className="relative">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-gray-400" />
                                </div>
                                <input
                                    id="confirmPassword"
                                    type={showConfirmPassword ? 'text' : 'password'}
                                    required
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="w-full pl-12 pr-12 py-3 bg-white/5 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition"
                                    placeholder="Confirm your password"
                                    minLength={8}
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-gray-400 hover:text-white transition"
                                >
                                    {showConfirmPassword ? (
                                        <EyeOff className="h-5 w-5" />
                                    ) : (
                                        <Eye className="h-5 w-5" />
                                    )}
                                </button>
                            </div>
                        </div>

                        {/* Submit Button */}
                        <button
                            type="submit"
                            disabled={loading}
                            className="w-full bg-gradient-to-r from-purple-600 to-pink-600 text-white py-3 rounded-xl font-semibold hover:from-purple-700 hover:to-pink-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 focus:ring-offset-gray-900 transition-all transform hover:scale-[1.02] disabled:opacity-50 disabled:cursor-not-allowed disabled:transform-none mt-6"
                        >
                            {loading ? (
                                <span className="flex items-center justify-center">
                                    <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                    </svg>
                                    Creating account...
                                </span>
                            ) : (
                                'Create Account'
                            )}
                        </button>
                    </form>

                    {/* Divider */}
                    <div className="mt-6 mb-6 flex items-center">
                        <div className="flex-1 border-t border-white/10"></div>
                        <span className="px-4 text-sm text-gray-400">or</span>
                        <div className="flex-1 border-t border-white/10"></div>
                    </div>

                    {/* Login Link */}
                    <div className="text-center">
                        <p className="text-sm text-gray-400">
                            Already have an account?{' '}
                            <Link 
                                to="/login" 
                                className="text-purple-400 hover:text-purple-300 font-semibold transition"
                            >
                                Sign in
                            </Link>
                        </p>
                    </div>
                </div>

                {/* Back to Home */}
                <div className="text-center mt-6">
                    <Link 
                        to="/" 
                        className="text-sm text-gray-400 hover:text-white transition inline-flex items-center"
                    >
                        <svg className="w-4 h-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 19l-7-7m0 0l7-7m-7 7h18" />
                        </svg>
                        Back to Home
                    </Link>
                </div>
            </div>
        </div>
    );
};

// Password Requirement Component
const PasswordRequirement: React.FC<{ met: boolean; text: string }> = ({ met, text }) => (
    <div className="flex items-center space-x-2">
        {met ? (
            <Check className="h-4 w-4 text-green-400" />
        ) : (
            <X className="h-4 w-4 text-gray-500" />
        )}
        <span className={`text-xs ${met ? 'text-green-400' : 'text-gray-500'}`}>
            {text}
        </span>
    </div>
);

export default SignupPage;
