"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getTickets, createTicket } from "@/lib/api";

export default function TicketsPage() {
  const [items, setItems] = useState<any[]>([]);
  const [open, setOpen] = useState(false);
  const [form, setForm] = useState({ category: "connectivity", title: "", description: "", priority: "medium" });

  async function load() {
    try {
      const r = await getTickets();
      setItems(r.items || []);
    } catch {}
  }

  useEffect(() => { load(); }, []);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    await createTicket(form);
    setOpen(false);
    setForm({ category: "connectivity", title: "", description: "", priority: "medium" });
    load();
  }

  return (
    <main className="max-w-5xl mx-auto p-6">
      <header className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">My Tickets</h1>
        <div className="flex gap-3">
          <button onClick={() => setOpen(true)} className="btn-primary">Raise Ticket</button>
          <Link href="/dashboard" className="text-blue-600 text-sm py-2">← Dashboard</Link>
        </div>
      </header>

      <div className="card overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-left text-gray-500 border-b">
            <tr>
              <th className="py-2">Ticket #</th>
              <th>Title</th>
              <th>Category</th>
              <th>Priority</th>
              <th>Status</th>
              <th>Created</th>
            </tr>
          </thead>
          <tbody>
            {!items.length && <tr><td colSpan={6} className="py-4 text-gray-500">No tickets yet.</td></tr>}
            {items.map((t) => (
              <tr key={t.id} className="border-b">
                <td className="py-3 font-mono">{t.ticket_number}</td>
                <td>{t.title}</td>
                <td>{t.category}</td>
                <td><span className="capitalize">{t.priority}</span></td>
                <td><span className="capitalize">{t.status}</span></td>
                <td>{new Date(t.created_at).toLocaleDateString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {open && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center p-4">
          <form onSubmit={submit} className="card w-full max-w-lg space-y-3">
            <h2 className="text-xl font-bold">New Support Ticket</h2>
            <select
              value={form.category}
              onChange={(e) => setForm({ ...form, category: e.target.value })}
              className="w-full border rounded px-3 py-2"
            >
              <option value="connectivity">Connectivity</option>
              <option value="billing">Billing</option>
              <option value="hardware">Hardware</option>
              <option value="inquiry">Inquiry</option>
            </select>
            <input
              required
              placeholder="Title"
              value={form.title}
              onChange={(e) => setForm({ ...form, title: e.target.value })}
              className="w-full border rounded px-3 py-2"
            />
            <textarea
              required
              placeholder="Describe the issue"
              rows={5}
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              className="w-full border rounded px-3 py-2"
            />
            <select
              value={form.priority}
              onChange={(e) => setForm({ ...form, priority: e.target.value })}
              className="w-full border rounded px-3 py-2"
            >
              <option value="low">Low</option>
              <option value="medium">Medium</option>
              <option value="high">High</option>
            </select>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setOpen(false)} className="px-4 py-2">Cancel</button>
              <button type="submit" className="btn-primary">Create</button>
            </div>
          </form>
        </div>
      )}
    </main>
  );
}
