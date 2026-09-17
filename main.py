# -*- coding: utf-8 -*-
"""
智能桌面化工伴侣猫 - 桌面宠物 v5
"""
import os, sys

# 设置 TCL/TK 数据目录（必须在 import tkinter 之前）
_TK_BASE = os.path.dirname(os.path.abspath(__file__))
if hasattr(sys, '_MEIPASS'):
    _TK_BASE = sys._MEIPASS

# 源码运行时，把 tkinter 包路径加入 sys.path
# managed Python 是 slim 安装，tkinter 不在 sys.path 默认位置
import importlib
_tkinter_lib = os.path.join(
    os.path.dirname(os.path.dirname(_TK_BASE)),
    'binaries', 'python', 'versions', '3.13.12', 'Lib'
) if not hasattr(sys, '_MEIPASS') else _TK_BASE
# 尝试多个可能的 tkinter 位置
_candidates = [
    os.path.join(_TK_BASE, 'tkinter'),
    os.environ.get('DAIMAO_TKINTER_PATH', ''),
]
for cand in _candidates:
    if cand and os.path.isdir(cand) and cand not in sys.path:
        sys.path.insert(0, cand)
        break

_tcl_dir = os.path.join(_TK_BASE, '_tcl_data')
if os.path.isdir(_tcl_dir):
    os.environ['TCL_LIBRARY'] = _tcl_dir
    tk_dir = os.path.join(_TK_BASE, '_tk_data')
    if os.path.isdir(tk_dir):
        os.environ['TK_LIBRARY'] = tk_dir

import tkinter as tk
import random, time, math, json, tempfile, subprocess, ctypes
import ctypes.wintypes

# 模块
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules'))
import urllib.request, urllib.parse, re, sqlite3

# ====================== 载入 .env ======================
# 必须在导入子模块之前执行：子模块在 import 时就要读 DATA_DIR / SOP_DIR
def _load_env():
    """从 .env 读取本机配置：密钥与本地路径不进版本库"""
    env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env')
    if not os.path.isfile(env_path):
        return
    try:
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except Exception:
        pass


_load_env()

# ====================== 导入子模块 ======================
def _mod_dir():
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, 'modules')
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), 'modules')

MOD_DIR = _mod_dir()
if os.path.isdir(MOD_DIR):
    sys.path.insert(0, os.path.dirname(MOD_DIR))

from modules import stats as mod_stats
from modules import scheduler as mod_scheduler
from modules import pipe_calc as mod_pipe
from modules import notifilter as mod_noti

# ====================== 常量 ======================
# 化工知识库（可选）：在 .env 里填自己的路径，留空则自动关闭检索功能
KB_ROOT = os.environ.get('KB_ROOT', '')
RAG_DB = os.environ.get('RAG_DB', '')

# 中英文同义词映射（搜中文时自动查英文关键词覆盖 Perry 等英文手册）
BILINGUAL_MAP = {
    '分布器': 'distributor', '分布管': 'distributor pipe', '分布器计算': 'distributor calculation design',
    '换热器': 'heat exchanger', '换热器设计': 'heat exchanger design',
    '精馏': 'distillation', '精馏塔': 'distillation column',
    '填料': 'packing', '填料塔': 'packed column',
    '反应器': 'reactor', '反应器设计': 'reactor design',
    '吸收': 'absorption', '吸收塔': 'absorption column',
    '泵': 'pump', '泵选型': 'pump selection',
    '糠醛': 'furfural', '糠醇': 'furfuryl alcohol',
    '加氢': 'hydrogenation', '加氢反应器': 'hydrogenation reactor',
    '压降': 'pressure drop', '压降计算': 'pressure drop calculation',
    '孔板': 'orifice plate', '孔板波纹': 'structured packing',
    '安全阀': 'safety valve', '安全阀计算': 'safety valve calculation sizing',
    '管道': 'pipe', '管道计算': 'pipe calculation sizing',
    '蒸发': 'evaporation', '结晶': 'crystallization',
    '干燥': 'drying', '过滤': 'filtration',
    '搅拌': 'agitation mixing', '搅拌器': 'agitator mixer',
    '膜分离': 'membrane separation',
}


def rag_search(query, limit=5, dir_hint=None):
    """知识库检索: FTS + LIKE 兜底 + os.walk 三路
       dir_hint: 可选子目录名 (如 'Section_14') 直接在指定目录下查找原文"""
    import re as _re
    # FTS5 不支持中文分词，预处理：英文/数字术语 + 中文关键词 分别搜
    en_terms = _re.findall(r'[A-Za-z0-9]+', query)
    cn_terms = _re.findall(r'[\u4e00-\u9fff]+', query)
    has_complex = bool(en_terms) and bool(cn_terms)

    # 生成变体查询：352Y → [352Y, M352Y, 352]
    fts_queries = list(en_terms)
    for term in en_terms:
        if _re.match(r'^\d+[A-Za-z]', term):
            m_var = 'M' + term.upper()
            if m_var not in fts_queries: fts_queries.append(m_var)
            num_only = _re.match(r'^(\d+)', term).group(1)
            if num_only not in fts_queries: fts_queries.append(num_only)

    results = []
    seen = set()

    # 如果指定了目录过滤，直接搜原文 (os.walk 限于该目录)
    if dir_hint:
        _search_dir = os.path.join(KB_ROOT, dir_hint) if os.path.isdir(os.path.join(KB_ROOT, dir_hint)) else KB_ROOT
        _kw = query.split()
        for root, dirs, files in os.walk(_search_dir):
            for fname in files:
                if not fname.endswith('.md'): continue
                full = os.path.join(root, fname)
                try:
                    with open(full, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read().lower()
                except: continue
                for kw in _kw:
                    if kw.lower() in content:
                        fn_short = full.replace(KB_ROOT + '\\', '').replace('\\', '/')
                        idx = content.find(kw.lower())
                        key = fn_short + str(idx) + 'dir'
                        if key in seen: continue
                        seen.add(key)
                        preview = content[max(0,idx-30):idx+300].strip()
                        results.append((fn_short, 0, preview, -99))
                        break  # 一个关键词匹配即可
                if len(results) >= limit * 2: break
            if len(results) >= limit * 2: break
        return results[:limit * 2]

    # 方法A: FTS（英文/数字术语 + 变体）
    if os.path.isfile(RAG_DB):
        try:
            db = sqlite3.connect(RAG_DB)
            cur = db.cursor()
            if not fts_queries and has_complex:
                fts_queries = [query]
            for fq in fts_queries:
                try:
                    cur.execute("""
                        SELECT rowid, filename, path, content, rank
                        FROM chunks_fts
                        WHERE chunks_fts MATCH ? ORDER BY rank LIMIT ?
                    """, (fq, limit * 2))
                    for cid, fn, p, txt, rk in cur.fetchall():
                        key = str(fn) + 'id' + str(cid)
                        if key not in seen:
                            seen.add(key)
                            _txt = (txt or '')
                            # 关键词居中截断（关键数据 300 m²/m³ 落在 1260 时也能取到）
                            _best = 0
                            for kw in en_terms:
                                _pos = _txt.find(kw)
                                if _pos > _best:
                                    _best = _pos
                            if _best > 0:
                                clean = _txt[max(0, _best - 100):_best + 800]
                            else:
                                clean = _txt[:2000]
                            results.append((fn, p, clean, rk))
                except Exception:
                    continue

            # 方法A2: LIKE 模糊匹配（兜底搜 352.Y 这种带点号变体）
            for term in en_terms:
                if len(term) >= 3:
                    # 多种变体：原样、点号、大写、+Y
                    variants = [term, term.upper(), term + '.Y', term.upper() + '.Y']
                    # 数字+字母组合，加 M 前缀变体（带和不带点号）
                    if _re.match(r'^\d+[A-Za-z]', term):
                        m_var = 'M' + term.upper()
                        variants.append(m_var)
                        # 重要：M352.Y（带点号）才对得上 TR-178 里的写法
                        m_dot = 'M' + term.upper()[:-1] + '.' + term.upper()[-1]
                        variants.append(m_dot)
                        variants.append(m_var + '.' + term.upper()[-1])
                    for v in variants:
                        try:
                            cur.execute("""
                                SELECT id, c1, c2, c0 FROM chunks_fts_content
                                WHERE c0 LIKE ? LIMIT 50
                            """, ('%' + v + '%',))
                            for cid, fn, p, txt in cur.fetchall():
                                # 用 id 作唯一标识（c1/c2 在同一文件的所有 chunk 里相同）
                                key = str(fn) + 'id' + str(cid) + 'like_' + v
                                if key not in seen:
                                    seen.add(key)
                                    _txt = (txt or '')
                                    # 截断：优先以关键词位置居中，整段 ≤ 2000 字符
                                    _pos = _txt.find(v)
                                    if _pos >= 0:
                                        # 包含所有关键词位置（向前 + 关键词后保留 800 字符）
                                        clean = _txt[max(0, _pos - 100):_pos + 800]
                                    else:
                                        clean = _txt[:2000]
                                    results.append((fn, p, clean, -50))
                        except Exception:
                            continue
            db.close()
        except Exception as e:
            print(f'[FTS错误] {e}')

    # 方法B: os.walk 原生搜索 (兜底，中文拆字+英文保持)
    try:
        import re as _re2
        _raw = query.split() if query.split() else [query]
        _parts = []
        for w in _raw:
            cn = _re2.findall(r'[\u4e00-\u9fff]', w)
            if cn: _parts.extend(cn)  # 单字
            for i in range(len(cn)-1): _parts.append(cn[i]+cn[i+1])  # 双字
            en = _re2.findall(r'[A-Za-z0-9]+', w)
            _parts.extend(en)
        keywords = [k for k in _parts if len(k) >= 2]
        if not keywords: keywords = [query]
        found = 0
        for root, dirs, files in os.walk(KB_ROOT):
            if found >= limit * 3: break
            for fname in files:
                if not fname.endswith('.md'): continue
                full = os.path.join(root, fname)
                try:
                    with open(full, 'r', encoding='utf-8', errors='replace') as f:
                        content = f.read().lower()
                except: continue
                # 所有关键词 AND 匹配
                for kw in keywords:
                    if kw.lower() not in content: break
                else:
                    fn_short = full.replace(KB_ROOT + '\\', '').replace('\\', '/')
                    idx = content.find(keywords[0].lower())
                    key = fn_short + str(idx)
                    if key in seen: continue
                    seen.add(key)
                    preview = content[max(0,idx-30):idx+300].strip()
                    line_num = content[:idx].count('\n') + 1
                    results.append((fn_short, line_num, preview, -99))
                    found += 1
    except: pass

    return results[:limit * 2] if results else None

# 密钥、接口地址、模型名全部从 .env 读取，禁止硬编码进版本库
DEEPSEEK_KEY = os.environ.get('DEEPSEEK_API_KEY', '')
DEEPSEEK_API = os.environ.get('DEEPSEEK_API_BASE',
                              'https://api.deepseek.com/v1/chat/completions')
# 兼容 OpenAI 消息格式的服务商模型名各不相同：
# DeepSeek 官方 deepseek-chat / 通义 qwen-plus / 本地 Ollama 用实际模型名
MODEL_NAME = os.environ.get('MODEL_NAME', 'deepseek-chat')
W, H = 140, 140
CX, CY = W // 2, H // 2 + 5
CLR_BG = 'gray'
CLR_WHITE = '#FFFFFF'
CLR_BLACK = '#1a1a1a'
CLR_PINK = '#FFB6C1'
CLR_BLUSH = '#FFB3BA'
CLR_ORANGE = '#FF8C00'

_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/126.0.0.0'


def web_search(query, limit=5):
    try:
        enc = urllib.parse.quote(query)
        req = urllib.request.Request(f'https://www.bing.com/search?q={enc}',
                                     headers={'User-Agent': _UA})
        with urllib.request.urlopen(req, timeout=10) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception:
        return None
    results = []
    blocks = html.split('<li class="b_algo"')
    for block in blocks[1:limit+1]:
        hm = re.search(r'<h2[^>]*>(.*?)</h2>', block, re.DOTALL)
        if not hm: continue
        m = re.search(r'href="(https?://[^"]+)"[^>]*>(.*?)</a>', hm.group(1), re.DOTALL)
        if not m: continue
        title = re.sub(r'<[^>]+>', '', m.group(2)).strip()
        if not title: continue
        pm = re.search(r'<p[^>]*>(.*?)</p>', block, re.DOTALL)
        snippet = re.sub(r'<[^>]+>', '', pm.group(1)).strip() if pm else ''
        results.append((title, m.group(1), snippet[:300]))
    return results if results else []


def deepseek_chat(messages, max_tokens=2000, temperature=0.7):
    import traceback as _tb
    try:
        payload = json.dumps({
            'model': MODEL_NAME,
            'messages': messages,
            'max_tokens': max_tokens,
            'temperature': temperature,
        }, ensure_ascii=False)
        tmp = os.path.join(tempfile.gettempdir(), '_ds_req.json')
        with open(tmp, 'w', encoding='utf-8') as f: f.write(payload)
        si = subprocess.STARTUPINFO()
        si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        si.wShowWindow = 0
        r = subprocess.run(
            ['curl', '-s', '-X', 'POST', DEEPSEEK_API,
             '-H', 'Content-Type: application/json',
             '-H', 'Authorization: Bearer ' + DEEPSEEK_KEY,
             '-d', '@' + tmp, '--connect-timeout', '10', '--max-time', '90'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=95, startupinfo=si, creationflags=0x08000000)
        try: os.remove(tmp)
        except: pass
        raw = r.stdout
        if raw is None: raw = b''
        if isinstance(raw, bytes): out = raw.decode('utf-8', errors='replace')
        else: out = str(raw)
        err = r.stderr or b''
        if isinstance(err, bytes): err = err.decode('utf-8', errors='replace')
        if r.returncode != 0:
            return '[curl失败 rc=%d: %s]' % (r.returncode, err[:120] or 'no stderr')
        if not out.strip():
            return '[curl空响应: %s]' % (err[:100] or '无输出')
        try:
            ret = json.loads(out)
        except json.JSONDecodeError as je:
            return '[curl响应非JSON: %s | 响应前80: %s]' % (str(je)[:50], out[:80].replace('\n',' '))
        if 'error' in ret:
            return '[API错误: ' + str(ret['error'].get('message',''))[:80] + ']'
        if not ret.get('choices'): return '[API响应异常: 无choices]'
        content = ret['choices'][0].get('message', {}).get('content', '')
        if not content or not content.strip():
            # curl 路径也加重试: reasoning 模型可能烧完 token, 用 4000 重试
            try:
                payload2 = json.dumps({'model': MODEL_NAME,'messages': messages,
                                          'max_tokens': 4000,'temperature': temperature},
                                         ensure_ascii=False)
                tmp2 = os.path.join(tempfile.gettempdir(), '_ds_req2.json')
                with open(tmp2, 'w', encoding='utf-8') as f: f.write(payload2)
                r2 = subprocess.run(
                    ['curl', '-s', '-X', 'POST', DEEPSEEK_API,
                     '-H', 'Content-Type: application/json',
                     '-H', 'Authorization: Bearer ' + DEEPSEEK_KEY,
                     '-d', '@' + tmp2, '--connect-timeout', '10', '--max-time', '90'],
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    timeout=95, startupinfo=si, creationflags=0x08000000)
                try: os.remove(tmp2)
                except: pass
                if r2.returncode == 0:
                    ret2_raw = r2.stdout
                    if ret2_raw:
                        if isinstance(ret2_raw, bytes): ret2_out = ret2_raw.decode('utf-8', errors='replace')
                        else: ret2_out = str(ret2_raw)
                        if ret2_out.strip():
                            ret2 = json.loads(ret2_out)
                            if ret2.get('choices'):
                                content = ret2['choices'][0].get('message', {}).get('content', '')
            except Exception: pass
            if not content or not content.strip(): return '[API返回空白]'
        return content
    except FileNotFoundError: pass
    except Exception as e: return '[curl异常: ' + str(e)[:60] + ']'
    try:
        data = json.dumps({'model': MODEL_NAME,'messages':messages,'max_tokens':max_tokens,'temperature':temperature}).encode()
        try: import certifi, ssl; ctx = ssl.create_default_context(cafile=certifi.where())
        except: import ssl; ctx = ssl._create_unverified_context()
        headers = {'Content-Type':'application/json','Authorization':'Bearer '+DEEPSEEK_KEY}
        def _call(mt):
            d = json.dumps({'model':MODEL_NAME,'messages':messages,'max_tokens':mt,'temperature':temperature}).encode()
            req = urllib.request.Request(DEEPSEEK_API, data=d, headers=headers)
            raw = r.read() if (r := urllib.request.urlopen(req, timeout=90, context=ctx)) else b''
            text = raw.decode('utf-8', errors='replace') if isinstance(raw, bytes) else str(raw)
            if not text.strip():
                raise json.JSONDecodeError('空响应', '', 0)
            return json.loads(text)
        ret = _call(max_tokens)
        if 'error' in ret:
            return '[API错误: '+str(ret['error'].get('message',''))[:80]+']'
        msg = ret.get('choices',[{}])[0].get('message', {}) if ret.get('choices') else {}
        content = msg.get('content', '')
        # 如果 reasoning 把 token 全用完 content 为空, 重试用 4000 tokens
        if not content or not content.strip():
            try:
                ret2 = _call(4000)
                msg2 = ret2.get('choices',[{}])[0].get('message', {}) if ret2.get('choices') else {}
                content = msg2.get('content', '')
            except Exception:
                pass
        if not content or not content.strip():
            return '[API返回空白]'
        return content
    except Exception as e: return '[网络异常: '+str(e)[:60]+']'


class CatDraw:
    def __init__(self, canvas):
        self.cv = canvas; self.mx = CX; self.my = CY
        self.state = 'normal'; self._frame = 0; self._blink = 0; self._look_dir = (0,0)
        self._clock_timer = 0; self._pupil_size = 12
    def draw(self):
        import time as draw_time
        self._frame += 1

        if self._blink > 0: self._blink -= 1
        elif random.randint(0, 35) == 0: self._blink = 4

        if self._frame % 18 == 0 and self._blink == 0:
            self._look_dir = (random.choice([0,10,-10,0]), random.choice([0,6,-6,0]))
            self._pupil_size = random.choice([10,11,12,13])

        mx = min(75, max(65, self.mx + self._look_dir[0]))
        my = min(80, max(70, self.my + self._look_dir[1]))

        self.cv.delete('all')

        # 头顶时间
        timestr = draw_time.strftime('%H:%M:%S')
        self.cv.create_rectangle(0, 0, W, 20, fill='#3D3D3D', outline='')
        self.cv.create_text(70, 10, text=timestr, font=('Consolas', 10, 'bold'), fill='#FFFF00')

        # 头 - 更大更圆（参考图风格）
        self.cv.create_oval(4, 14, 136, 140, fill='#FFF', outline='#3D3D3D', width=2)

        # 三角耳 - 小巧顶端
        self.cv.create_polygon(22, 30, 14, 4, 48, 18, fill='#FFF', outline='#3D3D3D', width=2)
        self.cv.create_polygon(118, 30, 126, 4, 92, 18, fill='#FFF', outline='#3D3D3D', width=2)
        self.cv.create_polygon(28, 28, 18, 10, 44, 20, fill='#FFCCCB', outline='')
        self.cv.create_polygon(112, 28, 122, 10, 96, 20, fill='#FFCCCB', outline='')

        # 眼 - 更大萌眼
        ex1, ey1 = 50, 74
        ex2, ey2 = 90, 74
        ps = self._pupil_size
        if self._blink:
            self.cv.create_arc(ex1-16, ey1-3, ex1+16, ey1+3, start=0, extent=-180, style='arc', outline='#3D3D3D', width=2.5)
            self.cv.create_arc(ex2-16, ey2-3, ex2+16, ey2+3, start=0, extent=-180, style='arc', outline='#3D3D3D', width=2.5)
        else:
            ox = (mx-70)//3; oy = (my-74)//3
            # 大眼白
            self.cv.create_oval(ex1-17, ey1-17, ex1+17, ey1+17, fill='#FFF', outline='#3D3D3D', width=2)
            self.cv.create_oval(ex2-17, ey2-17, ex2+17, ey2+17, fill='#FFF', outline='#3D3D3D', width=2)
            # 大黑瞳
            self.cv.create_oval(ex1-ps+ox, ey1-ps+oy, ex1+ps+ox, ey1+ps+oy, fill='#222', outline='')
            self.cv.create_oval(ex2-ps+ox, ey2-ps+oy, ex2+ps+ox, ey2+ps+oy, fill='#222', outline='')
            # 双高光（更立体）
            self.cv.create_oval(ex1-8+ox, ey1-9+oy, ex1-2+ox, ey1-3+oy, fill='#FFF')
            self.cv.create_oval(ex2-8+ox, ey2-9+oy, ex2-2+ox, ey2-3+oy, fill='#FFF')
            self.cv.create_oval(ex1+3+ox, ey1+3+oy, ex1+6+ox, ey1+6+oy, fill='#FFF')
            self.cv.create_oval(ex2+3+ox, ey2+3+oy, ex2+6+ox, ey2+6+oy, fill='#FFF')


        # 三角鼻
        self.cv.create_polygon(67, 90, 73, 90, 70, 95, fill='#FFB6C1', outline='#3D3D3D', width=1.5)

        # 倒 M 嘴 - 从鼻尖直接弯到嘴角（左右两段弧）
        if self.state in ('happy', 'love'):
            color = '#E91E63' if self.state == 'love' else '#3D3D3D'
        else:
            color = '#3D3D3D'
        # 左弧：从鼻尖 (70,95) 到左嘴角 (58,107)
        self.cv.create_arc(58, 95, 70, 107, start=0, extent=-180, style='arc', outline=color, width=1.5)
        # 右弧：从鼻尖 (70,95) 到右嘴角 (82,107)
        self.cv.create_arc(70, 95, 82, 107, start=180, extent=180, style='arc', outline=color, width=1.5)

        # 表情
        if self.state == 'angry':
            for e in [ex1, ex2]:
                self.cv.create_line(e-8, ey1-8, e-2, ey1-1, width=2, fill='#E74C3C')
                self.cv.create_line(e-2, ey1-8, e-8, ey1-1, width=2, fill='#E74C3C')
        elif self.state == 'love':
            self.cv.create_text(45, 46, text='\u2665', font=('Arial', 12, 'bold'), fill='#E91E63')
            self.cv.create_text(95, 44, text='\u2665', font=('Arial', 12, 'bold'), fill='#E91E63')
        elif self.state == 'sleep':
            self.cv.create_text(95, 42, text='z', font=('Arial', 10), fill='#888')
            self.cv.create_text(100, 28, text='Z', font=('Arial', 13, 'bold'), fill='#666')
        elif self.state == 'confused':
            self.cv.create_text(96, 36, text='?', font=('Arial', 13, 'bold'), fill='#F57C00')
        elif self.state == 'wow':
            self.cv.create_oval(65, 88, 75, 97, fill='#3D3D3D', outline='')
            self.cv.create_oval(67, 90, 73, 95, fill='#FF9999', outline='')
        elif self.state == 'shy':
            self.cv.create_oval(46, 86, 55, 96, fill='#FF9999', outline='')
            self.cv.create_oval(85, 86, 94, 96, fill='#FF9999', outline='')
# end of draw
    def _eye_offset(self, mx, my, ex, ey, max_r=5):
        dx, dy = mx - ex, my - ey
        dist = math.sqrt(dx*dx + dy*dy)
        if dist < max_r * 2: return int(dx), int(dy)
        return int(dx/dist*max_r), int(dy/dist*max_r)


class CatApp:
    def __init__(self):
        self.root = tk.Tk()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.root.geometry(f'{W}x{H}+{sw-W-20}+{sh-H-60}')
        self.root.title("智能桌面化工伴侣猫")
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        try: self.root.attributes('-transparentcolor', CLR_BG)
        except: pass
        try:
            icon = os.path.join(MOD_DIR, '..', 'assets', 'cat_icon.ico')
            if os.path.isfile(icon): self.root.iconbitmap(icon)
        except: pass

        self.cv = tk.Canvas(self.root, width=W, height=H, bg=CLR_BG, highlightthickness=0)
        self.cv.pack()
        self.draw = CatDraw(self.cv)
        self.draw.draw()

        # 状态
        self.dragging = False; self.walking = False; self.throwing = False
        self.txv = self.tyv = 0; self.drags = 0; self.idle_since = time.time()
        self.chat_history = []
        self._notif_queue = []
        self._bubble_win = None; self._remind_check_id = None
        self._folded = set()

        # 数据目录
        exe_dir = os.path.dirname(sys.executable) if hasattr(sys, '_MEIPASS') else os.path.dirname(os.path.abspath(__file__))
        self.data_dir = os.path.join(exe_dir, 'data')
        os.makedirs(self.data_dir, exist_ok=True)

        # 统计 / 日程
        self.stats = mod_stats.Stats()
        self.scheduler = mod_scheduler.Scheduler(on_remind=self._on_remind)
        self.rag_ok = os.path.isfile(RAG_DB)

        # 待办
        from modules.todos import TodoList
        self.todos = TodoList()

        # 事件绑定
        self.cv.bind('<Button-1>', self.on_down)
        self.cv.bind('<B1-Motion>', self.on_move)
        self.cv.bind('<ButtonRelease-1>', self.on_up)
        self.cv.bind('<Button-3>', self._on_right)
        self.cv.bind('<Double-Button-1>', lambda e: self._open_qa_input())

        # 启动
        self._poll_mouse()
        self._remind_check()
        self._ad_scan_loop()
        self._idle_loop()

        # 全局热键绑定
        self.root.bind_all('<Key-b>', lambda e: self._toggle_hide())
        self.root.bind_all('<Key-B>', lambda e: self._toggle_hide())
        self.root.bind_all('<Escape>', lambda e: self._toggle_hide())
        self.root.bind_all('<Control-h>', lambda e: self._toggle_hide())
        self.root.bind_all('<Control-q>', lambda e: self._close_app())

        # 招呼语
        self.chat_history = [
            {'role':'system','content':'我是智能桌面化工伴侣猫'},
            {'role':'assistant','content':'\u55b6\u5570~\u6211\u53eb\u5446\u732b\u516b\u6761\uff01\u53cc\u51fb\u6211\u6253\u5f00\u95ee\u9898\u6846 (\u00b4\u00b7\u03c9\u00b7\u00b4)'}
        ]
        # 3秒后招呼气泡
        self.root.after(3000, lambda: self.bubble('\u55b6\u5570~\u6211\u662f\u5446\u732b\u516b\u6761\uff01'))

        # 招呼语 + B 键隐藏
        self.chat_history = [
            {'role':'system','content':'我是智能桌面化工伴侣猫,可爱的桌面宠物猫兼化工工艺小助手'},
            {'role':'assistant','content':'\u55b6\u5570~\u6211\u53eb\u5446\u732b\u516b\u6761\uff0c\u662f\u4f60\u7684\u684c\u9762\u5ba0\u7269\u732b\u517c\u5316\u5de5\u5de5\u827a\u5c0f\u52a9\u624b\uff01(=\uffe3\xdf\xe2*\u09f9\uff09\u00b4\u00b7\u03c9\u00b7\u00b4) \u6709\u5565\u9700\u8981\u5e2e\u5fd9\u7684\u5c3d\u7ba1\u8bf4\u55b6~'}
        ]
        # B 键隐藏

        # 首次启动气泡
        self.root.after(2000, lambda: self.bubble('\u55b6\u5570~\u6211\u662f\u5446\u732b\u516b\u6761~\u53cc\u51fb\u6211\u6253\u5f00\u95ee\u9898\u6846!'))

    def _center_win(self, win, w, h):
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            win.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
        except: pass

    def set_state(self, state, tmp=False):
        self.draw.state = state
        if tmp:
            self.root.after(2000, lambda: setattr(self.draw, 'state', 'normal') if self.draw.state == state else None)

    def refresh_draw(self):
        self.draw.draw()
        self.cv.update_idletasks()

    def _poll_mouse(self):
        try:
            pt = ctypes.wintypes.POINT()
            ctypes.windll.user32.GetCursorPos(ctypes.byref(pt))
            wx = self.root.winfo_rootx(); wy = self.root.winfo_rooty()
            target_x = pt.x - wx; target_y = pt.y - wy
            old_mx, old_my = self.draw.mx, self.draw.my
            self.draw.mx = int(0.8 * self.draw.mx + 0.2 * target_x)
            self.draw.my = int(0.8 * self.draw.my + 0.2 * target_y)
            if abs(self.draw.mx - old_mx) > 1 or abs(self.draw.my - old_my) > 1:
                self.refresh_draw()
        except: pass
        self.root.after(50, self._poll_mouse)

    def on_down(self, e):
        self.dx0, self.dy0 = e.x, e.y; self.dragging = False; self.last = time.time()

    def on_move(self, e):
        dx, dy = e.x - self.dx0, e.y - self.dy0
        if abs(dx) > 3 or abs(dy) > 3: self.dragging = True
        if self.dragging:
            x = self.root.winfo_x() + dx; y = self.root.winfo_y() + dy
            sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
            x = max(0, min(x, sw - W)); y = max(0, min(y, sh - H))
            self.root.geometry(f'+{x}+{y}')
            self.set_state('confused', True)

    def on_up(self, e):
        if self.dragging:
            self.drags += 1; self.dragging = False; self.stats.total_drags += 1
            self.throwing = True
            self.txv = random.randint(-10, 10)
            self.tyv = -random.randint(8, 13)
            self._throw_loop()
            self.set_state('wow', True); self.stats.xp += 2; self.stats.add_affection(-2); self.stats.save()
        else:
            self._click()
        self._after_action()

    def _show_achievement_popup(self, name):
        win = tk.Toplevel(self.root)
        win.title('成就解锁')
        win.attributes('-topmost', True)
        win.resizable(False, False)
        win.config(bg='#FFD700')
        self._center_win(win, 380, 240)

        tk.Label(win, text='\U0001f3c6', font=('Microsoft YaHei', 56), bg='#FFD700').pack(pady=(18, 0))
        tk.Label(win, text='成就解锁!', font=('Microsoft YaHei', 14, 'bold'),
                 fg='#8B4513', bg='#FFD700').pack()
        tk.Label(win, text=name, font=('Microsoft YaHei', 20, 'bold'),
                 fg='white', bg='#8B4513', pady=8, padx=40).pack(fill='x', pady=8)
        tk.Button(win, text='\U0001f389 太棒了!', command=win.destroy,
                  font=('Microsoft YaHei', 12, 'bold'), bg='#FF6B6B', fg='white',
                  width=12).pack(pady=(4, 16))
        win.lift()
        win.update()
        self.bubble('\U0001f389 ' + name + '!')
        self.root.after(30000, lambda: win.destroy() if win.winfo_exists() else None)

    def _check_achievements(self):
        s = self.stats
        already = set(getattr(s, '_popped', []))
        items = [
            ('total_clicks', 1, '初次触碰✨'),
            ('total_clicks', 10, '频繁戳猫'),
            ('total_clicks', 50, '猫奴入门'),
            ('total_clicks', 200, '戳猫上瘾'),
            ('total_drags', 5, '拖拽初体验'),
            ('total_drags', 50, '拖拽高手'),
            ('total_qa_actions', 5, '提问初试'),
            ('total_qa_actions', 30, '多嘴猫'),
            ('total_walks', 10, '散步者'),
            ('total_walks', 50, '运动达人'),
            ('total_throws', 5, '投接新手'),
            ('total_throws', 30, '空中飞猫'),
        ]
        for attr, threshold, name in items:
            key = f'{attr}_{threshold}'
            if key not in already and getattr(s, attr, 0) >= threshold:
                already.add(key)
                self.bubble('✨ 解锁：' + name)
                break
        s._popped = list(already)

    def _show_achievement_popup(self, name):
        win = tk.Toplevel(self.root)
        win.title('成就解锁')
        win.attributes('-topmost', True)
        win.resizable(False, False)
        win.config(bg='#FFD700')
        self._center_win(win, 380, 240)

        tk.Label(win, text='\U0001f3c6', font=('Microsoft YaHei', 56), bg='#FFD700').pack(pady=(18, 0))
        tk.Label(win, text='成就解锁!', font=('Microsoft YaHei', 14, 'bold'),
                 fg='#8B4513', bg='#FFD700').pack()
        tk.Label(win, text=name, font=('Microsoft YaHei', 20, 'bold'),
                 fg='white', bg='#8B4513', pady=8, padx=40).pack(fill='x', pady=8)
        tk.Button(win, text='\U0001f389 太棒了!', command=win.destroy,
                  font=('Microsoft YaHei', 12, 'bold'), bg='#FF6B6B', fg='white',
                  width=12).pack(pady=(4, 16))
        win.lift()
        win.update()
        self.bubble('\U0001f389 ' + name + '!')
        self.root.after(30000, lambda: win.destroy() if win.winfo_exists() else None)

    def _check_achievements(self):
        s = self.stats
        already = set(getattr(s, '_popped', []))
        items = [
            ('total_clicks', 1, '初次触碰'),
            ('total_clicks', 10, '频繁戳猫'),
            ('total_clicks', 50, '猫奴入门'),
            ('total_clicks', 200, '戳猫上瘾'),
            ('total_drags', 5, '拖拽初体验'),
            ('total_drags', 50, '拖拽高手'),
            ('total_qa_actions', 5, '提问初试'),
            ('total_qa_actions', 30, '多嘴猫'),
            ('total_walks', 10, '散步者'),
            ('total_walks', 50, '运动达人'),
            ('total_throws', 5, '抛掷新手'),
            ('total_throws', 30, '空中飞猫'),
        ]
        for attr, threshold, name in items:
            key = f'{attr}_{threshold}'
            if key not in already and getattr(s, attr, 0) >= threshold:
                already.add(key)
                self._show_achievement_popup(name)
                break
        s._popped = list(already)
        s.save()

    def _show_achievement_popup(self, name):
        win = tk.Toplevel(self.root)
        win.title('成就解锁')
        win.attributes('-topmost', True)
        win.resizable(False, False)
        win.config(bg='#FFD700')
        self._center_win(win, 380, 240)

        tk.Label(win, text='\U0001f3c6', font=('Microsoft YaHei', 56), bg='#FFD700').pack(pady=(18, 0))
        tk.Label(win, text='成就解锁!', font=('Microsoft YaHei', 14, 'bold'),
                 fg='#8B4513', bg='#FFD700').pack()
        tk.Label(win, text=name, font=('Microsoft YaHei', 20, 'bold'),
                 fg='white', bg='#8B4513', pady=8, padx=40).pack(fill='x', pady=8)
        tk.Button(win, text='\U0001f389 太棒了!', command=win.destroy,
                  font=('Microsoft YaHei', 12, 'bold'), bg='#FF6B6B', fg='white',
                  width=12).pack(pady=(4, 16))
        win.lift()
        win.update()
        self.bubble('\U0001f389 ' + name + '!')
        self.root.after(30000, lambda: win.destroy() if win.winfo_exists() else None)

    def _check_achievements(self):
        s = self.stats
        already = set(getattr(s, '_popped', []))
        items = [
            ('total_clicks', 1, '初次触碰'),
            ('total_clicks', 10, '频繁戳猫'),
            ('total_clicks', 50, '猫奴入门'),
            ('total_clicks', 200, '戳猫上瘾'),
            ('total_drags', 5, '拖拽初体验'),
            ('total_drags', 50, '拖拽高手'),
            ('total_qa_actions', 5, '提问初试'),
            ('total_qa_actions', 30, '多嘴猫'),
            ('total_walks', 10, '散步者'),
            ('total_walks', 50, '运动达人'),
            ('total_throws', 5, '抛掷新手'),
            ('total_throws', 30, '空中飞猫'),
        ]
        for attr, threshold, name in items:
            key = f'{attr}_{threshold}'
            if key not in already and getattr(s, attr, 0) >= threshold:
                already.add(key)
                self.bubble('✨ 解锁: ' + name)
                break
        s._popped = list(already)
        s.save()

    def _click(self):
        self.set_state('happy', True)
        self.stats.total_clicks += 1
        self.stats.xp += 5
        self.stats.add_affection(1)
        self.stats.save()
        self._check_achievements()
        self._check_achievements()
        self._check_achievements()

    def _after_action(self):
        self.idle_since = time.time()

    def _on_right(self, e):
        m = tk.Menu(self.root, tearoff=0, font=('Microsoft YaHei', 9))
        # 表情
        mood = tk.Menu(m, tearoff=0, font=('Microsoft YaHei', 9))
        for st in ('happy','angry','confused','love','shy','sleep','sad','wow'):
            mood.add_command(label=self._mood_label(st), command=lambda s=st: self._apply_mood(s))
        m.add_cascade(label='\U0001f642 表情', menu=mood)
        # 动作
        act = tk.Menu(m, tearoff=0, font=('Microsoft YaHei', 9))
        act.add_command(label='\U0001f463 散步', command=self._walk)
        act.add_command(label='\U0001f5f3 跳一跳', command=self._jump)
        m.add_cascade(label='\U0001f504 动作', menu=act)
        m.add_separator()
        # 主要功能
        m.add_command(label='\U0001f50d 提问', command=self._open_qa_input)
        m.add_command(label='\U0001f4cb 待办事项', command=self._open_todos)
        m.add_command(label='\U0001f4c5 日程管理', command=self._open_scheduler)
        m.add_command(label='\U0001f4ca 工作报告', command=self._open_report)
        m.add_command(label='\U0001f4a7 管路流量', command=self._open_pipe_calc)
        m.add_command(label='\U0001f33f 算下工具', command=self._open_sops)
        m.add_command(label='\U0001f3c6 成就/统计', command=self._open_stats)
        m.add_separator()
        # 系统
        m.add_command(label='\U0001f502 隐藏 (B键)', command=self._toggle_hide)
        m.add_command(label='\U0001f4a4 关掉', command=self._close_app)
        try: m.tk_popup(e.x_root, e.y_root)
        finally: m.grab_release()

    def _mood_label(self, state):
        d = {'happy':'\U0001f642 开心','angry':'\U0001f620 生气','confused':'\U0001f914 疑惑',
             'love':'\u2764\ufe0f 喜欢','shy':'\U0001f633 害臊','sleep':'\U0001f634 睡觉',
             'sad':'\U0001f622 委屈','wow':'\u26a0\ufe0f 惊讶'}
        return d.get(state, state)

    def _apply_mood(self, state):
        """永久设置心情"""
        self.draw.state = state
        self.refresh_draw()
    def _jump(self):
        self.throwing = True
        self.txv = random.randint(-15, 15)
        self.tyv = -random.randint(20, 30)
        self.bubble('\u26a0\ufe0f 哇!')
        self._throw_loop()

    def _toggle_hide(self):
        if self.root.winfo_viewable():
            self.root.withdraw()
        else:
            self.root.deiconify()

    def _open_report(self):
        from modules.todo_dialog import TodoDialog
        td = TodoDialog(self.root, self.todos, deepseek_fn=deepseek_chat)
        td.status_lbl.config(text='正在生成报告...')
        td.win.update()
        td._gen_report()

    def _open_stats(self):
        s = self.stats
        win = tk.Toplevel(self.root)
        win.title('成就/统计')
        win.attributes('-topmost', True); win.resizable(False, False)
        self._center_win(win, 460, 560)
        win.config(bg='#FFF8DC')
        xp = getattr(s, 'xp', 0); aff = max(0, getattr(s, 'affection', 50))
        level = max(1, xp // 50)
        tk.Label(win, text=f'Lv{level}  XP:{xp}/{level*50}',
                 font=('Microsoft YaHei', 14, 'bold'), fg='#8B4513', bg='#FFF8DC', pady=6).pack()
        aff_bar = tk.Canvas(win, width=300, height=16, bg='#EEE', highlightthickness=0)
        aff_bar.pack(pady=2)
        aff_bar.create_rectangle(0, 0, 300 * aff / 100, 16, fill='#FF6B6B', outline='')
        tk.Label(win, text=f'好感度: {aff}/100', font=('Microsoft YaHei', 9, 'bold'), fg='#E74C3C', bg='#FFF8DC').pack(pady=2)
        ach = tk.Frame(win, bg='#FFF8DC'); ach.pack(fill='both', expand=True, padx=8, pady=4)
        items = [
            ('初次触碰', '第一次戳猫', 'total_clicks', 1),
            ('频繁戳猫', '戳猫10次', 'total_clicks', 10),
            ('猫奴入门', '戳猫50次', 'total_clicks', 50),
            ('戳猫上瘾', '戳猫200次', 'total_clicks', 200),
            ('拖拽初体验', '拖拽5次', 'total_drags', 5),
            ('拖拽高手', '拖拽50次', 'total_drags', 50),
            ('提问初试', '提问5次', 'total_qa_actions', 5),
            ('多嘴猫', '提问30次', 'total_qa_actions', 30),
            ('散步者', '走路10次', 'total_walks', 10),
            ('运动达人', '走路50次', 'total_walks', 50),
            ('抛掷新手', '投掷5次', 'total_throws', 5),
            ('空中飞猫', '投掷30次', 'total_throws', 30),
        ]
        for name, desc, attr, threshold in items:
            val = getattr(s, attr, 0)
            mark = '\u2705' if val >= threshold else '\u2b1c'
            color = '#000' if val >= threshold else '#999'
            tk.Label(ach, text=f'{mark} {name}', font=('Microsoft YaHei', 10, 'bold'),
                     fg=color, bg='#FFF8DC').pack(anchor='w')
            tk.Label(ach, text=f'  {desc} ({val}/{threshold})', font=('Microsoft YaHei', 8),
                     fg='#666', bg='#FFF8DC').pack(anchor='w')
        tk.Button(win, text='关闭', command=win.destroy, bg='#DDD').pack(pady=6)


    def _close_app(self):
        self._shutdown()
        self.root.destroy()

    def _shutdown(self):
        if self._remind_check_id:
            self.root.after_cancel(self._remind_check_id)
        if self._bubble_win:
            try: self._bubble_win.destroy()
            except: pass
        try:
            import json, base64
            s = self.stats
            d = {'affection': s.affection, 'total_drags': s.total_drags,
                 'total_walks': s.total_walks, 'total_qa_actions': s.total_qa_actions,
                 'total_sessions': s.total_sessions, 'total_throws': s.total_throws}
            with open(os.path.join(self.data_dir, 'state.json'), 'w', encoding='utf-8') as f:
                json.dump(d, f, ensure_ascii=False)
        except: pass

    def bubble(self, text):
        if self._bubble_win:
            try: self._bubble_win.destroy()
            except: pass
        if not text: return
        # 用 智能桌面化工伴侣猫Canvas 画一个弹出式标签，避开 ad-killer 的 Toplevel 干扰
        win = tk.Toplevel(self.root)
        win.title('智能桌面化工伴侣猫')
        win.overrideredirect(True); win.attributes('-topmost', True)
        win.config(bg='#FFF8DC')
        rootx = self.root.winfo_rootx(); rooty = self.root.winfo_rooty()
        tk.Label(win, text=text, font=('Microsoft YaHei', 8), bg='#FFF8DC', fg='#666',
                 padx=4, pady=2).pack()
        win.update_idletasks()
        win.geometry(f'+{rootx-20}+{rooty-28}')
        win.lift()
        self._bubble_win = win
        self.root.after(2500, lambda: win.destroy() if win.winfo_exists() else None)

    # ====================== QA ======================
    def _open_qa_input(self):
        win = tk.Toplevel(self.root)
        win.title('提问 智能桌面化工伴侣猫(有记忆)')
        win.attributes('-topmost', True); win.resizable(False, False)
        self._center_win(win, 460, 180)
        info = '\U0001f4ad 当前记忆%d轮' % (len(self.chat_history)//2) if self.chat_history else '\U0001f4ad 新对话'
        tk.Label(win, text=info, font=('Microsoft YaHei',8), fg='#888').pack(anchor='w',padx=10)
        tk.Label(win, text='\U0001f4ac 问猫猫:', font=('Microsoft YaHei',10)).pack(padx=10, pady=(2,2))
        entry = tk.Entry(win, width=40, font=('Microsoft YaHei',10))
        entry.pack(padx=10, pady=2); entry.focus_set()
        entry.bind('<Return>', lambda e: self._ask(entry.get(), win))
        bf = tk.Frame(win); bf.pack(pady=(0,8))
        tk.Button(bf, text='\U0001f431 提问', command=lambda: self._ask(entry.get(), win),
                  bg='#8E44AD', fg='white', width=16, font=('Microsoft YaHei',10,'bold')).pack(side=tk.LEFT, padx=2)
        if self.chat_history:
            tk.Button(bf, text='\U0001f5d1 清记忆', command=self._clear_chat,
                      bg='#E74C3C', fg='white', width=8).pack(side=tk.LEFT, padx=2)

    def _clear_chat(self):
        self.chat_history = []; self.bubble('\U0001f4ac 记忆已清空!')

    def _ask(self, query, win):
        query = query.strip()
        if not query: return
        win.destroy(); self.stats.total_qa_actions += 1; self.stats.xp += 10; self.stats.save()
        self.chat_history.append({'role':'user','content':query})
        self.set_state('think', True); self.bubble('\U0001f916 正在思考...'); self.root.update()

        import threading
        def work():
            try:
                rag_context = ''
                if self.rag_ok:
                    import re as _re
                    # 统一交给 rag_search 处理变体（自动生成 M352Y 等）
                    all_res = []
                    # 用原查询搜（拉 30 条，覆盖小排名但含关键数据的 chunks）
                    for r in rag_search(query, limit=30):
                        if r not in all_res: all_res.append(r)
                    # 用大写查询搜（解决 352y 不会触发变体）
                    upper_query = query.upper()
                    if upper_query != query:
                        for r in rag_search(upper_query, limit=30):
                            if r not in all_res: all_res.append(r)
                    # 提取数字+字母术语单独搜（如 352Y → 直接搜含 352Y 的 chunk）
                    for term in _re.findall(r'\b\d+[A-Za-z]\b', query):
                        for r in rag_search(term, limit=20):
                            if r not in all_res: all_res.append(r)
                    # 中文→英文映射（搜中文时也搜英文关键词，覆盖 Perry 等英文手册）
                    for cn_term, en_term in BILINGUAL_MAP.items():
                        if cn_term in query:
                            for r in rag_search(en_term, limit=10):
                                if r not in all_res: all_res.append(r)
                            # 直接搜 Perry 相关目录 (中文搜不到英文手册，用 dir_hint 过滤)
                            for dh in ['01_通用手册/Perrys_Handbook_9th', '01_通用手册/石油化工设计手册']:
                                for r in rag_search(en_term, limit=5, dir_hint=dh):
                                    if r not in all_res: all_res.append(r)
                            break  # 命中一个映射即可

                    # 优先排序: 含"specific area"、"300 m²/m³"等关键参数的 chunk 排前面
                    priority_keys = ['specific surface', 'specific area', '比表面积',
                                     '300 m²/m3', '300 m^2/m^3', '500 m²/m3', '250 m²/m3',
                                     'M352.Y', 'M252.Y', 'M452.Y']
                                        # 检查查询是否含中文
                    query_has_cn = any('\u4e00' <= c <= '\u9fff' for c in query)
                    def _priority(r):
                        fn, p, txt, rk = r
                        fn_lower = str(fn).lower()
                        # 含查询原词的 chunks 优先
                        if query in txt or query.split()[0] in txt:
                            return -2000
                        # 含关键参数的优先
                        for pk in priority_keys:
                            if pk in txt:
                                return -1000
                        # Section 14 (Perry 设备章节，含分布器/填料/塔板) 优先
                        if 'section_14' in fn_lower:
                            return -800
                        # 其他英文权威手册
                        for pf in ['perrys', 'perry', 'fri-', 'henry kister',
                                   'chemical engineers', 'distillation design', 'distillation operation']:
                            if pf in fn_lower:
                                return -500
                        # 中文查询时优先含中文 chunk
                        if query_has_cn and any('\u4e00' <= c <= '\u9fff' for c in txt):
                            return -200
                        return rk
                    all_res.sort(key=_priority)

                    results = all_res[:5] if all_res else []
                    if results:
                        chunks = []
                        # 检测中英对照（让 AI 知道 chunks 里的英文术语对应中文什么）
                        cn_en_hint = ''
                        for cn_term, en_term in BILINGUAL_MAP.items():
                            if cn_term in query:
                                cn_en_hint = f'【关键术语】{cn_term} = {en_term}\n\n'
                                break
                        for fn, p, txt, rk in results[:5]:
                            fname = os.path.basename(str(fn)).replace('.md','')
                            chunks.append('\u3010' + fname + '\u3011' + str(txt))
                        rag_context = ('以下是化工知识库里的硬数据，回答时必须原文引用,不许猜数字\n'
                                      '特别警告: 塔填料型号的数字 (如 352Y) 本身不代表任何物理参数! 比表面积 300 不能写成 352!\n\n'
                                      + cn_en_hint
                                      + '\n\n'.join(chunks) + '\n\n')
                sys_msg = {
                    'role':'system',
                    'content':(rag_context +
                              '你是智能桌面化工伴侣猫，化工助手的桌面宠物。'
                              '【中文查询对应的英文术语】distributor=分布器/分布管, packing=填料, tray=塔板, '
                              'distillation=精馏, absorption=吸收, reactor=反应器, heat exchanger=换热器, '
                              'furfural=糠醛, furfuryl alcohol=糠醇, hydrogenation=加氢, '
                              'pressure drop=压降, orifice=孔板, perrys=Perry手册, kister=亨利克斯特蒸馏手册。'
                              '【最重要】回答必须基于 chunks 内容，但**不要直接抄原文**。'
                              '用你自己的话解释、总结、补充：说明chunks里没说什么、原理是什么、如何应用。'
                              '当用户问中文但 chunks 是英文术语时,翻译成中文回答。'
                              '【限足重要】准确心不能动:如果资料里有 "300 m2/m3"，必须吐口「300」，绝不要凑成 352 那个型号数字。'
                              '其它型号 (350Y 是 350, 352Y 是 300, 452Y 是 350) 别互相套用,别胛造。'
                              '如果资料完全无关或空,才能说没搜到。')
                }
                msgs = [sys_msg] + self.chat_history[-10:]
                reply = deepseek_chat(msgs)
                if reply.startswith('['):
                    self.root.after(0, lambda r=reply, src=results: self._show_answer(query, '\u26a0\ufe0f '+r, src))
                else:
                    self.chat_history.append({'role':'assistant','content':reply})
                    self.root.after(0, lambda r=reply, src=results: self._show_answer(query, r, src))
            except Exception as e:
                self.root.after(0, lambda: self.bubble('\U0001f63f 回答失败'))
            self.root.after(0, self._after_action)
        t = threading.Thread(target=work, daemon=True); t.start()

    def _show_answer(self, query, reply, sources=None):
        lines = []
        for msg in self.chat_history:
            r = msg.get('role',''); t = msg.get('content','')
            if r == 'user': lines.append('\U0001f9d1 你: ' + str(t))
            elif r == 'assistant': lines.append('\U0001f431 猫: ' + str(t))
        if not lines and reply: lines.append('\U0001f431 猫: ' + str(reply))
        if not lines: lines.append('(暂无内容, 错误: ' + str(reply)[:60] + ')')

        # 添加来源引用 (化工知识库检索结果)
        if sources:
            lines.append('')
            lines.append('\U0001f4da 知识库来源 (' + str(len(sources)) + ' 条):')
            for i, (fn, p, txt, rk) in enumerate(sources[:5], 1):
                fn_str = os.path.basename(str(fn))
                p_str = str(p) if p and str(p) != '0' else ''
                loc = f' (行 {p_str})' if p_str.isdigit() else (f' ({p_str})' if p_str else '')
                lines.append(f'  {i}. {fn_str}{loc}')

        display = '\n\n'.join(lines)
        win = tk.Toplevel(self.root); win.title('\U0001f431 智能桌面化工伴侣猫')
        win.attributes('-topmost', True); self._center_win(win, 540, 500)
        win.config(bg='#FAF5FF'); win.update_idletasks()
        hdr = tk.Frame(win, bg='#8E44AD', pady=6); hdr.pack(fill='x')
        tk.Label(hdr, text='\U0001f431 智能桌面化工伴侣猫 - 对话记录 ('+str(len(self.chat_history)//2)+'轮)',
                 font=('Microsoft YaHei',11,'bold'), fg='white', bg='#8E44AD').pack()
        from tkinter import scrolledtext
        tb = scrolledtext.ScrolledText(win, font=('Microsoft YaHei',10),
                                       bg='#FAF5FF', fg='#222', wrap='word',
                                       padx=12, pady=10, height=15)
        tb.pack(fill='both', expand=True, padx=4, pady=(4,0))
        tb.insert('1.0', display); tb.see('end'); tb.config(state='disabled')
        follow_frame = tk.Frame(win, bg='#FAF5FF', padx=8, pady=4); follow_frame.pack(fill='x')
        tk.Label(follow_frame, text='\U0001f504 追问:', font=('Microsoft YaHei',9), fg='#555', bg='#FAF5FF').pack(anchor='w')
        entry = tk.Entry(follow_frame, width=45, font=('Microsoft YaHei',10))
        entry.pack(side='left', fill='x', expand=True, padx=(0,4))
        def do_follow():
            q = entry.get().strip()
            if q: win.destroy(); self._ask(q, tk.Toplevel(self.root))
        entry.bind('<Return>', lambda e: do_follow())
        tk.Button(follow_frame, text='\U0001f431 追问', command=do_follow,
                  bg='#8E44AD', fg='white', font=('Microsoft YaHei',9,'bold'), width=8).pack(side='right')
        tk.Button(follow_frame, text='\u2715', command=win.destroy, width=3).pack(side='right', padx=2)
        win.update(); win.lift(); win.focus_force()

    # ====================== 待办 ======================
    def _open_todos(self):
        from modules.todo_dialog import TodoDialog
        TodoDialog(self.root, self.todos, deepseek_fn=deepseek_chat)

    def _open_scheduler(self):
        from modules.scheduler_dialog import SchedulerDialog
        SchedulerDialog(self.root, self.scheduler, self.stats)

    # ====================== 日程 ======================
    def _on_remind(self, text, category):
        self._notif_queue.append((text, category))

    def _process_notif(self):
        if not self._notif_queue: return
        text, category = self._notif_queue.pop(0)
        self.set_state('wow', True)
        self._show_reminder_dialog(text)

    def _show_reminder_dialog(self, text):
        text = str(text or '')
        win = tk.Toplevel(self.root); win.title('智能桌面化工伴侣猫 提醒')
        win.attributes('-topmost', True); win.minsize(360, 180)
        tk.Message(win, text='智能桌面化工伴侣猫提醒你\n\n' + (text or '(空)'),
                   font=('Microsoft YaHei', 14, 'bold'), fg='#000000', bg='#FFFFE0',
                   width=320, justify='center').pack(expand=True, fill='both', padx=15, pady=15)
        tk.Button(win, text='知道了', command=win.destroy,
                  bg='#4A90D9', fg='white', width=10, font=('Microsoft YaHei', 11)).pack(pady=(0, 12))
        self._center_win(win, 380, 220); win.update(); win.lift()

    def _remind_check(self):
        triggered = self.scheduler.check()
        for text, cat in triggered: self._on_remind(text, cat)
        self._process_notif()
        self._remind_check_id = self.root.after(5000, self._remind_check)

    # ====================== 广告杀手 ======================
    AD_KEYWORDS = ['搜狗','搜狗输入法','广告','元宝','推送','推荐','news',
                   '弹窗','通知','优惠','红包','抽奖','热榜','热点','热门',
                   '查看全文','下载','戳一下','专属推荐','热搜','帮你']

    def _ad_scan_loop(self):
        try:
            WNDENUMPROC = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
            user32 = ctypes.windll.user32
            def enum_proc(hwnd, lParam):
                class_buf = ctypes.create_unicode_buffer(128)
                user32.GetClassNameW(hwnd, class_buf, 128)
                cls = class_buf.value
                if cls in ('Static','Button','Edit','Shell_TrayWnd','Progman','WorkerW',
                           '#32768','#32771','SysListView32','SysTabControl32',
                           'IMEWnd','MSCTFIME UI','Default IME','Toplevel'): return True
                if not user32.IsWindowVisible(hwnd): return True
                length = user32.GetWindowTextLengthW(hwnd)
                if length == 0: return True
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value
                rect = ctypes.wintypes.RECT()
                user32.GetWindowRect(hwnd, ctypes.byref(rect))
                w = rect.right - rect.left; h = rect.bottom - rect.top
                if not (50 < w < 700 and 30 < h < 500): return True
                for kw in self.AD_KEYWORDS:
                    if kw in title:
                        user32.PostMessageW(hwnd, 0x0010, 0, 0)
                        break
                return True
            user32.EnumWindows(WNDENUMPROC(enum_proc), 0)
        except: pass
        self.root.after(1200, self._ad_scan_loop)

    # ====================== 投掷 + 行走 + 空闲 ======================
    def _throw_loop(self):
        if not self.throwing: return
        self.tyv *= 0.995; self.txv *= 0.995; self.tyv += 2
        x = int(self.root.winfo_x() + self.txv)
        y = int(self.root.winfo_y() + self.tyv)
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        bounced = False
        if y > sh - H: y, self.tyv, self.txv = sh - H, -self.tyv * 0.5, self.txv * 0.7; bounced = True
        if y < 0: y, self.tyv = 0, abs(self.tyv) * 0.5; bounced = True
        if x < 0: x, self.txv = 0, abs(self.txv) * 0.5; bounced = True
        if x > sw - W: x, self.txv = sw - W, -abs(self.txv) * 0.5; bounced = True
        if bounced: self.stats.total_throws += 1; self.stats.xp += 8; self.stats.save()
        if abs(self.txv) < 0.5 and abs(self.tyv) < 2 and y >= sh - H:
            self.throwing = False; self.set_state('confused', True)
            self.bubble('晕...'); self._after_action(); return
        self.root.geometry(f'+{x}+{y}')
        self.root.after(30, self._throw_loop)

    def _idle_loop(self):
        now = time.time()
        if False:  # 已禁用闲置自动走路
            if now - self.idle_since > 20 and not self.walking and not self.dragging and not self.throwing:
                self._walk()
        self.root.after(10000, self._idle_loop)

    def _walk(self):
        if self.walking: return
        self.walking = True; self.stats.total_walks += 1; self.stats.xp += 3; self.stats.save()
        sw, sh = self.root.winfo_screenwidth(), self.root.winfo_screenheight()
        self.wt = (random.randint(0, sw - W), random.randint(0, sh - H))
        self.bubble('去溜达~')
        self._walk_step()

    def _walk_step(self):
        if not self.walking: return
        cx = self.root.winfo_x(); cy = self.root.winfo_y()
        tx, ty = self.wt
        dx, dy = tx - cx, ty - cy
        d = max(1, math.sqrt(dx*dx+dy*dy))
        step = 3
        if d < 5: self.walking = False; self._after_action(); return
        nx = int(cx + dx/d * step); ny = int(cy + dy/d * step)
        self.root.geometry(f'+{nx}+{ny}')
        self.root.after(20, self._walk_step)

    def _open_pipe_calc(self):
        from modules.pipe_calc_dialog import open_pipe_calc
        open_pipe_calc(self.root)

    def _open_sops(self):
        from modules.sop_calculator import open_sop_calculator
        open_sop_calculator(self.root)


if __name__ == '__main__':
    app = CatApp()
    app.root.mainloop()
