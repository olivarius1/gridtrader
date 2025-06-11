"""
accounts.schemas
~~~~~~~~~~~~~~

用户账户管理模块的Schema定义

该模块包含以下Schema:
- 用户认证相关Schema (注册、登录、登出)
- 用户信息相关Schema (个人信息、资金信息)
- 佣金方案相关Schema
- 响应消息Schema

作者: Grid Trading System
创建时间: 2024
"""

from decimal import Decimal
from typing import Optional, List
from ninja import Schema, ModelSchema
from pydantic import Field, field_validator, EmailStr

from .models import User, CommissionPlan


# ==================== 认证相关Schema ====================

class UserRegisterSchema(Schema):
    """用户注册Schema"""
    username: str = Field(..., min_length=3, max_length=150, description="用户名，3-150字符")
    email: EmailStr = Field(..., description="邮箱地址")
    password: str = Field(..., min_length=6, max_length=128, description="密码，至少6位")
    password_confirm: str = Field(..., description="确认密码")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    real_name: Optional[str] = Field(None, max_length=100, description="真实姓名")
    
    @field_validator('password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        if hasattr(info, 'data') and 'password' in info.data and v != info.data['password']:
            raise ValueError('密码和确认密码不一致')
        return v
    
    @field_validator('username')
    @classmethod
    def username_valid(cls, v):
        if not v.replace('_', '').replace('-', '').isalnum():
            raise ValueError('用户名只能包含字母、数字、下划线和连字符')
        return v


class UserLoginSchema(Schema):
    """用户登录Schema"""
    username: str = Field(..., description="用户名或邮箱")
    password: str = Field(..., description="密码")
    remember_me: bool = Field(False, description="记住我")


class PasswordChangeSchema(Schema):
    """修改密码Schema"""
    old_password: str = Field(..., description="当前密码")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码，至少6位")
    new_password_confirm: str = Field(..., description="确认新密码")
    
    @field_validator('new_password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        if hasattr(info, 'data') and 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('新密码和确认密码不一致')
        return v


class PasswordResetRequestSchema(Schema):
    """密码重置请求Schema"""
    email: EmailStr = Field(..., description="注册邮箱")


class PasswordResetSchema(Schema):
    """密码重置Schema"""
    token: str = Field(..., description="重置令牌")
    new_password: str = Field(..., min_length=6, max_length=128, description="新密码")
    new_password_confirm: str = Field(..., description="确认新密码")
    
    @field_validator('new_password_confirm')
    @classmethod
    def passwords_match(cls, v, info):
        if hasattr(info, 'data') and 'new_password' in info.data and v != info.data['new_password']:
            raise ValueError('新密码和确认密码不一致')
        return v


# ==================== 用户信息相关Schema ====================

class UserProfileSchema(ModelSchema):
    """用户基本信息Schema"""
    
    class Config:
        model = User
        model_fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'phone', 'real_name', 'is_verified', 'date_joined', 'last_login'
        ]


class UserProfileUpdateSchema(Schema):
    """用户信息更新Schema"""
    email: Optional[EmailStr] = Field(None, description="邮箱地址")
    first_name: Optional[str] = Field(None, max_length=30, description="名")
    last_name: Optional[str] = Field(None, max_length=30, description="姓")
    phone: Optional[str] = Field(None, max_length=20, description="手机号")
    real_name: Optional[str] = Field(None, max_length=100, description="真实姓名")


class UserBalanceSchema(Schema):
    """用户资金信息Schema"""
    total_balance: Decimal = Field(..., description="总资产")
    available_balance: Decimal = Field(..., description="可用资金")
    frozen_balance: Decimal = Field(..., description="冻结资金")
    updated_at: str = Field(..., description="更新时间")


class BalanceUpdateSchema(Schema):
    """资金变动Schema"""
    amount: Decimal = Field(..., description="变动金额，正数为增加，负数为减少")
    transaction_type: str = Field(..., description="交易类型")
    description: Optional[str] = Field(None, max_length=200, description="变动说明")
    
    @field_validator('transaction_type')
    @classmethod
    def transaction_type_valid(cls, v):
        allowed_types = {'deposit', 'withdraw', 'freeze', 'unfreeze', 'trade'}
        if v not in allowed_types:
            raise ValueError(f'交易类型必须是以下之一: {", ".join(allowed_types)}')
        return v


# ==================== 佣金方案相关Schema ====================

class CommissionPlanSchema(Schema):
    """佣金方案Schema"""
    id: int = Field(..., description="方案ID")
    plan_name: str = Field(..., description="方案名称")
    rate: Decimal = Field(..., description="佣金费率")
    min_commission: Decimal = Field(..., description="最低佣金")
    transfer_fee_rate: Decimal = Field(..., description="过户费费率")
    stamp_tax_rate: Decimal = Field(..., description="印花税费率")
    is_active: bool = Field(..., description="是否启用")
    created_at: str = Field(..., description="创建时间")
    updated_at: str = Field(..., description="更新时间")

    @classmethod
    def from_orm(cls, obj):
        """从ORM对象创建Schema实例"""
        return cls(
            id=obj.id,
            plan_name=obj.plan_name,
            rate=obj.rate,
            min_commission=obj.min_commission,
            transfer_fee_rate=obj.transfer_fee_rate,
            stamp_tax_rate=obj.stamp_tax_rate,
            is_active=obj.is_active,
            created_at=obj.created_at.isoformat(),
            updated_at=obj.updated_at.isoformat()
        )


class CommissionPlanCreateSchema(Schema):
    """创建佣金方案Schema"""
    plan_name: str = Field(..., max_length=100, description="方案名称")
    rate: Decimal = Field(Decimal("0.0003"), description="佣金费率，默认万3")
    min_commission: Decimal = Field(Decimal("5.00"), description="最低佣金，默认5元")
    transfer_fee_rate: Decimal = Field(Decimal("0.00002"), description="过户费费率")
    stamp_tax_rate: Decimal = Field(Decimal("0.001"), description="印花税费率")
    
    @field_validator('rate')
    @classmethod
    def commission_rate_valid(cls, v):
        if v < 0 or v > 0.01:  # 最大1%
            raise ValueError('佣金费率应在0-1%之间')
        return v
    
    @field_validator('min_commission')
    @classmethod
    def min_commission_valid(cls, v):
        if v < 0:
            raise ValueError('最低佣金不能为负数')
        return v


class CommissionPlanUpdateSchema(Schema):
    """更新佣金方案Schema"""
    plan_name: Optional[str] = Field(None, max_length=100, description="方案名称")
    rate: Optional[Decimal] = Field(None, description="佣金费率")
    min_commission: Optional[Decimal] = Field(None, description="最低佣金")
    transfer_fee_rate: Optional[Decimal] = Field(None, description="过户费费率")
    stamp_tax_rate: Optional[Decimal] = Field(None, description="印花税费率")
    is_active: Optional[bool] = Field(None, description="是否启用")


class FeeCalculationRequest(Schema):
    """费用计算请求Schema"""
    amount: Decimal = Field(..., gt=0, description="交易金额")
    trade_type: str = Field(..., description="交易类型")
    commission_plan_id: Optional[int] = Field(None, description="佣金方案ID，不指定则使用默认方案")
    
    @field_validator('trade_type')
    @classmethod
    def trade_type_valid(cls, v):
        allowed_types = {'buy', 'sell'}
        if v not in allowed_types:
            raise ValueError(f'交易类型必须是以下之一: {", ".join(allowed_types)}')
        return v


class FeeCalculationResponse(Schema):
    """费用计算响应Schema"""
    amount: Decimal = Field(..., description="交易金额")
    commission: Decimal = Field(..., description="佣金")
    transfer_fee: Decimal = Field(..., description="过户费")
    stamp_tax: Decimal = Field(..., description="印花税")
    total_fee: Decimal = Field(..., description="总费用")
    net_amount: Decimal = Field(..., description="净额")
    plan_name: str = Field(..., description="使用的佣金方案")


# ==================== 响应消息Schema ====================

class AuthResponse(Schema):
    """认证响应Schema"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    user: Optional[UserProfileSchema] = Field(None, description="用户信息")
    token: Optional[str] = Field(None, description="访问令牌")


class MessageResponse(Schema):
    """通用消息响应Schema"""
    success: bool = Field(..., description="是否成功")
    message: str = Field(..., description="响应消息")
    data: Optional[dict] = Field(None, description="额外数据")


class ErrorResponse(Schema):
    """错误响应Schema"""
    success: bool = Field(False, description="总是False")
    message: str = Field(..., description="错误消息")
    error_code: Optional[str] = Field(None, description="错误代码")
    details: Optional[dict] = Field(None, description="错误详情")


# ==================== 统计信息Schema ====================

class UserStatsSchema(Schema):
    """用户统计信息Schema"""
    total_users: int = Field(..., description="总用户数")
    active_users: int = Field(..., description="活跃用户数")
    verified_users: int = Field(..., description="已认证用户数")
    total_balance_sum: Decimal = Field(..., description="用户总资产")
    avg_balance_per_user: Decimal = Field(..., description="平均每用户资产")


# ==================== 扩展功能Schema（预留）====================

class EmailVerificationSchema(Schema):
    """邮箱验证Schema（预留）"""
    email: EmailStr = Field(..., description="邮箱地址")
    verification_code: str = Field(..., description="验证码")


class PhoneVerificationSchema(Schema):
    """手机验证Schema（预留）"""
    phone: str = Field(..., description="手机号")
    verification_code: str = Field(..., description="验证码")


class TwoFactorAuthSchema(Schema):
    """双因子认证Schema（预留）"""
    code: str = Field(..., description="认证码")
    remember_device: bool = Field(False, description="记住设备")


class UserSecuritySettingsSchema(Schema):
    """用户安全设置Schema（预留）"""
    enable_2fa: bool = Field(False, description="启用双因子认证")
    login_notifications: bool = Field(True, description="登录通知")
    security_alerts: bool = Field(True, description="安全警报") 