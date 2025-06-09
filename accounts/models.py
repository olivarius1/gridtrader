from decimal import Decimal

from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """扩展用户模型"""

    phone = models.CharField(
        max_length=20, blank=True, null=True, verbose_name="手机号"
    )
    real_name = models.CharField(
        max_length=100, blank=True, null=True, verbose_name="真实姓名"
    )

    # 账户状态
    is_verified = models.BooleanField(default=False, verbose_name="是否已认证")

    # 资金相关
    total_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=Decimal("0.00"), verbose_name="总资产"
    )
    available_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="可用资金",
    )
    frozen_balance = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="冻结资金",
    )

    # 时间字段
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "accounts_user"
        verbose_name = "用户"
        verbose_name_plural = "用户"

    def __str__(self):
        return f"User({self.username})"


class CommissionScheme(models.Model):
    """佣金方案模型"""

    scheme_name = models.CharField(max_length=100, verbose_name="方案名称")
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="用户")

    # 佣金费率设置
    commission_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        default=Decimal("0.0003"),
        verbose_name="佣金费率",
        help_text="默认万3",
    )
    min_commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("5.00"),
        verbose_name="最低佣金",
        help_text="默认5元",
    )

    # 其他费用
    transfer_fee_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        default=Decimal("0.00002"),
        verbose_name="过户费费率",
    )
    stamp_tax_rate = models.DecimalField(
        max_digits=8,
        decimal_places=6,
        default=Decimal("0.001"),
        verbose_name="印花税费率",
        help_text="卖出时收取",
    )

    # 状态
    is_active = models.BooleanField(default=True, verbose_name="是否启用")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="创建时间")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="更新时间")

    class Meta:
        db_table = "commission_schemes"
        verbose_name = "佣金方案"
        verbose_name_plural = "佣金方案"
        indexes = [
            models.Index(fields=["user", "scheme_name"]),
        ]

    def __str__(self):
        return f"CommissionScheme({self.scheme_name})"

    def calculate_commission(self, amount):
        """计算佣金"""
        commission = amount * self.commission_rate
        return max(commission, self.min_commission)

    def calculate_transfer_fee(self, amount):
        """计算过户费"""
        return amount * self.transfer_fee_rate

    def calculate_stamp_tax(self, amount):
        """计算印花税（仅卖出时）"""
        return amount * self.stamp_tax_rate
