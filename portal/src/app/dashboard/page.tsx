"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getProfile, getAreaOutage } from "@/lib/api";

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
      } catch {}
      setLoading(false);
    })();
  }, []);

  if (loading) return <main className="p-8">Loading…</main>;
  if (!profile) return <main className="p-8">Unable to load profile. <Link href="/login" className="text-blue-600">Sign in</Link>.</main>;

  const sub = profile.active_subscription;
  const device = profile.devices?.[0];

  return (
    <main className="max-w-6xl mx-auto p-6 space-y-6">
      <header className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Welcome, {profile.full_name}</h1>
          <p className="text-sm text-gray-500">Customer #{profile.customer_code}</p>
        </div>
        <nav className="flex gap-4 text-sm">
          <Link href="/dashboard" className="text-blue-600">Overview</Link>
          <Link href="/dashboard/invoices" className="text-gray-700">Invoices</Link>
          <Link href="/dashboard/tickets" className="text-gray-700">Tickets</Link>
          <Link href="/dashboard/upgrade" className="text-gray-700">Upgrade</Link>
          <Link href="/dashboard/speed-test" className="text-gray-700">Speed Test</Link>
        </nav>
      </header>

      {outage?.has_outage && (
        <div className="card border-l-4 border-red-500 bg-red-50">
          <h3 className="font-semibold text-red-700">Active Outage in Your Area</h3>
          <p className="text-sm mt-1">{outage.title}</p>
          {outage.estimated_resolution && (
            <p className="text-xs text-gray-600 mt-1">ETA: {new Date(outage.estimated_resolution).toLocaleString()}</p>
          )}
        </div>
      )}

      <div className="grid md:grid-cols-3 gap-4">
        <div className="card">
          <h3 className="font-semibold mb-2">Current Plan</h3>
          {sub ? (
            <>
              <p className="text-lg">{sub.package_name}</p>
              <p className="text-sm text-gray-500">{sub.speed_down} / {sub.speed_up} Mbps</p>
              <p className="text-xs mt-2">Expires {new Date(sub.expires_at).toLocaleDateString()}</p>
            </>
          ) : <p>No active subscription</p>}
        </div>
        <div className="card">
          <h3 className="font-semibold mb-2">Network Status</h3>
          {device ? (
            <>
              <p className="text-lg capitalize">{device.status}</p>
              <p className="text-sm text-gray-500">Signal: {device.signal_quality}</p>
              <p className="text-xs mt-2">Last seen: {device.last_seen_at ? new Date(device.last_seen_at).toLocaleString() : "Never"}</p>
            </>
          ) : <p>No device</p>}
        </div>
        <div className="card">
          <h3 className="font-semibold mb-2">Outstanding Bills</h3>
          <p className="text-2xl font-bold">
            NPR {(profile.outstanding_invoices ?? []).reduce((sum: number, i: any) => sum + (i.total_amount || 0), 0).toFixed(2)}
          </p>
          <p className="text-xs text-gray-500 mt-2">{(profile.outstanding_invoices ?? []).length} pending invoices</p>
        </div>
      </div>
    </main>
  );
}
