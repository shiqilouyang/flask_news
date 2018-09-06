from info import constants, db
from info.models import User, News, Category, Comment
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import news_blue
from flask import render_template, current_app, session, jsonify, request, g, abort

'''添加评论！'''


@news_blue.route('/news_comment', methods=["POST"])
@user_login_data
def add_news_comment():
    """添加评论"""

    # 0. 判断用户登录
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 1. 获取参数
    data_dict = request.json
    news_id = data_dict.get("news_id")
    comment_str = data_dict.get("comment")
    parent_id = data_dict.get("parent_id")

    # 2. 校验参数
    if not all([news_id, comment_str]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数不足")

    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="该新闻不存在")

    # 3. 逻辑处理 --> 创建评论模型数据 --> 添加到数据库中 --> 还需要返回给前端
    comment = Comment()
    comment.user_id = user.id
    comment.news_id = news_id
    comment.content = comment_str
    if parent_id:
        comment.parent_id = parent_id

    # # 这里必须及时的手动提交
    # 自动提交不是万能的. 有些时候我们在返回数据之前, 是一定要先添加数据的.
    # 自动提交也不能在失败的时候返回错误日志及错误信息.
    # 还是建议手动提交
    try:
        db.session.add(comment)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    # 4. 返回数据
    return jsonify(errno=RET.OK, errmsg="成功", data=comment.to_dict())


'''收藏新闻操作！'''


@news_blue.route("/news_collect", methods=['POST'])
@user_login_data
def news_collect():
    """新闻收藏"""

    # 0. 判断登录
    user = g.user
    if not user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    # 1. 获取参数
    news_id = request.json.get('news_id')
    action = request.json.get('action')

    # 2. 校验参数
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ['collect', 'cancel_collect']:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 先判断是int类型, 再查询新闻数据, 确定有值
    try:
        news_id = int(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="无数据")

    # 3. 逻辑处理 --> 根据不同的点击处理不同的逻辑(添加数据/删除数据)
    if action == 'cancel_collect':
        # 取消收藏
        if news in user.collection_news:
            # 判断自己添加过该新闻,才能删除
            user.collection_news.remove(news)
    else:
        # 添加收藏
        if news not in user.collection_news:
            user.collection_news.append(news)

    # 4. 返回数据
    return jsonify(errno=RET.OK, errmsg="成功")


'''二级页面跳转！'''


@news_blue.route('/<int:news_id>')
@user_login_data
def get_news_detail(news_id):
    # 一. 用户信息
    user = g.user

    # 二. 分类排行
    try:
        news_model_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")

    news_dict_li = []
    # TODO 记得判空处理
    for news in news_model_list:
        news_dict_li.append(news.to_dict())

    # 三. 新闻详情
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    if not news:
        abort(404)

    news.clicks += 1

    # 四. 判断是否收藏
    is_collected = False

    # if 用户已登录: 判断用户是否收藏了当前新闻, 如果收藏, 修改变量为True
    if user:
        if news in user.collection_news:
            is_collected = True

    # 五. 新闻评论信息
    comment_model_list = []
    try:
        comment_model_list = Comment.query.filter(Comment.news_id == news_id).order_by(Comment.create_time.desc()).all()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据库错误")

    comment_dict_list = []
    for comment in comment_model_list:
        comment_dict_list.append(comment.to_dict())

    '''用户关注的设置！是通过发布人的外键指向了新闻，新闻反向判断是否是发布人！'''
    is_follow = False
    # news.user 指的是新闻有发布人信息！
    # user 代表我自己登录！
    if news.user and user:
        if news.user in user.followed:
            is_follow = True

    data = {
        'user': user.to_dict() if user else None,
        'news_dict_li': news_dict_li,
        'news': news.to_dict(),
        'is_collected': is_collected,
        'comments': comment_dict_list,
        'is_follow': is_follow
    }
    return render_template('news/detail.html', data=data)


'''关注与取消关注！'''
'''前端发送'action' 与user_id '''


@news_blue.route('/followed_user', methods=["POST"])
@user_login_data
def followed_user():
    """关注/取消关注用户"""
    if not g.user:
        return jsonify(errno=RET.SESSIONERR, errmsg="用户未登录")

    user_id = request.json.get("user_id")
    action = request.json.get("action")

    if not all([user_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    if action not in ("follow", "unfollow"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    # 查询到关注的用户信息
    try:
        target_user = User.query.get(user_id)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询数据库失败")

    if not target_user:
        return jsonify(errno=RET.NODATA, errmsg="未查询到用户数据")

    # 根据不同操作做不同逻辑
    if action == "follow":
        # 查询当前的新闻id 与是不是我关注的,如果不是那么就添加到我的关注之中！
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            return jsonify(errno=RET.DATAEXIST, errmsg="当前已关注")
        target_user.followers.append(g.user)
    else:
        if target_user.followers.filter(User.id == g.user.id).count() > 0:
            target_user.followers.remove(g.user)

    # 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="数据保存错误")

    return jsonify(errno=RET.OK, errmsg="操作成功")


'''
    使用装饰器，增加了验证的功能！必须这样设置，因为不设置所有使用这个装饰器的都会改成一样的名字！

'''
