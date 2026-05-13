import React, { useState, useEffect } from 'react';
import { 
  Users, Phone, Ticket, Wifi, AlertTriangle, 
  TrendingUp, Clock, Shield, Globe, Cpu,
  BarChart3, Activity, Zap, Search, Bell
} from 'lucide-react';
import { 
  LineChart, Line, AreaChart, Area, 
  XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, PieChart, Pie, Cell 
} from 'recharts';

// --- Mock Data ---
const CALL_METRICS = [
  { time: '10:00', calls: 45, latency: 120 },
  { time: '11:00', calls: 52, latency: 110 },
  { time: '12:00', calls: 85, latency: 145 },
  { time: '13:00', calls: 65, latency: 130 },
  { time: '14:00', calls: 48, latency: 115 },
  { time: '15:00', calls: 70, latency: 125 },
];

const NETWORK_HEALTH = [
  { name: 'Kathmandu', online: 98.5, total: 12500 },
  { name: 'Lalitpur', online: 99.2, total: 8400 },
  { name: 'Bhaktapur', online: 97.8, total: 5200 },
  { name: 'Pokhara', online: 96.5, total: 9100 },
  { name: 'Butwal', online: 99.8, total: 4300 },
];

const COLORS = ['#f04e23', '#2c3e50', '#27ae60', '#f1c40f', '#e74c3c'];

// --- Components ---

const StatCard = ({ title, value, change, icon: Icon, color }) => (
  <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 hover:shadow-md transition-all">
    <div className="flex justify-between items-start">
      <div>
        <p className="text-slate-500 text-sm font-medium">{title}</p>
        <h3 className="text-2xl font-bold text-slate-800 mt-1">{value}</h3>
        <div className={`flex items-center gap-1 mt-2 text-xs font-bold ${change.startsWith('+') ? 'text-emerald-500' : 'text-red-500'}`}>
          <TrendingUp className="w-3 h-3" />
          {change} vs last 24h
        </div>
      </div>
      <div className={`${color} p-3 rounded-xl`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
    </div>
  </div>
);

const RealTimeCallMonitor = () => (
  <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 h-full">
    <div className="flex justify-between items-center mb-6">
      <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
        <Activity className="w-5 h-5 text-orange-500" />
        Live Voice Traffic
      </h3>
      <div className="flex gap-2">
        <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          <div className="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></div>
          Live
        </span>
      </div>
    </div>
    <div className="h-64">
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={CALL_METRICS}>
          <defs>
            <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#f04e23" stopOpacity={0.1}/>
              <stop offset="95%" stopColor="#f04e23" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
          <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
          <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
          <Tooltip 
            contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }}
          />
          <Area type="monotone" dataKey="calls" stroke="#f04e23" strokeWidth={3} fillOpacity={1} fill="url(#colorCalls)" />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  </div>
);

const NetworkHealthPanel = () => (
  <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
    <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
      <Globe className="w-5 h-5 text-blue-500" />
      Regional Network Health
    </h3>
    <div className="space-y-4">
      {NETWORK_HEALTH.map((area, i) => (
        <div key={i} className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-semibold text-slate-700">{area.name}</span>
            <span className="font-bold text-slate-900">{area.online}%</span>
          </div>
          <div className="w-full bg-slate-100 h-2 rounded-full overflow-hidden">
            <div 
              className={`h-full rounded-full transition-all duration-1000 ${area.online > 99 ? 'bg-emerald-500' : area.online > 97 ? 'bg-amber-500' : 'bg-red-500'}`}
              style={{ width: `${area.online}%` }}
            ></div>
          </div>
          <div className="flex justify-between text-[10px] text-slate-400 font-medium">
            <span>{area.total.toLocaleString()} Active Devices</span>
            <span>{Math.round(area.total * (100-area.online)/100)} Issues</span>
          </div>
        </div>
      ))}
    </div>
  </div>
);

const LiveEventFeed = () => (
  <div className="bg-slate-900 rounded-2xl p-6 shadow-xl border border-slate-800 text-slate-300">
    <div className="flex justify-between items-center mb-6">
      <h3 className="text-lg font-bold text-white flex items-center gap-2">
        <Cpu className="w-5 h-5 text-emerald-400" />
        System Event Stream
      </h3>
      <div className="bg-emerald-500/10 text-emerald-400 text-[10px] font-black px-2 py-1 rounded-md uppercase border border-emerald-500/20">
        Connected
      </div>
    </div>
    <div className="space-y-3 font-mono text-[11px] h-[400px] overflow-y-auto custom-scrollbar">
      {[
        { time: '16:20:05', type: 'VOICE', msg: 'Incoming call from 9841234567 [Session: dh_82a1]' },
        { time: '16:20:08', type: 'LLM', msg: 'Recognized: "My internet is slow"' },
        { time: '16:20:10', type: 'TOOL', msg: 'check_network_status(customer_id="..." ) -> ONLINE' },
        { time: '16:20:12', type: 'LLM', msg: 'Response generated: "I see your router is online..."' },
        { time: '16:21:00', type: 'NOC', msg: 'Minor spike in latency detected in Bhaktapur region' },
        { time: '16:21:45', type: 'TICKET', msg: 'Auto-created ticket #49221: High packet loss' },
      ].map((ev, i) => (
        <div key={i} className="flex gap-3 border-l border-slate-700 pl-3 py-1 hover:bg-slate-800/50 transition-colors">
          <span className="text-slate-500 shrink-0">{ev.time}</span>
          <span className={`font-black shrink-0 ${ev.type === 'VOICE' ? 'text-blue-400' : ev.type === 'LLM' ? 'text-purple-400' : ev.type === 'TOOL' ? 'text-orange-400' : 'text-emerald-400'}`}>
            [{ev.type}]
          </span>
          <span className="text-slate-200">{ev.msg}</span>
        </div>
      ))}
    </div>
  </div>
);

export default function SuperAdminDashboard() {
  return (
    <div className="min-h-screen bg-[#f8fafc] flex">
      {/* Sidebar */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col fixed h-full z-20">
        <div className="p-6 border-b border-slate-100">
          <div className="flex items-center gap-3">
            <div className="bg-orange-600 p-2 rounded-xl rotate-3 shadow-lg shadow-orange-200">
              <Shield className="text-white w-6 h-6" />
            </div>
            <h1 className="text-xl font-black tracking-tight text-slate-800">Nexa<span className="text-orange-600">Admin</span></h1>
          </div>
        </div>
        
        <nav className="flex-1 p-4 space-y-1">
          {[
            { label: 'Overview', icon: LayoutDashboard, active: true },
            { label: 'Live Monitor', icon: Activity },
            { label: 'Customer Map', icon: Globe },
            { label: 'Ticketing', icon: Ticket },
            { label: 'Network NOC', icon: Wifi },
            { label: 'Billing/Rev', icon: BarChart3 },
            { label: 'AI Settings', icon: Cpu },
          ].map((item, i) => (
            <button key={i} className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${item.active ? 'bg-orange-50 text-orange-600 shadow-sm shadow-orange-100' : 'text-slate-500 hover:bg-slate-50'}`}>
              <item.icon className="w-5 h-5" />
              {item.label}
            </button>
          ))}
        </nav>

        <div className="p-4 border-t border-slate-100">
          <div className="bg-slate-50 rounded-2xl p-4 border border-slate-100">
            <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest mb-2">System Health</p>
            <div className="flex items-center gap-2 mb-3">
              <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div className="h-full w-[94%] bg-emerald-500"></div>
              </div>
              <span className="text-[10px] font-bold text-emerald-600">94%</span>
            </div>
            <p className="text-[10px] text-slate-500 leading-tight">All clusters healthy. Ollama running at 12 tokens/sec.</p>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <main className="flex-1 ml-64 p-8">
        <header className="flex justify-between items-center mb-10">
          <div>
            <h2 className="text-2xl font-black text-slate-800">Operations Dashboard</h2>
            <p className="text-slate-500 text-sm font-medium">Real-time intelligence for DishHome ISP infrastructure.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative hidden lg:block">
              <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input type="text" placeholder="Search customer, IP, or ticket..." className="bg-white border border-slate-200 pl-11 pr-4 py-2.5 rounded-xl text-sm w-80 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none shadow-sm" />
            </div>
            <button className="bg-white border border-slate-200 p-2.5 rounded-xl shadow-sm hover:bg-slate-50 transition-colors relative">
              <Bell className="w-5 h-5 text-slate-600" />
              <span className="absolute top-0 right-0 w-3 h-3 bg-red-500 border-2 border-white rounded-full"></span>
            </button>
            <div className="flex items-center gap-3 pl-4 border-l border-slate-200">
              <div className="text-right">
                <p className="text-sm font-bold text-slate-800">Rajan Chand</p>
                <p className="text-[10px] font-black text-orange-600 uppercase">Super Admin</p>
              </div>
              <div className="w-10 h-10 rounded-xl bg-orange-600 flex items-center justify-center text-white font-bold shadow-lg shadow-orange-200 rotate-2 hover:rotate-0 transition-transform cursor-pointer">
                RC
              </div>
            </div>
          </div>
        </header>

        {/* Stats Grid */}
        <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-10">
          <StatCard title="Active Voice Calls" value="12" change="+30%" icon={Phone} color="bg-orange-500 shadow-orange-200" />
          <StatCard title="Total Subscribers" value="48.2k" change="+1.2%" icon={Users} color="bg-blue-500 shadow-blue-200" />
          <StatCard title="Open Tickets" value="342" change="-12%" icon={Ticket} color="bg-indigo-500 shadow-indigo-200" />
          <StatCard title="Critical Outages" value="2" change="+100%" icon={AlertTriangle} color="bg-red-500 shadow-red-200" />
        </section>

        {/* Middle Row */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8 mb-10">
          <div className="lg:col-span-2">
            <RealTimeCallMonitor />
          </div>
          <div>
            <NetworkHealthPanel />
          </div>
        </section>

        {/* Bottom Row */}
        <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-1">
            <LiveEventFeed />
          </div>
          <div className="lg:col-span-2">
            <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 h-full">
              <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-indigo-500" />
                Revenue & SLA Compliance
              </h3>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">SLA Compliance Rate</p>
                  <div className="flex items-end gap-3">
                    <span className="text-4xl font-black text-slate-800">92.4%</span>
                    <span className="text-emerald-500 text-xs font-bold pb-1">↑ 2.1%</span>
                  </div>
                  <div className="mt-4 flex gap-1">
                    {[65, 80, 45, 90, 70, 85, 92].map((v, i) => (
                      <div key={i} className="flex-1 bg-indigo-200 rounded-full h-12 relative overflow-hidden">
                        <div className="absolute bottom-0 left-0 right-0 bg-indigo-600 rounded-full transition-all duration-1000" style={{ height: `${v}%` }}></div>
                      </div>
                    ))}
                  </div>
                </div>
                <div className="p-6 bg-slate-50 rounded-2xl border border-slate-100">
                  <p className="text-xs font-bold text-slate-400 uppercase tracking-widest mb-2">Monthly Revenue (NPR)</p>
                  <div className="flex items-end gap-3">
                    <span className="text-4xl font-black text-slate-800">12.5M</span>
                    <span className="text-emerald-500 text-xs font-bold pb-1">↑ 8.4%</span>
                  </div>
                  <p className="text-xs text-slate-500 mt-4 leading-relaxed">
                    Average revenue per user (ARPU) is up 4% this month due to 100Mbps plan upgrades.
                  </p>
                  <button className="text-xs font-bold text-indigo-600 mt-4 underline">View Detailed Report</button>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
    </div>
  );
}
