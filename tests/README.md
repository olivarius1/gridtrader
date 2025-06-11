# 测试目录结构

本目录包含网格交易后端系统的所有测试文件。

## 目录结构

```
tests/
├── api/                    # API接口测试
│   ├── test_api_basic.py      # 基础API连通性测试
│   └── test_api_complete.py   # 完整API功能测试
├── integration/            # 集成测试
│   ├── test_db_simple.py      # 简单数据库功能测试
│   └── test_database_functions.py  # 完整数据库功能测试
├── data/                   # 测试数据
│   └── create_test_data.py    # 测试数据生成脚本
├── results/                # 测试结果
│   └── *.json                 # 测试结果文件
├── docs/                   # 测试文档
│   ├── api_test_plan.md       # API测试计划
│   └── API_TEST_REPORT.md     # API测试报告
└── README.md              # 本文件
```

## 测试类型说明

### API测试 (`api/`)
- **test_api_basic.py**: 测试API基础连通性、文档访问等
- **test_api_complete.py**: 测试完整的API功能，包括认证、CRUD操作等

### 集成测试 (`integration/`)
- **test_db_simple.py**: 简化版数据库功能测试，绕过认证直接测试业务逻辑
- **test_database_functions.py**: 完整的数据库层面功能测试

### 测试数据 (`data/`)
- **create_test_data.py**: 生成测试用的用户、股票、网格策略等数据

### 测试结果 (`results/`)
- 存储各次测试运行的JSON结果文件

### 测试文档 (`docs/`)
- **api_test_plan.md**: 详细的API测试计划和策略
- **API_TEST_REPORT.md**: 测试执行报告和分析

## 运行测试

从项目根目录运行：

```bash
# 运行API基础测试
python tests/api/test_api_basic.py

# 运行完整API测试
python tests/api/test_api_complete.py

# 运行数据库集成测试
python tests/integration/test_db_simple.py

# 生成测试数据
python tests/data/create_test_data.py
```

## 注意事项

1. 在运行测试前，确保Django开发服务器已启动
2. 某些测试需要数据库权限和测试数据
3. API测试目前存在认证问题（401错误），需要先解决认证机制
4. 测试结果文件会自动生成时间戳 