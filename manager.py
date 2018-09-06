from flask_migrate import Migrate, MigrateCommand
from info import create_app, db, models
from config import DevelopmentConfig, ProductionConfig
from  flask_script import Manager
# 通过继承Congig 来实现其他的功能！增加dubug 功能
# 通过create_app, 传递不同的配置信息, 来实现manager以不同模式来启动
from info.models import User

app = create_app(DevelopmentConfig)

# 创建一个管理器，用来管理对象！,可以迁移，也可以终端执行开启命令
# 创建Managers
manager = Manager(app)

# 创建迁移对象
# 将app 与db进行关联！
Migrate(app, db)

# 给Manager绑定迁移命令
# db 是指的是变量名称！ MigrateCommand指的是迁移
manager.add_command('db', MigrateCommand)


# 命令行的方式控制createsuperuser()方法！
@manager.option('-n', '-name', dest='name')
@manager.option('-p', '-password', dest='password')
def createsuperuser(name, password):
    """创建管理员用户"""
    if not all([name, password]):
        print('参数不足')
        return

    user = User()
    user.mobile = name
    user.nick_name = name
    user.password = password
    user.is_admin = True

    try:
        db.session.add(user)
        db.session.commit()
        print("创建成功")
    except Exception as e:
        print(e)
        db.session.rollback()


if __name__ == '__main__':
    manager.run()

'''
    info 存储的是 app 项目启动的配置
    Manager 管理项目启动！用来管理对象！,可以迁移，也可以终端执行开启命令
    ProductionConfig与setting 文件联系！ 
    create_app 与__init__相关联！
    日志是跟踪软件运行时的状态的！
'''

