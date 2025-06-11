# 一个处理网格交易的后端

技术: python3.12
web框架: django==5.2.2
其他包:django-ninja==1.4.3
数据库: postgreSQL


# 业务逻辑
## 场景
投资人(用户)想要投资某个股票/ETF标的, 通过网格交易的形式获取利润.
示例品种: 沪深300 代码 SZ.510300
以下是用户的交易记录:
交易标的 成交日期 成交时间 成交价格 成交数量 交易类型 成交金额 佣金 过户费 印花税 备注 
SZ.510300 20250101 09:31 1.0  10000 b 10000.00 1.0  0.00 0.00 建仓 
SZ.510300 20250201 09:58 1.1  8000 s 8800.00 0.88 0.00 0.00 盈利卖出一部分


数据结构:
股票表
交易记录表
佣金方案表
...

同时还需要记录用户的盈亏, 按日/月/季度/年 自定义周期 统计用户收益和亏损.
还需要记录用户在每个品种上的盈亏.
用户在单个品种(股票)的交易, 可以制定交易计划(网格计划).

# 需求表:
1.1 网格交易计划管理
 基础的网格计划创建和管理
需完善:
添加更直观的网格可视化配置界面
支持导入/导出网格配置模板
添加网格计划模拟功能
1.2 交易记录和配对管理
完整的订单和交易对数据模型
需完善:
自动交易配对逻辑优化
交易记录的批量导入功能
手动调整交易配对的界面
1.3 收益分析系统
已完成: 基础的盈亏计算逻辑
需新增:
实时收益监控面板: 显示当前每笔交易的盈亏状态
品种收益分析: 按股票品种统计盈亏情况
风险分析模块:
距离第一网的下跌幅度计算
距离压力测试位置的预警
最大回撤分析
收益趋势图表: 日/周/月/季度/年度收益趋势
网格效率分析: 每个网格的成交频率和收益贡献
2. 数据管理和自动化

2.1 价格数据获取和缓存
akshare集成，StockPrice模型定义

需实现:
自动价格更新服务: 定时从akshare获取最新价格
CSV缓存管理: 本地CSV文件的自动管理和更新
历史数据补全: 自动填补缺失的历史价格数据
2.2 智能提醒系统
🆕 需新增:
价格触发提醒: 当价格触及网格买卖点时推送通知
风险预警: 接近压力测试位置时的警报
收益里程碑: 达到收益目标时的通知
多渠道通知: 邮件、短信、Web推送

## 模块状态

### ✅ accounts - 用户账户模块
- ✅ 用户注册、登录、登出
- ✅ 用户信息管理
- ✅ 资金管理 (充值、提现、冻结、解冻)
- ✅ 佣金方案管理
- ✅ 费用计算功能
- ✅ Pydantic V2兼容性
- 🔄 扩展性支持 (邮箱验证、双因子认证等预留)

### ✅ grid - 网格交易核心模块
- ✅ 网格策略管理
- ✅ 网格计划配置和预览
- ✅ 网格模拟和回测
- ✅ 模板管理和导入导出
- ✅ 完整的服务层和API

### 🔄 stocks - 股票数据模块
- 基础模型已实现
- 需要集成akshare数据获取

### 🔄 trading - 交易执行模块
- 基础模型已实现
- 需要与grid模块深度集成

### 🔄 analytics - 数据分析模块
- 基础模型已实现
- 需要实现完整的分析服务

## API接口

### 用户账户API
```
POST   /api/accounts/auth/register              # 用户注册
POST   /api/accounts/auth/login                 # 用户登录
POST   /api/accounts/user/logout                # 用户登出
GET    /api/accounts/user/profile               # 获取用户信息
PUT    /api/accounts/user/profile               # 更新用户信息
GET    /api/accounts/user/balance               # 获取资金信息
POST   /api/accounts/user/balance/update        # 更新资金
GET    /api/accounts/user/commission-plans    # 获取佣金方案
POST   /api/accounts/user/commission-plans    # 创建佣金方案
POST   /api/accounts/user/calculate-fees        # 计算交易费用
```

### 网格交易API
```
GET    /api/grid/strategies                     # 获取策略列表
POST   /api/grid/strategies                     # 创建策略
GET    /api/grid/plans                          # 获取计划列表
POST   /api/grid/plans                          # 创建计划
POST   /api/grid/config/preview                 # 预览配置
POST   /api/grid/config/validate                # 验证配置
GET    /api/grid/templates                      # 获取模板列表
POST   /api/grid/simulations                    # 运行模拟
```

## 测试

### 账户模块测试
```bash
# 运行账户模块API测试
python accounts/test_accounts_api.py
```

### 项目整体测试
项目采用分层测试结构，所有测试文件已组织到 `tests/` 目录下：

#### 测试目录结构
```
tests/
├── api/                    # API接口测试
├── integration/            # 集成测试
├── data/                   # 测试数据生成
├── results/                # 测试结果存储
├── docs/                   # 测试文档
└── README.md              # 测试说明
```

#### 快速运行测试
```bash
# 交互式菜单
python run_tests.py

# 命令行参数
python run_tests.py --all          # 运行所有测试
python run_tests.py --api-basic    # API基础测试
python run_tests.py --db-simple    # 数据库测试
python run_tests.py --create-data  # 生成测试数据
```

#### 手动运行特定测试
```bash
# 生成测试数据
python tests/data/create_test_data.py

# API基础测试
python tests/api/test_api_basic.py

# 数据库功能测试
python tests/integration/test_db_simple.py
```

更多测试信息请查看 `tests/README.md`。