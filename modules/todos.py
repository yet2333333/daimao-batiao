# -*- coding: utf-8 -*-
"""待办事项 - 层级数据层 (项目 + 子事项)"""
import json, os, time, sys

# 数据目录优先级：.env 的 DATA_DIR > exe 同目录/data > 项目根/data
def _resolve_data_dir():
    env_dir = os.environ.get('DATA_DIR', '').strip()
    if env_dir:
        return env_dir
    if hasattr(sys, '_MEIPASS'):
        # 打包成 exe：数据放 exe 同目录，整个文件夹拷走就能带走全部数据
        return os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'data')
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


DATA_DIR = _resolve_data_dir()
TODOS_FILE = os.path.join(DATA_DIR, 'todos.json')


class Todo:
    def __init__(self, tid, text, done=False, created=None, note='', parent=None):
        self.id = tid         # 唯一 ID
        self.text = text       # 事项名称
        self.done = done       # 完成状态
        self.created = created or time.strftime('%Y-%m-%d %H:%M')
        self.note = note       # 备注
        self.parent = parent   # 父项 ID (None = 顶级项目)

    def to_dict(self):
        return {'id':self.id,'text':self.text,'done':self.done,
                'created':self.created,'note':self.note,'parent':self.parent}

    @staticmethod
    def from_dict(d):
        return Todo(d['id'], d['text'], d.get('done',False),
                    d.get('created',''), d.get('note',''), d.get('parent'))


class TodoList:
    def __init__(self):
        self.items = []
        self._counter = 0
        self.load()

    def add(self, text, parent=None):
        """添加项目(parent=None)或子事项(parent=父项id)"""
        self._counter += 1
        t = Todo(f't{self._counter}_{int(time.time())}', text, parent=parent)
        self.items.append(t)
        self.save()
        return t

    def toggle(self, tid):
        for t in self.items:
            if t.id == tid:
                t.done = not t.done
                # 项目完成/取消 → 子项同步
                if not t.parent:  # 是项目
                    for sub in self.items:
                        if sub.parent == t.id:
                            sub.done = t.done
                self.save()
                return t.done
        return None

    def remove(self, tid):
        """删除项目时级联删除所有子项"""
        self.items = [t for t in self.items if t.id != tid and t.parent != tid]
        self.save()

    def set_note(self, tid, note):
        """保存备注，自动在前面加上日期戳 [YYYY-MM-DD]"""
        import re
        for t in self.items:
            if t.id == tid:
                today = time.strftime('%Y-%m-%d')
                # 去掉已有的日期戳，避免重复叠加
                note_clean = re.sub(r'^\s*\[\d{4}-\d{2}-\d{2}(\s+\d{2}:\d{2})?\]\s*', '', note)
                t.note = f'[{today}] {note_clean}'.strip()
                self.save()
                return True
        return False

    def get_projects(self):
        """获取所有顶级项目"""
        return sorted([t for t in self.items if not t.parent],
                      key=lambda t: (t.done, t.created or ''), reverse=False)

    def get_children(self, pid):
        """获取某个项目的子事项"""
        return sorted([t for t in self.items if t.parent == pid],
                      key=lambda t: (t.done, t.created or ''), reverse=False)

    def get_all(self):
        """按树状顺序返回"""
        result = []
        for proj in self.get_projects():
            result.append(proj)
            for sub in self.get_children(proj.id):
                result.append(sub)
        return result

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(TODOS_FILE, 'w', encoding='utf-8') as f:
            json.dump([t.to_dict() for t in self.items], f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.isfile(TODOS_FILE):
            try:
                with open(TODOS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    migrated = False
                    for d in data:
                        t = Todo.from_dict(d)
                        # 迁移: 老数据备注没有日期戳，自动补上 [YYYY-MM-DD]
                        if t.note and not t.note.startswith('['):
                            d_date = t.created[:10] if t.created else time.strftime('%Y-%m-%d')
                            t.note = f'[{d_date}] {t.note}'
                            migrated = True
                        self.items.append(t)
                    if self.items:
                        ids = [int(t.id.split('_')[0][1:]) for t in self.items if t.id]
                        self._counter = max(ids) if ids else 0
                    if migrated:
                        self.save()
            except Exception:
                pass
