#!/usr/bin/env python3
"""
基础API测试脚本
测试服务器连通性和基本API功能
"""

import os
import requests
import json
from datetime import datetime, date
from decimal import Decimal
import time

# 配置
BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api"

class APITester:
    def __init__(self):
        self.session = requests.Session()
        self.test_results = []
    
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
        if data:
            print(f"   Data: {json.dumps(data, indent=2, default=str)}")
    
    def test_server_connectivity(self):
        """测试服务器连通性"""
        try:
            response = self.session.get(BASE_URL, timeout=5)
            if response.status_code in [200, 404]:  # 404 is also OK, means server is running
                self.log_result("服务器连通性", True, f"服务器响应状态码: {response.status_code}")
                return True
            else:
                self.log_result("服务器连通性", False, f"服务器响应异常: {response.status_code}")
                return False
        except requests.RequestException as e:
            self.log_result("服务器连通性", False, f"无法连接服务器: {str(e)}")
            return False
    
    def test_api_docs_access(self):
        """测试API文档访问"""
        try:
            response = self.session.get(f"{API_BASE}/docs", timeout=5)
            success = response.status_code == 200
            self.log_result("API文档访问", success, f"状态码: {response.status_code}")
            return success
        except requests.RequestException as e:
            self.log_result("API文档访问", False, f"访问失败: {str(e)}")
            return False
    
    def test_api_schema_access(self):
        """测试API Schema访问"""
        try:
            response = self.session.get(f"{API_BASE}/openapi.json", timeout=5)
            success = response.status_code == 200
            if success:
                schema = response.json()
                self.log_result("API Schema访问", True, 
                              f"Schema版本: {schema.get('openapi', 'unknown')}, 标题: {schema.get('info', {}).get('title', 'unknown')}")
            else:
                self.log_result("API Schema访问", False, f"状态码: {response.status_code}")
            return success
        except requests.RequestException as e:
            self.log_result("API Schema访问", False, f"访问失败: {str(e)}")
            return False
        except json.JSONDecodeError as e:
            self.log_result("API Schema访问", False, f"JSON解析失败: {str(e)}")
            return False
    
    def test_grid_endpoints_without_auth(self):
        """测试网格API端点（无认证）"""
        endpoints = [
            ("GET", "/grid/strategies", "获取策略列表"),
            ("GET", "/grid/plans", "获取计划列表"),
            ("GET", "/grid/dashboard", "获取仪表板"),
            ("GET", "/grid/templates", "获取模板列表"),
        ]
        
        for method, endpoint, description in endpoints:
            try:
                url = f"{API_BASE}{endpoint}"
                if method == "GET":
                    response = self.session.get(url, timeout=5)
                else:
                    response = self.session.request(method, url, timeout=5)
                
                # 401 (未认证) 或 403 (无权限) 也是正常的，说明端点存在但需要认证
                if response.status_code in [200, 401, 403]:
                    self.log_result(f"端点测试: {description}", True, 
                                  f"状态码: {response.status_code} (端点存在)")
                elif response.status_code == 404:
                    self.log_result(f"端点测试: {description}", False, 
                                  f"端点不存在: {response.status_code}")
                else:
                    self.log_result(f"端点测试: {description}", False, 
                                  f"异常状态码: {response.status_code}")
            except requests.RequestException as e:
                self.log_result(f"端点测试: {description}", False, f"请求失败: {str(e)}")
    
    def test_database_connectivity(self):
        """通过API测试数据库连通性"""
        # 尝试访问一个简单的端点来验证数据库连接
        try:
            response = self.session.get(f"{API_BASE}/grid/strategies", timeout=10)
            
            # 如果返回401/403，说明API正常但需要认证
            # 如果返回200，说明一切正常
            # 如果返回500，可能是数据库连接问题
            if response.status_code in [200, 401, 403]:
                self.log_result("数据库连通性", True, 
                              f"API响应正常 (状态码: {response.status_code})")
                return True
            elif response.status_code == 500:
                self.log_result("数据库连通性", False, 
                              "服务器内部错误，可能是数据库连接问题")
                return False
            else:
                self.log_result("数据库连通性", False, 
                              f"异常响应: {response.status_code}")
                return False
        except requests.RequestException as e:
            self.log_result("数据库连通性", False, f"请求失败: {str(e)}")
            return False
    
    def run_basic_tests(self):
        """运行基础测试套件"""
        print("=" * 60)
        print("开始运行基础API测试")
        print("=" * 60)
        
        # 测试顺序很重要
        tests = [
            self.test_server_connectivity,
            self.test_api_docs_access,
            self.test_api_schema_access,
            self.test_database_connectivity,
            self.test_grid_endpoints_without_auth,
        ]
        
        for test_func in tests:
            test_func()
            time.sleep(0.5)  # 短暂延迟避免过快请求
        
        # 汇总结果
        self.print_summary()
    
    def print_summary(self):
        """打印测试结果汇总"""
        print("\n" + "=" * 60)
        print("测试结果汇总")
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
        results_dir = os.path.join(os.path.dirname(__file__), '..', 'results')
        os.makedirs(results_dir, exist_ok=True)
        filename = f"test_results_basic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = os.path.join(results_dir, filename)
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.test_results, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n详细测试结果已保存到: {filepath}")

def main():
    """主函数"""
    tester = APITester()
    tester.run_basic_tests()

if __name__ == "__main__":
    main() 