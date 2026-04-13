"""
Real-Time Visualization Functions
Professional visualizations for system monitoring
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from config import FOG_NODES, FOG_COVERAGE_RADIUS


def create_city_map(vehicles_data: list, tasks_offloaded: dict) -> go.Figure:
    """
    Create interactive Istanbul city map showing:
    - Fog node locations and coverage zones
    - Vehicle positions
    - Task offloading flows
    
    Args:
        vehicles_data: List of vehicle positions {vehicle_id, x, y, speed}
        tasks_offloaded: Dict mapping vehicle_id to offloading destination
    
    Returns:
        Plotly Figure object
    """
    fig = go.Figure()
    
    # Add coverage zones for each fog node
    for fog_id, fog_data in FOG_NODES.items():
        x_center, y_center = fog_data['pos']
        name = fog_data['name']
        
        # Create circle for coverage zone
        theta = np.linspace(0, 2*np.pi, 100)
        x_circle = x_center + FOG_COVERAGE_RADIUS * np.cos(theta)
        y_circle = y_center + FOG_COVERAGE_RADIUS * np.sin(theta)
        
        fig.add_trace(go.Scatter(
            x=x_circle, y=y_circle,
            fill='toself',
            name=f'{fog_id} Coverage ({name})',
            mode='lines',
            line=dict(color=f'rgba(100, 150, 200, 0.3)', width=2),
            fillcolor=f'rgba(100, 150, 200, 0.1)',
            hovertemplate=f'{name} Coverage Zone<br>Radius: {FOG_COVERAGE_RADIUS}m<extra></extra>',
        ))
    
    # Add fog node markers
    fog_ids = list(FOG_NODES.keys())
    fog_names = [FOG_NODES[fid]['name'] for fid in fog_ids]
    fog_x = [FOG_NODES[fid]['pos'][0] for fid in fog_ids]
    fog_y = [FOG_NODES[fid]['pos'][1] for fid in fog_ids]
    
    fig.add_trace(go.Scatter(
        x=fog_x, y=fog_y,
        mode='markers+text',
        name='Fog Nodes',
        marker=dict(size=20, color='darkblue', symbol='square'),
        text=fog_ids,
        textposition='top center',
        hovertemplate='<b>%{text}</b><br>%{customdata}<br>Position: (%{x}, %{y})<extra></extra>',
        customdata=fog_names,
    ))
    
    # Add cloud server location (center of map)
    fig.add_trace(go.Scatter(
        x=[500], y=[500],
        mode='markers+text',
        name='Cloud Server',
        marker=dict(size=25, color='red', symbol='star'),
        text=['CLOUD'],
        textposition='top center',
        hovertemplate='Cloud Server<br>Position: (500, 500)<extra></extra>',
    ))
    
    # Add vehicle positions if data provided
    if vehicles_data:
        vehicle_ids = [v['vehicle_id'] for v in vehicles_data]
        vehicle_x = [v['x'] for v in vehicles_data]
        vehicle_y = [v['y'] for v in vehicles_data]
        vehicle_speeds = [v['speed_kmh'] for v in vehicles_data]
        
        # Color by offloading destination
        colors = []
        offload_text = []
        for vid in vehicle_ids:
            dest = tasks_offloaded.get(vid, 'local')
            offload_text.append(dest)
            if dest == 'local':
                colors.append('green')
            elif dest == 'cloud':
                colors.append('red')
            else:
                colors.append('orange')
        
        fig.add_trace(go.Scatter(
            x=vehicle_x, y=vehicle_y,
            mode='markers',
            name='Vehicles',
            marker=dict(size=10, color=colors, opacity=0.7),
            text=vehicle_ids,
            hovertemplate='<b>Vehicle %{text}</b><br>Speed: %{customdata[0]:.1f} km/h<br>Offload: %{customdata[1]}<extra></extra>',
            customdata=np.column_stack([vehicle_speeds, offload_text]),
        ))
    
    # Layout configuration
    fig.update_layout(
        title='Istanbul Smart City - Real-Time Vehicle Tracking',
        xaxis=dict(
            title='Distance (meters)',
            range=[0, 1000],
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
        ),
        yaxis=dict(
            title='Distance (meters)',
            range=[0, 1000],
            showgrid=True,
            gridwidth=1,
            gridcolor='lightgray',
        ),
        hovermode='closest',
        plot_bgcolor='rgba(240, 240, 250, 0.5)',
        height=700,
        showlegend=True,
        template='plotly_white',
    )
    
    return fig


def create_metrics_dashboard(metrics_history: list) -> go.Figure:
    """
    Create real-time metrics dashboard with multiple traces
    
    Args:
        metrics_history: List of {timestamp, latency_ms, energy_j, deadline_met, handoff_success}
    
    Returns:
        Plotly Figure with subplots
    """
    if not metrics_history:
        # Return empty figure if no data
        return go.Figure().update_layout(
            title='Waiting for data...',
            xaxis_title='Time (s)',
        )
    
    df = pd.DataFrame(metrics_history)
    
    fig = go.Figure()
    
    # Latency trace (left y-axis)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['latency_ms'],
        name='Latency (ms)',
        mode='lines',
        line=dict(color='blue', width=2),
        yaxis='y1',
        fill='tozeroy',
        fillcolor='rgba(0, 0, 255, 0.1)',
    ))
    
    # Energy trace (right y-axis)
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['energy_j'],
        name='Energy (J)',
        mode='lines',
        line=dict(color='orange', width=2),
        yaxis='y2',
    ))
    
    # Deadline compliance rate
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['deadline_met'],
        name='Deadline Success (%)',
        mode='lines+markers',
        line=dict(color='green', width=2),
        marker=dict(size=4),
        yaxis='y3',
    ))
    
    fig.update_layout(
        title='Real-Time System Metrics',
        xaxis=dict(title='Simulation Time (seconds)'),
        yaxis=dict(
            title='Latency (ms)',
            titlefont=dict(color='blue'),
            tickfont=dict(color='blue'),
            side='left',
        ),
        yaxis2=dict(
            title='Energy Consumption (J)',
            titlefont=dict(color='orange'),
            tickfont=dict(color='orange'),
            anchor='x',
            overlaying='y',
            side='right',
        ),
        yaxis3=dict(
            title='Deadline Success (%)',
            titlefont=dict(color='green'),
            tickfont=dict(color='green'),
            anchor='free',
            overlaying='y',
            side='right',
            position=0.85,
        ),
        hovermode='x unified',
        height=500,
        template='plotly_white',
        margin=dict(r=100),
    )
    
    return fig


def create_task_flow_visualization(fog_loads: dict, cloud_load: float) -> go.Figure:
    """
    Create sankey diagram showing task distribution across infrastructure
    
    Args:
        fog_loads: Dict {fog_id: load_percentage}
        cloud_load: Cloud server load percentage
    
    Returns:
        Plotly Figure
    """
    fog_names = list(fog_loads.keys())
    fog_values = list(fog_loads.values())
    
    # Sankey nodes: Vehicles -> Fog Nodes -> Cloud
    nodes = ['Vehicles'] + fog_names + ['Cloud']
    
    # Create connections
    source = [0] * len(fog_names) + [i+1 for i in range(len(fog_names))]
    target = list(range(1, len(fog_names)+1)) + [len(fog_names)+1] * len(fog_names)
    value = fog_values + [cloud_load] * len(fog_names)
    colors_links = ['rgba(0, 100, 200, 0.4)'] * len(fog_names) + \
                   ['rgba(200, 0, 0, 0.4)'] * len(fog_names)
    
    fig = go.Figure(data=[go.Sankey(
        node=dict(
            pad=15,
            thickness=20,
            line=dict(color='black', width=0.5),
            label=nodes,
            color=['lightblue'] + ['orange']*len(fog_names) + ['red'],
        ),
        link=dict(
            source=source,
            target=target,
            value=value,
            color=colors_links,
        ),
    )])
    
    fig.update_layout(
        title='Task Distribution Flow (Sankey)',
        font=dict(size=12),
        height=500,
        template='plotly_white',
    )
    
    return fig


def create_performance_comparison(systems_data: dict) -> go.Figure:
    """
    Create bar chart comparing performance of different systems/baselines
    
    Args:
        systems_data: Dict {system_name: {metric: value}}
            e.g., {'Baseline1': {'latency': 850, 'feasibility': 45},
                   'Proposed': {'latency': 210, 'feasibility': 91}}
    
    Returns:
        Plotly Figure
    """
    if not systems_data:
        return go.Figure().update_layout(title='No comparison data available')
    
    systems = list(systems_data.keys())
    
    # Extract metrics
    latency_values = [systems_data[s].get('latency_ms', 0) for s in systems]
    feasibility_values = [systems_data[s].get('feasibility_pct', 0) for s in systems]
    energy_values = [systems_data[s].get('energy_j', 0) for s in systems]
    handoff_values = [systems_data[s].get('handoff_success_pct', 0) for s in systems]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=systems,
        y=latency_values,
        name='Latency (ms)',
        marker_color='blue',
        yaxis='y1',
    ))
    
    fig.add_trace(go.Bar(
        x=systems,
        y=energy_values,
        name='Energy (J)',
        marker_color='orange',
        yaxis='y2',
    ))
    
    fig.add_trace(go.Scatter(
        x=systems,
        y=feasibility_values,
        name='Deadline Success (%)',
        mode='lines+markers',
        marker=dict(size=10, color='green'),
        yaxis='y3',
    ))
    
    fig.add_trace(go.Scatter(
        x=systems,
        y=handoff_values,
        name='Handoff Success (%)',
        mode='lines+markers',
        marker=dict(size=10, color='purple'),
        yaxis='y4',
    ))
    
    fig.update_layout(
        title='Performance Comparison: Baseline Systems vs. Proposed',
        xaxis=dict(title='System'),
        yaxis=dict(
            title='Latency (ms)',
            titlefont=dict(color='blue'),
            side='left',
        ),
        yaxis2=dict(
            title='Energy (J)',
            titlefont=dict(color='orange'),
            overlaying='y',
            side='right',
            anchor='x',
            position=0.85,
        ),
        yaxis3=dict(
            title='Deadline Success (%)',
            titlefont=dict(color='green'),
            overlaying='y',
            anchor='free',
            side='right',
            position=0.92,
        ),
        yaxis4=dict(
            title='Handoff Success (%)',
            titlefont=dict(color='purple'),
            overlaying='y',
            anchor='free',
            side='right',
            position=0.99,
        ),
        hovermode='x unified',
        height=500,
        barmode='group',
        template='plotly_white',
        margin=dict(r=150),
    )
    
    return fig


def create_network_heatmap(bandwidth_data: pd.DataFrame) -> go.Figure:
    """
    Create heatmap of network bandwidth usage over time
    
    Args:
        bandwidth_data: DataFrame with columns [timestamp, link_name, bandwidth_mbps]
    
    Returns:
        Plotly Figure
    """
    if bandwidth_data.empty:
        return go.Figure().update_layout(title='No bandwidth data available')
    
    pivot_data = bandwidth_data.pivot_table(
        index='link_name',
        columns='timestamp',
        values='bandwidth_mbps'
    )
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=pivot_data.columns,
        y=pivot_data.index,
        colorscale='Viridis',
        colorbar=dict(title='Bandwidth (Mbps)'),
    ))
    
    fig.update_layout(
        title='Network Bandwidth Utilization Heatmap',
        xaxis_title='Time (seconds)',
        yaxis_title='Network Link',
        height=400,
        template='plotly_white',
    )
    
    return fig


def create_queue_status(fog_queues: dict, cloud_queue: int) -> go.Figure:
    """
    Create real-time queue status bar chart
    
    Args:
        fog_queues: Dict {fog_id: queue_length}
        cloud_queue: Cloud queue length
    
    Returns:
        Plotly Figure
    """
    fog_names = list(fog_queues.keys())
    fog_lengths = list(fog_queues.values())
    
    labels = fog_names + ['Cloud']
    values = fog_lengths + [cloud_queue]
    colors = ['orange', 'orange', 'orange', 'orange', 'red']
    
    fig = go.Figure(data=[
        go.Bar(
            x=labels,
            y=values,
            marker=dict(color=colors),
            text=values,
            textposition='auto',
            hovertemplate='<b>%{x}</b><br>Queue Length: %{y}<extra></extra>',
        )
    ])
    
    fig.update_layout(
        title='Queue Status - Tasks Waiting for Processing',
        xaxis_title='Resource',
        yaxis_title='Number of Tasks in Queue',
        height=400,
        template='plotly_white',
        showlegend=False,
    )
    
    return fig
