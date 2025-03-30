"""
步骤引擎实现
"""
from typing import Dict, Any, List, Callable
import time
from functools import wraps
import logging

class StepEngine:
    """步骤引擎类"""
    
    def __init__(self):
        self.steps = {}
        self.retry_times = 3
        self.retry_interval = 1
        self.logger = logging.getLogger(__name__)
        
    def register_step(self, name: str, func: Callable):
        """注册测试步骤
        
        Args:
            name: 步骤名称
            func: 步骤函数
        """
        self.steps[name] = func
        
    def execute_step(self, step_name: str, **kwargs) -> Any:
        """执行测试步骤
        
        Args:
            step_name: 步骤名称
            **kwargs: 步骤参数
            
        Returns:
            步骤执行结果
        """
        if step_name not in self.steps:
            raise ValueError(f"未注册的步骤: {step_name}")
            
        step_func = self.steps[step_name]
        
        for attempt in range(self.retry_times):
            try:
                self.logger.info(f"执行步骤: {step_name}, 参数: {kwargs}")
                result = step_func(**kwargs)
                self.logger.info(f"步骤执行成功: {step_name}")
                return result
            except Exception as e:
                self.logger.error(f"步骤执行失败: {step_name}, 错误: {str(e)}")
                if attempt == self.retry_times - 1:
                    raise
                time.sleep(self.retry_interval)
                
    def execute_sequence(self, steps: List[Dict[str, Any]]) -> List[Any]:
        """执行步骤序列
        
        Args:
            steps: 步骤列表，每个步骤包含name和params
            
        Returns:
            步骤执行结果列表
        """
        results = []
        for step in steps:
            result = self.execute_step(step["name"], **step.get("params", {}))
            results.append(result)
        return results
        
    def retry_on_failure(self, max_retries: int = 3, delay: float = 1.0):
        """重试装饰器
        
        Args:
            max_retries: 最大重试次数
            delay: 重试间隔(秒)
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                for attempt in range(max_retries):
                    try:
                        return func(*args, **kwargs)
                    except Exception as e:
                        if attempt == max_retries - 1:
                            raise
                        self.logger.warning(f"步骤执行失败，准备重试: {func.__name__}, 错误: {str(e)}")
                        time.sleep(delay)
                return None
            return wrapper
        return decorator 