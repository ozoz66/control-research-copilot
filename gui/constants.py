# -*- coding: utf-8 -*-
"""
GUI 常量定义
包含所有下拉菜单选项和配置常量
"""

# Section A: 主算法域
MAIN_ALGORITHMS = {
    "adaptive": "自适应控制 (Adaptive Control)",
    "ilc": "迭代学习控制 (Iterative Learning Control)",
    "repetitive": "重复控制 (Repetitive Control)",
    "robust": "鲁棒控制 (Robust Control)",
    "mpc": "模型预测控制 (Model Predictive Control)",
    "optimal": "最优控制 (Optimal Control)",
    "neural_network": "神经网络控制 (Neural Network Control)",
    "fuzzy": "模糊控制 (Fuzzy Control)",
    "reinforcement": "强化学习控制 (Reinforcement Learning)",
    "fault_tolerant": "容错控制 (Fault-Tolerant Control)",
    "nonlinear": "非线性控制 (Nonlinear Control)",
    "stochastic": "随机控制 (Stochastic Control)",
    "distributed": "分布式控制 (Distributed Control)",
    "cooperative": "协同控制 (Cooperative Control)",
    "event_triggered": "事件触发控制 (Event-Triggered Control)"
}

# Section B: 性能目标
PERFORMANCE_OBJECTIVES = {
    "chattering_elimination": "消除抖动 (Chattering Elimination)",
    "finite_time": "有限时间收敛 (Finite-time Convergence)",
    "fast_transient": "快速瞬态响应 (Fast Transient Response)",
    "high_precision": "高精度跟踪 (High Precision Tracking)",
    "disturbance_rejection": "扰动抑制 (Disturbance Rejection)",
    "robustness": "鲁棒性增强 (Robustness Enhancement)",
    "energy_saving": "节能优化 (Energy Saving)",
    "overshoot_reduction": "超调抑制 (Overshoot Reduction)",
    "noise_attenuation": "噪声衰减 (Noise Attenuation)",
    "steady_state_error": "稳态误差消除 (Steady-State Error Elimination)",
    "bandwidth_extension": "带宽扩展 (Bandwidth Extension)",
    "stability_margin": "稳定裕度增强 (Stability Margin Enhancement)",
    "anti_windup": "抗积分饱和 (Anti-Windup)",
    "constraint_handling": "约束处理 (Constraint Handling)"
}

# Section C: 复合架构组件
FEEDBACK_CONTROLLERS = {
    "none": "无 (None)",
    "pid": "PID控制器",
    "smc": "滑模控制 (Sliding Mode Control)",
    "backstepping": "反步控制 (Backstepping)",
    "h_infinity": "H∞控制 (H-infinity)",
    "lqr": "线性二次调节器 (LQR)",
    "lqg": "线性二次高斯 (LQG)",
    "pole_placement": "极点配置 (Pole Placement)",
    "passivity_based": "无源性控制 (Passivity-Based)",
    "feedback_linearization": "反馈线性化 (Feedback Linearization)",
    "dynamic_inversion": "动态逆 (Dynamic Inversion)",
    "mu_synthesis": "μ综合 (μ-Synthesis)",
    "gain_scheduling": "增益调度 (Gain Scheduling)"
}

FEEDFORWARD_CONTROLLERS = {
    "none": "无 (None)",
    "zpetc": "零相位误差跟踪 (ZPETC)",
    "inverse_dynamics": "逆动力学 (Inverse Dynamics)",
    "iterative_ff": "迭代前馈 (Iterative Feedforward)",
    "model_based_ff": "基于模型前馈 (Model-Based FF)",
    "preview_control": "预见控制 (Preview Control)",
    "acceleration_ff": "加速度前馈 (Acceleration FF)",
    "friction_compensation": "摩擦补偿 (Friction Compensation)",
    "gravity_compensation": "重力补偿 (Gravity Compensation)",
    "inertia_ff": "惯性前馈 (Inertia Feedforward)"
}

OBSERVERS = {
    "none": "无 (None)",
    "eso": "扩展状态观测器 (ESO)",
    "smo": "滑模观测器 (SMO)",
    "dob": "扰动观测器 (DOB)",
    "kalman": "卡尔曼滤波器 (Kalman Filter)",
    "ekf": "扩展卡尔曼滤波 (EKF)",
    "ukf": "无迹卡尔曼滤波 (UKF)",
    "luenberger": "龙伯格观测器 (Luenberger)",
    "high_gain": "高增益观测器 (High-Gain Observer)",
    "adaptive_observer": "自适应观测器 (Adaptive Observer)",
    "unknown_input": "未知输入观测器 (UIO)",
    "finite_time_observer": "有限时间观测器 (FTO)",
    "neural_observer": "神经网络观测器 (Neural Observer)"
}

# Section D: 应用场景
APPLICATION_SCENARIOS = {
    "none": "无 (通用系统)",
    "servo_motor": "伺服电机控制 (Servo Motor)",
    "robot_manipulator": "机械臂控制 (Robot Manipulator)",
    "quadrotor": "四旋翼无人机 (Quadrotor UAV)",
    "autonomous_vehicle": "自动驾驶车辆 (Autonomous Vehicle)",
    "power_converter": "电力变换器 (Power Converter)",
    "active_suspension": "主动悬架系统 (Active Suspension)",
    "magnetic_levitation": "磁悬浮系统 (Magnetic Levitation)",
    "flexible_manipulator": "柔性机械臂 (Flexible Manipulator)",
    "inverted_pendulum": "倒立摆 (Inverted Pendulum)",
    "ball_beam": "球杆系统 (Ball and Beam)",
    "hvac_system": "暖通空调系统 (HVAC)",
    "chemical_process": "化工过程控制 (Chemical Process)",
    "wind_turbine": "风力发电机 (Wind Turbine)",
    "ship_steering": "船舶航向控制 (Ship Steering)",
    "spacecraft_attitude": "航天器姿态控制 (Spacecraft Attitude)"
}

# 日志颜色配置
LOG_COLORS = {
    "info": "#d4d4d4",      # 灰白色
    "success": "#4ec9b0",   # 青绿色
    "warning": "#dcdcaa",   # 黄色
    "error": "#f14c4c",     # 红色
    "agent": "#569cd6"      # 蓝色
}

# 主题样式配置
THEME_STYLES = {
    "dark": {
        "background": "#1e1e1e",
        "text": "#d4d4d4",
        "border": "#3c3c3c",
        "input_background": "#2d2d2d",
        "button_primary": "#0078d4",
        "button_primary_hover": "#106ebe",
        "button_success": "#4CAF50",
        "button_warning": "#FF9800",
        "button_danger": "#f44336",
    }
}
