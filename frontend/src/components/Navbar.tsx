import { Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useTheme } from '../contexts/ThemeContext';
import { useLanguage } from '../contexts/LanguageContext';
import { LogOut, Sun, Moon, Users } from 'lucide-react';

const Navbar = () => {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const { user, isAuthenticated, isAdmin, logout } = useAuth();
  const { isDark, toggleTheme } = useTheme();
  const { language, setLanguage, translate } = useLanguage();

  // Auto-close mobile menu on route change
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [location.pathname]);

  const navItems = [
    { path: '/', label: { bn: 'বিশ্লেষণ', en: 'Analyze' }, icon: '🔍', protected: false },
    { path: '/articles', label: { bn: 'প্রবন্ধ', en: 'Articles' }, icon: '📰', protected: false },
    { path: '/clusters', label: { bn: 'ক্লাস্টার', en: 'Clusters' }, icon: '🔗', protected: false },
    { path: '/dashboard', label: { bn: 'ড্যাশবোর্ড', en: 'Dashboard' }, icon: '📊', protected: true, adminOnly: false },
    { path: '/scrape', label: { bn: 'স্ক্র্যাপ', en: 'Scrape' }, icon: '🌐', protected: true, adminOnly: true },
  ];

  // Filter nav items based on authentication
  const visibleNavItems = navItems.filter(item => {
    if (!item.protected) return true;
    if (!isAuthenticated) return false;
    if (item.adminOnly && !isAdmin) return false;
    return true;
  });

  const isExactActive = (path: string) => location.pathname === path;

  return (
    <nav className={`navbar-container backdrop-blur-sm border-b sticky top-0 z-50 ${isDark ? 'bg-gray-900/95 border-gray-800' : ''}`}>
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10">
        <div className="flex items-center justify-between h-20 py-2">
          {/* Logo */}
          <Link to="/" className="flex items-center space-x-3 group shrink-0">
            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-lg flex items-center justify-center group-hover:scale-110 transition-transform">
              <span className="text-2xl">✨</span>
            </div>
            <div className="hidden sm:block">
              <h1 className="text-lg font-bold bg-gradient-to-r from-primary-400 to-emerald-400 bg-clip-text text-transparent">
                BiasFree News
              </h1>
              <p className="navbar-subtitle text-xs">Unbiased news</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="hidden md:flex items-center space-x-2">
            {visibleNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`
                  px-4 py-2 rounded-lg font-medium transition-all duration-200
                  flex items-center space-x-2 border
                  ${
                    isExactActive(item.path)
                      ? (isDark
                        ? 'bg-primary-500/15 text-primary-400 border-primary-500/40 shadow-sm shadow-primary-500/10'
                        : 'nav-item-active')
                      : (isDark
                        ? 'text-gray-400 border-gray-800/60 bg-gray-900/30 hover:bg-gray-800/60 hover:text-white hover:border-gray-600 hover:shadow-md hover:shadow-black/20'
                        : 'nav-item-inactive')
                  }
                `}
              >
                <span>{item.icon}</span>
                <span>{translate(item.label.bn, item.label.en)}</span>
              </Link>
            ))}

            {/* Auth Section */}
            {isAuthenticated ? (
              <div className="flex items-center ml-2 space-x-2">
                {/* Admin Users link */}
                {isAdmin && (
                  <Link
                    to="/admin/users"
                    className={`
                      flex items-center gap-1.5 px-3 py-2 rounded-lg font-medium transition-all duration-200 border
                      ${isExactActive('/admin/users')
                        ? (isDark ? 'bg-yellow-500/15 text-yellow-400 border-yellow-500/40' : 'nav-item-admin-active')
                        : (isDark ? 'text-gray-400 border-gray-800/60 bg-gray-900/30 hover:bg-yellow-500/10 hover:text-yellow-400 hover:border-yellow-500/30' : 'nav-item-admin-inactive')
                      }
                    `}
                    title={translate('ব্যবহারকারী পরিচালনা করুন', 'Manage users')}
                  >
                    <Users className="w-4 h-4" />
                    <span className="text-sm">{translate('ব্যবহারকারী', 'Users')}</span>
                  </Link>
                )}

                {/* Profile - Direct link */}
                <Link
                  to="/profile"
                  className={`
                    flex items-center space-x-2 px-4 py-2 rounded-lg font-medium transition-all duration-200 border
                    ${
                      isExactActive('/profile')
                        ? (isDark
                          ? 'bg-primary-500/15 text-primary-400 border-primary-500/40 shadow-sm shadow-primary-500/10'
                          : 'nav-item-active')
                        : (isDark
                          ? 'text-gray-400 border-gray-800/60 bg-gray-900/30 hover:bg-gray-800/60 hover:text-white hover:border-gray-600 hover:shadow-md hover:shadow-black/20'
                          : 'nav-item-inactive')
                    }
                  `}
                >
                  <span className="text-lg">👤</span>
                  <span>{user?.username}</span>
                  {isAdmin && (
                    <span className="px-1.5 py-0.5 text-[10px] bg-yellow-500/20 text-yellow-400 rounded font-semibold">
                      {translate('অ্যাডমিন', 'Admin')}
                    </span>
                  )}
                </Link>

                {/* Theme toggle */}
                <button
                  onClick={toggleTheme}
                  className={`p-2 rounded-lg border transition-all duration-200 ${isDark ? 'border-gray-800/60 bg-gray-900/30 text-gray-400 hover:text-amber-400 hover:border-amber-500/40 hover:bg-amber-500/10' : 'theme-toggle-light'}`}
                  title={isDark ? translate('দিনের থিমে যান', 'Switch to day view') : translate('রাতের থিমে যান', 'Switch to night view')}
                >
                  {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                </button>

                <div className="flex items-center rounded-lg border border-gray-800/60 overflow-hidden">
                  <button
                    onClick={() => setLanguage('bn')}
                    className={`px-2.5 py-1.5 text-xs font-semibold transition-colors ${language === 'bn' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/70'}`}
                    title={translate('বাংলা', 'Bangla')}
                  >
                    BN
                  </button>
                  <button
                    onClick={() => setLanguage('en')}
                    className={`px-2.5 py-1.5 text-xs font-semibold transition-colors border-l border-gray-800/60 ${language === 'en' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/70'}`}
                    title={translate('ইংরেজি', 'English')}
                  >
                    EN
                  </button>
                </div>

                {/* Logout button */}
                <button
                  onClick={logout}
                  className={`p-2 rounded-lg border transition-all duration-200 ${isDark ? 'border-gray-800/60 bg-gray-900/30 text-gray-500 hover:text-red-400 hover:border-red-500/40 hover:bg-red-500/10' : 'logout-btn-light'}`}
                  title={translate('লগ আউট', 'Logout')}
                >
                  <LogOut className="w-4.5 h-4.5" />
                </button>
              </div>
            ) : (
              <div className="flex items-center ml-2 gap-2">
                {/* Theme toggle (guest) */}
                <button
                  onClick={toggleTheme}
                  className={`p-2 rounded-lg border transition-all duration-200 ${isDark ? 'border-gray-800/60 bg-gray-900/30 text-gray-400 hover:text-amber-400 hover:border-amber-500/40 hover:bg-amber-500/10' : 'theme-toggle-light'}`}
                  title={isDark ? translate('দিনের থিমে যান', 'Switch to day view') : translate('রাতের থিমে যান', 'Switch to night view')}
                >
                  {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
                </button>
                <div className="flex items-center rounded-lg border border-gray-800/60 overflow-hidden">
                  <button
                    onClick={() => setLanguage('bn')}
                    className={`px-2.5 py-1.5 text-xs font-semibold transition-colors ${language === 'bn' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/70'}`}
                  >
                    BN
                  </button>
                  <button
                    onClick={() => setLanguage('en')}
                    className={`px-2.5 py-1.5 text-xs font-semibold transition-colors border-l border-gray-800/60 ${language === 'en' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/70'}`}
                  >
                    EN
                  </button>
                </div>
                <Link
                  to="/login"
                  className="px-4 py-2 rounded-lg font-medium bg-primary-500 text-white hover:bg-primary-600 transition-all duration-200 border border-primary-500 hover:shadow-md hover:shadow-primary-500/20"
                >
                  {translate('লগ ইন', 'Login')}
                </Link>
              </div>
            )}
          </div>

          {/* Mobile menu button */}
          <div className="md:hidden flex items-center gap-2">
            <div className="flex items-center rounded-lg border border-gray-800/60 overflow-hidden">
              <button
                onClick={() => setLanguage('bn')}
                className={`px-2.5 py-1.5 text-xs font-semibold transition-colors ${language === 'bn' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/70'}`}
              >
                BN
              </button>
              <button
                onClick={() => setLanguage('en')}
                className={`px-2.5 py-1.5 text-xs font-semibold transition-colors border-l border-gray-800/60 ${language === 'en' ? 'bg-primary-500 text-white' : 'text-gray-400 hover:text-white hover:bg-gray-800/70'}`}
              >
                EN
              </button>
            </div>
            {/* Mobile theme toggle */}
            <button
              onClick={toggleTheme}
              className={`p-2 rounded-lg border transition-colors ${isDark ? 'border-gray-800/60 text-gray-400 hover:text-amber-400' : 'theme-toggle-light'}`}
            >
              {isDark ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </button>
            <button
              onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
              className={`p-2 rounded-lg transition-colors border ${isDark ? 'text-gray-400 hover:text-white hover:bg-gray-800 border-gray-800/60' : 'mobile-menu-btn-light'}`}
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
      </div>

      {/* Mobile Navigation */}
      <div className={`md:hidden overflow-hidden transition-all duration-300 ease-in-out ${isMobileMenuOpen ? 'max-h-[500px] opacity-100' : 'max-h-0 opacity-0'}`}>
        <div className={`border-t px-2 pt-2 pb-3 space-y-1 ${isDark ? 'border-gray-800 bg-gray-900' : 'mobile-menu-light'}`}>
            {visibleNavItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`
                  px-3 py-2.5 rounded-lg font-medium transition-all duration-200 border
                  flex items-center space-x-2
                  ${
                    isExactActive(item.path)
                      ? (isDark ? 'bg-primary-500/15 text-primary-400 border-primary-500/40' : 'nav-item-active')
                      : (isDark ? 'text-gray-400 border-gray-800/60 hover:bg-gray-800/60 hover:text-white hover:border-gray-600' : 'nav-item-inactive')
                  }
                `}
              >
                <span>{item.icon}</span>
                <span>{translate(item.label.bn, item.label.en)}</span>
              </Link>
            ))}

            {/* Mobile Auth Section */}
            {isAuthenticated ? (
              <div className={`border-t pt-2 mt-2 space-y-1 ${isDark ? 'border-gray-800' : 'mobile-divider-light'}`}>
                {/* Admin users link (mobile) */}
                {isAdmin && (
                  <Link
                    to="/admin/users"
                    onClick={() => setIsMobileMenuOpen(false)}
                    className={`flex items-center space-x-2 px-3 py-2.5 rounded-lg font-medium transition-all duration-200 border ${
                      isExactActive('/admin/users')
                        ? (isDark ? 'bg-yellow-500/15 text-yellow-400 border-yellow-500/40' : 'nav-item-admin-active')
                        : (isDark ? 'text-gray-400 border-gray-800/60 hover:bg-yellow-500/10 hover:text-yellow-400 hover:border-yellow-500/30' : 'nav-item-admin-inactive')
                    }`}
                  >
                    <Users className="w-4 h-4" />
                    <span>{translate('ব্যবহারকারী পরিচালনা করুন', 'Manage users')}</span>
                  </Link>
                )}
                <Link
                  to="/profile"
                  onClick={() => setIsMobileMenuOpen(false)}
                  className={`
                    flex items-center space-x-2 px-3 py-2.5 rounded-lg font-medium transition-all duration-200 border
                    ${
                      isExactActive('/profile')
                        ? (isDark ? 'bg-primary-500/15 text-primary-400 border-primary-500/40' : 'nav-item-active')
                        : (isDark ? 'text-gray-400 border-gray-800/60 hover:bg-gray-800/60 hover:text-white hover:border-gray-600' : 'nav-item-inactive')
                    }
                  `}
                >
                  <span>👤</span>
                  <span>{user?.username}</span>
                  {isAdmin && (
                    <span className="px-1.5 py-0.5 text-[10px] bg-yellow-500/20 text-yellow-400 rounded font-semibold">
                      {translate('অ্যাডমিন', 'Admin')}
                    </span>
                  )}
                </Link>
                <button
                  onClick={() => {
                    logout();
                    setIsMobileMenuOpen(false);
                  }}
                  className={`w-full text-left px-3 py-2.5 rounded-lg border flex items-center space-x-2 transition-all duration-200 ${isDark ? 'text-red-400 border-gray-800/60 hover:bg-red-500/10 hover:border-red-500/40' : 'logout-mobile-light'}`}
                >
                  <LogOut className="w-4 h-4" />
                  <span>{translate('লগ আউট', 'Logout')}</span>
                </button>
              </div>
            ) : (
              <Link
                to="/login"
                onClick={() => setIsMobileMenuOpen(false)}
                className="block px-3 py-2.5 rounded-lg font-medium bg-primary-500 text-white hover:bg-primary-600 transition-all duration-200 text-center border border-primary-500"
              >
                {translate('লগ ইন', 'Login')}
              </Link>
            )}
          </div>
        </div>
    </nav>
  );
};

export default Navbar;
