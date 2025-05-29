### zippy

- 说明
1. 将Python项目及其依赖打包为单个.pyz文件
2. 运行是使用Pythonj解释器直接调用.pyz文件，即: python example.pyz

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
zippy -p example/ -o example.pyz -e main.py

# 运行打包文件
# 设置: export MYAPP_EXTRACT_DIR=./.zippy, 环境变量,默认为: /tmp
# 注意: 设置MYAPP_EXTRACT_DIR时, 不要设置为: ./
python example.pyz
```