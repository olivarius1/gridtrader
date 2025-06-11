#!/usr/bin/env python3
"""
完整API功能测试脚本
包括认证、CRUD操作和网格策略计算测试
"""

import requests
import json
from datetime import datetime, date
from decimal import Decimal
import time

# 配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

class CompleteAPITester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
        self.auth_token = None
        self.test_user_credentials = {
            'username': 'test_trader',
            'password': 'TestPass123'
        }
    
    def log_result(self, test_name: str, success: bool, message: str = "", data: dict = None):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "success": success,
            "message": message,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }
        self.test_results.append(result)
        
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        if data and success:
            print(f"   数据概要: {self._format_data_summary(data)}")
        elif data and not success:
            print(f"   错误详情: {json.dumps(data, indent=2, ensure_ascii=False, default=str)}")
    
    def _format_data_summary(self, data):
        """格式化数据概要"""
        if isinstance(data, dict):
            if 'id' in data:
                return f"ID: {data['id']}"
            elif 'count' in data:
                return f"数量: {data['count']}"
            else:
                return f"字段数: {len(data)}"
        elif isinstance(data, list):
            return f"列表长度: {len(data)}"
        else:
            return str(data)
    
    def test_django_auth_login(self):
        """测试Django认证登录"""
        # 首先获取CSRF Token
        try:
            # 访问一个需要CSRF的页面来获取token
            response = self.session.get(f"{BASE_URL}/admin/login/")
            if 'csrftoken' in self.session.cookies:
                csrftoken = self.session.cookies['csrftoken']
            else:
                # 尝试从meta标签中提取csrf token
                csrftoken = None
                
            # 尝试通过Django的login API登录
            login_data = {
                'username': self.test_user_credentials['username'],
                'password': self.test_user_credentials['password']
            }
            
            if csrftoken:
                login_data['csrfmiddlewaretoken'] = csrftoken
                self.session.headers.update({'X-CSRFToken': csrftoken})
            
            response = self.session.post(f"{BASE_URL}/admin/login/", data=login_data)
            
            # 检查是否登录成功（通过检查session cookie或重定向）
            if response.status_code in [200, 302] and 'sessionid' in self.session.cookies:
                self.log_result("Django认证登录", True, "成功获取会话认证")
                return True
            else:
                self.log_result("Django认证登录", False, f"登录失败，状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("Django认证登录", False, f"登录异常: {str(e)}")
            return False
    
    def test_grid_strategies_crud(self):
        """测试网格策略CRUD操作"""
        
        # 1. 获取策略列表
        try:
            response = self.session.get(f"{API_BASE}/grid/strategies")
            if response.status_code == 200:
                strategies = response.json()
                self.log_result("获取策略列表", True, f"获取到 {len(strategies)} 个策略", {"count": len(strategies)})
            else:
                self.log_result("获取策略列表", False, f"状态码: {response.status_code}", response.json() if response.status_code != 500 else None)
                return False
        except Exception as e:
            self.log_result("获取策略列表", False, f"请求异常: {str(e)}")
            return False
        
        # 2. 创建新策略
        try:
            new_strategy = {
                "name": "测试策略",
                "version": "2.0",
                "description": "API测试创建的策略",
                "grid_interval_percent": "2.5"
            }
            
            response = self.session.post(f"{API_BASE}/grid/strategies", json=new_strategy)
            if response.status_code == 200:
                created_strategy = response.json()
                strategy_id = created_strategy.get('id')
                self.log_result("创建新策略", True, f"成功创建策略 ID: {strategy_id}", {"id": strategy_id})
                
                # 3. 获取创建的策略详情
                response = self.session.get(f"{API_BASE}/grid/strategies/{strategy_id}")
                if response.status_code == 200:
                    strategy_detail = response.json()
                    self.log_result("获取策略详情", True, f"策略名称: {strategy_detail.get('name')}")
                    
                    # 4. 更新策略
                    update_data = {
                        "name": "测试策略(已更新)",
                        "version": "2.0",
                        "description": "更新后的描述",
                        "grid_interval_percent": "3.0"
                    }
                    
                    response = self.session.put(f"{API_BASE}/grid/strategies/{strategy_id}", json=update_data)
                    if response.status_code == 200:
                        updated_strategy = response.json()
                        self.log_result("更新策略", True, f"新名称: {updated_strategy.get('name')}")
                        
                        # 5. 删除策略
                        response = self.session.delete(f"{API_BASE}/grid/strategies/{strategy_id}")
                        if response.status_code == 200:
                            self.log_result("删除策略", True, "策略删除成功")
                            return True
                        else:
                            self.log_result("删除策略", False, f"状态码: {response.status_code}")
                    else:
                        self.log_result("更新策略", False, f"状态码: {response.status_code}")
                else:
                    self.log_result("获取策略详情", False, f"状态码: {response.status_code}")
            else:
                self.log_result("创建新策略", False, f"状态码: {response.status_code}", response.json() if response.status_code != 500 else None)
                return False
                
        except Exception as e:
            self.log_result("策略CRUD操作", False, f"异常: {str(e)}")
            return False
    
    def test_grid_plans_operations(self):
        """测试网格计划操作"""
        
        # 首先获取可用的策略和股票
        try:
            # 获取策略
            response = self.session.get(f"{API_BASE}/grid/strategies")
            if response.status_code != 200:
                self.log_result("获取策略用于计划测试", False, f"无法获取策略列表: {response.status_code}")
                return False
            
            strategies = response.json()
            if not strategies:
                self.log_result("获取策略用于计划测试", False, "没有可用的策略")
                return False
            
            strategy_id = strategies[0]['id']
            
            # 由于我们没有stocks API，我们需要直接查询数据库中的股票
            # 这里我们假设存在股票数据，使用固定的股票ID
            
            # 创建网格计划
            plan_data = {
                "plan_name": "测试网格计划",
                "description": "API测试创建的网格计划",
                "stock": 1,  # 假设第一个股票的ID是1
                "strategy_data": {
                    "version": "2.0",
                    "grid_interval_percent": "2.0"
                },
                "base_price": "100.00",
                "base_investment": "5000.00",
                "max_investment": "20000.00"
            }
            
            response = self.session.post(f"{API_BASE}/grid/plans", json=plan_data)
            if response.status_code == 200:
                created_plan = response.json()
                plan_id = created_plan.get('id')
                self.log_result("创建网格计划", True, f"计划ID: {plan_id}", {"id": plan_id})
                
                # 获取计划列表
                response = self.session.get(f"{API_BASE}/grid/plans")
                if response.status_code == 200:
                    plans = response.json()
                    self.log_result("获取计划列表", True, f"找到 {len(plans)} 个计划")
                    
                    # 获取计划详情
                    response = self.session.get(f"{API_BASE}/grid/plans/{plan_id}")
                    if response.status_code == 200:
                        plan_detail = response.json()
                        self.log_result("获取计划详情", True, f"计划名称: {plan_detail.get('plan_name')}")
                        
                        # 删除计划
                        response = self.session.delete(f"{API_BASE}/grid/plans/{plan_id}")
                        if response.status_code == 200:
                            self.log_result("删除计划", True, "计划删除成功")
                            return True
                        else:
                            self.log_result("删除计划", False, f"状态码: {response.status_code}")
                    else:
                        self.log_result("获取计划详情", False, f"状态码: {response.status_code}")
                else:
                    self.log_result("获取计划列表", False, f"状态码: {response.status_code}")
            else:
                error_detail = None
                try:
                    error_detail = response.json()
                except:
                    error_detail = response.text
                self.log_result("创建网格计划", False, f"状态码: {response.status_code}", error_detail)
                return False
                
        except Exception as e:
            self.log_result("网格计划操作", False, f"异常: {str(e)}")
            return False
    
    def test_grid_config_preview(self):
        """测试网格配置预览功能"""
        try:
            preview_data = {
                "version": "2.0",
                "base_price": "100.00",
                "grid_interval_percent": "2.0",
                "base_investment": "1000.00",
                "max_investment": "10000.00",
                "min_price": "80.00",
                "max_price": "120.00"
            }
            
            response = self.session.post(f"{API_BASE}/grid/config/preview", json=preview_data)
            if response.status_code == 200:
                preview_result = response.json()
                self.log_result("网格配置预览", True, f"生成了网格配置预览", preview_result)
                return True
            else:
                self.log_result("网格配置预览", False, f"状态码: {response.status_code}", response.json() if response.status_code != 500 else None)
                return False
                
        except Exception as e:
            self.log_result("网格配置预览", False, f"异常: {str(e)}")
            return False
    
    def test_grid_dashboard(self):
        """测试网格仪表板"""
        try:
            # 测试基础仪表板
            response = self.session.get(f"{API_BASE}/grid/dashboard")
            if response.status_code == 200:
                dashboard_data = response.json()
                self.log_result("基础仪表板", True, "获取仪表板数据成功", {"fields": len(dashboard_data)})
                
                # 测试增强仪表板
                response = self.session.get(f"{API_BASE}/grid/dashboard?enhanced=true")
                if response.status_code == 200:
                    enhanced_data = response.json()
                    self.log_result("增强仪表板", True, "获取增强仪表板数据成功", {"fields": len(enhanced_data)})
                    return True
                else:
                    self.log_result("增强仪表板", False, f"状态码: {response.status_code}")
            else:
                self.log_result("基础仪表板", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("仪表板测试", False, f"异常: {str(e)}")
            return False
    
    def test_grid_templates(self):
        """测试网格模板功能"""
        try:
            # 获取模板列表
            response = self.session.get(f"{API_BASE}/grid/templates")
            if response.status_code == 200:
                templates = response.json()
                self.log_result("获取模板列表", True, f"找到 {len(templates)} 个模板")
                
                # 创建新模板
                template_data = {
                    "name": "测试模板",
                    "description": "API测试创建的模板",
                    "category": "custom",
                    "template_data": {
                        "version": "2.0",
                        "grid_interval_percent": "2.5",
                        "base_investment": "1000.00"
                    }
                }
                
                response = self.session.post(f"{API_BASE}/grid/templates", json=template_data)
                if response.status_code == 200:
                    created_template = response.json()
                    template_id = created_template.get('id')
                    self.log_result("创建模板", True, f"模板ID: {template_id}")
                    
                    # 获取模板详情
                    response = self.session.get(f"{API_BASE}/grid/templates/{template_id}")
                    if response.status_code == 200:
                        template_detail = response.json()
                        self.log_result("获取模板详情", True, f"模板名称: {template_detail.get('name')}")
                        
                        # 删除模板
                        response = self.session.delete(f"{API_BASE}/grid/templates/{template_id}")
                        if response.status_code == 200:
                            self.log_result("删除模板", True, "模板删除成功")
                            return True
                        else:
                            self.log_result("删除模板", False, f"状态码: {response.status_code}")
                    else:
                        self.log_result("获取模板详情", False, f"状态码: {response.status_code}")
                else:
                    self.log_result("创建模板", False, f"状态码: {response.status_code}", response.json() if response.status_code != 500 else None)
            else:
                self.log_result("获取模板列表", False, f"状态码: {response.status_code}")
                return False
                
        except Exception as e:
            self.log_result("模板功能测试", False, f"异常: {str(e)}")
            return False
    
    def run_complete_tests(self):
        """运行完整测试套件"""
        print("=" * 60)
        print("开始运行完整API功能测试")
        print("=" * 60)
        
        # 测试步骤
        test_steps = [
            ("认证登录", self.test_django_auth_login),
            ("网格策略CRUD", self.test_grid_strategies_crud),
            ("网格计划操作", self.test_grid_plans_operations),
            ("配置预览功能", self.test_grid_config_preview),
            ("仪表板功能", self.test_grid_dashboard),
            ("模板管理功能", self.test_grid_templates),
        ]
        
        successful_tests = 0
        for step_name, test_func in test_steps:
            print(f"\n--- 测试阶段: {step_name} ---")
            try:
                if test_func():
                    successful_tests += 1
                    print(f"✅ {step_name} 测试通过")
                else:
                    print(f"❌ {step_name} 测试失败")
            except Exception as e:
                print(f"❌ {step_name} 测试异常: {str(e)}")
            
            time.sleep(1)  # 短暂延迟
        
        # 打印汇总结果
        self.print_summary()
        
        print(f"\n测试阶段汇总: {successful_tests}/{len(test_steps)} 个阶段通过")
    
    def print_summary(self):
        """打印测试结果汇总"""
        print("\n" + "=" * 60)
        print("详细测试结果汇总")
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
        
        # 保存详细结果到文件
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"test_results_complete_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n详细测试结果已保存到: {filename}")

def main():
    """主函数"""
    tester = CompleteAPITester()
    tester.run_complete_tests()

if __name__ == "__main__":
    main() 