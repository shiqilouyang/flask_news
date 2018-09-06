# 自定义的公用工具类


# 自定义模板过滤器
import functools
from flask import session, current_app, g, jsonify

from info.models import User
from info.utils.response_code import RET


def do_index_class(index):
    if index == 1:
        return 'first'
    elif index == 2:
        return 'second'
    elif index == 3:
        return 'third'
    return ''


def user_login_data(f):
    # 经过装饰器包装后, 此时函数的名字(__name__)就会被更改为内层函数名(wrapper)
    # @functools.wraps(f): 能够让函数的__name__保持原始名字
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        # 1. 从session中获取user_id
        # 每次的请求都包含session信息！
        user_id = session.get('user_id')

        user = None
        # 2. 如果有user_id, 查询数据库
        if user_id:
            try:
                user = User.query.get(user_id)
            except Exception as e:
                current_app.logger.error(e)
                return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录！")

        # 3. 使用g变量,可以方便的咋一个请求中的多个函数中进行传值
        g.user = user
        return f(*args, **kwargs)

    return wrapper
