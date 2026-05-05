import React, { useState, useEffect, useRef } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { authApi } from '../services/api';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

const VerifyEmailPage: React.FC = () => {
    const { token } = useParams<{ token: string }>();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');
    const calledRef = useRef(false);

    useEffect(() => {
        if (calledRef.current) return;   // prevent React StrictMode double-invoke
        calledRef.current = true;

        const verifyEmail = async () => {
            if (!token) {
                setError('Invalid verification link');
                setLoading(false);
                return;
            }

            try {
                await authApi.verifyEmail(token);
                setSuccess(true);
                // Redirect to login after 3 seconds
                setTimeout(() => {
                    navigate('/login');
                }, 3000);
            } catch (err: any) {
                setError(err.response?.data?.detail || 'Email verification failed');
            } finally {
                setLoading(false);
            }
        };

        verifyEmail();
    }, [token, navigate]);

    return (
        <div className="min-h-[calc(100vh-64px)] bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center px-4 py-12">
            <div className="max-w-md w-full">
                <div className="bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl p-8 text-center">
                    {loading && (
                        <React.Fragment>
                            <div className="inline-flex items-center justify-center w-20 h-20 bg-blue-500/20 rounded-full mb-6">
                                <Loader2 className="h-10 w-10 text-blue-400 animate-spin" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Verifying your email...
                            </h2>
                            <p className="text-gray-400">
                                Please wait while we verify your email address.
                            </p>
                        </React.Fragment>
                    )}

                    {!loading && success && (
                        <React.Fragment>
                            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-500/20 rounded-full mb-6">
                                <CheckCircle className="h-10 w-10 text-green-400" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Email Verified! ✅
                            </h2>
                            <p className="text-gray-400 mb-6">
                                Your email has been successfully verified. You can now sign in to your account.
                            </p>
                            <p className="text-sm text-gray-500 mb-6">
                                Redirecting to login page in 3 seconds...
                            </p>
                            <Link
                                to="/login"
                                className="inline-block px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all duration-300 shadow-lg"
                            >
                                Go to Login
                            </Link>
                        </React.Fragment>
                    )}

                    {!loading && error && (
                        <React.Fragment>
                            <div className="inline-flex items-center justify-center w-20 h-20 bg-red-500/20 rounded-full mb-6">
                                <XCircle className="h-10 w-10 text-red-400" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Verification Failed
                            </h2>
                            <p className="text-gray-400 mb-6">
                                {error}
                            </p>
                            <p className="text-sm text-gray-500 mb-6">
                                The verification link may have expired (1 minute limit). Please go to the login page and request a new verification email.
                            </p>
                            <div className="space-y-3">
                                <Link
                                    to="/login"
                                    className="block w-full px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 text-white font-semibold rounded-xl hover:from-blue-700 hover:to-purple-700 transition-all duration-300 shadow-lg"
                                >
                                    Go to Login & Resend Verification
                                </Link>
                                <Link
                                    to="/signup"
                                    className="block w-full px-6 py-3 bg-white/5 border border-white/10 text-white font-semibold rounded-xl hover:bg-white/10 transition-all duration-300"
                                >
                                    Create New Account
                                </Link>
                            </div>
                        </React.Fragment>
                    )}
                </div>
            </div>
        </div>
    );
};

export default VerifyEmailPage;
