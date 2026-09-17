# -*- coding: utf-8 -*-
"""计算 SOP 文档 - 自动发现 + 打开"""
import tkinter as tk
import os
import glob

# SOP 目录 (按优先级查找)：.env 的 SOP_DIR > 项目根/sop > 用户桌面/sop
_HERE = os.path.dirname(os.path.abspath(__file__))
SOP_DIRS = []
_env_sop = os.environ.get('SOP_DIR', '').strip()
if _env_sop:
    SOP_DIRS.append(_env_sop)
SOP_DIRS += [
    os.path.join(os.path.dirname(_HERE), 'sop'),
    os.path.join(os.path.dirname(os.path.dirname(_HERE)), 'sop'),
    os.path.join(os.path.expanduser('~'), 'Desktop', 'sop'),
]

# SOP 分类标签
SOP_CATEGORIES = {
    '泵': '💧 泵',
    '压': '🌀 压缩机/真空泵',
    '风': '🌪️ 风机',
    '管': '🔧 管道/管径',
    '容': '📦 容器',
    '换': '🔥 换热器',
    '搅': '🔄 搅拌',
    '分': '💦 分布器',
    '泄': '⚠️ 泄放',
}


class SOPManager:
    def __init__(self):
        self.sop_dir = self._find_sop_dir()
        self.files = self._scan()

    def _find_sop_dir(self):
        for d in SOP_DIRS:
            if os.path.isdir(d):
                return d
        return None

    def _scan(self):
        if not self.sop_dir:
            return []
        result = []
        for f in sorted(glob.glob(os.path.join(self.sop_dir, '*.html'))):
            name = os.path.basename(f).replace('.html', '')
            if name.startswith('_'):
                continue
            # 找分类
            category = '📄 其他'
            for key, label in SOP_CATEGORIES.items():
                if key in name:
                    category = label
                    break
            result.append({
                'name': name,
                'path': f,
                'category': category,
                'size': os.path.getsize(f),
            })
        return result


class SOPDialog:
    def __init__(self, parent):
        self.parent = parent
        self.mgr = SOPManager()

        self.win = tk.Toplevel(parent)
        self.win.title('📐 计算 SOP 工具')
        self.win.attributes('-topmost', True)
        self.win.geometry(f'420x480+{parent.winfo_x()+50}+{parent.winfo_y()-200}')
        self.win.resizable(False, False)

        # 标题
        title = '📐 计算 SOP 工具'
        if self.mgr.sop_dir:
            title += f'  ({len(self.mgr.files)} 个)'
        tk.Label(self.win, text=title, font=('Microsoft YaHei', 12, 'bold'),
                 bg='#9B59B6', fg='white', pady=6).pack(fill='x')

        if not self.mgr.sop_dir:
            tk.Label(self.win, text='⚠️ 未找到 SOP 目录\n请在 .env 中配置 SOP_DIR',
                     font=('Microsoft YaHei', 10), fg='red', pady=20).pack()
            tk.Button(self.win, text='关闭', command=self.win.destroy, width=10).pack()
            return

        # 说明
        tk.Label(self.win, text='💡 双击列表项 → 在 Edge/Chrome 中打开计算器',
                 font=('Microsoft YaHei', 8), fg='#888').pack(anchor='w', padx=10, pady=(2, 0))
        # 路径提示
        tk.Label(self.win, text=f'📁 {self.mgr.sop_dir}',
                 font=('Microsoft YaHei', 8), fg='#666', wraplength=400).pack(anchor='w', padx=10, pady=(2, 2))

        # 列表
        lf = tk.Frame(self.win); lf.pack(fill='both', expand=True, padx=8, pady=4)
        self.lb = tk.Listbox(lf, font=('Microsoft YaHei', 10), height=14)
        self.lb.pack(side='left', fill='both', expand=True)
        sc = tk.Scrollbar(lf, orient='vertical', command=self.lb.yview)
        sc.pack(side='right', fill='y')
        self.lb.config(yscrollcommand=sc.set)
        self.lb.bind('<Double-Button-1>', lambda e: self._open())

        # 填充
        for f in self.mgr.files:
            size_mb = f['size'] / 1024 / 1024
            self.lb.insert(tk.END, f"{f['category']}  {f['name']}  ({size_mb:.1f}MB)")

        # 按钮
        bf = tk.Frame(self.win); bf.pack(pady=(0, 8))
        tk.Button(bf, text='🌐 在浏览器打开(推荐)', command=self._open,
                  bg='#9B59B6', fg='white', width=18).pack(side='left', padx=2)
        tk.Button(bf, text='📁 打开所在文件夹', command=self._open_folder,
                  bg='#3498DB', fg='white', width=14).pack(side='left', padx=2)
        tk.Button(bf, text='关闭', command=self.win.destroy, width=8).pack(side='left', padx=2)

    def _open(self):
        sel = self.lb.curselection()
        if not sel or len(sel) == 0:
            if hasattr(self.parent, 'bubble'):
                self.parent.bubble('请先点击选中一个计算器')
            return
        f = self.mgr.files[sel[0]]
        from sop_viewer import SOPViewer
        SOPViewer(self.parent, f['path'])

    def _open_folder(self):
        if self.mgr.sop_dir:
            os.startfile(self.mgr.sop_dir)
