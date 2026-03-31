"""
Real-time WebSocket Server for React Dashboard
Streams live metrics from SimPy simulation to connected clients
"""

import asyncio
import json
import threading
from dataclasses import dataclass, asdict
from typing import Set, Optional, Dict, Any
import websockets
from datetime import datetime
from queue import Queue, Empty


@dataclass
class SystemMetrics:
    """Real-time system metrics"""
    timestamp: str
    simulation_time: float
    success_rate: float
    avg_latency: float
    task_count: int
    throughput: float
    
    # Device loads
    fog1_load: float
    fog2_load: float
    fog3_load: float
    fog4_load: float
    cloud_load: float
    
    # Network
    bandwidth_used: float
    congestion_points: int
    
    # Agent performance
    agent1_latency: float
    agent2_latency: float
    
    # Handoff
    handoff_count: int
    task_migrations: int

    # Optional live-map payload
    map_snapshot: Optional[Dict[str, Any]] = None
    agent_snapshot: Optional[Dict[str, Any]] = None
    
    def to_dict(self):
        """Convert to JSON-serializable dict"""
        return {
            'timestamp': self.timestamp,
            'simulationTime': self.simulation_time,
            'successRate': self.success_rate,
            'avgLatency': self.avg_latency,
            'taskCount': self.task_count,
            'throughput': self.throughput,
            'devices': {
                'fog1': self.fog1_load,
                'fog2': self.fog2_load,
                'fog3': self.fog3_load,
                'fog4': self.fog4_load,
                'cloud': self.cloud_load,
            },
            'network': {
                'bandwidthUsed': self.bandwidth_used,
                'congestionPoints': self.congestion_points,
            },
            'agents': {
                'agent1Latency': self.agent1_latency,
                'agent2Latency': self.agent2_latency,
            },
            'agentDetails': self.agent_snapshot or {},
            'handoff': {
                'count': self.handoff_count,
                'taskMigrations': self.task_migrations,
            },
            'map': self.map_snapshot or {}
        }


class WebSocketServer:
    """Manages WebSocket connections and broadcasts metrics"""
    
    def __init__(self, host='127.0.0.1', port=8765):
        self.host = host
        self.port = port
        self.clients: Set = set()
        self.metrics_queue: Queue = Queue()
        self.loop = None
        self.server = None
        self.running = False
        self.latest_state: Dict[str, Any] = {}  # Store latest map state for API queries
        
    async def register_client(self, websocket):
        """Register new WebSocket client"""
        self.clients.add(websocket)
        print(f"[WS] Client connected. Total: {len(self.clients)}")
        
        try:
            # Keep connection alive
            async for message in websocket:
                if message == "ping":
                    await websocket.send("pong")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            await self.unregister_client(websocket)
    
    async def unregister_client(self, websocket):
        """Unregister disconnected client"""
        self.clients.discard(websocket)
        print(f"[WS] Client disconnected. Total: {len(self.clients)}")
    
    async def broadcast_metrics(self, metrics: SystemMetrics):
        """Send metrics to all connected clients"""
        if not self.clients:
            return
        
        # Store latest state for API queries
        metrics_dict = metrics.to_dict()
        self.latest_state = {
            'vehicles': metrics_dict.get('map', {}).get('vehicles', []),
            'fogNodes': metrics_dict.get('map', {}).get('fogNodes', []),
            'cloud': metrics_dict.get('map', {}).get('cloud', {}),
            'connections': metrics_dict.get('map', {}).get('connections', []),
            'handoffs': metrics_dict.get('map', {}).get('handoffs', []),
            'coverageZones': metrics_dict.get('map', {}).get('coverageZones', []),
            'timestamp': metrics_dict.get('timestamp'),
        }
            
        msg = json.dumps({
            'type': 'metrics',
            'data': metrics_dict
        })
        
        # Send to all clients, remove disconnected ones
        disconnected = set()
        for client in self.clients:
            try:
                await client.send(msg)
            except websockets.exceptions.ConnectionClosed:
                disconnected.add(client)
        
        # Clean up disconnected clients
        for client in disconnected:
            self.clients.discard(client)
    
    async def metrics_processor(self):
        """Process metrics from queue and broadcast"""
        while self.running:
            try:
                metrics = self.metrics_queue.get(timeout=0.1)
                await self.broadcast_metrics(metrics)
            except Empty:
                await asyncio.sleep(0.1)
            except Exception as e:
                print(f"[WS] Error processing metrics: {e}")
    
    async def start_server(self):
        """Start WebSocket server"""
        async with websockets.serve(self.register_client, self.host, self.port):
            print(f"[WS] Server running on ws://{self.host}:{self.port}")
            self.running = True
            
            # Start metrics processor
            processor_task = asyncio.create_task(self.metrics_processor())
            
            try:
                await asyncio.Future()  # Run forever
            except KeyboardInterrupt:
                print("[WS] Server shutdown")
            finally:
                self.running = False
                processor_task.cancel()
    
    def put_metrics(self, metrics: SystemMetrics):
        """Add metrics to broadcast queue (thread-safe)"""
        self.metrics_queue.put(metrics)
    
    def run_in_thread(self):
        """Run server in background thread"""
        def run():
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            self.loop.run_until_complete(self.start_server())
        
        thread = threading.Thread(target=run, daemon=True)
        thread.start()
        return thread
    
    def stop(self):
        """Stop server"""
        self.running = False
        if self.loop:
            self.loop.call_soon_threadsafe(self.loop.stop)


# Global instance
_ws_server: Optional[WebSocketServer] = None


def get_ws_server() -> WebSocketServer:
    """Get or create global WebSocket server"""
    global _ws_server
    if _ws_server is None:
        _ws_server = WebSocketServer()
    return _ws_server


def send_metrics(metrics: SystemMetrics):
    """Send metrics to all connected clients"""
    server = get_ws_server()
    server.put_metrics(metrics)


def start_websocket_server():
    """Start WebSocket server in background"""
    server = get_ws_server()
    return server.run_in_thread()


if __name__ == '__main__':
    # Test server
    server = WebSocketServer()
    
    # Send test metrics
    async def test():
        await asyncio.sleep(1)
        for i in range(10):
            metrics = SystemMetrics(
                timestamp=datetime.now().isoformat(),
                simulation_time=float(i),
                success_rate=50.0 + i * 2,
                avg_latency=150.0 - i * 2,
                task_count=i * 1000,
                throughput=9850.0,
                fog1_load=0.8,
                fog2_load=0.45,
                fog3_load=0.6,
                fog4_load=0.5,
                cloud_load=0.2,
                bandwidth_used=45.3,
                congestion_points=3,
                agent1_latency=8.3,
                agent2_latency=2.1,
                handoff_count=int(i * 50),
                task_migrations=int(i * 30)
            )
            await server.broadcast_metrics(metrics)
            await asyncio.sleep(1)
    
    async def main():
        await asyncio.gather(
            server.start_server(),
            test()
        )
    
    asyncio.run(main())
