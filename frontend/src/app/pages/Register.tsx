import { useState } from "react";
import { useNavigate } from "@tanstack/react-router";
import { useUser } from "@/components/UserProvider";
import { Eye, EyeOff, Loader2 } from "lucide-react";

export default function Register() {
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const navigate = useNavigate();
  const { register } = useUser();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await register(email, username, password);
      navigate({ to: "/home" });
    } catch (err: any) {
      setError(err.message || "Registration failed. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-black flex items-center justify-center px-4 py-12">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-10">
          <h1 className="text-5xl font-bold tracking-tighter text-yellow-500">Watch!fy</h1>
        </div>

        <div className="bg-zinc-900/90 backdrop-blur-md rounded-2xl p-10 shadow-2xl border border-zinc-800">
          <h2 className="text-3xl font-semibold mb-8 text-center">Create Account</h2>

          <form onSubmit={handleSubmit} className="space-y-6">
            <div>
              <label className="text-sm text-gray-400 block mb-2">Email Address</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 focus:border-yellow-500 rounded-lg px-5 py-3.5 text-white placeholder-gray-500 focus:outline-none transition-colors"
                placeholder="you@example.com"
                required
              />
            </div>

            <div>
              <label className="text-sm text-gray-400 block mb-2">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-zinc-800 border border-zinc-700 focus:border-yellow-500 rounded-lg px-5 py-3.5 text-white placeholder-gray-500 focus:outline-none transition-colors"
                placeholder="johndoe"
                required
              />
            </div>

            <div>
              <label className="text-sm text-gray-400 block mb-2">Password</label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-zinc-800 border border-zinc-700 focus:border-yellow-500 rounded-lg px-5 py-3.5 text-white placeholder-gray-500 focus:outline-none transition-colors"
                  placeholder="••••••••"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-1/2 -translate-y-1/2 text-gray-400 hover:text-white transition-colors"
                >
                  {showPassword ? <EyeOff size={20} /> : <Eye size={20} />}
                </button>
              </div>
            </div>

            {error && (
              <p className="text-red-500 text-sm bg-red-500/10 border border-red-500/30 rounded-lg p-3">
                {error}
              </p>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-red-600 hover:bg-red-700 disabled:bg-red-700/70 transition-all py-3.5 rounded-lg font-semibold text-lg flex items-center justify-center gap-2"
            >
              {loading ? (
                <>
                  <Loader2 size={22} className="animate-spin" />
                  Creating Account...
                </>
              ) : (
                "Create Account"
              )}
            </button>

            <div className="text-xs text-gray-500 text-center">
              By signing up, you agree to our{" "}
              <a href="#" className="text-gray-400 hover:text-white underline">Terms of Service</a>
            </div>
          </form>

          <div className="mt-8 text-center text-sm text-gray-500">
            Already have an account?{" "}
            <a href="/login" className="text-white hover:text-yellow-500 transition-colors font-medium">
              Sign in
            </a>
          </div>
        </div>

        <p className="text-center text-xs text-gray-600 mt-8">
          Your information is secure and encrypted.
        </p>
      </div>
    </div>
  );
}