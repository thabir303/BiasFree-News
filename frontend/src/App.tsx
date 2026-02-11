import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './contexts/AuthContext';
import Navbar from './components/Navbar';
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
import ProfilePage from './pages/ProfilePage';

function App() {
  return (
    <Router>
      <AuthProvider>
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
          <Navbar />
          <Routes>
            {/* Public Routes */}
            <Route path="/" element={<HomePage />} />
            <Route path="/articles" element={<ArticlesPage />} />
            <Route path="/articles/category/:categoryName" element={<CategoryArticlesPage />} />
            <Route path="/article/:id" element={<ArticleDetailPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/signup" element={<SignupPage />} />
            <Route path="/verify-email/:token" element={<VerifyEmailPage />} />

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
          </Routes>

        </div>
      </AuthProvider>
    </Router>
  );
}

export default App;
