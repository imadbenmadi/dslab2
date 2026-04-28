/**
 * Global PCNME Parameters based on Methodology Section 1
 */

export const PARAMS = {
  // Compute and Network
  FOG_MIPS: 2000,
  CLOUD_MIPS: 8000,
  BANDWIDTH_MBPS: 100,
  FOG_CLOUD_BW: 1000,
  G5_LATENCY_MS: 2,
  WAN_LATENCY_MS: 30,
  WAN_ENERGY_ALPHA: 1.8,
  COMPUTE_ENERGY_KAPPA: 0.001, // J/MI
  TX_POWER_WATTS: 0.5,

  // TOF-Broker
  EC_THRESHOLD: 1.0, // seconds
  Q_MAX: 50,

  // Mobility
  FOG_COVERAGE_RADIUS: 250, // metres
  T_EXIT_MAX_S: 10.0,
  SPEED_MAX_MS: 33.3, // 120 km/h

  // Simulation
  MAP_SIZE: 1000, // 1km x 1km simulation area
  TASK_RATE_HZ: 1, // tasks per second
  N_VEHICLES: 5,
} as const;
