from decimal import Decimal
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from ninja import Schema, ModelSchema
from pydantic import Field, field_validator

from .models import (
    GridStrategy, GridPlan, GridLevel, GridOrder, 
    GridTradePair, GridPerformanceSnapshot, GridTemplate, GridSimulation
)


# 基础Schema
class GridStrategySchema(ModelSchema):
    """网格策略Schema"""
    
    class Config:
        model = GridStrategy
        model_fields = '__all__'


class GridStrategyCreateSchema(Schema):
    """网格策略创建Schema"""
    name: str = Field(..., description="策略名称")
    description: Optional[str] = Field(None, description="策略描述")
    version: str = Field(default="1.0", description="策略版本")
    grid_interval_percent: Decimal = Field(..., description="网格间距百分比", gt=0)
    
    # 留利润策略参数 (2.1)
    keep_profit: bool = Field(default=False, description="启用留利润策略")
    profit_keep_ratio: Decimal = Field(default=Decimal("100.00"), description="利润保留比例")
    
    # 逐格加码策略参数 (2.2)
    progressive_investment: bool = Field(default=False, description="启用逐格加码")
    investment_increase_percent: Decimal = Field(default=Decimal("5.00"), description="加码百分比")
    start_increase_from_grid: int = Field(default=2, description="从第几格开始加码", ge=1)
    
    # 一网打尽策略参数 (2.3)
    multi_grid: bool = Field(default=False, description="启用多重网格")
    small_grid_percent: Decimal = Field(default=Decimal("5.00"), description="小网格间距")
    medium_grid_percent: Decimal = Field(default=Decimal("15.00"), description="中网格间距")
    large_grid_percent: Decimal = Field(default=Decimal("30.00"), description="大网格间距")
    
    # 资金分配比例
    small_grid_ratio: Decimal = Field(default=Decimal("50.00"), description="小网格资金比例")
    medium_grid_ratio: Decimal = Field(default=Decimal("30.00"), description="中网格资金比例")
    large_grid_ratio: Decimal = Field(default=Decimal("20.00"), description="大网格资金比例")

    @field_validator('small_grid_ratio', 'medium_grid_ratio', 'large_grid_ratio')
    @classmethod
    def validate_strategy(cls, v, info):
        """验证策略参数"""
        # 验证多重网格资金分配比例
        if hasattr(info, 'data') and info.data.get('multi_grid', False):
            total_ratio = (
                info.data.get('small_grid_ratio', 0) + 
                info.data.get('medium_grid_ratio', 0) + 
                info.data.get('large_grid_ratio', 0)
            )
            if abs(total_ratio - 100) > 0.01:
                raise ValueError("多重网格资金分配比例总和必须为100%")
        
        return v


class StockSimpleSchema(Schema):
    """股票简单Schema"""
    id: int
    symbol: str
    name: str
    exchange: str


class GridLevelSchema(ModelSchema):
    """网格等级Schema"""
    
    class Config:
        model = GridLevel
        model_fields = '__all__'


class GridOrderSchema(ModelSchema):
    """网格订单Schema"""
    grid_level_info: Optional[GridLevelSchema] = None
    
    class Config:
        model = GridOrder
        model_fields = '__all__'


class GridTradePairSchema(ModelSchema):
    """网格交易对Schema"""
    buy_order_info: Optional[GridOrderSchema] = None
    sell_order_info: Optional[GridOrderSchema] = None
    
    class Config:
        model = GridTradePair
        model_fields = '__all__'


class GridPlanSchema(ModelSchema):
    """网格计划Schema"""
    strategy_info: Optional[GridStrategySchema] = None
    stock_info: Optional[StockSimpleSchema] = None
    active_orders_count: Optional[int] = None
    completed_trades_count: Optional[int] = None
    current_roi: Optional[float] = None
    
    class Config:
        model = GridPlan
        model_fields = '__all__'


class GridPlanCreateSchema(Schema):
    """网格计划创建Schema"""
    # 基本信息
    plan_name: str = Field(..., description="计划名称")
    description: Optional[str] = Field(None, description="计划描述")
    stock: int = Field(..., description="交易标的ID")
    
    # 网格参数
    base_price: Decimal = Field(..., description="基准价格", gt=0)
    min_price: Decimal = Field(..., description="最低价格", gt=0)
    max_price: Decimal = Field(..., description="最高价格", gt=0)
    max_drawdown_percent: Decimal = Field(default=Decimal("50.00"), description="最大下跌比例")
    
    # 资金参数
    base_investment: Decimal = Field(..., description="基础投资金额", gt=0)
    max_investment: Decimal = Field(..., description="最大投资金额", gt=0)
    
    # 策略数据
    strategy_data: Dict[str, Any] = Field(..., description="策略配置数据")

    @field_validator('min_price')
    @classmethod
    def validate_min_price(cls, v, info):
        if hasattr(info, 'data') and 'base_price' in info.data and v >= info.data['base_price']:
            raise ValueError("最低价格必须小于基准价格")
        return v

    @field_validator('max_price')
    @classmethod
    def validate_max_price(cls, v, info):
        if hasattr(info, 'data') and 'base_price' in info.data and v <= info.data['base_price']:
            raise ValueError("最高价格必须大于基准价格")
        return v

    @field_validator('max_investment')
    @classmethod
    def validate_max_investment(cls, v, info):
        if hasattr(info, 'data') and 'base_investment' in info.data and v < info.data['base_investment']:
            raise ValueError("最大投资金额不能小于基础投资金额")
        return v

    @field_validator('strategy_data')
    @classmethod
    def validate_strategy_data(cls, v):
        if not v:
            raise ValueError("必须提供策略配置数据")
        
        grid_interval = v.get('grid_interval_percent')
        if not grid_interval or grid_interval <= 0:
            raise ValueError("网格间距必须大于0")
        
        return v


class GridPerformanceSnapshotSchema(ModelSchema):
    """网格性能快照Schema"""
    grid_plan_info: Optional[Dict[str, Any]] = None
    
    class Config:
        model = GridPerformanceSnapshot
        model_fields = '__all__'


# 请求/响应Schema
class TriggerLevelsRequest(Schema):
    """触发网格等级请求"""
    current_price: Decimal = Field(..., description="当前价格", gt=0)


class TriggerLevelsResponse(Schema):
    """触发网格等级响应"""
    triggered_count: int
    orders: List[GridOrderSchema]


class OrderFillRequest(Schema):
    """订单成交请求"""
    filled_price: Decimal = Field(..., description="成交价格", gt=0)
    filled_quantity: Decimal = Field(..., description="成交数量", gt=0)


class OrderFillResponse(Schema):
    """订单成交响应"""
    message: str
    order: GridOrderSchema
    additional_info: Dict[str, Any]


class PerformanceRequest(Schema):
    """性能查询请求"""
    current_price: Decimal = Field(..., description="当前价格", gt=0)


class PerformanceResponse(Schema):
    """性能响应"""
    realized_profit: Decimal
    unrealized_pnl: Decimal
    total_profit: Decimal
    total_position: Decimal
    total_cost: Decimal
    current_value: Decimal
    kept_profit_shares: Decimal
    kept_profit_value: Decimal
    completed_trades: int
    total_invested: Decimal
    available_funds: Decimal
    fund_utilization: float


class SuggestionsResponse(Schema):
    """交易建议响应"""
    buy_suggestions: List[Dict[str, Any]]
    sell_suggestions: List[Dict[str, Any]]
    alerts: List[Dict[str, Any]]


class PressureTestResponse(Schema):
    """压力测试响应"""
    stress_price: Decimal
    total_investment_needed: Decimal
    available_funds: Decimal
    is_feasible: bool
    fund_utilization_rate: Decimal
    buy_levels_count: int
    buy_levels: List[Dict[str, Any]]


class OptimizationResponse(Schema):
    """优化建议响应"""
    suggestions: List[Dict[str, Any]]


class DashboardResponse(Schema):
    """仪表板响应"""
    summary: Dict[str, Any]
    recent_trades: List[GridTradePairSchema]
    best_plans: List[GridPlanSchema]
    active_plans: List[GridPlanSchema]


class BacktestRequest(Schema):
    """回测请求"""
    strategy: Dict[str, Any] = Field(..., description="策略参数")
    price_data: List[Dict[str, Any]] = Field(..., description="历史价格数据")
    initial_capital: Decimal = Field(default=Decimal("10000.00"), description="初始资金")

    @field_validator('price_data')
    @classmethod
    def validate_price_data(cls, v):
        if not v:
            raise ValueError("价格数据不能为空")
        
        for item in v:
            if 'price' not in item:
                raise ValueError("价格数据必须包含'price'字段")
            
            try:
                float(item['price'])
            except (ValueError, TypeError):
                raise ValueError("价格必须是有效的数字")
        
        return v

    @field_validator('strategy')
    @classmethod
    def validate_strategy(cls, v):
        required_fields = ['grid_interval_percent', 'base_investment']
        
        for field in required_fields:
            if field not in v:
                raise ValueError(f"策略参数缺少必需字段: {field}")
        
        # 验证网格间距
        grid_interval = v.get('grid_interval_percent')
        try:
            if float(grid_interval) <= 0:
                raise ValueError("网格间距必须大于0")
        except (ValueError, TypeError):
            raise ValueError("网格间距必须是有效的数字")
        
        # 验证基础投资金额
        base_investment = v.get('base_investment')
        try:
            if float(base_investment) <= 0:
                raise ValueError("基础投资金额必须大于0")
        except (ValueError, TypeError):
            raise ValueError("基础投资金额必须是有效的数字")
        
        return v


class BacktestResponse(Schema):
    """回测响应"""
    initial_capital: Decimal
    final_capital: Decimal
    total_profit: Decimal
    total_trades: int
    win_rate: float
    max_drawdown: float
    trades: List[Dict[str, Any]]
    error: Optional[str] = None


class StrategyPerformanceResponse(Schema):
    """策略性能响应"""
    strategy: GridStrategySchema
    total_plans: int
    successful_plans: int
    success_rate: float
    total_profit: Decimal
    average_profit_per_plan: Decimal
    total_trades: int
    average_trades_per_plan: float


class CompareStrategiesRequest(Schema):
    """策略比较请求"""
    strategy_ids: List[int] = Field(..., description="策略ID列表")
    days: int = Field(default=30, description="分析天数")


class MessageResponse(Schema):
    """消息响应"""
    message: str


class ErrorResponse(Schema):
    """错误响应"""
    error: str


# ==================== 网格模板相关 Schema ====================

class GridTemplateSchema(ModelSchema):
    """网格模板Schema"""
    
    class Config:
        model = GridTemplate
        model_fields = '__all__'


class GridTemplateCreateSchema(Schema):
    """网格模板创建Schema"""
    name: str = Field(..., description="模板名称")
    description: Optional[str] = Field(None, description="模板描述")
    template_data: Dict[str, Any] = Field(..., description="模板数据")
    category: str = Field(default="custom", description="模板分类")
    is_public: bool = Field(default=False, description="是否公开")


class GridTemplateImportRequest(Schema):
    """模板导入请求"""
    template_file: str = Field(..., description="模板文件内容(JSON字符串)")
    apply_to_plan_id: Optional[int] = Field(None, description="应用到指定计划")


# ==================== 网格配置预览相关 Schema ====================

class GridConfigPreviewRequest(Schema):
    """网格配置预览请求"""
    base_price: Decimal = Field(..., description="基准价格", gt=0)
    min_price: Decimal = Field(..., description="最低价格", gt=0) 
    max_price: Decimal = Field(..., description="最高价格", gt=0)
    grid_interval_percent: Decimal = Field(..., description="网格间距", gt=0)
    base_investment: Decimal = Field(..., description="基础投资金额", gt=0)
    max_investment: Decimal = Field(..., description="最大投资金额", gt=0)
    strategy_config: Dict[str, Any] = Field(default_factory=dict, description="策略配置")

    @field_validator('min_price')
    @classmethod
    def validate_min_price(cls, v, info):
        if hasattr(info, 'data') and 'base_price' in info.data and v >= info.data['base_price']:
            raise ValueError("最低价格必须小于基准价格")
        return v

    @field_validator('max_price')
    @classmethod
    def validate_max_price(cls, v, info):
        if hasattr(info, 'data') and 'base_price' in info.data and v <= info.data['base_price']:
            raise ValueError("最高价格必须大于基准价格")
        return v


class GridLevelPreviewSchema(Schema):
    """网格等级预览Schema"""
    price: Decimal
    investment_amount: Decimal
    level_index: int
    distance_from_base: float
    sell_price: Optional[Decimal] = None
    grid_type: str = "single"


class GridConfigPreviewResponse(Schema):
    """网格配置预览响应"""
    levels: List[GridLevelPreviewSchema]
    total_levels: int
    buy_levels: List[GridLevelPreviewSchema]
    sell_levels: List[GridLevelPreviewSchema]
    investment_distribution: Dict[str, Any]
    risk_analysis: Dict[str, Any]
    visual_data: Dict[str, Any]


class GridConfigValidationResponse(Schema):
    """网格配置验证响应"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    score: float


# ==================== 网格模拟相关 Schema ====================

class GridSimulationRequest(Schema):
    """网格模拟请求"""
    config_data: Dict[str, Any] = Field(..., description="网格配置")
    simulation_days: int = Field(default=30, description="模拟天数", ge=1, le=365)
    price_volatility: Decimal = Field(default=Decimal("15.0"), description="价格波动率(%)", ge=0, le=100)
    trend_direction: str = Field(default="neutral", description="趋势方向: up/down/neutral")
    trend_strength: Decimal = Field(default=Decimal("0.0"), description="趋势强度(%)", ge=-50, le=50)

    @field_validator('trend_direction')
    @classmethod
    def validate_trend_direction(cls, v):
        if v not in ['up', 'down', 'neutral']:
            raise ValueError("趋势方向必须是: up/down/neutral")
        return v


class SimulationTradeSchema(Schema):
    """模拟交易Schema"""
    date: str
    type: str  # buy/sell
    price: Decimal
    quantity: Decimal
    amount: Decimal
    profit: Optional[Decimal] = None
    level: int


class GridSimulationResponse(Schema):
    """网格模拟响应"""
    simulation_id: str
    config_summary: Dict[str, Any]
    simulation_results: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    trade_history: List[SimulationTradeSchema]
    price_chart_data: List[Dict[str, Any]]
    recommendations: List[str]
    status: str


class GridSimulationListResponse(Schema):
    """模拟列表响应"""
    simulation_id: str
    config_summary: Dict[str, Any]
    performance_summary: Dict[str, Any]
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None


# ==================== 模板应用相关 Schema ====================

class ApplyTemplateRequest(Schema):
    """应用模板请求"""
    template_id: int = Field(..., description="模板ID")
    override_params: Optional[Dict[str, Any]] = Field(None, description="覆盖参数")


class TemplateExportResponse(Schema):
    """模板导出响应"""
    template_info: Dict[str, Any]
    config_data: Dict[str, Any]
    export_metadata: Dict[str, Any] 