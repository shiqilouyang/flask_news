# 1.1 导入蓝图模块
from flask import Blueprint

# 1.2 创建蓝图对象
passport_blue = Blueprint('passport', __name__, url_prefix='/passport')

# 1.3 导入子模块
from . import views
