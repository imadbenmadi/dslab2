export enum TaskClass {
  BOULDER = "BOULDER",
  PEBBLE = "PEBBLE",
}

export enum Destination {
  LOCAL = "LOCAL",
  FOG_1 = "FOG_1",
  FOG_2 = "FOG_2",
  FOG_3 = "FOG_3",
  FOG_4 = "FOG_4",
  CLOUD = "CLOUD",
}

export enum HandoffMode {
  DIRECT = "DIRECT",
  PROACTIVE = "PROACTIVE",
}

export interface TaskStep {
  id: string;
  mi: number; // Million Instructions
  dataIn: number; // KB
  dataOut: number; // KB
  deadline: number; // ms
  isCritical: boolean;
}

export interface Task {
  id: string;
  vehicleId: string;
  steps: TaskStep[];
  startTime: number;
  totalDeadline: number;
}

export interface FogNode {
  id: string;
  name: string;
  pos: { x: number; y: number };
  radius: number;
  mips: number;
  currentLoad: number; // 0-1
  queueDepth: number;
}

export interface Vehicle {
  id: string;
  pos: { x: number; y: number };
  speed: number; // m/s
  heading: number; // radians
  activeTasks: Task[];
}

export interface SimulationState {
  time: number;
  vehicles: Vehicle[];
  fogNodes: FogNode[];
  completedTasks: any[];
  metrics: {
    latency: number[];
    energy: number[];
    feasibility: number[];
  };
}
