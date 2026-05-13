"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getInvoices } from "@/lib/api";

export default function InvoicesPage() {
  const [items, setItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const r = await getInvoices();
        setItems(r.items || []);
      } catch {}
      setLoading(false);
    })();
  }, []);

  return (
    <main className="max-w-5xl mx-auto p-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">Invoices</h1>
        <Link href="/dashboard" className="text-blue-600 text-sm">← Dashboard</Link>
      </header>
      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-gray-500 border-b">
            <tr>
              <th className="py-2">Invoice #</th>
              <th>Total (NPR)</th>
              <th>Due Date</th>
              <th>Status</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={5} className="py-4">Loading…</td></tr>}
            {!loading && !items.length && <tr><td colSpan={5} className="py-4 text-gray-500">No invoices.</td></tr>}
            {items.map((inv) => (
              <tr key={inv.id} className="border-b">
                <td className="py-3 font-mono">{inv.invoice_number}</td>
                <td>{Number(inv.total_amount).toFixed(2)}</td>
                <td>{inv.due_date}</td>
                <td>
                  <span className={`px-2 py-0.5 rounded text-xs ${
                    inv.status === "paid" ? "bg-green-100 text-green-700" :
                    inv.status === "overdue" ? "bg-red-100 text-red-700" :
                    "bg-yellow-100 text-yellow-700"
                  }`}>{inv.status}</span>
                </td>
                <td>
                  {inv.status !== "paid" && (
                    <button className="text-blue-600 text-sm">Pay Now</button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </main>
  );
}
