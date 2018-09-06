# 1.1 导入蓝图模块
from flask import Blueprint

# 1.2 创建蓝图对象
news_blue = Blueprint('news', __name__, url_prefix='/news')

# 1.3 导入子模块
from . import views
