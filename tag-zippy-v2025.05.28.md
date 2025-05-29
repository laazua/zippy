### zippy

- 说明
1. 打包Python项目及其依赖为单个 .pyz 结尾的压缩文件
2. 可以通过Python解释器直接调用该压缩文件运行, 即: python example.pyz
3. 注意打包使用的的Python解释器和运行的Python解释器版本要一致

- 示例
```
# 项目结构
example/
├── app
│   ├── __init__.py
│   └── user.py
├── main.py
└── requirements.txt

# 打包
zippy example/ -o example.pyz -m main
```

- 注意
1. 在安装时指定的Python版本：python3.11 -m pip install zippy-2025.5.28.tar.gz  
   这里的python3.11要与后面运行打包文件example.pyz指定的Python解释器一致: python3.11 example.pyz  
2. 将zippy-2025.5.28.tar.gz安装到系统环境中: python3.11 -m pip install zippy-2025.5.28.tar.gz --break-system-packages
