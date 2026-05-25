import UserProfile from "@/components/UserProfile";
import { User, Settings, History, Download } from "lucide-react";

export default function Profile() {
  return (
    <div className="min-h-screen bg-black text-white pb-16">
      {/* Header */}
      <div className="bg-zinc-900 border-b border-zinc-800 py-10">
        <div className="max-w-5xl mx-auto px-6">
          <h1 className="text-4xl font-bold mb-2">My Account</h1>
          <p className="text-gray-400">Manage your profile, preferences, and activity</p>
        </div>
      </div>

      <div className="max-w-5xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-10">
          {/* Sidebar Navigation */}
          <div className="lg:col-span-3">
            <div className="sticky top-20">
              <nav className="space-y-1">
                <a href="#" className="flex items-center gap-3 px-4 py-3 bg-zinc-800 rounded-xl text-white font-medium">
                  <User size={20} />
                  Profile
                </a>
                <a href="#" className="flex items-center gap-3 px-4 py-3 hover:bg-zinc-900 rounded-xl text-gray-400 hover:text-white transition-colors">
                  <History size={20} />
                  Watch History
                </a>
                <a href="/downloads" className="flex items-center gap-3 px-4 py-3 hover:bg-zinc-900 rounded-xl text-gray-400 hover:text-white transition-colors">
                  <Download size={20} />
                  Downloads
                </a>
                <a href="#" className="flex items-center gap-3 px-4 py-3 hover:bg-zinc-900 rounded-xl text-gray-400 hover:text-white transition-colors">
                  <Settings size={20} />
                  Settings
                </a>
              </nav>
            </div>
          </div>

          {/* Main Content */}
          <div className="lg:col-span-9">
            <div className="bg-zinc-900 rounded-2xl p-8 border border-zinc-800">
              <UserProfile />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}