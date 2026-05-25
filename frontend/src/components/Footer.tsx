import { Link } from "@tanstack/react-router";

export default function Footer() {
  return (
    <footer className="bg-black text-white py-8 mt-12">
      <div className="container mx-auto px-6">
        <div className="flex flex-col md:flex-row justify-between items-center">
          <div className="mb-4 md:mb-0">
            <h3 className="text-2xl font-bold text-red-600">Watch!fy</h3>
            <p className="text-gray-500 mt-2">
              Unlimited movies, TV shows, and downloads. Stream anywhere, anytime.
            </p>
          </div>
          
          <div className="mb-4 md:mb-0">
            <div className="flex gap-4">
              <Link to="/privacy" className="text-gray-400 hover:text-white">
                Privacy
              </Link>
              <Link to="/terms" className="text-gray-400 hover:text-white">
                Terms
              </Link>
              <Link to="/help" className="text-gray-400 hover:text-white">
                Help
              </Link>
            </div>
          </div>
          
          <div className="text-gray-500 text-sm">
            &copy; {new Date().getFullYear()} Watch!fy. All rights reserved.
          </div>
        </div>
      </div>
    </footer>
  );
}