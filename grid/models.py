from decimal import Decimal

from django.db import models


class GridPlan(models.Model):
    """网格计划模型"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, verbose_name="用户"
    )
    stock = models.ForeignKey(
        "stocks.Stock", on_delete=models.CASCADE, verbose_name="交易标的"
    )

    # 基本信息
    plan_name = models.CharField(max_length=100, verbose_name="计划名称")
    description = models.TextField(
        max_length=500, blank=True, null=True, verbose_name="计划描述"
    )

    # 网格参数
    base_price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="基准价格"
    )
    grid_interval = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        verbose_name="网格间距",
        help_text="价格间距或百分比",
    )

    INTERVAL_TYPE_CHOICES = [
        ("fixed", "固定金额"),
        ("percent", "百分比"),
    ]
    interval_type = models.CharField(
        max_length=10,
        choices=INTERVAL_TYPE_CHOICES,
        default="percent",
        verbose_name="间距类型",
    )

    # 价格范围
    min_price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="最低价格"
    )
    max_price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="最高价格"
    )

    # 交易参数
    base_quantity = models.IntegerField(verbose_name="基础交易数量")
    max_investment = models.DecimalField(
        max_digits=15, decimal_places=2, verbose_name="最大投资金额"
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
    total_trades = models.IntegerField(default=0, verbose_name="总交易次数")
    buy_trades = models.IntegerField(default=0, verbose_name="买入次数")
    sell_trades = models.IntegerField(default=0, verbose_name="卖出次数")

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

    def calculate_grid_prices(self):
        """计算网格价格点"""
        prices = []
        current_price = self.base_price

        # 向上计算价格点
        while current_price <= self.max_price:
            prices.append(current_price)
            if self.interval_type == "percent":
                current_price *= 1 + self.grid_interval / 100
            else:
                current_price += self.grid_interval

        # 向下计算价格点
        current_price = self.base_price
        if self.interval_type == "percent":
            current_price *= 1 - self.grid_interval / 100
        else:
            current_price -= self.grid_interval

        while current_price >= self.min_price:
            prices.insert(0, current_price)
            if self.interval_type == "percent":
                current_price *= 1 - self.grid_interval / 100
            else:
                current_price -= self.grid_interval

        return sorted(prices)


class GridOrder(models.Model):
    """网格订单模型"""

    grid_plan = models.ForeignKey(
        GridPlan,
        on_delete=models.CASCADE,
        verbose_name="网格计划",
        related_name="orders",
    )

    # 订单信息
    price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="订单价格"
    )
    quantity = models.IntegerField(verbose_name="订单数量")

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
    filled_quantity = models.IntegerField(default=0, verbose_name="已成交数量")
    filled_price = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="成交价格"
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
        ]
        ordering = ["price"]

    def __str__(self):
        type_display = "买入" if self.order_type == "buy" else "卖出"
        return f"{self.grid_plan.stock.symbol}-{type_display}@{self.price}"
