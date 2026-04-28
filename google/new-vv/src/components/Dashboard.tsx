import React, { useEffect, useState } from 'react';
import { 
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend
} from 'recharts';
import { Play, Activity, Cpu, Network, Save, Zap } from 'lucide-react';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

// Utility for neat class merging
function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

type TrainingState = {
  phase: 'idle' | 'starting' | 'nsga2' | 'bc' | 'online' | 'done' | 'error';
  progress: number;
  message?: string;
  nsga2_front: Array<{ latency: number; energy: number; gene: number[] }>;
  bc_loss: Array<{ epoch: number; loss: number }>;
  online_metrics: Array<{ step: number; latency: number; energy: number; violations: number; reward: number }>;
};

export default function Dashboard() {
  const [data, setData] = useState<TrainingState>({
    phase: 'idle',
    progress: 0,
    nsga2_front: [],
    bc_loss: [],
    online_metrics: []
  });

  useEffect(() => {
    let interval: number;

    const pullStatus = async () => {
      try {
        const res = await fetch('/api/status');
        if (res.ok) {
          const json = await res.json();
          setData(prev => ({ ...prev, ...json }));
        }
      } catch (err) {
        console.error("Failed to fetch status", err);
      }
    };

    if (data.phase !== 'idle' && data.phase !== 'done' && data.phase !== 'error') {
      interval = window.setInterval(pullStatus, 500); // pull roughly every 500ms during training
    } else {
      pullStatus();
    }

    return () => {
      if (interval) clearInterval(interval);
    };
  }, [data.phase]);

  const startTraining = async () => {
    setData(prev => ({ ...prev, phase: 'starting', progress: 0 }));
    try {
      await fetch('/api/start', { method: 'POST' });
    } catch (err) {
      console.error(err);
    }
  };

  const getPhaseName = () => {
    switch (data.phase) {
      case 'idle': return 'SYSTEM_IDLE';
      case 'starting': return 'INITIALIZING...';
      case 'nsga2': return 'NSGA-II + MMDE OFFLINE GENERATION';
      case 'bc': return 'BEHAVIORAL CLONING PRETRAINING';
      case 'online': return 'DQN LIVE ADAPTATION';
      case 'done': return 'DEPLOYED';
      default: return 'UNKNOWN';
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0A0A] text-gray-100 font-sans p-6 overflow-hidden flex flex-col">
      {/* Header */}
      <header className="flex items-center justify-between border-b border-gray-800 pb-4 mb-6">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-white flex items-center gap-2">
            <Network className="text-blue-500" />
            PCNME Command Center
          </h1>
          <p className="text-sm font-mono text-gray-500 mt-1">Predictive Cloud-Native Mobile Edge • RL Task Offloading</p>
        </div>
        <div className="flex gap-4 items-center">
          <div className="flex items-center gap-2 font-mono text-xs bg-gray-900 px-3 py-1.5 rounded border border-gray-800">
            <div className={cn("w-2 h-2 rounded-full", data.phase === 'done' ? "bg-green-500" : data.phase === 'idle' ? "bg-gray-500" : "bg-blue-500 animate-pulse")} />
            {getPhaseName()}
          </div>
          <button 
            onClick={startTraining}
            disabled={data.phase !== 'idle' && data.phase !== 'done'}
            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-4 py-2 rounded font-medium transition-colors"
          >
            <Play size={16} />
            Initialize Pipeline
          </button>
        </div>
      </header>

      {/* Main Grid View */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 flex-1 min-h-0">
        
        {/* Left Column: Progress & Metrics */}
        <div className="space-y-6 flex flex-col min-h-0">
          
          <div className="bg-[#111111] p-5 rounded-xl border border-gray-800 shadow-sm flex-shrink-0">
            <h2 className="text-sm font-semibold tracking-wide text-gray-400 mb-4 uppercase">System Status</h2>
            
            <div className="mb-4">
              <div className="flex justify-between font-mono text-xs mb-1">
                <span className="text-blue-400">Pipeline Progress</span>
                <span>{data.progress}%</span>
              </div>
              <div className="h-2 w-full bg-gray-900 rounded-full overflow-hidden">
                <div 
                  className="h-full bg-blue-500 transition-all duration-300"
                  style={{ width: `${data.progress}%` }}
                />
              </div>
            </div>

            <div className="grid grid-cols-2 gap-4">
               <div className="bg-black/50 p-3 rounded border border-gray-800/50">
                  <div className="text-gray-500 text-xs font-mono mb-1 flex items-center gap-1.5"><Save size={12}/>Pareto Fronts</div>
                  <div className="text-xl font-mono text-white">{data.nsga2_front?.length || 0}</div>
               </div>
               <div className="bg-black/50 p-3 rounded border border-gray-800/50">
                  <div className="text-gray-500 text-xs font-mono mb-1 flex items-center gap-1.5"><Activity size={12}/>Live Reward</div>
                  <div className="text-xl font-mono text-green-400">
                    {data.online_metrics?.length > 0 
                      ? data.online_metrics[data.online_metrics.length - 1].reward.toFixed(2)
                      : "0.00"}
                  </div>
               </div>
            </div>
          </div>

          {/* Behavior Cloning Loss Line Chart */}
          <div className="bg-[#111111] p-5 rounded-xl border border-gray-800 shadow-sm flex-1 min-h-[250px] flex flex-col">
             <h2 className="text-sm font-semibold tracking-wide text-gray-400 mb-4 uppercase flex items-center gap-2">
               <Cpu size={16} /> Behavioral Cloning Loss
             </h2>
             <div className="flex-1 w-full relative">
               <ResponsiveContainer width="100%" height="100%">
                 <LineChart data={data.bc_loss || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                   <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                   <XAxis dataKey="epoch" stroke="#555" tick={{fontSize: 10, fill: '#888', fontFamily: 'monospace'}} />
                   <YAxis yAxisId="left" stroke="#555" tick={{fontSize: 10, fill: '#888', fontFamily: 'monospace'}} domain={['auto', 'auto']}/>
                   <Tooltip 
                     contentStyle={{ backgroundColor: '#000', borderColor: '#333', fontFamily: 'monospace' }}
                     itemStyle={{ color: '#fff' }}
                   />
                   <Line yAxisId="left" type="monotone" dataKey="loss" stroke="#3b82f6" dot={false} strokeWidth={2} />
                 </LineChart>
               </ResponsiveContainer>
               {!(data.bc_loss?.length) && (
                 <div className="absolute inset-0 flex items-center justify-center font-mono text-xs text-gray-600">AWAITING BC PRETRAINING...</div>
               )}
             </div>
          </div>
        </div>

        {/* Middle/Right Columns: NSGA & Live Monitor */}
        <div className="lg:col-span-2 space-y-6 flex flex-col min-h-0">
          
          {/* Top: NSGA-II Pareto Front Scatter Chart */}
          <div className="bg-[#111111] p-5 rounded-xl border border-gray-800 shadow-sm flex-1 min-h-[250px] flex flex-col">
            <h2 className="text-sm font-semibold tracking-wide text-gray-400 mb-4 uppercase">Offline NSGA-II Pareto Front (Eq 20 vs 17)</h2>
            <div className="flex-1 w-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: -10 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                  <XAxis type="number" dataKey="latency" name="Latency (ms)" stroke="#555" tick={{fontSize: 10, fill: '#888', fontFamily: 'monospace'}} domain={['auto', 'auto']} label={{ value: 'Latency (ms) ->', position: 'insideBottomRight', offset: -5, fill: '#666', fontSize: 10, fontFamily: 'monospace' }}/>
                  <YAxis type="number" dataKey="energy" name="Energy (J)" stroke="#555" tick={{fontSize: 10, fill: '#888', fontFamily: 'monospace'}} domain={['auto', 'auto']} label={{ value: 'Energy (J)', angle: -90, position: 'insideLeft', fill: '#666', fontSize: 10, fontFamily: 'monospace' }}/>
                  <Tooltip 
                    cursor={{ strokeWidth: 1, strokeDasharray: '3 3', stroke: '#555' }}
                    contentStyle={{ backgroundColor: '#000', borderColor: '#333', fontFamily: 'monospace' }}
                  />
                  <Scatter name="Non-Dominated" data={data.nsga2_front || []} fill="#a855f7" />
                </ScatterChart>
              </ResponsiveContainer>
              {!(data.nsga2_front?.length) && (
                <div className="absolute inset-0 flex items-center justify-center font-mono text-xs text-gray-600">AWAITING NSGA-II SAMPLES...</div>
              )}
            </div>
          </div>

          {/* Bottom: Online Metrics */}
          <div className="bg-[#111111] p-5 rounded-xl border border-gray-800 shadow-sm flex-1 min-h-[250px] flex flex-col">
            <h2 className="text-sm font-semibold tracking-wide text-gray-400 mb-4 uppercase flex items-center gap-2">
              <Zap size={16} className="text-yellow-500"/> Live Agent Handoff / Step Telemetry
            </h2>
            <div className="flex-1 w-full relative">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={data.online_metrics || []} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#222" />
                  <XAxis dataKey="step" stroke="#555" tick={{fontSize: 10, fill: '#888', fontFamily: 'monospace'}} />
                  <YAxis yAxisId="left" stroke="#555" tick={{fontSize: 10, fill: '#888', fontFamily: 'monospace'}} domain={[20, 60]}/>
                  <YAxis yAxisId="right" orientation="right" stroke="#555" tick={{fontSize: 10, fill: '#888', fontFamily: 'monospace'}} domain={[0.0, 0.2]}/>
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#000', borderColor: '#333', fontFamily: 'monospace' }}
                  />
                  <Legend iconType="circle" wrapperStyle={{ fontSize: 12, fontFamily: 'monospace', color: '#888' }}/>
                  <Line yAxisId="left" type="monotone" dataKey="latency" name="Avg Latency" stroke="#f59e0b" dot={false} strokeWidth={2} />
                  <Line yAxisId="right" type="monotone" dataKey="energy" name="Avg Energy" stroke="#10b981" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
              {!(data.online_metrics?.length) && (
                <div className="absolute inset-0 flex items-center justify-center font-mono text-xs text-gray-600">AWAITING ONLINE ENVIRONMENT...</div>
              )}
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
