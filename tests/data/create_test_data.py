#!/usr/bin/env python3
"""
测试数据生成脚本
创建用户、股票、网格策略等测试数据
"""

import os
import sys
import django
from decimal import Decimal
from datetime import datetime, date, timedelta

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trader.settings')
django.setup()

from django.contrib.auth import get_user_model
from django.db import transaction
from accounts.models import CommissionPlan
from stocks.models import Stock, StockPrice
from grid.models import GridStrategy

User = get_user_model()

class TestDataGenerator:
    def __init__(self):
        self.created_objects = {
            'users': [],
            'commission_schemes': [],
            'stocks': [],
            'stock_prices': [],
            'grid_strategies': []
        }
    
    def create_test_users(self):
        """创建测试用户"""
        print("创建测试用户...")
        
        users_data = [
            {
                'username': 'test_trader',
                'email': 'test@example.com',
                'password': 'TestPass123',
                'real_name': '测试交易员',
                'phone': '13800138000',
                'total_balance': Decimal('100000.00'),
                'available_balance': Decimal('50000.00'),
                'frozen_balance': Decimal('0.00'),
                'is_verified': True
            },
            {
                'username': 'demo_user',
                'email': 'demo@example.com',
                'password': 'DemoPass123',
                'real_name': '演示用户',
                'phone': '13800138001',
                'total_balance': Decimal('200000.00'),
                'available_balance': Decimal('100000.00'),
                'frozen_balance': Decimal('0.00'),
                'is_verified': True
            }
        ]
        
        for user_data in users_data:
            password = user_data.pop('password')
            user, created = User.objects.get_or_create(
                username=user_data['username'],
                defaults=user_data
            )
            if created:
                user.set_password(password)
                user.save()
                self.created_objects['users'].append(user)
                print(f"  ✅ 创建用户: {user.username}")
            else:
                print(f"  ⚠️  用户已存在: {user.username}")
    
    def create_commission_schemes(self):
        """创建佣金方案"""
        print("创建佣金方案...")
        
        for user in User.objects.filter(username__in=['test_trader', 'demo_user']):
            scheme, created = CommissionPlan.objects.get_or_create(
                user=user,
                plan_name='默认方案',
                defaults={
                    'rate': Decimal('0.0003'),  # 万三
                    'min_commission': Decimal('5.00'),
                    'transfer_fee_rate': Decimal('0.00002'),
                    'stamp_tax_rate': Decimal('0.001'),
                    'is_active': True
                }
            )
            if created:
                self.created_objects['commission_schemes'].append(scheme)
                print(f"  ✅ 创建佣金方案: {user.username}")
            else:
                print(f"  ⚠️  佣金方案已存在: {user.username}")
    
    def create_test_stocks(self):
        """创建测试股票"""
        print("创建测试股票...")
        
        stocks_data = [
            {
                'symbol': '000001',
                'name': '平安银行',
                'market': 'SZ',
                'category': 'stock',
                'is_active': True,
                'current_price': Decimal('12.50')
            },
            {
                'symbol': '000002',
                'name': '万科A',
                'market': 'SZ',
                'category': 'stock',
                'is_active': True,
                'current_price': Decimal('18.30')
            },
            {
                'symbol': '000858',
                'name': '五粮液',
                'market': 'SZ',
                'category': 'stock',
                'is_active': True,
                'current_price': Decimal('165.80')
            },
            {
                'symbol': '600036',
                'name': '招商银行',
                'market': 'SH',
                'category': 'stock',
                'is_active': True,
                'current_price': Decimal('38.50')
            },
            {
                'symbol': '600519',
                'name': '贵州茅台',
                'market': 'SH',
                'category': 'stock',
                'is_active': True,
                'current_price': Decimal('1850.00')
            }
        ]
        
        for stock_data in stocks_data:
            current_price = stock_data.pop('current_price')
            stock, created = Stock.objects.get_or_create(
                symbol=stock_data['symbol'],
                defaults=stock_data
            )
            if created:
                self.created_objects['stocks'].append(stock)
                print(f"  ✅ 创建股票: {stock.symbol} - {stock.name}")
                
                # 创建历史价格数据
                self.create_stock_prices(stock, current_price)
            else:
                print(f"  ⚠️  股票已存在: {stock.symbol} - {stock.name}")
    
    def create_stock_prices(self, stock, current_price):
        """创建股票历史价格数据"""
        base_price = current_price
        
        # 创建过去30天的价格数据
        for i in range(30, 0, -1):
            trade_date = date.today() - timedelta(days=i)
            
            # 跳过周末
            if trade_date.weekday() >= 5:  # 5=Saturday, 6=Sunday
                continue
            
            # 模拟价格波动 (-3% to +3%)
            import random
            change_percent = (random.random() - 0.5) * 0.06  # -3% to +3%
            price = base_price * (1 + Decimal(str(change_percent)))
            
            # 确保价格合理范围
            price = max(price, base_price * Decimal('0.9'))  # 最低不低于90%
            price = min(price, base_price * Decimal('1.1'))  # 最高不超过110%
            
            stock_price, created = StockPrice.objects.get_or_create(
                stock=stock,
                trade_date=trade_date,
                defaults={
                    'open_price': price,
                    'high_price': price * Decimal('1.02'),
                    'low_price': price * Decimal('0.98'),
                    'close_price': price,
                    'volume': random.randint(100000, 1000000),
                    'amount': price * random.randint(100000, 1000000)
                }
            )
            if created:
                self.created_objects['stock_prices'].append(stock_price)
        
        print(f"    ✅ 创建 {stock.name} 的历史价格数据")
    
    def create_grid_strategies(self):
        """创建网格策略模板"""
        print("创建网格策略模板...")
        
        strategies_data = [
            {
                'name': '保守型网格',
                'version': '2.0',
                'description': '适合低风险投资者的保守网格策略',
                'grid_interval_percent': Decimal('3.0')
            },
            {
                'name': '积极型网格',
                'version': '2.1',
                'description': '适合中等风险投资者的积极网格策略',
                'grid_interval_percent': Decimal('2.0'),
                'keep_profit': True,
                'profit_keep_ratio': Decimal('30.00')
            },
            {
                'name': '激进型网格',
                'version': '2.3',
                'description': '适合高风险投资者的激进网格策略',
                'grid_interval_percent': Decimal('1.5'),
                'multi_grid': True,
                'small_grid_percent': Decimal('1.5'),
                'medium_grid_percent': Decimal('5.0'),
                'large_grid_percent': Decimal('15.0'),
                'small_grid_ratio': Decimal('50.00'),
                'medium_grid_ratio': Decimal('30.00'),
                'large_grid_ratio': Decimal('20.00')
            }
        ]
        
        for strategy_data in strategies_data:
            strategy, created = GridStrategy.objects.get_or_create(
                name=strategy_data['name'],
                version=strategy_data['version'],
                defaults=strategy_data
            )
            if created:
                self.created_objects['grid_strategies'].append(strategy)
                print(f"  ✅ 创建网格策略: {strategy.name} v{strategy.version}")
            else:
                print(f"  ⚠️  网格策略已存在: {strategy.name} v{strategy.version}")
    
    def create_test_data(self):
        """创建所有测试数据"""
        print("=" * 60)
        print("开始创建测试数据")
        print("=" * 60)
        
        try:
            with transaction.atomic():
                self.create_test_users()
                self.create_commission_schemes()
                self.create_test_stocks()
                self.create_grid_strategies()
                
                print("\n" + "=" * 60)
                print("测试数据创建完成")
                print("=" * 60)
                
                # 打印汇总
                total_objects = sum(len(objects) for objects in self.created_objects.values())
                print(f"总共创建了 {total_objects} 个对象:")
                for category, objects in self.created_objects.items():
                    if objects:
                        print(f"  - {category}: {len(objects)} 个")
                
                print("\n测试账户信息:")
                for user in User.objects.filter(username__in=['test_trader', 'demo_user']):
                    print(f"  用户名: {user.username}")
                    print(f"  密码: TestPass123 或 DemoPass123")
                    print(f"  邮箱: {user.email}")
                    print(f"  总资产: ¥{user.total_balance}")
                    print(f"  可用资金: ¥{user.available_balance}")
                    print()
                
        except Exception as e:
            print(f"❌ 创建测试数据失败: {str(e)}")
            raise
    
    def cleanup_test_data(self):
        """清理测试数据"""
        print("清理测试数据...")
        
        # 按照依赖关系逆序删除
        StockPrice.objects.filter(stock__symbol__in=['000001', '000002', '000858', '600036', '600519']).delete()
        Stock.objects.filter(symbol__in=['000001', '000002', '000858', '600036', '600519']).delete()
        CommissionPlan.objects.filter(user__username__in=['test_trader', 'demo_user']).delete()
        User.objects.filter(username__in=['test_trader', 'demo_user']).delete()
        GridStrategy.objects.filter(name__in=['保守型网格', '积极型网格', '激进型网格']).delete()
        
        print("测试数据已清理")

def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='测试数据管理工具')
    parser.add_argument('--cleanup', action='store_true', help='清理测试数据')
    parser.add_argument('--create', action='store_true', help='创建测试数据')
    
    args = parser.parse_args()
    
    generator = TestDataGenerator()
    
    if args.cleanup:
        generator.cleanup_test_data()
    elif args.create:
        generator.create_test_data()
    else:
        # 默认创建测试数据
        generator.create_test_data()

if __name__ == "__main__":
    main() 