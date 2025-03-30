# 智能分层测试框架

## 1. 项目概述

这是一个基于Python的智能分层测试框架，支持UI测试和API测试，具有以下特点：
- 分层架构设计
- 支持UI和API测试
- 智能会话管理
- 自动化报告生成
- 灵活的数据驱动

## 2. 目录结构

```
项目根目录/
├── src/                          # 源代码目录
│   └── test_framework/          # 测试框架核心代码
│       ├── api/                 # API测试相关
│       │   └── client.py       # API客户端实现
│       ├── data/               # 数据管理
│       │   ├── __init__.py
│       │   └── parser.py      # 数据解析器
│       ├── engine/            # 执行引擎
│       │   └── runner.py     # 测试执行器
│       ├── report/           # 报告生成
│       │   ├── __init__.py
│       │   ├── generator.py  # 报告生成器
│       │   └── templates/    # 报告模板
│       ├── session/         # 会话管理
│       │   ├── __init__.py
│       │   └── manager.py  # 会话管理器
│       ├── step_engine/    # 步骤引擎
│       │   └── engine.py  # 步骤执行引擎
│       ├── ui/           # UI测试相关
│       │   └── page_object.py  # 页面对象基类
│       └── utils/       # 工具类
│           └── logger.py  # 日志工具
├── tests/              # 测试用例目录
│   ├── conftest.py    # Pytest配置文件
│   └── test_bilibili_login.py  # B站登录测试用例
├── test_data/        # 测试数据目录
│   └── bilibili_login.yaml  # B站登录测试数据
├── reports/         # 报告目录
│   ├── results/    # 测试结果
│   ├── allure-results/  # Allure报告
│   └── html/      # HTML报告
├── setup.py       # 安装配置
├── requirements.txt  # 依赖管理
└── pyproject.toml   # 项目配置
```

## 3. 核心模块说明

### 3.1 数据层 (Data Layer)
- **DataParser**: 负责解析YAML格式的测试数据
- 支持动态数据生成和参数化测试

### 3.2 步骤引擎层 (Step Engine Layer)
- **StepEngine**: 负责解析和执行测试步骤
- 支持UI和API两种类型的步骤
- 提供步骤执行状态追踪

### 3.3 UI技术实现层 (UI Layer)
- **BasePage**: 页面对象基类
- 封装了常用的UI操作
- 支持智能元素定位

### 3.4 API技术实现层 (API Layer)
- **APIClient**: API客户端实现
- 支持多种HTTP方法
- 提供响应验证功能

### 3.5 会话管理层 (Session Layer)
- **SessionManager**: 管理UI和API会话
- 支持会话的保存和恢复
- 实现登录状态的持久化

### 3.6 执行引擎层 (Engine Layer)
- **TestRunner**: 测试执行引擎
- 负责测试用例的执行流程
- 提供测试环境的管理

### 3.7 报告层 (Report Layer)
- **ReportGenerator**: 报告生成器
- 支持Allure和HTML两种报告格式
- 提供详细的测试结果分析

## 4. 使用示例

### 4.1 测试数据示例
```yaml
- name: "B站登录成功测试"
  description: "使用正确的用户名和密码登录B站"
  session: "bilibili_session"
  steps:
    - name: "打开B站首页"
      type: "ui"
      action: "navigate"
      params:
        url: "https://www.bilibili.com"
    # ... 更多步骤
```

### 4.2 测试用例示例
```python
def test_bilibili_login(test_data, runner):
    """测试B站登录"""
    logger.info("开始测试B站登录")
    result = runner.run_test(test_data)
    assert result["status"] == "passed"
```

## 5. 运行测试

```bash
# 安装依赖
pip install -r requirements.txt

# 运行测试
pytest tests/test_bilibili_login.py -v

# 生成报告
allure serve reports/allure-results
```

## 6. 主要特性

1. **分层架构**
   - 清晰的模块划分
   - 高内聚低耦合
   - 易于扩展和维护

2. **智能会话管理**
   - 自动保存和恢复会话
   - 支持多会话并行
   - 会话状态持久化

3. **自动化报告**
   - 支持多种报告格式
   - 详细的测试步骤记录
   - 美观的报告展示

4. **灵活的数据驱动**
   - YAML格式测试数据
   - 支持参数化测试
   - 动态数据生成

5. **完善的日志系统**
   - 分级日志记录
   - 详细的执行追踪
   - 便于问题定位

## 7. 注意事项

1. 确保已安装所有依赖包
2. 测试数据文件需要符合YAML格式
3. 运行UI测试前需要安装Playwright浏览器
4. 报告生成需要安装Allure命令行工具

## 8. 后续优化方向

1. 添加更多UI操作封装
2. 支持更多API测试特性
3. 优化报告展示效果
4. 添加测试用例管理功能
5. 支持分布式测试执行 