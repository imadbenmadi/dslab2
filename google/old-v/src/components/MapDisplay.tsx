import React from 'react';
import { motion } from 'motion/react';
import { FogNode, Vehicle } from '../types';
import { PARAMS } from '../constants';
import { Server, Car } from 'lucide-react';

interface MapDisplayProps {
  vehicles: Vehicle[];
  fogNodes: FogNode[];
}

export const MapDisplay: React.FC<MapDisplayProps> = ({ vehicles, fogNodes }) => {
  const scale = 0.5; // Scale map for UI

  return (
    <div 
      id="simulation-map"
      className="relative bg-slate-900 border border-slate-700 rounded-xl overflow-hidden h-[400px] w-full"
      style={{ backgroundImage: 'radial-gradient(circle, #1e293b 1px, transparent 1px)', backgroundSize: '20px 20px' }}
    >
      {/* Fog Nodes */}
      {fogNodes.map((node) => (
        <div
          key={node.id}
          className="absolute flex flex-col items-center justify-center transform -translate-x-1/2 -translate-y-1/2"
          style={{ left: node.pos.x * scale, top: node.pos.y * scale }}
        >
          {/* Coverage Circle */}
          <div 
            className="absolute rounded-full border-2 border-dashed border-blue-500/30 bg-blue-500/5"
            style={{ 
              width: node.radius * scale * 2, 
              height: node.radius * scale * 2,
            }}
          />
          <div className="z-10 bg-blue-600 p-1.5 rounded-lg shadow-lg shadow-blue-900/50">
            <Server className="w-4 h-4 text-white" />
          </div>
          <span className="text-[10px] text-slate-400 mt-1 font-mono uppercase bg-slate-900 px-1 rounded">{node.name}</span>
          <div className="mt-1 w-8 h-1 bg-slate-800 rounded-full overflow-hidden border border-slate-700">
             <div 
               className="h-full bg-blue-400 transition-all duration-300" 
               style={{ width: `${node.currentLoad * 100}%` }} 
             />
          </div>
        </div>
      ))}

      {/* Vehicles */}
      {vehicles.map((vehicle) => (
        <motion.div
          key={vehicle.id}
          id={`vehicle-${vehicle.id}`}
          className="absolute z-20 flex flex-col items-center transform -translate-x-1/2 -translate-y-1/2"
          animate={{ left: vehicle.pos.x * scale, top: vehicle.pos.y * scale, rotate: (vehicle.heading * 180) / Math.PI }}
          transition={{ duration: 0.1, ease: "linear" }}
        >
          <div className="bg-emerald-500 p-1 rounded shadow-lg shadow-emerald-900/50">
            <Car className="w-3 h-3 text-white" />
          </div>
        </motion.div>
      ))}

      <div className="absolute bottom-2 right-2 text-[10px] text-slate-500 font-mono">
        {PARAMS.MAP_SIZE}m x {PARAMS.MAP_SIZE}m Area
      </div>
    </div>
  );
};
