import ezdxf

def create_sample_mine_dxf(filepath="e:/miners/sample_mine_drift_blueprint.dxf"):
    doc = ezdxf.new('R2000')
    doc.units = ezdxf.units.M # Meters
    msp = doc.modelspace()
    
    # Layer for Mine Walls
    doc.layers.add('MINE_WALLS', color=7)
    
    # 1. Outer boundary (20m x 20m)
    msp.add_lwpolyline([(0, 0), (20, 0), (20, 20), (0, 20)], close=True, dxfattribs={'layer': 'MINE_WALLS'})
    
    # 2. Main Central Pillar (Pillar 1: 5m to 8m X, 4m to 16m Y)
    msp.add_lwpolyline([(5, 4), (8, 4), (8, 16), (5, 16)], close=True, dxfattribs={'layer': 'MINE_WALLS'})
    
    # 3. East Pillar (Pillar 2: 12m to 15m X, 4m to 9m Y)
    msp.add_lwpolyline([(12, 4), (15, 4), (15, 9), (12, 9)], close=True, dxfattribs={'layer': 'MINE_WALLS'})
    
    # 4. North-East Pillar (Pillar 3: 12m to 15m X, 12m to 16m Y)
    msp.add_lwpolyline([(12, 12), (15, 12), (15, 16), (12, 16)], close=True, dxfattribs={'layer': 'MINE_WALLS'})
    
    # 5. Rockfall Obstacle in East Crosscut
    msp.add_line((15, 10.5), (20, 10.5), dxfattribs={'layer': 'MINE_WALLS'})
    
    doc.saveas(filepath)
    print(f"[Sample Mine Blueprint Created] {filepath}")

if __name__ == '__main__':
    create_sample_mine_dxf()
