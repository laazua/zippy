#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zippy：把项目源码和 pip 安装的依赖打包成 .pyz。
依赖列表从项目根目录下的 requirements.txt 自动读取并在构建时安装到临时目录，
将这些依赖连同源码一起打包。
运行时自动解压到指定目录，并设置 PYTHONPATH 环境变量指向解压后的 deps 目录和项目根目录，
以子进程方式执行入口脚本，在等待期间响应中断信号，执行结束后删除解压目录。
可通过 --entry 指定入口脚本（无需 __main__.py）。
打包后生成的 .pyz 文件为可执行 zipapp。
"""

import os
import sys
import zipfile
import argparse
import subprocess
import tempfile
import shutil

# Bootstrap 模板，写入 __main__.py
BOOTSTRAP_TEMPLATE = """#!/usr/bin/env python3
#自解压启动脚本：
#1. 解压 zip 到指定目录
#2. 设置 PYTHONPATH 环境变量包含 deps 子目录和项目根目录
#3. 以子进程方式运行入口脚本，带原始命令行参数
#4. 等待子进程结束或中断后清理解压目录

import os, sys, zipfile, tempfile, shutil, subprocess, signal

ENTRY = '{ENTRY_SCRIPT}'
# 获取归档路径和基目录
archive = os.path.abspath(sys.argv[0])
base_dir = os.path.dirname(archive)
# 切换工作目录
os.chdir(base_dir)
EXTRACT_DIR = os.environ.get('MYAPP_EXTRACT_DIR') or tempfile.mkdtemp(prefix='zippy_app_')
DEPS_DIR = os.path.join(EXTRACT_DIR, 'deps')

# 解压
archive = os.path.abspath(sys.argv[0])
with zipfile.ZipFile(archive, 'r') as zf:
    zf.extractall(EXTRACT_DIR)

# 设置 PYTHONPATH
orig = os.environ.get('PYTHONPATH', '')
paths = [DEPS_DIR, EXTRACT_DIR]
if orig:
    paths.append(orig)
os.environ['PYTHONPATH'] = os.pathsep.join(paths)

# 构建入口路径
entry_path = os.path.join(EXTRACT_DIR, ENTRY)
if not os.path.isfile(entry_path):
    sys.exit(f"ERROR: 找不到入口脚本: {ENTRY}")

# 清理解压目录
def cleanup():
    try:
        shutil.rmtree(EXTRACT_DIR)
    except Exception:
        pass

# 捕获信号，转发给子进程
child = None

def _signal_handler(sig, frame):
    if child:
        child.send_signal(sig)
signal.signal(signal.SIGINT, _signal_handler)
signal.signal(signal.SIGTERM, _signal_handler)

# 启动子进程并等待
try:
    child = subprocess.Popen([sys.executable, entry_path] + sys.argv[1:], env=os.environ)
    ret = child.wait()
except KeyboardInterrupt:
    # 中断时杀掉子进程
    try:
        child.kill()
    except:
        pass
    ret = 1
finally:
    cleanup()

sys.exit(ret)
"""


def collect_project(zf, project_dir):
    # fns = ('.py', '.html', '.txt', '.css', '.png', '.gif')
    for root, dirs, files in os.walk(project_dir):
        # 忽略 .venv 目录
        dirs[:] = [d for d in dirs if d != '.venv']
        for fn in files:
            # if fn.endswith(fns):
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, project_dir)
            zf.write(full, rel)


def collect_deps(zf, deps_tmp):
    for root, dirs, files in os.walk(deps_tmp):
        for fn in files:
            full = os.path.join(root, fn)
            rel = os.path.relpath(full, deps_tmp)
            zf.write(full, os.path.join('deps', rel))


def build(project_dir, output, entry):
    deps_temp = tempfile.mkdtemp(prefix='deps_')
    try:
        req = os.path.join(project_dir, 'requirements.txt')
        if not os.path.isfile(req):
            print(f"ERROR: 找不到 requirements.txt: {req}")
            sys.exit(1)
        subprocess.check_call([
            sys.executable, '-m', 'pip', 'install',
            '--target', deps_temp, '-r', req
        ])

        tmp = tempfile.NamedTemporaryFile(delete=False)
        tmp.close()
        with zipfile.ZipFile(tmp.name, 'w', zipfile.ZIP_DEFLATED) as zf:
            zf.writestr('__main__.py', BOOTSTRAP_TEMPLATE.replace('{ENTRY_SCRIPT}', entry))
            collect_project(zf, project_dir)
            collect_deps(zf, deps_temp)

        if os.path.exists(output):
            os.remove(output)
        with open(output, 'wb') as outf, open(tmp.name, 'rb') as inf:
            outf.write(b'#!/usr/bin/env python3\n')
            shutil.copyfileobj(inf, outf)
        os.chmod(output, 0o755)
        print(f"打包完成: {output}")
    finally:
        shutil.rmtree(deps_temp)
        os.remove(tmp.name)


def main():
    p = argparse.ArgumentParser(description='打包 Python 项目为 .pyz')
    p.add_argument('-p', '--project', required=True, help='项目根目录')
    p.add_argument('-o', '--output', required=True, help='.pyz 输出路径')
    p.add_argument('-e', '--entry', required=True, help='入口脚本，相对项目根')
    args = p.parse_args()
    proj = os.path.abspath(args.project)
    ent = os.path.join(proj, args.entry)
    if not os.path.isfile(ent):
        print(f"ERROR: 找不到入口脚本: {ent}")
        sys.exit(1)
    build(proj, os.path.abspath(args.output), args.entry)


if __name__ == '__main__':
    main()
