"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { supabase } from "@/lib/supabase";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setErr(null);
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email,
        password,
      });
      
      if (error) throw error;
      
      // Store token for the existing API proxy if still needed
      if (data.session?.access_token) {
        localStorage.setItem("dh_portal_token", data.session.access_token);
      }
      
      router.push("/dashboard");
    } catch (e: any) {
      setErr(e.message || "Login failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex items-center justify-center p-4 bg-slate-50">
      <form onSubmit={onSubmit} className="card w-full max-w-md space-y-6">
        <div className="text-center">
          <h1 className="text-3xl font-black text-slate-800">DishHome</h1>
          <p className="text-orange-600 font-bold text-sm tracking-widest uppercase">Customer Portal</p>
        </div>
        
        <div className="space-y-4">
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Email Address</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="name@example.com"
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-orange-500 outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-bold text-slate-500 uppercase mb-1">Password</label>
            <input
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              className="w-full border border-slate-200 rounded-xl px-4 py-3 focus:ring-2 focus:ring-orange-500 outline-none"
            />
          </div>
        </div>

        {err && (
          <div className="bg-red-50 text-red-600 text-xs p-3 rounded-lg border border-red-100">
            {err}
          </div>
        )}

        <button type="submit" disabled={loading} className="btn-primary w-full py-4 rounded-xl disabled:opacity-50 text-base">
          {loading ? "Verifying..." : "Sign In to Portal"}
        </button>
        
        <p className="text-center text-xs text-slate-400">
          Managed via Supabase Cloud Infrastructure
        </p>
      </form>
    </main>
  );
}
