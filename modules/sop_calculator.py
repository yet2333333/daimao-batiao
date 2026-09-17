# -*- coding: utf-8 -*-
"""SOP 弹窗计算器 - 纯 tkinter 实现, 无浏览器依赖"""
import tkinter as tk
from tkinter import ttk, scrolledtext
import math


def _center(win, w, h):
    try:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    except: pass


# ====================== 工具函数 ======================
def _make_entry(parent, label, default, unit='', width=10):
    """创建一行带标签的输入框"""
    row = tk.Frame(parent); row.pack(fill='x', pady=1)
    tk.Label(row, text=label, font=('Microsoft YaHei', 9), width=14, anchor='w').pack(side='left')
    e = tk.Entry(row, width=width, font=('Microsoft YaHei', 10))
    e.insert(0, str(default))
    e.pack(side='left', padx=2)
    if unit:
        tk.Label(row, text=unit, font=('Microsoft YaHei', 8), fg='#666').pack(side='left')
    return e


def _make_result(parent, rows=6):
    """创建结果输出文本框"""
    txt = tk.Text(parent, font=('Microsoft YaHei', 10), height=rows, width=50,
                  bg='#F5F7FA', fg='#2C5282', state='disabled')
    txt.pack(fill='x', pady=4)
    return txt


def _set_result(txt, lines):
    txt.config(state='normal')
    txt.delete('1.0', tk.END)
    txt.insert('1.0', '\n'.join(lines))
    txt.config(state='disabled')


# ====================== 液体管道计算 (替代 SOP 管径选择) ======================
def open_liquid_pipe(parent):
    from modules.pipe_calc import liquid_diameter, liquid_flow
    win = tk.Toplevel(parent)
    win.title('💧 液体管路流量计算'); win.attributes('-topmost', True)
    _center(win, 360, 330)
    win.resizable(False, False)

    tk.Label(win, text='💧 液体管道计算', font=('Microsoft YaHei',12,'bold'),
             bg='#E0F7FA', fg='#333', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    tk.Label(f, text='算管径 (Q+v → d)', font=('Microsoft YaHei',9,'bold'), fg='#444').pack(anchor='w')
    e1 = _make_entry(f, '流量 Q', 100, 'm³/h')
    e2 = _make_entry(f, '流速 v', 2.0, 'm/s')

    tk.Label(f, text='算流量 (d+v → Q)', font=('Microsoft YaHei',9,'bold'), fg='#444').pack(anchor='w', pady=(6,0))
    e3 = _make_entry(f, '管径 d', 100, 'mm')
    e4 = _make_entry(f, '流速 v', 2.0, 'm/s')

    res = _make_result(f, 4)

    def calc():
        try:
            d1 = liquid_diameter(float(e1.get()), float(e2.get()))
            q1 = liquid_flow(float(e3.get()), float(e4.get()))
            _set_result(res, [
                f'算管径: d = {d1:.2f} mm',
                f'算流量: Q = {q1:.2f} m³/h',
            ])
        except: _set_result(res, ['输入无效'])

    tk.Button(f, text='计算', command=calc, bg='#00ACC1', fg='white', width=12).pack(pady=4)


# ====================== 泵选型计算 ======================
def open_pump_calc(parent):
    """泵选型计算 V2.1 -- 11种泵型全覆盖"""
    win = tk.Toplevel(parent)
    win.title('\U0001f4a7 泵选型计算 V2.1'); win.attributes('-topmost', True)
    _center(win, 480, 620)
    win.resizable(False, False)

    tk.Label(win, text='\U0001f4a7 泵选型计算 V2.1 \u2014 11种泵型', font=('Microsoft YaHei',12,'bold'),
             bg='#1A365D', fg='white', pady=6).pack(fill='x')

    nb = ttk.Notebook(win); nb.pack(fill='both', expand=True, padx=4, pady=4)

    t1 = tk.Frame(nb, padx=8, pady=6)
    nb.add(t1, text='\u5de5\u827a\u53c2\u6570')

    cb_frame = tk.Frame(t1)
    cb_frame.pack(fill='x', pady=2)
    tk.Label(cb_frame, text='\u6cf5\u578b', font=('Microsoft YaHei',9), width=14, anchor='w').pack(side='left')
    pump_names = ['\u79bb\u5fc3\u6cf5','\u6df7\u6d41\u6cf5','\u8f74\u6d41\u6cf5','\u6e6f\u6da1\u6cf5',
                  '\u6d3b\u585e\u6cf5','\u67f1\u585e\u6cf5','\u9694\u819c\u6cf5',
                  '\u9f7f\u8f6e\u6cf5','\u87ba\u6746\u6cf5','\u6ed1\u7247\u6cf5','\u88d5\u52a8\u6cf5']
    pump_ids = ['centrifugal','mixed','axial','vortex',
                'piston','plunger','diaphragm','gear','screw','vane','peristaltic']
    pump_dict = dict(zip(pump_names, pump_ids))
    pump_var = tk.StringVar(value='\u79bb\u5fc3\u6cf5')
    pump_menu = ttk.Combobox(cb_frame, textvariable=pump_var, values=pump_names,
                              font=('Microsoft YaHei',9), width=18, state='readonly')
    pump_menu.pack(side='left')

    g = 9.81
    e1 = _make_entry(t1, 'Q', 100, 'm\u00b3/h')
    e2 = _make_entry(t1, 'H', 30, 'm / MPa')
    e3 = _make_entry(t1, '\u03c1', 1000, 'kg/m\u00b3')
    e4 = _make_entry(t1, '\u03bc', 1.0, 'cP')
    e5 = _make_entry(t1, 'T', 25, '\u00b0C')
    e6 = _make_entry(t1, 'n', 1450, 'rpm')
    e7 = _make_entry(t1, 'ps', 101.3, 'kPa')
    e8 = _make_entry(t1, 'pv', 2.34, 'kPa')
    e9 = _make_entry(t1, 'Hg', 2, 'm')
    e10 = _make_entry(t1, 'ds', 250, 'mm')
    e11 = _make_entry(t1, 'hfs', 1.5, 'm')
    e12 = _make_entry(t1, 'Ls', 5, 'm')
    e13 = _make_entry(t1, 'z', 3, '')
    e14 = _make_entry(t1, '\u03b7', 0.75, '')
    e15 = _make_entry(t1, '\u03b7v', 0.90, '')
    e16 = _make_entry(t1, 'NPSHr', 3.5, 'm')

    t3 = tk.Frame(nb, padx=8, pady=6)
    nb.add(t3, text='\u8ba1\u7b97\u7ed3\u679c')
    res = _make_result(t3, 18)

    def calc():
        try:
            pump_id = pump_dict.get(pump_var.get(), 'centrifugal')
            Q_m3h = float(e1.get()); Q = Q_m3h / 3600.0
            H = float(e2.get()); rho = float(e3.get())
            mu_cp = float(e4.get()); T = float(e5.get())
            n = float(e6.get()); ps = float(e7.get()); pv = float(e8.get())
            Hg = float(e9.get()); ds_mm = float(e10.get())
            hfs = float(e11.get()); Ls = float(e12.get())
            z = int(e13.get()) if e13.get().strip() else 3
            eta = float(e14.get()); etav = float(e15.get()) if e15.get().strip() else 0.90
            npshr_input = float(e16.get()) if e16.get().strip() else 3.5

            lines = []
            blade = ['centrifugal','mixed','axial','vortex']
            pd = ['piston','plunger','diaphragm']
            rotary = ['gear','screw','vane']

            NPSHa = (ps-pv)*1000/(rho*g) + Hg - hfs
            ds_m = ds_mm/1000.0
            As = math.pi*ds_m*ds_m/4 if ds_m > 0 else 1
            Vs = Q_m3h/3600/As

            nu_cSt = mu_cp*1000/rho if rho > 0 else mu_cp
            need_corr = nu_cSt > 20 and pump_id in blade
            fQ = max(0.6, 1.0 - 2.5e-4*(nu_cSt-20)) if need_corr else 1.0
            fH = max(0.6, 1.0 - 3.5e-4*(nu_cSt-20)) if need_corr else 1.0
            fE = max(0.3, 1.0 - 5.0e-4*(nu_cSt-20)) if need_corr else 1.0
            Qe = Q/fQ if need_corr else Q
            He = H/fH if need_corr else H
            et = eta*fE if need_corr else eta

            names = {'centrifugal':'\u79bb\u5fc3\u6cf5','mixed':'\u6df7\u6d41\u6cf5',
                     'axial':'\u8f74\u6d41\u6cf5','vortex':'\u6e6f\u6da1\u6cf5',
                     'piston':'\u6d3b\u585e\u6cf5','plunger':'\u67f1\u585e\u6cf5',
                     'diaphragm':'\u9694\u819c\u6cf5','gear':'\u9f7f\u8f6e\u6cf5',
                     'screw':'\u87ba\u6746\u6cf5','vane':'\u6ed1\u7247\u6cf5',
                     'peristaltic':'\u88d5\u52a8\u6cf5'}
            lines.append('\u6cf5\u578b: ' + names.get(pump_id, pump_id))

            if pump_id in blade:
                ns = 3.56 * n * math.sqrt(abs(Qe)) / ((abs(He)+0.001)**0.75)
                Phyd = rho*g*Qe*He/1000
                Pshaft = Phyd/et if et > 0 else 0
                mk = 1.25 if Pshaft < 15 else (1.15 if Pshaft < 55 else 1.10)
                Pm = Pshaft*mk/0.93
                npsh_ok = NPSHa >= npshr_input + 0.5
                d_opt = math.sqrt(4*Q/(math.pi*2.0))*1000 if Q > 0 else 0
                lines += ['\U0001f4ca \u53f6\u7247\u6cf5:']
                lines.append('  ns=' + f'{ns:.1f}')
                lines.append('  Phyd=' + f'{Phyd:.2f}' + ' kW')
                lines.append('  Pshaft=' + f'{Pshaft:.2f}' + ' kW')
                lines.append('  Pmotor=' + f'{Pm:.2f}' + ' kW')
                lines.append('  NPSHa=' + f'{NPSHa:.2f}' + ' m ' + ('\u2705' if npsh_ok else '\u26a0\ufe0f'))
                lines.append('  DN' + f'{d_opt:.0f}' + ' (v\u22482m/s)')
                if need_corr:
                    lines.append('  HI\u7c98\u5ea6\u4fee\u6b63: fQ=' + f'{fQ:.3f}' + ' fH=' + f'{fH:.3f}')

            elif pump_id in pd:
                p_Pa = H*1e6
                Qd = Q; Qt = Qd/etav if etav > 0 else 0
                Cv = {1:0.200,2:0.115,3:0.066}.get(z,0.066)
                ha = Ls*Vs*n*Cv/(g*1.4) if g*1.4 > 0 else 0
                hv = 1.5 if pump_id=='diaphragm' else 0
                npsh_pd = NPSHa - ha - hv
                Phyd = p_Pa*Qd/1000
                Pshaft = Phyd/eta if eta > 0 else 0
                Pm = Pshaft*1.25/0.93
                lines += ['\U0001f4ca \u5f80\u590d\u6cf5:']
                lines.append('  Qt=' + f'{Qt*3600:.2f}' + ' m\u00b3/h')
                lines.append('  Phyd=' + f'{Phyd:.2f}' + ' kW')
                lines.append('  Pshaft=' + f'{Pshaft:.2f}' + ' kW')
                lines.append('  Pmotor=' + f'{Pm:.2f}' + ' kW')
                lines.append('  ha=' + f'{ha:.2f}' + ' m')
                lines.append('  NPSHa=' + f'{npsh_pd:.2f}' + ' m ' + ('\u2705' if npsh_pd>=2.5 else '\u26a0\ufe0f'))

            elif pump_id in rotary:
                p_Pa = H*1e6
                Qd = Q; Qt = Qd/etav if etav > 0 else 0
                Phyd = p_Pa*Qd/1000
                Pshaft = Phyd/eta if eta > 0 else 0
                Pm = Pshaft*1.25/0.93
                lines += ['\U0001f4ca \u65cb\u8f6c\u6cf5:']
                lines.append('  Qt=' + f'{Qt*3600:.2f}' + ' m\u00b3/h')
                lines.append('  Phyd=' + f'{Phyd:.2f}' + ' kW')
                lines.append('  Pshaft=' + f'{Pshaft:.2f}' + ' kW')
                lines.append('  Pmotor=' + f'{Pm:.2f}' + ' kW')

            elif pump_id == 'peristaltic':
                dt = 8/1000; dr = 80/1000
                Qtm = math.pi**2*dr*dt**2*n/(4*60)
                Qt_h = Qtm*3600
                p_Pa = H*1e6
                Phyd = p_Pa*Q/1000
                Pshaft = Phyd/eta if eta>0 else 0
                Pm = Pshaft*1.25/0.90
                lines += ['\U0001f4ca \u88d5\u52a8\u6cf5:']
                lines.append('  Qt=' + f'{Qt_h:.2f}' + ' m\u00b3/h')
                lines.append('  Phyd=' + f'{Phyd:.2f}' + ' kW')
                lines.append('  Pshaft=' + f'{Pshaft:.2f}' + ' kW')
                lines.append('  Pmotor=' + f'{Pm:.2f}' + ' kW')

            lines.append('')
            if NPSHa < 3: lines.append('\u26a0\ufe0f NPSHa<3m')
            lines.append(names.get(pump_id, pump_id))

            _set_result(res, lines)

        except Exception as ex:
            _set_result(res, ['\u9519\u8bef: ' + str(ex)])

    tk.Button(win, text='\U0001f9ee \u8ba1\u7b97', command=calc, bg='#2B6CB0', fg='white',
              font=('Microsoft YaHei', 10, 'bold'), width=15).pack(pady=(0, 8))


# ====================== 管道阻力计算 ======================
def open_pipe_resistance(parent):
    win = tk.Toplevel(parent)
    win.title('🔧 管道阻力计算'); win.attributes('-topmost', True)
    _center(win, 400, 420)
    win.resizable(False, False)

    tk.Label(win, text='🔧 管道阻力计算', font=('Microsoft YaHei',12,'bold'),
             bg='#922B21', fg='white', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    e1 = _make_entry(f, '流量 Q', 100, 'm³/h')
    e2 = _make_entry(f, '管径 d', 100, 'mm')
    e3 = _make_entry(f, '管长 L', 100, 'm')
    e4 = _make_entry(f, '密度 ρ', 1000, 'kg/m³')
    e5 = _make_entry(f, '粘度 μ', 1.0, 'cP')
    e6 = _make_entry(f, '粗糙度 ε', 0.046, 'mm')

    res = _make_result(f, 8)

    def calc():
        try:
            Q = float(e1.get())/3600.0
            d = float(e2.get())/1000.0
            L = float(e3.get())
            rho = float(e4.get())
            mu = float(e5.get())/1000.0
            rough = float(e6.get())/1000.0

            v = Q / (math.pi*d*d/4)
            Re = rho*v*d/mu if mu > 0 else 0

            # 摩擦系数 (Colebrook)
            if Re < 2100:
                f_fric = 64/Re
                flow_type = '层流'
            else:
                f_fric = 0.3164/(Re**0.25) if Re < 100000 else \
                    0.25/(math.log10(rough/d/3.7 + 5.74/Re**0.9))**2
                flow_type = '湍流'

            dp = f_fric * (L/d) * (rho*v*v/2) / 1000  # kPa

            _set_result(res, [
                f'流速: {v:.2f} m/s',
                f'雷诺数: {Re:,.0f} ({flow_type})',
                f'摩擦系数: {f_fric:.5f}',
                f'压力降: {dp:.2f} kPa',
                f'压力降: {dp*0.102:.2f} m液柱',
            ])
        except Exception as ex:
            _set_result(res, [f'错误: {ex}'])

    tk.Button(f, text='计算', command=calc, bg='#922B21', fg='white', width=12).pack(pady=4)


# ====================== 风机选型 ======================
def open_fan_calc(parent):
    win = tk.Toplevel(parent)
    win.title('🌪️ 风机选型计算'); win.attributes('-topmost', True)
    _center(win, 400, 400)
    win.resizable(False, False)

    tk.Label(win, text='🌪️ 风机选型计算', font=('Microsoft YaHei',12,'bold'),
             bg='#1A5276', fg='white', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    e1 = _make_entry(f, '流量 Q', 5000, 'm³/h')
    e2 = _make_entry(f, '全压 P', 2000, 'Pa')
    e3 = _make_entry(f, '温度 T', 20, '°C')
    e4 = _make_entry(f, '海拔', 0, 'm')
    e5 = _make_entry(f, '效率 η', 0.75, '')

    res = _make_result(f, 8)

    def calc():
        try:
            Q = float(e1.get())/3600.0
            P = float(e2.get())
            T = float(e3.get())+273.15
            alt = float(e4.get())
            eta = float(e5.get())

            # 海拔修正大气压
            Patm = 101325 * math.exp(-alt/8400)
            rho = Patm * 0.029 / (8.314 * T)  # 理想气体

            # 轴功率
            Pshaft = Q * P / eta / 1000  # kW
            # 推荐电机功率 (裕度)
            Pmotor = Pshaft * 1.15

            _set_result(res, [
                f'工况密度: {rho:.3f} kg/m³',
                f'海拔气压: {Patm/1000:.1f} kPa',
                f'轴功率: {Pshaft:.2f} kW',
                f'电机功率: {Pmotor:.2f} kW (含15%裕度)',
            ])
        except Exception as ex:
            _set_result(res, [f'错误: {ex}'])

    tk.Button(f, text='计算', command=calc, bg='#1A5276', fg='white', width=12).pack(pady=4)


# ====================== 搅拌系统 ======================
def open_mixer_calc(parent):
    win = tk.Toplevel(parent)
    win.title('🔄 搅拌系统设计计算'); win.attributes('-topmost', True)
    _center(win, 400, 450)
    win.resizable(False, False)

    tk.Label(win, text='🔄 搅拌系统设计', font=('Microsoft YaHei',12,'bold'),
             bg='#7D3C98', fg='white', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    e1 = _make_entry(f, '罐径 Dt', 2000, 'mm')
    e2 = _make_entry(f, '桨径 Dj', 800, 'mm')
    e3 = _make_entry(f, '转速 N', 100, 'rpm')
    e4 = _make_entry(f, '密度 ρ', 1000, 'kg/m³')
    e5 = _make_entry(f, '粘度 μ', 100, 'cP')
    e6 = _make_entry(f, '功率准数 Np', 5.0, '')

    res = _make_result(f, 10)

    def calc():
        try:
            Dt = float(e1.get())/1000.0
            Dj = float(e2.get())/1000.0
            N = float(e3.get())/60.0  # rps
            rho = float(e4.get())
            mu = float(e5.get())/1000.0
            Np = float(e6.get())

            Re = rho * N * Dj**2 / mu
            if Re < 10:
                flow_type = '层流'
                P = Np * mu * (N**2) * (Dj**3) * \
                    (1 if Re == 0 else 10/Re)
            else:
                flow_type = '湍流' if Re > 10000 else '过渡'
                P = Np * rho * (N**3) * (Dj**5)

            # 单位换算 W → kW
            P_kW = P / 1000
            # 搅拌时间估计
            theta = 36 * (Re/10)**0.17 if Re > 10 else 120

            _set_result(res, [
                f'雷诺数 Re: {Re:,.0f}',
                f'流型: {flow_type}',
                f'搅拌功率: {P_kW:.2f} kW',
                f'单位体积功率: {P_kW/(math.pi*Dt**3/4):.2f} kW/m³',
                f'估计混合时间: {theta:.1f} s',
            ])
        except Exception as ex:
            _set_result(res, [f'错误: {ex}'])

    tk.Button(f, text='计算', command=calc, bg='#7D3C98', fg='white', width=12).pack(pady=4)


# ====================== 真空泵 ======================
def open_vacuum_calc(parent):
    win = tk.Toplevel(parent)
    win.title('🌀 真空泵选型计算'); win.attributes('-topmost', True)
    _center(win, 400, 380)
    win.resizable(False, False)

    tk.Label(win, text='🌀 真空泵选型计算', font=('Microsoft YaHei',12,'bold'),
             bg='#B9770E', fg='white', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    e1 = _make_entry(f, '容器容积 V', 5, 'm³')
    e2 = _make_entry(f, '起始压力 p1', 101.3, 'kPa')
    e3 = _make_entry(f, '目标压力 p2', 5, 'kPa')
    e4 = _make_entry(f, '抽气时间 t', 30, 'min')
    e5 = _make_entry(f, '极限压力 p_ult', 0.5, 'kPa')

    res = _make_result(f, 8)

    def calc():
        try:
            V = float(e1.get())
            p1 = float(e2.get())
            p2 = float(e3.get())
            t = float(e4.get())
            p_ult = float(e5.get())

            S = V / t * math.log((p1-p_ult)/(p2-p_ult))  # m³/min

            _set_result(res, [
                f'所需抽速: {S:.2f} m³/min',
                f'所需抽速: {S*60:.1f} m³/h',
                f'推荐: '
                + ('水环真空泵' if S < 30 else
                   '旋片真空泵' if S < 100 else
                   '罗茨真空泵机组'),
            ])
        except Exception as ex:
            _set_result(res, [f'错误: {ex}'])

    tk.Button(f, text='计算', command=calc, bg='#B9770E', fg='white', width=12).pack(pady=4)


# ====================== 泄放计算 ======================
def open_relief_calc(parent):
    win = tk.Toplevel(parent)
    win.title('⚠️ 安全阀泄放计算 (API 520)'); win.attributes('-topmost', True)
    _center(win, 440, 520)
    win.resizable(False, False)

    tk.Label(win, text='⚠️ 安全阀泄放计算 API 520', font=('Microsoft YaHei',12,'bold'),
             bg='#C0392B', fg='white', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    e1 = _make_entry(f, '泄放流量 W', 5000, 'kg/h')
    e2 = _make_entry(f, '泄放压力 P1', 1.0, 'MPaG')
    e3 = _make_entry(f, '泄放温度 T', 150, '°C')
    e4 = _make_entry(f, '分子量 M', 29, '')
    e5 = _make_entry(f, '压缩因子 Z', 1.0, '')
    e6 = _make_entry(f, 'k=Cp/Cv', 1.4, '')
    e7 = _make_entry(f, 'Kd 排量系数', 0.975, '')
    e8 = _make_entry(f, 'Kb 背压修正', 1.0, '(≤10%背压=1.0)')
    e9 = _make_entry(f, 'Kc 组合修正', 1.0, '(有爆破片=0.9)')

    res = _make_result(f, 10)

    def calc():
        try:
            W = float(e1.get())  # kg/h
            P1 = (float(e2.get())+0.1013)*1000  # kPa abs (API 520 用kPa)
            T = float(e3.get())+273.15
            M = float(e4.get())
            Z = float(e5.get())
            k = float(e6.get())
            Kd = float(e7.get())
            Kb = float(e8.get())
            Kc = float(e9.get())

            # API 520 Section 3.6.2 - 气体临界流
            C = 520 * math.sqrt(k * (2/(k+1))**((k+1)/(k-1)))
            # A(mm²) = 13160 × W / (C × Kd × Kb × Kc × P1) × √(T×Z/M)
            A = 13160 * W / (C * Kd * Kb * Kc * P1) * math.sqrt(T*Z/M)

            d = math.sqrt(4*A/math.pi)

            # API 526 标准喉径
            api526 = [(9.5,20),(19.6,25),(32.4,32),(51.6,40),(82.4,50),(119,52),
                      (200,60),(324,72),(507,81),(781,96),(1130,102)]
            rec_orifice = 'F'
            for area, diam in api526:
                if A <= area:
                    rec_orifice = f'{diam}mm (≤{area}mm²)'
                    break
            else:
                rec_orifice = '超过标准范围, 需定制'

            _set_result(res, [
                f'{"="*35}',
                f'API 520 泄放面积计算',
                f'{"="*35}',
                f'C 系数: {C:.2f}',
                f'Kd={Kd}  Kb={Kb}  Kc={Kc}',
                f'泄放面积 A: {A:.2f} mm²',
                f'喉部直径 d: {d:.2f} mm',
                f'API 526孔口: {rec_orifice}',
                f'{"="*35}',
            ])
        except Exception as ex:
            _set_result(res, [f'错误: {ex}'])

    tk.Button(f, text='计算 (API 520)', command=calc, bg='#C0392B', fg='white', width=14).pack(pady=4)


# ====================== 分布器计算 ======================
def open_distributor_calc(parent):
    win = tk.Toplevel(parent)
    win.title('💦 分布器计算'); win.attributes('-topmost', True)
    _center(win, 400, 400)
    win.resizable(False, False)

    tk.Label(win, text='💦 液体分布器计算', font=('Microsoft YaHei',12,'bold'),
             bg='#148F77', fg='white', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    e1 = _make_entry(f, '液体流量 L', 10, 'm³/h')
    e2 = _make_entry(f, '塔径 D', 1000, 'mm')
    e3 = _make_entry(f, '开孔数 n', 50, '')
    e4 = _make_entry(f, '液层高度 hL', 50, 'mm')
    e5 = _make_entry(f, '密度 ρ', 1000, 'kg/m³')

    res = _make_result(f, 8)

    def calc():
        try:
            L = float(e1.get())
            D = float(e2.get())/1000.0
            n = float(e3.get())
            hL = float(e4.get())
            rho = float(e5.get())

            Q = L/3600.0  # m³/s
            # 孔速 (假设孔口径8mm)
            d_hole = 8  # mm
            A_hole = math.pi * (d_hole/1000)**2 / 4
            v_hole = Q / (n * A_hole)

            # 流量系数 FRI
            To = d_hole / 25.4  # inch
            Do = d_hole  # mm
            if Do >= 12.7:
                C = (0.863 - 0.035*math.log(hL)) * (1.027 - 0.078*((To-2.108)/2.108)**2)
            else:
                C = 0.7

            # 喷淋密度
            spray = L / (math.pi*D**2/4)

            _set_result(res, [
                f'孔速: {v_hole:.2f} m/s',
                f'流量系数 C: {C:.3f}',
                f'喷淋密度: {spray:.2f} m³/m²·h',
                f'总开孔面积: {n*A_hole*1e6:.0f} mm²',
            ])
        except Exception as ex:
            _set_result(res, [f'错误: {ex}'])

    tk.Button(f, text='计算', command=calc, bg='#148F77', fg='white', width=12).pack(pady=4)


# ====================== 容器选型 ======================
def open_vessel_calc(parent):
    win = tk.Toplevel(parent)
    win.title('📦 容器选型计算'); win.attributes('-topmost', True)
    _center(win, 400, 380)
    win.resizable(False, False)

    tk.Label(win, text='📦 容器选型计算', font=('Microsoft YaHei',12,'bold'),
             bg='#2E86C1', fg='white', pady=6).pack(fill='x')

    f = tk.Frame(win, padx=10, pady=6); f.pack(fill='both', expand=True)

    e1 = _make_entry(f, '容积 V', 10, 'm³')
    e2 = _make_entry(f, '设计压力 P', 1.0, 'MPa')
    e3 = _make_entry(f, '设计温度 T', 150, '°C')
    e4 = _make_entry(f, '许用应力 S', 118, 'MPa')
    e5 = _make_entry(f, '腐蚀裕量 C', 2, 'mm')

    res = _make_result(f, 8)

    def calc():
        try:
            V = float(e1.get())
            P = float(e2.get())
            T = float(e3.get())
            S = float(e4.get())
            C = float(e5.get())

            # 假设 L/D = 3 的卧式容器
            L_D = 3
            D = (4*V/(math.pi*L_D))**(1/3) * 1000  # mm
            L = D * L_D

            # 壁厚 (GB 150)
            t = (P * D) / (2 * S * 0.85 - P) + C

            _set_result(res, [
                f'内径 D: {D:.0f} mm',
                f'筒长 L: {L:.0f} mm',
                f'L/D: {L_D:.1f}',
                f'壁厚 t: {t:.1f} mm',
                f'推荐: 卧式容器',
            ])
        except Exception as ex:
            _set_result(res, [f'错误: {ex}'])

    tk.Button(f, text='计算', command=calc, bg='#2E86C1', fg='white', width=12).pack(pady=4)


# ====================== 主窗口列表 ======================
CALCULATORS = [
    ('💧 泵选型计算', open_pump_calc, '流量、扬程、功率、NPSH、比转速'),
    ('💧 液体管路计算', open_liquid_pipe, '管径/流速/流量互算'),
    ('🔧 管道阻力', open_pipe_resistance, '流速、雷诺数、压降'),
    ('🌪️ 风机选型', open_fan_calc, '风量、风压、功率、海拔修正'),
    ('🔄 搅拌系统', open_mixer_calc, '搅拌功率、雷诺数、混合时间'),
    ('🌀 真空泵', open_vacuum_calc, '抽速、抽气时间、泵型推荐'),
    ('⚠️ 安全泄放', open_relief_calc, '泄放面积、喉径、API 520'),
    ('💦 分布器', open_distributor_calc, '孔速、流量系数、喷淋密度'),
    ('📦 容器选型', open_vessel_calc, '筒体尺寸、壁厚、GB 150'),
]


def open_sop_calculator(parent):
    """替代原 SOP 对话框, 弹出一个计算器列表"""
    win = tk.Toplevel(parent)
    win.title('📐 计算器工具集'); win.attributes('-topmost', True)
    _center(win, 420, 480)
    win.resizable(False, False)

    tk.Label(win, text='📐 化工计算工具集', font=('Microsoft YaHei', 12, 'bold'),
             bg='#8E44AD', fg='white', pady=6).pack(fill='x')

    tk.Label(win, text='点击打开计算器弹窗', font=('Microsoft YaHei', 9),
             fg='#888').pack(anchor='w', padx=10, pady=(4, 0))

    lf = tk.Frame(win); lf.pack(fill='both', expand=True, padx=8, pady=4)
    canvas = tk.Canvas(lf, highlightthickness=0)
    sb = tk.Scrollbar(lf, orient='vertical', command=canvas.yview)
    sf = tk.Frame(canvas)
    sf.bind('<Configure>', lambda e: canvas.configure(scrollregion=canvas.bbox('all')))
    canvas.create_window((0, 0), window=sf, anchor='nw', width=380)
    canvas.configure(yscrollcommand=sb.set)
    canvas.pack(side='left', fill='both', expand=True)
    sb.pack(side='right', fill='y')

    for name, func, desc in CALCULATORS:
        fp = tk.Frame(sf, bg='#F5F7FA', bd=1, relief='solid')
        fp.pack(fill='x', padx=4, pady=3)

        btn = tk.Button(fp, text=name, font=('Microsoft YaHei', 11, 'bold'),
                        command=lambda f=func: f(parent),
                        bg='#8E44AD', fg='white', anchor='w', padx=8,
                        relief='flat', cursor='hand2')
        btn.pack(fill='x')

        tk.Label(fp, text=desc, font=('Microsoft YaHei', 8), fg='#666',
                 bg='#F5F7FA', anchor='w').pack(fill='x', padx=8, pady=(0, 3))

    tk.Button(win, text='关闭', command=win.destroy, bg='#DDD', width=10).pack(pady=(0, 8))
