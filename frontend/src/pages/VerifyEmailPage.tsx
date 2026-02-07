import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import { authApi } from '../services/api';
import { CheckCircle, XCircle, Loader2 } from 'lucide-react';

const VerifyEmailPage: React.FC = () => {
    const { token } = useParams<{ token: string }>();
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [success, setSuccess] = useState(false);
    const [error, setError] = useState('');

    useEffect(() => {
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
        <div className="min-h-[calc(100vh-64px)] bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900 flex items-center justify-center px-4">
            <div className="max-w-md w-full">
                <div className="bg-white/10 backdrop-blur-xl rounded-3xl border border-white/20 shadow-2xl p-8 text-center">
                    {loading && (
                        <>
                            <div className="inline-flex items-center justify-center w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-600 rounded-full mb-6">
                                <Loader2 className="h-10 w-10 text-white animate-spin" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Verifying your email...
                            </h2>
                            <p className="text-gray-400">
                                Please wait while we verify your email address.
                            </p>
                        </>
                    )}

                    {!loading && success && (
                        <>
                            <div className="inline-flex items-center justify-center w-20 h-20 bg-green-500/20 rounded-full mb-6">
                                <CheckCircle className="h-10 w-10 text-green-400" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Email Verified!
                            </h2>
                            <p className="text-gray-400 mb-6">
                                Your email has been successfully verified. You can now sign in to your account.
                            </p>
                            <p className="text-sm text-gray-500 mb-6">
                                Redirecting to login page in 3 seconds...
                            </p>
                            <Link
                                to="/login"
                                className="inline-block px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 shadow-lg"
                            >
                                Go to Login
                            </Link>
                        </>
                    )}

                    {!loading && error && (
                        <>
                            <div className="inline-flex items-center justify-center w-20 h-20 bg-red-500/20 rounded-full mb-6">
                                <XCircle className="h-10 w-10 text-red-400" />
                            </div>
                            <h2 className="text-2xl font-bold text-white mb-2">
                                Verification Failed
                            </h2>
                            <p className="text-gray-400 mb-6">
                                {error}
                            </p>
                            <div className="space-y-3">
                                <Link
                                    to="/signup"
                                    className="block w-full px-6 py-3 bg-gradient-to-r from-purple-600 to-pink-600 text-white font-semibold rounded-xl hover:from-purple-700 hover:to-pink-700 transition-all duration-300 shadow-lg"
                                >
                                    Create New Account
                                </Link>
                                <Link
                                    to="/login"
                                    className="block w-full px-6 py-3 bg-white/5 border border-white/10 text-white font-semibold rounded-xl hover:bg-white/10 transition-all duration-300"
                                >
                                    Back to Login
                                </Link>
                            </div>
                        </>
                    )}
                </div>
            </div>
        </div>
    );
};

export default VerifyEmailPage;
