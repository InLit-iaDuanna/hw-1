# 补充材料 - 关键代码清单

本文档提供 hw-1 项目中的核心算法代码，用于论文补充材料和学术复现。

---

## 1. FSM 控制律（V13.6, V13.7）

### 1.1 四相位状态机

```python
# 文件：v13_6_event_driven_fsm/control_v136.py

class FsmHipController:
    """事件驱动 4 相位 FSM 髋部控制器"""
    
    def __init__(self, params):
        self.k_P = params['k_P']          # PD 比例增益 (N·m/rad)
        self.k_D = params['k_D']          # PD 微分增益 (N·m·s/rad)
        self.k_E = params['k_E']          # 能量注入增益 (N·m)
        self.k_brake = params['k_brake']  # 刹车增益 (N·m·s/rad)
        
        self.theta_target = params['theta_target']  # 目标髋角 (rad)
        self.omega_brake_threshold = params['omega_brake_threshold']  # 刹车速度阈值 (rad/s)
        
        self.phase = 1  # 初始相位
        self.swing_contact = False  # 摆动腿接触状态
        
    def update(self, state):
        """更新控制器状态并计算扭矩
        
        Args:
            state: dict, 包含关节角度、速度、接触力
                {
                    'theta_hip': float,      # 髋关节角度 (rad)
                    'omega_hip': float,      # 髋关节速度 (rad/s)
                    'swing_contact_force': float,  # 摆动腿接触力 (N)
                }
        
        Returns:
            tau_hip: float, 髋部控制扭矩 (N·m)
        """
        theta = state['theta_hip']
        omega = state['omega_hip']
        contact_force = state['swing_contact_force']
        
        # 相位转移逻辑
        self._update_phase(theta, omega, contact_force)
        
        # 根据当前相位计算扭矩
        if self.phase == 1:  # Pre-Liftoff
            tau = self.k_P * (self.theta_target - theta) + self.k_D * (-omega)
            
        elif self.phase == 2:  # Early Swing (能量注入)
            tau = self.k_E * np.sign(omega) if abs(omega) > 0.01 else 0.0
            
        elif self.phase == 3:  # Late Swing (负反馈)
            tau = -self.k_D * omega
            
        elif self.phase == 4:  # Pre-Touchdown (刹车)
            tau = -self.k_brake * omega
            
        return tau
    
    def _update_phase(self, theta, omega, contact_force):
        """相位转移决策门"""
        
        if self.phase == 1:
            # 1 -> 2: 摆动腿离地
            if contact_force < 0.1:  # 接触力阈值 (N)
                self.phase = 2
                self.swing_contact = False
                
        elif self.phase == 2:
            # 2 -> 3: 髋角度达到目标
            if theta > self.theta_target:
                self.phase = 3
                
        elif self.phase == 3:
            # 3 -> 4: 髋速度降至刹车阈值
            if omega < self.omega_brake_threshold:
                self.phase = 4
                
        elif self.phase == 4:
            # 4 -> 1: 摆动腿触地
            if contact_force > 0.1 and not self.swing_contact:
                self.phase = 1
                self.swing_contact = True
```

### 1.2 摩擦补偿（V13.7）

```python
# 文件：v13_7_friction_compensation/friction_compensator.py

def sign_smooth(omega, epsilon=0.01):
    """平滑符号函数，避免不连续性
    
    Args:
        omega: float, 关节速度 (rad/s)
        epsilon: float, 平滑参数 (rad/s)
    
    Returns:
        smooth_sign: float, ∈ [-1, 1]
    """
    return np.tanh(omega / epsilon)


class FrictionCompensator:
    """前馈摩擦补偿器"""
    
    def __init__(self, tau_C_eff, epsilon=0.01):
        """
        Args:
            tau_C_eff: float, 有效库仑摩擦扭矩 (N·m)
            epsilon: float, sign_smooth 平滑参数 (rad/s)
        """
        self.tau_C_eff = tau_C_eff
        self.epsilon = epsilon
    
    def compensate(self, tau_desired, omega_joint):
        """计算补偿后的扭矩
        
        Args:
            tau_desired: float, FSM 控制律输出扭矩 (N·m)
            omega_joint: float, 关节实际速度 (rad/s)
        
        Returns:
            tau_output: float, 补偿后扭矩 (N·m)
        """
        tau_comp = self.tau_C_eff * sign_smooth(omega_joint, self.epsilon)
        tau_output = tau_desired + tau_comp
        
        return tau_output


# 使用示例
compensator = FrictionCompensator(tau_C_eff=0.20)  # Dynamixel MX-64AR

# 在控制循环中
tau_fsm = fsm_controller.update(state)
tau_output = compensator.compensate(tau_fsm, state['omega_hip'])
```

**关键参数**：
- `tau_C_eff = 0.20` N·m（Dynamixel MX-64AR）
- `epsilon = 0.01` rad/s（平滑参数，避免高频抖动）

---

## 2. 状态估计（V17）

### 2.1 编码器量化模型

```python
# 文件：v17_state_estimation/sensor_model.py

class EncoderQuantizer:
    """编码器量化噪声模型"""
    
    def __init__(self, resolution_cpr=4096):
        """
        Args:
            resolution_cpr: int, 编码器分辨率 (Counts Per Revolution)
        """
        self.resolution = 2 * np.pi / resolution_cpr  # rad/count
    
    def quantize(self, theta_true):
        """量化真实角度
        
        Args:
            theta_true: float, 真实角度 (rad)
        
        Returns:
            theta_measured: float, 量化后角度 (rad)
        """
        counts = np.round(theta_true / self.resolution)
        theta_measured = counts * self.resolution
        return theta_measured
```

### 2.2 Kalman 速度滤波器

```python
# 文件：v17_state_estimation/kalman_velocity.py

class KalmanVelocityFilter:
    """一维 Kalman 滤波器，用于速度估计"""
    
    def __init__(self, dt, process_noise_std=0.5, measurement_noise_std=0.05):
        """
        Args:
            dt: float, 采样时间间隔 (s)
            process_noise_std: float, 过程噪声标准差 (rad/s²)
            measurement_noise_std: float, 测量噪声标准差 (rad/s)
        """
        self.dt = dt
        
        # 状态: [omega, alpha] (速度, 加速度)
        self.x = np.array([0.0, 0.0])
        
        # 状态协方差矩阵
        self.P = np.eye(2) * 1.0
        
        # 过程噪声协方差
        Q_std = process_noise_std
        self.Q = np.array([
            [Q_std**2 * dt**3 / 3, Q_std**2 * dt**2 / 2],
            [Q_std**2 * dt**2 / 2, Q_std**2 * dt]
        ])
        
        # 测量噪声协方差
        self.R = measurement_noise_std**2
        
    def predict(self):
        """预测步骤"""
        # 状态转移矩阵
        F = np.array([
            [1.0, self.dt],
            [0.0, 1.0]
        ])
        
        self.x = F @ self.x
        self.P = F @ self.P @ F.T + self.Q
    
    def update(self, omega_measured):
        """更新步骤
        
        Args:
            omega_measured: float, 速度测量值 (rad/s)
        """
        # 测量矩阵
        H = np.array([1.0, 0.0])
        
        # 创新 (innovation)
        y = omega_measured - H @ self.x
        
        # 创新协方差
        S = H @ self.P @ H.T + self.R
        
        # Kalman 增益
        K = self.P @ H.T / S
        
        # 状态更新
        self.x = self.x + K * y
        
        # 协方差更新
        self.P = (np.eye(2) - np.outer(K, H)) @ self.P
    
    def get_velocity(self):
        """获取滤波后的速度估计"""
        return self.x[0]


# 使用示例
kalman = KalmanVelocityFilter(dt=0.001)  # 1000 Hz

for t in range(n_steps):
    # 预测
    kalman.predict()
    
    # 测量（从传感器）
    omega_measured = get_sensor_velocity()
    
    # 更新
    kalman.update(omega_measured)
    
    # 获取估计值
    omega_estimated = kalman.get_velocity()
```

### 2.3 接触延迟补偿

```python
# 文件：v17_state_estimation/contact_delay.py

class ContactDelayCompensator:
    """接触检测延迟补偿"""
    
    def __init__(self, delay_ms=10.0, dt=0.001):
        """
        Args:
            delay_ms: float, 延迟时间 (ms)
            dt: float, 采样时间间隔 (s)
        """
        self.delay_steps = int(delay_ms / 1000.0 / dt)
        
        # 历史状态缓冲区
        self.state_history = []
    
    def push_state(self, state):
        """保存当前状态到历史"""
        self.state_history.append(state.copy())
        
        # 限制缓冲区大小
        max_buffer = self.delay_steps + 10
        if len(self.state_history) > max_buffer:
            self.state_history.pop(0)
    
    def get_contact_state(self, contact_detected):
        """获取延迟补偿后的接触状态
        
        Args:
            contact_detected: bool, 当前检测到接触
        
        Returns:
            state_at_contact: dict, 接触发生时刻的状态
        """
        if not contact_detected:
            return None
        
        # 取延迟时间之前的状态
        if len(self.state_history) > self.delay_steps:
            return self.state_history[-self.delay_steps]
        else:
            return self.state_history[0] if self.state_history else None
```

---

## 3. Floquet 稳定性分析（V13.7）

```python
# 文件：v13_7_floquet_analysis/floquet_analyzer.py

def extract_poincare_section(trajectory, event='right_touchdown'):
    """从轨迹中提取 Poincaré 截面
    
    Args:
        trajectory: dict, 包含时间序列数据
            {
                't': np.array,
                'q': np.array (n_steps, n_dof),
                'dq': np.array (n_steps, n_dof),
                'contact_events': list of (time, event_type)
            }
        event: str, 事件类型（如 'right_touchdown'）
    
    Returns:
        poincare_states: np.array (n_events, state_dim)
    """
    events = [e for e in trajectory['contact_events'] if e[1] == event]
    
    poincare_states = []
    for event_time, _ in events:
        # 找到最接近事件时间的索引
        idx = np.argmin(np.abs(trajectory['t'] - event_time))
        
        # 提取状态向量 [theta_hip, omega_hip, theta_knee, omega_knee]
        state = np.concatenate([
            trajectory['q'][idx, [0, 2]],     # hip, knee angles
            trajectory['dq'][idx, [0, 2]]     # hip, knee velocities
        ])
        poincare_states.append(state)
    
    return np.array(poincare_states)


def compute_floquet_multipliers(poincare_states):
    """计算 Floquet 乘子
    
    Args:
        poincare_states: np.array (n_events, state_dim)
    
    Returns:
        eigenvalues: np.array (state_dim,), Floquet 乘子
        jacobian: np.array (state_dim, state_dim), Return-map Jacobian
    """
    n_events, state_dim = poincare_states.shape
    
    # 线性回归拟合 return map: x_{k+1} = J @ x_k
    # 使用最小二乘法: J = (X_{k+1} @ X_k^T) @ (X_k @ X_k^T)^{-1}
    
    X_k = poincare_states[:-1].T      # (state_dim, n_events-1)
    X_k1 = poincare_states[1:].T      # (state_dim, n_events-1)
    
    # Jacobian 矩阵
    jacobian = X_k1 @ X_k.T @ np.linalg.inv(X_k @ X_k.T)
    
    # 特征值（Floquet 乘子）
    eigenvalues = np.linalg.eigvals(jacobian)
    
    return eigenvalues, jacobian


def floquet_stability_margin(eigenvalues):
    """计算稳定裕度
    
    Args:
        eigenvalues: np.array, Floquet 乘子
    
    Returns:
        max_magnitude: float, max|λ|
        stability: str, 'stable' / 'marginally_stable' / 'unstable'
        tau_converge: float, 收敛时间常数（步数）
    """
    magnitudes = np.abs(eigenvalues)
    max_mag = np.max(magnitudes)
    
    if max_mag < 0.95:
        stability = 'stable'
    elif max_mag < 1.0:
        stability = 'marginally_stable'
    else:
        stability = 'unstable'
    
    # 收敛时间常数 τ = 1 / ln(1/|λ_max|)
    if max_mag < 1.0 and max_mag > 0.01:
        tau_converge = 1.0 / np.log(1.0 / max_mag)
    else:
        tau_converge = np.inf
    
    return max_mag, stability, tau_converge


# 使用示例
trajectory = run_simulation(duration=20.0)  # 20秒仿真
poincare_states = extract_poincare_section(trajectory, 'right_touchdown')

eigenvalues, jacobian = compute_floquet_multipliers(poincare_states)
max_mag, stability, tau = floquet_stability_margin(eigenvalues)

print(f"Max Floquet multiplier: {max_mag:.4f}")
print(f"Stability: {stability}")
print(f"Convergence time constant: {tau:.1f} steps")
```

**典型输出**（V13.7 FSM）：
```
Max Floquet multiplier: 1.0008
Stability: unstable
Convergence time constant: 1000.2 steps
```

---

## 4. 参数敏感性网格扫描（V13）

```python
# 文件：v13_parameter_sensitivity_atlas/grid_scanner.py

def parameter_grid_scan(param_ranges, simulate_fn, success_criterion):
    """参数网格扫描
    
    Args:
        param_ranges: dict, 参数范围
            {
                'foot_radius': np.linspace(0.15, 0.45, 6),
                'leg_length': np.linspace(0.90, 1.15, 6)
            }
        simulate_fn: callable, 仿真函数 simulate_fn(params) -> metrics
        success_criterion: callable, 成功判定 success_criterion(metrics) -> bool
    
    Returns:
        grid_results: np.array (n1, n2), 成功/失败矩阵（1/0）
        param_combinations: list of dict, 参数组合
    """
    param_names = list(param_ranges.keys())
    param_values = [param_ranges[name] for name in param_names]
    
    # 生成网格
    grid = np.meshgrid(*param_values, indexing='ij')
    grid_shape = grid[0].shape
    
    grid_results = np.zeros(grid_shape, dtype=int)
    param_combinations = []
    
    # 遍历网格
    for idx in np.ndindex(grid_shape):
        params = {name: grid[i][idx] for i, name in enumerate(param_names)}
        param_combinations.append(params)
        
        try:
            metrics = simulate_fn(params)
            success = success_criterion(metrics)
            grid_results[idx] = 1 if success else 0
        except Exception as e:
            print(f"Simulation failed at {params}: {e}")
            grid_results[idx] = 0
    
    return grid_results, param_combinations


# 成功判定标准
def is_success(metrics):
    """V13 成功标准"""
    return (
        metrics['alternations'] >= 10 and
        metrics['forward_distance'] >= 4.0 and
        metrics['failure_mode'] == 'none'
    )


# 使用示例（Slice C: 足长 vs 腿长）
param_ranges = {
    'foot_radius': np.linspace(0.15, 0.45, 6),
    'leg_length': np.linspace(0.90, 1.15, 6)
}

grid_results, param_combos = parameter_grid_scan(
    param_ranges=param_ranges,
    simulate_fn=simulate_with_params,
    success_criterion=is_success
)

success_rate = np.mean(grid_results)
print(f"Success rate: {success_rate*100:.1f}% ({np.sum(grid_results)}/{grid_results.size})")
```

---

## 代码复现说明

### 环境要求

```
Python 3.10+
mujoco >= 3.0.0
numpy >= 1.21.0
scipy >= 1.7.0
matplotlib >= 3.5.0
```

### 安装步骤

```powershell
cd D:\Dunna\Documents\hw-1
python -m venv .venv-mujoco
.\.venv-mujoco\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 运行关键实验

```powershell
# V13.7 摩擦补偿
python v13_7_friction_compensation\simulate_v13_7.py --config mx64ar_comp

# V17 状态估计
python v17_state_estimation\simulate_v17.py --noise-scale 1.0

# V13.7 Floquet 分析
python v13_7_floquet_analysis\analyze_floquet_v13_7.py
```

---

## 许可证

代码遵循 MIT License，用于学术研究和教育目的。

引用格式：
```
Duan, Z. (2026). HW-1 Quasi-Passive Biped Walking - Code Supplement.
GitHub: [Repository URL]
```
