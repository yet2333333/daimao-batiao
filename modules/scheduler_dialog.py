# -*- coding: utf-8 -*-
"""日程对话框 - 独立类避免闭包陷阱"""
import tkinter as tk
import time
import os, sys


def _center(parent, win, w, h):
    try:
        sw = parent.winfo_screenwidth()
        sh = parent.winfo_screenheight()
        win.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    except: pass


class SchedulerDialog:
    """日程管理独立窗口类, 所有方法直接绑定 self"""

    def __init__(self, parent, scheduler, stats):
        self.parent = parent
        self.scheduler = scheduler
        self.stats = stats

        self.win = tk.Toplevel(parent)
        self.win.title('⏰ 日程管理')
        self.win.attributes('-topmost', True)
        self.win.resizable(False, False)
        _center(parent, self.win, 440, 520)

        tk.Label(self.win, text='📅 我的日程', font=('Microsoft YaHei', 12, 'bold'),
                 bg='#4A90D9', fg='white', pady=6).pack(fill='x')

        # 新建提醒区
        new_frame = tk.LabelFrame(self.win, text='  新建提醒  ', font=('Microsoft YaHei', 10, 'bold'),
                                   bg='#F5F7FA', padx=8, pady=8)
        new_frame.pack(fill='x', padx=8, pady=8)

        now = time.localtime()

        # 日期选择
        df = tk.Frame(new_frame, bg='#F5F7FA'); df.pack(fill='x', pady=2)
        tk.Label(df, text='📅 日期', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')
        self.yr = tk.Spinbox(df, from_=2024, to=2099, width=5, wrap=True, font=('Microsoft YaHei', 10))
        self.yr.delete(0, tk.END); self.yr.insert(0, str(now.tm_year)); self.yr.pack(side='left', padx=2)
        tk.Label(df, text='年', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')
        self.mo = tk.Spinbox(df, from_=1, to=12, width=3, wrap=True, font=('Microsoft YaHei', 10))
        self.mo.delete(0, tk.END); self.mo.insert(0, str(now.tm_mon)); self.mo.pack(side='left', padx=2)
        tk.Label(df, text='月', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')
        self.dy = tk.Spinbox(df, from_=1, to=31, width=3, wrap=True, font=('Microsoft YaHei', 10))
        self.dy.delete(0, tk.END); self.dy.insert(0, str(now.tm_mday)); self.dy.pack(side='left', padx=2)
        tk.Label(df, text='日', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')

        # 快捷日期
        qdf = tk.Frame(new_frame, bg='#F5F7FA'); qdf.pack(fill='x', pady=4)
        for label, kw in [('今天', 0), ('明天', 1), ('后天', 2), ('下周一', 7)]:
            tk.Button(qdf, text=label, font=('Microsoft YaHei', 8),
                      command=lambda d=kw: self._set_date(d), bg='#E0E0E0', width=6).pack(side='left', padx=2)

        # 时间选择
        tf = tk.Frame(new_frame, bg='#F5F7FA'); tf.pack(fill='x', pady=2)
        tk.Label(tf, text='⏰ 时间', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')
        self.hr = tk.Spinbox(tf, from_=0, to=23, width=3, wrap=True, format='%02.0f', font=('Microsoft YaHei', 10))
        self.hr.delete(0, tk.END); self.hr.insert(0, f'{(now.tm_hour+1)%24:02d}'); self.hr.pack(side='left', padx=2)
        tk.Label(tf, text='时', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')
        self.mn = tk.Spinbox(tf, from_=0, to=59, width=3, wrap=True, format='%02.0f', font=('Microsoft YaHei', 10))
        self.mn.delete(0, tk.END); self.mn.insert(0, '00'); self.mn.pack(side='left', padx=2)
        tk.Label(tf, text='分', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')

        # 快捷时间
        qtf = tk.Frame(new_frame, bg='#F5F7FA'); qtf.pack(fill='x', pady=2)
        for txt, h, m in [('+5分', None, 5), ('+10分', None, 10), ('+15分', None, 15), ('早9点', 9, 0)]:
            tk.Button(qtf, text=txt, font=('Microsoft YaHei', 8),
                      command=lambda hh=h, mm=m: self._set_quick(hh, mm),
                      bg='#E0E0E0', width=6).pack(side='left', padx=2)

        # 内容
        tk.Label(new_frame, text='💬 提醒内容', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(anchor='w', pady=(6, 0))
        self.tx = tk.Text(new_frame, height=2, font=('Microsoft YaHei', 10), wrap='word')
        self.tx.pack(fill='x', pady=2)

        # 重复
        rp = tk.Frame(new_frame, bg='#F5F7FA'); rp.pack(fill='x', pady=4)
        tk.Label(rp, text='🔁 重复', font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left')
        self.rep = tk.StringVar(value='once')
        for val, txt in [('once', '不重复'), ('daily', '每天'), ('weekly', '每周'), ('workday', '工作日')]:
            tk.Radiobutton(rp, text=txt, variable=self.rep, value=val,
                           font=('Microsoft YaHei', 9), bg='#F5F7FA').pack(side='left', padx=4)

        # 保存按钮
        bf = tk.Frame(new_frame, bg='#F5F7FA'); bf.pack(fill='x', pady=4)
        tk.Button(bf, text='💾 保存提醒', command=self._save,
                  bg='#4A90D9', fg='white', width=12).pack(side='left', padx=4)
        tk.Button(bf, text='清空', command=lambda: self.tx.delete('1.0', tk.END), width=8).pack(side='left', padx=4)

        # 已有提醒列表
        tk.Label(self.win, text='📋 已有提醒', font=('Microsoft YaHei', 10, 'bold'),
                 bg='#F5F7FA').pack(anchor='w', padx=10, pady=(4, 2))
        lf = tk.Frame(self.win); lf.pack(fill='both', expand=True, padx=8, pady=2)
        self.lb = tk.Listbox(lf, font=('Microsoft YaHei', 9), height=8)
        self.lb.pack(side='left', fill='both', expand=True)
        sc = tk.Scrollbar(lf, orient='vertical', command=self.lb.yview); sc.pack(side='right', fill='y')
        self.lb.config(yscrollcommand=sc.set)

        # 操作按钮（删除按钮加大，更醒目）
        bf2 = tk.Frame(self.win); bf2.pack(pady=(0, 8))
        btn_del = tk.Button(bf2, text='🗑️ 删除选中', command=self._del,
                            bg='#E74C3C', fg='white', width=14, font=('Microsoft YaHei', 10, 'bold'))
        btn_del.pack(side='left', padx=2)
        tk.Button(bf2, text='⏹ 开关', command=self._toggle,
                  bg='#F39C12', fg='white', width=8).pack(side='left', padx=2)
        tk.Button(bf2, text='🔄 刷新', command=self._refresh,
                  bg='#2ECC71', fg='white', width=8).pack(side='left', padx=2)
        tk.Button(bf2, text='关闭', command=self.win.destroy, width=8).pack(side='left', padx=2)

        # 点击列表时记录最后选中位置
        self._last_sel = -1
        self.lb.bind('<ButtonRelease-1>', self._on_listbox_click)

        # 右键菜单 (额外删除方式)
        self.context_menu = tk.Menu(self.win, tearoff=0)
        self.context_menu.add_command(label='🗑️ 删除这条', command=self._del)
        self.context_menu.add_command(label='⏹ 切换开关', command=self._toggle)
        self.context_menu.add_separator()
        self.context_menu.add_command(label='🔄 刷新', command=self._refresh)
        self.lb.bind('<Button-3>', self._show_context_menu)

        # 双击删除
        self.lb.bind('<Double-Button-1>', lambda e: self._del())

        # 初始刷新
        self._refresh()

    def _on_listbox_click(self, event):
        self._last_sel = self.lb.nearest(event.y)

    def _show_context_menu(self, event):
        idx = self.lb.nearest(event.y)
        if idx >= 0:
            self.lb.selection_clear(0, tk.END)
            self.lb.selection_set(idx)
            self.lb.activate(idx)
            self._last_sel = idx
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    @property
    def _selected_idx(self):
        """获取当前选中的索引 (先查 curselection, 回退到 last_sel)"""
        cur = self.lb.curselection()
        if cur:
            return cur[0]
        if self._last_sel >= 0 and self._last_sel < self.lb.size():
            return self._last_sel
        return None

    def _set_date(self, offset_days):
        t = time.time() + offset_days * 86400
        nt = time.localtime(t)
        self.yr.delete(0, tk.END); self.yr.insert(0, str(nt.tm_year))
        self.mo.delete(0, tk.END); self.mo.insert(0, str(nt.tm_mon))
        self.dy.delete(0, tk.END); self.dy.insert(0, str(nt.tm_mday))

    def _set_quick(self, hh, mm):
        """快捷时间: hh=None 表示当前时间 + mm 分钟"""
        nt = time.localtime()
        self.yr.delete(0, tk.END); self.yr.insert(0, str(nt.tm_year))
        self.mo.delete(0, tk.END); self.mo.insert(0, str(nt.tm_mon))
        self.dy.delete(0, tk.END); self.dy.insert(0, str(nt.tm_mday))
        if hh is None:
            t = time.time() + mm * 60
            nt = time.localtime(t)
            self.hr.delete(0, tk.END); self.hr.insert(0, f'{nt.tm_hour:02d}')
            self.mn.delete(0, tk.END); self.mn.insert(0, f'{nt.tm_min:02d}')
        else:
            self.hr.delete(0, tk.END); self.hr.insert(0, f'{hh:02d}')
            self.mn.delete(0, tk.END); self.mn.insert(0, f'{mm:02d}')

    def _save(self):
        try:
            y = int(self.yr.get()); m = int(self.mo.get()); d = int(self.dy.get())
            h = int(self.hr.get()); mn = int(self.mn.get())
            dt_str = f'{y:04d}-{m:02d}-{d:02d} {h:02d}:{mn:02d}'
            time.strptime(dt_str, '%Y-%m-%d %H:%M')
        except ValueError:
            # 用气泡通知父窗口
            self.parent.bubble('日期无效!')
            return
        txt = self.tx.get('1.0', tk.END).strip()
        if not txt:
            self.parent.bubble('内容不能为空')
            return
        self.scheduler.add(txt, dt_str, repeat=self.rep.get())
        self.stats.total_reminders += 1
        self._after_action()
        self._refresh()
        self.tx.delete('1.0', tk.END)
        self.win.update_idletasks()
        self.parent.bubble('✅ 提醒已保存!')

    def _del(self):
        idx = self._selected_idx
        if idx is None:
            self.parent.bubble('请先点击列表选中一条提醒')
            return
        all_r = self.scheduler.get_all()
        if idx >= len(all_r):
            self.parent.bubble('索引失效, 试试刷新')
            return
        removed = all_r[idx]
        self.scheduler.remove(removed.id)
        self._last_sel = -1
        self._refresh()
        self.win.update_idletasks()
        self.parent.bubble(f'🗑️ 已删除 {removed.text[:20]}')

    def _toggle(self):
        idx = self._selected_idx
        if idx is None:
            self.parent.bubble('请先选中一条提醒')
            return
        all_r = self.scheduler.get_all()
        if idx >= len(all_r):
            self.parent.bubble('索引无效')
            return
        new_state = self.scheduler.toggle(all_r[idx].id)
        self._refresh()
        self.win.update_idletasks()
        self.parent.bubble(f'{"✅ 已开启" if new_state else "🚫 已关闭"}')

    def _refresh(self):
        self.lb.delete(0, tk.END)
        for r in self.scheduler.get_all():
            status = '✅' if r.enabled else '🚫'
            rep_map = {'once': '一次', 'daily': '每天', 'weekly': '每周', 'workday': '工作日'}
            rep = rep_map.get(r.repeat, r.repeat)
            display = f'{status} {r.dt_str} [{rep}] {r.text[:30]}'
            self.lb.insert(tk.END, display)

    def _after_action(self):
        # 调用父对象的 after_action
        if hasattr(self.parent, '_after_action'):
            self.parent._after_action()
