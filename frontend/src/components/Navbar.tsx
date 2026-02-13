import { Link, useLocation } from 'react-router-dom';
import { useState } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { LogOut } from 'lucide-react';

const Navbar = () => {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, isAdmin, logout } = useAuth();

  const navItems = [
    { path: '/', label: 'Analyze', icon: '🔍', protected: false },
    { path: '/articles', label: 'Articles', icon: '📰', protected: false },
    { path: '/dashboard', label: 'Dashboard', icon: '📊', protected: true, adminOnly: false },
    { path: '/scrape', label: 'Scrape', icon: '🌐', protected: true, adminOnly: true },
  ];

  // Filter nav items based on authentication
  const visibleNavItems = navItems.filter(item => {
    if (!item.protected) return true;
    if (!isAuthenticated) return false;
    if (item.adminOnly && !isAdmin) return false;
    return true;
  });

  const isActive = (path: string) => location.pathname === path;

  return (
    <nav className="bg-gray-900/95 backdrop-blur-sm border-b border-gray-800 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <span className="text-2xl">✨</span>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-xl font-bold bg-gradient-to-r from-primary-400 to-emerald-400 bg-clip-text text-transparent">
                BiasFree News
              </h1>
              <p className="text-xs text-gray-400">নিরপেক্ষ সংবাদ</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-1.5">
            {visibleNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  px-4 py-2 rounded-lg font-medium transition-all duration-200
                  flex items-center space-x-2 border
                  ${
                    isActive(item.path)
                      ? 'bg-primary-500/15 text-primary-400 border-primary-500/40 shadow-sm shadow-primary-500/10'
                      : 'text-gray-400 border-gray-800/60 bg-gray-900/30 hover:bg-gray-800/60 hover:text-white hover:border-gray-600 hover:shadow-md hover:shadow-black/20'
                  }
                `}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}

            {/* Auth Section */}
            {isAuthenticated ? (
              <div className="flex items-center ml-2 space-x-1.5">
                {/* Profile - Direct link */}
                <Link
                  to="/profile"
                  className={`
                    flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 border
                    ${
                      isActive('/profile')
                        ? 'bg-primary-500/15 text-primary-400 border-primary-500/40 shadow-sm shadow-primary-500/10'
                        : 'text-gray-400 border-gray-800/60 bg-gray-900/30 hover:bg-gray-800/60 hover:text-white hover:border-gray-600 hover:shadow-md hover:shadow-black/20'
                    }
                  `}
                >
                  <span className="text-lg">👤</span>
                  <span>{user?.username}</span>
                  {isAdmin && (
                    <span className="px-1.5 py-0.5 text-[10px] bg-yellow-500/20 text-yellow-400 rounded font-semibold">
                      Admin
                    </span>
                  )}
                </Link>

                {/* Logout button */}
                <button
                  onClick={logout}
                  className="p-2 rounded-lg border border-gray-800/60 bg-gray-900/30 text-gray-500 hover:text-red-400 hover:border-red-500/40 hover:bg-red-500/10 transition-all duration-200"
                  title="Logout"
                >
                  <LogOut className="w-4.5 h-4.5" />
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                className="ml-2 px-4 py-2 rounded-lg font-medium bg-primary-500 text-white hover:bg-primary-600 transition-all duration-200 border border-primary-500 hover:shadow-md hover:shadow-primary-500/20"
              >
                Login
              </Link>
            )}
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 rounded-lg text-gray-400 hover:text-white hover:bg-gray-800 transition-colors border border-gray-800/60"
          >
            <svg
              className="w-6 h-6"
              fill="none"
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth="2"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              {isMobileMenuOpen ? (
                <path d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Navigation */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-gray-800 bg-gray-900">
          <div className="px-2 pt-2 pb-3 space-y-1">
            {visibleNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`
                  px-3 py-2.5 rounded-lg font-medium transition-all duration-200 border
                  flex items-center space-x-2
                  ${
                    isActive(item.path)
                      ? 'bg-primary-500/15 text-primary-400 border-primary-500/40'
                      : 'text-gray-400 border-gray-800/60 hover:bg-gray-800/60 hover:text-white hover:border-gray-600'
                  }
                `}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </Link>
            ))}

            {/* Mobile Auth Section */}
            {isAuthenticated ? (
              <div className="border-t border-gray-800 pt-2 mt-2 space-y-1">
                <Link
                  to="/profile"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`
                    flex items-center space-x-2 px-3 py-2.5 rounded-lg font-medium transition-all duration-200 border
                    ${
                      isActive('/profile')
                        ? 'bg-primary-500/15 text-primary-400 border-primary-500/40'
                        : 'text-gray-400 border-gray-800/60 hover:bg-gray-800/60 hover:text-white hover:border-gray-600'
                    }
                  `}
                >
                  <span>👤</span>
                  <span>{user?.username}</span>
                  {isAdmin && (
                    <span className="px-1.5 py-0.5 text-[10px] bg-yellow-500/20 text-yellow-400 rounded font-semibold">
                      Admin
                    </span>
                  )}
                </Link>
                <button
                  onClick={() => {
                    logout();
                    setIsMobileMenuOpen(false);
                  }}
                  className="w-full text-left px-3 py-2.5 rounded-lg text-red-400 border border-gray-800/60 hover:bg-red-500/10 hover:border-red-500/40 transition-all duration-200 flex items-center space-x-2"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Logout</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block px-3 py-2.5 rounded-lg font-medium bg-primary-500 text-white hover:bg-primary-600 transition-all duration-200 text-center border border-primary-500"
              >
                Login
              </Link>
            )}
          </div>
        </div>
      )}
    </nav>
  );
};

export default Navbar;
