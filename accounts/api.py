"""
accounts.api
~~~~~~~~~~

用户账户管理模块的API接口

该模块提供以下API功能:
- 用户认证相关API (注册、登录、登出、密码管理)
- 用户信息管理API (个人信息、资金信息)
- 佣金方案管理API
- 费用计算API

作者: Grid Trading System
创建时间: 2024
"""

from decimal import Decimal
from typing import List, Dict, Any, Optional

from django.contrib.auth import login, logout
from django.shortcuts import get_object_or_404
from django.db import transaction
from ninja import Router, Query
from ninja.security import django_auth

from .models import User, CommissionPlan
from .services import UserAuthService, UserManagementService, BalanceService, CommissionService
from . import schemas

# 创建路由器
accounts_router = Router()
auth_router = Router()  # 不需要认证的路由
user_router = Router(auth=django_auth)  # 需要认证的路由


# ==================== 认证相关API ====================

@auth_router.post("/register", response=schemas.AuthResponse)
def register(request, data: schemas.UserRegisterSchema):
    """用户注册"""
    try:
        success, message, user = UserAuthService.register_user(
            username=data.username,
            email=data.email,
            password=data.password,
            phone=data.phone or None,
            real_name=data.real_name or None
        )
        
        if success:
            # 自动登录
            login(request, user)
            return schemas.AuthResponse(
                success=True,
                message=message,
                user=schemas.UserProfileSchema.from_orm(user),
                token=None
            )
        else:
            return schemas.AuthResponse(
                success=False,
                message=message,
                user=None,
                token=None
            )
            
    except Exception as e:
        return schemas.AuthResponse(
            success=False,
            message=f"注册失败: {str(e)}",
            user=None,
            token=None
        )


@auth_router.post("/login", response=schemas.AuthResponse)
def login_user(request, data: schemas.UserLoginSchema):
    """用户登录"""
    try:
        result = UserAuthService.login_user(
            username=data.username,
            password=data.password
        )
        
        if result.success and result.data and result.data.user:
            login(request, result.data.user)
            return schemas.AuthResponse(
                success=True,
                message=result.message,
                user=schemas.UserProfileSchema.from_orm(result.data.user),
                token=None
            )
        else:
            return schemas.AuthResponse(
                success=False,
                message=result.message,
                user=None,
                token=None
            )
            
    except Exception as e:
        return schemas.AuthResponse(
            success=False,
            message=f"登录失败: {str(e)}",
            user=None,
            token=None
        )


@user_router.post("/logout", response=schemas.MessageResponse)
def logout_user(request):
    """用户登出"""
    try:
        logout(request)
        return schemas.MessageResponse(
            success=True,
            message="登出成功",
            data=None
        )
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"登出失败: {str(e)}",
            data=None
        )


@user_router.post("/change-password", response=schemas.MessageResponse)
def change_password(request, data: schemas.PasswordChangeSchema):
    """修改密码"""
    try:
        success, message = UserAuthService.change_password(
            user=request.user,
            old_password=data.old_password,
            new_password=data.new_password
        )
        
        return schemas.MessageResponse(
            success=success,
            message=message,
            data=None
        )
        
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"密码修改失败: {str(e)}",
            data=None
        )


@auth_router.post("/reset-password-request", response=schemas.MessageResponse)
def reset_password_request(request, data: schemas.PasswordResetRequestSchema):
    """请求重置密码"""
    try:
        success, message, token = UserAuthService.generate_reset_token(data.email)
        
        # 实际应用中这里应该发送邮件，而不是直接返回token
        return schemas.MessageResponse(
            success=success,
            message=message,
            data={'token': token} if success else None
        )
        
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"请求重置密码失败: {str(e)}",
            data=None
        )


# ==================== 用户信息管理API ====================

@user_router.get("/profile", response=schemas.UserProfileSchema)
def get_user_profile(request):
    """获取用户基本信息"""
    return schemas.UserProfileSchema.from_orm(request.user)


@user_router.put("/profile", response=schemas.MessageResponse)
def update_user_profile(request, data: schemas.UserProfileUpdateSchema):
    """更新用户信息"""
    try:
        success, message, user = UserManagementService.update_user_profile(
            user=request.user,
            email=str(data.email) if data.email else None,
            first_name=data.first_name,
            last_name=data.last_name,
            phone=data.phone,
            real_name=data.real_name
        )
        
        return schemas.MessageResponse(
            success=success,
            message=message,
            data=None
        )
        
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"信息更新失败: {str(e)}",
            data=None
        )


@user_router.get("/balance", response=schemas.UserBalanceSchema)
def get_user_balance(request):
    """获取用户资金信息"""
    try:
        balance_data = BalanceService.get_user_balance(request.user)
        return schemas.UserBalanceSchema(**balance_data)
    except Exception as e:
        return schemas.ErrorResponse(
            success=False,
            message=f"获取资金信息失败: {str(e)}",
            error_code=None,
            details=None
        )


@user_router.post("/balance/update", response=schemas.MessageResponse)
def update_user_balance(request, data: schemas.BalanceUpdateSchema):
    """更新用户资金"""
    try:
        result = BalanceService.update_balance(
            user=request.user,
            amount=data.amount,
            transaction_type=data.transaction_type,
            description=data.description
        )
        
        return schemas.MessageResponse(
            success=result.success,
            message=result.message,
            data=None
        )
        
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"资金更新失败: {str(e)}",
            data=None
        )


# ==================== 佣金方案管理API ====================

@user_router.get("/commission-plans", response=List[schemas.CommissionPlanSchema])
def get_commission_schemes(request):
    """获取用户的佣金方案列表"""
    try:
        schemes = CommissionService.get_user_commission_schemes(request.user)
        return [schemas.CommissionPlanSchema.from_orm(scheme) for scheme in schemes]
    except Exception as e:
        return []


@user_router.post("/commission-plans", response=schemas.MessageResponse)
def create_commission_scheme(request, data: schemas.CommissionPlanCreateSchema):
    """创建佣金方案"""
    try:
        success, message, scheme = CommissionService.create_commission_scheme(
            user=request.user,
            plan_name=data.plan_name,
            rate=data.rate,
            min_commission=data.min_commission,
            transfer_fee_rate=data.transfer_fee_rate,
            stamp_tax_rate=data.stamp_tax_rate
        )
        
        # 安全访问scheme.id，确保scheme不为None
        scheme_data = None
        if success and scheme:
            scheme_data = {'plan_id': getattr(scheme, 'id', None)}
        
        return schemas.MessageResponse(
            success=success,
            message=message,
            data=scheme_data
        )
        
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"创建佣金方案失败: {str(e)}",
            data=None
        )


@user_router.get("/commission-plans/{plan_id}", response=schemas.CommissionPlanSchema)
def get_commission_scheme(request, plan_id: int):
    """获取佣金方案详情"""
    scheme = get_object_or_404(
        CommissionPlan,
        id=plan_id,
        user=request.user
    )
    return schemas.CommissionPlanSchema.from_orm(scheme)


@user_router.put("/commission-plans/{plan_id}", response=schemas.MessageResponse)
def update_commission_scheme(request, plan_id: int, data: schemas.CommissionPlanUpdateSchema):
    """更新佣金方案"""
    try:
        scheme = get_object_or_404(
            CommissionPlan,
            id=plan_id,
            user=request.user
        )
        
        update_fields = []
        
        if data.plan_name is not None:
            scheme.plan_name = data.plan_name
            update_fields.append('plan_name')
        
        if data.rate is not None:
            scheme.rate = data.rate
            update_fields.append('rate')
        
        if data.min_commission is not None:
            scheme.min_commission = data.min_commission
            update_fields.append('min_commission')
        
        if data.transfer_fee_rate is not None:
            scheme.transfer_fee_rate = data.transfer_fee_rate
            update_fields.append('transfer_fee_rate')
        
        if data.stamp_tax_rate is not None:
            scheme.stamp_tax_rate = data.stamp_tax_rate
            update_fields.append('stamp_tax_rate')
        
        if data.is_active is not None:
            scheme.is_active = data.is_active
            update_fields.append('is_active')
        
        if update_fields:
            update_fields.append('updated_at')
            scheme.save(update_fields=update_fields)
        
        return schemas.MessageResponse(
            success=True,
            message="佣金方案更新成功",
            data=None
        )
        
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"佣金方案更新失败: {str(e)}",
            data=None
        )


@user_router.delete("/commission-plans/{plan_id}", response=schemas.MessageResponse)
def delete_commission_scheme(request, plan_id: int):
    """删除佣金方案"""
    try:
        scheme = get_object_or_404(
            CommissionPlan,
            id=plan_id,
            user=request.user
        )
        
        # 检查是否是最后一个方案
        user_schemes_count = CommissionPlan.objects.filter(user=request.user).count()
        if user_schemes_count <= 1:
            return schemas.MessageResponse(
                success=False,
                message="至少需要保留一个佣金方案",
                data=None
            )
        
        scheme.delete()
        
        return schemas.MessageResponse(
            success=True,
            message="佣金方案删除成功",
            data=None
        )
        
    except Exception as e:
        return schemas.MessageResponse(
            success=False,
            message=f"佣金方案删除失败: {str(e)}",
            data=None
        )


# ==================== 费用计算API ====================

@user_router.post("/calculate-fees", response=schemas.FeeCalculationResponse)
def calculate_trading_fees(request, data: schemas.FeeCalculationRequest):
    """计算交易费用"""
    try:
        # 获取佣金方案
        if data.commission_plan_id:
            scheme = get_object_or_404(
                CommissionPlan,
                id=data.commission_plan_id,
                user=request.user
            )
        else:
            scheme = CommissionService.get_or_create_default_scheme(request.user)
        
        # 计算费用
        fee_data = CommissionService.calculate_trading_fees(
            amount=data.amount,
            trade_type=data.trade_type,
            commission_scheme=scheme
        )
        
        if isinstance(fee_data, dict) and 'error' in fee_data:
            return schemas.ErrorResponse(
                success=False,
                message=fee_data['error'],
                error_code=None,
                details=None
            )
        
        return schemas.FeeCalculationResponse(**fee_data)
        
    except Exception as e:
        return schemas.ErrorResponse(
            success=False,
            message=f"费用计算失败: {str(e)}",
            error_code=None,
            details=None
        )


# ==================== 统计信息API ====================

@user_router.get("/stats", response=schemas.UserStatsSchema)
def get_user_stats(request):
    """获取用户统计信息（管理员功能）"""
    try:
        # 这里可以添加权限检查
        if not request.user.is_staff:
            return schemas.ErrorResponse(
                success=False,
                message="无权限访问统计信息",
                error_code="PERMISSION_DENIED",
                details=None
            )
        
        stats = UserManagementService.get_user_stats()
        return schemas.UserStatsSchema(**stats)
        
    except Exception as e:
        return schemas.ErrorResponse(
            success=False,
            message=f"获取统计信息失败: {str(e)}",
            error_code=None,
            details=None
        )


# ==================== 当前用户状态API ====================

@user_router.get("/me", response=Dict[str, Any])
def get_current_user_info(request):
    """获取当前用户完整信息"""
    try:
        user = request.user
        
        # 获取用户基本信息
        profile = UserManagementService.get_user_profile(user)
        
        # 获取资金信息
        balance = BalanceService.get_user_balance(user)
        
        # 获取佣金方案
        schemes = CommissionService.get_user_commission_schemes(user)
        
        return {
            'profile': profile,
            'balance': balance,
            'commission_schemes': [
                schemas.CommissionPlanSchema.from_orm(scheme).dict() 
                for scheme in schemes
            ],
            'stats': {
                'total_schemes': len(schemes),
                'active_schemes': len([s for s in schemes if s.is_active])
            }
        }
        
    except Exception as e:
        return {
            'error': f"获取用户信息失败: {str(e)}"
        }


# 将子路由器合并到主路由器
accounts_router.add_router("/auth", auth_router)
accounts_router.add_router("/user", user_router) 