from datetime import datetime, timedelta
import time
from info import constants, db
from info.models import User, News, Category, Comment
from info.utils.common import user_login_data
from info.utils.image_storage import storage
from info.utils.response_code import RET
from . import admin_blue
from flask import render_template, current_app, session, jsonify, request, g, abort, redirect, url_for

'''登录界面显示
    先判断是否有session 信息，如果有session信息就会直接进入index页面
    session 是get 请求来传递信息的！
    点击提交按钮，验证查询信息，如果用户名或者密码有误，那么就会返回到前端页面
    登录界面是从新渲染登录页面来执行的！ 
    登录界面是从新渲染登录页面来执行的！ 
'''


@admin_blue.route('/login', methods=['get', 'POST'])
@user_login_data
def login():
    user = g.user
    if request.method == 'GET':
        # 如果有管理员的session信息，那么直接进入到管理员页面，不需要登录！
        is_user = session.get('user_id', None)
        is_admin = session.get('is_admin', False)
        if is_admin and is_user:
            return redirect(url_for('admin.index'))
        return render_template('admin/login.html')

    username = request.form.get('username')

    password = request.form.get('password')

    if not all([username, password]):
        return render_template('admin/login.html', errmsg='参数不完整!')

    try:
        user = User.query.filter(username == User.mobile, User.is_admin == True).first()
    except Exception as e:
        current_app.logger.error(e)
        return render_template('admin/login.html', errmsg='数据库查询失败！')
    # 用户名称或者密码验证
    if not user:
        return render_template('admin/login.html', errmsg='你输入密码不正确或者用户名不存在！')
    if not user.check_passowrd(password):
        return render_template('admin/login.html', errmsg='你输入密码不正确或者用户名不存在！')

    session['user_id'] = user.id
    session['nickname'] = user.nick_name
    session['mobile'] = user.mobile
    session['is_admin'] = user.is_admin

    return redirect(url_for('admin.index'))


'''

跳转页面!
    通过装饰器进行身份验证！
    页面跳转是通过请求钩子来进行！
    在addmin __init__ 之中定义请求钩子！

'''


@admin_blue.route('/index')
@user_login_data
def index():
    user = g.user
    data = {
        'user': user.to_dict()
    }
    return render_template('admin/index.html', data=data)


'''通过渲染一个页面包含另一个页面！用户活跃统计查询！
    只有get 请求，返回数据！
    日期格式保持与数据库日期格式相同！
'''


@admin_blue.route('/user_count')
@user_login_data
def user_count():
    user = g.user
    total_count = 0
    # 获取用户总数！
    try:
        total_count = User.query.filter(User.is_admin == False).count()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg='数据库查询失败！')

    # 查询每月的增加人数！
    loca_time = time.localtime()
    # time.struct_time(tm_year=2018, tm_mon=6, tm_mday=4, tm_hour=21,
    #  tm_min=22, tm_sec=26, tm_wday=0, tm_yday=155, tm_isdst=0)
    mon_count = 0
    # 2018-6-1 00:00:00  需要显示这样的时间，才能进行相减操作
    mou_people = datetime.strptime('%d-%02d-1' % (loca_time.tm_year, loca_time.tm_mon), '%Y-%m-%d')
    try:
        mon_count = User.query.filter(User.is_admin == False, User.create_time >= mou_people).count()
    except Exception as e:
        current_app.logger.error(e)
        return jsonify(errno=RET.DATAERR, errmsg='数据库查询失败！')

    # 查询每天增加的人数！
    day_count = 0
    try:
        # 查询今天的时间！
        day_begin = '%d-%02d-%02d' % (loca_time.tm_year, loca_time.tm_mon, loca_time.tm_mday)
        # 将今天的时间格式化一下 2018-6-4 00:00:00
        day_begin_date = datetime.strptime(day_begin, '%Y-%m-%d')
        day_count = User.query.filter(User.is_admin == False, User.create_time > day_begin_date).count()
    except Exception as e:
        current_app.logger.error(e)

    '''根据前端的图表实现方式，只需要传递列表（日期）与数据列表'''
    dat = datetime.now().strftime('%Y-%m-%d')
    now_date = datetime.strptime(datetime.now().strftime('%Y-%m-%d'), '%Y-%m-%d')
    # 总量
    active_count = []
    # 日期！
    active_date = []
    for i in range(0, 31):
        # timedelta(day=i) 表示增加 i 天！
        begin_date = now_date - timedelta(days=i)
        end_date = now_date - timedelta(days=(i - 1))
        active_date.append(begin_date.strftime('%Y-%m-%d'))
        count = 0
    try:
        # 查询日期！
        count = User.query.filter(User.is_admin == False, User.last_login >= begin_date,
                                  User.last_login < end_date).count()
    except Exception as e:
        current_app.logger.error(e)
    active_count.append(count)
    active_count.reverse()
    active_count.reverse()
    data = {
        'total_count': total_count,
        'mon_count': mon_count,
        'day_count': day_count,
        'active_count': active_count,
        'active_date': active_date
    }
    return render_template('admin/user_count.html', data=data)


'''
    列表查询排序！
    分页查询！
    
'''


@admin_blue.route('/user_list')
@user_login_data
def user_list():
    """获取用户列表"""
    # 获取参数
    page = request.args.get("p", 1)

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    # 设置变量默认值
    users = []
    current_page = 1
    total_page = 1
    # 查询数据
    try:
        paginate = User.query.filter(User.is_admin == False).order_by(
            User.last_login.desc()).paginate(page,
                                             constants.ADMIN_USER_PAGE_MAX_COUNT,
                                             False)
        # 通过get 请求的得到的每页数据！
        users = paginate.items
        # 总页数
        current_page = paginate.page
        # 页码数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
    # 将模型列表转成字典列表
    users_list = []
    for user in users:
        users_list.append(user.to_admin_dict())

    # 只需要将总页数，每页有多少个，第几页传递即可！
    context = {
        "total_page": total_page,
        "current_page": current_page,
        "users": users_list
    }
    return render_template('admin/user_list.html', data=context)


'''新闻发布状态显示！与新闻搜索功能的实现！'''
'''新闻搜索是get 请求发送过去的！'''


@admin_blue.route('/news_review')
@user_login_data
def news_review():
    # 前端发送给我们需要第几页的数据
    page = request.args.get('page', 1)
    key_worlds = request.args.get('keywords', '')

    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1
    current_page = 1
    total_page = 1
    users = []
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
    # 分页获取数据！
    # 通过解包来为 filter增加内容!
    files = [News.status != 0]
    if key_worlds:
        files.append(News.title.contains(key_worlds))
    try:
        paginate = News.query.filter(*files).order_by(News.create_time.desc()).paginate(page,
                                                                                        constants.ADMIN_NEWS_PAGE_MAX_COUNT,
                                                                                        False)
        users = paginate.items
        # 总页数
        current_page = paginate.page
        # 页码数
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)
    # 返回的是一个对象，因此需要转换成字典(每个对象都需要转换！)
    user_list = []
    for user in users:
        user_list.append(user.to_dict())

    data = {
        "total_page": total_page,
        "current_page": current_page,
        "news_list": user_list
    }

    return render_template('admin/news_review.html', data=data)


'''新闻审核'''
'''　get 请求最终必须返回数据! '''


@admin_blue.route('/news_review_detail', methods=['GET', 'POST'])
def news_review_detail():
    """新闻审核"""
    if request.method == 'GET':
        # 获取新闻id
        news_id = request.args.get("news_id")
        if not news_id:
            return render_template('admin/news_review_detail.html', data={"errmsg": "未查询到此新闻"})

        # 通过id查询新闻
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_review_detail.html', data={"errmsg": "未查询到此新闻"})
        # 必须返回 news ,前面都满足的情况之下，有数据返回！
        data = {'news': news.to_dict()}
        return render_template('admin/news_review_detail.html', data=data)

    # 执行审核操作
    # 1.获取参数
    news_id = request.json.get("news_id")
    action = request.json.get("action")

    # 2.判断参数
    if not all([news_id, action]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    if action not in ("accept", "reject"):
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")

    news = None
    try:
        # 3.查询新闻
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)

    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到数据")

    # 4.根据不同的状态设置不同的值
    if action == "accept":
        news.status = 0
    else:
        # 拒绝通过，需要获取原因，将原因存储到数据库之中！
        reason = request.json.get("reason")
        if not reason:
            return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
        news.reason = reason
        news.status = -1

    # 保存数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="数据保存失败")
    return jsonify(errno=RET.OK, errmsg="操作成功")


'''新闻版式编辑状态显示!搜索功能的实现！'''


@admin_blue.route('/news_edit')
def news_edit():
    """返回新闻列表"""

    page = request.args.get("p", 1)
    keywords = request.args.get("keywords", "")
    try:
        page = int(page)
    except Exception as e:
        current_app.logger.error(e)
        page = 1

    news_list = []
    current_page = 1
    total_page = 1

    # 也是利用拆包来实现条件的增加！
    try:
        filters = []
        # 如果有关键词
        if keywords:
            # 添加关键词的检索选项
            filters.append(News.title.contains(keywords))

        # 查询
        paginate = News.query.filter(*filters) \
            .order_by(News.create_time.desc()) \
            .paginate(page, constants.ADMIN_NEWS_PAGE_MAX_COUNT, False)

        news_list = paginate.items
        current_page = paginate.page
        total_page = paginate.pages
    except Exception as e:
        current_app.logger.error(e)

    news_dict_list = []
    for news in news_list:
        news_dict_list.append(news.to_basic_dict())

    context = {"total_page": total_page, "current_page": current_page, "news_list": news_dict_list}

    return render_template('admin/news_edit.html', data=context)


'''新闻的编辑'''


@admin_blue.route('/news_edit_detail', methods=['GET', 'POST'])
def news_edit_detail():
    """新闻编辑详情"""
    if request.method == 'GET':
        # 获取参数
        news_id = request.args.get("news_id")

        if not news_id:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})

        # 查询新闻
        news = None
        try:
            news = News.query.get(news_id)
        except Exception as e:
            current_app.logger.error(e)

        if not news:
            return render_template('admin/news_edit_detail.html', data={"errmsg": "未查询到此新闻"})

        # 查询分类的数据,删除最新的分类
        categories = Category.query.all()
        categories_li = []
        for category in categories:
            c_dict = category.to_dict()
            c_dict["is_selected"] = False
            if category.id == news.category_id:
                c_dict["is_selected"] = True
            categories_li.append(c_dict)
        # 移除`最新`分类
        categories_li.pop(0)

        data = {
            "news": news.to_dict(),
            "categories": categories_li
        }
        return render_template('admin/news_edit_detail.html', data=data)
    news_id = request.form.get("news_id")
    title = request.form.get("title")
    digest = request.form.get("digest")
    content = request.form.get("content")
    index_image = request.files.get("index_image")
    category_id = request.form.get("category_id")
    # 1.1 判断数据是否有值
    if not all([title, digest, content, category_id]):
        return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

    news = None
    try:
        news = News.query.get(news_id)
    except Exception as e:
        current_app.logger.error(e)
    if not news:
        return jsonify(errno=RET.NODATA, errmsg="未查询到新闻数据")

    # 1.2 尝试读取图片
    if index_image:
        try:
            index_image = index_image.read()
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.PARAMERR, errmsg="参数有误")

        # 2. 将标题图片上传到七牛
        try:
            key = storage(index_image)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.THIRDERR, errmsg="上传图片错误")
        news.index_image_url = constants.QINIU_DOMIN_PREFIX + key
    # 3. 设置相关数据
    news.title = title
    news.digest = digest
    news.content = content
    news.category_id = category_id

    # 4. 保存到数据库
    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    # 5. 返回结果
    return jsonify(errno=RET.OK, errmsg="编辑成功")


'''新闻分类管理'''
'''前端发送请求如果只有name 那么就是添加分类信息,如果两者都有那么就是更改分类信息！'''


@admin_blue.route('/news_type', methods=['GET', 'POST'])
def news_type():
    if request.method == 'GET':
        # 获取所有的分类数据
        categories = Category.query.all()
        # 定义列表保存分类数据
        categories_dicts = []

        for category in categories:
            # 获取字典
            cate_dict = category.to_dict()
            # 拼接内容
            categories_dicts.append(cate_dict)

        categories_dicts.pop(0)
        # 返回内容
        return render_template('admin/news_type.html', data={"categories": categories_dicts})
    # post　请求！
    category_id = request.json.get("id")
    category_name = request.json.get("name")
    if not category_name:
        return jsonify(errno=RET.PARAMERR, errmsg="参数错误")
    # 判断是否有分类id
    if category_id:
        try:
            category = Category.query.get(category_id)
        except Exception as e:
            current_app.logger.error(e)
            return jsonify(errno=RET.DBERR, errmsg="查询数据失败")

        if not category:
            return jsonify(errno=RET.NODATA, errmsg="未查询到分类信息")
        # 如果传入的id 与名称能够在数据库之中查询到，就更改名称！
        category.name = category_name
    else:
        # 如果没有分类id，则是添加分类
        category = Category()
        category.name = category_name
        db.session.add(category)

    try:
        db.session.commit()
    except Exception as e:
        current_app.logger.error(e)
        db.session.rollback()
        return jsonify(errno=RET.DBERR, errmsg="保存数据失败")
    return jsonify(errno=RET.OK, errmsg="保存数据成功")
