from info import constants
from info.models import User, News, Category
from info.utils.common import user_login_data
from info.utils.response_code import RET
from . import index_blue
from flask import render_template, current_app, session, jsonify, request, g

# GET请求
# cid : 分类ID
# page : 当前页码
# per_page: 每页的数量
# 全部选填
''' ajax动态加载数据,前端触发事件，事件发送请求获取数据！数据进行响应！
    动态加载数据，每当触发一个条件就会触发get请求
 '''


@index_blue.route('/news_list')
def get_new_list():
    # 1. 获取参数(可选, 可以设置默认值)

    cid = request.args.get('cid', 1)
    page = request.args.get('page', 1)
    per_page = request.args.get('per_page', 10)

    # 2. 校验参数(int --> 强转类型成功, 就说明是数字)
    try:
        cid = int(cid)
        page = int(page)
        per_page = int(per_page)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.PARAMERR, errmsg='参数错误')

    # 3. 查询数据(filter(可能有,可能没有).order_by(时间降序).paginate(页码, 每页的数量, 出错是否要返回报错信息))

    # 如果分类ID传入的是1, 那么就不需要设置filter.
    # 实际数据库之中没有category_id 没有 1
    filter = [News.status == 0]  # 判断新闻的状态是否为０　，为０表示已经审核完成！
    if cid != 1:
        filter.append(News.category_id == cid)

    try:
        # *filter可以将根据查询参数产生的查询条件语句展开
        # 根据新闻的分类查出对应的新闻并且时间倒序，取出前十个
        # paginate 是指的是页码！
        paginates = News.query.filter(*filter).order_by(News.create_time.desc()).paginate(page, per_page, False)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg='查询数据库错误')

    # 获取需要的数据
    news_model_list = paginates.items
    total_page = paginates.pages
    current_page = paginates.page

    # 模型转字典
    news_dict_li = []
    for news in news_model_list:
        news_dict_li.append(news.to_dict())

    data = {

        'news_dict_li': news_dict_li,
        'total_page': total_page,
        'current_page': current_page
    }

    # 4. 返回数据
    return jsonify(errno=RET.OK, errmsg='OK', data=data)


'''
    排行信息，分类信息加载！
    直接进入到主页面进行用户身份认证，排行榜加载！
    前端没有不需要发送数据加载请求，只需要后端返回数据即可！
'''


@index_blue.route('/')
@user_login_data
def index():
    # 一. 用户信息
    user = g.user

    # 二. 点击排行
    # 查询数据库-->模型列表-->模型转字典-->拼接到data中-->处理模板代码
    try:
        news_model_list = News.query.order_by(News.clicks.desc()).limit(constants.CLICK_RANK_MAX_NEWS)
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")

    news_dict_li = []
    for news in news_model_list:
        news_dict_li.append(news.to_dict())

    # 三. 分类信息查询
    try:
        categories = Category.query.all()
    except Exception as e:
        current_app.looger.error(e)
        return jsonify(errno=RET.DBERR, errmsg="查询失败")

    category_dict_li = []
    for category in categories:
        category_dict_li.append(category.to_dict())

    # 如果查询到了--> 可以拼接要显示的相关数据
    data = {
        'user': user.to_dict() if user else None,
        'news_dict_li': news_dict_li,
        'category_dict_li': category_dict_li
    }
    # 将数据传递给模板
    return render_template('news/index.html', data=data)


'''每次加载一个新的页面就会加上图标的样式！'''


# 处理浏览器自动访问网站图标的路由
@index_blue.route('/favicon.ico')
def favicon_ico():
    # 使用current_app, 发送静态文件(图片/文本/js/html)
    return current_app.send_static_file('news/favicon.ico')


'''

    主要是将列表转换成字典的形式，巧妙的 to_dict()    
    登录之前先验证是否有session值，如果有session 的值，那么就会渲染模板！
    
'''
