"""
Gymnasium Environment for Compass Gait Walker (V13.7 Model)

This environment wraps the MuJoCo compass gait walker for reinforcement learning.
It supports multiple reward functions and includes realistic physics simulation.
"""

from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import gymnasium as gym
import mujoco
import numpy as np
from gymnasium import spaces


class CompassGaitEnv(gym.Env):
    """
    Gymnasium environment for the compass gait walker with 4 actuators.

    Based on V13.7 friction compensation model with passive arms.

    Action Space:
        Box(4) - Joint torques for [left_hip, left_knee, right_hip, right_knee]
        Range: [-6.0, 6.0] N·m (extended from model's [-4, 4] for exploration)

    Observation Space:
        Box(20) - [joint_angles(6), joint_velocities(6), hip_pos(2), hip_vel(2), contact(4)]
        - joint_angles: [left_hip, left_knee, left_ankle, right_hip, right_knee, right_ankle]
        - joint_velocities: same order as angles
        - hip_pos: [x, z] position of hip in world frame
        - hip_vel: [vx, vz] velocity of hip
        - contact: [left_heel, left_toe, right_heel, right_toe] binary contact states

    Reward Functions:
        - 'forward': Maximize forward velocity
        - 'energy_efficient': Maximize forward velocity while minimizing energy
        - 'limit_cycle': Encourage stable periodic gait
        - 'imitation': Match reference gait trajectory
    """

    metadata = {"render_modes": ["human", "rgb_array"], "render_fps": 50}

    def __init__(
        self,
        model_path: Optional[str] = None,
        reward_type: str = "forward",
        frame_skip: int = 20,
        render_mode: Optional[str] = None,
        reset_noise_scale: float = 0.01,
        fall_height_threshold: float = 0.2,
        max_steps: int = 1000,
    ):
        """
        Initialize the Compass Gait environment.

        Args:
            model_path: Path to MuJoCo XML model file. If None, uses V13.7 default.
            reward_type: Reward function type ('forward', 'energy_efficient', 'limit_cycle', 'imitation')
            frame_skip: Number of simulation steps per environment step (dt = 0.001 * frame_skip)
            render_mode: Render mode ('human' or 'rgb_array')
            reset_noise_scale: Standard deviation of random perturbations on reset
            fall_height_threshold: Hip height threshold for fall detection (meters)
            max_steps: Maximum episode length
        """
        super().__init__()

        # Locate model file
        if model_path is None:
            base_path = Path(__file__).parent.parent
            model_path = (
                base_path
                / "v13_7_friction_compensation"
                / "out"
                / "v13_7_models"
                / "friction_comp_walker.xml"
            )

        self.model_path = str(model_path)
        self.reward_type = reward_type
        self.frame_skip = frame_skip
        self.render_mode = render_mode
        self.reset_noise_scale = reset_noise_scale
        self.fall_height_threshold = fall_height_threshold
        self.max_steps = max_steps

        # Load MuJoCo model
        self.model = mujoco.MjModel.from_xml_path(self.model_path)
        self.data = mujoco.MjData(self.model)

        # Extract important indices
        self._setup_indices()

        # Define action space: 4 joint torques [-6, 6] N·m
        self.action_space = spaces.Box(low=-6.0, high=6.0, shape=(4,), dtype=np.float32)

        # Define observation space: 20-dimensional state
        obs_low = np.array(
            [
                -np.pi,
                0,
                -np.pi / 6,
                -np.pi,
                0,
                -np.pi / 6,  # joint angles (rad)
                -10,
                -10,
                -10,
                -10,
                -10,
                -10,  # joint velocities (rad/s)
                -np.inf,
                0.0,  # hip position x, z
                -10,
                -10,  # hip velocity vx, vz
                0,
                0,
                0,
                0,  # contact states
            ],
            dtype=np.float32,
        )

        obs_high = np.array(
            [
                np.pi,
                np.pi * 70 / 180,
                np.pi / 6,
                np.pi,
                np.pi * 70 / 180,
                np.pi / 6,  # joint angles
                10,
                10,
                10,
                10,
                10,
                10,  # joint velocities
                np.inf,
                2.0,  # hip position
                10,
                10,  # hip velocity
                1,
                1,
                1,
                1,  # contact states
            ],
            dtype=np.float32,
        )

        self.observation_space = spaces.Box(
            low=obs_low, high=obs_high, dtype=np.float32
        )

        # State tracking
        self.steps = 0
        self.last_hip_x = 0.0
        self.cumulative_energy = 0.0

        # For limit cycle reward
        self.gait_phase_history = []
        self.max_history_length = 100

        # For imitation reward (reference trajectory)
        self.reference_trajectory = None

        # Rendering
        self.renderer = None
        if self.render_mode is not None:
            self._setup_renderer()

    def _setup_indices(self):
        """Extract joint, actuator, and sensor indices from model."""
        # Joint indices (exclude hip_x and hip_z which are free slides)
        self.joint_names = [
            "left_hip",
            "left_knee",
            "left_ankle",
            "right_hip",
            "right_knee",
            "right_ankle",
        ]
        self.joint_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_JOINT, name)
            for name in self.joint_names
        ]
        # qpos / qvel addresses for each named joint.
        # NOTE: mj_name2id returns the joint index; the actual slot in qpos/qvel
        # must be looked up via jnt_qposadr / jnt_dofadr. Do NOT hard-code "+2".
        self.joint_qposadr = [
            int(self.model.jnt_qposadr[jid]) for jid in self.joint_ids
        ]
        self.joint_dofadr = [int(self.model.jnt_dofadr[jid]) for jid in self.joint_ids]

        # Actuator indices
        self.actuator_names = [
            "left_hip_muscle",
            "left_knee_stabilizer",
            "right_hip_muscle",
            "right_knee_stabilizer",
        ]
        self.actuator_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_ACTUATOR, name)
            for name in self.actuator_names
        ]

        # Body indices
        self.hip_body_id = mujoco.mj_name2id(
            self.model, mujoco.mjtObj.mjOBJ_BODY, "hip"
        )

        # Site indices for contact detection
        self.contact_site_names = [
            "left_heel_site",
            "left_toe_site",
            "right_heel_site",
            "right_toe_site",
        ]
        self.contact_site_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_SITE, name)
            for name in self.contact_site_names
        ]

        # Geom indices for contact detection (alternative method)
        self.foot_geom_names = ["left_heel", "left_toe", "right_heel", "right_toe"]
        self.foot_geom_ids = [
            mujoco.mj_name2id(self.model, mujoco.mjtObj.mjOBJ_GEOM, name)
            for name in self.foot_geom_names
        ]

    def _setup_renderer(self):
        """Initialize MuJoCo renderer."""
        if self.render_mode == "human":
            from mujoco import viewer

            self.renderer = viewer.launch_passive(self.model, self.data)
        elif self.render_mode == "rgb_array":
            self.renderer = mujoco.Renderer(self.model, height=480, width=640)

    def _get_obs(self) -> np.ndarray:
        """
        Construct observation vector.

        Returns:
            20-dimensional observation array
        """
        # Joint angles (6)
        joint_angles = np.array(
            [self.data.qpos[self.joint_qposadr[i]] for i in range(6)]
        )

        # Joint velocities (6)
        joint_velocities = np.array(
            [self.data.qvel[self.joint_dofadr[i]] for i in range(6)]
        )

        # Hip position (2): x and z
        hip_pos = self.data.xpos[self.hip_body_id][[0, 2]]

        # Hip velocity (2): vx and vz
        hip_vel = self.data.cvel[self.hip_body_id][[3, 5]]  # translational velocity

        # Contact states (4): binary indicator for each foot contact point
        contact_states = self._get_contact_states()

        obs = np.concatenate(
            [joint_angles, joint_velocities, hip_pos, hip_vel, contact_states]
        ).astype(np.float32)

        return obs

    def _get_contact_states(self) -> np.ndarray:
        """
        Detect ground contact for each foot segment.

        Returns:
            Binary array [left_heel, left_toe, right_heel, right_toe]
        """
        contact_states = np.zeros(4, dtype=np.float32)

        # Check all contacts in the simulation
        for i in range(self.data.ncon):
            contact = self.data.contact[i]
            geom1 = contact.geom1
            geom2 = contact.geom2

            # Check if either geom is a foot segment
            for j, foot_geom_id in enumerate(self.foot_geom_ids):
                if geom1 == foot_geom_id or geom2 == foot_geom_id:
                    # Contact detected, check if force magnitude is significant
                    if (
                        np.linalg.norm(contact.frame[:3]) > 0.1
                    ):  # Normal force threshold
                        contact_states[j] = 1.0

        return contact_states

    def _compute_reward(self, action: np.ndarray) -> float:
        """
        Compute reward based on selected reward function.

        Args:
            action: Applied control action

        Returns:
            Scalar reward value
        """
        if self.reward_type == "forward":
            return self._reward_forward()
        elif self.reward_type == "energy_efficient":
            return self._reward_energy_efficient(action)
        elif self.reward_type == "limit_cycle":
            return self._reward_limit_cycle()
        elif self.reward_type == "imitation":
            return self._reward_imitation()
        else:
            raise ValueError(f"Unknown reward type: {self.reward_type}")

    def _reward_forward(self) -> float:
        """
        Forward velocity reward.

        Encourages the walker to move forward quickly while staying upright.
        """
        hip_vel_x = self.data.cvel[self.hip_body_id][3]
        hip_height = self.data.xpos[self.hip_body_id][2]

        # Reward forward velocity
        forward_reward = hip_vel_x

        # Small penalty for deviating from target height
        height_penalty = -0.1 * (hip_height - 1.0) ** 2

        # Alive bonus
        alive_bonus = 1.0

        return forward_reward + height_penalty + alive_bonus

    def _reward_energy_efficient(self, action: np.ndarray) -> float:
        """
        Energy-efficient locomotion reward.

        Maximizes forward velocity while minimizing energy consumption.
        """
        hip_vel_x = self.data.cvel[self.hip_body_id][3]

        # Energy cost: sum of squared torques
        energy_cost = np.sum(action**2)
        self.cumulative_energy += energy_cost

        # Reward: forward velocity minus energy penalty
        forward_reward = 5.0 * hip_vel_x
        energy_penalty = 0.01 * energy_cost

        # Smoothness penalty: discourage abrupt control changes
        if hasattr(self, "last_action"):
            smoothness_penalty = 0.001 * np.sum((action - self.last_action) ** 2)
        else:
            smoothness_penalty = 0.0

        self.last_action = action.copy()

        return forward_reward - energy_penalty - smoothness_penalty

    def _reward_limit_cycle(self) -> float:
        """
        Limit cycle stability reward.

        Encourages the walker to converge to a stable periodic gait pattern.
        """
        hip_vel_x = self.data.cvel[self.hip_body_id][3]

        # Extract gait phase features
        left_hip_angle = self.data.qpos[self.joint_qposadr[0]]
        right_hip_angle = self.data.qpos[self.joint_qposadr[3]]
        left_knee_angle = self.data.qpos[self.joint_qposadr[1]]
        right_knee_angle = self.data.qpos[self.joint_qposadr[4]]

        gait_phase = np.array(
            [left_hip_angle, right_hip_angle, left_knee_angle, right_knee_angle]
        )
        self.gait_phase_history.append(gait_phase)

        # Keep history bounded
        if len(self.gait_phase_history) > self.max_history_length:
            self.gait_phase_history.pop(0)

        # Compute periodicity measure (variance of phase differences)
        periodicity_reward = 0.0
        if len(self.gait_phase_history) > 20:
            history_array = np.array(self.gait_phase_history[-20:])
            # Look for repeating patterns
            phase_variance = np.var(history_array, axis=0).mean()
            periodicity_reward = -0.1 * phase_variance

        # Reward forward velocity
        forward_reward = 3.0 * hip_vel_x

        # Symmetry reward: encourage symmetric gait
        hip_symmetry = -0.5 * abs(left_hip_angle + right_hip_angle)
        knee_symmetry = -0.5 * abs(left_knee_angle - right_knee_angle)

        return forward_reward + periodicity_reward + hip_symmetry + knee_symmetry

    def _reward_imitation(self) -> float:
        """
        Imitation learning reward.

        Encourages the walker to match a reference trajectory.
        This requires reference_trajectory to be set.
        """
        if self.reference_trajectory is None:
            # Fall back to forward reward if no reference available
            return self._reward_forward()

        # Get current state
        current_state = self._get_obs()[:12]  # Joint angles and velocities

        # Get reference state at current timestep
        if self.steps < len(self.reference_trajectory):
            reference_state = self.reference_trajectory[self.steps]

            # Compute tracking error
            tracking_error = np.linalg.norm(current_state - reference_state)
            tracking_reward = -tracking_error
        else:
            tracking_reward = 0.0

        # Also reward forward progress
        hip_vel_x = self.data.cvel[self.hip_body_id][3]
        forward_reward = 2.0 * hip_vel_x

        return tracking_reward + forward_reward

    def _is_terminated(self) -> bool:
        """
        Check if episode should terminate (fall detected).

        Returns:
            True if walker has fallen
        """
        hip_height = self.data.xpos[self.hip_body_id][2]

        # Fall detection: hip too low
        if hip_height < self.fall_height_threshold:
            return True

        # Fall detection: hip tilted too much (check if hip moved too far in y direction)
        hip_y = self.data.xpos[self.hip_body_id][1]
        if abs(hip_y) > 0.5:
            return True

        return False

    def _is_truncated(self) -> bool:
        """
        Check if episode should be truncated (max steps reached).

        Returns:
            True if max steps exceeded
        """
        return self.steps >= self.max_steps

    def reset(
        self, seed: Optional[int] = None, options: Optional[Dict[str, Any]] = None
    ) -> Tuple[np.ndarray, Dict[str, Any]]:
        """
        Reset the environment to initial state with random perturbations.

        Args:
            seed: Random seed for reproducibility
            options: Additional reset options

        Returns:
            observation: Initial observation
            info: Additional information dictionary
        """
        super().reset(seed=seed)

        # Reset MuJoCo simulation
        mujoco.mj_resetData(self.model, self.data)

        # Set initial position: hip at (0, 1.0), standing upright
        self.data.qpos[0] = 0.0  # hip_x (forward position)
        self.data.qpos[1] = (
            1.0  # hip_z (height) - CORRECT: qpos[1] is hip_z based on jnt_qposadr verification
        )

        # Add random perturbations to joint angles
        if self.reset_noise_scale > 0:
            noise = self.np_random.normal(
                0, self.reset_noise_scale, size=len(self.joint_ids)
            )
            for i in range(len(self.joint_ids)):
                self.data.qpos[self.joint_qposadr[i]] += noise[i]

        # Add small random velocities
        if self.reset_noise_scale > 0:
            vel_noise = self.np_random.normal(
                0, self.reset_noise_scale * 0.5, size=len(self.joint_ids)
            )
            for i in range(len(self.joint_ids)):
                self.data.qvel[self.joint_dofadr[i]] = vel_noise[i]

        # Forward dynamics to settle the model
        mujoco.mj_forward(self.model, self.data)

        # Reset tracking variables
        self.steps = 0
        self.last_hip_x = self.data.xpos[self.hip_body_id][0]
        self.cumulative_energy = 0.0
        self.gait_phase_history = []
        if hasattr(self, "last_action"):
            delattr(self, "last_action")

        observation = self._get_obs()
        info = {
            "hip_x": self.last_hip_x,
            "hip_height": self.data.xpos[self.hip_body_id][2],
        }

        return observation, info

    def step(
        self, action: np.ndarray
    ) -> Tuple[np.ndarray, float, bool, bool, Dict[str, Any]]:
        """
        Execute one environment step.

        Args:
            action: 4-dimensional control vector [left_hip, left_knee, right_hip, right_knee]

        Returns:
            observation: New observation
            reward: Reward for this step
            terminated: Whether episode terminated (fall)
            truncated: Whether episode truncated (max steps)
            info: Additional information
        """
        # Clip action to valid range
        action = np.clip(action, self.action_space.low, self.action_space.high)

        # Apply action to actuators
        self.data.ctrl[:] = action

        # Step simulation (frame_skip times)
        for _ in range(self.frame_skip):
            mujoco.mj_step(self.model, self.data)

        # Get new observation
        observation = self._get_obs()

        # Compute reward
        reward = self._compute_reward(action)

        # Check termination conditions
        terminated = self._is_terminated()
        truncated = self._is_truncated()

        # Update step counter
        self.steps += 1

        # Gather info
        hip_x = self.data.xpos[self.hip_body_id][0]
        hip_height = self.data.xpos[self.hip_body_id][2]
        hip_vel_x = self.data.cvel[self.hip_body_id][3]

        info = {
            "hip_x": hip_x,
            "hip_height": hip_height,
            "hip_vel_x": hip_vel_x,
            "distance_traveled": hip_x - self.last_hip_x,
            "cumulative_energy": self.cumulative_energy,
            "steps": self.steps,
        }

        return observation, reward, terminated, truncated, info

    def render(self):
        """Render the environment."""
        if self.render_mode == "human":
            if self.renderer is not None:
                self.renderer.sync()
        elif self.render_mode == "rgb_array":
            if self.renderer is not None:
                self.renderer.update_scene(self.data)
                return self.renderer.render()
        return None

    def close(self):
        """Clean up resources."""
        if self.renderer is not None:
            if self.render_mode == "human":
                self.renderer.close()
            self.renderer = None

    def set_reference_trajectory(self, trajectory: np.ndarray):
        """
        Set reference trajectory for imitation learning.

        Args:
            trajectory: Array of shape (T, 12) containing reference states
        """
        self.reference_trajectory = trajectory


def make_compass_gait_env(**kwargs) -> CompassGaitEnv:
    """
    Factory function to create CompassGaitEnv.

    Args:
        **kwargs: Arguments passed to CompassGaitEnv constructor

    Returns:
        Initialized environment
    """
    return CompassGaitEnv(**kwargs)


# Register environment with Gymnasium
try:
    gym.register(
        id="CompassGait-v0",
        entry_point="environment:CompassGaitEnv",
        max_episode_steps=1000,
        reward_threshold=500.0,
    )
except gym.error.Error:
    # Already registered
    pass
