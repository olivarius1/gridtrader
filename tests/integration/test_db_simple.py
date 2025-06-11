#!/usr/bin/env python3
import os
import sys
import django
from decimal import Decimal

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "trader.settings")
django.setup()

from django.contrib.auth import get_user_model
from accounts.models import CommissionPlan
from stocks.models import Stock
from grid.models import GridStrategy, GridPlan
from grid.services import GridStrategyService

User = get_user_model()

print("=" * 50)
print("数据库功能测试")
print("=" * 50)

# 检查测试数据
print("检查测试数据...")
user = User.objects.filter(username="test_trader").first()
if user:
    print(f"✅ 找到测试用户: {user.username}")
    print(f"   资产: {user.total_balance}, 可用: {user.available_balance}")
else:
    print("❌ 未找到测试用户")

stock = Stock.objects.first()
if stock:
    print(f"✅ 找到测试股票: {stock.symbol} - {stock.name}")
else:
    print("❌ 未找到测试股票")

strategy = GridStrategy.objects.first()
if strategy:
    print(f"✅ 找到测试策略: {strategy.name} v{strategy.version}")
else:
    print("❌ 未找到测试策略")

# 测试佣金计算
print("\n测试佣金计算...")
if user:
    commission_scheme = CommissionPlan.objects.filter(user=user).first()
    if commission_scheme:
        amount = Decimal("10000.00")
        commission = commission_scheme.calculate_commission(amount)
        transfer_fee = commission_scheme.calculate_transfer_fee(amount)
        stamp_tax = commission_scheme.calculate_stamp_tax(amount)
        print(f"✅ 佣金计算: {amount} 元")
        print(f"   佣金: {commission} 元")
        print(f"   过户费: {transfer_fee} 元")  
        print(f"   印花税: {stamp_tax} 元")
    else:
        print("❌ 未找到佣金方案")

# 测试网格策略创建
print("\n测试网格策略创建...")
try:
    test_strategy = GridStrategy.objects.create(
        name='测试策略',
        version='2.0',
        description='测试创建的策略',
        grid_interval_percent=Decimal('2.0')
    )
    print(f"✅ 创建策略成功: ID {test_strategy.id}")
    
    # 删除测试策略
    test_strategy.delete()
    print("✅ 删除策略成功")
except Exception as e:
    print(f"❌ 策略操作失败: {e}")

# 测试网格计划创建
print("\n测试网格计划创建...")
if user and stock:
    try:
        # 分离策略数据和计划数据
        strategy_data = {
            'name': '测试策略',
            'version': '2.0',
            'description': '测试创建的策略',
            'grid_interval_percent': Decimal('2.0')
        }
        
        plan_data = {
            'plan_name': '测试计划',
            'description': '测试创建的计划',
            'base_price': Decimal('100.00'),
            'base_investment': Decimal('5000.00'),
            'max_investment': Decimal('20000.00')
        }
        
        # 合并数据
        full_data = {**strategy_data, **plan_data}
        
        plan = GridStrategyService.create_grid_plan(
            user=user,
            stock=stock,
            strategy_data=full_data
        )
        print(f"✅ 创建计划成功: ID {plan.id}")
        
        # 测试网格等级计算
        levels = plan.calculate_grid_levels()
        print(f"✅ 计算网格等级: {len(levels)} 个等级")
        
        # 删除测试计划
        plan.delete()
        print("✅ 删除计划成功")
    except Exception as e:
        print(f"❌ 计划操作失败: {e}")

print("\n数据库功能测试完成") 