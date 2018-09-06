# 1.1 导入蓝图模块
from flask import Blueprint, session, request, url_for, redirect

# 1.2 创建蓝图对象
admin_blue = Blueprint('admin', __name__)

# 1.3 导入子模块
from . import views


# 对是否是管理员用户的判断, 只需要在admin模块实现
# 所以请求钩子函数, 只需要在模块内部配置接口

@admin_blue.before_request
def before_request():
    # 判断如果不是登录页面的请求
    if not request.url.endswith(url_for("admin.login")):
        user_id = session.get("user_id")
        is_admin = session.get("is_admin", False)
        if not user_id or not is_admin:
            # 判断当前是否有用户登录，或者是否是管理员，如果不是，直接重定向到项目主页
            return redirect('/')


'''
    在管理员，在定义蓝图地方设置　请求钩子，用来为当前用户的请求设置访问限制！
    
'''
