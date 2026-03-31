# Frontend UI Routes

- `/` Main real-time dashboard
- `/map` Full Istanbul map view
- `/agents` Agent observability page
- `/logic` Full logic explorer (includes storage health and historical analytics)
- `/thesis` Thesis Architecture Proposal v2 explainer page

The logic explorer now includes:

- Redis/PostgreSQL storage health
- 1h/24h aggregated analytics window view
- Per-vehicle historical analytics query

# Smart City Dashboard - React Frontend

Professional real-time dashboard for the Smart City Vehicular Task Offloading System.

## Features

✅ **Real-Time Metrics** - Live updates via WebSocket  
✅ **System Control** - Start/stop/reset simulations  
✅ **Responsive Design** - Works on desktop, tablet, mobile (Tailwind CSS)  
✅ **Multiple Baselines** - Compare Baseline1, 2, 3, and Proposed systems  
✅ **Beautiful UI** - Modern dark theme with Recharts visualizations

## Tech Stack

- **React 18** - UI framework
- **Zustand** - State management
- **Tailwind CSS** - Styling
- **Recharts** - Data visualization
- **WebSocket** - Real-time communication
- **Axios** - HTTP requests

## Setup & Installation

### Prerequisites

- Node.js 16+ (https://nodejs.org)
- npm or yarn

### Installation

```bash
cd frontend

# Install dependencies
npm install

# Set environment variables (optional - defaults to localhost)
# Create .env if needed (already created with defaults)
cat .env

# Start development server
npm start
```

The dashboard will open at **http://localhost:3000**

## Building for Production

```bash
npm run build
```

This creates an optimized build in `build/` directory.

## Project Structure

```
frontend/
├── package.json           # Dependencies and scripts
├── tailwind.config.js     # Tailwind CSS configuration
├── postcss.config.js      # PostCSS configuration
├── .env                   # Environment variables
├── public/
│   └── index.html         # HTML entry point
└── src/
    ├── App.jsx            # Main app component
    ├── App.css            # Styling
    ├── index.jsx          # React entry point
    ├── index.css          # Global styles
    ├── components/
    │   └── Dashboard.jsx   # Main dashboard component
    ├── store/
    │   └── systemStore.js # Zustand state management
    └── hooks/
        └── useWebSocket.js # WebSocket connection hook
```

## Usage

### Starting the System

1. **Start Python backend and simulation:**

```bash
cd ..
python app.py proposed  # or baseline1/2/3
```

This starts:

- Flask API server on http://localhost:5000
- WebSocket server on ws://localhost:8765
- SimPy simulation

2. **Start React dashboard:**

```bash
cd frontend
npm start
```

Opens dashboard at http://localhost:3000

3. **Use dashboard to:**
    - Select system type (Baseline 1-3, or Proposed)
    - Start/stop/reset simulations
    - View real-time metrics
    - Monitor device utilization
    - Track network metrics
    - Watch agent performance

### API Endpoints

The dashboard connects to these REST endpoints:

- `GET /api/health` - Server health
- `GET /api/status` - Simulation status
- `GET /api/metrics/current` - Latest metrics
- `GET /api/metrics/history?limit=50` - Historical data
- `POST /api/simulation/start` - Start simulation
- `POST /api/simulation/stop` - Stop simulation
- `POST /api/simulation/reset` - Reset simulation
- `GET /api/config` - System configuration
- `GET /api/baselines` - Baseline comparison data
- `GET /api/system-info` - System information
- `GET /api/export` - Export metrics as CSV

### WebSocket Messages

Real-time metrics sent via WebSocket:

```json
{
    "type": "metrics",
    "data": {
        "timestamp": "2024-03-30T15:30:45.123Z",
        "simulationTime": 150.5,
        "successRate": 74.2,
        "avgLatency": 156,
        "taskCount": 385200,
        "throughput": 9850,
        "devices": {
            "fog1": 0.82,
            "fog2": 0.45,
            "fog3": 0.6,
            "fog4": 0.5,
            "cloud": 0.18
        },
        "network": {
            "bandwidthUsed": 45.3,
            "congestionPoints": 3
        },
        "agents": {
            "agent1Latency": 8.3,
            "agent2Latency": 2.1
        },
        "handoff": {
            "count": 723,
            "taskMigrations": 1875
        }
    }
}
```

## Customization

### Change Colors

Edit `tailwind.config.js`:

```javascript
theme: {
  extend: {
    colors: {
      primary: '#3b82f6',  // Blue
      success: '#10b981',  // Green
    }
  }
}
```

### Change Fonts

Edit `index.css`:

```css
body {
    font-family: "Your Font", sans-serif;
}
```

### Change Refresh Rate

Edit `store/systemStore.js`:

```javascript
// Adjust WebSocket interval (milliseconds)
setInterval(() => ws.send("ping"), 30000);
```

## Environment Variables

Create `.env` in `frontend/` folder:

```env
REACT_APP_API_URL=http://localhost:5000/api
REACT_APP_WS_URL=ws://localhost:8765
```

For production (e.g., deployed to cloud):

```env
REACT_APP_API_URL=https://api.example.com
REACT_APP_WS_URL=wss://api.example.com
```

## Troubleshooting

### "Cannot find module 'react'"

```bash
npm install
npm start
```

### WebSocket connection fails

- Ensure Python backend is running: `python app.py proposed`
- Check WebSocket URL in `.env` matches backend
- Verify firewall allows port 8765

### Dashboard shows no data

- Check browser console for errors (F12)
- Verify API endpoints with `curl http://localhost:5000/api/health`
- Check Flask/WebSocket server is running

### Slow performance

- Close other browser tabs
- Reduce `maxResults` in store if too much data
- Check system resources: `top` or Task Manager

## Deployment

### Deploy to Vercel (free)

```bash
npm i -g vercel
vercel
```

Follow prompts to connect to GitHub repository.

### Deploy to Netlify (free)

```bash
npm i -g netlify-cli
npm run build
netlify deploy --prod --dir=build
```

### Docker

Create `Dockerfile`:

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
EXPOSE 3000
CMD ["npm", "start"]
```

Build and run:

```bash
docker build -t smart-city-dashboard .
docker run -p 3000:3000 smart-city-dashboard
```

## Performance Optimization

- **Code Splitting**: Using React.lazy for large components
- **Memoization**: Using React.memo to prevent unnecessary re-renders
- **Virtualization**: Can add react-window for large lists
- **Bundle Size**: ~150KB gzipped (optimized with production build)

## License

This project is part of Smart City Task Offloading System research.

## Support

For issues or questions:

1. Check console logs (F12)
2. Review API server output
3. Verify all services running
4. Contact project maintainers
