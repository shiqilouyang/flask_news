# 开发的主要目录, 代码基本都在这个目录中
import redis
import logging

from flask import Flask, render_template, g
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_wtf.csrf import CSRFProtect, generate_csrf
from logging.handlers import RotatingFileHandler

#  创建数据库


db = SQLAlchemy()

# 定义空redis存储对象,供视图调用！
redis_store = None  # type: redis.StrictRedis


def setup_log(config_name):
    # 设置日志的记录等级
    logging.basicConfig(level=config_name.LOG_LEVEL)  # 调试debug级
    # 创建日志记录器，指明日志保存的路径、每个日志文件的最大大小、保存的日志文件个数上限
    file_log_handler = RotatingFileHandler("logs/log", maxBytes=1024 * 1024 * 100, backupCount=10)
    # 创建日志记录的格式 日志等级 输入日志信息的文件名 行数 日志信息
    formatter = logging.Formatter('%(levelname)s %(filename)s:%(lineno)d %(message)s')
    # 为刚创建的日志记录器设置日志记录格式
    file_log_handler.setFormatter(formatter)
    # 为全局的日志工具对象（flask app使用的）添加日志记录器
    logging.getLogger().addHandler(file_log_handler)


# 提供一个函数, 工厂方法, 方便的根据不同的参数, 实现不同的配置加载
def create_app(config_name):
    '''     通过manager 传参，传入的是对象！，对象在setting 之中，对象属性来进行添加属性！
            两次连接redis 一次连接是为了供视图使用，一次是为了存储session的值
     '''
    # 配置项目日志
    setup_log(config_name)

    app = Flask(__name__)

    app.config.from_object(config_name)

    # 几乎所有的扩展都支持这种创建方式
    db.init_app(app)

    # 创建redis对象
    global redis_store
    # 连接redis,返回对象供视图使用！ decode_responses 表示将字节码转换成字符串
    redis_store = redis.StrictRedis(host=config_name.REDIS_HOST, port=config_name.REDIS_PORT, decode_responses=True)

    # 开启CSRF保护 --> 会启用csrf_token对比机制
    # 1. wtf中有函数可以直接生成
    # 2. 在请求钩子中进行设置
    # 3. ajax可以增加一个字段: headers:("X-CSRFToken")
    # 4. 到时候会自动从cookie中获取csrftoken, 从ajax的参数中获取csrftoken, 然后进行对比

    CSRFProtect(app)
    from info.utils.common import user_login_data
    # 所有的请求进行检测，是否有404错误！
    @app.errorhandler(404)
    @user_login_data
    def page_not_found(_):
        user = g.user
        data = {
            "user_info": user.to_dict() if user else None
        }
        return render_template('news/404.html', data=data)

    # 请求钩子，每次请求都会设置 csrf_token值
    # 在每次请求之后, 生成csrf_token, 设置到cookie中
    @app.after_request
    def after_request(response):
        # token生成后,会缓存起来, 多次生成仍是同一个
        csrf_token = generate_csrf()
        # WTF扩展会自动将corf_token存入session, 然后通过flask-session扩展同步到服务器的redis中
        response.set_cookie('csrf_token', csrf_token)
        return response

    # 增加自定义过滤器
    from info.utils.common import do_index_class
    app.add_template_filter(do_index_class, 'index_class')

    # 设置Flask-Session扩展.
    # 将存在浏览器的cookie中的session数据, 同步到服务器的指定地址中(redis)
    Session(app)

    # 蓝图在用到的时候再导包, 可以当做固定规则
    from info.modules.index import index_blue
    # 注册蓝图对象
    app.register_blueprint(index_blue)

    from info.modules.passport import passport_blue
    app.register_blueprint(passport_blue)

    from info.modules.profile import profile_blue
    app.register_blueprint(profile_blue)

    from info.modules.news import news_blue
    app.register_blueprint(news_blue)
    # 将url_prefix='/admin'设置到这里是说明这个是管理员用户！(可选！)
    from info.modules.admin import admin_blue
    app.register_blueprint(admin_blue, url_prefix='/admin')

    return app
