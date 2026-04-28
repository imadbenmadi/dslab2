import express from 'express';
import { createServer as createViteServer } from 'vite';
import { spawn } from 'child_process';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

async function startServer() {
  const app = express();
  const PORT = 3000;
  
  app.use(express.json());

  const stateFile = path.resolve(__dirname, 'training_state.json');
  
  if (!fs.existsSync(stateFile)) {
    fs.writeFileSync(stateFile, JSON.stringify({ phase: "idle", progress: 0, nsga2_front: [], bc_loss: [], online_metrics: [] }));
  }

  app.get('/api/status', (req, res) => {
    try {
      const data = fs.readFileSync(stateFile, 'utf-8');
      res.setHeader('Cache-Control', 'no-cache');
      res.json(JSON.parse(data));
    } catch (e) {
      res.json({ phase: 'error', message: 'Could not read state' });
    }
  });

  app.post('/api/start', (req, res) => {
    fs.writeFileSync(stateFile, JSON.stringify({ phase: "starting", progress: 0, nsga2_front: [], bc_loss: [], online_metrics: [] }));
    
    console.log("Spawning PCNME Python trainer...");
    const pyProcess = spawn('python3', ['pcnme_train.py'], { cwd: __dirname });
    
    pyProcess.stdout.on('data', (data) => console.log(`[Python]: ${data.toString().trim()}`));
    pyProcess.stderr.on('data', (data) => console.error(`[Python Err]: ${data.toString().trim()}`));
    
    pyProcess.on('close', (code) => {
      console.log(`Python training exited with code ${code}`);
    });
    
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
    console.log(`PCNME Operations Center API listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
