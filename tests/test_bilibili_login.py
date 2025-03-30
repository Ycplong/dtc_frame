"""
B站登录测试用例
"""
import pytest
import logging
from test_framework.data.parser import DataParser
from test_framework.engine.runner import TestRunner

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 在 test_bilibili_login.py 中修改
import os
from pathlib import Path

@pytest.fixture
def test_data():
    """加载测试数据"""
    parser = DataParser()
    # 获取项目根目录的绝对路径
    base_dir = Path(__file__).parent.parent
    # 拼接正确的文件路径
    test_data_path = base_dir / "test_data" / "bilibili_login.yaml"
    return parser.load_test_data(str(test_data_path))

@pytest.fixture
def runner():
    """创建测试执行器"""
    return TestRunner()

def test_bilibili_login(test_data, runner):
    """测试B站登录"""
    logger.info("开始测试B站登录")
    result = runner.run_test(test_data)
    assert result["status"] == "passed"
    runner.generate_reports()
    logger.info("测试完成") 