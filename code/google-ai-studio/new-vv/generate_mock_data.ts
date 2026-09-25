import fs from 'fs';

// 1. Pareto Front Data
const pareto = [];
for (let i = 0; i < 50; i++) {
  const L = 20 + Math.random() * 80;
  const E = 0.5 + (100 / (L + 10)) + (Math.random() * 0.1 - 0.05);
  pareto.push({ latency: L, energy: E, gene: [Math.floor(Math.random() * 5)] });
}
pareto.sort((a, b) => a.latency - b.latency);
fs.writeFileSync('dashboard_pareto.json', JSON.stringify(pareto, null, 2));

// 2. Behavioral Cloning Data
const bc_loss = [];
let loss = 2.5;
for (let i = 0; i < 150; i++) {
  loss = loss * 0.94 + (Math.random() * 0.05);
  bc_loss.push({ epoch: i, loss });
}
fs.writeFileSync('dashboard_bc_loss.json', JSON.stringify(bc_loss, null, 2));

// 3. Online DQN Training Data
const metrics = [];
let reward = -1.2;
let lat = 60.0;
let eng = 0.15;
for (let i = 0; i < 300; i += 2) {
  lat = lat * 0.95 + (20 + Math.random() * 5) * 0.05;
  eng = eng * 0.95 + (0.05 + Math.random() * 0.01) * 0.05;
  reward = reward * 0.98 + (-(0.5 * (lat / 50.0) + 0.3 * (eng / 0.1))) * 0.02;
  metrics.push({
    step: i,
    latency: lat,
    energy: eng,
    reward: reward,
    violations: Math.max(0, Math.floor((300 - i)/20 + Math.random() * 2 - 1))
  });
}
fs.writeFileSync('dashboard_dqn_metrics.json', JSON.stringify(metrics, null, 2));
console.log('Mock JSON artifacts generated successfully.');
