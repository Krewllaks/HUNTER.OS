"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/context/AuthContext";
import { Crosshair, Eye, EyeOff } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState("");
  const [isLoading, setIsLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setIsLoading(true);

    try {
      await login(email, password);
      router.push("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-background flex items-center justify-center p-grid-4">
      <div className="w-full max-w-md">
        {/* Logo */}
        <div className="text-center mb-grid-8">
          <div className="inline-flex items-center gap-3 mb-grid-2">
            <Crosshair size={32} className="text-primary" />
            <h1 className="font-display text-display-lg tracking-tight">
              HUNTER<span className="text-primary">.OS</span>
            </h1>
          </div>
          <p className="text-body-md text-text-secondary">
            AI-Powered Sales Hunter
          </p>
        </div>

        {/* Login Card */}
        <div className="card">
          <h2 className="font-display text-display-sm mb-grid-3">Sign In</h2>

          <form onSubmit={handleSubmit} className="space-y-grid-2">
            {error && (
              <div className="bg-danger/10 text-danger text-body-sm p-grid-2 rounded-sm">
                {error}
              </div>
            )}

            <div>
              <label className="text-label text-text-muted block mb-1">
                EMAIL
              </label>
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className="input"
                placeholder="you@company.com"
                required
                autoFocus
              />
            </div>

            <div>
              <label className="text-label text-text-muted block mb-1">
                PASSWORD
              </label>
              <div className="relative">
                <input
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="input pr-10"
                  placeholder="Enter your password"
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text"
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={isLoading}
              className="btn-primary w-full mt-grid-2"
            >
              {isLoading ? "Signing in..." : "Sign In"}
            </button>
          </form>

          <p className="text-body-sm text-text-muted text-center mt-grid-3">
            Don&apos;t have an account?{" "}
            <Link href="/register" className="text-primary hover:underline">
              Create one
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
