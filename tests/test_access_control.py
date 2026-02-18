import os
import tempfile
import unittest

from app import create_app
from app.models import db, User


class TestConfig:
    TESTING = True
    SECRET_KEY = "test-secret"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


class AccessControlTestCase(unittest.TestCase):
    def setUp(self):
        self.db_fd, self.db_path = tempfile.mkstemp(suffix=".db")
        TestConfig.SQLALCHEMY_DATABASE_URI = f"sqlite:///{self.db_path}"

        self.app = create_app(TestConfig)
        self.client = self.app.test_client()

        with self.app.app_context():
            db.create_all()
            admin = User(
                username="admin1",
                role="admin",
                real_name="Admin",
                is_approved=True,
            )
            admin.set_password("pass123")

            teacher = User(
                username="teacher1",
                role="teacher",
                real_name="Teacher",
                is_approved=True,
            )
            teacher.set_password("pass123")
            db.session.add_all([admin, teacher])
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        os.close(self.db_fd)
        os.unlink(self.db_path)

    def _login(self, username, password="pass123"):
        return self.client.post(
            "/api/auth/login", json={"username": username, "password": password}
        )

    def test_unauthenticated_access_returns_401(self):
        admin_resp = self.client.get("/api/admin/pending_users")
        teacher_resp = self.client.get("/api/teacher/score_list")

        self.assertEqual(admin_resp.status_code, 401)
        self.assertEqual(teacher_resp.status_code, 401)

    def test_teacher_cannot_access_admin_api(self):
        self._login("teacher1")
        resp = self.client.get("/api/admin/pending_users")
        self.assertEqual(resp.status_code, 403)

    def test_admin_cannot_access_teacher_api(self):
        self._login("admin1")
        resp = self.client.get("/api/teacher/score_list")
        self.assertEqual(resp.status_code, 403)


if __name__ == "__main__":
    unittest.main()
