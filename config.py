import base64

import os
import redis
import logging


#cp /usr/local/Python34/lib/python3.4/configparser.py /usr/local/Python34/lib/python3.4/ConfigParser.py

class Config(object):

    # 配置SQLAlchemy
    SQLALCHEMY_DATABASE_URI = 'mysql://root:x@127.0.0.1/manager'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # 在请求结束之前, 自动提交数据库修改
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True

    # 配置Redis
    REDIS_HOST = '127.0.0.1'
    REDIS_PORT = 6379

    # import os,base64
    # base64.b64encode(os.urandom(32))

    SECRET_KEY = base64.b64encode(os.urandom(32))

    # 配置flask-session扩展
    SESSION_TYPE = 'redis'  # 设置要同步的位置
    SESSION_REDIS = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT)
    SESSION_USE_SIGNER = True  # 开启签名, 保证数据安全
    PERMANENT_SESSION_LIFETIME = 86400 * 7  # 配置过期时间


class DevelopmentConfig(Config):
    """开发模式下的配置"""
    DEBUG = True
    LOG_LEVEL = logging.DEBUG


class ProductionConfig(Config):
    """生产模式下的配置"""
    DEBUG = False
    LOG_LEVEL = logging.WARNING

