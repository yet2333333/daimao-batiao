# -*- coding: utf-8 -*-
"""成就 + 成长值系统"""
import json, os, time, sys


# 数据目录优先级：.env 的 DATA_DIR > exe 同目录/data > 项目根/data
def _resolve_data_dir():
    env_dir = os.environ.get('DATA_DIR', '').strip()
    if env_dir:
        return env_dir
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(os.path.dirname(os.path.abspath(sys.executable)), 'data')
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')


DATA_DIR = _resolve_data_dir()
STATS_FILE = os.path.join(DATA_DIR, 'stats.json')
ACHIEVEMENTS_FILE = os.path.join(DATA_DIR, 'achievements.json')

ACHIEVEMENT_DEFS = {
    # ===== 互动类 =====
    'first_click':   {'name':'初次触碰',  'desc':'第一次戳猫',          'icon':'👆', 'xp':10},
    'click_10':      {'name':'小试牛刀',  'desc':'戳猫10次',            'icon':'🖱️', 'xp':15},
    'click_50':      {'name':'猫奴入门',  'desc':'戳猫50次',            'icon':'🖱️', 'xp':30},
    'click_200':     {'name':'停不下来',  'desc':'戳猫200次',           'icon':'✋', 'xp':60},
    'click_500':     {'name':'戳猫狂魔',  'desc':'戳猫500次',           'icon':'💯', 'xp':100},
    'click_1000':    {'name':'神级猫奴',  'desc':'戳猫1000次',          'icon':'👑', 'xp':200},
    # ===== 拖拽类 =====
    'drag_10':       {'name':'拖拽新手',  'desc':'拖拽10次',            'icon':'🎯', 'xp':15},
    'drag_30':       {'name':'拖拽大师',  'desc':'拖拽30次',            'icon':'🎯', 'xp':30},
    'drag_100':      {'name':'大力士',    'desc':'拖拽100次',           'icon':'💪', 'xp':60},
    'drag_500':      {'name':'搬家师傅',  'desc':'拖拽500次',           'icon':'📦', 'xp':100},
    'throw_5':       {'name':'抛掷新手',  'desc':'扔出去5次',           'icon':'🎱', 'xp':35},
    'throw_20':      {'name':'抛掷高手',  'desc':'扔出去20次',          'icon':'🎳', 'xp':70},
    'throw_50':      {'name':'抛掷大师',  'desc':'扔出去50次',          'icon':'🎯', 'xp':120},
    # ===== 搜索/Q&A =====
    'qa_first':      {'name':'初次对话',  'desc':'首次使用问答',         'icon':'💬', 'xp':30},
    'qa_10':         {'name':'侃侃而谈',  'desc':'问答10次',             'icon':'🗣️', 'xp':60},
    'qa_50':         {'name':'话痨猫',    'desc':'问答50次',             'icon':'📢', 'xp':120},
    'qa_200':        {'name':'知无不言',  'desc':'问答200次',            'icon':'🎙️', 'xp':250},
    # ===== 搜索类 =====
    'search_kb_10':  {'name':'学霸猫',    'desc':'知识库搜索10次',       'icon':'📚', 'xp':40},
    'search_kb_50':  {'name':'知识宝库',  'desc':'知识库搜索50次',       'icon':'📖', 'xp':80},
    'search_web_5':  {'name':'冲浪猫',    'desc':'网络搜索5次',         'icon':'🌊', 'xp':30},
    'search_web_20': {'name':'互联网猫',  'desc':'网络搜索20次',        'icon':'🌐', 'xp':60},
    'search_total_100': {'name':'搜索狂', 'desc':'搜索累计100次',        'icon':'🔍', 'xp':150},
    # ===== 等级 =====
    'level_2':       {'name':'初出茅庐',  'desc':'达到2级',              'icon':'⭐', 'xp':30},
    'level_3':       {'name':'渐入佳境',  'desc':'达到3级',              'icon':'⭐', 'xp':50},
    'level_5':       {'name':'小有所成',  'desc':'达到5级',              'icon':'🌟', 'xp':100},
    'level_10':      {'name':'资深猫奴',  'desc':'达到10级',             'icon':'👑', 'xp':200},
    'level_20':      {'name':'猫咪宗师',  'desc':'达到20级',             'icon':'🏆', 'xp':400},
    # ===== 好感度 =====
    'affection_10':  {'name':'初见好感',  'desc':'好感度10',              'icon':'💗', 'xp':20},
    'affection_25':  {'name':'投缘',      'desc':'好感度25',              'icon':'💓', 'xp':40},
    'affection_50':  {'name':'好朋友',    'desc':'好感度50',              'icon':'🤝', 'xp':80},
    'affection_80':  {'name':'形影不离',  'desc':'好感度80',              'icon':'💞', 'xp':150},
    'affection_100': {'name':'满满的爱',  'desc':'好感度100',             'icon':'💖', 'xp':200},
    # ===== 连续登录 =====
    'consecutive_1': {'name':'初次见面',  'desc':'首次上线',              'icon':'🌱', 'xp':5},
    'consecutive_3': {'name':'三日不辍',  'desc':'连续使用3天',           'icon':'🔥', 'xp':60},
    'consecutive_7': {'name':'忠实伙伴',  'desc':'连续使用7天',           'icon':'💎', 'xp':150},
    'consecutive_30':{'name':'三十如一',  'desc':'连续使用30天',          'icon':'🌟', 'xp':400},
    'consecutive_100':{'name':'百日纪念', 'desc':'连续使用100天',         'icon':'🏆', 'xp':1000},
    # ===== 日程类 =====
    'first_reminder':{'name':'闹钟猫',    'desc':'设置第一个提醒',        'icon':'⏰', 'xp':20},
    'reminder_5':    {'name':'时间管理新手','desc':'设置5个提醒',          'icon':'📅', 'xp':30},
    'reminder_10':   {'name':'时间管理猫','desc':'设置10个提醒',          'icon':'📅', 'xp':50},
    'reminder_30':   {'name':'日程达人',  'desc':'设置30个提醒',          'icon':'🗓️', 'xp':120},
    'reminder_50':   {'name':'时间大师',  'desc':'设置50个提醒',          'icon':'⏳', 'xp':200},
    # ===== 管道类 =====
    'pipe_first':    {'name':'管道工程师','desc':'首次管道计算',          'icon':'🔧', 'xp':50},
    'pipe_10':       {'name':'管道老手',  'desc':'管道计算10次',          'icon':'⚙️', 'xp':80},
    'pipe_50':       {'name':'管道专家',  'desc':'管道计算50次',          'icon':'🔬', 'xp':200},
    'pipe_100':      {'name':'管道宗师',  'desc':'管道计算100次',         'icon':'🎓', 'xp':400},
    'pipe_liquid':   {'name':'液体专家',  'desc':'使用液体计算',          'icon':'💧', 'xp':30},
    'pipe_air':      {'name':'气体专家',  'desc':'使用压空计算',          'icon':'💨', 'xp':30},
    'pipe_steam':    {'name':'蒸汽专家',  'desc':'使用蒸汽计算',          'icon':'♨️', 'xp':30},
    'pipe_all':      {'name':'集齐三家',  'desc':'三种流体都用过',        'icon':'🌈', 'xp':100},
    # ===== 时间成就 =====
    'night_owl':     {'name':'夜猫子',    'desc':'凌晨1-5点在线',         'icon':'🦉', 'xp':25},
    'morning_bird':  {'name':'早起的猫',  'desc':'早上6-8点在线',         'icon':'🌅', 'xp':25},
    'lunch_time':    {'name':'干饭猫',    'desc':'中午11-13点在线',       'icon':'🍚', 'xp':20},
    'late_night':    {'name':'深夜猫',    'desc':'晚上22-24点在线',       'icon':'🌙', 'xp':20},
    'work_hours':    {'name':'工作猫',    'desc':'工作时间9-18点在线',    'icon':'💼', 'xp':15},
    # ===== 动作类 =====
    'jump_10':       {'name':'弹跳新手',  'desc':'跳跃10次',              'icon':'🦘', 'xp':20},
    'jump_20':       {'name':'弹跳高手',  'desc':'跳跃20次',              'icon':'🦘', 'xp':40},
    'jump_100':      {'name':'弹跳达人',  'desc':'跳跃100次',             'icon':'🏀', 'xp':120},
    'walk_10':       {'name':'散步达人',  'desc':'散步10次',              'icon':'🚶', 'xp':30},
    'walk_50':       {'name':'远足爱好者','desc':'散步50次',              'icon':'🥾', 'xp':100},
    # ===== 弹窗拦截 =====
    'kill_first':    {'name':'广告杀手',  'desc':'首次拦截弹窗',           'icon':'🗡️', 'xp':30},
    'kill_10':       {'name':'广告终结者','desc':'拦截10次弹窗',           'icon':'🗡️', 'xp':60},
    'kill_100':      {'name':'清净大师',  'desc':'拦截100次弹窗',          'icon':'🛡️', 'xp':150},
    'kill_500':      {'name':'桌面守护者','desc':'拦截500次弹窗',          'icon':'👑', 'xp':300},
    # ===== 跨功能 =====
    'chatty':        {'name':'健谈猫',    'desc':'闲聊模式互动100次',     'icon':'💬', 'xp':80},
    'scholar':       {'name':'学者猫',    'desc':'问答模式50次',          'icon':'🎓', 'xp':100},
    'multi_feature': {'name':'多才多艺',  'desc':'使用过所有主要功能',     'icon':'🌟', 'xp':200},
    'all_emotions':  {'name':'百变表情',  'desc':'触发所有9种表情',       'icon':'🎭', 'xp':150},
    'first_ach':     {'name':'第一枚成就','desc':'解锁第一个成就',         'icon':'🏅', 'xp':10},
    'ach_10':        {'name':'成就收集者','desc':'解锁10个成就',           'icon':'🏅', 'xp':50},
    'ach_25':        {'name':'成就猎人',  'desc':'解锁25个成就',           'icon':'🏆', 'xp':150},
    'ach_40':        {'name':'成就大师',  'desc':'解锁40个成就',           'icon':'👑', 'xp':300},
    'ach_50':        {'name':'成就全满',  'desc':'解锁50个成就',           'icon':'🏆', 'xp':500},
}


class Stats:
    def __init__(self):
        self.level = 1
        self.xp = 0
        self.affection = 0
        self.total_clicks = 0
        self.total_drags = 0
        self.total_searches_kb = 0
        self.total_searches_web = 0
        self.total_chats = 0           # 闲聊模式点击
        self.total_qa_actions = 0      # 问答模式
        self.total_jumps = 0
        self.total_walks = 0
        self.total_throws = 0
        self.total_reminders = 0
        self.total_pipe_calcs = 0
        self.total_killed_notifs = 0
        self.used_pipe_liquid = False
        self.used_pipe_air = False
        self.used_pipe_steam = False
        self.unlocked_emotions = set() # 记录触发过的表情
        self.birthday = time.strftime('%Y-%m-%d %H:%M')
        self.last_date = time.strftime('%Y-%m-%d')
        self.consecutive_days = 1
        self.total_days = 1
        self.new_achievements = []

    def xp_for_level(self, lv):
        return lv * 100 + 50

    def add_xp(self, amount):
        self.xp += amount
        old_level = self.level
        while self.xp >= self.xp_for_level(self.level):
            self.xp -= self.xp_for_level(self.level)
            self.level += 1
        if self.level > old_level:
            return self.level
        return None

    def add_affection(self, amount):
        self.affection = min(100, max(0, self.affection + amount))

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        d = dict(self.__dict__)
        # set → list (JSON 不支持 set)
        for k in list(d.keys()):
            if isinstance(d[k], set):
                d[k] = list(d[k])
        with open(STATS_FILE, 'w', encoding='utf-8') as f:
            json.dump(d, f, ensure_ascii=False, indent=2)

    def load(self):
        if os.path.isfile(STATS_FILE):
            try:
                with open(STATS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for k, v in data.items():
                        if k in self.__dict__:
                            setattr(self, k, v)
                # JSON 的 set 会变成 list, 转回去
                if isinstance(self.unlocked_emotions, list):
                    self.unlocked_emotions = set(self.unlocked_emotions)
            except Exception:
                pass
        # 天数更新
        today = time.strftime('%Y-%m-%d')
        if self.last_date != today:
            self.total_days += 1
            if (time.mktime(time.strptime(today, '%Y-%m-%d')) -
                time.mktime(time.strptime(self.last_date, '%Y-%m-%d'))) == 86400:
                self.consecutive_days += 1
            else:
                self.consecutive_days = 1
            self.last_date = today
            self.add_affection(3)  # 每天上线好感度+3


class AchievementTracker:
    def __init__(self, stats):
        self.stats = stats
        self.unlocked = set()
        self.just_unlocked = []
        if os.path.isfile(ACHIEVEMENTS_FILE):
            try:
                with open(ACHIEVEMENTS_FILE, 'r', encoding='utf-8') as f:
                    self.unlocked = set(json.load(f))
            except Exception:
                pass

    def save(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(ACHIEVEMENTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(list(self.unlocked), f, ensure_ascii=False, indent=2)

    def check(self):
        self.just_unlocked = []
        s = self.stats
        # 计算本次检查中新解锁的条件（不含成就进度类，避免循环）
        cond_any_other = (
            s.total_clicks >= 1 or s.total_drags >= 1 or s.total_searches_kb >= 1 or
            s.total_searches_web >= 1 or s.total_chats >= 1 or s.total_qa_actions >= 1 or
            s.total_jumps >= 1 or s.total_walks >= 1 or s.total_throws >= 1 or
            s.total_reminders >= 1 or s.total_pipe_calcs >= 1 or s.level >= 2 or
            s.affection >= 10 or s.consecutive_days >= 1 or s.total_killed_notifs >= 1
        )
        checks = {
            # 互动
            'first_click':   s.total_clicks >= 1,
            'click_10':      s.total_clicks >= 10,
            'click_50':      s.total_clicks >= 50,
            'click_200':     s.total_clicks >= 200,
            'click_500':     s.total_clicks >= 500,
            'click_1000':    s.total_clicks >= 1000,
            # 拖拽
            'drag_10':       s.total_drags >= 10,
            'drag_30':       s.total_drags >= 30,
            'drag_100':      s.total_drags >= 100,
            'drag_500':      s.total_drags >= 500,
            'throw_5':       s.total_throws >= 5,
            'throw_20':      s.total_throws >= 20,
            'throw_50':      s.total_throws >= 50,
            # 搜索/q&a
            'search_kb_10':  s.total_searches_kb >= 10,
            'search_kb_50':  s.total_searches_kb >= 50,
            'search_web_5':  s.total_searches_web >= 5,
            'search_web_20': s.total_searches_web >= 20,
            'search_total_100': (s.total_searches_kb + s.total_searches_web) >= 100,
            'qa_first':      s.total_qa_actions >= 1,
            'qa_10':         s.total_qa_actions >= 10,
            'qa_50':         s.total_qa_actions >= 50,
            'qa_200':        s.total_qa_actions >= 200,
            # 等级
            'level_2':       s.level >= 2,
            'level_3':       s.level >= 3,
            'level_5':       s.level >= 5,
            'level_10':      s.level >= 10,
            'level_20':      s.level >= 20,
            # 好感度
            'affection_10':  s.affection >= 10,
            'affection_25':  s.affection >= 25,
            'affection_50':  s.affection >= 50,
            'affection_80':  s.affection >= 80,
            'affection_100': s.affection >= 100,
            # 连续
            'consecutive_1': s.consecutive_days >= 1,
            'consecutive_3': s.consecutive_days >= 3,
            'consecutive_7': s.consecutive_days >= 7,
            'consecutive_30':s.consecutive_days >= 30,
            'consecutive_100':s.consecutive_days >= 100,
            # 日程
            'first_reminder':s.total_reminders >= 1,
            'reminder_5':    s.total_reminders >= 5,
            'reminder_10':   s.total_reminders >= 10,
            'reminder_30':   s.total_reminders >= 30,
            'reminder_50':   s.total_reminders >= 50,
            # 管道
            'pipe_first':    s.total_pipe_calcs >= 1,
            'pipe_10':       s.total_pipe_calcs >= 10,
            'pipe_50':       s.total_pipe_calcs >= 50,
            'pipe_100':      s.total_pipe_calcs >= 100,
            'pipe_liquid':   s.used_pipe_liquid,
            'pipe_air':      s.used_pipe_air,
            'pipe_steam':    s.used_pipe_steam,
            'pipe_all':      s.used_pipe_liquid and s.used_pipe_air and s.used_pipe_steam,
            # 跨功能
            'chatty':        s.total_chats >= 100,
            'scholar':       s.total_qa_actions >= 50,
            'multi_feature': (s.total_pipe_calcs > 0 and s.total_searches_kb > 0
                              and s.total_searches_web > 0 and s.total_reminders > 0
                              and s.total_qa_actions > 0),
            'all_emotions':  len(s.unlocked_emotions) >= 9,
            # 动作
            'jump_10':       s.total_jumps >= 10,
            'jump_20':       s.total_jumps >= 20,
            'jump_100':      s.total_jumps >= 100,
            'walk_10':       s.total_walks >= 10,
            'walk_50':       s.total_walks >= 50,
            # 弹窗拦截
            'kill_first':    s.total_killed_notifs >= 1,
            'kill_10':       s.total_killed_notifs >= 10,
            'kill_100':      s.total_killed_notifs >= 100,
            'kill_500':      s.total_killed_notifs >= 500,
        }
        # 时间成就
        h = time.localtime().tm_hour
        if h in range(1, 6): checks['night_owl'] = True
        if h in range(6, 9): checks['morning_bird'] = True
        if h in range(11, 14): checks['lunch_time'] = True
        if h in range(22, 25) or h == 0: checks['late_night'] = True
        if h in range(9, 19): checks['work_hours'] = True
        # 第一枚成就 (一旦有其他成就解锁, 这个也解锁)
        if cond_any_other and 'first_ach' not in self.unlocked:
            checks['first_ach'] = True
        # 成就数量里程碑 (不计 first_ach 本身)
        ach_count = len(self.unlocked - {'first_ach'}) + len(self.just_unlocked)
        if ach_count >= 10: checks['ach_10'] = True
        if ach_count >= 25: checks['ach_25'] = True
        if ach_count >= 40: checks['ach_40'] = True
        if ach_count >= 50: checks['ach_50'] = True
        if h in range(9, 19): checks['work_hours'] = True

        for key, cond in checks.items():
            if cond and key not in self.unlocked:
                self.unlocked.add(key)
                self.just_unlocked.append(key)
                self.stats.add_xp(ACHIEVEMENT_DEFS[key]['xp'])
                self.stats.add_affection(5)
        if self.just_unlocked:
            self.save()
            self.stats.save()
        return self.just_unlocked

    def get_all(self):
        result = []
        for key, defn in ACHIEVEMENT_DEFS.items():
            result.append((key, defn, key in self.unlocked))
        return result
