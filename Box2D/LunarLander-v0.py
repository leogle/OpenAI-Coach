import numpy as np
import tensorflow as tf
import time
import gym

env = gym.make('LunarLander-v2')
env.reset()
env.render()