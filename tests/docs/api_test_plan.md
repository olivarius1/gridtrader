# API测试和验证计划

## 测试目标

1. **创建测试用户和数据**
2. **验证核心API功能**
3. **测试网格策略计算逻辑**

## 测试环境准备

- 开发服务器: http://localhost:8000
- API文档: http://localhost:8000/api/docs
- 数据库: PostgreSQL (所有迁移已完成)

## 测试分阶段执行

### 阶段1: 用户账户模块测试 (accounts)

**测试用例**:
1. 创建测试用户
2. 验证用户认证功能
3. 测试资金账户管理
4. 验证佣金费率设置

**API端点**:
- POST `/api/accounts/users/` - 创建用户
- POST `/api/accounts/auth/login/` - 用户登录
- GET `/api/accounts/profile/` - 获取用户信息
- PUT `/api/accounts/profile/` - 更新用户信息
- POST `/api/accounts/commission/` - 设置佣金方案

### 阶段2: 股票标的模块测试 (stocks)

**测试用例**:
1. 添加测试股票数据
2. 验证价格数据管理
3. 测试自选股功能

**API端点**:
- POST `/api/stocks/` - 添加股票
- GET `/api/stocks/` - 获取股票列表
- POST `/api/stocks/prices/` - 添加价格数据
- GET `/api/stocks/{id}/prices/` - 获取历史价格
- POST `/api/stocks/watchlist/` - 添加自选股

### 阶段3: 网格策略核心测试 (grid)

**测试用例**:
1. 创建网格策略配置
2. 生成网格交易计划
3. 测试网格等级计算
4. 验证配置预览功能
5. 测试策略模拟

**API端点**:
- POST `/api/grid/strategies/` - 创建策略
- POST `/api/grid/plans/` - 创建交易计划
- GET `/api/grid/plans/{id}/preview/` - 配置预览
- POST `/api/grid/plans/{id}/simulate/` - 策略模拟
- GET `/api/grid/dashboard/` - 仪表板数据

### 阶段4: 交易执行模块测试 (trading)

**测试用例**:
1. 创建交易记录
2. 验证费用计算
3. 测试持仓管理

**API端点**:
- POST `/api/trading/records/` - 创建交易记录
- GET `/api/trading/positions/` - 获取持仓信息
- GET `/api/trading/records/` - 获取交易历史

### 阶段5: 数据分析模块测试 (analytics)

**测试用例**:
1. 生成盈亏统计
2. 验证绩效指标计算
3. 测试数据聚合功能

**API端点**:
- GET `/api/analytics/profit-loss/` - 盈亏统计
- GET `/api/analytics/performance/` - 绩效分析
- GET `/api/analytics/balance/` - 资产变化

## 测试数据准备

### 测试用户数据
```json
{
  "username": "test_trader",
  "email": "test@example.com",
  "password": "TestPass123",
  "total_assets": 100000.00,
  "available_funds": 50000.00
}
```

### 测试股票数据
```json
[
  {
    "code": "000001",
    "name": "平安银行",
    "market": "SZ",
    "stock_type": "stock"
  },
  {
    "code": "000002", 
    "name": "万科A",
    "market": "SZ",
    "stock_type": "stock"
  }
]
```

### 测试网格策略数据
```json
{
  "version": "2.1",
  "grid_interval_percent": 2.0,
  "stop_loss_percent": 10.0,
  "take_profit_percent": 20.0,
  "max_position_percent": 30.0
}
```

## 测试脚本

- `test_accounts.py` - 账户模块测试
- `test_stocks.py` - 股票模块测试
- `test_grid.py` - 网格策略测试
- `test_trading.py` - 交易模块测试
- `test_analytics.py` - 分析模块测试
- `test_integration.py` - 集成测试

## 预期结果

1. 所有API端点正常响应
2. 数据创建和查询功能正确
3. 网格策略计算逻辑准确
4. 费用计算准确无误
5. 数据统计结果正确

## 测试工具

- **requests**: Python HTTP库
- **pytest**: 测试框架
- **Django TestCase**: Django内置测试工具
- **Postman**: API手动测试工具

## 错误处理验证

1. 无效输入数据处理
2. 权限验证
3. 数据约束检查
4. 异常情况处理

## 性能测试

1. 并发用户测试
2. 大数据量处理
3. 响应时间测试
4. 数据库查询优化验证 