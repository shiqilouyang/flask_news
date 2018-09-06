# 2.1 导入蓝图对象
import random
import re
from datetime import datetime

from flask import request, make_response, current_app, jsonify, session

from info import redis_store, constants, db
from info.libs.yuntongxun.sms import CCP
from info.models import User
from info.utils.response_code import RET
from . import passport_blue
from info.utils.captcha.captcha import captcha

'''
    用户退出登录,删除 session信息，包含管理员的标志!
    前端发送post 请求，并且返回数据之后就会刷新页面操作！
    
'''


@passport_blue.route("/logout", methods=['POST'])
def logout():
    """
    清除session中的对应登录之后保存的信息
    """
    session.pop('user_id', None)
    session.pop('nick_name', None)
    session.pop('mobile', None)
    session.pop('is_admin', None)
    # 返回结果
    return jsonify(errno=RET.OK, errmsg="OK")


'''手机号，用户登录验证！
    登录请求前端发送表单post 请求，后端进行一系列的验证！
    数据库查询用户是否存在！
    判断用户的完整性！
    每次登录之后保存用户的session信息，用来判断用户的状态信息！
'''


@passport_blue.route('/login', methods=['POST'])
def login():
    '''
    1. 获取参数（2个）
    2. 校验参数（完整性， 手机号）
    3. 判断数据库是否有该用户的手机号
    4. 判断密码正确性
    5. 设置登录
    6. 返回登录成功
    '''
    # 1. 获取参数（2个）
    json_dict = request.json
    mobile = json_dict.get('mobile')
    password = json_dict.get('password')

    # 2. 校验参数（完整性， 手机号）
    if not all([mobile, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    if not re.match('1[3456789][0-9]{9}', mobile):
        # 如果不匹配
        return jsonify(errno=RET.DATAERR, errmsg='手机号格式不正确')

    # 3. 判断数据库是否有该用户的手机号
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询mysql的用户信息失败')

    # 4. 判断用户名或密码错误 --> 为了安全性, 不需要分开判断
    if not user or not user.check_passowrd(password):
        # 用户不存在 或者 密码错误
        return jsonify(errno=RET.DATAERR, errmsg='用户名或密码错误')

    # 设置最后登录的时间为当前时间
    user.last_login = datetime.now()
    # try:
    #     db.session.commit()
    # except Exception as e:
    #     current_app.logger.error(e)
    #     db.session.rollback()

    # 5. 设置登录
    session['user_id'] = user.id
    session['nickname'] = user.nick_name
    session['mobile'] = user.mobile

    # 6. 返回数据
    return jsonify(errno=RET.OK, errmsg='登录成功')


'''

    注册按钮的实现！
    判断注册数据是否符合标准
    判断用户的完整
    判断存储到redis之中的手机验证码是否与输出的相同！
    

'''''


# 注册用户
# 请求方式:POST
# URL: /register
# 参数: mobile, sms_code, password
@passport_blue.route('/register', methods=['POST'])
def register():
    '''
    1. 获取参数（3个）
    2. 校验参数（完整性， 手机号）
    3. 从redis中获取短信验证码
    4. 对比验证码， 对比失败返回信息
    5. 对比成功， 删除短信验证码
    6. 成功注册用户（1. 手机号是否注册过 2. 创建User对象 3. 添加到mysql数据库）
    7. 设置用户登录 —> session
    8. 返回数据
    '''
    # 一. 获取数据
    # 1. 获取参数（3个)
    json_dict = request.json
    mobile = json_dict.get('mobile')
    sms_code = json_dict.get('sms_code')
    password = json_dict.get('password')

    # 二. 校验参数
    # 2. 校验参数（完整性， 手机号）
    if not all([mobile, sms_code, password]):
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    if not re.match('1[3456789][0-9]{9}', mobile):
        # 如果不匹配
        return jsonify(errno=RET.DATAERR, errmsg='手机号格式不正确')

    # 三. 逻辑处理
    # 3. 从redis中获取短信验证码
    try:
        real_sms_code = redis_store.get('SMS_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据库失败')

    if not real_sms_code:
        return jsonify(errno=RET.NODATA, errmsg='短信验证码过期或手机号填写错误')

    # 4. 对比验证码， 对比失败返回信息
    if real_sms_code != sms_code:
        return jsonify(errno=RET.DATAERR, errmsg='短信验证码填写错误')

    # 5. 对比成功， 删除短信验证码
    try:
        redis_store.delete('SMS_' + mobile)
    except Exception as e:
        current_app.logger.error(e)
        # 从用户体验角度来说, 如果出错了, 可以不用返回JSON信息
        # return jsonify(errno=RET.DBERR, errmsg='查询数据库失败')

    # 6. 对比成功, 注册用户（1. 手机号是否注册过 2. 创建User对象 3. 添加到mysql数据库）
    # 6.1 手机号是否注册过
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询mysql的用户信息失败')

    if user:
        # 说明用户已注册
        return jsonify(errno=RET.DATAEXIST, errmsg='手机号已注册')

    # 6.2 创建User对象
    user = User()
    user.nick_name = mobile
    user.mobile = mobile
    # 实际开发中, 如果需要对模型数据进行处理, 不会放在视图函数中进行, 而是放在模型中进行.
    # user.password_hash = password
    # 我们希望有个属性可以直接进行密码的加密处理, 并赋值给password_hash属性.
    user.password = password

    # 6.3 添加到mysql数据库
    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        # 数据的修改操作, 失败了需要回滚
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='添加mysql的用户信息失败')

    # 7. 设置用户登录 —> session
    session['user_id'] = user.id
    session['nickname'] = user.nick_name
    session['mobile'] = user.mobile

    # 四. 返回数据
    return jsonify(errno=RET.OK, errmsg='注册成功')


'''点击获取验证码！
    首先验证手机号，取出数据库的验证码,判断是否正确！
'''


# 获取短信验证码
# 请求方式:POST
# URL: /sms_code?mobile=13XXXXXXXXX&image_code=abcd&image_code_id=XXXXXXXX
# 参数: mobile, image_code, image_code_id
@passport_blue.route('/sms_code', methods=['POST'])
def get_sms_code():
    # 一. 获取数据
    # 1. 获取参数(手机号,图像验证码内容,图像验证码ID
    # 局部数据更新需要使用JSON来传递数据
    # request.data返回的是字符串数据
    # json.loads(request.data)
    json_data = request.json
    mobile = json_data.get('mobile')
    # 图像验证码
    image_code = json_data.get('image_code')
    # 图像验证码标示！是唯一标示
    image_code_id = json_data.get('image_code_id')

    # 二. 校验数据
    # 2. 检验数据(完整性, 正则验证手机号)
    if not all([mobile, image_code, image_code_id]):
        # 如果参数不全, 会进入该分支
        return jsonify(errno=RET.PARAMERR, errmsg='参数不全')

    if not re.match('1[3456789][0-9]{9}', mobile):
        # 如果不匹配
        return jsonify(errno=RET.DATAERR, errmsg='手机号格式不正确')

    # 三. 逻辑处理
    # 3. 从redis获取图像验证码
    try:
        real_image_code = redis_store.get('ImageCodeID_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='redis查询失败')

    # 查询mysql&redis, 都需要做判空处理
    if not real_image_code:
        # 验证码已过期
        return jsonify(errno=RET.NODATA, errmsg="验证码已过期")

    # 4. 将2个数据进行对比, 对比失败，返回JSON数据
    # 4.1  为了完善逻辑-->图像验证码从redis获取之后就删除
    try:
        redis_store.delete('ImageCodeID_' + image_code_id)
    except Exception as e:
        current_app.logger.error(e)
        # 可删可不删
        return jsonify(errno=RET.DBERR, errmsg='redis删除失败')

    # 4.2 对比redis和用户传入的数据
    if real_image_code.lower() != image_code.lower():
        # 对比失败，返回JSON数据
        return jsonify(errno=RET.DATAERR, errmsg="验证码填写错误")

    # 4.3 图像验证码对比成功, 再手机号是否注册过
    try:
        user = User.query.filter_by(mobile=mobile).first()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询mysql的用户信息失败')

    if user:
        # 说明用户已注册
        return jsonify(errno=RET.DATAEXIST, errmsg='手机号已注册')

    # 5. 对比成功，生成短信验证码
    # '%06d': 数字是6位的, 不足以0补齐
    sms_code_str = '%06d' % random.randint(0, 999999)

    # 6. 保存到redis中
    try:
        redis_store.set("SMS_" + mobile, sms_code_str, constants.SMS_CODE_REDIS_EXPIRES)
    except Exception as e:
        current_app.logger.error(e)
        # 保存短信验证码失败
        return jsonify(errno=RET.DBERR, errmsg="保存短信验证码失败")

    # 7. 调用云通讯发短信
    # result = CCP().send_template_sms(mobile, [sms_code_str, 5], 1)
    # if result != 0:
    #     # 发送失败
    #     return jsonify(errno=RET.THIRDERR, errmsg="发送短信验证码失败")

    # 四. 返回数据
    # 发送成功，返回JSON数据
    # '{'errno':'0', 'errmsg':'发送短信验证码成功'}'
    return jsonify(errno=RET.OK, errmsg="发送短信验证码成功")


'''图像验证码的处理！在此处将图片验证码存储到redis！'''


# 获取图像验证码
# 请求方式: GET
# URL: /image_code
# 参数: image_code_id
@passport_blue.route('/image_code')
def get_image_code():
    # 1. 获取参数
    image_code_id = request.args.get('image_code_id')

    # 2. 生成验证码、图像   name 是指的唯一值,hash 值
    name, text, image_data = captcha.generate_captcha()

    # 3. 保存redis try
    try:
        # 可以给redis增加类型注释来查看
        redis_store.set('ImageCodeID_' + image_code_id, text, constants.IMAGE_CODE_REDIS_EXPIRES)
    except Exception as e:
        # 保存日志
        current_app.logger.error(e)
        # 返回错误信息-->JSON格式
        # 如果要全局更新网页, 可以渲染模板.
        # 如果只是局部更新数据, 前后端只需要使用JSON传输即可
        # "{'errno': 4001, 'errmsg': '保存redis出错'}"
        return jsonify(errno=RET.DBERR, errmsg='保存redis出错')

    # 4. 返回图像
    response = make_response(image_data)
    response.headers['Content-Type'] = 'image/jpg'
    return response
