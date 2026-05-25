import { createContext, useContext, useEffect, useState } from "react";

interface UserContextType {
  user: any | null;
  loading: boolean;
  error: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (
    email: string, 
    username: string, 
    password: string
  ) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const useUser = () => {
  const context = useContext(UserContext);
  if (!context) {
    throw new Error("useUser must be used within UserProvider");
  }
  return context;
};

export default function UserProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("access_token");
    if (token) {
      fetchProfile();
    } else {
      setLoading(false);
    }
  }, []);

  const fetchProfile = async () => {
    try {
      const response = await fetch("/api/auth/profile", {
        headers: { Authorization: `Bearer ${localStorage.getItem("access_token")}` },
      });
      if (response.ok) {
        const profile = await response.json();
        setUser(profile);
      } else {
        localStorage.removeItem("access_token");
        localStorage.removeItem("refresh_token");
      }
    } catch (err) {
      console.error("Error fetching profile:", err);
      localStorage.removeItem("access_token");
      localStorage.removeItem("refresh_token");
    } finally {
      setLoading(false);
    }
  };

  const login = async (email: string, password: string) => {
    try {
      const response = await fetch("/api/auth/token", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username: email, password }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Login failed");
      }
      
      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      setUser({ email, username: email });
    } catch (err: any) {
      throw new Error(err.message || "Login failed");
    }
  };

  const register = async (
    email: string,
    username: string,
    password: string
  ) => {
    try {
      const response = await fetch("/api/auth/register", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, username, password }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || "Registration failed");
      }
      
      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      localStorage.setItem("refresh_token", data.refresh_token);
      
      return data;
    } catch (err: any) {
      throw new Error(err.message || "Registration failed");
    }
  };

  const logout = async () => {
    localStorage.removeItem("access_token");
    localStorage.removeItem("refresh_token");
    setUser(null);
  };

  const refreshToken = async () => {
    try {
      const refresh_token = localStorage.getItem("refresh_token");
      if (!refresh_token) {
        throw new Error("No refresh token found");
      }
      
      const response = await fetch("/api/auth/token/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token }),
      });
      
      if (!response.ok) {
        throw new Error("Failed to refresh token");
      }
      
      const data = await response.json();
      localStorage.setItem("access_token", data.access_token);
      return data.access_token;
    } catch (err: any) {
      console.error("Refresh token error:", err);
      throw err;
    }
  };

  return (
    <UserContext.Provider value={{ user, loading, error, login, register, logout, refreshToken }}>
      {children}
    </UserContext.Provider>
  );
}