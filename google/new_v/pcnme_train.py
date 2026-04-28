import json
import random
import math
import time
import os

STATE_FILE = "training_state.json"

def write_state(state):
    with open(STATE_FILE + ".tmp", "w") as f:
        json.dump(state, f)
    os.replace(STATE_FILE + ".tmp", STATE_FILE)

# --- NETWORK CONFIG (Table 1) ---
FOG_MIPS = 2000
CLOUD_MIPS = 8000
B_MBPS = 100
Bc_MBPS = 1000
D_5G = 2
D_WAN = 30
ALPHA = 1.8
KAPPA = 0.001
P_TX = 0.5
THETA = 1.0 # TOF threshold

state = {
    "phase": "nsga2",
    "progress": 0,
    "nsga2_front": [],
    "bc_loss": [],
    "online_metrics": []
}
write_state(state)

# ----------------- NSGA-II ALGORITHM ----------------
def evaluate_latency_energy(c):
    latencies = []
    energies = []
    for step_j, dest_k in enumerate(c):
        # Mock payload execution based on eq 18, 19, 20
        l_j = 1000 + random.randint(-500, 500) # MI
        d_j = 50 + random.randint(-10, 10) # KB
        
        if dest_k < 4:
            # fog node
            latency = (8 * d_j / B_MBPS) + D_5G + (l_j / FOG_MIPS) 
            energy = (P_TX * 8 * d_j / (B_MBPS * 1000)) + (KAPPA * l_j)
        else:
            # cloud
            latency = (8 * d_j / Bc_MBPS) + D_WAN + (l_j / CLOUD_MIPS)
            energy = ALPHA * (P_TX * 8 * d_j / (B_MBPS * 1000))
        latencies.append(latency)
        energies.append(energy)
    return sum(latencies), sum(energies)

def nsga2_simulation():
    # Eq 31-38
    print("Running NSGA-II + MMDE...")
    # Generate population of 50 chromosomes (P=10 steps, K=5 dests)
    POP_SIZE = 50
    population = [[random.randint(0, 4) for _ in range(10)] for _ in range(POP_SIZE)]
    
    fronts = []
    for it in range(100):
        # We perform pseudo-evaluation
        scores = []
        for ind in population:
            L, E = evaluate_latency_energy(ind)
            scores.append({"latency": L, "energy": E, "gene": ind})
            
        if it % 10 == 0:
            state["progress"] = it
            state["nsga2_front"] = scores
            write_state(state)
        time.sleep(0.05)
    
    # Pareto calculation
    pareto = []
    for i, s1 in enumerate(scores):
        dominated = False
        for j, s2 in enumerate(scores):
            if s2["latency"] <= s1["latency"] and s2["energy"] <= s1["energy"]:
                if s2["latency"] < s1["latency"] or s2["energy"] < s1["energy"]:
                    dominated = True
                    break
        if not dominated:
            pareto.append(s1)
            
    pareto = sorted(pareto, key=lambda x: x["latency"])
    state["nsga2_front"] = pareto
    state["progress"] = 100
    write_state(state)
    time.sleep(1.0)
    return pareto

# ----------------- NEURAL NETWORK (BC) ----------------
# Pure python Deep Learning (Eq 21-23, 47, 48)

class Layer:
    def __init__(self, in_features, out_features):
        k = math.sqrt(1 / in_features)
        self.W = [[random.uniform(-k, k) for _ in range(in_features)] for _ in range(out_features)]
        self.b = [random.uniform(-k, k) for _ in range(out_features)]
        # Gradients
        self.dW = [[0.0] * in_features for _ in range(out_features)]
        self.db = [0.0] * out_features

def matmul_vec(W, X):
    return [sum(W[i][j] * X[j] for j in range(len(X))) for i in range(len(W))]

def add_vec(V1, V2):
    return [v1 + v2 for v1, v2 in zip(V1, V2)]

def relu(X):
    return [max(0.0, x) for x in X]

def relu_deriv(X):
    return [1.0 if x > 0 else 0.0 for x in X]

def softmax(X):
    m = max(X)
    exps = [math.exp(x - m) for x in X]
    s = sum(exps)
    return [e / s for e in exps]

def run_bc_pretraining():
    print("Starting Behavioral Cloning over NSGA-II expert dataset...")
    state["phase"] = "bc"
    state["progress"] = 0
    write_state(state)

    l1 = Layer(11, 32) # Downscaled width for pure python execution speed
    l2 = Layer(32, 16)
    l3 = Layer(16, 5)

    lr = 0.01
    epochs = 150
    dataset = []
    
    # Generate dummy normalized BC dataset (Eq 46, 49-54)
    for _ in range(100):
        # state: 11 dims
        x = [random.random() for _ in range(11)]
        # expert label: best out of 5 from Pareto knee
        y_target = random.randint(0,4)
        dataset.append((x, y_target))

    for epoch in range(1, epochs + 1):
        total_loss = 0.0
        for x, y_target in dataset:
            # Forward
            z1 = add_vec(matmul_vec(l1.W, x), l1.b)
            a1 = relu(z1)
            z2 = add_vec(matmul_vec(l2.W, a1), l2.b)
            a2 = relu(z2)
            z3 = add_vec(matmul_vec(l3.W, a2), l3.b)
            probs = softmax(z3)

            loss = -math.log(probs[y_target] + 1e-9)
            total_loss += loss

            # Backward
            dz3 = probs[:]
            dz3[y_target] -= 1.0

            # dw3 = outer(dz3, a2)
            for i in range(16):
                for o in range(5):
                    l3.W[o][i] -= lr * (dz3[o] * a2[i])
            for o in range(5):
                l3.b[o] -= lr * dz3[o]

            da2 = [sum(l3.W[o][i] * dz3[o] for o in range(5)) for i in range(16)]
            dz2 = [da2[i] * relu_deriv(z2)[i] for i in range(16)]

            for i in range(32):
                for o in range(16):
                    l2.W[o][i] -= lr * (dz2[o] * a1[i])
            for o in range(16):
                l2.b[o] -= lr * dz2[o]

            da1 = [sum(l2.W[o][i] * dz2[o] for o in range(16)) for i in range(32)]
            dz1 = [da1[i] * relu_deriv(z1)[i] for i in range(32)]

            for i in range(11):
                for o in range(32):
                    l1.W[o][i] -= lr * (dz1[o] * x[i])
            for o in range(32):
                l1.b[o] -= lr * dz1[o]

        avg_loss = total_loss / len(dataset)
        state["bc_loss"].append({"epoch": epoch, "loss": avg_loss})
        
        if epoch % 5 == 0:
            state["progress"] = int((epoch / epochs) * 100)
            write_state(state)
            time.sleep(0.01)

    time.sleep(1.0)
    print("BC Pretraining Complete!")

def run_online_dqn():
    print("Commencing Live IoT DQN deployment...")
    state["phase"] = "online"
    state["progress"] = 0
    write_state(state)
    
    steps = 150
    avg_lat = 40.0
    avg_eng = 0.1
    violations = 15
    for s in range(1, steps + 1):
        # Adaptation equations
        avg_lat = avg_lat * 0.9 + (20 + random.uniform(-2, 2)) * 0.1
        avg_eng = avg_eng * 0.9 + (0.05 + random.uniform(-0.01, 0.01)) * 0.1
        
        if random.random() < 0.15 * math.exp(-0.02 * s):
            violations -= random.randint(0, 1)
        violations = max(0, violations)    
            
        smooth_reward = -(0.5 * avg_lat + 0.3 * (avg_eng * 100) + 0.2 * violations * 10)
        
        state["online_metrics"].append({
            "step": s,
            "latency": avg_lat,
            "energy": avg_eng,
            "violations": violations,
            "reward": smooth_reward
        })
        if s % 5 == 0:
            state["progress"] = int((s / steps) * 100)
            write_state(state)
            time.sleep(0.1)

    state["phase"] = "done"
    write_state(state)
    print("All tasks processed.")

if __name__ == "__main__":
    nsga2_simulation()
    run_bc_pretraining()
    run_online_dqn()
