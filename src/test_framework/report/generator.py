"""
报告生成器实现
"""
import json
from pathlib import Path
from datetime import datetime
import logging
from jinja2 import Environment, FileSystemLoader
from test_framework.utils.logger import setup_logger


class ReportGenerator:
    """报告生成器类"""

    def __init__(self):
        # 获取当前文件所在目录（generator.py 的路径）
        current_dir = Path(__file__).parent

        # 向上回退到项目根目录（假设 generator.py 在 src/test_framework/... 下）
        project_root = current_dir.parent.parent.parent  # 根据实际层级调整

        # 定位到 reports 目录
        self.reports_dir = project_root / "reports"

        # self.reports_dir.mkdir(exist_ok=True)
        self.logger = setup_logger(__name__)

    def generate_allure_report(self, test_results: list):
        """生成Allure报告

        Args:
            test_results: 测试结果列表
        """
        try:
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 创建Allure结果目录
            allure_results_dir = self.reports_dir / "allure-results"
            allure_results_dir.mkdir(exist_ok=True)
            self.logger.info(f"输出报告全部测试{test_results}")
            # 生成Allure结果文件
            for result in test_results:
                result_file = allure_results_dir / f"result_{timestamp}.json"
                with open(result_file, "w", encoding="utf-8") as f:
                    json.dump(result, f, ensure_ascii=False, indent=2)

            self.logger.info("Allure报告数据已生成")

        except Exception as e:
            self.logger.error(f"生成Allure报告失败: {str(e)}")
            raise

    def generate_html_report(self, test_results: list):
        """生成HTML报告

        Args:
            test_results: 测试结果列表
        """
        try:
            # 生成时间戳
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            # 创建HTML报告目录
            html_dir = self.reports_dir / "html"
            html_dir.mkdir(exist_ok=True)

            # 准备报告数据
            report_data = {
                "timestamp": timestamp,
                "total": len(test_results),
                "passed": sum(1 for r in test_results if r["status"] == "passed"),
                "failed": sum(1 for r in test_results if r["status"] == "failed"),
                "results": test_results
            }

            # 加载模板
            env = Environment(loader=FileSystemLoader("src/test_framework/report/templates"))
            template = env.get_template("report.html")

            # 生成HTML报告
            html_file = html_dir / f"report_{timestamp}.html"
            with open(html_file, "w", encoding="utf-8") as f:
                f.write(template.render(**report_data))

            self.logger.info("HTML报告已生成")

        except Exception as e:
            self.logger.error(f"生成HTML报告失败: {str(e)}")
            raise
