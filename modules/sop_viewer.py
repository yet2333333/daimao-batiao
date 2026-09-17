# -*- coding: utf-8 -*-
"""SOP 浏览器 - 系统默认浏览器打开 (最稳方案)"""
import os
import webbrowser


class SOPViewer:
    """用默认浏览器打开 SOP 计算器 (Edge/Chrome 全部按钮可用)"""

    def __init__(self, parent, html_path):
        try:
            url = 'file:///' + html_path.replace('\\', '/')
            webbrowser.open(url, new=2)
        except Exception as e:
            try:
                parent.bubble(f'打开失败: {str(e)[:35]}')
            except:
                pass
