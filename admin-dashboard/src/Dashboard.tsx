import React, { useState, useEffect } from 'react';
import { 
  Users, Phone, Ticket, Wifi, AlertTriangle, 
  TrendingUp, Clock, Shield, Globe, Cpu,
  BarChart3, Activity, Zap, Search, Bell, LayoutDashboard,
  UserCheck, Heart, ShieldCheck, History, Settings,
  Sparkles, DollarSign, ListTree, HardDrive
} from 'lucide-react';
import { 
  LineChart, Line, AreaChart, Area, 
  XAxis, YAxis, CartesianGrid, Tooltip, 
  ResponsiveContainer, PieChart, Pie, Cell,
  BarChart, Bar
} from 'recharts';

// --- Types ---
interface StatCardProps {
  title: string;
  value: string | number;
  change: string;
  icon: React.ElementType;
  color: string;
}

interface EventData {
  time: string;
  type: string;
  msg: string;
  channel?: string;
}

interface NetworkArea {
  name: string;
  online: number;
  total: number;
}

// --- Components ---

const StatCard = ({ title, value, change, icon: Icon, color }: StatCardProps) => (
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
      <div className={`${color} p-3 rounded-xl shadow-lg`}>
        <Icon className="w-6 h-6 text-white" />
      </div>
    </div>
  </div>
);

// --- Section Components ---

const CommandCenter = ({ stats, callHistory, networkHealth, events }: any) => (
  <div className="space-y-8">
    {/* Stats Grid */}
    <section className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <StatCard title="Active Voice Calls" value={stats.activeCalls} change="+30%" icon={Phone} color="bg-orange-500 shadow-orange-200" />
      <StatCard title="Total Subscribers" value={stats.totalSubscribers} change="+1.2%" icon={Users} color="bg-blue-500 shadow-blue-200" />
      <StatCard title="Open Tickets" value={stats.openTickets} change="-12%" icon={Ticket} color="bg-indigo-500 shadow-indigo-200" />
      <StatCard title="Critical Outages" value={stats.criticalOutages} change="+100%" icon={AlertTriangle} color="bg-red-500 shadow-red-200" />
    </section>

    {/* Middle Row */}
    <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div className="lg:col-span-2">
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100 h-full">
          <div className="flex justify-between items-center mb-6">
            <h3 className="text-lg font-bold text-slate-800 flex items-center gap-2">
              <Activity className="w-5 h-5 text-orange-500" />
              Live Voice Traffic
            </h3>
            <span className="flex items-center gap-1 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></span>
              Live
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={callHistory}>
                <defs>
                  <linearGradient id="colorCalls" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#f04e23" stopOpacity={0.1}/>
                    <stop offset="95%" stopColor="#f04e23" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                <XAxis dataKey="time" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
                <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
                <Tooltip contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} />
                <Area type="monotone" dataKey="calls" stroke="#f04e23" strokeWidth={3} fillOpacity={1} fill="url(#colorCalls)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
      <div>
        <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
          <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
            <Globe className="w-5 h-5 text-blue-500" />
            Regional Network Health
          </h3>
          <div className="space-y-4">
            {networkHealth.map((area: any, i: number) => (
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
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>

    {/* Bottom Row */}
    <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
      <div className="lg:col-span-1">
        <div className="bg-slate-900 rounded-2xl p-6 shadow-xl border border-slate-800 text-slate-300">
          <h3 className="text-lg font-bold text-white mb-6 flex items-center gap-2">
            <Cpu className="w-5 h-5 text-emerald-400" />
            System Event Stream
          </h3>
          <div className="space-y-3 font-mono text-[11px] h-[400px] overflow-y-auto custom-scrollbar">
            {events.map((ev: any, i: number) => (
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
                <span className="text-4xl font-black text-slate-800">{stats.slaCompliance}%</span>
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
                <span className="text-4xl font-black text-slate-800">{stats.revenue}</span>
                <span className="text-emerald-500 text-xs font-bold pb-1">↑ 8.4%</span>
              </div>
              <p className="text-xs text-slate-500 mt-4 leading-relaxed">
                Average revenue per user (ARPU) is up 4% this month due to 100Mbps plan upgrades.
              </p>
            </div>
          </div>
        </div>
      </div>
    </section>
  </div>
);

const AIPerformance = () => (
  <div className="space-y-8">
    <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <StatCard title="Automation Rate" value="78.4%" change="+5.2%" icon={Sparkles} color="bg-purple-500 shadow-purple-200" />
      <StatCard title="Avg. LLM Latency" value="1.2s" change="-0.3s" icon={Zap} color="bg-amber-500 shadow-amber-200" />
      <StatCard title="Tool Success Rate" value="99.1%" change="+0.5%" icon={UserCheck} color="bg-emerald-500 shadow-emerald-200" />
    </section>
    
    <div className="bg-white rounded-2xl p-8 border border-slate-100 shadow-sm">
      <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
        <Cpu className="w-5 h-5 text-purple-500" />
        Khushi's Tool Usage Distribution
      </h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={[
            { name: 'Identity Ver.', count: 1240 },
            { name: 'Net Status', count: 980 },
            { name: 'Billing Check', count: 850 },
            { name: 'Ticket Create', count: 420 },
            { name: 'Router Reboot', count: 210 },
            { name: 'Pkg Upgrade', count: 150 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
            <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
            <YAxis axisLine={false} tickLine={false} tick={{fill: '#94a3b8', fontSize: 12}} />
            <Tooltip cursor={{fill: '#f8fafc'}} contentStyle={{ borderRadius: '12px', border: 'none', boxShadow: '0 10px 15px -3px rgb(0 0 0 / 0.1)' }} />
            <Bar dataKey="count" fill="#8b5cf6" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  </div>
);

const UserManagement = () => (
  <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
    <div className="p-6 border-b border-slate-100 flex justify-between items-center">
      <h3 className="text-lg font-bold text-slate-800">Internal Staff & RBAC</h3>
      <button className="bg-orange-600 text-white px-4 py-2 rounded-xl text-sm font-bold shadow-lg shadow-orange-200 flex items-center gap-2">
        <UserCheck className="w-4 h-4" /> Provision User
      </button>
    </div>
    <table className="w-full text-left">
      <thead className="bg-slate-50 text-slate-500 text-[10px] font-black uppercase tracking-widest">
        <tr>
          <th className="px-6 py-4">User</th>
          <th className="px-6 py-4">Role</th>
          <th className="px-6 py-4">Status</th>
          <th className="px-6 py-4">MFA</th>
          <th className="px-6 py-4 text-right">Action</th>
        </tr>
      </thead>
      <tbody className="divide-y divide-slate-100">
        {[
          { name: 'Rajan Chand', role: 'Super Admin', status: 'Active', mfa: 'Enabled' },
          { name: 'Anita Shrestha', role: 'Ops Manager', status: 'Active', mfa: 'Enabled' },
          { name: 'Bikram Thapa', role: 'Support Agent', status: 'Away', mfa: 'Disabled' },
          { name: 'Sagar Gurung', role: 'Technician', status: 'Field', mfa: 'Enabled' },
        ].map((user, i) => (
          <tr key={i} className="hover:bg-slate-50/50 transition-colors">
            <td className="px-6 py-4 font-bold text-slate-700">{user.name}</td>
            <td className="px-6 py-4"><span className="bg-slate-100 text-slate-600 px-2 py-1 rounded text-[10px] font-black uppercase">{user.role}</span></td>
            <td className="px-6 py-4">
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${user.status === 'Active' ? 'bg-emerald-500' : 'bg-amber-500'}`}></div>
                <span className="text-sm text-slate-600">{user.status}</span>
              </div>
            </td>
            <td className="px-6 py-4 text-sm text-slate-500">{user.mfa}</td>
            <td className="px-6 py-4 text-right"><button className="text-slate-400 hover:text-orange-600 font-black text-xs uppercase">Edit</button></td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);

const NetworkHealth = ({ networkHealth }: any) => (
  <div className="space-y-8">
    <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
      <StatCard title="Global Online Rate" value="98.2%" change="+0.4%" icon={Globe} color="bg-blue-600 shadow-blue-200" />
      <StatCard title="Active Outages" value="2" change="-1" icon={AlertTriangle} color="bg-red-500 shadow-red-200" />
      <StatCard title="Avg. Signal (Rx)" value="-18dBm" change="Optimal" icon={Wifi} color="bg-emerald-500 shadow-emerald-200" />
      <StatCard title="NOC Alerts" value="14" change="+3" icon={Bell} color="bg-amber-500 shadow-amber-200" />
    </section>

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <h3 className="text-lg font-bold text-slate-800 mb-6">Area Signal Distribution</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={networkHealth}>
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Area type="monotone" dataKey="online" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.1} />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="bg-white rounded-2xl p-6 shadow-sm border border-slate-100">
        <h3 className="text-lg font-bold text-slate-800 mb-6">Regional Device Density</h3>
        <div className="space-y-4">
          {networkHealth.map((area: any, i: number) => (
            <div key={i} className="flex items-center gap-4">
              <span className="w-24 text-sm font-semibold text-slate-600">{area.name}</span>
              <div className="flex-1 bg-slate-100 h-4 rounded-full overflow-hidden">
                <div className="bg-blue-500 h-full" style={{ width: `${(area.total / 15000) * 100}%` }}></div>
              </div>
              <span className="text-xs font-bold text-slate-800">{area.total.toLocaleString()}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const RevenueBilling = () => (
  <div className="space-y-8">
    <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <StatCard title="Monthly Recurring Rev (MRR)" value="रू 4.2M" change="+12%" icon={DollarSign} color="bg-emerald-600 shadow-emerald-200" />
      <StatCard title="Avg. Revenue Per User" value="रू 1,250" change="+4.2%" icon={TrendingUp} color="bg-blue-600 shadow-blue-200" />
      <StatCard title="Churn Rate" value="1.4%" change="-0.2%" icon={AlertTriangle} color="bg-red-500 shadow-red-200" />
    </section>

    <div className="bg-white rounded-2xl p-8 border border-slate-100 shadow-sm">
      <h3 className="text-lg font-bold text-slate-800 mb-6">Collection Aging (Days)</h3>
      <div className="h-80">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={[
            { range: '0-30', amount: 3200000 },
            { range: '31-60', amount: 850000 },
            { range: '61-90', amount: 120000 },
            { range: '90+', amount: 45000 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="range" />
            <YAxis />
            <Tooltip />
            <Bar dataKey="amount" fill="#10b981" radius={[6, 6, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  </div>
);

const TicketAnalytics = () => (
  <div className="space-y-8">
    <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
      <StatCard title="Unresolved" value="42" change="-8" icon={Ticket} color="bg-indigo-600 shadow-indigo-200" />
      <StatCard title="SLA Breach" value="3" change="+1" icon={Clock} color="bg-red-500 shadow-red-200" />
      <StatCard title="Mean Time To Resolve" value="4.2h" change="-1.1h" icon={Zap} color="bg-amber-500 shadow-amber-200" />
      <StatCard title="First Call Resolution" value="84%" change="+2.1%" icon={UserCheck} color="bg-emerald-500 shadow-emerald-200" />
    </section>

    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div className="bg-white rounded-2xl p-8 border border-slate-100">
        <h3 className="text-lg font-bold text-slate-800 mb-6">Tickets by Category</h3>
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={[
                  { name: 'Connectivity', value: 45 },
                  { name: 'Billing', value: 25 },
                  { name: 'WiFi', value: 20 },
                  { name: 'Speed', value: 10 },
                ]}
                innerRadius={60}
                outerRadius={80}
                paddingAngle={5}
                dataKey="value"
              >
                {['#6366f1', '#10b981', '#f59e0b', '#ef4444'].map((color, index) => (
                  <Cell key={`cell-${index}`} fill={color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>
      <div className="bg-white rounded-2xl p-8 border border-slate-100 overflow-hidden">
        <h3 className="text-lg font-bold text-slate-800 mb-6">Recent Escalations</h3>
        <div className="space-y-4">
          {[
            { id: '#49221', customer: 'Aayush M.', priority: 'CRITICAL', time: '12m ago' },
            { id: '#49218', customer: 'Sita R.', priority: 'HIGH', time: '45m ago' },
            { id: '#49215', customer: 'Kiran K.', priority: 'MEDIUM', time: '1h ago' },
          ].map((t, i) => (
            <div key={i} className="flex justify-between items-center p-3 bg-slate-50 rounded-xl">
              <div>
                <p className="text-sm font-bold text-slate-800">{t.id} - {t.customer}</p>
                <p className="text-[10px] font-black text-slate-400 uppercase">{t.time}</p>
              </div>
              <span className={`px-2 py-1 rounded text-[10px] font-black ${t.priority === 'CRITICAL' ? 'bg-red-100 text-red-600' : 'bg-orange-100 text-orange-600'}`}>
                {t.priority}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  </div>
);

const AgentPerformance = () => (
  <div className="space-y-8">
    <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
      <div className="p-6 border-b border-slate-100">
        <h3 className="text-lg font-bold text-slate-800">Agent Efficiency Metrics</h3>
      </div>
      <table className="w-full text-left">
        <thead className="bg-slate-50 text-slate-500 text-[10px] font-black uppercase tracking-widest">
          <tr>
            <th className="px-6 py-4">Agent</th>
            <th className="px-6 py-4">Calls</th>
            <th className="px-6 py-4">Avg. Handle Time</th>
            <th className="px-6 py-4">CSAT Score</th>
            <th className="px-6 py-4">Resolution Rate</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {[
            { name: 'Anita Shrestha', calls: 142, aht: '4.2m', csat: '4.8/5', res: '94%' },
            { name: 'Bikram Thapa', calls: 98, aht: '5.1m', csat: '4.5/5', res: '88%' },
            { name: 'Sunita P.', calls: 115, aht: '4.8m', csat: '4.9/5', res: '92%' },
          ].map((a, i) => (
            <tr key={i} className="hover:bg-slate-50/50 transition-colors">
              <td className="px-6 py-4 font-bold text-slate-700">{a.name}</td>
              <td className="px-6 py-4 text-sm text-slate-600">{a.calls}</td>
              <td className="px-6 py-4 text-sm text-slate-600">{a.aht}</td>
              <td className="px-6 py-4">
                <span className="text-emerald-600 font-bold">{a.csat}</span>
              </td>
              <td className="px-6 py-4">
                <div className="w-24 bg-slate-100 h-2 rounded-full overflow-hidden">
                  <div className="bg-emerald-500 h-full" style={{ width: a.res }}></div>
                </div>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  </div>
);

const CustomerInsights = () => (
  <div className="space-y-8">
    <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
      <StatCard title="Loyalty Tier: Diamond" value="1,240" change="+45" icon={Sparkles} color="bg-indigo-600 shadow-indigo-200" />
      <StatCard title="Churn Risk (High)" value="142" change="-12" icon={AlertTriangle} color="bg-red-500 shadow-red-200" />
      <StatCard title="New Signups" value="840" change="+120" icon={Users} color="bg-emerald-600 shadow-emerald-200" />
    </section>

    <div className="bg-white rounded-2xl p-8 border border-slate-100 shadow-sm">
      <h3 className="text-lg font-bold text-slate-800 mb-6">Customer Sentiment Trends</h3>
      <div className="h-64">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={[
            { day: 'Mon', positive: 65, negative: 12 },
            { day: 'Tue', positive: 70, negative: 10 },
            { day: 'Wed', positive: 45, negative: 35 },
            { day: 'Thu', positive: 80, negative: 8 },
            { day: 'Fri', positive: 85, negative: 5 },
          ]}>
            <CartesianGrid strokeDasharray="3 3" vertical={false} />
            <XAxis dataKey="day" />
            <YAxis />
            <Tooltip />
            <Line type="monotone" dataKey="positive" stroke="#10b981" strokeWidth={3} />
            <Line type="monotone" dataKey="negative" stroke="#ef4444" strokeWidth={3} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  </div>
);

const AuditSecurity = () => (
  <div className="bg-white rounded-2xl border border-slate-100 shadow-sm overflow-hidden">
    <div className="p-6 border-b border-slate-100">
      <h3 className="text-lg font-bold text-slate-800">System Audit Trail</h3>
    </div>
    <div className="space-y-0 divide-y divide-slate-100 font-mono text-xs">
      {[
        { user: 'Rajan Chand', action: 'LOGIN_SUCCESS', ip: '192.168.1.45', time: '2m ago' },
        { user: 'System', action: 'DB_BACKUP_COMPLETED', ip: 'internal', time: '1h ago' },
        { user: 'Anita S.', action: 'CONFIG_CHANGE', detail: 'SLA threshold updated', time: '2h ago' },
        { user: 'External', action: 'AUTH_FAILURE', ip: '45.12.23.1', time: '4h ago' },
      ].map((log, i) => (
        <div key={i} className="px-6 py-4 flex justify-between hover:bg-slate-50 transition-colors">
          <div className="flex gap-4">
            <span className="text-slate-400 w-24">{log.time}</span>
            <span className="font-bold text-slate-700">{log.user}</span>
            <span className={`px-2 rounded ${log.action.includes('FAILURE') ? 'bg-red-100 text-red-600' : 'bg-emerald-100 text-emerald-600'}`}>
              {log.action}
            </span>
          </div>
          <span className="text-slate-400">{log.ip || log.detail}</span>
        </div>
      ))}
    </div>
  </div>
);

const SystemConfig = () => (
  <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
    <div className="bg-white rounded-2xl p-8 border border-slate-100 shadow-sm">
      <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
        <Sparkles className="w-5 h-5 text-purple-500" />
        AI Engine Configuration
      </h3>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <p className="font-bold text-slate-700">Khushi Agent Identity</p>
            <p className="text-xs text-slate-500">Tone, language and persona settings</p>
          </div>
          <button className="text-orange-600 font-black text-[10px] uppercase underline">Configure</button>
        </div>
        <div className="flex justify-between items-center">
          <div>
            <p className="font-bold text-slate-700">Automation Threshold</p>
            <p className="text-xs text-slate-500">Minimum confidence to take action (85%)</p>
          </div>
          <input type="range" className="accent-orange-600" />
        </div>
        <div className="flex justify-between items-center">
          <div>
            <p className="font-bold text-slate-700">Voice Synthesis (TTS)</p>
            <p className="text-xs text-slate-500">Currently: Edge-TTS (ne-NP-SagarNeural)</p>
          </div>
          <button className="text-slate-400 font-black text-[10px] uppercase underline">Change</button>
        </div>
      </div>
    </div>

    <div className="bg-white rounded-2xl p-8 border border-slate-100 shadow-sm">
      <h3 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
        <Settings className="w-5 h-5 text-slate-500" />
        SLA & Operational Thresholds
      </h3>
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <p className="font-bold text-slate-700 text-sm">Critical Ticket SLA</p>
          <div className="flex items-center gap-2">
            <input type="number" defaultValue={2} className="w-12 border rounded px-2 py-1 text-sm" />
            <span className="text-xs text-slate-500">Hours</span>
          </div>
        </div>
        <div className="flex justify-between items-center">
          <p className="font-bold text-slate-700 text-sm">Escalation Timeout</p>
          <div className="flex items-center gap-2">
            <input type="number" defaultValue={30} className="w-12 border rounded px-2 py-1 text-sm" />
            <span className="text-xs text-slate-500">Mins</span>
          </div>
        </div>
        <button className="w-full bg-slate-900 text-white py-3 rounded-xl font-bold text-sm mt-4">Save Configuration</button>
      </div>
    </div>
  </div>
);

// --- Main Dashboard Component ---

export default function SuperAdminDashboard() {
  const [activeTab, setActiveTab] = useState('Command Center');
  const [stats, setStats] = useState({
    activeCalls: 12,
    totalSubscribers: '48.2k',
    openTickets: 342,
    criticalOutages: 2,
    slaCompliance: 92.4,
    revenue: '12.5M'
  });

  const [networkHealth, setNetworkHealth] = useState<NetworkArea[]>([
    { name: 'Kathmandu', online: 98.5, total: 12500 },
    { name: 'Lalitpur', online: 99.2, total: 8400 },
    { name: 'Bhaktapur', online: 97.8, total: 5200 },
    { name: 'Pokhara', online: 96.5, total: 9100 },
    { name: 'Butwal', online: 99.8, total: 4300 },
  ]);

  const [events, setEvents] = useState<EventData[]>([
    { time: '16:20:05', type: 'VOICE', msg: 'Incoming call from 9841234567 [Session: dh_82a1]' },
    { time: '16:20:08', type: 'LLM', msg: 'Recognized: "My internet is slow"' },
    { time: '16:20:10', type: 'TOOL', msg: 'check_network_status(customer_id="..." ) -> ONLINE' },
    { time: '16:20:12', type: 'LLM', msg: 'Response generated: "I see your router is online..."' },
    { time: '16:21:00', type: 'NOC', msg: 'Minor spike in latency detected in Bhaktapur region' },
    { time: '16:21:45', type: 'TICKET', msg: 'Auto-created ticket #49221: High packet loss' },
  ]);

  const [callHistory, setCallHistory] = useState([
    { time: '10:00', calls: 45 },
    { time: '11:00', calls: 52 },
    { time: '12:00', calls: 85 },
    { time: '13:00', calls: 65 },
    { time: '14:00', calls: 48 },
    { time: '15:00', calls: 70 },
  ]);

  const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`${API_URL}/api/admin/dashboard/stats`);
        if (response.ok) {
          const data = await response.json();
          setStats(prev => ({
            ...prev,
            activeCalls: data.active_calls ?? prev.activeCalls,
            totalSubscribers: data.total_customers ? `${(data.total_customers / 1000).toFixed(1)}k` : prev.totalSubscribers,
            openTickets: data.active_tickets ?? prev.openTickets,
            criticalOutages: data.critical_outages ?? prev.criticalOutages,
          }));
        }
      } catch (err) {
        console.warn("Failed to fetch dashboard stats", err);
      }
    };

    fetchData();
    const interval = setInterval(fetchData, 30000);

    const userId = "admin";
    const wsProto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const wsUrl = `${wsProto}://${API_URL.replace(/^https?:\/\//, '')}/api/agent/ws/${userId}`;
    
    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl);
      ws.onmessage = (e) => {
        try {
          const ev = JSON.parse(e.data);
          const newEvent = {
            time: new Date().toLocaleTimeString(),
            type: ev.channel?.split(':')[0]?.toUpperCase() || 'INFO',
            msg: typeof ev.data === 'string' ? ev.data : JSON.stringify(ev.data).slice(0, 100)
          };
          setEvents(prev => [newEvent, ...prev].slice(0, 50));
          
          if (ev.channel === 'voice:call') {
            setStats(prev => ({ ...prev, activeCalls: prev.activeCalls + 1 }));
          }
        } catch (_) {}
      };
    } catch (err) {
      console.warn("WS connection failed", err);
    }

    return () => {
      clearInterval(interval);
      if (ws) ws.close();
    };
  }, [API_URL]);

  const sidebarItems = [
    { label: 'Command Center', icon: LayoutDashboard },
    { label: 'Network Health', icon: Wifi },
    { label: 'Revenue & Billing', icon: DollarSign },
    { label: 'Ticket Analytics', icon: Ticket },
    { label: 'Agent Performance', icon: Users },
    { label: 'AI Performance', icon: Cpu },
    { label: 'Customer Insights', icon: Heart },
    { label: 'User Management', icon: ShieldCheck },
    { label: 'Audit & Security', icon: History },
    { label: 'System Config', icon: Settings },
  ];

  const renderContent = () => {
    switch (activeTab) {
      case 'Command Center':
        return <CommandCenter stats={stats} callHistory={callHistory} networkHealth={networkHealth} events={events} />;
      case 'Network Health':
        return <NetworkHealth networkHealth={networkHealth} />;
      case 'Revenue & Billing':
        return <RevenueBilling />;
      case 'Ticket Analytics':
        return <TicketAnalytics />;
      case 'Agent Performance':
        return <AgentPerformance />;
      case 'AI Performance':
        return <AIPerformance />;
      case 'Customer Insights':
        return <CustomerInsights />;
      case 'User Management':
        return <UserManagement />;
      case 'Audit & Security':
        return <AuditSecurity />;
      case 'System Config':
        return <SystemConfig />;
      default:
        return (
          <div className="flex flex-col items-center justify-center h-[60vh] text-slate-400">
            <HardDrive className="w-16 h-16 mb-4 opacity-20" />
            <h3 className="text-xl font-bold">Module Under Construction</h3>
            <p className="text-sm">The {activeTab} panel is being synchronized with the enterprise API.</p>
          </div>
        );
    }
  };

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
        
        <nav className="flex-1 p-4 space-y-1 overflow-y-auto custom-scrollbar">
          <p className="text-[10px] font-black text-slate-400 uppercase tracking-widest px-4 mb-2 mt-4">Enterprise Panels</p>
          {sidebarItems.map((item, i) => (
            <button 
              key={i} 
              onClick={() => setActiveTab(item.label)}
              className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-semibold transition-all ${activeTab === item.label ? 'bg-orange-50 text-orange-600 shadow-sm shadow-orange-100' : 'text-slate-500 hover:bg-slate-50'}`}
            >
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
            <h2 className="text-2xl font-black text-slate-800">{activeTab}</h2>
            <p className="text-slate-500 text-sm font-medium">Enterprise Intelligence for DishHome ISP infrastructure.</p>
          </div>
          <div className="flex items-center gap-4">
            <div className="relative hidden lg:block">
              <Search className="w-4 h-4 text-slate-400 absolute left-4 top-1/2 -translate-y-1/2" />
              <input type="text" placeholder="Search customer, IP, or ticket..." className="bg-white border border-slate-200 pl-11 pr-4 py-2.5 rounded-xl text-sm w-80 focus:ring-2 focus:ring-orange-500 focus:border-transparent outline-none shadow-sm" />
            </div>
            <button className="bg-white border border-slate-200 p-2.5 rounded-xl shadow-sm hover:bg-slate-50 transition-colors relative">
              <Bell className="w-5 h-5 text-slate-600" />
              <span className="absolute top-1 right-1 w-3 h-3 bg-red-500 border-2 border-white rounded-full"></span>
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

        {renderContent()}
      </main>
    </div>
  );
}



