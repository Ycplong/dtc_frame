"""
登录功能测试用例
"""
import pytest
from test_framework.data_parser.parser import DataParser
from test_framework.engine.runner import TestRunner

@pytest.fixture
def test_data():
    """加载测试数据"""
    parser = DataParser()
    return parser.parse_test_data("login")

@pytest.fixture
def runner():
    """创建测试执行器"""
    return TestRunner()

def test_login_success(test_data, runner):
    """测试登录成功场景"""
    result = runner.run_test(test_data[0])
    assert result["status"] == "passed"

def test_login_failed(test_data, runner):
    """测试登录失败场景"""
    result = runner.run_test(test_data[1])
    assert result["status"] == "failed" 