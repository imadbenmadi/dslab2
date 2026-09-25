import express from 'express';
import { createServer as createViteServer } from 'vite';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;
  
  app.use(express.json());

  // In-memory simulation state
  const simState = {
    started: false,
    phase: 'idle', // idle -> nsga2 -> bc -> online -> done
    progress: 0,
    nsga2_front: [],
    bc_loss: [],
    online_metrics: [],
    startTime: 0
  };

  let max_nsga2 = [];
  let max_bc = [];
  let max_online = [];

  try {
    max_nsga2 = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'dashboard_pareto.json'), 'utf-8'));
    max_bc = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'dashboard_bc_loss.json'), 'utf-8'));
    max_online = JSON.parse(fs.readFileSync(path.resolve(__dirname, 'dashboard_dqn_metrics.json'), 'utf-8'));
  } catch (e) {
    console.error('Failed to load JSON artifacts', e);
  }

  app.get('/api/status', (req, res) => {
    if (!simState.started) {
      return res.json(simState);
    }
    
    const now = Date.now();
    const elapsed = (now - simState.startTime) / 1000; // in seconds

    // Simulation takes approx 30 seconds total
    if (elapsed < 5) {
      simState.phase = 'nsga2';
      simState.progress = Math.min(100, Math.floor((elapsed / 5) * 100));
      const items = Math.floor((elapsed / 5) * max_nsga2.length);
      simState.nsga2_front = max_nsga2.slice(0, items);
    } else if (elapsed < 15) {
      simState.phase = 'bc';
      const phaseElapsed = elapsed - 5;
      simState.progress = Math.min(100, Math.floor((phaseElapsed / 10) * 100));
      const items = Math.floor((phaseElapsed / 10) * max_bc.length);
      simState.bc_loss = max_bc.slice(0, items);
      // keep full nsga2
      simState.nsga2_front = max_nsga2;
    } else if (elapsed < 30) {
      simState.phase = 'online';
      const phaseElapsed = elapsed - 15;
      simState.progress = Math.min(100, Math.floor((phaseElapsed / 15) * 100));
      const items = Math.floor((phaseElapsed / 15) * max_online.length);
      simState.online_metrics = max_online.slice(0, items);
      // keep full previous
      simState.nsga2_front = max_nsga2;
      simState.bc_loss = max_bc;
    } else {
      simState.phase = 'done';
      simState.progress = 100;
      simState.nsga2_front = max_nsga2;
      simState.bc_loss = max_bc;
      simState.online_metrics = max_online;
    }

    res.setHeader('Cache-Control', 'no-cache');
    res.json(simState);
  });

  app.post('/api/start', (req, res) => {
    simState.started = true;
    simState.phase = 'starting';
    simState.progress = 0;
    simState.nsga2_front = [];
    simState.bc_loss = [];
    simState.online_metrics = [];
    simState.startTime = Date.now();
    
    // NOTE: In a real environment, this is where we'd spawn:
    // spawn('python3', ['backend_thesis/pcnme_thesis_system.py'])
    
    res.json({ success: true });
  });

  if (process.env.NODE_ENV !== "production") {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: "spa",
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(__dirname, 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      if (!req.url.startsWith('/api')) {
        res.sendFile(path.join(distPath, 'index.html'));
      }
    });
  }

  app.listen(PORT, "0.0.0.0", () => {
    console.log(`Backend API listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
