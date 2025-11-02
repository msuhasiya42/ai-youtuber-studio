import React from 'react';

type View = 'dashboard' | 'contentStudio' | 'analyzer' | 'videoStatus' | 'allVideos';

interface NavbarProps {
  currentView: View;
  onNavigate: (view: View) => void;
}

const Navbar: React.FC<NavbarProps> = ({ currentView, onNavigate }) => {
  const navItems: { view: View; label: string; icon: string }[] = [
    { view: 'dashboard', label: 'Home', icon: '🏠' },
    { view: 'contentStudio', label: 'Content Studio', icon: '🎬' },
    { view: 'analyzer', label: 'Performance Analyzer', icon: '📊' },
    { view: 'videoStatus', label: 'Processing Status', icon: '⚙️' },
    { view: 'allVideos', label: 'All Videos', icon: '📹' },
  ];

  return (
    <nav className="bg-gray-800 border-b border-gray-700">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          {/* Logo/Brand */}
          <div className="flex items-center">
            <h1 className="text-xl font-bold text-white">AI YouTuber Studio</h1>
          </div>

          {/* Navigation Links */}
          <div className="flex space-x-1">
            {navItems.map((item) => (
              <button
                key={item.view}
                onClick={() => onNavigate(item.view)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  currentView === item.view
                    ? 'bg-gray-900 text-white'
                    : 'text-gray-300 hover:bg-gray-700 hover:text-white'
                }`}
              >
                <span className="mr-2">{item.icon}</span>
                <span className="hidden sm:inline">{item.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
};

export default Navbar;
