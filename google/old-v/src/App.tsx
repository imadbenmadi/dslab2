import React, { useState, useEffect } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area
} from 'recharts';
import { 
  Activity, Zap, Clock, ShieldAlert, Car, Server, Database, Globe, 
  ChevronRight, RotateCcw, AlertTriangle, Cpu
} from 'lucide-react';
import { io, Socket } from 'socket.io-client';

import { Destination, TaskClass } from './types';
import { PARAMS } from './constants';
import { MapDisplay } from './components/MapDisplay';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export default function App() {
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [fogNodes, setFogNodes] = useState<any[]>([]);
  const [logs, setLogs] = useState<any[]>([]);
  const [metricsHistory, setMetricsHistory] = useState<any[]>([]);
  const [stats, setStats] = useState({
    totalTasks: 0,
    successfulTasks: 0,
    totalLatency: 0,
    totalEnergy: 0,
  });
  const [epsilon, setEpsilon] = useState(0.3);

  useEffect(() => {
    const s = io();

    s.on('sim_state', (state) => {
      setVehicles(state.vehicles);
      setFogNodes(state.fogNodes);
      setStats(state.stats);
      setEpsilon(state.epsilon);

      setMetricsHistory(prev => [
        ...prev.slice(-19),
        {
          time: Date.now(),
          latency: state.stats.totalLatency / Math.max(1, state.stats.totalTasks),
          feasibility: (state.stats.successfulTasks / Math.max(1, state.stats.totalTasks)) * 100
        }
      ]);
    });

    s.on('task_processed', (log) => {
      setLogs(prev => [log, ...prev.slice(0, 49)]);
    });

    return () => { s.disconnect(); };
  }, []);

  const feasibilityRate = stats.totalTasks > 0 
    ? (stats.successfulTasks / stats.totalTasks * 100).toFixed(1) 
    : "0.0";

  const avgLatency = stats.totalTasks > 0
    ? (stats.totalLatency / stats.totalTasks).toFixed(1)
    : "0.0";

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200 font-sans p-4 md:p-8">
      {/* Header */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row md:items-center justify-between gap-4 mb-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight text-white flex items-center gap-3">
            <Zap className="text-blue-400 w-8 h-8" />
            PCNME Framework
          </h1>
          <p className="text-slate-400 mt-1">Predictive Cloud-Native Mobile Edge Simulator</p>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-xs font-mono">
            <Cpu className="w-3 h-3 text-blue-400" />
            <span className="text-slate-400">Agent ε:</span>
            <span className="text-white">{epsilon.toFixed(3)}</span>
          </div>
          <button 
            onClick={() => window.location.reload()}
            className="p-2 rounded-lg bg-slate-800 text-slate-400 border border-slate-700 hover:text-white transition-colors"
          >
            <RotateCcw className="w-5 h-5" />
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        {/* Left Column: Visualizer & Stats */}
        <div className="lg:col-span-8 space-y-6">
          
          {/* Map Section */}
          <section className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-2xl">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Globe className="w-5 h-5 text-blue-400" />
                Network Topology Visualizer
              </h2>
              <div className="flex gap-4 text-xs font-mono">
                <span className="flex items-center gap-1.5"><Car className="w-3 h-3 text-emerald-500" /> Vehicle</span>
                <span className="flex items-center gap-1.5"><Server className="w-3 h-3 text-blue-500" /> Fog Node</span>
              </div>
            </div>
            <MapDisplay vehicles={vehicles} fogNodes={fogNodes} />
            
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-6">
               {fogNodes.map(node => (
                 <div key={node.id} className="bg-slate-950/50 border border-slate-800 rounded-xl p-3">
                    <p className="text-xs text-slate-500 uppercase tracking-wider font-bold mb-1">{node.name}</p>
                    <div className="flex items-end justify-between">
                      <span className="text-xl font-mono text-white">{(node.currentLoad * 100).toFixed(0)}%</span>
                      <span className="text-[10px] text-slate-500 lowercase">load</span>
                    </div>
                    <div className="mt-2 w-full h-1 bg-slate-800 rounded-full overflow-hidden">
                      <div 
                        className={cn("h-full transition-all duration-500", node.currentLoad > 0.8 ? "bg-red-500" : "bg-blue-500")}
                        style={{ width: `${node.currentLoad * 100}%` }}
                      />
                    </div>
                 </div>
               ))}
            </div>
          </section>

          {/* Performance Charts */}
          <section className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-medium text-slate-400 flex items-center gap-2 mb-4">
                <Clock className="w-4 h-4" /> Avg Latency (ms) / Task
              </h3>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={metricsHistory}>
                    <defs>
                      <linearGradient id="colorLat" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#60a5fa" stopOpacity={0.3}/>
                        <stop offset="95%" stopColor="#60a5fa" stopOpacity={0}/>
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis stroke="#475569" fontSize={10} axisLine={false} tickLine={false} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
                      itemStyle={{ color: '#60a5fa' }}
                    />
                    <Area type="monotone" dataKey="latency" stroke="#60a5fa" fillOpacity={1} fill="url(#colorLat)" />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </div>

            <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 shadow-xl">
              <h3 className="text-sm font-medium text-slate-400 flex items-center gap-2 mb-4">
                <ShieldAlert className="w-4 h-4" /> Feasibility Rate (%)
              </h3>
              <div className="h-[200px]">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={metricsHistory}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" vertical={false} />
                    <XAxis dataKey="time" hide />
                    <YAxis stroke="#475569" fontSize={10} axisLine={false} tickLine={false} domain={[0, 100]} />
                    <Tooltip 
                      contentStyle={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '8px', fontSize: '12px' }}
                    />
                    <Line type="step" dataKey="feasibility" stroke="#10b981" strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          </section>
        </div>

        {/* Right Column: Decisions & Real-time Metrics */}
        <div className="lg:col-span-4 space-y-6">
          
          {/* Real-time KPI Card */}
          <div className="bg-blue-600 rounded-2xl p-6 text-white shadow-xl shadow-blue-900/20">
            <h3 className="text-blue-100 text-xs font-bold uppercase tracking-wider mb-4 flex items-center gap-2">
              <Activity className="w-4 h-4" /> Live Operational Stats
            </h3>
            <div className="grid grid-cols-2 gap-6">
              <div>
                <p className="text-blue-200 text-[10px] font-medium leading-none">Feasibility Rate</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-3xl font-bold">{feasibilityRate}%</span>
                </div>
              </div>
              <div>
                <p className="text-blue-200 text-[10px] font-medium leading-none">Total Tasks</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-3xl font-bold">{stats.totalTasks}</span>
                </div>
              </div>
              <div>
                <p className="text-blue-200 text-[10px] font-medium leading-none">Avg Latency</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-3xl font-bold">{(stats.totalLatency / Math.max(1, stats.totalTasks)).toFixed(1)}</span>
                  <span className="text-xs font-medium">ms</span>
                </div>
              </div>
              <div>
                <p className="text-blue-200 text-[10px] font-medium leading-none">Energy (kJ)</p>
                <div className="flex items-baseline gap-1 mt-1">
                  <span className="text-3xl font-bold">{(stats.totalEnergy).toFixed(2)}</span>
                </div>
              </div>
            </div>
          </div>

          {/* Decision Pipeline Log */}
          <section className="bg-slate-900 border border-slate-800 rounded-2xl flex flex-col min-h-[515px] overflow-hidden">
            <div className="p-6 border-b border-slate-800 bg-slate-900/50 sticky top-0 z-10">
               <h3 className="text-sm font-semibold flex items-center gap-2">
                 <Database className="w-4 h-4 text-emerald-400" />
                 Decision Pipeline Trace
               </h3>
               <p className="text-[10px] text-slate-500 mt-1 uppercase font-mono">Live Offloading Log (Last 50)</p>
            </div>
            
            <div className="flex-1 overflow-y-auto max-h-[500px] scrollbar-hide p-4 space-y-3">
              {logs.length === 0 && (
                <div className="flex flex-col items-center justify-center h-40 text-slate-600 italic text-sm">
                  Waiting for task arrivals...
                </div>
              )}
              {logs.map((log) => (
                <div 
                  key={log.id} 
                  className={cn(
                    "p-3 rounded-xl border border-slate-800/50 bg-slate-950 transition-all hover:bg-slate-800/20",
                    log.status === 'failure' && "border-red-900/30 bg-red-950/10"
                  )}
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-300">
                      #{log.id}
                    </span>
                    <span className={cn(
                      "text-[10px] font-bold uppercase",
                      log.status === 'success' ? "text-emerald-500" : "text-red-500"
                    )}>
                      {log.status === 'success' ? 'Deadline Met' : 'Deadline Viol.'}
                    </span>
                  </div>
                  
                  <div className="flex items-center gap-3 text-xs">
                    <div className="flex items-center gap-1.5 min-w-0">
                      <div className={cn(
                        "w-2 h-2 rounded-full",
                        log.class === TaskClass.BOULDER ? "bg-amber-500" : "bg-blue-400"
                      )} title={log.class} />
                      <span className="text-slate-200">
                        {log.dest}
                      </span>
                    </div>
                    <ChevronRight className="w-3 h-3 text-slate-700 shrink-0" />
                    <div className="flex items-center gap-2 text-slate-400 font-mono">
                      <span>{log.latency}ms</span>
                    </div>
                  </div>
                  
                  <div className="mt-2 text-[10px] text-slate-500 leading-relaxed italic line-clamp-1">
                    {log.reason}
                  </div>
                </div>
              ))}
            </div>
          </section>

        </div>
      </main>

      {/* Footer Info */}
      <footer className="max-w-7xl mx-auto mt-12 pt-8 border-t border-slate-800 text-center space-y-4">
        <div className="flex flex-wrap justify-center gap-x-8 gap-y-4">
           <div className="flex items-center gap-2 text-xs text-slate-500">
             <div className="w-2 h-2 rounded-full bg-amber-500" />
             <span>Boulders ({'>='} {PARAMS.EC_THRESHOLD}s EC) {'->'} Direct Cloud</span>
           </div>
           <div className="flex items-center gap-2 text-xs text-slate-500">
             <div className="w-2 h-2 rounded-full bg-blue-400" />
             <span>Pebbles (&lt; {PARAMS.EC_THRESHOLD}s EC) {'->'} DQN Placement</span>
           </div>
           <div className="flex items-center gap-2 text-xs text-slate-500">
             <AlertTriangle className="w-3 h-3 text-red-500" />
             <span>Deadline Violations Penalized (Eq 26)</span>
           </div>
        </div>
        <p className="text-[10px] text-slate-600 uppercase tracking-widest font-mono">
          Implementing PCNME Mathematical Foundation v1.0
        </p>
      </footer>
    </div>
  );
}
