"""
UI页面对象实现
"""
from typing import Optional, Dict, Any
from playwright.sync_api import Page, Locator, TimeoutError
import cv2
import numpy as np
import time
from pathlib import Path
import logging
from loguru import logger

class BasePage:
    """页面基类"""
    
    def __init__(self, page: Page):
        self.page = page
        self.screenshot_dir = Path("screenshots")
        self.screenshot_dir.mkdir(exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
    def find_element(self, selector: str, timeout: int = 30000, 
                    smart_wait: bool = True) -> Optional[Locator]:
        """智能查找元素
        
        Args:
            selector: 元素选择器
            timeout: 超时时间(ms)
            smart_wait: 是否启用智能等待
            
        Returns:
            元素对象
        """
        self.logger.info(f"查找元素: {selector}")
        if smart_wait:
            # 等待网络空闲
            self.logger.info("等待页面加载完成")
            self.page.wait_for_load_state("networkidle")
            
        try:
            element = self.page.wait_for_selector(selector, timeout=timeout)
            if element:
                # 等待元素稳定
                self._wait_for_element_stable(element)
            self.logger.info(f"元素已找到: {selector}")
            return element
        except TimeoutError as e:
            self.logger.error(f"查找元素失败: {str(e)}")
            # 尝试图像识别定位
            return self._find_element_by_image(selector)
            
    def _wait_for_element_stable(self, element: Locator, max_attempts: int = 3):
        """等待元素稳定
        
        Args:
            element: 元素对象
            max_attempts: 最大尝试次数
        """
        for _ in range(max_attempts):
            try:
                # 检查元素是否可见和可交互
                if element.is_visible() and element.is_enabled():
                    return
                time.sleep(0.5)
            except Exception:
                time.sleep(0.5)
                
    def _find_element_by_image(self, image_path: str) -> Optional[Locator]:
        """通过图像识别定位元素
        
        Args:
            image_path: 图像路径
            
        Returns:
            元素对象
        """
        # 获取页面截图
        screenshot = self.page.screenshot()
        screenshot_path = self.screenshot_dir / "temp_screenshot.png"
        with open(screenshot_path, "wb") as f:
            f.write(screenshot)
            
        # 读取模板图像
        template = cv2.imread(image_path)
        if template is None:
            return None
            
        # 读取页面截图
        screenshot_img = cv2.imread(str(screenshot_path))
        
        # 模板匹配
        result = cv2.matchTemplate(screenshot_img, template, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(result)
        
        if max_val > 0.8:  # 匹配度阈值
            # 计算元素中心点
            h, w = template.shape[:2]
            center_x = max_loc[0] + w // 2
            center_y = max_loc[1] + h // 2
            
            # 转换为页面坐标
            element = self.page.evaluate(f"""
                () => {{
                    const element = document.elementFromPoint({center_x}, {center_y});
                    return element;
                }}
            """)
            
            if element:
                return Locator(self.page, element)
                
        return None
        
    def click(self, selector: str, timeout: int = 30000) -> bool:
        """智能点击元素
        
        Args:
            selector: 元素选择器
            timeout: 超时时间(ms)
            
        Returns:
            是否点击成功
        """
        self.logger.info(f"点击元素: {selector}")
        element = self.find_element(selector, timeout)
        if element:
            try:
                element.click()
                self.logger.info(f"元素点击成功: {selector}")
                return True
            except Exception as e:
                self.logger.error(f"点击元素失败: {str(e)}")
                # 尝试JavaScript点击
                self.page.evaluate(f"document.querySelector('{selector}').click()")
                return True
        return False
        
    def input_text(self, selector: str, text: str, timeout: int = 30000) -> bool:
        """智能输入文本
        
        Args:
            selector: 元素选择器
            text: 要输入的文本
            timeout: 超时时间(ms)
            
        Returns:
            是否输入成功
        """
        self.logger.info(f"输入文本到元素: {selector}, 文本: {text}")
        element = self.find_element(selector, timeout)
        if element:
            try:
                element.fill(text)
                self.logger.info(f"文本输入成功: {selector}")
                return True
            except Exception as e:
                self.logger.error(f"输入文本失败: {str(e)}")
                # 尝试JavaScript输入
                self.page.evaluate(f"""
                    (text) => {{
                        const element = document.querySelector('{selector}');
                        element.value = text;
                        element.dispatchEvent(new Event('input'));
                    }}
                """, text)
                return True
        return False
        
    def get_text(self, selector: str, timeout: int = 30000) -> Optional[str]:
        """获取元素文本
        
        Args:
            selector: 元素选择器
            timeout: 超时时间(ms)
            
        Returns:
            元素文本
        """
        element = self.find_element(selector, timeout)
        if element:
            return element.text_content()
        return None
        
    def verify_text(self, selector: str, expected_text: str, timeout: int = 30000) -> bool:
        """验证元素文本
        
        Args:
            selector: 元素选择器
            expected_text: 期望的文本
            timeout: 超时时间(ms)
            
        Returns:
            是否验证通过
        """
        self.logger.info(f"验证元素文本: {selector}, 期望文本: {expected_text}")
        actual_text = self.get_text(selector, timeout)
        if actual_text:
            self.logger.info(f"实际文本: {actual_text}")
            assert expected_text in actual_text, f"文本验证失败: 期望 '{expected_text}', 实际 '{actual_text}'"
            self.logger.info("文本验证成功")
            return True
        self.logger.error("获取文本失败")
        return False
        
    def wait_for_load_state(self, state: str, timeout: int = 30000):
        """等待页面加载状态
        
        Args:
            state: 加载状态
            timeout: 超时时间(ms)
        """
        self.logger.info(f"等待页面加载状态: {state}")
        self.page.wait_for_load_state(state, timeout=timeout) 