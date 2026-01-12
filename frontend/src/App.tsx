import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import HomePage from './pages/HomePage';
import ArticlesPage from './pages/ArticlesPage';
import ArticleDetailPage from './pages/ArticleDetailPage';
import DashboardPage from './pages/DashboardPage';
import ManualScrapingPage from './pages/ManualScrapingPage';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
        <Navbar />
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/articles" element={<ArticlesPage />} />
          <Route path="/article/:id" element={<ArticleDetailPage />} />
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/scrape" element={<ManualScrapingPage />} />
        </Routes>

        {/* Footer */}
        <footer className="border-t border-gray-800 mt-12 py-8">
          <div className="max-w-7xl mx-auto px-4 text-center text-gray-400 text-sm">
            <p>© 2026 BiasFree News. Powered by AI to ensure unbiased journalism.</p>
          </div>
        </footer>
      </div>
    </Router>
  );
}

export default App;
