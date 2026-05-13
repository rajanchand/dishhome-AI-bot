"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getProfile, getAreaOutage } from "@/lib/api";
import { Activity, CreditCard, LayoutDashboard, Package, Receipt, Signal, Zap } from "lucide-react";

export default function DashboardPage() {
  const [profile, setProfile] = useState<any>(null);
  const [outage, setOutage] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [p, o] = await Promise.all([getProfile(), getAreaOutage()]);
        setProfile(p);
        setOutage(o);
      } catch (err) {
        console.error("Dashboard data fetch failed", err);
      }
      setLoading(false);
    })();
  }, []);

  if (loading) return (
    <div className="flex items-center justify-center min-h-screen bg-slate-50">
      <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-orange-500"></div>
    </div>
  );

  if (!profile) return (
    <main className="flex flex-col items-center justify-center min-h-screen p-6 text-center">
      <h2 className="text-2xl font-bold text-slate-800">Session Expired</h2>
      <p className="text-slate-500 mt-2">Please sign in to access your portal.</p>
      <Link href="/login" className="btn-primary mt-6">Sign In</Link>
    </main>
  );

  const sub = profile.active_subscription;
  const device = profile.devices?.[0];
  const outstandingAmount = (profile.outstanding_invoices ?? []).reduce((sum: number, i: any) => sum + (i.total_amount || 0), 0);

  return (
    <div className="min-h-screen bg-slate-50 pb-12">
      {/* Navigation */}
      <nav className="sticky top-0 z-50 bg-white/80 backdrop-blur-md border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex justify-between h-16 items-center">
            <div className="flex items-center gap-2">
              <div className="bg-orange-500 p-2 rounded-lg">
                <Zap className="text-white w-6 h-6" />
              </div>
              <span className="text-xl font-bold tracking-tight">DishHome <span className="text-orange-600">Portal</span></span>
            </div>
            <div className="hidden md:flex items-center gap-8 text-sm font-medium">
              <Link href="/dashboard" className="text-orange-600 border-b-2 border-orange-500 pb-5 pt-5">Overview</Link>
              <Link href="/dashboard/invoices" className="text-slate-600 hover:text-orange-600 transition">Invoices</Link>
              <Link href="/dashboard/tickets" className="text-slate-600 hover:text-orange-600 transition">Tickets</Link>
              <Link href="/dashboard/upgrade" className="text-slate-600 hover:text-orange-600 transition">Upgrade</Link>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right hidden sm:block">
                <p className="text-sm font-semibold">{profile.full_name}</p>
                <p className="text-xs text-slate-500">#{profile.customer_code}</p>
              </div>
              <div className="w-10 h-10 rounded-full bg-slate-200 border border-slate-300 flex items-center justify-center text-slate-600 font-bold">
                {profile.full_name.charAt(0)}
              </div>
            </div>
          </div>
        </div>
      </nav>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-8 space-y-8">
        {/* Alerts */}
        {outage?.has_outage && (
          <div className="bg-red-50 border border-red-100 rounded-2xl p-4 flex items-start gap-4 animate-pulse">
            <Activity className="text-red-500 w-6 h-6 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-bold text-red-800">Network Alert: {outage.title}</h3>
              <p className="text-sm text-red-700/80 mt-1">Our team is working to restore services in your area.</p>
              {outage.estimated_resolution && (
                <p className="text-xs font-semibold text-red-900 mt-2">Estimated Restoration: {new Date(outage.estimated_resolution).toLocaleTimeString()}</p>
              )}
            </div>
          </div>
        )}

        {/* Hero KPI Section */}
        <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="card bg-gradient-to-br from-orange-500 to-red-600 text-white border-none">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-white/20 p-2 rounded-xl">
                <Package className="w-6 h-6" />
              </div>
              <span className="text-xs font-bold uppercase tracking-wider bg-white/20 px-2 py-1 rounded-full">Active</span>
            </div>
            <h3 className="text-sm font-medium opacity-80">Current Subscription</h3>
            <p className="text-2xl font-bold mt-1">{sub?.package_name || "No Plan Selected"}</p>
            <div className="flex items-center gap-4 mt-6 text-sm">
              <div className="flex flex-col">
                <span className="opacity-70 text-[10px] uppercase">Speed</span>
                <span className="font-bold">{sub?.speed_down || 0} Mbps</span>
              </div>
              <div className="w-px h-8 bg-white/20"></div>
              <div className="flex flex-col">
                <span className="opacity-70 text-[10px] uppercase">Expiry</span>
                <span className="font-bold">{sub?.expires_at ? new Date(sub.expires_at).toLocaleDateString() : "N/A"}</span>
              </div>
            </div>
          </div>

          <div className="card">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-blue-50 p-2 rounded-xl">
                <Signal className="text-blue-600 w-6 h-6" />
              </div>
              <div className="flex items-center gap-1.5">
                <div className={`w-2 h-2 rounded-full ${device?.status === 'online' ? 'bg-green-500' : 'bg-slate-400'}`}></div>
                <span className="text-xs font-bold uppercase text-slate-500">{device?.status || 'offline'}</span>
              </div>
            </div>
            <h3 className="text-sm font-medium text-slate-500">Router Signal Status</h3>
            <p className="text-2xl font-bold text-slate-800 mt-1">{device?.signal_quality === 'excellent' ? 'Excellent' : device?.signal_quality === 'good' ? 'Stable' : 'Weak'}</p>
            <p className="text-xs text-slate-400 mt-2 italic">Last seen: {device?.last_seen_at ? new Date(device.last_seen_at).toLocaleTimeString() : 'Unknown'}</p>
            <div className="mt-4 flex gap-2">
              <button className="text-xs font-bold text-blue-600 hover:underline">Run Diagnostics</button>
              <span className="text-slate-300">•</span>
              <button className="text-xs font-bold text-blue-600 hover:underline">Reboot Router</button>
            </div>
          </div>

          <div className="card">
            <div className="flex justify-between items-start mb-4">
              <div className="bg-emerald-50 p-2 rounded-xl">
                <Receipt className="text-emerald-600 w-6 h-6" />
              </div>
              {outstandingAmount > 0 && <span className="bg-red-100 text-red-600 text-[10px] font-black px-2 py-0.5 rounded-full uppercase">Due</span>}
            </div>
            <h3 className="text-sm font-medium text-slate-500">Balance Due</h3>
            <p className="text-2xl font-bold text-slate-800 mt-1">NPR {outstandingAmount.toLocaleString()}</p>
            <p className="text-xs text-slate-400 mt-2">{(profile.outstanding_invoices ?? []).length} unpaid invoices pending</p>
            <button className="btn-primary w-full mt-4 text-xs">Pay Now</button>
          </div>
        </section>

        {/* Secondary Section */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
                <LayoutDashboard className="w-5 h-5 text-orange-500" />
                Quick Actions
              </h2>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              {[
                { label: "Change WiFi", icon: Signal, color: "text-blue-600", bg: "bg-blue-50" },
                { label: "Upgrade Plan", icon: Zap, color: "text-orange-600", bg: "bg-orange-50" },
                { label: "Support Ticket", icon: Activity, color: "text-indigo-600", bg: "bg-indigo-50" },
                { label: "Payment History", icon: CreditCard, color: "text-emerald-600", bg: "bg-emerald-50" },
              ].map((action, i) => (
                <button key={i} className="card flex flex-col items-center justify-center gap-3 py-8 hover:-translate-y-1 transition-transform border-none shadow-sm">
                  <div className={`${action.bg} ${action.color} p-3 rounded-2xl`}>
                    <action.icon className="w-6 h-6" />
                  </div>
                  <span className="text-xs font-bold text-slate-700">{action.label}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="space-y-6">
            <h2 className="text-lg font-bold text-slate-800">Support</h2>
            <div className="card bg-slate-900 text-white border-none overflow-hidden relative">
              <div className="relative z-10">
                <h3 className="font-bold">Need Help?</h3>
                <p className="text-xs text-slate-400 mt-1">Talk to Nexa, our AI Assistant</p>
                <button className="bg-white text-slate-900 text-xs font-bold px-4 py-2 rounded-lg mt-4 flex items-center gap-2">
                  <Zap className="w-3 h-3 fill-orange-500 text-orange-500" />
                  Start AI Chat
                </button>
              </div>
              <div className="absolute -right-4 -bottom-4 w-24 h-24 bg-orange-500/20 rounded-full blur-2xl"></div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
