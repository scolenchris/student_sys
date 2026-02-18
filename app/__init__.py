from flask import Flask, request, session, g
from flask_cors import CORS
from config import Config
from .models import db, User
from sqlalchemy.exc import OperationalError
from flask import jsonify
import os
import sys

def create_app(config_class=Config):
    # 优先使用当前目录或 exe 目录的 dist，兼容源码运行和打包运行。
    cwd_dist = os.path.join(os.getcwd(), "dist")
    exe_dist = os.path.join(os.path.dirname(sys.executable), "dist")
    dev_dist = "./dist"

    if os.path.exists(cwd_dist):
        dist_path = cwd_dist
        mode_msg = "生产模式 (在当前目录下找到 dist)"
    elif os.path.exists(exe_dist):
        dist_path = exe_dist
        mode_msg = "生产模式 (在exe目录下找到 dist)"
    else:
        dist_path = dev_dist
        mode_msg = "开发模式 (未找到本地dist，尝试使用源码路径)"

    # 启动时输出路径判定，便于排查静态资源问题。
    print("=" * 60)
    print(f"路径判定结果: {mode_msg}")
    print(f"最终使用的前端路径: {dist_path}")
    print(f"路径有效性校验: {os.path.exists(dist_path)}")
    print("=" * 60)

    app = Flask(__name__, static_folder=dist_path, static_url_path="")
    app.config.from_object(config_class)

    # 初始化插件
    CORS(app, supports_credentials=True)
    db.init_app(app)

    @app.before_request
    def load_current_user():
        user_id = session.get("user_id")
        if not user_id:
            g.current_user = None
            return

        user = User.query.get(user_id)
        if not user:
            session.clear()
            g.current_user = None
            return

        g.current_user = user

    @app.errorhandler(413)
    def request_entity_too_large(error):
        return jsonify(msg="上传文件过大，请限制在 16MB 以内"), 413

    @app.errorhandler(OperationalError)
    def handle_db_error(e):
        print(f"数据库错误: {str(e)}")

        if "database is locked" in str(e):
            return jsonify({"msg": "当前提交人数过多，系统繁忙，请稍后重试！"}), 500

        return jsonify({"msg": "数据库操作异常"}), 500

    # 注册蓝图
    from .routes.auth import auth_bp
    from .routes.admin import admin_bp
    from .routes.teacher import teacher_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(admin_bp, url_prefix="/api/admin")
    app.register_blueprint(teacher_bp, url_prefix="/api/teacher")

    @app.route("/")
    def index():
        if not os.path.exists(app.static_folder):
            return (
                "前端构建文件(dist)未找到，请先执行 npm run build 并将 dist 文件夹拷贝到后端根目录。",
                404,
            )
        return app.send_static_file("index.html")

    @app.errorhandler(404)
    def not_found(e):
        # API 路由保持标准 404；前端路由交给 SPA 入口处理。
        if request.path.startswith("/api/"):
            return jsonify(msg="接口不存在"), 404

        if os.path.exists(os.path.join(app.static_folder, "index.html")):
            return app.send_static_file("index.html")

        return "404 Not Found", 404

    # 创建表并在首次启动时补齐科目基础数据。
    with app.app_context():
        db.create_all()

        from .models import Subject

        target_order = [
            "语文",
            "数学",
            "英语",
            "英语听说",
            "物理",
            "化学",
            "道德与法治",
            "历史",
            "生物",
            "地理",
            "体育与健康",
            "信息科技",
            "美术",
            "音乐",
        ]

        if Subject.query.count() == 0:
            for name in target_order:
                db.session.add(Subject(name=name))
            db.session.commit()
            print(">> [SQLite] 科目表初始化完成。")

        db.session.commit()

    return app
