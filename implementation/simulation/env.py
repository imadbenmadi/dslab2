import gymnasium as gym
from gymnasium import spaces
import numpy as np

class TaskOffloadingEnv(gym.Env):
    """RL environment for task offloading decisions."""
    
    def __init__(self):
        self.observation_space = spaces.Box(low=0, high=1, shape=(13,), dtype=np.float32)
        self.action_space = spaces.Discrete(5)  # 5 offloading destinations
    
    def reset(self):
        """Reset environment to initial state"""
        return self.observation_space.sample()
    
    def step(self, action):
        """Execute one environment step"""
        observation = self.observation_space.sample()
        reward = 0.0
        terminated = False
        truncated = False
        info = {}
        return observation, reward, terminated, truncated, info
