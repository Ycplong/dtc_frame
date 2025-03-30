"""
数据解析器实现
"""
import yaml
from pathlib import Path
from typing import Dict, Any
from test_framework.utils.logger import setup_logger

class DataParser:
    """数据解析器类"""
    
    def __init__(self):
        self.logger = setup_logger(__name__)
        
    def load_test_data(self, file_path: str) -> Dict[str, Any]:
        """加载测试数据

        Args:
            file_path: YAML文件路径

        Returns:
            测试数据字典
        """
        try:
            # 读取YAML文件
            with open(file_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            self.logger.info(f"成功加载测试数据: {file_path}")
            if isinstance(data, list):
                if len(data) > 0:
                    return data[0]  # 取第一个测试用例
                return {}
            return data

        except Exception as e:
            self.logger.error(f"加载测试数据失败: {str(e)}")
            raise