# -*- coding: utf-8 -*-
"""管路流量综合计算 - 液体/压空/蒸汽"""
import tkinter as tk
from modules.pipe_calc import (
    liquid_diameter, liquid_flow,
    air_diameter, air_flow,
    steam_diameter, steam_flow
)


class PipeCalcDialog:
    def __init__(self, parent):
        self.win = tk.Toplevel(parent)
        self.win.title('管路流量')
        self.win.attributes('-topmost', True)
        self.win.config(bg='#F5F5F5')

        # 加宽到 1100 px 容下两个算模式
        try:
            sw = parent.winfo_screenwidth()
            sh = parent.winfo_screenheight()
            self.win.geometry(f'1100x900+{(sw-1100)//2}+{(sh-900)//2}')
        except: pass

        self.win.resizable(False, False)

        tk.Label(self.win, text='管路流量综合计算', font=('Microsoft YaHei', 14, 'bold'),
                 bg='#8E44AD', fg='white', pady=8).pack(fill='x')

        body = tk.Frame(self.win, bg='#F5F5F5')
        body.pack(fill='both', expand=True, padx=8, pady=4)

        # 3 个画板纵向堆叠, 每个全宽, 内部分两侧
        self._build_liquid_panel(body)
        self._build_air_panel(body)
        self._build_steam_panel(body)

        tk.Button(self.win, text='关闭', command=self.win.destroy,
                  bg='#555', fg='white', width=12,
                  font=('Microsoft YaHei', 10)).pack(pady=6)

    def _panel(self, parent, color, title, side):
        f = tk.Frame(parent, bg=color, bd=2, relief='ridge')
        f.pack(side=side, fill='both', expand=True, padx=4)
        tk.Label(f, text=title, font=('Microsoft YaHei', 12, 'bold'),
                 bg=color, fg='#333').pack(pady=(8, 4))
        return f

    def _entry(self, parent, label, default, unit, color):
        row = tk.Frame(parent, bg=color)
        row.pack(fill='x', padx=20, pady=2)
        tk.Label(row, text=label, width=8, bg=color, font=('Microsoft YaHei', 9)).pack(side='left')
        e = tk.Entry(row, width=12, font=('Microsoft YaHei', 10), justify='center')
        e.insert(0, str(default))
        e.pack(side='left', padx=2)
        tk.Label(row, text=unit, width=8, bg=color, font=('Microsoft YaHei', 9)).pack(side='left')
        return e

    def _result_label(self, parent, color):
        r = tk.Frame(parent, bg=color)
        r.pack(fill='x', padx=20, pady=2)
        tk.Label(r, text='', width=14, bg=color, font=('Microsoft YaHei', 11, 'bold'),
                 fg='#000').pack(side='left', padx=2)
        tk.Label(r, text='', width=8, bg=color, font=('Microsoft YaHei', 9)).pack(side='left')
        return r

    def _calc_button(self, parent, text, command, color):
        tk.Button(parent, text=text, command=command, bg=color,
                  font=('Microsoft YaHei', 9, 'bold'), width=10).pack(pady=8)

    # ----- 液体 -----
    def _build_liquid_panel(self, parent):
        f = tk.Frame(parent, bg='#D6F5F5', bd=2, relief='ridge')
        f.pack(side='top', fill='x', expand=False, pady=4)
        tk.Label(f, text='液体流量 计算', font=('Microsoft YaHei', 12, 'bold'),
                 bg='#D6F5F5', fg='#333').pack(pady=(8, 4))
        body = tk.Frame(f, bg='#D6F5F5')
        body.pack(fill='x', padx=4, pady=4)
        # 左:算管径 Q+V→d
        left = tk.Frame(body, bg='#D6F5F5')
        left.pack(side='left', fill='x', expand=True, padx=4, pady=4)
        right = tk.Frame(body, bg='#D6F5F5')
        right.pack(side='left', fill='x', expand=True, padx=4, pady=4)
        # 左:算管径 Q+V→d
        self.liq_flow_e = self._entry(left, '流量', 100.0, 'm3/h', '#D6F5F5')
        self.liq_vel_e = self._entry(left, '流速', 2.0, 'm/s', '#D6F5F5')
        self.liq_d_frame = tk.Frame(left, bg='#D6F5F5')
        self.liq_d_frame.pack(fill='x', padx=20, pady=2)
        self.liq_d_val = tk.Label(self.liq_d_frame, text='', width=14, bg='#D6F5F5',
                                  font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.liq_d_val.pack(side='left', padx=2)
        tk.Label(self.liq_d_frame, text='mm', width=8, bg='#D6F5F5',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        self._calc_button(left, '计算管径', self._calc_liq_d, '#A8E6E6')
        # 右:算流量 D+V→Q
        self.liq_d_e = self._entry(right, '管径', 100.0, 'mm', '#D6F5F5')
        self.liq_vel2_e = self._entry(right, '流速', 2.0, 'm/s', '#D6F5F5')
        self.liq_q_frame = tk.Frame(right, bg='#D6F5F5')
        self.liq_q_frame.pack(fill='x', padx=20, pady=2)
        self.liq_q_val = tk.Label(self.liq_q_frame, text='', width=14, bg='#D6F5F5',
                                  font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.liq_q_val.pack(side='left', padx=2)
        tk.Label(self.liq_q_frame, text='m3/h', width=8, bg='#D6F5F5',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        self._calc_button(right, '计算流量', self._calc_liq_q, '#A8E6E6')

    def _calc_liq_d(self):
        try:
            q = float(self.liq_flow_e.get())
            v = float(self.liq_vel_e.get())
            d = liquid_diameter(q, v)
            self.liq_d_val.config(text=f'{d:.2f}')
        except Exception as e:
            self.liq_d_val.config(text=f'错误:{e}')

    def _calc_liq_q(self):
        try:
            d = float(self.liq_d_e.get())
            v = float(self.liq_vel2_e.get())
            q = liquid_flow(d, v)
            self.liq_q_val.config(text=f'{q:.2f}')
        except Exception as e:
            self.liq_q_val.config(text=f'错误:{e}')

    # ----- 压空 -----
    def _build_air_panel(self, parent):
        f = tk.Frame(parent, bg='#FFFACD', bd=2, relief='ridge')
        f.pack(side='top', fill='x', expand=False, pady=4)
        tk.Label(f, text='压空流量 计算', font=('Microsoft YaHei', 12, 'bold'),
                 bg='#FFFACD', fg='#333').pack(pady=(8, 4))
        body = tk.Frame(f, bg='#FFFACD')
        body.pack(fill='x', padx=4, pady=4)
        left = tk.Frame(body, bg='#FFFACD')
        left.pack(side='left', fill='x', expand=True, padx=4, pady=4)
        right = tk.Frame(body, bg='#FFFACD')
        right.pack(side='left', fill='x', expand=True, padx=4, pady=4)
        self.air_q_e = self._entry(left, '流量', 2.0, 'Nm3/min', '#FFFACD')
        self.air_p_e = self._entry(left, '表压', 2.0, 'atm', '#FFFACD')
        self.air_v_e = self._entry(left, '压力下流速', 10.0, 'm/s', '#FFFACD')
        self.air_t_e = self._entry(left, '温度', 25.0, '°C', '#FFFACD')
        self.air_d_frame = tk.Frame(left, bg='#FFFACD')
        self.air_d_frame.pack(fill='x', padx=20, pady=2)
        self.air_d_val = tk.Label(self.air_d_frame, text='', width=14, bg='#FFFACD',
                                  font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.air_d_val.pack(side='left', padx=2)
        tk.Label(self.air_d_frame, text='mm', width=8, bg='#FFFACD',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        self._calc_button(left, '计算管径', self._calc_air_d, '#FFEC8B')

        self.air_d2_e = self._entry(right, '管径', 65.0, 'mm', '#FFFACD')
        self.air_p2_e = self._entry(right, '表压', 8.0, 'atm', '#FFFACD')
        self.air_v2_e = self._entry(right, '压力下流速', 10.0, 'm/s', '#FFFACD')
        self.air_t2_e = self._entry(right, '温度', 25.0, '°C', '#FFFACD')
        self.air_q_frame = tk.Frame(right, bg='#FFFACD')
        self.air_q_frame.pack(fill='x', padx=20, pady=2)
        self.air_q_val = tk.Label(self.air_q_frame, text='', width=14, bg='#FFFACD',
                                  font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.air_q_val.pack(side='left', padx=2)
        tk.Label(self.air_q_frame, text='Nm3/min', width=8, bg='#FFFACD',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        self._calc_button(right, '计算流量', self._calc_air_q, '#FFEC8B')

    def _calc_air_d(self):
        try:
            q = float(self.air_q_e.get())
            p = float(self.air_p_e.get())
            v = float(self.air_v_e.get())
            t = float(self.air_t_e.get())
            d = air_diameter(q, v, p, t)
            self.air_d_val.config(text=f'{d:.2f}')
        except Exception as e:
            self.air_d_val.config(text=f'错误:{e}')

    def _calc_air_q(self):
        try:
            d = float(self.air_d2_e.get())
            p = float(self.air_p2_e.get())
            v = float(self.air_v2_e.get())
            t = float(self.air_t2_e.get())
            q = air_flow(d, v, p, t)
            self.air_q_val.config(text=f'{q:.2f}')
        except Exception as e:
            self.air_q_val.config(text=f'错误:{e}')

    # ----- 蒸汽 -----
    def _build_steam_panel(self, parent):
        f = tk.Frame(parent, bg='#D4F8D4', bd=2, relief='ridge')
        f.pack(side='top', fill='x', expand=False, pady=4)
        tk.Label(f, text='蒸汽流量 计算', font=('Microsoft YaHei', 12, 'bold'),
                 bg='#D4F8D4', fg='#333').pack(pady=(8, 4))
        body = tk.Frame(f, bg='#D4F8D4')
        body.pack(fill='x', padx=4, pady=4)
        left = tk.Frame(body, bg='#D4F8D4')
        left.pack(side='left', fill='x', expand=True, padx=4, pady=4)
        right = tk.Frame(body, bg='#D4F8D4')
        right.pack(side='left', fill='x', expand=True, padx=4, pady=4)
        self.stm_q_e = self._entry(left, '流量', 5.0, 't/h', '#D4F8D4')
        self.stm_p_e = self._entry(left, '表压', 4.0, 'atm', '#D4F8D4')
        self.stm_t_e = self._entry(left, '温度', 141.0, '°C', '#D4F8D4')
        self.stm_v_e = self._entry(left, '压力下流速', 10.0, 'm/s', '#D4F8D4')
        # 管径结果��示
        self.stm_d_result_frame = tk.Frame(left, bg='#D4F8D4')
        self.stm_d_result_frame.pack(fill='x', padx=20, pady=2)
        self.stm_d_val = tk.Label(self.stm_d_result_frame, text='', width=14, bg='#D4F8D4',
                                  font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.stm_d_val.pack(side='left', padx=2)
        tk.Label(self.stm_d_result_frame, text='mm', width=8, bg='#D4F8D4',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        # 密度结果显示
        self.stm_d_den_frame = tk.Frame(left, bg='#D4F8D4')
        self.stm_d_den_frame.pack(fill='x', padx=20, pady=2)
        tk.Label(self.stm_d_den_frame, text='密度', width=8, bg='#D4F8D4',
                 font=('Microsoft YaHei', 9, 'bold'), fg='#555').pack(side='left')
        self.stm_d_den_lbl = tk.Label(self.stm_d_den_frame, text='', width=10, bg='#D4F8D4',
                                      font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.stm_d_den_lbl.pack(side='left', padx=2)
        tk.Label(self.stm_d_den_frame, text='kg/m3', width=8, bg='#D4F8D4',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        self._calc_button(left, '计算管径', self._calc_stm_d, '#A0E8A0')

        self.stm_d2_e = self._entry(right, '管径', 105.0, 'mm', '#D4F8D4')
        self.stm_p2_e = self._entry(right, '表压', 3.0, 'atm', '#D4F8D4')
        self.stm_t2_e = self._entry(right, '温度', 141.0, '°C', '#D4F8D4')
        self.stm_v2_e = self._entry(right, '压力下流速', 10.0, 'm/s', '#D4F8D4')
        # 流量结果显示
        self.stm_q_result_frame = tk.Frame(right, bg='#D4F8D4')
        self.stm_q_result_frame.pack(fill='x', padx=20, pady=2)
        self.stm_q_val = tk.Label(self.stm_q_result_frame, text='', width=14, bg='#D4F8D4',
                                  font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.stm_q_val.pack(side='left', padx=2)
        tk.Label(self.stm_q_result_frame, text='t/h', width=8, bg='#D4F8D4',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        # 密度结果显示
        self.stm_q_den_frame = tk.Frame(right, bg='#D4F8D4')
        self.stm_q_den_frame.pack(fill='x', padx=20, pady=2)
        tk.Label(self.stm_q_den_frame, text='密度', width=8, bg='#D4F8D4',
                 font=('Microsoft YaHei', 9, 'bold'), fg='#555').pack(side='left')
        self.stm_q_den_lbl = tk.Label(self.stm_q_den_frame, text='', width=10, bg='#D4F8D4',
                                      font=('Microsoft YaHei', 11, 'bold'), fg='#000')
        self.stm_q_den_lbl.pack(side='left', padx=2)
        tk.Label(self.stm_q_den_frame, text='kg/m3', width=8, bg='#D4F8D4',
                 font=('Microsoft YaHei', 9)).pack(side='left')
        self._calc_button(right, '计算流量', self._calc_stm_q, '#A0E8A0')

    def _calc_stm_d(self):
        try:
            q = float(self.stm_q_e.get())
            p = float(self.stm_p_e.get())
            t = float(self.stm_t_e.get())
            v = float(self.stm_v_e.get())
            d = steam_diameter(q, v, p, t)
            self.stm_d_val.config(text=f'{d:.2f}')
            from modules.pipe_calc import steam_density
            den = steam_density(p, t)
            self.stm_d_den_lbl.config(text=f'{den:.2f}')
        except Exception as e:
            self.stm_d_val.config(text=f'错误:{e}')

    def _calc_stm_q(self):
        try:
            d = float(self.stm_d2_e.get())
            p = float(self.stm_p2_e.get())
            t = float(self.stm_t2_e.get())
            v = float(self.stm_v2_e.get())
            q = steam_flow(d, v, p, t)
            self.stm_q_val.config(text=f'{q:.2f}')
            from modules.pipe_calc import steam_density
            den = steam_density(p, t)
            self.stm_q_den_lbl.config(text=f'{den:.2f}')
        except Exception as e:
            self.stm_q_val.config(text=f'错误:{e}')


def open_pipe_calc(parent):
    PipeCalcDialog(parent)
