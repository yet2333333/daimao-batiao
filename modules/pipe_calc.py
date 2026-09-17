# -*- coding: utf-8 -*-
"""
管路流量计算 - 液体 / 压空 / 蒸汽 三种流体
完全复刻原版工具, 算管径 / 算流量 双模式
"""
import math

# ====================== 通用常数 ======================
M_AIR = 0.029      # 空气分子量 kg/mol
M_WATER = 0.018    # 水蒸气分子量 kg/mol
R_GAS = 8.314      # 通用气体常数 J/(mol·K)
RHO_AIR_STD = 1.293   # 标况空气密度 (0°C, 1atm) kg/m³
P_STD = 101325     # 标准压力 Pa
T_STD = 273.15     # 标准温度 K

# 饱和水蒸气表 (温度°C → 压力 MPa) - 简版, 用于蒸汽密度计算
SAT_STEAM_TABLE = {
    100: 0.1013, 110: 0.1433, 120: 0.1985, 130: 0.2701, 140: 0.3613,
    150: 0.4758, 160: 0.6178, 170: 0.7917, 180: 1.0021, 190: 1.2551,
    200: 1.5549, 210: 1.9077, 220: 2.3198, 230: 2.7976, 240: 3.3478,
    250: 3.9772, 260: 4.6937, 270: 5.5050, 280: 6.4165, 290: 7.4357,
    300: 8.5693, 310: 9.8243, 320: 11.207, 330: 12.725, 340: 14.385,
    350: 16.213,
}


def _p_abs_atm(gauge_atm):
    """表压(atm) → 绝压(atm)"""
    return gauge_atm + 1.0


def _p_abs_pa(gauge_atm):
    """表压(atm) → 绝压(Pa)"""
    return _p_abs_atm(gauge_atm) * P_STD


def _t_abs(t_c):
    """温度(°C) → 温度(K)"""
    return t_c + 273.15


# ====================== 液体流量 ======================
def liquid_diameter(flow_m3h, velocity_ms):
    """液体: 已知流量+流速 → 管径 mm"""
    if velocity_ms <= 0:
        return 0
    q = flow_m3h / 3600.0
    d = math.sqrt(4 * q / (math.pi * velocity_ms)) * 1000
    return round(d, 2)


def liquid_flow(diameter_mm, velocity_ms):
    """液体: 已知管径+流速 → 流量 m3/h"""
    if diameter_mm <= 0:
        return 0
    d = diameter_mm / 1000.0
    a = math.pi * d * d / 4
    q = a * velocity_ms * 3600.0
    return round(q, 2)


# ====================== 压空(压缩空气) ======================
def air_density_working(gauge_atm, t_c):
    """压缩空气工况密度 (kg/m³)"""
    p_abs = _p_abs_pa(gauge_atm)
    t_abs = _t_abs(t_c)
    return p_abs * M_AIR / (R_GAS * t_abs)


def air_diameter(flow_nm3min, velocity_ms, gauge_atm, t_c):
    """压缩空气: 已知流量(Nm3/min)+流速+表压+温度 → 管径 mm"""
    if velocity_ms <= 0:
        return 0
    # 标况体积流量 → 质量流量
    rho_working = air_density_working(gauge_atm, t_c)
    m_dot = RHO_AIR_STD * flow_nm3min / 60.0  # kg/s
    # 工作体积流量
    q_working = m_dot / rho_working  # m³/s
    d = math.sqrt(4 * q_working / (math.pi * velocity_ms)) * 1000
    return round(d, 2)


def air_flow(diameter_mm, velocity_ms, gauge_atm, t_c):
    """压缩空气: 已知管径+流速+表压+温度 → 流量 Nm3/min"""
    if diameter_mm <= 0:
        return 0
    d = diameter_mm / 1000.0
    a = math.pi * d * d / 4
    q_working = a * velocity_ms  # m³/s
    rho_working = air_density_working(gauge_atm, t_c)
    m_dot = q_working * rho_working  # kg/s
    flow_nm3min = m_dot / RHO_AIR_STD * 60.0
    return round(flow_nm3min, 2)


# ====================== 蒸汽 ======================
def steam_saturation_pressure_mpa(t_c):
    """查饱和蒸汽压力 (MPa) - 线性插值"""
    if t_c <= 100:
        return 0.1013
    if t_c >= 350:
        return 16.213
    keys = sorted(SAT_STEAM_TABLE.keys())
    for i in range(len(keys)-1):
        if keys[i] <= t_c <= keys[i+1]:
            t1, t2 = keys[i], keys[i+1]
            p1, p2 = SAT_STEAM_TABLE[t1], SAT_STEAM_TABLE[t2]
            return p1 + (p2 - p1) * (t_c - t1) / (t2 - t1)
    return 0.1013


def steam_density(gauge_atm, t_c):
    """蒸汽密度 (kg/m³)
    1. 若表压对应的绝压 ≈ 饱和压力(给定T), 视为饱和蒸汽, 用饱和压力
    2. 否则按理想气体计算
    """
    p_gauge_mpa = gauge_atm * 0.101325  # atm → MPa
    p_sat = steam_saturation_pressure_mpa(t_c)
    p_abs = p_gauge_mpa + 0.101325      # 表压 + 大气压
    # 选较大者 (确保不低估密度)
    p_use = max(p_abs, p_sat)
    t_abs = _t_abs(t_c)
    rho = p_use * 1e6 * M_WATER / (R_GAS * t_abs)
    return round(rho, 3)


def steam_diameter(flow_th, velocity_ms, gauge_atm, t_c):
    """蒸汽: 已知流量(t/h)+流速+表压+温度 → 管径 mm"""
    if velocity_ms <= 0:
        return 0
    rho = steam_density(gauge_atm, t_c)
    m_dot = flow_th * 1000.0 / 3600.0  # t/h → kg/s
    q_working = m_dot / rho  # m³/s
    d = math.sqrt(4 * q_working / (math.pi * velocity_ms)) * 1000
    return round(d, 2)


def steam_flow(diameter_mm, velocity_ms, gauge_atm, t_c):
    """蒸汽: 已知管径+流速+表压+温度 → 流量 t/h"""
    if diameter_mm <= 0:
        return 0
    d = diameter_mm / 1000.0
    a = math.pi * d * d / 4
    q_working = a * velocity_ms
    rho = steam_density(gauge_atm, t_c)
    m_dot = q_working * rho  # kg/s
    flow_th = m_dot * 3600.0 / 1000.0
    return round(flow_th, 2)
