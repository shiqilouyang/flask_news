# 1.1 导入蓝图模块
from flask import Blueprint

# 1.2 创建蓝图对象
profile_blue = Blueprint('profile', __name__, url_prefix='/user')

# 1.3 导入子模块
from . import views
