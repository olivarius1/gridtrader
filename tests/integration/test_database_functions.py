#!/usr/bin/env python3
"""
数据库功能测试脚本
直接测试模型、服务和核心业务逻辑，绕过API认证问题
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
from grid.models import GridStrategy, GridPlan, GridLevel, GridOrder, GridTradePair, GridTemplate
from grid.services import GridStrategyService, GridConfigService, GridTemplateService

User = get_user_model()

class DatabaseFunctionTester:
    def __init__(self):
        self.test_results = []
        self.test_user = None
        self.test_stock = None
        self.test_strategy = None
        self.test_plan = None
    
    def log_result(self, test_name: str, success: bool, message: str = "", details: str = ""):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if details:
            print(f"   详情: {details}")
    
    def test_data_availability(self):
        """测试基础测试数据是否可用"""
        try:
            # 检查测试用户
            self.test_user = User.objects.filter(username='test_trader').first()
            if self.test_user:
                self.log_result("测试用户可用性", True, f"找到测试用户: {self.test_user.username}")
            else:
                self.log_result("测试用户可用性", False, "未找到测试用户")
                return False
            
            # 检查测试股票
            self.test_stock = Stock.objects.first()
            if self.test_stock:
                self.log_result("测试股票可用性", True, f"找到测试股票: {self.test_stock.symbol}")
            else:
                self.log_result("测试股票可用性", False, "未找到测试股票")
                return False
            
            # 检查测试策略
            self.test_strategy = GridStrategy.objects.first()
            if self.test_strategy:
                self.log_result("测试策略可用性", True, f"找到测试策略: {self.test_strategy.name}")
            else:
                self.log_result("测试策略可用性", False, "未找到测试策略")
                return False
            
            return True
            
        except Exception as e:
            self.log_result("基础数据检查", False, f"检查异常: {str(e)}")
            return False
    
    def test_grid_strategy_operations(self):
        """测试网格策略操作"""
        try:
            # 创建新策略
            strategy_data = {
                'name': '数据库测试策略',
                'version': '2.1',
                'description': '数据库功能测试创建的策略',
                'grid_interval_percent': Decimal('2.5'),
                'keep_profit': True,
                'profit_keep_ratio': Decimal('25.00')
            }
            
            strategy = GridStrategy.objects.create(**strategy_data)
            self.log_result("创建网格策略", True, f"策略ID: {strategy.id}", f"名称: {strategy.name}")
            
            # 查询策略
            retrieved_strategy = GridStrategy.objects.get(id=strategy.id)
            self.log_result("查询网格策略", True, f"策略名称: {retrieved_strategy.name}")
            
            # 更新策略
            retrieved_strategy.description = "更新后的描述"
            retrieved_strategy.save()
            self.log_result("更新网格策略", True, "策略更新成功")
            
            # 删除策略
            strategy.delete()
            self.log_result("删除网格策略", True, "策略删除成功")
            
            return True
            
        except Exception as e:
            self.log_result("网格策略操作", False, f"操作异常: {str(e)}")
            return False
    
    def test_grid_plan_creation(self):
        """测试网格计划创建"""
        try:
            # 使用GridStrategyService创建网格计划
            strategy_data = {
                'version': '2.0',
                'grid_interval_percent': Decimal('2.0'),
                'base_price': Decimal('100.00'),
                'base_investment': Decimal('5000.00'),
                'max_investment': Decimal('20000.00'),
                'plan_name': '数据库测试计划',
                'description': '数据库功能测试创建的计划'
            }
            
            self.test_plan = GridStrategyService.create_grid_plan(
                user=self.test_user,
                stock=self.test_stock,
                strategy_data=strategy_data
            )
            
            self.log_result("创建网格计划", True, f"计划ID: {self.test_plan.id}", 
                          f"计划名称: {self.test_plan.plan_name}")
            
            # 验证计划属性
            if self.test_plan.user == self.test_user:
                self.log_result("计划用户关联", True, "用户关联正确")
            else:
                self.log_result("计划用户关联", False, "用户关联错误")
            
            if self.test_plan.stock == self.test_stock:
                self.log_result("计划股票关联", True, "股票关联正确")
            else:
                self.log_result("计划股票关联", False, "股票关联错误")
            
            return True
            
        except Exception as e:
            self.log_result("网格计划创建", False, f"创建异常: {str(e)}")
            return False
    
    def test_grid_levels_calculation(self):
        """测试网格等级计算"""
        try:
            if not self.test_plan:
                self.log_result("网格等级计算", False, "没有可用的测试计划")
                return False
            
            # 计算网格等级
            levels = self.test_plan.calculate_grid_levels()
            
            if levels:
                self.log_result("计算网格等级", True, f"生成了 {len(levels)} 个网格等级")
                
                # 检查等级数据
                for level in levels[:3]:  # 只检查前3个
                    if level['price'] and level['investment_amount']:
                        self.log_result(f"网格等级 {level['grid_index']}", True, 
                                      f"价格: {level['price']}, 投资: {level['investment_amount']}")
                    else:
                        self.log_result(f"网格等级 {level['grid_index']}", False, "等级数据不完整")
                
                return True
            else:
                self.log_result("计算网格等级", False, "未生成网格等级")
                return False
                
        except Exception as e:
            self.log_result("网格等级计算", False, f"计算异常: {str(e)}")
            return False
    
    def test_grid_config_preview(self):
        """测试网格配置预览功能"""
        try:
            config_data = {
                'version': '2.0',
                'base_price': Decimal('100.00'),
                'grid_interval_percent': Decimal('2.0'),
                'base_investment': Decimal('1000.00'),
                'max_investment': Decimal('10000.00'),
                'min_price': Decimal('80.00'),
                'max_price': Decimal('120.00')
            }
            
            preview_result = GridConfigService.preview_grid_config(config_data)
            
            if preview_result:
                self.log_result("网格配置预览", True, "预览生成成功", 
                              f"预览数据包含 {len(preview_result)} 个字段")
                
                # 检查预览结果的关键字段
                expected_fields = ['levels', 'investment_distribution', 'risk_analysis']
                for field in expected_fields:
                    if field in preview_result:
                        self.log_result(f"预览字段 {field}", True, "字段存在")
                    else:
                        self.log_result(f"预览字段 {field}", False, "字段缺失")
                
                return True
            else:
                self.log_result("网格配置预览", False, "预览生成失败")
                return False
                
        except Exception as e:
            self.log_result("网格配置预览", False, f"预览异常: {str(e)}")
            return False
    
    def test_grid_template_operations(self):
        """测试网格模板操作"""
        try:
            # 创建模板
            template_data = {
                'name': '数据库测试模板',
                'description': '数据库功能测试创建的模板',
                'category': 'custom',
                'template_data': {
                    'version': '2.0',
                    'grid_interval_percent': '2.5',
                    'base_investment': '1000.00'
                },
                'user': self.test_user,
                'is_public': False
            }
            
            template = GridTemplate.objects.create(**template_data)
            self.log_result("创建网格模板", True, f"模板ID: {template.id}", f"模板名称: {template.name}")
            
            # 查询模板
            retrieved_template = GridTemplate.objects.get(id=template.id)
            self.log_result("查询网格模板", True, f"模板名称: {retrieved_template.name}")
            
            # 测试模板服务功能
            templates = GridTemplateService.get_user_templates(self.test_user)
            if templates.filter(id=template.id).exists():
                self.log_result("用户模板查询", True, "找到用户创建的模板")
            else:
                self.log_result("用户模板查询", False, "未找到用户创建的模板")
            
            # 删除模板
            template.delete()
            self.log_result("删除网格模板", True, "模板删除成功")
            
            return True
            
        except Exception as e:
            self.log_result("网格模板操作", False, f"操作异常: {str(e)}")
            return False
    
    def test_commission_calculation(self):
        """测试佣金计算功能"""
        try:
            # 获取用户的佣金方案
            commission_scheme = CommissionPlan.objects.filter(user=self.test_user).first()
            
            if commission_scheme:
                # 测试佣金计算
                amount = Decimal('10000.00')
                commission = commission_scheme.calculate_commission(amount)
                transfer_fee = commission_scheme.calculate_transfer_fee(amount)
                stamp_tax = commission_scheme.calculate_stamp_tax(amount)
                
                self.log_result("佣金计算", True, f"佣金: {commission}")
                self.log_result("过户费计算", True, f"过户费: {transfer_fee}")
                self.log_result("印花税计算", True, f"印花税: {stamp_tax}")
                
                # 验证计算结果合理性
                if commission >= commission_scheme.min_commission:
                    self.log_result("佣金最低限制", True, "佣金计算符合最低限制")
                else:
                    self.log_result("佣金最低限制", False, "佣金计算低于最低限制")
                
                return True
            else:
                self.log_result("佣金方案查询", False, "未找到用户佣金方案")
                return False
                
        except Exception as e:
            self.log_result("佣金计算功能", False, f"计算异常: {str(e)}")
            return False
    
    def test_stock_operations(self):
        """测试股票数据操作"""
        try:
            # 获取股票价格数据
            prices = StockPrice.objects.filter(stock=self.test_stock).order_by('-trade_date')[:5]
            
            if prices:
                self.log_result("股票价格查询", True, f"找到 {prices.count()} 条价格记录")
                
                # 检查价格数据完整性
                latest_price = prices.first()
                if latest_price.open_price and latest_price.close_price:
                    self.log_result("价格数据完整性", True, 
                                  f"开盘: {latest_price.open_price}, 收盘: {latest_price.close_price}")
                else:
                    self.log_result("价格数据完整性", False, "价格数据不完整")
                
                return True
            else:
                self.log_result("股票价格查询", False, "未找到价格数据")
                return False
                
        except Exception as e:
            self.log_result("股票数据操作", False, f"操作异常: {str(e)}")
            return False
    
    def cleanup_test_data(self):
        """清理测试过程中创建的数据"""
        try:
            # 删除测试计划（如果存在）
            if self.test_plan:
                self.test_plan.delete()
                self.log_result("清理测试计划", True, "测试计划已删除")
            
            # 删除测试创建的策略
            GridStrategy.objects.filter(name='数据库测试策略').delete()
            
            # 删除测试创建的模板
            GridTemplate.objects.filter(name='数据库测试模板').delete()
            
            self.log_result("清理测试数据", True, "清理完成")
            
        except Exception as e:
            self.log_result("清理测试数据", False, f"清理异常: {str(e)}")
    
    def run_all_tests(self):
        """运行所有数据库功能测试"""
        print("=" * 60)
        print("开始运行数据库功能测试")
        print("=" * 60)
        
        test_functions = [
            ("基础数据可用性", self.test_data_availability),
            ("网格策略操作", self.test_grid_strategy_operations),
            ("网格计划创建", self.test_grid_plan_creation),
            ("网格等级计算", self.test_grid_levels_calculation),
            ("网格配置预览", self.test_grid_config_preview),
            ("网格模板操作", self.test_grid_template_operations),
            ("佣金计算功能", self.test_commission_calculation),
            ("股票数据操作", self.test_stock_operations),
        ]
        
        successful_tests = 0
        
        try:
            with transaction.atomic():
                # 设置保存点，以便回滚测试数据
                sid = transaction.savepoint()
                
                for test_name, test_func in test_functions:
                    print(f"\n--- 测试: {test_name} ---")
                    try:
                        if test_func():
                            successful_tests += 1
                            print(f"✅ {test_name} 测试通过")
                        else:
                            print(f"❌ {test_name} 测试失败")
                    except Exception as e:
                        print(f"❌ {test_name} 测试异常: {str(e)}")
                
                # 回滚到保存点，清理测试数据
                transaction.savepoint_rollback(sid)
                print("\n🧹 测试数据已自动清理")
                
        except Exception as e:
            print(f"❌ 测试执行异常: {str(e)}")
        
        # 额外的清理（防止有数据泄露）
        self.cleanup_test_data()
        
        # 打印汇总结果
        self.print_summary()
        print(f"\n测试汇总: {successful_tests}/{len(test_functions)} 个测试通过")
    
    def print_summary(self):
        """打印测试结果汇总"""
        print("\n" + "=" * 60)
        print("数据库功能测试结果汇总")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result["success"])
        failed_tests = total_tests - passed_tests
        
        print(f"总测试数: {total_tests}")
        print(f"通过: {passed_tests}")
        print(f"失败: {failed_tests}")
        print(f"成功率: {passed_tests/total_tests*100:.1f}%")
        
        if failed_tests > 0:
            print("\n失败的测试:")
            for result in self.test_results:
                if not result["success"]:
                    print(f"  - {result['test_name']}: {result['message']}")

def main():
    """主函数"""
    tester = DatabaseFunctionTester()
    tester.run_all_tests()

if __name__ == "__main__":
    main() 