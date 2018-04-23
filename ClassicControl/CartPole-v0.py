import numpy as np
import tensorflow as tf
import gym

env = gym.make('CartPole-v0')

class QNetwork:
    def __init__(self,learning_rate=0.01,state_size=4,action_size=2,hidden_size=10,name='QNetwork'):
        with tf.variable_scope(name):
            self.inputs_= tf.placeholder(tf.float32,[None,state_size],name='input')

            self.actions_ = tf.placeholder(tf.int32, [None], name= 'actions')
            one_hot_actions = tf.one_hot(self.actions_, action_size)

            self.targetQs_ = tf.placeholder(tf.float32, [None], name = 'target')

            self.fc1 = tf.contrib.layers.fully_connected(self.inputs_, hidden_size);
            self.fc2 = tf.contrib.layers.fully_connected(self.fc1, hidden_size);

            self.output = tf.contrib.layers.fully_connected(self.fc2, action_size, activation_fn=None);

            self.Q = tf.reduce_sum(tf.multiply(self.output, one_hot_actions), axis=1)
            self.loss = tf.reduce_mean(tf.square(self.targetQs_ - self.Q))
            self.opt = tf.train.AdamOptimizer(learning_rate).minimize(self.loss)

from collections import deque

class Memory():
    def __init__(self,max_size = 1000):
        self.buffer = deque(maxlen = max_size)
    
    def add(self,experience):
        self.buffer.append(experience)
    
    def sample(self, batch_size):
        idx = np.random.choice(np.arange(len(self.buffer)),
                                            size=batch_size,
                                            replace = False)
        return [self.buffer[ii] for ii in idx]

def conTuple(a,t):
    l = list(t)
    l.insert(0,a)
    return tuple(l)

# hyperparameters
train_episodes = 1000          # max number of episodes to learn from
max_steps = 200                # max steps in an episode
gamma = 0.99                   # future reward discount

# Exploration parameters
explore_start = 1.0            # exploration probability at start
explore_stop = 0.01            # minimum exploration probability 
decay_rate = 0.0001            # exponential decay rate for exploration prob

# Network parameters
hidden_size = 64               # number of units in each Q-network hidden layer
learning_rate = 0.0001         # Q-network learning rate

# Memory parameters
memory_size = 10000            # memory capacity
batch_size = 20                # experience mini-batch size
pretrain_length = batch_size   # number experiences to pretrain the memory

tf.reset_default_graph()
mainQN= QNetwork(name='main', hidden_size=hidden_size ,learning_rate=learning_rate)

env.reset()
state,reward,done, _ = env.step(env.action_space.sample())

memory = Memory(max_size=memory_size)

for ii in range(pretrain_length):
    action = env.action_space.sample()
    next_state,reward,done, _ = env.step(action)

    if(done):
        next_state = np.zeros(state.shape)
        memory.add((state,action,reward,next_state))

        env.reset()
        state, reward, done, _ = env.step(env.action_space.sample())
    else:
        # Add experience to memory
        memory.add((state, action, reward, next_state))
        state = next_state

# Training
# Now train with experiences
saver = tf.train.Saver()
rewards_list = []
with tf.Session() as sess:
    # Initialize variables
    sess.run(tf.global_variables_initializer())

    step = 0
    for ep in range(1, train_episodes):
        total_reward = 0
        t = 0
        while t < max_steps:
            step += 1
            # Uncomment this next line to watch the training
            env.render() 

            # Explore or Exploit
            explore_p = explore_stop + (explore_start - explore_stop)*np.exp(-decay_rate*step) 
            if explore_p > np.random.rand():
                # Make a random action
                action = env.action_space.sample()
            else:
                # Get action from Q-network
                feed = {mainQN.inputs_: state.reshape(conTuple(1, state.shape))}
                Qs = sess.run(mainQN.output, feed_dict=feed)
                action = np.argmax(Qs)

            # Take action, get new state and reward
            next_state, reward, done, _ = env.step(action)

            total_reward += reward

            if done:
                # the episode ends so no next state
                next_state = np.zeros(state.shape)
                t = max_steps

                print('Episode: {}'.format(ep),
                      'Total reward: {}'.format(total_reward),
                      'Training loss: {:.4f}'.format(loss),
                      'Explore P: {:.4f}'.format(explore_p))
                rewards_list.append((ep, total_reward))

                # Add experience to memory
                memory.add((state, action, reward, next_state))

                # Start new episode
                env.reset()
                # Take one random step to get the pole and cart moving
                state, reward, done, _ = env.step(env.action_space.sample())

            else:
                # Add experience to memory
                memory.add((state, action, reward, next_state))
                state = next_state
                t += 1

            # Sample mini-batch from memory
            batch = memory.sample(batch_size)
            states = np.array([each[0] for each in batch])
            actions = np.array([each[1] for each in batch])
            rewards = np.array([each[2] for each in batch])
            next_states = np.array([each[3] for each in batch])

            # Train network
            target_Qs = sess.run(mainQN.output, feed_dict={mainQN.inputs_: next_states})

            # Set target_Qs to 0 for states where episode ends
            episode_ends = (next_states == np.zeros(states[0].shape)).all(axis=1)
            target_Qs[episode_ends] = (0, 0)

            targets = rewards + gamma * np.max(target_Qs, axis=1)

            loss, _ = sess.run([mainQN.loss, mainQN.opt],
                                feed_dict={mainQN.inputs_: states,
                                           mainQN.targetQs_: targets,
                                           mainQN.actions_: actions})

    saver.save(sess, "checkpoints/cartpole.ckpt")

    # Testing
test_episodes = 10
test_max_steps = 400
env.reset()
with tf.Session() as sess:
    saver.restore(sess, tf.train.latest_checkpoint('checkpoints'))

    for ep in range(1, test_episodes):
        t = 0
        while t < test_max_steps:
            env.render() 

            # Get action from Q-network
            feed = {mainQN.inputs_: state.reshape(conTuple(1, state.shape))}
            Qs = sess.run(mainQN.output, feed_dict=feed)
            action = np.argmax(Qs)

            # Take action, get new state and reward
            next_state, reward, done, _ = env.step(action)

            if done:
                t = test_max_steps
                env.reset()
                # Take one random step to get the pole and cart moving
                state, reward, done, _ = env.step(env.action_space.sample())

            else:
                state = next_state
                t += 1

env.close()

