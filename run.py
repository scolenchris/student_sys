import os
import sys
from waitress import serve
import traceback

basedir = os.path.dirname(os.path.abspath(__file__))
if basedir not in sys.path:
    sys.path.insert(0, basedir)

try:
    from app import create_app, db
    from app.models import User
except ModuleNotFoundError as e:
    print(f"当前搜索路径: {sys.path}")
    input(f"导入错误: {e}\n按回车键退出...")  # 防止闪退
    sys.exit(1)

app = create_app()


def initialize_system():
    """
    冷启动初始化：
    1) 自动创建数据库表
    2) 检测并创建默认管理员账户
    """
    print("-" * 50)
    print("[系统自检] 正在检查数据库环境...")

    with app.app_context():
        # 确保所有表已创建（SQLite 文件不存在时会自动生成）
        db.create_all()

        # 检查默认管理员是否存在
        admin_user = User.query.filter_by(username="adminwds").first()

        if not admin_user:
            print("[系统初始化] 未检测到管理员，正在创建默认账户...")

            new_admin = User(
                username="adminwds",
                real_name="韦东生",
                role="admin",
                is_approved=True,
                must_change_password=False,
            )

            new_admin.set_password("wds123456@")

            db.session.add(new_admin)
            db.session.commit()

            print("[系统初始化] 管理员创建成功！")
        else:
            print("[系统自检] 管理员账户已存在，跳过初始化。")
    print("-" * 50)


if __name__ == "__main__":

    try:
        initialize_system()

        cpu_count = os.cpu_count() or 2
        default_threads = max(2, min(cpu_count, 4))
        waitress_threads = int(os.environ.get("WAITRESS_THREADS", default_threads))

        print("系统启动中... 请访问 http://localhost:5173 进行调试")
        print(f"Waitress 线程数: {waitress_threads}")
        print(
            "SQLite 模式: "
            f"journal={app.config.get('SQLITE_JOURNAL_MODE')}, "
            f"synchronous={app.config.get('SQLITE_SYNCHRONOUS')}"
        )
        print("注意：如需关闭服务器，请直接关闭此窗口")
        print("=" * 60)

        # 使用 Waitress 作为生产/联调启动方式
        serve(app, host="0.0.0.0", port=5173, threads=waitress_threads)

    except OSError as e:
        if e.winerror == 10048:
            print("\n" + "!" * 60)
            print("【启动失败】端口 5173 被占用！")
            print("原因：上一次运行的程序可能没有完全关闭。")
            print("解决方法：请打开任务管理器，结束所有 'run.exe' 或 'main.exe' 进程。")
            print("!" * 60 + "\n")
        else:
            print(f"\n【启动错误】: {e}")
            traceback.print_exc()
    except Exception as e:
        print(f"\n【未知错误】: {e}")
        traceback.print_exc()
    finally:
        # 避免 Windows 双击启动时窗口闪退，便于查看错误信息
        input("\n程序已结束，按回车键关闭窗口...")
