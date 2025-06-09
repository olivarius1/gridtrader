from decimal import Decimal

from django.db import models


class ProfitLossRecord(models.Model):
    """盈亏记录模型 - 按周期统计用户收益和亏损"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, verbose_name="用户"
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="股票",
    )

    # 统计周期
    PERIOD_TYPE_CHOICES = [
        ("daily", "日"),
        ("weekly", "周"),
        ("monthly", "月"),
        ("quarterly", "季度"),
        ("yearly", "年"),
    ]
    period_type = models.CharField(
        max_length=20, choices=PERIOD_TYPE_CHOICES, verbose_name="统计周期"
    )
    period_date = models.DateField(verbose_name="统计日期")

    # 盈亏数据
    realized_pnl = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="已实现盈亏",
    )
    unrealized_pnl = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="浮动盈亏",
    )
    total_pnl = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="总盈亏"
    )

    # 收益率
    return_rate = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.00"), verbose_name="收益率"
    )

    # 交易统计
    total_trades = models.IntegerField(default=0, verbose_name="交易次数")
    buy_trades = models.IntegerField(default=0, verbose_name="买入次数")
    sell_trades = models.IntegerField(default=0, verbose_name="卖出次数")

    # 资金统计
    total_investment = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="总投入"
    )
    current_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="当前价值",
    )

    # 费用统计
    total_commission = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="总佣金"
    )
    total_fees = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="总费用"
    )

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "profit_loss_records"
        verbose_name = "盈亏记录"
        verbose_name_plural = "盈亏记录"
        unique_together = [
            ["user", "stock", "period_type", "period_date"]
        ]  # 确保唯一性
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["stock"]),
            models.Index(fields=["period_type"]),
            models.Index(fields=["period_date"]),
            models.Index(fields=["user", "period_type", "period_date"]),
        ]
        ordering = ["-period_date"]

    def __str__(self):
        stock_name = self.stock.symbol if self.stock else "全部"
        period_map = {
            "daily": "日",
            "weekly": "周",
            "monthly": "月",
            "quarterly": "季度",
            "yearly": "年",
        }
        period_display = period_map.get(self.period_type, self.period_type)
        return f"{self.user.username}-{stock_name}-{period_display}-{self.period_date}"


class TradingPerformance(models.Model):
    """交易表现模型 - 详细的交易分析指标"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, verbose_name="用户"
    )
    stock = models.ForeignKey(
        "stocks.Stock",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        verbose_name="股票",
    )

    # 统计时间范围
    start_date = models.DateField(verbose_name="开始日期")
    end_date = models.DateField(verbose_name="结束日期")

    # 基础指标
    total_trades = models.IntegerField(default=0, verbose_name="总交易次数")
    winning_trades = models.IntegerField(default=0, verbose_name="盈利交易次数")
    losing_trades = models.IntegerField(default=0, verbose_name="亏损交易次数")

    # 胜率和盈亏比
    win_rate = models.DecimalField(
        max_digits=5, decimal_places=2, default=Decimal("0.00"), verbose_name="胜率"
    )
    profit_loss_ratio = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.00"), verbose_name="盈亏比"
    )

    # 收益指标
    total_return = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="总收益"
    )
    total_return_rate = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.00"), verbose_name="总收益率"
    )
    average_return_per_trade = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="平均每笔收益",
    )

    # 最大盈亏
    max_profit = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="最大盈利",
    )
    max_loss = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="最大亏损",
    )
    max_drawdown = models.DecimalField(
        max_digits=8, decimal_places=4, default=Decimal("0.00"), verbose_name="最大回撤"
    )

    # 风险指标
    sharpe_ratio = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True, verbose_name="夏普比率"
    )
    volatility = models.DecimalField(
        max_digits=8, decimal_places=4, null=True, blank=True, verbose_name="波动率"
    )

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "trading_performance"
        verbose_name = "交易表现"
        verbose_name_plural = "交易表现"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["stock"]),
            models.Index(fields=["start_date", "end_date"]),
        ]
        ordering = ["-end_date"]

    def __str__(self):
        stock_name = self.stock.symbol if self.stock else "全部"
        return f"{self.user.username}-{stock_name}-{self.start_date}到{self.end_date}"


class DailyBalance(models.Model):
    """每日资产余额模型 - 用于计算收益曲线"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, verbose_name="用户"
    )

    # 日期
    balance_date = models.DateField(verbose_name="日期")

    # 资产信息
    cash_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="现金余额",
    )
    stock_value = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="股票市值",
    )
    total_value = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="总资产"
    )

    # 当日变化
    daily_pnl = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="当日盈亏",
    )
    daily_return_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.00"),
        verbose_name="当日收益率",
    )

    # 累计收益
    cumulative_pnl = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="累计盈亏",
    )
    cumulative_return_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.00"),
        verbose_name="累计收益率",
    )

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "daily_balances"
        verbose_name = "每日资产"
        verbose_name_plural = "每日资产"
        unique_together = [["user", "balance_date"]]  # 确保每用户每天只有一条记录
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["balance_date"]),
            models.Index(fields=["user", "balance_date"]),
        ]
        ordering = ["-balance_date"]

    def __str__(self):
        return f"{self.user.username}-{self.balance_date}-{self.total_value}"
