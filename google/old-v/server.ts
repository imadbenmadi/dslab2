import express from 'express';
import { createServer } from 'http';
import { Server } from 'socket.io';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import * as tf from '@tensorflow/tfjs-node';
import { nanoid } from 'nanoid';

import { PARAMS } from './src/constants';
import { Destination, TaskClass, HandoffMode } from './src/types';
import {
  getExecutionCost,
  getExecutionTime,
  getTransmissionTime,
  getEnergyCost,
  getMobilityMetrics,
  determineHandoffMode
} from './src/lib/pcnme-engine';

// --- DQN AGENT IMPLEMENTATION (Section 8.3) ---
class DQNAgent {
  model: tf.LayersModel;
  targetModel: tf.LayersModel;
  memory: any[] = [];
  gamma = 0.95;
  epsilon = 0.3;
  epsilonMin = 0.05;
  epsilonDecay = 0.9995;
  batchSize = 64;

  constructor(stateDim: number, actionDim: number) {
    this.model = this.createModel(stateDim, actionDim);
    this.targetModel = this.createModel(stateDim, actionDim);
    this.updateTargetModel();
  }

  createModel(stateDim: number, actionDim: number) {
    const model = tf.sequential();
    model.add(tf.layers.dense({ units: 256, activation: 'relu', inputShape: [stateDim] }));
    model.add(tf.layers.dense({ units: 128, activation: 'relu' }));
    model.add(tf.layers.dense({ units: actionDim, activation: 'linear' }));
    model.compile({ optimizer: tf.train.adam(0.001), loss: 'meanSquaredError' });
    return model;
  }

  updateTargetModel() {
    this.targetModel.setWeights(this.model.getWeights());
  }

  act(state: number[]) {
    if (Math.random() <= this.epsilon) {
      return Math.floor(Math.random() * 5); // 4 fogs + 1 cloud
    }
    const qValues = this.model.predict(tf.tensor2d([state])) as tf.Tensor;
    return qValues.argMax(1).dataSync()[0];
  }

  remember(state: number[], action: number, reward: number, nextState: number[], done: boolean) {
    this.memory.push({ state, action, reward, nextState, done });
    if (this.memory.length > 10000) this.memory.shift();
  }

  async train() {
    if (this.memory.length < this.batchSize) return;

    const batch = [];
    for (let i = 0; i < this.batchSize; i++) {
      batch.push(this.memory[Math.floor(Math.random() * this.memory.length)]);
    }

    const states = tf.tensor2d(batch.map(m => m.state));
    const nextStates = tf.tensor2d(batch.map(m => m.nextState));
    
    const currentQs = this.model.predict(states) as tf.Tensor;
    const nextQs = this.targetModel.predict(nextStates) as tf.Tensor;
    
    const updatedQs = currentQs.arraySync() as number[][];
    const nextQsData = nextQs.arraySync() as number[][];

    batch.forEach((m, i) => {
      const target = m.reward + (m.done ? 0 : this.gamma * Math.max(...nextQsData[i]));
      updatedQs[i][m.action] = target;
    });

    await this.model.fit(states, tf.tensor2d(updatedQs), { epochs: 1, verbose: 0 });

    if (this.epsilon > this.epsilonMin) {
      this.epsilon *= this.epsilonDecay;
    }
  }
}

// --- SERVER SETUP ---
async function startServer() {
  const app = express();
  const httpServer = createServer(app);
  const io = new Server(httpServer);
  const PORT = 3000;

  const agent = new DQNAgent(11, 5); // State: 4 load, 4 queue, 1 EC, 1 speed, 1 T_exit
  
  // Simulation State
  let fogNodes = [
    { id: 'f1', name: 'Fog Node 1', pos: { x: 250, y: 250 }, radius: 250, mips: 2000, currentLoad: 0.2, queueDepth: 0 },
    { id: 'f2', name: 'Fog Node 2', pos: { x: 750, y: 250 }, radius: 250, mips: 2000, currentLoad: 0.1, queueDepth: 0 },
    { id: 'f3', name: 'Fog Node 3', pos: { x: 250, y: 750 }, radius: 250, mips: 2000, currentLoad: 0.3, queueDepth: 0 },
    { id: 'f4', name: 'Fog Node 4', pos: { x: 750, y: 750 }, radius: 250, mips: 2000, currentLoad: 0.15, queueDepth: 0 },
  ];

  let vehicles = Array.from({ length: PARAMS.N_VEHICLES }, (_, i) => ({
    id: `v${i}`,
    pos: { x: Math.random() * 1000, y: Math.random() * 1000 },
    speed: 10 + Math.random() * 5,
    heading: Math.random() * 2 * Math.PI,
  }));

  let stats = {
    totalTasks: 0,
    successfulTasks: 0,
    totalLatency: 0,
    totalEnergy: 0,
  };

  // Main Simulation Core Loop (Server Side)
  setInterval(async () => {
    // 1. Mobility
    vehicles = vehicles.map(v => {
      let nx = v.pos.x + v.speed * Math.cos(v.heading) * 0.1;
      let ny = v.pos.y + v.speed * Math.sin(v.heading) * 0.1;
      let nh = v.heading;
      if (nx < 0 || nx > 1000) nh = Math.PI - nh;
      if (ny < 0 || ny > 1000) nh = -nh;
      return { ...v, pos: { x: Math.max(0, Math.min(1000, nx)), y: Math.max(0, Math.min(1000, ny)) }, heading: nh };
    });

    // 2. Task Arrival & Placement
    if (Math.random() < 0.2) {
      const v = vehicles[Math.floor(Math.random() * vehicles.length)];
      const step = {
        id: nanoid(5),
        mi: 500 + Math.random() * 2000,
        dataIn: 100 + Math.random() * 500,
        deadline: 250,
        isCritical: Math.random() > 0.8
      };

      const taskClass = getExecutionCost(step.mi) >= PARAMS.EC_THRESHOLD ? TaskClass.BOULDER : TaskClass.PEBBLE;
      
      let action = 4; // Default: Cloud
      let latency = 0;
      let energy = 0;
      let result = "Routing to Cloud";

      if (taskClass === TaskClass.PEBBLE) {
        // Construct State Vector (Section 8.2)
        const state = [
          ...fogNodes.map(f => f.currentLoad),
          ...fogNodes.map(f => f.queueDepth / PARAMS.Q_MAX),
          getExecutionCost(step.mi) / PARAMS.EC_THRESHOLD,
          v.speed / PARAMS.SPEED_MAX_MS,
          0.5 // Simplified T_exit mock for state
        ];

        // Inference
        action = agent.act(state);
        
        if (action < 4) {
          const f = fogNodes[action];
          const dist = Math.sqrt((f.pos.x - v.pos.x)**2 + (f.pos.y - v.pos.y)**2);
          
          if (dist <= f.radius) {
            const execTime = getExecutionTime(step.mi, f.mips, f.currentLoad);
            const mob = getMobilityMetrics(v as any, f as any);
            const handoff = determineHandoffMode(execTime, mob.tExit);
            
            latency = getTransmissionTime(step.dataIn, PARAMS.BANDWIDTH_MBPS, PARAMS.G5_LATENCY_MS) + execTime;
            energy = getEnergyCost(step.dataIn, step.mi, Destination.FOG_1);
            result = `Placed on ${f.name} (${handoff})`;
            
            // Collect Reward & Train
            const reward = latency <= step.deadline ? 1 : -1;
            agent.remember(state, action, reward, state, false);
            await agent.train();
          } else {
            action = 4; // Force cloud if out of range despite agent choice (safety check)
          }
        }
      }

      if (action === 4) {
        latency = getTransmissionTime(step.dataIn, PARAMS.FOG_CLOUD_BW, PARAMS.WAN_LATENCY_MS) + getExecutionTime(step.mi, PARAMS.CLOUD_MIPS);
        energy = getEnergyCost(step.dataIn, step.mi, Destination.CLOUD);
      }

      stats.totalTasks++;
      stats.totalLatency += latency;
      stats.totalEnergy += energy;
      if (latency <= step.deadline) stats.successfulTasks++;

      io.emit('task_processed', { id: step.id, class: taskClass, action, latency, energy, result, status: latency <= step.deadline ? 'success' : 'failure' });
    }

    // 3. Update Fog States
    fogNodes = fogNodes.map(f => ({
      ...f,
      currentLoad: Math.max(0.1, Math.min(0.95, f.currentLoad + (Math.random() - 0.5) * 0.05))
    }));

    // Emit State
    io.emit('sim_state', { vehicles, fogNodes, stats, epsilon: agent.epsilon });
  }, 100);

  // Vite middleware for development
  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  httpServer.listen(PORT, "0.0.0.0", () => {
    console.log(`PCNME Full-Stack Server running on http://localhost:${PORT}`);
  });
}

startServer();
