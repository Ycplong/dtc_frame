"""
API客户端实现
"""
import requests
from typing import Dict, Any, Optional
from requests.exceptions import RequestException
import logging
import json
from pathlib import Path

class APIClient:
    """API客户端类"""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = requests.Session()
        self.logger = logging.getLogger(__name__)
        self.response_dir = Path("api_responses")
        self.response_dir.mkdir(exist_ok=True)
        
    def request(
        self,
        method: str,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: int = 30,
        save_response: bool = True
    ) -> requests.Response:
        """发送HTTP请求
        
        Args:
            method: 请求方法
            endpoint: 接口路径
            params: URL参数
            data: 请求体数据
            headers: 请求头
            timeout: 超时时间(秒)
            save_response: 是否保存响应
            
        Returns:
            响应对象
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            self.logger.info(f"发送请求: {method} {url}")
            self.logger.debug(f"请求参数: {params}")
            self.logger.debug(f"请求数据: {data}")
            
            response = self.session.request(
                method=method,
                url=url,
                params=params,
                json=data,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            
            if save_response:
                self._save_response(response)
                
            return response
            
        except RequestException as e:
            self.logger.error(f"请求失败: {str(e)}")
            raise APIError(f"请求失败: {str(e)}")
            
    def _save_response(self, response: requests.Response):
        """保存响应数据
        
        Args:
            response: 响应对象
        """
        timestamp = response.headers.get("Date", "")
        endpoint = response.request.path_url.replace("/", "_")
        filename = f"{endpoint}_{timestamp}.json"
        
        try:
            data = response.json()
            with open(self.response_dir / filename, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.warning(f"保存响应失败: {str(e)}")
            
    def get(self, endpoint: str, **kwargs) -> requests.Response:
        """发送GET请求"""
        return self.request("GET", endpoint, **kwargs)
        
    def post(self, endpoint: str, **kwargs) -> requests.Response:
        """发送POST请求"""
        return self.request("POST", endpoint, **kwargs)
        
    def put(self, endpoint: str, **kwargs) -> requests.Response:
        """发送PUT请求"""
        return self.request("PUT", endpoint, **kwargs)
        
    def delete(self, endpoint: str, **kwargs) -> requests.Response:
        """发送DELETE请求"""
        return self.request("DELETE", endpoint, **kwargs)
        
    def verify_response(self, response: requests.Response, 
                       expected_status: int = 200,
                       expected_data: Optional[Dict[str, Any]] = None) -> bool:
        """验证响应
        
        Args:
            response: 响应对象
            expected_status: 期望的状态码
            expected_data: 期望的响应数据
            
        Returns:
            是否验证通过
        """
        if response.status_code != expected_status:
            self.logger.error(f"状态码不匹配: 期望 {expected_status}, 实际 {response.status_code}")
            return False
            
        if expected_data:
            try:
                actual_data = response.json()
                for key, value in expected_data.items():
                    if key not in actual_data or actual_data[key] != value:
                        self.logger.error(f"响应数据不匹配: 期望 {expected_data}, 实际 {actual_data}")
                        return False
            except Exception as e:
                self.logger.error(f"验证响应数据失败: {str(e)}")
                return False
                
        return True

class APIError(Exception):
    """API异常类"""
    pass 