# Dataset Key: `gen_BC_dataset.csv`

This file serves as the legend mapping the state observations and expert actions generated for the Behavioral Cloning (BC) pre-training dataset.

## Actions (Target Variable)

The `action` column represents the optimal routing decision produced by the expert oracle:

- **`0`**: Offload task to **Fog Node A**
- **`1`**: Offload task to **Fog Node B**
- **`2`**: Offload task to **Fog Node C**
- **`3`**: Offload task to **Fog Node D**
- **`4`**: Offload task to **Cloud Server**

## States (Input Features)

All state values are continuous numbers normalized between `0.0` and `1.0`.

### Fog Node Status

- **`fog_A_load` to `fog_D_load`**: Current CPU utilization of the respective Fog Node.
- **`fog_A_queue` to `fog_D_queue`**: Current queue depth (waiting tasks) at the respective Fog Node.

### Task & Vehicle Context

- **`exec_cost_norm`**: Computational weight of the incoming task (higher means it requires more CPU cycles).
- **`speed_norm`**: Current speed of the vehicle generating the task.
- **`t_exit_norm`**: Remaining time before the vehicle exits the current fog coverage zone (lower means leaving sooner).
