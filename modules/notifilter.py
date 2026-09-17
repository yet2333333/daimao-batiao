# -*- coding: utf-8 -*-
"""低干扰通知拦截 - 检测前台窗口，避免打扰"""
import ctypes
import ctypes.wintypes

# Windows API
_GetForegroundWindow = ctypes.windll.user32.GetForegroundWindow
_GetWindowTextLengthW = ctypes.windll.user32.GetWindowTextLengthW
_GetWindowTextW = ctypes.windll.user32.GetWindowTextW

# 低干扰关键词 —— 这些窗口全屏时静默通知
SILENT_KEYWORDS = [
    'PowerPoint', '幻灯片', '放映', '全屏',
    'Zoom', '会议', 'Meeting', 'Teams',
    '腾讯会议', '钉钉', '飞书', '企业微信',
    '演示', 'presentation',
    '全屏', 'fullscreen',
    '游戏', 'Game',
    'VMware', 'VirtualBox', '远程桌面',
]

# 静默时段（不弹通知）
SILENT_HOURS = (22, 8)  # 22:00 - 08:00


def get_foreground_window_title():
    """获取当前前台窗口标题"""
    hwnd = _GetForegroundWindow()
    length = _GetWindowTextLengthW(hwnd)
    if length == 0:
        return ''
    buf = ctypes.create_unicode_buffer(length + 1)
    _GetWindowTextW(hwnd, buf, length + 1)
    return buf.value


def should_silence():
    """是否应该静默（不弹通知）"""
    # 1. 静默时段
    h = __import__('time').localtime().tm_hour
    if SILENT_HOURS[0] <= h or h < SILENT_HOURS[1]:
        return True, '静默时段'

    # 2. 前台窗口含关键词
    try:
        title = get_foreground_window_title()
        for kw in SILENT_KEYWORDS:
            if kw in title:
                return True, f'窗口"{title[:20]}..."'
    except Exception:
        pass

    return False, ''


def get_notification_level(msg=''):
    """确定通知强度: 'popup' / 'bubble' / 'mute'"""
    silent, reason = should_silence()
    if silent:
        return 'mute', reason
    # 短消息用气泡，长消息用弹窗
    if len(msg) < 30:
        return 'bubble', ''
    return 'popup', ''
