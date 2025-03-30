"""
数据解析器实现
"""
import os
import yaml
from typing import Dict, Any, List
from pathlib import Path

class DataParser:
    """数据解析器类"""
    
    def __init__(self, data_dir: str = "test_data"):
        # 获取项目根目录（src的父目录）
        self.root_dir = Path(__file__).parent.parent.parent.parent
        self.data_dir = self.root_dir / data_dir
        
    def load_yaml(self, file_name: str) -> List[Dict[str, Any]]:
        """加载YAML文件
        
        Args:
            file_name: YAML文件名
            
        Returns:
            解析后的数据列表
        """
        file_path = self.data_dir / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"数据文件不存在: {file_path}")
            
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            # 确保返回的是列表
            if isinstance(data, dict):
                return [data]
            return data
            
    def parse_test_data(self, test_case: str) -> Dict[str, Any]:
        """解析测试用例数据
        
        Args:
            test_case: 测试用例名称
            
        Returns:
            测试数据字典
        """
        data_file = f"{test_case}.yaml"
        raw_data = self.load_yaml(data_file)
        
        # 处理数据依赖关系
        processed_data = self._process_dependencies(raw_data)
        
        # 返回第一个测试用例
        return processed_data[0]
        
    def _process_dependencies(self, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """处理数据依赖关系
        
        Args:
            data: 原始数据列表
            
        Returns:
            处理后的数据列表
        """
        # TODO: 实现数据依赖处理逻辑
        return data 