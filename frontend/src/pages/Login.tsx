import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "@/App";
import { login as apiLogin, register as apiRegister, getMe } from "@/services/api";

export default function Login() {
  const { user, setUser } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  // Redirect if already logged in
  if (user) {
    navigate("/", { replace: true });
    return null;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSubmitting(true);

    try {
      if (mode === "register") {
        await apiRegister(email, username, password);
        // After registration, log in automatically
      }

      const { access_token } = await apiLogin(username, password);
      localStorage.setItem("token", access_token);
      const me = await getMe();
      setUser(me);
      navigate("/", { replace: true });
    } catch (err: unknown) {
      if (err && typeof err === "object" && "response" in err) {
        const axErr = err as { response?: { data?: { detail?: string } } };
        setError(axErr.response?.data?.detail || "Something went wrong");
      } else {
        setError("Network error");
      }
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div style={containerStyle}>
      <div style={cardStyle}>
        <h1 style={{ color: "#e94560", fontSize: 28, marginBottom: 4, textAlign: "center" }}>
          TradingSignal
        </h1>
        <p style={{ color: "#8a8a9a", fontSize: 14, marginBottom: 28, textAlign: "center" }}>
          {mode === "login" ? "Sign in to your account" : "Create a new account"}
        </p>

        {error && (
          <div style={errorStyle}>{error}</div>
        )}

        <form onSubmit={handleSubmit}>
          {mode === "register" && (
            <div style={fieldStyle}>
              <label style={labelStyle}>Email</label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                style={inputStyle}
                placeholder="you@example.com"
              />
            </div>
          )}

          <div style={fieldStyle}>
            <label style={labelStyle}>Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              style={inputStyle}
              placeholder="username"
            />
          </div>

          <div style={fieldStyle}>
            <label style={labelStyle}>Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              style={inputStyle}
              placeholder="password"
            />
          </div>

          <button type="submit" disabled={submitting} style={submitBtnStyle}>
            {submitting ? "..." : mode === "login" ? "Sign In" : "Create Account"}
          </button>
        </form>

        <div style={{ textAlign: "center", marginTop: 20 }}>
          <span style={{ color: "#8a8a9a", fontSize: 14 }}>
            {mode === "login" ? "Don't have an account? " : "Already have an account? "}
          </span>
          <button
            onClick={() => {
              setMode(mode === "login" ? "register" : "login");
              setError("");
            }}
            style={toggleBtnStyle}
          >
            {mode === "login" ? "Register" : "Sign In"}
          </button>
        </div>
      </div>
    </div>
  );
}

const containerStyle: React.CSSProperties = {
  display: "flex",
  justifyContent: "center",
  alignItems: "center",
  minHeight: "100vh",
  background: "#1a1a2e",
  padding: 20,
};

const cardStyle: React.CSSProperties = {
  background: "#16213e",
  borderRadius: 12,
  padding: "40px 36px",
  width: "100%",
  maxWidth: 400,
  border: "1px solid #0f3460",
};

const fieldStyle: React.CSSProperties = {
  marginBottom: 16,
};

const labelStyle: React.CSSProperties = {
  display: "block",
  color: "#b0b0c0",
  fontSize: 13,
  marginBottom: 6,
  fontWeight: 500,
};

const inputStyle: React.CSSProperties = {
  width: "100%",
  padding: "10px 14px",
  background: "#1a1a2e",
  border: "1px solid #0f3460",
  borderRadius: 6,
  color: "#e0e0e0",
  fontSize: 15,
  outline: "none",
};

const submitBtnStyle: React.CSSProperties = {
  width: "100%",
  padding: "12px 0",
  background: "#e94560",
  border: "none",
  borderRadius: 6,
  color: "#fff",
  fontSize: 16,
  fontWeight: 600,
  cursor: "pointer",
  marginTop: 8,
};

const toggleBtnStyle: React.CSSProperties = {
  background: "none",
  border: "none",
  color: "#e94560",
  cursor: "pointer",
  fontSize: 14,
  fontWeight: 600,
};

const errorStyle: React.CSSProperties = {
  background: "rgba(233, 69, 96, 0.15)",
  border: "1px solid #e94560",
  borderRadius: 6,
  padding: "10px 14px",
  color: "#e94560",
  fontSize: 14,
  marginBottom: 16,
};
