# -*- coding: utf-8 -*-
"""日程 / 待办 / 提醒系统"""
import json, os, time, threading, sys


# 数据目录优先级：.env 的 DATA_DIR > exe 同目录/data > 项目根/data
def _resolve_data_dir():
    env_dir = os.environ.get('DATA_DIR', '').strip()
    if env_dir:
        return env_dir
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'data')
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


DATA_DIR = _resolve_data_dir()
SCHED_FILE = os.path.join(DATA_DIR, 'schedule.json')

class Reminder:
    """一条提醒"""
    def __init__(self, rid, text, dt_str, repeat='once', category='一般'):
        self.id = rid
        self.text = text          # 提醒内容
        self.dt_str = dt_str      # ISO格式 "2026-07-22 14:30"
        self.repeat = repeat      # once / daily / weekly / workday
        self.category = category  # 一般 / 工作 / 个人
        self.enabled = True
        self.last_trigger = None  # 上次触发时间, 避免重复弹

    def to_dict(self):
        return {'id':self.id,'text':self.text,'dt_str':self.dt_str,
                'repeat':self.repeat,'category':self.category,
                'enabled':self.enabled,'last_trigger':self.last_trigger}

    @staticmethod
    def from_dict(d):
        r = Reminder(d['id'], d['text'], d['dt_str'], d.get('repeat','once'), d.get('category','一般'))
        r.enabled = d.get('enabled', True)
        r.last_trigger = d.get('last_trigger')
        return r


class Scheduler:
    def __init__(self, on_remind=None):
        """on_remind: 回调函数(提醒文本)"""
        self.reminders = []
        self.on_remind = on_remind
        self._counter = 0
        self.load()

    def add(self, text, dt_str, repeat='once', category='一般'):
        self._counter += 1
        r = Reminder(f'r{self._counter}_{int(time.time())}', text, dt_str, repeat, category)
        self.reminders.append(r)
        self.save()
        return r

    def remove(self, rid):
        self.reminders = [r for r in self.reminders if r.id != rid]
        self.save()

    def toggle(self, rid):
        for r in self.reminders:
            if r.id == rid:
                r.enabled = not r.enabled
                self.save()
                return r.enabled
        return None

    def check(self):
        """检查是否有到期的提醒, 返回 [(text, category), ...]"""
        now = time.time()
        triggered = []
        for r in self.reminders:
            if not r.enabled:
                continue
            try:
                dt = time.mktime(time.strptime(r.dt_str, '%Y-%m-%d %H:%M'))
            except:
                continue
            if r.last_trigger:
                try:
                    last = time.mktime(time.strptime(r.last_trigger, '%Y-%m-%d'))
                except:
                    last = 0
            else:
                last = 0

            should_trigger = False
            # 到时间了且今天没触发过
            if now >= dt and r.last_trigger is None:
                should_trigger = True
            elif now >= dt and r.repeat == 'daily':
                today = time.strftime('%Y-%m-%d')
                if r.last_trigger != today:
                    should_trigger = True
            elif now >= dt and r.repeat == 'weekly':
                today = time.strftime('%Y-%m-%d')
                # 每周同一天
                if r.last_trigger is None or r.last_trigger < today:
                    wd = time.localtime().tm_wday
                    try:
                        orig_wd = time.localtime(dt).tm_wday
                        if wd == orig_wd:
                            should_trigger = True
                    except:
                        pass
            elif now >= dt and r.repeat == 'workday':
                wd = time.localtime().tm_wday
                if wd < 5:  # 周一到周五
                    today = time.strftime('%Y-%m-%d')
                    if r.last_trigger != today:
                        should_trigger = True

            if should_trigger:
                r.last_trigger = time.strftime('%Y-%m-%d')
                triggered.append((r.text, r.category))
                self.save()
        return triggered

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(SCHED_FILE, 'w', encoding='utf-8') as f:
            json.dump([r.to_dict() for r in self.reminders], f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.isfile(SCHED_FILE):
            try:
                with open(SCHED_FILE, 'r', encoding='utf-8') as f:
                    for d in json.load(f):
                        self.reminders.append(Reminder.from_dict(d))
                    if self.reminders:
                        ids = [int(r.id.split('_')[0][1:]) for r in self.reminders if r.id]
                        self._counter = max(ids) if ids else 0
            except Exception:
                pass

    def get_all(self):
        return sorted(self.reminders, key=lambda r: r.dt_str)
