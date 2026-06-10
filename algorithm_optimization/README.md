# Algorithm Optimization for hw-1 Gait Device

This directory contains advanced optimization approaches for improving the control policies and parameter selection of the hw-1 quasi-passive biped walking robot. The baseline finite state machine (FSM) controller established in V13.6-V13.7 and V17 provides a stable foundation, but optimization algorithms can potentially discover better control strategies, more robust parameter configurations, and more energy-efficient gaits.

---

## Overview of Optimization Approaches

### 1. **Reinforcement Learning (RL)**
Train neural network policies to replace or augment the FSM controller. RL can discover non-intuitive control strategies that outperform hand-crafted rules.

**Suitable algorithms:**
- **PPO (Proximal Policy Optimization)**: Stable, sample-efficient, good for continuous control
- **SAC (Soft Actor-Critic)**: Off-policy, handles exploration well, suitable for complex tasks
- **TD3 (Twin Delayed DDPG)**: Deterministic policy, fast convergence for well-defined reward functions

**Use cases:**
- Hip torque modulation beyond FSM bang-bang control
- Adaptive gait on varying terrain (terrain robustness beyond V11)
- Energy minimization (lower CoT than V12 baseline)

### 2. **Evolutionary Algorithms (EA)**
Population-based search over controller parameters or gait primitives. Does not require gradient information; robust to local minima.

**Suitable algorithms:**
- **CMA-ES (Covariance Matrix Adaptation Evolution Strategy)**: Efficient gradient-free optimization
- **Genetic Algorithm (GA)**: Simple, interpretable, good for discrete parameter search
- **NSGA-II (Non-dominated Sorting GA)**: Multi-objective optimization (e.g., stability + energy efficiency)

**Use cases:**
- FSM parameter tuning (hip_kp, hip_kd, phase transition thresholds)
- Morphology co-optimization (leg length, foot radius, torso mass)
- Multi-objective optimization: stability + CoT + robustness

### 3. **Bayesian Optimization (BO)**
Sample-efficient black-box optimization using Gaussian Process surrogates. Ideal when simulation cost is high.

**Suitable algorithms:**
- **BO-GP (Gaussian Process-based BO)**: Standard choice for expensive functions
- **TPE (Tree-structured Parzen Estimator)**: Alternative surrogate, used in Optuna
- **SMAC (Sequential Model-based Algorithm Configuration)**: For mixed continuous/discrete spaces

**Use cases:**
- Fine-tuning control gains (extending V13 parameter atlas)
- Hyperparameter search for RL training
- Hardware calibration after system identification (V23)

### 4. **Trajectory Optimization**
Direct optimization of state-action trajectories using constrained nonlinear programming (NLP).

**Suitable algorithms:**
- **Direct Collocation**: Discretize continuous dynamics into NLP problem
- **DDP (Differential Dynamic Programming)**: Iterative LQR-like method for locally optimal trajectories
- **iLQG (iterative LQG)**: Handles stochastic disturbances

**Use cases:**
- Reference trajectory generation for tracking controllers
- Limit cycle refinement (V3/V5 follow-up)
- Minimum-energy gait synthesis

---

## Installation

### Prerequisites
- Python 3.9+ with MuJoCo bindings (already in `.venv-mujoco`)
- ~10 GB disk space for RL libraries and logged data

### Step 1: Activate Virtual Environment
```powershell
cd D:\Dunna\Documents\hw-1
.\.venv-mujoco\Scripts\Activate.ps1
```

### Step 2: Install RL Libraries
```powershell
# Core RL frameworks
pip install stable-baselines3==2.3.2         # PPO, SAC, TD3
pip install sb3-contrib==2.3.0                # Additional algorithms
pip install gymnasium[mujoco]==0.29.1         # Standard RL interface

# Evolutionary algorithms
pip install cma==3.3.0                        # CMA-ES
pip install deap==1.4.1                       # Genetic algorithms

# Bayesian optimization
pip install optuna==3.6.1                     # BO framework with TPE
pip install scikit-optimize==0.10.2           # BO-GP

# Trajectory optimization (optional, requires more dependencies)
pip install pyomo==6.8.0                      # Algebraic modeling
pip install ipopt==1.4.0                      # NLP solver
```

### Step 3: Verify Installation
```powershell
python -c "import stable_baselines3; import cma; import optuna; print('All packages loaded successfully')"
```

---

## Quick Start

### Example 1: RL Policy Training (PPO on V13.7 Baseline)
```powershell
cd D:\Dunna\Documents\hw-1\algorithm_optimization
python train_rl_policy.py --algorithm ppo --env-name hw1-v137-flat --total-steps 1000000 --save-freq 50000
```
**Expected training time**: 6-12 hours on GPU, 24-48 hours on CPU
**Output**: `models/ppo_hw1_v137/` containing checkpoints and TensorBoard logs

### Example 2: CMA-ES Parameter Tuning (FSM Gains)
```powershell
python optimize_cmaes.py --param-space fsm_gains --population 20 --generations 100
```
**Expected time**: ~10 hours (20 × 100 = 2000 evaluations × 12s sim each)
**Output**: `results/cmaes_fsm_gains.json` with best parameters and convergence history

### Example 3: Bayesian Optimization (Hardware-Sim Gap)
```powershell
python optimize_bayesian.py --param-space sim_to_real --n-trials 200 --surrogate gp
```
**Expected time**: ~4 hours (200 evaluations with GP overhead)
**Output**: `results/bo_sim_to_real.db` (Optuna study database)

---

## Computational Requirements

| Algorithm | CPU Cores | RAM | Disk | GPU | Training Time (est.) |
|-----------|-----------|-----|------|-----|----------------------|
| PPO       | 8-16      | 16 GB | 50 GB | Recommended (10× faster) | 6-48 hours |
| SAC       | 8-16      | 16 GB | 50 GB | Recommended | 8-60 hours |
| CMA-ES    | 4-8       | 8 GB  | 10 GB | Not used | 5-20 hours |
| BO-GP     | 2-4       | 4 GB  | 5 GB  | Not used | 2-10 hours |
| GA (DEAP) | 4-8       | 8 GB  | 10 GB | Not used | 10-30 hours |

**Notes:**
- RL training can be parallelized with `VecEnv` (multiple simulation environments)
- Evolution strategies are "embarrassingly parallel" (can distribute across nodes)
- Bayesian optimization is inherently sequential (but each evaluation can be parallelized)

---

## How to Interpret Results

### RL Policy Evaluation
After training, evaluate the learned policy:
```powershell
python evaluate_rl_policy.py --model models/ppo_hw1_v137/best_model.zip --episodes 100 --render
```

**Key metrics:**
- **Success rate**: Fraction of episodes achieving ≥10 alternations and ≥0.8 m forward distance
- **Mean reward**: Higher is better (reward function defined in `hw1_gym_env.py`)
- **CoT (Cost of Transport)**: Compare with V12 baseline (CoT_mech ≈ 0.066)
- **Robustness**: Test with domain randomization (±10% mass, ±5% leg length)

**What to look for:**
- Success rate >80% on flat terrain → policy is stable
- CoT <0.05 → energy efficiency improvement
- Graceful degradation under noise → robust to sim-to-real gap

### Evolutionary Algorithm Results
```powershell
python plot_cmaes_history.py --result results/cmaes_fsm_gains.json
```

**Key plots:**
- **Fitness convergence**: Should plateau after 50-100 generations
- **Parameter evolution**: Check if parameters converge to stable values
- **Best individuals**: Replay top 10 gaits to visually inspect quality

**What to look for:**
- Flat fitness plateau → algorithm converged
- Diverse Pareto front (for multi-objective) → good exploration of trade-offs
- Best parameters within hardware constraints (e.g., hip_kp ∈ [15, 45] from V13)

### Bayesian Optimization Output
```powershell
optuna-dashboard sqlite:///results/bo_sim_to_real.db
```
Open browser at `http://localhost:8080` to view interactive dashboard.

**Key insights:**
- **Best trial**: Parameter configuration achieving lowest objective (e.g., -success_rate)
- **Parallel coordinate plot**: Visualize parameter relationships
- **Hyperparameter importance**: Which parameters affect performance most

**What to look for:**
- Clear parameter sensitivities → focus tuning on important dimensions
- Flat regions in optimization landscape → need better reward shaping
- Best trial significantly better than random baseline → BO is effective

---

## Troubleshooting Guide

### Problem: RL training diverges (reward drops to -∞)
**Diagnosis:**
```powershell
tensorboard --logdir algorithm_optimization/logs/
```
Check if value function explodes or policy entropy collapses.

**Solutions:**
- Reduce learning rate: `--learning-rate 1e-5` (default 3e-4)
- Clip value function: `--clip-range-vf 0.2`
- Add action noise: `--action-noise 0.1`
- Simplify reward function: Remove shaping terms, keep only sparse rewards

### Problem: CMA-ES stuck in local minimum
**Symptoms:** Fitness plateau at suboptimal value, low parameter diversity

**Solutions:**
- Increase population size: `--population 50` (default 20)
- Restart with best solution as seed: `--initial-mean results/best_params.json`
- Add penalty for constraint violation (e.g., hip_kp out of hardware range)
- Use multi-start CMA-ES: Run 5-10 independent runs with different seeds

### Problem: Bayesian Optimization suggests physically infeasible parameters
**Examples:** Negative masses, leg length >2 m, hip_kp >1000

**Solutions:**
- Enforce hard constraints in objective function: Return `float('inf')` for invalid configs
- Use constrained BO: `optuna.create_study(sampler=TPESampler(constraints_func=...))`
- Logarithmic scaling for scale-sensitive parameters: Search log10(hip_kp) instead of hip_kp

### Problem: Simulation crashes during optimization
**Error:** `mujoco.FatalError: Pre-allocated contact buffer full`

**Solutions:**
- Reduce `nconmax` in XML model (less aggressive collision detection)
- Catch exceptions and return failure penalty:
```python
try:
    result = run_simulation(params)
except mujoco.FatalError:
    return {"success": False, "reward": -100}
```
- Add timeout: Kill simulations exceeding 30s wall-clock time

### Problem: Optimized controller works in sim but fails on hardware
**Root cause:** Sim-to-real gap (see V24 documentation)

**Solutions:**
- Train with domain randomization: `--domain-rand-mass 0.1 --domain-rand-friction 0.3`
- Use robust reward functions: Penalize jerky motions, large torques
- Validate on V17 sensor noise model before hardware deployment
- Iterative refinement: Hardware → V23 system ID → update sim → retrain → hardware

---

## Integration with hw-1 Project

### Relation to Existing Versions
- **V13.7**: FSM baseline controller → optimization target or initial policy for RL
- **V17**: Sensor noise model → add to RL environment for sim-to-real transfer
- **V22-V24**: Hardware specs → constraints for optimization (torque limits, mass budget)
- **V12**: Energy metrics → CoT as optimization objective

### Recommended Workflow
1. **Baseline reproduction**: Verify V13.7 FSM achieves 10 alternations in your optimization framework
2. **Hyperparameter sweep**: Use BO to tune FSM gains (5-10× faster than V13 grid search)
3. **RL policy learning**: Train PPO/SAC to learn adaptive control beyond FSM
4. **Hardware validation**: Test top 3 policies in V17 sensor noise environment
5. **Deployment**: Transfer best policy to V22 hardware via V24 sim-to-real strategy

### Data Sharing
- **Input**: Reuse V13.7 model XML (`v13_7_refactored/model_v13_7.py`)
- **Output**: Save optimized parameters to `algorithm_optimization/results/`
- **Visualization**: Use `common/plotting.py` for consistent figures across versions

---

## References

### Reinforcement Learning
1. Schulman et al. (2017). "Proximal Policy Optimization Algorithms." arXiv:1707.06347
2. Haarnoja et al. (2018). "Soft Actor-Critic: Off-Policy Maximum Entropy Deep RL." ICML 2018
3. Fujimoto et al. (2018). "Addressing Function Approximation Error in Actor-Critic Methods." ICML 2018

### Evolutionary Algorithms
4. Hansen & Ostermeier (2001). "Completely Derandomized Self-Adaptation in Evolution Strategies." Evolutionary Computation 9(2)
5. Deb et al. (2002). "A Fast and Elitist Multiobjective Genetic Algorithm: NSGA-II." IEEE Trans. Evolutionary Computation 6(2)

### Bayesian Optimization
6. Akiba et al. (2019). "Optuna: A Next-generation Hyperparameter Optimization Framework." KDD 2019
7. Snoek et al. (2012). "Practical Bayesian Optimization of Machine Learning Algorithms." NIPS 2012

### Trajectory Optimization
8. Kelly (2017). "An Introduction to Trajectory Optimization." SIAM Review 59(4)
9. Tassa et al. (2012). "Synthesis and Stabilization of Complex Behaviors through Online Trajectory Optimization." IROS 2012

### Legged Robotics Applications
10. Hwangbo et al. (2019). "Learning Agile and Dynamic Motor Skills for Legged Robots." Science Robotics 4(26)
11. Lee et al. (2020). "Learning Quadrupedal Locomotion over Challenging Terrain." Science Robotics 5(47)
12. Iscen et al. (2018). "Policies Modulating Trajectory Generators." CoRL 2018

---

## Contact and Contribution

This optimization framework is experimental. Key design decisions:
- **Modularity**: Each algorithm in separate script for independent testing
- **Reproducibility**: All hyperparameters exposed as CLI arguments
- **Hardware awareness**: Constraints derived from V22 hardware specs

**Next steps:**
- Implement Gym environment wrapper for V13.7 FSM (`hw1_gym_env.py`)
- Add reward shaping for energy efficiency (CoT penalty)
- Benchmark RL algorithms on V11 terrain robustness suite
- Multi-objective optimization: Pareto front of stability vs. energy vs. speed

---

**Version**: 1.0  
**Last updated**: 2026-06-08  
**Compatible with**: hw-1 V13.7 (FSM baseline), V17 (sensor model), V22-V24 (hardware specs)
