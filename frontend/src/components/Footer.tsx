import { Link } from 'react-router-dom';

const Footer = () => {
  return (
    <footer className="border-t border-gray-800/60 bg-gray-950/80 backdrop-blur-sm mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
          {/* Brand */}
          <div>
            <div className="flex items-center gap-2 mb-3">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-emerald-500 rounded-lg flex items-center justify-center">
                <span className="text-lg">✨</span>
              </div>
              <span className="text-lg font-bold bg-gradient-to-r from-primary-400 to-emerald-400 bg-clip-text text-transparent">
                BiasFree News
              </span>
            </div>
            <p className="text-xs text-gray-500 leading-relaxed">
              নিরপেক্ষ সংবাদ — AI-powered bias detection and analysis for Bangladeshi news media.
            </p>
          </div>

          {/* Quick Links */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">Quick Links</h4>
            <div className="space-y-1.5">
              <Link to="/" className="block text-xs text-gray-500 hover:text-primary-400 transition-colors">Analyze Article</Link>
              <Link to="/articles" className="block text-xs text-gray-500 hover:text-primary-400 transition-colors">Browse Articles</Link>
              <Link to="/clusters" className="block text-xs text-gray-500 hover:text-primary-400 transition-colors">Article Clusters</Link>
            </div>
          </div>

          {/* Info */}
          <div>
            <h4 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">About</h4>
            <p className="text-xs text-gray-500 leading-relaxed">
              Automated bias detection system for Bengali news articles.
            </p>
            <p className="text-[10px] text-gray-600 mt-2">
              v1.0.0
            </p>
          </div>
        </div>

        <div className="mt-6 pt-4 border-t border-gray-800/40 text-center">
          <p className="text-[10px] text-gray-600">
            © {new Date().getFullYear()} BiasFree News. All rights reserved.
          </p>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
