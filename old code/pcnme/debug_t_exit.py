from pcnme import formulas
import math

vehicle_x = 320
vehicle_y = 500
speed_ms = 19.4
heading_deg = 90
fog_x = 200
fog_y = 500
fog_radius = 250

print("T_exit Calculation Debug")
print(f"Vehicle: ({vehicle_x}, {vehicle_y})")
print(f"Fog: ({fog_x}, {fog_y})")
print(f"Speed: {speed_ms} m/s, Heading: {heading_deg}°")
print(f"Radius: {fog_radius} m")

# Step 1: Calculate distance
dist = math.sqrt((vehicle_x - fog_x)**2 + (vehicle_y - fog_y)**2)
print(f"\nDistance to fog: {dist} m")

# Step 2: Check if outside
if dist >= fog_radius:
    print("Outside fog zone - T_exit = 0")
else:
    print("Inside fog zone - computing T_exit")
    
    # Step 3: Calculate velocity
    heading_rad = math.radians(heading_deg)
    vx = speed_ms * math.cos(heading_rad)
    vy = speed_ms * math.sin(heading_rad)
    print(f"Velocity: ({vx:.2f}, {vy:.2f}) m/s")
    
    # Step 4: Calculate closing velocity
    dx = fog_x - vehicle_x
    dy = fog_y - vehicle_y
    dist_check = math.sqrt(dx**2 + dy**2)
    
    nx = -dx / dist_check if dist_check > 0 else 0
    ny = -dy / dist_check if dist_check > 0 else 0
    print(f"Normal vector: ({nx:.2f}, {ny:.2f})")
    
    v_close = vx * nx + vy * ny
    print(f"Closing velocity: {v_close:.2f} m/s")
    
    if v_close <= 0:
        print("Vehicle moving away (v_close <= 0) - T_exit = inf")
    else:
        t_exit = (fog_radius - dist) / v_close
        print(f"T_exit = ({fog_radius} - {dist}) / {v_close} = {t_exit:.2f} s")

# Now call the actual function
result = formulas.compute_t_exit(vehicle_x, vehicle_y, speed_ms, heading_deg, fog_x, fog_y, fog_radius)
print(f"\nActual function result: {result}")
print(f"Type: {type(result)}")
print(f"Is finite: {result != float('inf')}")
