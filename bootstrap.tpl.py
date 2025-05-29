#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
启动脚本模板，运行时会把自身后面的 ZIP 解压到指定目录，
并先把 DEPS_DIR 加入 sys.path，再运行项目入口脚本。
"""

import sys
import os
import io
import zipfile
import runpy
import tempfile

# --- 用户配置区 ---
# 入口脚本，相对于项目根目录，比如 'app/main.py'
ENTRY_SCRIPT = '{ENTRY_SCRIPT}'
# 解压目录：可用环境变量指定，否则默认临时目录
EXTRACT_ROOT = os.environ.get('MYAPP_EXTRACT_DIR') or tempfile.mkdtemp(prefix='myapp_')
# 依赖目录相对于 EXTRACT_ROOT 的子目录
DEPS_SUBDIR = 'deps'
# --- end 配置 ---

_MARKER = b'# === ZIP START ===\n'

# 1. 读取自身并定位 ZIP 数据
with open(__file__, 'rb') as f:
    data = f.read()
pos = data.find(_MARKER)
if pos < 0:
    sys.exit('ERROR: ZIP marker not found.')
zip_data = data[pos + len(_MARKER):]

# 2. 解压全部内容到 EXTRACT_ROOT
os.makedirs(EXTRACT_ROOT, exist_ok=True)
with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
    zf.extractall(EXTRACT_ROOT)

# 3. 把依赖目录加入 sys.path（优先）
deps_path = os.path.join(EXTRACT_ROOT, DEPS_SUBDIR)
if os.path.isdir(deps_path):
    sys.path.insert(0, deps_path)

# 4. 再把项目源码目录加入 sys.path
sys.path.insert(0, EXTRACT_ROOT)

# 5. 运行入口脚本
entry_path = os.path.join(EXTRACT_ROOT, ENTRY_SCRIPT)
if not os.path.isfile(entry_path):
    sys.exit(f'ERROR: entry script not found: {ENTRY_SCRIPT}')
runpy.run_path(entry_path, run_name='__main__')
