"""
测试执行引擎实现
"""
import pytest
from typing import Dict, Any, List
from datetime import datetime
import allure
from pathlib import Path
import json
import time
import logging
from playwright.sync_api import sync_playwright
from test_framework.ui.page_object import BasePage
from test_framework.api.client import APIClient
from test_framework.step_engine.engine import StepEngine
from test_framework.session.manager import SessionManager
from test_framework.utils.logger import setup_logger
from test_framework.report.generator import ReportGenerator

class TestRunner:
    """测试执行引擎类"""
    
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.logger = setup_logger(__name__)
        self.step_engine = StepEngine()
        self.session_manager = SessionManager()
        self.report_generator = ReportGenerator()
        self.test_results = []  # 用于存储所有测试结果

    def setup(self):
        """初始化测试环境"""
        self.logger.info("初始化测试环境")
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=False)
        self.context = self.browser.new_context()
        self.page = self.context.new_page()

    def teardown(self):
        """清理测试环境"""
        self.logger.info("清理测试环境")
        if self.page:
            self.page.close()
        if self.context:
            self.context.close()
        if self.browser:
            self.browser.close()
        if self.playwright:
            self.playwright.stop()

    def run_test(self, test_case: Dict[str, Any]) -> Dict[str, Any]:
        """运行单个测试用例

        Args:
            test_case: 测试用例数据

        Returns:
            测试结果
        """
        start_time = datetime.now()
        test_name = test_case.get("name", "未命名测试")
        self.logger.info(f"开始执行测试用例: {test_name}")

        try:
            # 设置测试用例描述
            allure.dynamic.title(test_name)
            allure.dynamic.description(test_case.get("description", ""))

            # 执行测试步骤
            for step in test_case.get("steps", []):
                step_name = step.get("name", "未命名步骤")
                self.logger.info(f"执行步骤: {step_name}")
                with allure.step(step_name):
                    self._execute_step(step)

            result = {
                "status": "passed",
                "name": test_name,
                "start_time": start_time,
                "end_time": datetime.now(),
                "steps": test_case.get("steps", [])
            }

        except Exception as e:
            self.logger.error(f"测试用例执行失败: {str(e)}")
            result = {
                "status": "failed",
                "name": test_name,
                "start_time": start_time,
                "end_time": datetime.now(),
                "error": str(e),
                "steps": test_case.get("steps", [])
            }
            raise

        finally:
            # 保存会话
            if "session" in test_case:
                self._save_session(test_case["session"])

            # 将结果添加到结果列表
            self.test_results.append(result)

            # 清理测试环境
            self.teardown()

        return result

    def _load_session(self, session_name: str):
        """加载会话

        Args:
            session_name: 会话名称
        """
        # 加载UI会话
        self.context = self.session_manager.load_ui_session(session_name)
        if self.context:
            self.page = self.context.new_page()

        # 加载API会话
        api_session = self.session_manager.load_api_session(session_name)
        if api_session:
            self.api_client = APIClient("")
            self.api_client.session = api_session

    def _save_session(self, session_name: str):
        """保存会话

        Args:
            session_name: 会话名称
        """
        if self.context:
            self.session_manager.save_ui_session(self.context, session_name)

        if hasattr(self, "api_client"):
            self.session_manager.save_api_session(self.api_client.session, session_name)

    def _execute_step(self, step: Dict[str, Any]):
        """执行测试步骤

        Args:
            step: 步骤数据
        """
        step_type = step.get("type")
        action = step.get("action")
        params = step.get("params", {})

        self.logger.info(f"执行步骤: {step.get('name', '未命名步骤')}")

        if step_type == "ui":
            self._execute_ui_step(action, params)
        elif step_type == "api":
            self._execute_api_step(action, params)
        else:
            raise ValueError(f"不支持的步骤类型: {step_type}")

    def _execute_ui_step(self, action: str, params: Dict[str, Any]):
        """执行UI测试步骤

        Args:
            action: 动作名称
            params: 动作参数
        """
        if not self.page:
            self.setup()

        page_object = BasePage(self.page)

        if action == "navigate":
            self.page.goto(params["url"])
        elif action == "click":
            page_object.click(params["selector"])
        elif action == "input_text":
            page_object.input_text(params["selector"], params["text"])
        elif action == "verify_text":
            page_object.verify_text(params["selector"], params["text"])
        elif action == "save_session":
            self._save_session(params["session_name"])
        elif action == "wait_for_load_state":
            page_object.wait_for_load_state(params["state"])
        else:
            raise ValueError(f"不支持的UI动作: {action}")

    def _execute_api_step(self, action: str, params: Dict[str, Any]):
        """执行API测试步骤

        Args:
            action: 动作名称
            params: 动作参数
        """
        if not hasattr(self, "api_client"):
            self.api_client = APIClient(params.get("base_url", ""))

        if action == "get":
            response = self.api_client.get(params["endpoint"], **params.get("kwargs", {}))
        elif action == "post":
            response = self.api_client.post(params["endpoint"], **params.get("kwargs", {}))
        elif action == "put":
            response = self.api_client.put(params["endpoint"], **params.get("kwargs", {}))
        elif action == "delete":
            response = self.api_client.delete(params["endpoint"], **params.get("kwargs", {}))
        elif action == "save_session":
            self._save_session(params["session_name"])
        else:
            raise ValueError(f"不支持的API动作: {action}")

        # 验证响应
        if "verify" in params:
            self.api_client.verify_response(response, **params["verify"])

    def generate_reports(self):
        """生成测试报告"""
        try:
            # 生成Allure报告
            self.report_generator.generate_allure_report(self.test_results)

            # 生成HTML报告
            self.report_generator.generate_html_report(self.test_results)

            self.logger.info("测试报告生成完成")

        except Exception as e:
            self.logger.error(f"生成测试报告失败: {str(e)}")
            raise

    def analyze_results(self) -> Dict[str, Any]:
        """分析测试结果

        Returns:
            分析结果
        """
        # 统计测试结果
        total = len(self.test_results)
        passed = sum(1 for r in self.test_results if r["status"] == "passed")
        failed = sum(1 for r in self.test_results if r["status"] == "failed")

        # 计算平均执行时间
        execution_times = []
        for result in self.test_results:
            start_time = result["start_time"]
            end_time = result["end_time"]
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time)
                end_time = datetime.fromisoformat(end_time)
            execution_times.append((end_time - start_time).total_seconds())

        avg_time = sum(execution_times) / len(execution_times) if execution_times else 0

        return {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total if total > 0 else 0,
            "avg_execution_time": avg_time
        }