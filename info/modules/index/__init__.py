# 1.1 导入蓝图模块
from flask import Blueprint

# 1.2 创建蓝图对象
index_blue = Blueprint('index', __name__)

# 1.3 导入子模块
from . import views
