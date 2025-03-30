"""
会话管理模块
"""
import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from playwright.sync_api import BrowserContext
import requests
import logging


class SessionManager:
    """会话管理类"""

    def __init__(self):
        self.sessions_dir = Path("sessions")
        self.sessions_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)

    def save_ui_session(self, context: BrowserContext, session_name: str):
        """保存UI会话

        Args:
            context: 浏览器上下文
            session_name: 会话名称
        """
        try:
            # 获取所有cookies
            cookies = context.cookies()

            # 保存cookies到文件
            session_file = self.sessions_dir / f"{session_name}_ui.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(cookies, f, ensure_ascii=False, indent=2)

            self.logger.info(f"UI会话已保存: {session_name}")

        except Exception as e:
            self.logger.error(f"保存UI会话失败: {str(e)}")
            raise

    def load_ui_session(self, session_name: str) -> Optional[BrowserContext]:
        """加载UI会话

        Args:
            session_name: 会话名称

        Returns:
            浏览器上下文
        """
        try:
            session_file = self.sessions_dir / f"{session_name}_ui.json"
            if not session_file.exists():
                self.logger.warning(f"UI会话文件不存在: {session_name}")
                return None

            # 读取cookies
            with open(session_file, "r", encoding="utf-8") as f:
                cookies = json.load(f)

            self.logger.info(f"UI会话已加载: {session_name}")
            return cookies

        except Exception as e:
            self.logger.error(f"加载UI会话失败: {str(e)}")
            return None

    def save_api_session(self, session: requests.Session, session_name: str):
        """保存API会话

        Args:
            session: requests会话对象
            session_name: 会话名称
        """
        try:
            # 获取cookies和headers
            session_data = {
                "cookies": dict(session.cookies),
                "headers": dict(session.headers)
            }

            # 保存会话数据到文件
            session_file = self.sessions_dir / f"{session_name}_api.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"API会话已保存: {session_name}")

        except Exception as e:
            self.logger.error(f"保存API会话失败: {str(e)}")
            raise

    def load_api_session(self, session_name: str) -> Optional[requests.Session]:
        """加载API会话

        Args:
            session_name: 会话名称

        Returns:
            requests会话对象
        """
        try:
            session_file = self.sessions_dir / f"{session_name}_api.json"
            if not session_file.exists():
                self.logger.warning(f"API会话文件不存在: {session_name}")
                return None

            # 读取会话数据
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            # 创建新的会话对象
            session = requests.Session()
            session.cookies.update(session_data["cookies"])
            session.headers.update(session_data["headers"])

            self.logger.info(f"API会话已加载: {session_name}")
            return session

        except Exception as e:
            self.logger.error(f"加载API会话失败: {str(e)}")
            return None

    def save_session_data(self, session_name: str, data: Dict[str, Any]):
        """保存会话数据

        Args:
            session_name: 会话名称
            data: 会话数据
        """
        try:
            session_file = self.sessions_dir / f"{session_name}_data.json"
            with open(session_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"会话数据已保存: {session_name}")

        except Exception as e:
            self.logger.error(f"保存会话数据失败: {str(e)}")
            raise

    def get_session_data(self, session_name: str) -> Optional[Dict[str, Any]]:
        """获取会话数据

        Args:
            session_name: 会话名称

        Returns:
            会话数据
        """
        try:
            session_file = self.sessions_dir / f"{session_name}_data.json"
            if not session_file.exists():
                self.logger.warning(f"会话数据文件不存在: {session_name}")
                return None

            with open(session_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            self.logger.info(f"会话数据已加载: {session_name}")
            return data

        except Exception as e:
            self.logger.error(f"加载会话数据失败: {str(e)}")
            return None

    def clear_session(self, session_name: str):
        """清除会话

        Args:
            session_name: 会话名称
        """
        try:
            # 删除所有相关的会话文件
            for file in self.sessions_dir.glob(f"{session_name}_*.json"):
                file.unlink()

            self.logger.info(f"会话已清除: {session_name}")

        except Exception as e:
            self.logger.error(f"清除会话失败: {str(e)}")
            raise