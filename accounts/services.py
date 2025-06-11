"""
accounts.services
~~~~~~~~~~~~~~~

用户账户管理模块的服务层

该模块包含以下服务类:
- UserAuthService: 用户认证服务
- UserManagementService: 用户管理服务
- BalanceService: 资金管理服务
- CommissionService: 佣金方案服务

作者: Grid Trading System
创建时间: 2024
"""

import hashlib
import secrets
from decimal import Decimal
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.hashers import make_password, check_password
from django.db import transaction, models
from django.db.models import Sum, Avg, Count, Q
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings

from .models import User, CommissionPlan


class UserAuthService:
    """用户认证服务"""
    
    @staticmethod
    def register_user(
        username: str,
        email: str,
        password: str,
        phone: Optional[str] = None,
        real_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[User]]:
        """
        用户注册
        
        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            phone: 手机号
            real_name: 真实姓名
            
        Returns:
            Tuple[是否成功, 消息, 用户对象]
        """
        try:
            # 检查用户名是否已存在
            if User.objects.filter(username=username).exists():
                return False, "用户名已存在", None
            
            # 检查邮箱是否已存在
            if User.objects.filter(email=email).exists():
                return False, "邮箱已被注册", None
                
            # 检查手机号是否已存在
            if phone and User.objects.filter(phone=phone).exists():
                return False, "手机号已被注册", None
            
            # 创建用户
            with transaction.atomic():
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    phone=phone,
                    real_name=real_name
                )
                
                # 创建默认佣金方案
                CommissionService.create_default_commission_scheme(user)
                
            return True, "注册成功", user
            
        except Exception as e:
            return False, f"注册失败: {str(e)}", None
    
    @staticmethod
    def login_user(username: str, password: str) -> Tuple[bool, str, Optional[User]]:
        """
        用户登录
        
        Args:
            username: 用户名或邮箱
            password: 密码
            
        Returns:
            Tuple[是否成功, 消息, 用户对象]
        """
        try:
            # 支持用户名或邮箱登录
            user = None
            if '@' in username:
                # 邮箱登录
                try:
                    user = User.objects.get(email=username)
                    user = authenticate(username=user.username, password=password)
                except User.DoesNotExist:
                    pass
            else:
                # 用户名登录
                user = authenticate(username=username, password=password)
            
            if user and user.is_active:
                return True, "登录成功", user
            else:
                return False, "用户名或密码错误", None
                
        except Exception as e:
            return False, f"登录失败: {str(e)}", None
    
    @staticmethod
    def change_password(
        user: User, 
        old_password: str, 
        new_password: str
    ) -> Tuple[bool, str]:
        """
        修改密码
        
        Args:
            user: 用户对象
            old_password: 当前密码
            new_password: 新密码
            
        Returns:
            Tuple[是否成功, 消息]
        """
        try:
            # 验证当前密码
            if not check_password(old_password, user.password):
                return False, "当前密码错误"
            
            # 设置新密码
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            return True, "密码修改成功"
            
        except Exception as e:
            return False, f"密码修改失败: {str(e)}"
    
    @staticmethod
    def generate_reset_token(email: str) -> Tuple[bool, str, Optional[str]]:
        """
        生成密码重置令牌
        
        Args:
            email: 邮箱地址
            
        Returns:
            Tuple[是否成功, 消息, 重置令牌]
        """
        try:
            user = User.objects.get(email=email)
            
            # 生成重置令牌 (简化版本，实际应该存储到数据库并设置过期时间)
            token = secrets.token_urlsafe(32)
            
            # 这里应该将token和过期时间存储到数据库
            # 为了演示，我们使用简单的方式
            
            return True, "重置令牌已生成", token
            
        except User.DoesNotExist:
            return False, "邮箱地址不存在", None
        except Exception as e:
            return False, f"生成重置令牌失败: {str(e)}", None


class UserManagementService:
    """用户管理服务"""
    
    @staticmethod
    def get_user_profile(user: User) -> Dict:
        """
        获取用户基本信息
        
        Args:
            user: 用户对象
            
        Returns:
            用户信息字典
        """
        return {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'phone': user.phone,
            'real_name': user.real_name,
            'is_verified': user.is_verified,
            'date_joined': user.date_joined,
            'last_login': user.last_login,
        }
    
    @staticmethod
    def update_user_profile(
        user: User,
        email: Optional[str] = None,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        phone: Optional[str] = None,
        real_name: Optional[str] = None
    ) -> Tuple[bool, str, Optional[User]]:
        """
        更新用户信息
        
        Args:
            user: 用户对象
            email: 邮箱
            first_name: 名
            last_name: 姓
            phone: 手机号
            real_name: 真实姓名
            
        Returns:
            Tuple[是否成功, 消息, 更新后的用户对象]
        """
        try:
            update_fields = []
            
            # 检查邮箱是否被其他用户使用
            if email and email != user.email:
                if User.objects.filter(email=email).exclude(id=user.id).exists():
                    return False, "邮箱已被其他用户使用", None
                user.email = email
                update_fields.append('email')
            
            # 检查手机号是否被其他用户使用
            if phone and phone != user.phone:
                if User.objects.filter(phone=phone).exclude(id=user.id).exists():
                    return False, "手机号已被其他用户使用", None
                user.phone = phone
                update_fields.append('phone')
            
            # 更新其他字段
            if first_name is not None:
                user.first_name = first_name
                update_fields.append('first_name')
            
            if last_name is not None:
                user.last_name = last_name
                update_fields.append('last_name')
            
            if real_name is not None:
                user.real_name = real_name
                update_fields.append('real_name')
            
            if update_fields:
                update_fields.append('updated_at')
                user.save(update_fields=update_fields)
            
            return True, "信息更新成功", user
            
        except Exception as e:
            return False, f"信息更新失败: {str(e)}", None
    
    @staticmethod
    def get_user_stats() -> Dict:
        """
        获取用户统计信息
        
        Returns:
            统计信息字典
        """
        try:
            # 基础统计
            total_users = User.objects.count()
            active_users = User.objects.filter(is_active=True).count()
            verified_users = User.objects.filter(is_verified=True).count()
            
            # 资金统计
            balance_stats = User.objects.aggregate(
                total_balance_sum=Sum('total_balance'),
                avg_balance=Avg('total_balance')
            )
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'verified_users': verified_users,
                'total_balance_sum': balance_stats['total_balance_sum'] or Decimal('0.00'),
                'avg_balance_per_user': balance_stats['avg_balance'] or Decimal('0.00'),
            }
            
        except Exception as e:
            return {
                'total_users': 0,
                'active_users': 0,
                'verified_users': 0,
                'total_balance_sum': Decimal('0.00'),
                'avg_balance_per_user': Decimal('0.00'),
                'error': str(e)
            }


class BalanceService:
    """资金管理服务"""
    
    @staticmethod
    def get_user_balance(user: User) -> Dict:
        """
        获取用户资金信息
        
        Args:
            user: 用户对象
            
        Returns:
            资金信息字典
        """
        user.refresh_from_db()
        return {
            'total_balance': user.total_balance,
            'available_balance': user.available_balance,
            'frozen_balance': user.frozen_balance,
            'updated_at': user.updated_at.isoformat()
        }
    
    @staticmethod
    def update_balance(
        user: User,
        amount: Decimal,
        transaction_type: str,
        description: str = None
    ) -> Tuple[bool, str]:
        """
        更新用户资金
        
        Args:
            user: 用户对象
            amount: 变动金额
            transaction_type: 交易类型
            description: 变动说明
            
        Returns:
            Tuple[是否成功, 消息]
        """
        try:
            with transaction.atomic():
                # 刷新用户数据
                user.refresh_from_db()
                
                if transaction_type == 'deposit':
                    # 存款
                    user.available_balance += amount
                    user.total_balance += amount
                    
                elif transaction_type == 'withdraw':
                    # 取款
                    if user.available_balance < amount:
                        return False, "可用资金不足"
                    user.available_balance -= amount
                    user.total_balance -= amount
                    
                elif transaction_type == 'freeze':
                    # 冻结资金
                    if user.available_balance < amount:
                        return False, "可用资金不足"
                    user.available_balance -= amount
                    user.frozen_balance += amount
                    
                elif transaction_type == 'unfreeze':
                    # 解冻资金
                    if user.frozen_balance < amount:
                        return False, "冻结资金不足"
                    user.frozen_balance -= amount
                    user.available_balance += amount
                    
                elif transaction_type == 'trade':
                    # 交易相关资金变动
                    if amount < 0 and user.available_balance < abs(amount):
                        return False, "可用资金不足"
                    user.available_balance += amount
                    user.total_balance += amount
                
                else:
                    return False, f"不支持的交易类型: {transaction_type}"
                
                user.save(update_fields=[
                    'total_balance', 'available_balance', 'frozen_balance', 'updated_at'
                ])
                
                # 这里可以记录资金变动历史（需要额外的模型）
                
                return True, "资金更新成功"
                
        except Exception as e:
            return False, f"资金更新失败: {str(e)}"
    
    @staticmethod
    def transfer_funds(
        from_user: User,
        to_user: User,
        amount: Decimal,
        description: str = None
    ) -> Tuple[bool, str]:
        """
        用户间转账
        
        Args:
            from_user: 转出用户
            to_user: 转入用户
            amount: 转账金额
            description: 转账说明
            
        Returns:
            Tuple[是否成功, 消息]
        """
        try:
            if amount <= 0:
                return False, "转账金额必须大于0"
            
            with transaction.atomic():
                # 刷新用户数据
                from_user.refresh_from_db()
                to_user.refresh_from_db()
                
                # 检查转出用户资金
                if from_user.available_balance < amount:
                    return False, "转出用户可用资金不足"
                
                # 执行转账
                from_user.available_balance -= amount
                from_user.total_balance -= amount
                
                to_user.available_balance += amount
                to_user.total_balance += amount
                
                # 保存更改
                from_user.save(update_fields=[
                    'total_balance', 'available_balance', 'updated_at'
                ])
                to_user.save(update_fields=[
                    'total_balance', 'available_balance', 'updated_at'
                ])
                
                return True, "转账成功"
                
        except Exception as e:
            return False, f"转账失败: {str(e)}"


class CommissionService:
    """佣金方案服务"""
    
    @staticmethod
    def create_default_commission_scheme(user: User) -> CommissionPlan:
        """
        为用户创建默认佣金方案
        
        Args:
            user: 用户对象
            
        Returns:
            创建的佣金方案
        """
        return CommissionPlan.objects.create(
            plan_name="默认方案",
            user=user,
            rate=Decimal("0.0003"),  # 万3
            min_commission=Decimal("5.00"),      # 最低5元
            transfer_fee_rate=Decimal("0.00002"), # 过户费
            stamp_tax_rate=Decimal("0.001"),     # 印花税
            is_active=True
        )
    
    @staticmethod
    def get_user_commission_schemes(user: User) -> List[CommissionPlan]:
        """
        获取用户的佣金方案列表
        
        Args:
            user: 用户对象
            
        Returns:
            佣金方案列表
        """
        return list(CommissionPlan.objects.filter(user=user).order_by('-created_at'))
    
    @staticmethod
    def create_commission_scheme(
        user: User,
        plan_name: str,
        rate: Decimal,
        min_commission: Decimal,
        transfer_fee_rate: Decimal,
        stamp_tax_rate: Decimal
    ) -> Tuple[bool, str, Optional[CommissionPlan]]:
        """
        创建佣金方案
        
        Args:
            user: 用户对象
            plan_name: 方案名称
            rate: 佣金费率
            min_commission: 最低佣金
            transfer_fee_rate: 过户费费率
            stamp_tax_rate: 印花税费率
            
        Returns:
            Tuple[是否成功, 消息, 佣金方案对象]
        """
        try:
            # 检查方案名称是否重复
            if CommissionPlan.objects.filter(
                user=user, plan_name=plan_name
            ).exists():
                return False, "方案名称已存在", None
            
            scheme = CommissionPlan.objects.create(
                user=user,
                plan_name=plan_name,
                rate=rate,
                min_commission=min_commission,
                transfer_fee_rate=transfer_fee_rate,
                stamp_tax_rate=stamp_tax_rate,
                is_active=True
            )
            
            return True, "佣金方案创建成功", scheme
            
        except Exception as e:
            return False, f"佣金方案创建失败: {str(e)}", None
    
    @staticmethod
    def calculate_trading_fees(
        amount: Decimal,
        trade_type: str,
        commission_scheme: CommissionPlan
    ) -> Dict:
        """
        计算交易费用
        
        Args:
            amount: 交易金额
            trade_type: 交易类型 (buy/sell)
            commission_scheme: 佣金方案
            
        Returns:
            费用详情字典
        """
        try:
            # 计算佣金
            commission = commission_scheme.calculate_commission(amount)
            
            # 计算过户费
            transfer_fee = commission_scheme.calculate_transfer_fee(amount)
            
            # 计算印花税（仅卖出时收取）
            stamp_tax = Decimal('0.00')
            if trade_type == 'sell':
                stamp_tax = commission_scheme.calculate_stamp_tax(amount)
            
            # 总费用
            total_fee = commission + transfer_fee + stamp_tax
            
            # 净额
            if trade_type == 'buy':
                net_amount = amount + total_fee  # 买入时加上费用
            else:
                net_amount = amount - total_fee  # 卖出时减去费用
            
            return {
                'amount': amount,
                'commission': commission,
                'transfer_fee': transfer_fee,
                'stamp_tax': stamp_tax,
                'total_fee': total_fee,
                'net_amount': net_amount,
                'plan_name': commission_scheme.plan_name
            }
            
        except Exception as e:
            return {
                'error': f"费用计算失败: {str(e)}"
            }
    
    @staticmethod
    def get_or_create_default_scheme(user: User) -> CommissionPlan:
        """
        获取或创建用户的默认佣金方案
        
        Args:
            user: 用户对象
            
        Returns:
            佣金方案对象
        """
        scheme = CommissionPlan.objects.filter(
            user=user, is_active=True
        ).first()
        
        if not scheme:
            scheme = CommissionService.create_default_commission_scheme(user)
        
        return scheme 