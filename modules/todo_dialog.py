# -*- coding: utf-8 -*-
"""待办事项对话框 V4 - 编号+颜色+滚动报告"""
import tkinter as tk
from tkinter import scrolledtext, messagebox
import time
import os

def _user_name():
    """周报署名，从 .env 读取，默认'我'"""
    return os.environ.get('USER_DISPLAY_NAME', '我')

def _report_dir():
    """周报输出目录，可在 .env 用 REPORT_DIR 指定，默认桌面"""
    return os.environ.get('REPORT_DIR') or os.path.join(
        os.path.expanduser('~'), 'Desktop', _user_name() + '周报')

S_OK = '\u2705'; S_NO = '\u2b1c'
ARR_R = '\u25b6'; ARR_D = '\u25bc'
PKG = '\U0001f4e6'; NOTE_ICON = '\U0001f4dd'
REPORT_ICON = '\U0001f4ca'
COLORS = [
    '#2E86C1','#27AE60','#8E44AD','#D35400','#C0392B','#16A085',
    '#2980B9','#F39C12','#E74C3C','#1ABC9C','#9B59B6','#3498DB',
    '#E67E22','#2ECC71','#E91E63','#00BCD4','#FF5722','#009688',
    '#673AB7','#CDDC39','#795548','#607D8B','#FFC107','#2196F3',
    '#4CAF50','#FF9800','#03A9F4','#8BC34A','#9C27B0','#00BFA5',
]


def _center_win(win, w, h):
    try:
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        win.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    except: pass


class TodoDialog:
    def __init__(self, parent, todolist, deepseek_fn=None):
        self.parent = parent
        self.todos = todolist
        self.ds_fn = deepseek_fn
        self._current_tid = None
        self._mode = 'project'
        self._folded = set()

        self.win = tk.Toplevel(parent)
        self.win.title(PKG + ' 待办事项')
        self.win.attributes('-topmost', True)
        self.win.resizable(True, True)
        self.win.minsize(420, 480)
        self._zoomed = False
        _center_win(self.win, 520, 600)

        # 标题
        title_bar = tk.Frame(self.win, bg='#27AE60')
        title_bar.pack(fill='x')
        self._title_lbl = tk.Label(title_bar, text=PKG + ' 待办事项 (项目+子事项)',
                                   font=('Microsoft YaHei', 12, 'bold'),
                                   bg='#27AE60', fg='white', pady=6)
        self._title_lbl.pack(side='left', fill='x', expand=True)
        self._zoom_btn = tk.Button(title_bar, text='⛶', bg='#27AE60', fg='white',
                                   activebackground='#1E8449', activeforeground='white',
                                   bd=0, font=('Microsoft YaHei', 11, 'bold'),
                                   command=self._toggle_zoom, cursor='hand2')
        self._zoom_btn.pack(side='right', padx=8)
        self._title_lbl.bind('<Double-Button-1>', lambda e: self._toggle_zoom())
        title_bar.bind('<Double-Button-1>', lambda e: self._toggle_zoom())

        # 模式选择
        mf = tk.Frame(self.win, padx=8, pady=3)
        mf.pack(fill='x')
        tk.Label(mf, text='模式:', font=('Microsoft YaHei', 9), fg='#555').pack(side='left')
        self.mode_var = tk.StringVar(value='project')
        tk.Radiobutton(mf, text=PKG + ' 项目', variable=self.mode_var, value='project',
                       command=self._on_mode_change, font=('Microsoft YaHei', 9)).pack(side='left', padx=4)
        tk.Radiobutton(mf, text=NOTE_ICON + ' 子事项', variable=self.mode_var, value='sub',
                       command=self._on_mode_change, font=('Microsoft YaHei', 9)).pack(side='left', padx=4)
        self.mode_hint = tk.Label(mf, text='', font=('Microsoft YaHei', 8), fg='#888')
        self.mode_hint.pack(side='right')

        # 输入区
        add_frame = tk.Frame(self.win, padx=8, pady=3)
        add_frame.pack(fill='x')
        self.add_hint = tk.Label(add_frame, text='输入项目:', font=('Microsoft YaHei', 9), fg='#555')
        self.add_hint.pack(anchor='w')
        self.entry = tk.Entry(add_frame, font=('Microsoft YaHei', 10))
        self.entry.pack(side='left', fill='x', expand=True, padx=(0, 4))
        self.entry.bind('<Return>', lambda e: self._add())
        tk.Button(add_frame, text='添加', command=self._add,
                  bg='#27AE60', fg='white', width=6).pack(side='left')

        # 列表
        lf = tk.Frame(self.win)
        lf.pack(fill='both', padx=8, pady=2, expand=True)
        self.lb = tk.Listbox(lf, font=('Microsoft YaHei', 10), height=12,
                             selectmode='single', exportselection=False)
        self.lb.pack(side='left', fill='both', expand=True)
        sc = tk.Scrollbar(lf, orient='vertical', command=self.lb.yview)
        sc.pack(side='right', fill='y')
        self.lb.config(yscrollcommand=sc.set)
        self.lb.bind('<<ListboxSelect>>', self._on_select)
        self.lb.bind('<Button-1>', self._on_click_row, add='+')

        # 备注区
        note_frame = tk.Frame(self.win, padx=8, pady=2)
        note_frame.pack(fill='x')
        nt_head = tk.Frame(note_frame)
        nt_head.pack(fill='x')
        self.note_title = tk.Label(nt_head, text=NOTE_ICON + ' 备注 (点击事项切换)',
                                    font=('Microsoft YaHei', 9, 'bold'), fg='#555')
        self.note_title.pack(side='left')
        self.save_lbl = tk.Label(nt_head, text='', font=('Microsoft YaHei', 8), fg='#27AE60')
        self.save_lbl.pack(side='right')
        self.note_text = scrolledtext.ScrolledText(note_frame, font=('Microsoft YaHei', 9),
                                                    height=3, wrap='word')
        self.note_text.pack(fill='x')
        self.note_text.bind('<KeyRelease>', lambda e: self.win.after(150, self._save_note))
        self.note_text.config(state='disabled', bg='#F5F5F5')

        self.status_lbl = tk.Label(self.win, text='', font=('Microsoft YaHei', 9), fg='#8E44AD', pady=2)
        self.status_lbl.pack()

        # 按钮区
        bf = tk.Frame(self.win)
        bf.pack(fill='x', padx=8, pady=4)
        tk.Button(bf, text=S_OK + ' 完成/取消', command=self._toggle,
                  bg='#27AE60', fg='white', width=10).pack(side='left', padx=2)
        tk.Button(bf, text='\U0001f5d1\ufe0f 删除', command=self._del,
                  bg='#E74C3C', fg='white', width=6).pack(side='left', padx=2)
        tk.Button(bf, text=REPORT_ICON + ' 生成报告', command=self._gen_report,
                  bg='#8E44AD', fg='white', width=12,
                  font=('Microsoft YaHei', 9, 'bold')).pack(side='right', padx=2)
        tk.Button(bf, text='关闭', command=self.win.destroy, width=6).pack(side='right', padx=2)

        self._refresh()
        self._on_mode_change()

    # ====================== 交互 ======================
    def _on_mode_change(self):
        self._mode = self.mode_var.get()
        if self._mode == 'project':
            self.add_hint.config(text='输入项目:')
            self.mode_hint.config(text='')
        else:
            self.add_hint.config(text='添加子事项 (先点击一个项目):')
            self.mode_hint.config(text='')

    def _toggle_zoom(self):
        """切换最大化/还原窗口"""
        try:
            self._zoomed = not self._zoomed
            if self._zoomed:
                # 全屏
                self._save_geom = self.win.geometry()
                sw = self.win.winfo_screenwidth()
                sh = self.win.winfo_screenheight()
                self.win.geometry(f'{sw}x{sh}+0+0')
                self._zoom_btn.config(text='🗗')
            else:
                # 还原
                if hasattr(self, '_save_geom'):
                    self.win.geometry(self._save_geom)
                self._zoom_btn.config(text='⛶')
        except Exception:
            pass

    def _add(self):
        txt = self.entry.get().strip()
        if not txt: return
        if self._mode == 'project':
            self.todos.add(txt, parent=None)
            self.mode_hint.config(text=S_OK + ' 已添加: ' + txt[:12])
        else:
            sel = self.lb.curselection()
            tid = self._row_to_tid(sel[0]) if sel else None
            if not tid:
                projs = self.todos.get_projects()
                if not projs: return
                tid = projs[0].id
            self.todos.add(txt, parent=tid)
            self.mode_hint.config(text=S_OK + ' 已添加子事项')
        self.entry.delete(0, tk.END)
        self._refresh()

    def _toggle(self):
        sel = self.lb.curselection()
        if not sel: return
        tid = self._row_to_tid(sel[0])
        if not tid: return
        self.todos.toggle(tid)
        self._current_tid = tid
        self._refresh()
        self.lb.selection_set(sel[0])

    def _del(self):
        sel = self.lb.curselection()
        if not sel: return
        tid = self._row_to_tid(sel[0])
        if not tid: return
        self.todos.remove(tid)
        self._current_tid = None
        self.note_text.config(state='disabled', bg='#F5F5F5')
        self.note_text.delete('1.0', tk.END)
        self._refresh()

    def _on_click_row(self, e):
        idx = self.lb.nearest(e.y)
        if idx < 0: return
        text = self.lb.get(idx)
        if not text: return
        if text[0] in (ARR_R, ARR_D):
            bbox = self.lb.bbox(idx)
            if bbox and e.x - bbox[0] < 30:
                self._toggle_fold(idx)
                return
        tid = self._row_to_tid(idx)
        if tid: self._show_note_for(tid)

    def _on_select(self, e):
        sel = self.lb.curselection()
        if not sel: return
        tid = self._row_to_tid(sel[0])
        if tid: self._show_note_for(tid)

    def _toggle_fold(self, list_idx):
        all_t = self.todos.get_all()
        for i in range(list_idx, -1, -1):
            if i < len(all_t) and not all_t[i].parent:
                pid = all_t[i].id
                if pid in self._folded:
                    self._folded.discard(pid)
                else:
                    self._folded.add(pid)
                self._refresh()
                self.lb.selection_clear(0, tk.END)
                self.lb.selection_set(list_idx)
                return

    def _row_to_tid(self, row):
        i = 0
        for proj in self.todos.get_projects():
            if i == row: return proj.id
            i += 1
            if proj.note: i += 1
            if proj.id in self._folded: continue
            for sub in self.todos.get_children(proj.id):
                if i == row: return sub.id
                i += 1
                if sub.note: i += 1
        return None

    def _show_note_for(self, tid):
        for t in self.todos.items:
            if t.id == tid:
                self._current_tid = tid
                prefix = PKG + ' ' if not t.parent else NOTE_ICON + ' '
                self.note_title.config(text=NOTE_ICON + ' [' + prefix.strip() + t.text[:18] + '] 的备注')
                self.note_text.config(state='normal', bg='white')
                self.note_text.delete('1.0', tk.END)
                self.note_text.insert('1.0', t.note or '')
                self.save_lbl.config(text='')
                return

    def _save_note(self):
        if not self._current_tid: return
        note = self.note_text.get('1.0', tk.END).strip()
        self.todos.set_note(self._current_tid, note)
        self.save_lbl.config(text='\u2713 已保存')
        self.win.after(1500, lambda: self.save_lbl.config(text=''))
        self._refresh()

    def _refresh(self):
        self.lb.delete(0, tk.END)
        i = 0
        for idx, proj in enumerate(self.todos.get_projects()):
            color = COLORS[idx % len(COLORS)]
            folded = proj.id in self._folded
            status = S_OK if proj.done else S_NO
            arrow = ARR_R if folded else ARR_D
            num = idx + 1
            pd = proj.created[:10] if proj.created else ''
            line = arrow + ' ' + str(num) + '. ' + PKG + ' ' + status + ' ' + proj.text[:18]
            if pd: line += '  [' + pd + ']'
            self.lb.insert(tk.END, line)
            try: self.lb.itemconfigure(i, fg=color)
            except: pass
            i += 1
            if proj.note:
                np = proj.note[:18] + ('...' if len(proj.note) > 18 else '')
                self.lb.insert(tk.END, '       ' + NOTE_ICON + ' ' + np)
                try: self.lb.itemconfigure(i, fg=color)
                except: pass
                i += 1
            if not folded:
                for sub in self.todos.get_children(proj.id):
                    st = S_OK if sub.done else S_NO
                    sd = sub.created[:10] if sub.created else ''
                    sl = '      ' + NOTE_ICON + ' ' + st + ' ' + sub.text[:21]
                    if sd: sl += '  [' + sd + ']'
                    self.lb.insert(tk.END, sl)
                    try: self.lb.itemconfigure(i, fg=color)
                    except: pass
                    i += 1
                    if sub.note:
                        np = sub.note[:18] + ('...' if len(sub.note) > 18 else '')
                        self.lb.insert(tk.END, '         ' + NOTE_ICON + ' ' + np)
                        try: self.lb.itemconfigure(i, fg=color)
                        except: pass
                        i += 1
        self.win.update_idletasks()

    # ====================== 报告 ======================
    def _gen_report(self):
        self.status_lbl.config(text=REPORT_ICON + ' 正在生成报告...')
        self.win.update()

        if not self.ds_fn:
            self.status_lbl.config(text='\u274c 未接入 AI')
            return

        all_t = self.todos.get_all()
        if not all_t:
            self.status_lbl.config(text='\u274c 没有待办事项')
            return

        now = time.strftime('%Y-%m-%d %H:%M')
        lines = ['工作报告 - ' + now, '']
        done_count = total_count = 0
        pending_projs = []
        pending_subs = []
        proj_stats = []  # (num, name, done/total, pending_subs)
        for idx, proj in enumerate(self.todos.get_projects()):
            total_count += 1
            p_status = '(已完成)' if proj.done else '(未完成)'
            num = idx + 1
            lines.append(str(num) + '. ' + proj.text + ' ' + p_status)
            if proj.note: lines.append('    项目备注: ' + proj.note)
            if proj.done: done_count += 1
            else: pending_projs.append(f'{num}. {proj.text}')
            subs = self.todos.get_children(proj.id)
            done_subs = 0
            sub_pending = []
            for sub in subs:
                total_count += 1
                status = '(已完成)' if sub.done else '(未完成)'
                lines.append('    - ' + sub.text + ' ' + status)
                if sub.note: lines.append('      备注: ' + sub.note)
                if sub.done:
                    done_count += 1
                    done_subs += 1
                else:
                    sub_pending.append(sub.text)
                    pending_subs.append(f'{proj.text}→{sub.text}')
            proj_stats.append((num, proj.text, done_subs, len(subs), sub_pending))
            lines.append('')

        rate = round(done_count * 100 / max(total_count, 1), 1)

        # 构建 AI 参考数据 (含完整统计)
        summary_block = (
            f'核心统计:\n'
            f'- 项目总数: {len(self.todos.get_projects())}\n'
            f'- 子项总数: {total_count - len(self.todos.get_projects())}\n'
            f'- 总完成: {done_count} / {total_count}\n'
            f'- 完成率: {rate}%\n'
            f'- 未完成项目: {", ".join(pending_projs) if pending_projs else "(无)"}\n'
            f'- 未完成子项: {", ".join(pending_subs) if pending_subs else "(无)"}\n\n'
            f'各项目进度:\n'
        )
        for num, name, done_subs, total_subs, pending in proj_stats:
            if total_subs > 0:
                summary_block += f'- {num}. {name}: 子项 {done_subs}/{total_subs} 已完成\n'
                for p in pending:
                    summary_block += f'  待办: {p}\n'

        todo_text = '\n'.join(lines)
        prompt = (
            '将以下待办事项整理成一份带编号、详细总结的工作报告。\n\n'
            '格式要求:\n'
            '1. 每个项目用原始编号作为标题, 如 "1. 萃取五期"\n'
            '2. 子事项用 - 缩进, 如 "  - 画P&ID图"\n'
            '3. (已完成)(未完成) 标记必须准确, 不能捏造!\n'
            '4. 备注内容用口语化表达\n'
            '5. ✅已完成 / ⏳待办\n'
            '6. 🔴困难 / 🟡中等 / 🟢简单\n'
            '7. 不要改变项目编号顺序\n\n'
            '【总结】部分必须丰富, 包含:\n'
            f'  - 总完成: {done_count}/{total_count}, 完成率 {rate}%\n'
            f'  - 项目完成情况: 已完成X个, 未完成Y个\n'
            f'  - 子项完成情况: 已完成M个, 未完成N个\n'
            f'  - 重点待办项: 列出3-5个最关键的待办\n'
            f'  - 整体评价: 一句话总结工作进展\n'
            '  - 下一步建议: 列出下一步要做的关键事项\n\n'
            f'统计参考:\n{summary_block}\n\n'
            f'原始数据:\n{todo_text}'
        )

        import threading
        def work():
            try:
                reply = self.ds_fn([{'role': 'user', 'content': prompt}], max_tokens=4000, temperature=0.5)
                if reply and not reply.startswith('['):
                    self.win.after(0, lambda r=reply: self._on_report_ok(r))
                else:
                    self.win.after(0, lambda: self._on_report_err(reply or 'AI 未响应'))
            except Exception as e:
                self.win.after(0, lambda: self._on_report_err(str(e)[:60]))

        t = threading.Thread(target=work, daemon=True)
        t.start()

    def _on_report_ok(self, report):
        self.status_lbl.config(text=S_OK + ' 报告已生成')
        win = tk.Toplevel(self.win)
        win.title(REPORT_ICON + f' {_user_name()} 工作报告')
        win.attributes('-topmost', True)
        _center_win(win, 720, 620)
        win.config(bg='#FAF5FF')

        tk.Label(win, text=REPORT_ICON + f' {_user_name()}工作报告',
                 font=('Microsoft YaHei', 24, 'bold'), fg='white', bg='#8E44AD', pady=14).pack(fill='x')

        tb_frame = tk.Frame(win, bg='#FAF5FF')
        tb_frame.pack(fill='both', expand=True, padx=4, pady=4)
        sb = tk.Scrollbar(tb_frame)
        sb.pack(side='right', fill='y')
        tb = scrolledtext.ScrolledText(tb_frame, font=('Microsoft YaHei', 18),
                                       bg='#FAF5FF', fg='#222', wrap='word',
                                       padx=20, pady=18, yscrollcommand=sb.set)
        tb.pack(side='left', fill='both', expand=True)
        sb.config(command=tb.yview)

        # 插入 AI 报告
        tb.insert('end', report)

        # 扫描并着色: 匹配每个项目/子项的关键词, 给对应行染色
        for idx, proj in enumerate(self.todos.get_projects()):
            color = COLORS[idx % len(COLORS)]
            tag = f'tag{idx}'
            tb.tag_configure(tag, foreground=color, font=('Microsoft YaHei', 18, 'bold'))
            keywords = [proj.text] + [sub.text for sub in self.todos.get_children(proj.id)]
            for kw in keywords:
                if len(kw) < 2: continue
                start = '1.0'
                while True:
                    pos = tb.search(kw, start, 'end', nocase=False)
                    if not pos: break
                    line_start = tb.index(f'{pos} linestart')
                    line_end = tb.index(f'{pos} lineend')
                    tb.tag_add(tag, line_start, line_end)
                    start = line_end

        tb.config(state='disabled')
        win.update()
        win.lift()
        win.focus_force()

        tk.Button(win, text='关闭', command=win.destroy,
                  bg='#8E44AD', fg='white', width=14,
                  font=('Microsoft YaHei', 16, 'bold')).pack(pady=(0, 16))

        # 自动填充周报Excel模板
        self.win.after(300, lambda: self._fill_weekly_excel(report))

    def _fill_weekly_excel(self, report_text):
        """根据待办数据 + AI报告填充周报Excel模板"""
        import os as _os, time as _time, sys as _sys
        # 适配源码和exe运行
        if hasattr(_sys, '_MEIPASS'):
            template_path = _os.path.join(_sys._MEIPASS, 'data', '每周进度反馈模板.xlsx')
        else:
            template_path = _os.path.join(_os.path.dirname(
                _os.path.dirname(_os.path.abspath(__file__))), 'data', '每周进度反馈模板.xlsx')
        if not _os.path.isfile(template_path):
            self.status_lbl.config(text='\u274c 模板未找到')
            return

        try:
            import openpyxl
            from openpyxl.styles import Alignment, Font
        except ImportError:
            self.status_lbl.config(text='\u274c 缺少 openpyxl 库')
            return

        wb = openpyxl.load_workbook(template_path)
        ws = wb.active

        # 年份周数计算
        now = _time.localtime()
        week_num = now.tm_yday // 7 + 1
        today_str = _time.strftime('%Y-%m-%d', now)
        ws['A2'] = f'填报人：{_user_name()}   填报周期：{now.tm_year}年第{week_num}周   填报日期：{today_str}'

        projects = self.todos.get_projects()
        row = 5
        seq = 1
        styles_set = False

        for proj in projects:
            subs = self.todos.get_children(proj.id)
            done_subs = [s for s in subs if s.done]
            pending_subs = [s for s in subs if not s.done]
            total_subs = len(subs)
            rate = round(len(done_subs) * 100 / max(total_subs, 1)) if total_subs > 0 else (100 if proj.done else 0)

            item_date = proj.created[:10] if proj.created else today_str

            # 子事项备注补时间标记 (备注已被 set_note 加过日期, 这里只透传)
            def _stamp_note(sub):
                if not sub.note:
                    return ''
                return sub.note

            done_works = []
            # 项目备注放首位 (同样 set_note 已加日期)
            if proj.note:
                done_works.append(f'[整体状态] {proj.note}')
            for s in done_subs:
                w = s.text
                sn = _stamp_note(s)
                if sn:
                    w = f'{w}（{sn}）'
                done_works.append(w)

            pending_works = []
            for s in pending_subs:
                w = s.text
                sn = _stamp_note(s)
                if sn:
                    w = f'{w}（{sn}）'
                pending_works.append(w)

            # 提取风险信息
            risks = []
            for s in subs:
                if s.note and any(kw in s.note for kw in ['等','确认','设计院','改动','等待','暂']):
                    risks.append(s.note[:60])
            risk_text = '；'.join(risks) if risks else ''

            if row > ws.max_row:
                ws.insert_rows(row)

            ws.cell(row=row, column=1, value=seq)
            ws.cell(row=row, column=2, value=os.environ.get('COMPANY_NAME', ''))
            ws.cell(row=row, column=3, value=proj.text)
            ws.cell(row=row, column=4, value=os.environ.get('USER_DISPLAY_NAME', ''))
            # 关键节点: 优先取未完成的子事项里最重要的，否则取项目本身
            if pending_subs:
                critical = pending_subs[0].text
            elif done_subs:
                critical = done_subs[-1].text
            else:
                critical = proj.text
            ws.cell(row=row, column=5, value=critical[:24])
            ws.cell(row=row, column=7, value=rate)
            ws.cell(row=row, column=8, value='；'.join(done_works) if done_works else '无')
            ws.cell(row=row, column=9, value='；'.join(pending_works) if pending_works else '无')
            ws.cell(row=row, column=10, value=risk_text)
            ws.cell(row=row, column=11, value=os.environ.get('USER_DISPLAY_NAME', ''))
            ws.cell(row=row, column=12, value=item_date)

            # 设置单元格自动换行
            for col in range(1, 13):
                cell = ws.cell(row=row, column=col)
                if cell.value:
                    cell.alignment = Alignment(wrap_text=True, vertical='top')

            row += 1
            seq += 1

        # 输出到周报文件夹（默认桌面，可用 REPORT_DIR 指定）
        output_dir = _report_dir()
        _os.makedirs(output_dir, exist_ok=True)
        fname = f'周报_{now.tm_year}第{week_num}周_{_user_name()}.xlsx'
        output_path = _os.path.join(output_dir, fname)
        wb.save(output_path)

        self.status_lbl.config(text=REPORT_ICON + f' Excel已生成: {fname}')
        return output_path

    def _on_report_err(self, err):
        self.status_lbl.config(text='\u274c 失败: ' + err[:30])
        messagebox.showerror('报告生成失败', err, parent=self.win)
