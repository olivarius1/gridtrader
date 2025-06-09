from datetime import datetime
from decimal import Decimal

from django.db import models
from mongoengine import (
    BooleanField,
    DateTimeField,
    DecimalField,
    Document,
    IntField,
    StringField,
)

# Create your models here.


class TradingRecord(models.Model):
    """交易记录模型"""

    # 用户和标的信息
    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, verbose_name="用户"
    )
    stock = models.ForeignKey(
        "stocks.Stock", on_delete=models.CASCADE, verbose_name="交易标的"
    )

    # 交易基本信息
    trade_date = models.CharField(
        max_length=8, verbose_name="成交日期", help_text="格式：20250101"
    )
    trade_time = models.CharField(
        max_length=5, verbose_name="成交时间", help_text="格式：09:31"
    )

    # 价格和数量
    price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="成交价格"
    )
    quantity = models.IntegerField(verbose_name="成交数量")

    # 交易类型
    TRADE_TYPE_CHOICES = [("b", "买入"), ("s", "卖出")]
    trade_type = models.CharField(
        max_length=1, choices=TRADE_TYPE_CHOICES, verbose_name="交易类型"
    )

    # 金额计算
    amount = models.DecimalField(
        max_digits=15, decimal_places=2, verbose_name="成交金额"
    )

    # 费用信息
    commission = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="佣金"
    )
    transfer_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="过户费"
    )
    stamp_tax = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="印花税"
    )
    total_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal("0.00"), verbose_name="总费用"
    )

    # 实际成本/收入（含费用）
    net_amount = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="净额",
        help_text="买入时为负数（支出），卖出时为正数（收入）",
    )

    # 备注和状态
    notes = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="备注",
        help_text="如建仓、盈利卖出一部分",
    )

    STATUS_CHOICES = [
        ("completed", "已完成"),
        ("cancelled", "已取消"),
        ("pending", "待成交"),
    ]
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default="completed", verbose_name="状态"
    )

    # 关联信息
    commission_scheme = models.ForeignKey(
        "accounts.CommissionScheme",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="佣金方案",
    )
    grid_plan = models.ForeignKey(
        "grid.GridPlan",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name="网格计划",
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "trading_records"
        verbose_name = "交易记录"
        verbose_name_plural = "交易记录"
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["stock"]),
            models.Index(fields=["trade_date"]),
            models.Index(fields=["trade_type"]),
            models.Index(fields=["user", "stock"]),
            models.Index(fields=["user", "trade_date"]),
            models.Index(fields=["stock", "trade_date"]),
        ]
        ordering = ["-trade_date", "-trade_time"]

    def __str__(self):
        type_display = "买入" if self.trade_type == "b" else "卖出"
        return f"{self.stock.symbol}-{type_display}-{self.quantity}@{self.price}"

    def save(self, *args, **kwargs):
        """保存时自动计算净额"""
        self.calculate_net_amount()
        super().save(*args, **kwargs)

    def calculate_net_amount(self):
        """计算净额"""
        if self.trade_type == "b":  # 买入
            self.net_amount = -(self.amount + self.total_fee)
        else:  # 卖出
            self.net_amount = self.amount - self.total_fee


class Position(models.Model):
    """持仓模型"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, verbose_name="用户"
    )
    stock = models.ForeignKey(
        "stocks.Stock", on_delete=models.CASCADE, verbose_name="标的"
    )

    # 持仓信息
    total_quantity = models.IntegerField(default=0, verbose_name="总持仓数量")
    available_quantity = models.IntegerField(default=0, verbose_name="可用数量")
    frozen_quantity = models.IntegerField(default=0, verbose_name="冻结数量")

    # 成本信息
    avg_cost = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        default=Decimal("0.00"),
        verbose_name="平均成本价",
    )
    total_cost = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="总成本"
    )

    # 市值信息
    current_price = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="当前价格"
    )
    market_value = models.DecimalField(
        max_digits=15, decimal_places=2, null=True, blank=True, verbose_name="市值"
    )

    # 盈亏信息
    unrealized_pnl = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="浮动盈亏",
    )
    unrealized_pnl_rate = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        default=Decimal("0.00"),
        verbose_name="浮动盈亏率",
    )
    realized_pnl = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="已实现盈亏",
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    last_trade_date = models.DateTimeField(
        null=True, blank=True, verbose_name="最后交易日期"
    )

    class Meta:
        db_table = "positions"
        verbose_name = "持仓"
        verbose_name_plural = "持仓"
        unique_together = [["user", "stock"]]  # 保证用户-标的唯一性
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["user", "stock"]),
        ]

    def __str__(self):
        return f"{self.user.username}-{self.stock.symbol}-{self.total_quantity}"

    def update_position_from_trade(self, trade_record):
        """根据交易记录更新持仓"""
        from django.utils import timezone

        if trade_record.trade_type == "b":  # 买入
            # 更新持仓数量和成本
            new_total_cost = (
                self.total_cost + trade_record.amount + trade_record.total_fee
            )
            new_total_quantity = self.total_quantity + trade_record.quantity

            if new_total_quantity > 0:
                self.avg_cost = new_total_cost / new_total_quantity

            self.total_quantity = new_total_quantity
            self.available_quantity = new_total_quantity
            self.total_cost = new_total_cost

        else:  # 卖出
            # 计算已实现盈亏
            sell_cost = self.avg_cost * trade_record.quantity
            sell_income = trade_record.amount - trade_record.total_fee
            realized_pnl = sell_income - sell_cost
            self.realized_pnl += realized_pnl

            # 更新持仓数量
            self.total_quantity -= trade_record.quantity
            self.available_quantity = self.total_quantity

            # 按比例减少总成本
            if self.total_quantity > 0:
                cost_ratio = trade_record.quantity / (
                    self.total_quantity + trade_record.quantity
                )
                self.total_cost *= 1 - cost_ratio
            else:
                self.total_cost = Decimal("0.00")
                self.avg_cost = Decimal("0.00")

        self.last_trade_date = timezone.now()
        self.save()

    def calculate_pnl(self, current_price=None):
        """计算盈亏"""
        if current_price:
            self.current_price = current_price

        if self.current_price and self.total_quantity > 0:
            self.market_value = self.total_quantity * self.current_price

            if self.total_cost > 0:
                self.unrealized_pnl = self.market_value - self.total_cost
                self.unrealized_pnl_rate = self.unrealized_pnl / self.total_cost
            else:
                self.unrealized_pnl = Decimal("0.00")
                self.unrealized_pnl_rate = Decimal("0.00")
        else:
            self.market_value = Decimal("0.00")
            self.unrealized_pnl = Decimal("0.00")
            self.unrealized_pnl_rate = Decimal("0.00")

        self.save()
