from decimal import Decimal

from django.db import models


class Stock(models.Model):
    """股票/标的模型"""

    # 基本信息
    symbol = models.CharField(
        max_length=20, unique=True, verbose_name="股票代码", help_text="如 SZ.510300"
    )
    name = models.CharField(
        max_length=100, verbose_name="股票名称", help_text="如 沪深300ETF"
    )
    market = models.CharField(max_length=10, verbose_name="市场", help_text="如 SZ、SH")

    # 交易信息
    current_price = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="当前价格"
    )
    prev_close = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="昨收价"
    )

    # 基本面信息
    total_shares = models.BigIntegerField(null=True, blank=True, verbose_name="总股本")
    market_cap = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="总市值"
    )

    # 分类信息
    CATEGORY_CHOICES = [
        ("stock", "股票"),
        ("etf", "ETF"),
        ("fund", "基金"),
        ("bond", "债券"),
    ]
    category = models.CharField(
        max_length=50, choices=CATEGORY_CHOICES, default="stock", verbose_name="类别"
    )
    industry = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="行业"
    )
    sector = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="板块"
    )

    # 状态
    is_active = models.BooleanField(default=True, verbose_name="是否可交易")
    is_st = models.BooleanField(default=False, verbose_name="是否ST股票")

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")
    last_trade_date = models.DateTimeField(
        null=True, blank=True, verbose_name="最后交易日期"
    )

    class Meta:
        db_table = "stocks"
        verbose_name = "股票"
        verbose_name_plural = "股票"
        indexes = [
            models.Index(fields=["symbol"]),
            models.Index(fields=["market"]),
            models.Index(fields=["category"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self):
        return f"{self.symbol}-{self.name}"


class StockPrice(models.Model):
    """股票价格历史数据模型"""

    stock = models.ForeignKey(
        Stock, on_delete=models.CASCADE, verbose_name="股票", related_name="prices"
    )

    # 价格数据
    open_price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="开盘价"
    )
    high_price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="最高价"
    )
    low_price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="最低价"
    )
    close_price = models.DecimalField(
        max_digits=10, decimal_places=4, verbose_name="收盘价"
    )
    volume = models.BigIntegerField(verbose_name="成交量")
    amount = models.DecimalField(
        max_digits=20, decimal_places=2, null=True, blank=True, verbose_name="成交额"
    )

    # 时间信息
    trade_date = models.DateField(verbose_name="交易日期")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")

    class Meta:
        db_table = "stock_prices"
        verbose_name = "股票价格"
        verbose_name_plural = "股票价格"
        unique_together = [["stock", "trade_date"]]  # 确保每只股票每天只有一条记录
        indexes = [
            models.Index(fields=["trade_date"]),
            models.Index(fields=["stock", "trade_date"]),
        ]

    def __str__(self):
        return f"{self.stock.symbol}-{self.trade_date}"


class WatchList(models.Model):
    """用户自选股模型"""

    user = models.ForeignKey(
        "accounts.User", on_delete=models.CASCADE, verbose_name="用户"
    )
    stock = models.ForeignKey(Stock, on_delete=models.CASCADE, verbose_name="股票")

    # 自定义信息
    alias = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="用户自定义别名"
    )
    notes = models.TextField(max_length=500, blank=True, null=True, verbose_name="备注")

    # 监控设置
    target_price = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="目标价格"
    )
    stop_loss_price = models.DecimalField(
        max_digits=10, decimal_places=4, null=True, blank=True, verbose_name="止损价格"
    )

    # 时间戳
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "watch_lists"
        verbose_name = "自选股"
        verbose_name_plural = "自选股"
        unique_together = [["user", "stock"]]  # 保证用户-股票唯一性
        indexes = [
            models.Index(fields=["user"]),
            models.Index(fields=["user", "stock"]),
        ]

    def __str__(self):
        return f"{self.user.username}-{self.stock.symbol}"
