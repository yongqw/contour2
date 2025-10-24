#!/usr/bin/env python3
"""
Improved semicircular tunnel with bottom surface support.
"""

import sys
import os
import numpy as np
import plotly.graph_objects as go

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.visualization_3d import Visualization3DService
from services.triangulation import TriangulationService
from utils.demo_data import DemoDataGenerator

class ImprovedSemicircularTunnelGeometry:
    """Improved semicircular tunnel geometry with bottom surface."""

    def __init__(self, waypoints):
        """Initialize with list of waypoints."""
        self.waypoints = waypoints

    def get_mesh_vertices(self, segments_per_section: int = 32, points_per_segment: int = 20) -> np.ndarray:
        """Generate 3D mesh vertices for semicircular tunnel with bottom surface."""
        vertices = []

        if len(self.waypoints) < 2:
            return np.array([])

        # For each segment between waypoints
        for segment_idx in range(len(self.waypoints) - 1):
            wp1 = self.waypoints[segment_idx]
            wp2 = self.waypoints[segment_idx + 1]

            # Create interpolated points along the segment
            for j in range(points_per_segment):
                t = j / (points_per_segment - 1)

                # Linear interpolation of position
                x = wp1.x + t * (wp2.x - wp1.x)
                y = wp1.y + t * (wp2.y - wp1.y)
                z = wp1.z + t * (wp2.z - wp1.z)
                radius = wp1.radius + t * (wp2.radius - wp1.radius)

                # Create semicircular cross-section (flat bottom, semicircular top)
                for k in range(segments_per_section):
                    angle = -np.pi/2 + (np.pi * k) / (segments_per_section - 1)

                    tunnel_y = y + radius * np.sin(angle)
                    tunnel_z = z + radius * np.cos(angle)

                    vertices.append([x, tunnel_y, tunnel_z])

        return np.array(vertices)

    def get_mesh_triangles(self, segments_per_section: int = 32, points_per_segment: int = 20):
        """Generate triangle indices for semicircular tunnel mesh."""
        if len(self.waypoints) < 2:
            return None

        triangles = []

        for segment_idx in range(len(self.waypoints) - 1):
            start_idx = segment_idx * segments_per_section * points_per_segment
            next_start_idx = (segment_idx + 1) * segments_per_section * points_per_segment

            # Generate triangles for semicylindrical surface between segments
            for ring_idx in range(points_per_segment - 1):
                ring_start = start_idx + ring_idx * segments_per_section
                next_ring_start = start_idx + (ring_idx + 1) * segments_per_section

                for k in range(segments_per_section - 1):
                    v1 = ring_start + k
                    v2 = ring_start + k + 1
                    v3 = next_ring_start + k
                    v4 = next_ring_start + k + 1

                    triangles.append([v1, v2, v3])
                    triangles.append([v2, v4, v3])

            # Connect segments
            if segment_idx < len(self.waypoints) - 2:
                last_ring_start = start_idx + (points_per_segment - 1) * segments_per_section
                next_first_ring_start = next_start_idx

                for k in range(segments_per_section - 1):
                    v1 = last_ring_start + k
                    v2 = last_ring_start + k + 1
                    v3 = next_first_ring_start + k
                    v4 = next_first_ring_start + k + 1

                    triangles.append([v1, v2, v3])
                    triangles.append([v2, v4, v3])

        return triangles

    def get_bottom_surface_vertices(self, points_per_segment: int = 20) -> np.ndarray:
        """Generate bottom surface vertices (flat ground)."""
        vertices = []

        if len(self.waypoints) < 2:
            return np.array([])

        for segment_idx in range(len(self.waypoints) - 1):
            wp1 = self.waypoints[segment_idx]
            wp2 = self.waypoints[segment_idx + 1]

            # Create interpolated points along the segment
            for j in range(points_per_segment):
                t = j / (points_per_segment - 1)

                # Linear interpolation
                x = wp1.x + t * (wp2.x - wp1.x)
                y = wp1.y + t * (wp2.y - wp1.y)
                z = wp1.z + t * (wp2.z - wp1.z)
                radius = wp1.radius + t * (wp2.radius - wp1.radius)

                # Create rectangular bottom surface around tunnel
                # Extend slightly beyond tunnel edges for support
                margin = radius * 0.1  # 10% margin
                vertices.append([x, y - radius - margin, z])
                vertices.append([x, y + radius + margin, z])

        return np.array(vertices)

    def get_bottom_surface_triangles(self, points_per_segment: int = 20):
        """Generate triangles for bottom surface."""
        if len(self.waypoints) < 2:
            return None

        triangles = []

        for segment_idx in range(len(self.waypoints) - 1):
            start_idx = segment_idx * points_per_segment * 2
            next_start_idx = (segment_idx + 1) * points_per_segment * 2

            for j in range(points_per_segment - 1):
                # Current rectangle vertices
                v1 = start_idx + j * 2  # bottom-left
                v2 = start_idx + j * 2 + 1  # bottom-right
                v3 = next_start_idx + j * 2  # next bottom-left
                v4 = next_start_idx + j * 2 + 1  # next bottom-right

                # Two triangles per rectangle
                triangles.append([v1, v2, v3])
                triangles.append([v2, v4, v3])

        return triangles

class Waypoint:
    """Simple waypoint class."""
    def __init__(self, x, y, z, radius):
        self.x = x
        self.y = y
        self.z = z
        self.radius = radius

def create_improved_semicircular_tunnel():
    """Create improved semicircular tunnel with bottom surface."""
    print("Creating improved semicircular tunnel with bottom surface...")

    # Load terrain
    demo_generator = DemoDataGenerator()
    contour_data = demo_generator.generate_hill_terrain()
    triangulation_service = TriangulationService()
    terrain_mesh = triangulation_service.triangulate_contours(contour_data)

    # Create tunnel waypoints
    waypoints = [
        Waypoint(25.0, 25.0, 120.0, radius=20.0),
        Waypoint(75.0, 75.0, 120.0, radius=20.0),
    ]

    tunnel_geom = ImprovedSemicircularTunnelGeometry(waypoints)

    # Generate tunnel mesh
    print("Generating semicircular tunnel mesh...")
    tunnel_vertices = tunnel_geom.get_mesh_vertices(
        segments_per_section=32,
        points_per_segment=30
    )
    tunnel_triangles = tunnel_geom.get_mesh_triangles(
        segments_per_section=32,
        points_per_segment=30
    )

    # Generate bottom surface mesh
    print("Generating bottom surface mesh...")
    bottom_vertices = tunnel_geom.get_bottom_surface_vertices(points_per_segment=30)
    bottom_triangles = tunnel_geom.get_bottom_surface_triangles(points_per_segment=30)

    print(f"Tunnel mesh: {len(tunnel_vertices)} vertices, {len(tunnel_triangles)} triangles")
    print(f"Bottom surface: {len(bottom_vertices)} vertices, {len(bottom_triangles)} triangles")

    # Create visualization
    print("Creating 3D visualization...")
    fig = go.Figure()

    # Add terrain (semi-transparent)
    terrain_trace = go.Mesh3d(
        x=terrain_mesh.vertices[:, 0],
        y=terrain_mesh.vertices[:, 1],
        z=terrain_mesh.vertices[:, 2],
        i=[t.vertex_indices[0] for t in terrain_mesh.triangles],
        j=[t.vertex_indices[1] for t in terrain_mesh.triangles],
        k=[t.vertex_indices[2] for t in terrain_mesh.triangles],
        intensity=terrain_mesh.vertices[:, 2],
        colorscale=[[0.0, "brown"], [1.0, "white"]],
        name='Terrain',
        opacity=0.6,
        showscale=True
    )
    fig.add_trace(terrain_trace)

    # Add bottom surface (same color as tunnel)
    if bottom_triangles and len(bottom_triangles) > 0:
        bottom_array = np.array(bottom_triangles)

        bottom_trace = go.Mesh3d(
            x=bottom_vertices[:, 0],
            y=bottom_vertices[:, 1],
            z=bottom_vertices[:, 2],
            i=bottom_array[:, 0],
            j=bottom_array[:, 1],
            k=bottom_array[:, 2],
            color='gray',  # Same color as tunnel
            name='Bottom Surface',
            opacity=1.0,
            showscale=False,
            flatshading=True,
            lighting=dict(ambient=0.8, diffuse=0.8, specular=0.3, roughness=0.3)
        )
        fig.add_trace(bottom_trace)

    # Add semicircular tunnel
    if tunnel_triangles and len(tunnel_triangles) > 0:
        tunnel_array = np.array(tunnel_triangles)

        tunnel_trace = go.Mesh3d(
            x=tunnel_vertices[:, 0],
            y=tunnel_vertices[:, 1],
            z=tunnel_vertices[:, 2],
            i=tunnel_array[:, 0],
            j=tunnel_array[:, 1],
            k=tunnel_array[:, 2],
            color='gray',  # Same color as bottom
            name='Semicircular Tunnel',
            opacity=1.0,
            showscale=False,
            flatshading=True,
            lighting=dict(ambient=0.8, diffuse=0.8, specular=0.3, roughness=0.3)
        )
        fig.add_trace(tunnel_trace)

    # Add centerline with improved entrance/exit markers
    centerline = go.Scatter3d(
        x=[wp.x for wp in waypoints],
        y=[wp.y for wp in waypoints],
        z=[wp.z for wp in waypoints],
        mode='lines+markers',
        line=dict(color='red', width=10),
        marker=dict(
            symbol='diamond',  # Diamond shape instead of circle
            size=6,           # Smaller size
            color='orange',    # Orange instead of yellow
            line=dict(width=1, color='red')  # Red border to match line
        ),
        name='Vehicle Path'
    )
    fig.add_trace(centerline)

    # Add road surface edges
    for i in range(len(waypoints)):
        edge_line = go.Scatter3d(
            x=[waypoints[i].x, waypoints[i].x],
            y=[waypoints[i].y - waypoints[i].radius, waypoints[i].y + waypoints[i].radius],
            z=[waypoints[i].z, waypoints[i].z],
            mode='lines',
            line=dict(color='yellow', width=6, dash='dot'),
            name=f'Road Edge {i+1}' if i == 0 else None,
            showlegend=(i == 0)
        )
        fig.add_trace(edge_line)

    # Add road lane markings
    if len(waypoints) >= 2:
        # Center lane marking (dashed white line)
        center_lane = go.Scatter3d(
            x=[wp.x for wp in waypoints],
            y=[wp.y for wp in waypoints],
            z=[wp.z for wp in waypoints],
            mode='lines',
            line=dict(color='white', width=3, dash='dash'),
            name='Center Lane'
        )
        fig.add_trace(center_lane)

        # Side lane markings at 1/3 and 2/3 positions
        lane_positions = [0.33, 0.67]  # 1/3 and 2/3 of tunnel width
        lane_names = ['Left Lane Marking', 'Right Lane Marking']

        for i, lane_pos in enumerate(lane_positions):
            side_lane_x = []
            side_lane_y = []
            side_lane_z = []

            for wp in waypoints:
                side_lane_x.append(wp.x)
                # Calculate offset from center (tunnel center is at wp.y)
                lane_offset = (lane_pos - 0.5) * 2 * wp.radius
                side_lane_y.append(wp.y + lane_offset)
                side_lane_z.append(wp.z)

            side_lane = go.Scatter3d(
                x=side_lane_x,
                y=side_lane_y,
                z=side_lane_z,
                mode='lines',
                line=dict(color='white', width=2, dash='solid'),
                name=lane_names[i]
            )
            fig.add_trace(side_lane)

        # Directional arrows
        # Entrance arrow
        entrance_end_x = waypoints[0].x + 0.8 * (waypoints[1].x - waypoints[0].x)
        entrance_end_y = waypoints[0].y + 0.8 * (waypoints[1].y - waypoints[0].y)
        entrance_end_z = waypoints[0].z + 0.8 * (waypoints[1].z - waypoints[0].z)

        entrance_arrow = go.Scatter3d(
            x=[waypoints[0].x, entrance_end_x],
            y=[waypoints[0].y, entrance_end_y],
            z=[waypoints[0].z, entrance_end_z],
            mode='lines',
            line=dict(color='white', width=4),
            name='Entrance Direction'
        )
        fig.add_trace(entrance_arrow)

        # Exit arrow
        last_idx = len(waypoints) - 1
        exit_end_x = waypoints[last_idx].x + 0.8 * (waypoints[last_idx-1].x - waypoints[last_idx].x)
        exit_end_y = waypoints[last_idx].y + 0.8 * (waypoints[last_idx-1].y - waypoints[last_idx].y)
        exit_end_z = waypoints[last_idx].z + 0.8 * (waypoints[last_idx-1].z - waypoints[last_idx].z)

        exit_arrow = go.Scatter3d(
            x=[waypoints[last_idx].x, exit_end_x],
            y=[waypoints[last_idx].y, exit_end_y],
            z=[waypoints[last_idx].z, exit_end_z],
            mode='lines',
            line=dict(color='white', width=4),
            name='Exit Direction'
        )
        fig.add_trace(exit_arrow)

    fig.update_layout(
        title="Improved Semicircular Tunnel with Bottom Support",
        scene=dict(
            xaxis_title='X (m)',
            yaxis_title='Y (m)',
            zaxis_title='Elevation (m)',
            camera=dict(eye=dict(x=1.5, y=1.5, z=0.5)),
            bgcolor='white',
            aspectmode='data'
        ),
        width=1200,
        height=800,
        legend=dict(
            x=0.02,
            y=0.98,
            bgcolor='rgba(255,255,255,0.8)',
            bordercolor='black',
            borderwidth=1
        )
    )

    return fig

def main():
    """Main function."""
    print("="*70)
    print("IMPROVED SEMICIRCULAR TUNNEL WITH BOTTOM SUPPORT")
    print("="*70)

    try:
        fig = create_improved_semicircular_tunnel()

        if fig:
            fig.write_html("improved_semicircular_tunnel.html")
            print(f"\nImproved semicircular tunnel saved to: improved_semicircular_tunnel.html")
            print("\nFeatures:")
            print("- Semicircular tunnel with flat bottom")
            print("- Bottom surface with same color for continuity")
            print("- No visual gaps or floating appearance")
            print("- Proper support structure visualization")
            print("- Yellow dotted lines show road edges")

        else:
            print("\nTest failed!")

    except Exception as e:
        print(f"\nERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)