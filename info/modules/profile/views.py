from info import constants, db
from info.models import User, News, Category, Comment
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import profile_blue
from flask import render_template, current_app, session, jsonify, request, g, abort, redirect, url_for

'''用户的签名，签名，性别，昵称设置！'''


@profile_blue.route('/base_info', methods=['GET', 'POST'])
@user_login_data
def base_info():
    # 只要能进入该路由,一定是用户登录了
    # 使用get 请求来返回用户信息，首先登录的同时显示信息！
    if request.method == 'GET':
        data = {
            'user': g.user.to_dict()
        }
        return render_template('news/user_base_info.html', data=data)

    # POST请求
    # 1. 获取参数
    nick_name = request.json.get('nick_name')
    signature = request.json.get('signature')
    gender = request.json.get('gender')

    # 2. 校验参数
    if not all([nick_name, signature, gender]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if gender not in ['MAN', 'WOMEN']:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 3. 设置用户模型的数据
    user = g.user
    user.gender = gender
    user.signature = signature
    user.nick_name = nick_name

    try:
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    # 需要更新session信息
    session['nick_name'] = nick_name

    return jsonify(errno=RET.OK, errmsg="OK")


'''用户的登录显示,外边页面！'''


@profile_blue.route('/info')
@user_login_data
def user_info():
    # 只需要在这里判断一次用户登录即可
    user = g.user
    if not user:
        return redirect('/')

    data = {
        'user': g.user.to_dict()
    }
    return render_template('news/user.html', data=data)


'''上传图片信息'''


@profile_blue.route('/pic_info', methods=['GET', 'POST'])
@user_login_data
def pic_info():
    '''get 请求也是为了首次加载也能显示用户的信息！'''
    user = g.user
    if request.method == 'GET':
        data = {
            'user': user.to_dict()
        }
        return render_template('news/user_pic_info.html', data=data)
    # 从前端读取上传信息！
    try:
        avatar = request.files.get('avatar').read()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='图片读取失败！')
    # 上传到服务器
    try:
        file_name = storage(avatar)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='图片上称七牛云失败！')
    try:
        # 数据库存取的是文件名称,不需要完整的路径！文件名是独一无二的
        user.avatar_url = file_name
        db.session.add(user)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg='数据库存取失败！')
    # 将完整的url传递给前端！
    print(constants.QINIU_DOMIN_PREFIX + file_name)
    return jsonify(errno=RET.OK, errmsg='成功！', data={'avatar_url': constants.QINIU_DOMIN_PREFIX + file_name})


'''密码修改'''


@profile_blue.route('/pass_info', methods=['GET', 'POST'])
@user_login_data
def pass_info():
    user = g.user
    if request.method == 'GET':
        data = {
            'user': user.to_dict()
        }
        return render_template('news/user_pass_info.html', data=data)

    pass_info = request.json
    old_password = pass_info.get('old_password')
    new_password = pass_info.gey('new_password')

    if user.check_passowrd(old_password):
        try:
            user.password = new_password
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR, errmsg='数据库查询失败！')

    db.session.add(user)
    db.commit()
    return jsonify(errno=RET.OK, errmsg='成功！')


'''个人收藏'''


@profile_blue.route('/collection')
@user_login_data
def user_collection():
    # 获取页数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user
    collections = []
    current_page = 1
    total_page = 1
    try:
        # 进行分页数据查询 当前页数，一页多少数据，是否返回错误信息
        paginate = user.collection_news.paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取分页数据
        collections = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    # 收藏列表,将数据转换成字典形式，方便取出数据！
    collection_dict_li = []
    for news in collections:
        collection_dict_li.append(news.to_basic_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "collections": collection_dict_li
    }
    return render_template('news/user_collection.html', data=data)


'''新闻发布显示！'''


@profile_blue.route('/news_release', methods=['GET', 'POST'])
@user_login_data
def news_release():
    user = g.user
    if request.method == 'GET':
        # 查询所有的分类数据并且显示出来！
        try:
            category = Category.query.all()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DATAERR, errmsg='数据库查询失败！')
        category_data_list = []
        for item in category:
            category_data_list.append(item.to_dict())
            # 删除'最新' 这个数据
        category_data_list.pop(0)
        data = {
            'categories': category_data_list
        }

        return render_template('news/user_news_release.html', data=data)

    title = request.form.get("title")
    source = "个人发布"
    # 摘要
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 1.1 判断数据是否有值
    if not all([title, source, digest, content, index_image, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    # try:
    #     cate_data = Category.query(Category.id==category_id).first()
    # except Exception as e:
    #     current_app.logger.error(e)
    #     return jsonify(errno=RET.DATAERR, errmsg='数据库查询失败！')
    # 图片上传到七牛
    try:
        file_name = storage(index_image.read())
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.THIRDERR, errmsg='第三方错误！')
    # 保存到数据库之中！
    news = News()
    news.title = title
    news.digest = digest
    news.source = source
    news.content = content
    news.index_image_url = constants.QINIU_DOMIN_PREFIX + file_name
    news.category_id = category_id
    news.user_id = g.user.id
    # 1代表待审核状态
    news.status = 1
    # 4. 保存到数据库
    try:
        db.session.add(news)
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="发布成功，等待审核")


'''新闻列表显示'''


@profile_blue.route('/news_list')
@user_login_data
def news_list():
    # 获取页数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user
    news_li = []
    current_page = 1
    total_page = 1
    try:
        paginate = News.query.filter(News.user_id == user.id).paginate(p, constants.USER_COLLECTION_MAX_NEWS, False)
        # 获取当前页数据
        news_li = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_li = []

    for news_item in news_li:
        news_dict_li.append(news_item.to_review_dict())
    data = {
        "news_list": news_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }
    return render_template('news/user_news_list.html', data=data)


'''我的关注信息！'''


@profile_blue.route('/user_follow')
@user_login_data
def user_follow():
    # 获取页数
    p = request.args.get("p", 1)
    try:
        p = int(p)
    except Exception as e:
        current_app.logger.error(e)
        p = 1

    user = g.user

    follows = []
    current_page = 1
    total_page = 1
    try:
        paginate = user.followed.paginate(p, constants.USER_FOLLOWED_MAX_COUNT, False)
        # 获取当前页数据
        follows = paginate.items
        # 获取当前页
        current_page = paginate.page
        # 获取总页数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    user_dict_li = []

    for follow_user in follows:
        user_dict_li.append(follow_user.to_dict())
    data = {
        "users": user_dict_li,
        "total_page": total_page,
        "current_page": current_page
    }
    return render_template('news/user_follow.html', data=data)


'''其他信息！'''


@profile_blue.route('/other_info')
@user_login_data
def other_info():
    """查看其他用户信息"""
    user = g.user

    # 获取其他用户id
    user_id = request.args.get("user_id")
    if not user_id:
        abort(404)
    # 查询用户模型
    other = None
    try:
        other = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
    if not other:
        abort(404)

    # 判断当前登录用户是否关注过该用户
    is_followed = False
    if g.user:
        if other.followers.filter(User.id == user.id).count() > 0:
            is_followed = True

    # 组织数据，并返回
    data = {
        "is_followed": is_followed,
        "user": g.user.to_dict() if g.user else None,
        "other_info": other.to_dict()
    }

    return render_template('news/other.html', data=data)
