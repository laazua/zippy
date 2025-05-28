#!/usr/bin/env python3
"""
zippy - 支持自动打包并从内存加载 .so/.pyd 
通过 -m 参数指定入口模块，运行时使用自定义导入钩子(memfd+dlopen 或 磁盘回退)在内存加载动态库。

用法:
  zippy <src_dir> -o <output.pyz> -m <entry_module>
示例:
  zippy myproj -o myapp.pyz -m app_pkg.main
  chmod +x myapp.pyz
  ./myapp.pyz arg1 arg2
"""
import os
import sys
import zipfile
import tempfile
import shutil
import stat
import argparse
import subprocess


# 引导脚本模板：注册内存加载 .so/.pyd 的导入钩子，并在失败时回退到磁盘
STUB = r'''#!/usr/bin/env python3
import sys, os, zipfile, tempfile
import importlib.abc, importlib.util, importlib.machinery

# 打开 .pyz 包
archive = sys.argv[0]
zf = zipfile.ZipFile(archive)

class ZipExtLoader(importlib.abc.Loader):
    def __init__(self, fullname, zpath):
        self.fullname = fullname
        self.zpath = zpath
    def create_module(self, spec):
        return None
    def exec_module(self, module):
        data = zf.read(self.zpath)
        try:
            # 在内存创建匿名文件
            fd = os.memfd_create(self.fullname, flags=os.MFD_CLOEXEC)
            os.write(fd, data)
            os.lseek(fd, 0, os.SEEK_SET)
            path = f"/proc/self/fd/{{fd}}"
        except (AttributeError, OSError):
            # 回退：写磁盘临时文件
            tempdir = tempfile.gettempdir()
            fn = os.path.join(tempdir, os.path.basename(self.zpath))
            with open(fn, 'wb') as f:
                f.write(data)
            path = fn
        # 加载扩展模块
        loader = importlib.machinery.ExtensionFileLoader(self.fullname, path)
        spec = importlib.util.spec_from_loader(self.fullname, loader)
        mod = importlib.util.module_from_spec(spec)
        loader.exec_module(mod)
        sys.modules[self.fullname] = mod

class MetaImporter(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path, target=None):
        name = fullname.replace('.', '/')
        for suffix in importlib.machinery.EXTENSION_SUFFIXES:
            zpath = name + suffix
            if zpath in zf.namelist():
                loader = ZipExtLoader(fullname, zpath)
                return importlib.util.spec_from_loader(fullname, loader)
        return None

# 注册导入钩子和 sys.path
sys.meta_path.insert(0, MetaImporter())
sys.path.insert(0, archive)

# 执行入口模块
import runpy
runpy.run_module('{entry_module}', run_name='__main__')
'''

def install_deps(req_file, target_dir):
    subprocess.check_call([
        sys.executable, '-m', 'pip', 'install',
        '--upgrade', '-r', req_file,
        '-t', target_dir
    ])

def build(src, output, module):
    # 准备临时目录
    work = tempfile.mkdtemp(prefix='zippy_build_')
    # 复制源码及依赖
    shutil.copytree(src, work, dirs_exist_ok=True)
    req = os.path.join(src, 'requirements.txt')
    if os.path.isfile(req):
        print(f"Installing dependencies from {req}...")
        install_deps(req, work)
    # 写入 __main__.py
    with open(os.path.join(work, '__main__.py'), 'w') as f:
        f.write(STUB.format(entry_module=module))
    # 打包为 .pyz
    with open(output, 'wb') as f:
        f.write(b'#!/usr/bin/env python3\n')
    with zipfile.ZipFile(output, 'a', zipfile.ZIP_DEFLATED) as zf_out:
        for root, _, files in os.walk(work):
            for fn in files:
                path = os.path.join(root, fn)
                arc = os.path.relpath(path, work)
                zf_out.write(path, arc)
    # 设置可执行权限
    os.chmod(output, os.stat(output).st_mode | stat.S_IEXEC)
    # 清理临时目录
    shutil.rmtree(work)
    print(f"✅ 构建完成 {output}, 入口：{module}")

def main():
    parser = argparse.ArgumentParser(prog='zippy')
    parser.add_argument('src', help='源码目录')
    parser.add_argument('-o', '--output', required=True, help='输出 .pyz 文件')
    parser.add_argument('-m', '--module', required=True, help='入口模块，如 app_pkg.main')
    args = parser.parse_args()
    if args.src == "" or args.output == "" or args.module == "":
        parser.print_usage()
    else:
        build(args.src, args.output, args.module)

if __name__=='__main__':
    main()