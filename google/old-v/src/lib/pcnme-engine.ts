import { PARAMS } from "../constants";
import { Destination, FogNode, TaskStep, Vehicle, TaskClass, HandoffMode } from "../types";

/**
 * Section 3.1: Transmission Time
 */
export function getTransmissionTime(dataKb: number, bandwidthMbps: number, fixedLatencyMs: number = 0): number {
  return (8 * dataKb) / bandwidthMbps + fixedLatencyMs;
}

/**
 * Section 3.2 & 3.3: Execution Time
 */
export function getExecutionTime(mi: number, mips: number, load: number = 0): number {
  // Eq 15: T_exec = (mi / (mips * (1 - load))) * 1000
  const effectiveMips = mips * (1 - load);
  if (effectiveMips <= 0) return Infinity;
  return (mi / effectiveMips) * 1000; // ms
}

/**
 * Section 3.5: Energy Model
 */
export function getEnergyCost(dataKb: number, mi: number, destination: Destination): number {
  const txEnergy = PARAMS.TX_POWER_WATTS * ((8 * dataKb) / (PARAMS.BANDWIDTH_MBPS * 1000));
  const compEnergy = PARAMS.COMPUTE_ENERGY_KAPPA * mi;

  if (destination === Destination.CLOUD) {
    return txEnergy + PARAMS.WAN_ENERGY_ALPHA * txEnergy;
  }
  return txEnergy + compEnergy;
}

/**
 * Section 6.1: Execution Cost Metric
 */
export function getExecutionCost(mi: number): number {
  return mi / PARAMS.FOG_MIPS;
}

/**
 * Section 9.1: Proactive Mobility
 */
export function getMobilityMetrics(vehicle: Vehicle, fog: FogNode) {
  const dx = vehicle.pos.x - fog.pos.x;
  const dy = vehicle.pos.y - fog.pos.y;
  const distance = Math.sqrt(dx * dx + dy * dy);

  // Unit outward radial vector from fog center toward vehicle
  const nx = dx / distance;
  const ny = dy / distance;

  // Velocity vector
  const vx = vehicle.speed * Math.cos(vehicle.heading);
  const vy = vehicle.speed * Math.sin(vehicle.heading);

  // Eq 41: Closing speed (radial component directed outward)
  const vClose = vx * nx + vy * ny;

  // Eq 42: Zone Exit Time
  let tExit = Infinity;
  if (vClose > 0) {
    tExit = (fog.radius - distance) / vClose;
  }

  return { distance, vClose, tExit };
}

/**
 * Section 9.2: Handoff Mode Selection
 */
export function determineHandoffMode(execTimeMs: number, tExitS: number): HandoffMode {
  const tExecS = execTimeMs / 1000;
  return tExecS < tExitS ? HandoffMode.DIRECT : HandoffMode.PROACTIVE;
}

/**
 * Pipeline Decision Maker
 */
export class PCNMEFramework {
  static classifyTask(step: TaskStep): TaskClass {
    const ec = getExecutionCost(step.mi);
    return ec >= PARAMS.EC_THRESHOLD ? TaskClass.BOULDER : TaskClass.PEBBLE;
  }

  static getPlacementReward(latency: number, energy: number, deadline: number, isCritical: boolean): number {
    const omegaL = 0.5;
    const omegaE = 0.3;
    const omegaV = 0.2;
    const lambda = isCritical ? 10.0 : 1.0;

    const normLat = Math.min(latency / deadline, 3);
    const normEnergy = Math.min(energy / 0.1, 3);
    const violation = latency > deadline ? 1 : 0;

    return -(omegaL * normLat) - (omegaE * normEnergy) - (omegaV * violation * lambda);
  }
}
