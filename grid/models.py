"""
grid.models
~~~~~~~~~

网格交易核心模块

该模块包含网格交易系统的核心模型：

核心交易模型：
- GridStrategy: 网格策略配置（支持1.0-2.3版本）
- GridPlan: 网格交易计划
- GridLevel: 网格价格等级
- GridOrder: 网格订单
- GridTradePair: 网格交易对
- GridPerformanceSnapshot: 网格性能快照

辅助管理模型：
- GridTemplate: 网格配置模板
- GridSimulation: 网格策略模拟

支持的策略版本：
- 1.0: 基础网格策略
- 2.0: 进阶网格策略
- 2.1: 留利润策略
- 2.2: 逐格加码策略
- 2.3: 一网打尽策略（多重网格）

主要功能：
1. 多版本网格策略支持
2. 灵活的网格配置
3. 自动网格等级计算
4. 交易对管理和盈利计算
5. 性能快照和分析
6. 模板保存和共享
7. 策略模拟和回测

网格类型支持：
- single: 单一网格
- small: 小网格（多重网格模式）
- medium: 中网格（多重网格模式）
- large: 大网格（多重网格模式）

作者: Grid Trading System
创建时间: 2024
"""

from decimal import Decimal
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


class GridStrategy(models.Model):
    """网格策略模型 - 支持1.0, 2.0, 2.x版本"""
    
    name = models.CharField(max_length=100, verbose_name="策略名称")
    description = models.TextField(max_length=500, blank=True, null=True, verbose_name="策略描述")
    
    STRATEGY_VERSION_CHOICES = [
        ("1.0", "基础网格1.0"),
        ("2.0", "进阶网格2.0"),
        ("2.1", "留利润策略"),
        ("2.2", "逐格加码策略"),
        ("2.3", "一网打尽策略"),
    ]
    version = models.CharField(
        max_length=10, 
        choices=STRATEGY_VERSION_CHOICES, 
        default="1.0", 
        verbose_name="策略版本"
    )
    
    # 网格基本参数
    grid_interval_percent = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=Decimal("5.0000"),
        verbose_name="网格间距百分比",
        help_text="如5%填5.0000"
    )
    
    # 留利润策略参数 (2.1)
    keep_profit = models.BooleanField(default=False, verbose_name="启用留利润策略")
    profit_keep_ratio = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=Decimal("100.00"),
        verbose_name="利润保留比例",
        help_text="保留利润的百分比，100表示全部保留"
    )
    
    # 逐格加码策略参数 (2.2)
    progressive_investment = models.BooleanField(default=False, verbose_name="启用逐格加码")
    investment_increase_percent = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=Decimal("5.00"),
        verbose_name="加码百分比",
        help_text="每格投入增加的百分比"
    )
    start_increase_from_grid = models.IntegerField(
        default=2, 
        verbose_name="从第几格开始加码",
        validators=[MinValueValidator(1)]
    )
    
    # 一网打尽策略参数 (2.3)
    multi_grid = models.BooleanField(default=False, verbose_name="启用多重网格")
    small_grid_percent = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=Decimal("5.00"),
        verbose_name="小网格间距"
    )
    medium_grid_percent = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=Decimal("15.00"),
        verbose_name="中网格间距"
    )
    large_grid_percent = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=Decimal("30.00"),
        verbose_name="大网格间距"
    )
    
    # 资金分配比例 (多重网格)
    small_grid_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal("50.00"),
        verbose_name="小网格资金比例"
    )
    medium_grid_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal("30.00"),
        verbose_name="中网格资金比例"
    )
    large_grid_ratio = models.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        default=Decimal("20.00"),
        verbose_name="大网格资金比例"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = "grid_strategies"
        verbose_name = "网格策略"
        verbose_name_plural = "网格策略"
    
    def __str__(self):
        return f"{self.name} ({self.version})"


class GridPlan(models.Model):
    """网格计划模型"""

    user = models.ForeignKey(
        "accounts.User", 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        verbose_name="用户"
    )
    stock = models.ForeignKey(
        "stocks.Stock", 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        verbose_name="交易标的"
    )
    strategy = models.ForeignKey(
        GridStrategy, 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        verbose_name="使用策略"
    )

    # 基本信息
    plan_name = models.CharField(max_length=100, verbose_name="计划名称")
    description = models.TextField(
        max_length=500, blank=True, null=True, verbose_name="计划描述"
    )

    # 网格参数
    base_price = models.DecimalField(
        max_digits=10, decimal_places=4, 
        default=Decimal("100.0000"),
        verbose_name="基准价格"
    )

    # 价格范围 - 压力测试
    min_price = models.DecimalField(
        max_digits=10, decimal_places=4, 
        default=Decimal("50.0000"),
        verbose_name="最低价格",
        help_text="压力测试最低价格，用于风险控制"
    )
    max_price = models.DecimalField(
        max_digits=10, decimal_places=4, 
        default=Decimal("200.0000"),
        verbose_name="最高价格"
    )
    
    # 最大下跌比例 - 压力测试参数
    max_drawdown_percent = models.DecimalField(
        max_digits=8, 
        decimal_places=4, 
        default=Decimal("50.00"),
        verbose_name="最大下跌比例",
        help_text="压力测试参数，如50%下跌"
    )

    # 交易参数
    base_investment = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("1000.00"),
        verbose_name="基础投资金额"
    )
    max_investment = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("10000.00"),
        verbose_name="最大投资金额"
    )

    # 计划状态
    STATUS_CHOICES = [
        ("active", "运行中"),
        ("paused", "暂停"),
        ("stopped", "已停止"),
        ("completed", "已完成"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="active", verbose_name="状态"
    )

    # 统计信息
    total_profit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="总盈利"
    )
    realized_profit = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="已实现盈利"
    )
    kept_profit_shares = models.DecimalField(
        max_digits=15, decimal_places=4, default=Decimal("0.0000"), verbose_name="保留利润份额"
    )
    total_trades = models.IntegerField(default=0, verbose_name="总交易次数")
    buy_trades = models.IntegerField(default=0, verbose_name="买入次数")
    sell_trades = models.IntegerField(default=0, verbose_name="卖出次数")
    
    # 投入资金统计
    total_invested = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="累计投入资金"
    )
    available_funds = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="可用资金"
    )

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    started_at = models.DateTimeField(null=True, blank=True, verbose_name="启动时间")
    stopped_at = models.DateTimeField(null=True, blank=True, verbose_name="停止时间")

    class Meta:
        db_table = "grid_plans"
        verbose_name = "网格计划"
        verbose_name_plural = "网格计划"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["stock"]),
            models.Index(fields=["status"]),
            models.Index(fields=["user", "stock"]),
        ]

    def __str__(self):
        return f"{self.plan_name}-{self.stock.symbol}"

    def calculate_grid_levels(self):
        """计算网格价格等级"""
        levels = []
        
        if self.strategy.multi_grid:
            # 2.3 一网打尽策略 - 多重网格
            levels.extend(self._calculate_multi_grid_levels())
        else:
            # 单一网格策略
            levels.extend(self._calculate_single_grid_levels())
        
        return sorted(levels, key=lambda x: x['price'])
    
    def _calculate_single_grid_levels(self):
        """计算单一网格等级"""
        levels = []
        grid_percent = self.strategy.grid_interval_percent / 100
        
        # 向上计算
        current_price = self.base_price
        grid_index = 0
        while current_price <= self.max_price:
            investment_amount = self._calculate_investment_amount(grid_index)
            levels.append({
                'price': current_price,
                'investment_amount': investment_amount,
                'grid_type': 'single',
                'grid_index': grid_index
            })
            current_price *= (1 + grid_percent)
            grid_index += 1
        
        # 向下计算
        current_price = self.base_price * (1 - grid_percent)
        grid_index = -1
        while current_price >= self.min_price:
            investment_amount = self._calculate_investment_amount(abs(grid_index))
            levels.append({
                'price': current_price,
                'investment_amount': investment_amount,
                'grid_type': 'single',
                'grid_index': grid_index
            })
            current_price *= (1 - grid_percent)
            grid_index -= 1
        
        return levels
    
    def _calculate_multi_grid_levels(self):
        """计算多重网格等级 (2.3策略)"""
        levels = []
        
        # 小网格
        small_percent = self.strategy.small_grid_percent / 100
        small_investment = self.base_investment * self.strategy.small_grid_ratio / 100
        levels.extend(self._calculate_grid_for_type('small', small_percent, small_investment))
        
        # 中网格
        medium_percent = self.strategy.medium_grid_percent / 100
        medium_investment = self.base_investment * self.strategy.medium_grid_ratio / 100
        levels.extend(self._calculate_grid_for_type('medium', medium_percent, medium_investment))
        
        # 大网格
        large_percent = self.strategy.large_grid_percent / 100
        large_investment = self.base_investment * self.strategy.large_grid_ratio / 100
        levels.extend(self._calculate_grid_for_type('large', large_percent, large_investment))
        
        return levels
    
    def _calculate_grid_for_type(self, grid_type, percent, base_investment):
        """为特定类型网格计算等级"""
        levels = []
        
        # 向上计算
        current_price = self.base_price
        while current_price <= self.max_price:
            levels.append({
                'price': current_price,
                'investment_amount': base_investment,
                'grid_type': grid_type,
                'sell_price': current_price * (1 + percent)
            })
            current_price *= (1 + percent)
        
        # 向下计算
        current_price = self.base_price * (1 - percent)
        while current_price >= self.min_price:
            levels.append({
                'price': current_price,
                'investment_amount': base_investment,
                'grid_type': grid_type,
                'sell_price': self.base_price if current_price == self.base_price * (1 - percent) else current_price * (1 + percent)
            })
            current_price *= (1 - percent)
        
        return levels
    
    def _calculate_investment_amount(self, grid_index):
        """计算网格投资金额 (支持逐格加码策略)"""
        base_amount = self.base_investment
        
        if self.strategy.progressive_investment and grid_index >= self.strategy.start_increase_from_grid - 1:
            # 2.2 逐格加码策略
            increase_times = grid_index - (self.strategy.start_increase_from_grid - 1)
            increase_rate = self.strategy.investment_increase_percent / 100
            multiplier = (1 + increase_rate) ** increase_times
            return base_amount * multiplier
        
        return base_amount


class GridLevel(models.Model):
    """网格等级模型 - 预设的网格价格等级"""
    
    grid_plan = models.ForeignKey(
        GridPlan, 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        verbose_name="网格计划",
        related_name="levels"
    )
    
    # 网格信息
    price = models.DecimalField(
        max_digits=10, decimal_places=4, 
        default=Decimal("100.0000"),
        verbose_name="网格价格"
    )
    investment_amount = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("1000.00"),
        verbose_name="投资金额"
    )
    
    GRID_TYPE_CHOICES = [
        ("single", "单一网格"),
        ("small", "小网格"),
        ("medium", "中网格"),
        ("large", "大网格"),
    ]
    grid_type = models.CharField(
        max_length=10, choices=GRID_TYPE_CHOICES, verbose_name="网格类型"
    )
    
    grid_index = models.IntegerField(
        default=0,
        verbose_name="网格序号"
    )
    sell_price = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="卖出价格"
    )
    
    # 状态
    is_triggered = models.BooleanField(default=False, verbose_name="是否已触发")
    is_completed = models.BooleanField(default=False, verbose_name="是否已完成")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = "grid_levels"
        verbose_name = "网格等级"
        verbose_name_plural = "网格等级"
        unique_together = [["grid_plan", "price", "grid_type"]]
        indexes = [
            models.Index(fields=["grid_plan", "price"]),
            models.Index(fields=["grid_plan", "is_triggered"]),
        ]
    
    def __str__(self):
        return f"{self.grid_plan.plan_name}-{self.grid_type}@{self.price}"


class GridOrder(models.Model):
    """网格订单模型"""

    grid_plan = models.ForeignKey(
        GridPlan,
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name="网格计划",
        related_name="orders",
    )
    grid_level = models.ForeignKey(
        GridLevel,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="网格等级",
        related_name="orders"
    )

    # 订单信息
    price = models.DecimalField(
        max_digits=10, decimal_places=4, 
        default=Decimal("100.0000"),
        verbose_name="订单价格"
    )
    quantity = models.DecimalField(
        max_digits=15, decimal_places=4, 
        default=Decimal("100.0000"),
        verbose_name="订单数量"
    )
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="订单金额"
    )

    ORDER_TYPE_CHOICES = [
        ("buy", "买入订单"),
        ("sell", "卖出订单"),
    ]
    order_type = models.CharField(
        max_length=10, choices=ORDER_TYPE_CHOICES, verbose_name="订单类型"
    )

    # 订单状态
    STATUS_CHOICES = [
        ("pending", "待成交"),
        ("filled", "已成交"),
        ("cancelled", "已取消"),
        ("partial", "部分成交"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="pending", verbose_name="状态"
    )

    # 成交信息
    filled_quantity = models.DecimalField(
        max_digits=15, decimal_places=4, default=Decimal("0.0000"), verbose_name="已成交数量"
    )
    filled_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="已成交金额"
    )
    filled_price = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="成交价格"
    )
    
    # 利润相关 (留利润策略)
    profit_kept_quantity = models.DecimalField(
        max_digits=15, decimal_places=4, default=Decimal("0.0000"), verbose_name="保留利润数量"
    )

    # 关联交易记录
    trading_record = models.ForeignKey(
        "trading.TradingRecord",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="交易记录",
    )

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    filled_at = models.DateTimeField(null=True, blank=True, verbose_name="成交时间")

    class Meta:
        db_table = "grid_orders"
        verbose_name = "网格订单"
        verbose_name_plural = "网格订单"
        indexes = [
            models.Index(fields=["grid_plan"]),
            models.Index(fields=["status"]),
            models.Index(fields=["order_type"]),
            models.Index(fields=["price"]),
            models.Index(fields=["created_at"]),
        ]
        ordering = ["price"]

    def __str__(self):
        type_display = "买入" if self.order_type == "buy" else "卖出"
        return f"{self.grid_plan.stock.symbol}-{type_display}@{self.price}"


class GridTradePair(models.Model):
    """网格交易对模型 - 记录完整的买卖配对"""
    
    grid_plan = models.ForeignKey(
        GridPlan,
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name="网格计划",
        related_name="trade_pairs"
    )
    
    buy_order = models.OneToOneField(
        GridOrder,
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name="买入订单",
        related_name="buy_pair"
    )
    sell_order = models.OneToOneField(
        GridOrder,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="卖出订单",
        related_name="sell_pair"
    )
    
    # 收益信息
    profit_amount = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="盈利金额"
    )
    profit_rate = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.0000"), verbose_name="盈利率"
    )
    
    # 留利润策略相关
    kept_profit_shares = models.DecimalField(
        max_digits=15, decimal_places=4, default=Decimal("0.0000"), verbose_name="保留利润份额"
    )
    
    is_completed = models.BooleanField(default=False, verbose_name="是否完成")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = "grid_trade_pairs"
        verbose_name = "网格交易对"
        verbose_name_plural = "网格交易对"
        indexes = [
            models.Index(fields=["grid_plan"]),
            models.Index(fields=["is_completed"]),
            models.Index(fields=["completed_at"]),
        ]
    
    def calculate_profit(self):
        """计算交易对盈利"""
        if self.sell_order and self.buy_order:
            profit = (self.sell_order.filled_amount or 0) - (self.buy_order.filled_amount or 0)
            self.profit_amount = profit
            if self.buy_order.filled_amount:
                self.profit_rate = (profit / self.buy_order.filled_amount) * 100
        return self.profit_amount


class GridPerformanceSnapshot(models.Model):
    """网格性能快照 - 定期记录网格表现"""
    
    grid_plan = models.ForeignKey(
        GridPlan,
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name="网格计划",
        related_name="performance_snapshots"
    )
    
    # 快照时间
    snapshot_date = models.DateField(
        null=True, blank=True,
        verbose_name="快照日期"
    )
    
    # 性能指标
    total_profit = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="总盈利"
    )
    realized_profit = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="已实现盈利" 
    )
    unrealized_profit = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="未实现盈利"
    )
    
    # 持仓信息
    total_position = models.DecimalField(
        max_digits=15, decimal_places=4, 
        default=Decimal("0.0000"),
        verbose_name="总持仓"
    )
    kept_profit_position = models.DecimalField(
        max_digits=15, decimal_places=4, 
        default=Decimal("0.0000"),
        verbose_name="利润保留持仓"
    )
    
    # 交易统计
    total_trades = models.IntegerField(
        default=0,
        verbose_name="总交易次数"
    )
    completed_pairs = models.IntegerField(
        default=0,
        verbose_name="完成交易对数"
    )
    
    # 资金使用
    invested_amount = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="已投入金额"
    )
    available_amount = models.DecimalField(
        max_digits=15, decimal_places=2, 
        default=Decimal("0.00"),
        verbose_name="可用金额"
    )
    
    # 标的价格
    current_price = models.DecimalField(
        max_digits=10, decimal_places=4, 
        default=Decimal("100.0000"),
        verbose_name="当前价格"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    
    class Meta:
        db_table = "grid_performance_snapshots"
        verbose_name = "网格性能快照"
        verbose_name_plural = "网格性能快照"
        unique_together = [["grid_plan", "snapshot_date"]]
        indexes = [
            models.Index(fields=["grid_plan", "snapshot_date"]),
        ]
    
    def __str__(self):
        return f"{self.grid_plan.plan_name}-{self.snapshot_date}"


class GridTemplate(models.Model):
    """网格配置模板"""
    name = models.CharField(max_length=100, verbose_name="模板名称")
    description = models.TextField(max_length=500, blank=True, null=True, verbose_name="模板描述")
    template_data = models.JSONField(verbose_name="模板数据")
    
    CATEGORY_CHOICES = [
        ('conservative', '保守型'),
        ('balanced', '平衡型'),
        ('aggressive', '激进型'),
        ('custom', '自定义'),
    ]
    category = models.CharField(
        max_length=20, 
        choices=CATEGORY_CHOICES, 
        default='custom', 
        verbose_name="模板分类"
    )
    
    user = models.ForeignKey(
        'accounts.User', 
        on_delete=models.CASCADE, 
        null=True, blank=True,
        verbose_name="创建用户"
    )
    is_public = models.BooleanField(default=False, verbose_name="是否公开")
    usage_count = models.IntegerField(default=0, verbose_name="使用次数")
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    
    class Meta:
        db_table = "grid_templates"
        verbose_name = "网格模板"
        verbose_name_plural = "网格模板"
        indexes = [
            models.Index(fields=["category"]),
            models.Index(fields=["is_public"]),
            models.Index(fields=["user"]),
            models.Index(fields=["-usage_count"]),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.category})"


class GridSimulation(models.Model):
    """网格模拟记录"""
    simulation_id = models.CharField(max_length=36, unique=True, verbose_name="模拟ID")
    user = models.ForeignKey(
        'accounts.User',
        on_delete=models.CASCADE,
        null=True, blank=True,
        verbose_name="用户"
    )
    
    # 模拟配置
    config_data = models.JSONField(verbose_name="配置数据")
    simulation_params = models.JSONField(verbose_name="模拟参数")
    
    # 模拟结果
    simulation_results = models.JSONField(verbose_name="模拟结果")
    performance_metrics = models.JSONField(verbose_name="性能指标")
    
    # 状态
    STATUS_CHOICES = [
        ('running', '运行中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='running', 
        verbose_name="状态"
    )
    
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    completed_at = models.DateTimeField(null=True, blank=True, verbose_name="完成时间")
    
    class Meta:
        db_table = "grid_simulations"
        verbose_name = "网格模拟"
        verbose_name_plural = "网格模拟"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]
    
    def __str__(self):
        return f"模拟-{self.simulation_id[:8]} ({self.status})"
