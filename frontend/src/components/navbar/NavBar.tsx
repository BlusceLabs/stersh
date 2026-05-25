import { useState } from "react";
import { Link } from "@tanstack/react-router";
import { Search, User, LogOut, Menu, X } from "lucide-react";
import useUser from "@/store/useUserStore";

export default function NavBar() {
  const { user, logout } = useUser();
  const isAuthenticated = !!user;
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    setIsMobileMenuOpen(false);
  };

  return (
    <header className="fixed top-0 left-0 right-0 z-50 bg-black/95 backdrop-blur-md border-b border-zinc-800">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <Link to="/" className="flex items-center gap-2">
          <span className="text-3xl font-bold tracking-tighter text-yellow-500">Watch!fy</span>
        </Link>

        {/* Desktop Navigation */}
        <nav className="hidden md:flex items-center gap-8 text-sm font-medium">
          <Link to="/home" className="hover:text-yellow-500 transition-colors">
            Home
          </Link>
          <Link to="/movies" className="hover:text-yellow-500 transition-colors">
            Movies
          </Link>
          <Link to="/tv" className="hover:text-yellow-500 transition-colors">
            TV Shows
          </Link>
          <Link to="/search" className="hover:text-yellow-500 transition-colors flex items-center gap-1.5">
            <Search size={18} />
            Search
          </Link>
        </nav>

        {/* Right Side */}
        <div className="flex items-center gap-4">
          {isAuthenticated ? (
            <div className="hidden md:flex items-center gap-4">
              <Link 
                to="/profile" 
                className="flex items-center gap-3 hover:bg-zinc-900 px-4 py-2 rounded-xl transition-colors"
              >
                {user?.avatar ? (
                  <img 
                    src={user.avatar} 
                    alt={user.username} 
                    className="w-8 h-8 rounded-full object-cover border border-yellow-500/30"
                  />
                ) : (
                  <div className="w-8 h-8 bg-zinc-700 rounded-full flex items-center justify-center">
                    <User size={18} />
                  </div>
                )}
                <span className="font-medium">{user?.username}</span>
              </Link>

              <button
                onClick={handleLogout}
                className="p-2 hover:bg-zinc-900 rounded-xl text-gray-400 hover:text-red-500 transition-colors"
                title="Logout"
              >
                <LogOut size={20} />
              </button>
            </div>
          ) : (
            <Link
              to="/login"
              className="hidden md:block px-6 py-2 bg-white text-black font-semibold rounded-xl hover:bg-white/90 transition-colors"
            >
              Sign In
            </Link>
          )}

          {/* Mobile Menu Button */}
          <button
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            className="md:hidden p-2 text-gray-300 hover:text-white transition-colors"
          >
            {isMobileMenuOpen ? <X size={28} /> : <Menu size={28} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden border-t border-zinc-800 bg-black/95 backdrop-blur-md">
          <nav className="flex flex-col px-6 py-6 space-y-4 text-lg">
            <Link 
              to="/home" 
              className="py-3 hover:text-yellow-500 transition-colors"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Home
            </Link>
            <Link 
              to="/movies" 
              className="py-3 hover:text-yellow-500 transition-colors"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Movies
            </Link>
            <Link 
              to="/tv" 
              className="py-3 hover:text-yellow-500 transition-colors"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              TV Shows
            </Link>
            <Link 
              to="/search" 
              className="py-3 hover:text-yellow-500 transition-colors"
              onClick={() => setIsMobileMenuOpen(false)}
            >
              Search
            </Link>

            <div className="pt-4 border-t border-zinc-800">
              {isAuthenticated ? (
                <>
                  <Link 
                    to="/profile" 
                    className="py-3 flex items-center gap-3 hover:text-yellow-500 transition-colors"
                    onClick={() => setIsMobileMenuOpen(false)}
                  >
                    <User size={22} />
                    My Profile
                  </Link>
                  <button 
                    onClick={handleLogout}
                    className="py-3 w-full text-left flex items-center gap-3 text-red-500 hover:text-red-600 transition-colors"
                  >
                    <LogOut size={22} />
                    Logout
                  </button>
                </>
              ) : (
                <Link 
                  to="/login" 
                  className="block w-full py-4 text-center bg-red-600 hover:bg-red-700 rounded-xl font-semibold transition-colors"
                  onClick={() => setIsMobileMenuOpen(false)}
                >
                  Sign In
                </Link>
              )}
            </div>
          </nav>
        </div>
      )}
    </header>
  );
}