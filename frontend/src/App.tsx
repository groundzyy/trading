import React, { createContext, useContext, useEffect, useState, useCallback } from "react";
import { Routes, Route, Navigate, useNavigate, Link } from "react-router-dom";
import type { User } from "@/types";
import { getMe } from "@/services/api";
import Dashboard from "@/pages/Dashboard";
import StockDetail from "@/pages/StockDetail";
import Scanner from "@/pages/Scanner";
import Login from "@/pages/Login";

// ---------- Auth Context ----------
interface AuthContextValue {
  user: User | null;
  loading: boolean;
  setUser: (u: User | null) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue>({
  user: null,
  loading: true,
  setUser: () => {},
  logout: () => {},
});

export function useAuth() {
  return useContext(AuthContext);
}

// ---------- Global Styles ----------
const globalStyles = `
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: #1a1a2e;
    color: #e0e0e0;
    min-height: 100vh;
  }
  a { color: #e0e0e0; text-decoration: none; }
  a:hover { color: #ffffff; }
  input, button, select {
    font-family: inherit;
    font-size: inherit;
  }
  ::-webkit-scrollbar { width: 8px; }
  ::-webkit-scrollbar-track { background: #1a1a2e; }
  ::-webkit-scrollbar-thumb { background: #0f3460; border-radius: 4px; }
`;

// ---------- Protected Route ----------
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: "100vh" }}>
        <div style={{ color: "#8a8a9a", fontSize: 18 }}>Loading...</div>
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}

// ---------- Navbar ----------
function Navbar() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [search, setSearch] = useState("");

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const symbol = search.trim().toUpperCase();
    if (symbol) {
      navigate(`/stock/${symbol}`);
      setSearch("");
    }
  };

  if (!user) return null;

  return (
    <nav style={navStyle}>
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        <Link to="/" style={{ fontSize: 20, fontWeight: 700, color: "#e94560", letterSpacing: 1 }}>
          TradingSignal
        </Link>
        <form onSubmit={handleSearch} style={{ display: "flex", gap: 8 }}>
          <input
            type="text"
            placeholder="Search symbol..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={searchInputStyle}
          />
          <button type="submit" style={searchBtnStyle}>Go</button>
        </form>
      </div>
      <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
        <Link to="/" style={navLinkStyle}>Dashboard</Link>
        <Link to="/scanner" style={navLinkStyle}>Scanner</Link>
        <span style={{ color: "#8a8a9a", fontSize: 14 }}>{user.username}</span>
        <button onClick={logout} style={logoutBtnStyle}>Logout</button>
      </div>
    </nav>
  );
}

const navStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "space-between",
  alignItems: "center",
  padding: "12px 24px",
  background: "#16213e",
  borderBottom: "1px solid #0f3460",
  position: "sticky",
  top: 0,
  zIndex: 100,
};

const searchInputStyle: React.CSSProperties = {
  padding: "6px 12px",
  background: "#1a1a2e",
  border: "1px solid #0f3460",
  borderRadius: 4,
  color: "#e0e0e0",
  width: 180,
  outline: "none",
};

const searchBtnStyle: React.CSSProperties = {
  padding: "6px 14px",
  background: "#0f3460",
  border: "none",
  borderRadius: 4,
  color: "#e0e0e0",
  cursor: "pointer",
};

const navLinkStyle: React.CSSProperties = {
  color: "#b0b0c0",
  fontSize: 14,
  fontWeight: 500,
  transition: "color 0.2s",
};

const logoutBtnStyle: React.CSSProperties = {
  padding: "4px 12px",
  background: "transparent",
  border: "1px solid #e94560",
  borderRadius: 4,
  color: "#e94560",
  cursor: "pointer",
  fontSize: 13,
};

// ---------- App ----------
export default function App() {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) {
      setLoading(false);
      return;
    }
    getMe()
      .then((u) => setUser(u))
      .catch(() => {
        localStorage.removeItem("token");
      })
      .finally(() => setLoading(false));
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, setUser, logout }}>
      <style>{globalStyles}</style>
      <Navbar />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/stock/:symbol"
          element={
            <ProtectedRoute>
              <StockDetail />
            </ProtectedRoute>
          }
        />
        <Route
          path="/scanner"
          element={
            <ProtectedRoute>
              <Scanner />
            </ProtectedRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </AuthContext.Provider>
  );
}
