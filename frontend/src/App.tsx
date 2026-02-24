import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import { AuthProvider } from './contexts/AuthContext';
import { ThemeProvider, useTheme } from './contexts/ThemeContext';
import Navbar from './components/Navbar';
import Footer from './components/Footer';
import ErrorBoundary from './components/ErrorBoundary';
import ProtectedRoute from './components/ProtectedRoute';
import HomePage from './pages/HomePage';
import ArticlesPage from './pages/ArticlesPage';
import CategoryArticlesPage from './pages/CategoryArticlesPage';
import ArticleDetailPage from './pages/ArticleDetailPage';
import DashboardPage from './pages/DashboardPage';
import ManualScrapingPage from './pages/ManualScrapingPage';
import LoginPage from './pages/LoginPage';
import SignupPage from './pages/SignupPage';
import VerifyEmailPage from './pages/VerifyEmailPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import ProfilePage from './pages/ProfilePage';
import AnalysisDetailPage from './pages/AnalysisDetailPage';
import ClustersPage from './pages/ClustersPage';
import ClusterDetailPage from './pages/ClusterDetailPage';
import AdminUsersPage from './pages/AdminUsersPage';

const AppContent = () => {
  const { isDark } = useTheme();
  return (
    <div className={`min-h-screen flex flex-col ${isDark ? 'app-dark' : 'app-light'}`}>
      <Navbar />
      <div className="flex-1">
      <Routes>
        {/* Public Routes */}
        <Route path="/" element={<HomePage />} />
        <Route path="/articles" element={<ArticlesPage />} />
        <Route path="/articles/category/:categoryName" element={<CategoryArticlesPage />} />
        <Route path="/article/:id" element={<ArticleDetailPage />} />
        <Route path="/clusters" element={<ClustersPage />} />
        <Route path="/clusters/:id" element={<ClusterDetailPage />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignupPage />} />
        <Route path="/verify-email/:token" element={<VerifyEmailPage />} />
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />

        {/* Protected Routes - Authenticated Users */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <DashboardPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/analysis/:id"
          element={
            <ProtectedRoute>
              <AnalysisDetailPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/profile"
          element={
            <ProtectedRoute>
              <ProfilePage />
            </ProtectedRoute>
          }
        />

        {/* Protected Routes - Admin Only */}
        <Route
          path="/scrape"
          element={
            <ProtectedRoute requireAdmin>
              <ManualScrapingPage />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin/users"
          element={
            <ProtectedRoute requireAdmin>
              <AdminUsersPage />
            </ProtectedRoute>
          }
        />
      </Routes>
      </div>
      <Footer />
    </div>
  );
};

function App() {
  return (
    <Router>
      <ThemeProvider>
        <AuthProvider>
          <ErrorBoundary>
            <AppContent />
          </ErrorBoundary>
          <Toaster
            position="top-right"
            toastOptions={{
              duration: 4000,
              style: {
                background: '#1e293b',
                color: '#f1f5f9',
                border: '1px solid #334155',
                borderRadius: '12px',
                fontSize: '14px',
              },
              success: {
                iconTheme: { primary: '#34d399', secondary: '#1e293b' },
              },
              error: {
                iconTheme: { primary: '#f87171', secondary: '#1e293b' },
              },
            }}
          />
        </AuthProvider>
      </ThemeProvider>
    </Router>
  );
}

export default App;
