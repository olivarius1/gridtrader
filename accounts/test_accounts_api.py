"""
accounts.test_accounts_api
~~~~~~~~~~~~~~~~~~~~~~~~~

账户模块API测试脚本

该脚本用于验证accounts模块的基本API功能:
- 用户注册
- 用户登录
- 获取用户信息
- 资金管理
- 佣金方案管理

作者: Grid Trading System
创建时间: 2024
"""

import json
import requests
import uuid
from decimal import Decimal


class AccountsAPITest:
    """账户API测试类"""
    
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
        self.session = requests.Session()
        self.user_token = None
        
        # 生成唯一的测试用户信息
        self.test_id = str(uuid.uuid4())[:8]  # 使用UUID前8位作为标识
        self.test_username = f"testuser_{self.test_id}"
        self.test_email = f"test_{self.test_id}@example.com"
        self.test_password = "testpass123"
        self.test_phone = f"138{self.test_id[:8]}"  # 生成唯一手机号
        self.test_real_name = f"测试用户_{self.test_id}"
        
        print(f"🔧 测试配置:")
        print(f"   测试ID: {self.test_id}")
        print(f"   用户名: {self.test_username}")
        print(f"   邮箱: {self.test_email}")
        print(f"   手机号: {self.test_phone}")
        
        # 获取CSRF token
        self._get_csrf_token()
        
    def _get_csrf_token(self):
        """获取CSRF令牌"""
        try:
            # 通过访问主页或任何Django页面获取CSRF token
            response = self.session.get(f"{self.base_url}/admin/login/")
            
            # 从cookies中获取csrf token
            csrf_token = None
            for cookie in self.session.cookies:
                if cookie.name == 'csrftoken':
                    csrf_token = cookie.value
                    break
            
            if csrf_token:
                # 设置header
                self.session.headers.update({
                    'X-CSRFToken': csrf_token,
                    'Referer': self.base_url  # 某些配置需要Referer
                })
                print(f"🔐 CSRF Token获取成功: {csrf_token[:10]}...")
                return True
            else:
                print("⚠️ 未获取到CSRF Token")
                return False
        except Exception as e:
            print(f"⚠️ 获取CSRF Token失败: {str(e)}")
            return False

    def _make_post_request(self, url, data):
        """发送POST请求，自动处理CSRF"""
        headers = {'Content-Type': 'application/json'}
        if 'csrftoken' in self.session.cookies:
            headers['X-CSRFToken'] = self.session.cookies['csrftoken']
        return self.session.post(url, json=data, headers=headers)
        
    def _make_put_request(self, url, data):
        """发送PUT请求，自动处理CSRF"""
        headers = {'Content-Type': 'application/json'}
        if 'csrftoken' in self.session.cookies:
            headers['X-CSRFToken'] = self.session.cookies['csrftoken']
        return self.session.put(url, json=data, headers=headers)
    
    def test_user_registration(self):
        """测试用户注册"""
        print("🧪 测试用户注册...")
        
        url = f"{self.base_url}/api/accounts/auth/register"
        data = {
            "username": self.test_username,
            "email": self.test_email, 
            "password": self.test_password,
            "password_confirm": self.test_password,
            "phone": self.test_phone,
            "real_name": self.test_real_name
        }
        
        try:
            response = self._make_post_request(url, data)
            result = response.json()
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('success'):
                print("✅ 用户注册成功")
                return True
            else:
                print(f"❌ 用户注册失败: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_user_login(self):
        """测试用户登录"""
        print("🧪 测试用户登录...")
        
        url = f"{self.base_url}/api/accounts/auth/login"
        data = {
            "username": self.test_username,
            "password": self.test_password,
            "remember_me": True
        }

        try:
            response = self._make_post_request(url, data)
            result = response.json()
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('success'):
                print("✅ 用户登录成功")
                # 提取用户信息
                if 'user' in result:
                    user_info = result['user']
                    print(f"用户ID: {user_info.get('id')}")
                    print(f"用户名: {user_info.get('username')}")
                return True
            else:
                print(f"❌ 用户登录失败: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_user_profile(self):
        """测试获取用户信息"""
        print("🧪 测试获取用户信息...")
        
        url = f"{self.base_url}/api/accounts/user/profile"
        
        try:
            response = self.session.get(url)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"用户信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print("✅ 获取用户信息成功")
                return True
            else:
                print(f"❌ 获取用户信息失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_user_balance(self):
        """测试获取用户资金信息"""
        print("🧪 测试获取用户资金信息...")
        
        url = f"{self.base_url}/api/accounts/user/balance"
        
        try:
            response = self.session.get(url)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"资金信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print("✅ 获取资金信息成功")
                return True
            else:
                print(f"❌ 获取资金信息失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_balance_update(self):
        """测试资金更新"""
        print("🧪 测试资金更新...")
        
        url = f"{self.base_url}/api/accounts/user/balance/update"
        data = {
            "amount": "1000.00",
            "transaction_type": "deposit",
            "description": f"测试充值_{self.test_id}"
        }
        
        try:
            response = self._make_post_request(url, data)
            result = response.json()
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('success'):
                print("✅ 资金更新成功")
                return True
            else:
                print(f"❌ 资金更新失败: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
            
    def test_create_commission_scheme(self):
        """测试创建佣金方案"""
        print("🧪 测试创建佣金方案...")
        
        url = f"{self.base_url}/api/accounts/user/commission-plans"
        data = {
            "plan_name": f"测试方案_{self.test_id}",
            "rate": "0.0005",
            "min_commission": "5.00",
            "transfer_fee_rate": "0.00002",
            "stamp_tax_rate": "0.001"
        }
        
        try:
            response = self._make_post_request(url, data)
            result = response.json()
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('success'):
                print("✅ 创建佣金方案成功")
                return True
            else:
                print(f"❌ 创建佣金方案失败: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_commission_schemes(self):
        """测试佣金方案管理"""
        print("🧪 测试佣金方案管理...")
        
        # 获取佣金方案列表
        url = f"{self.base_url}/api/accounts/user/commission-plans"
        
        try:
            response = self.session.get(url)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"佣金方案列表: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print("✅ 获取佣金方案列表成功")
                return True
            else:
                print(f"❌ 获取佣金方案列表失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_fee_calculation(self):
        """测试费用计算"""
        print("🧪 测试费用计算...")
        
        url = f"{self.base_url}/api/accounts/user/calculate-fees"
        data = {
            "amount": "10000.00",
            "trade_type": "buy"
        }
        
        try:
            response = self._make_post_request(url, data)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"费用计算结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print("✅ 费用计算成功")
                return True
            else:
                print(f"❌ 费用计算失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_user_logout(self):
        """测试用户登出"""
        print("🧪 测试用户登出...")
        
        url = f"{self.base_url}/api/accounts/user/logout"
        
        try:
            response = self._make_post_request(url, {})
            result = response.json()
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('success'):
                print("✅ 用户登出成功")
                return True
            else:
                print(f"❌ 用户登出失败: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_profile_update(self):
        """测试更新用户信息"""
        print("🧪 测试更新用户信息...")
        
        url = f"{self.base_url}/api/accounts/user/profile"
        data = {
            "first_name": "测试",
            "last_name": "用户",
            "real_name": f"更新的真实姓名_{self.test_id}"
        }
        
        try:
            response = self._make_put_request(url, data)
            result = response.json()
            
            print(f"状态码: {response.status_code}")
            print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")
            
            if result.get('success'):
                print("✅ 更新用户信息成功")
                return True
            else:
                print(f"❌ 更新用户信息失败: {result.get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def test_get_user_me(self):
        """测试获取当前用户完整信息"""
        print("🧪 测试获取当前用户完整信息...")
        
        url = f"{self.base_url}/api/accounts/user/me"
        
        try:
            response = self.session.get(url)
            
            print(f"状态码: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"用户完整信息: {json.dumps(result, indent=2, ensure_ascii=False)}")
                print("✅ 获取用户完整信息成功")
                return True
            else:
                print(f"❌ 获取用户完整信息失败: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ 请求异常: {str(e)}")
            return False
    
    def cleanup_test_user(self):
        """清理测试用户数据（可选）"""
        print("🧹 清理测试数据...")
        # 在实际应用中，可以添加删除测试用户的逻辑
        # 但在开发阶段，保留测试数据有助于调试
        print("✅ 测试数据保留（便于调试）")
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始账户模块API测试")
        print("=" * 60)
        
        test_results = []
        
        # 按顺序执行测试
        tests = [
            ("用户注册", self.test_user_registration),
            ("用户登录", self.test_user_login),
            ("获取用户信息", self.test_user_profile),
            ("更新用户信息", self.test_profile_update),
            ("获取资金信息", self.test_user_balance),
            ("资金更新", self.test_balance_update),
            ("创建佣金方案", self.test_create_commission_scheme),
            ("获取佣金方案列表", self.test_commission_schemes),
            ("费用计算", self.test_fee_calculation),
            ("获取用户完整信息", self.test_get_user_me),
            ("用户登出", self.test_user_logout),
        ]
        
        for test_name, test_func in tests:
            print(f"\n--- {test_name} ---")
            result = test_func()
            test_results.append((test_name, result))
            print("-" * 40)
        
        # 汇总结果
        print("\n" + "=" * 60)
        print("📊 测试结果汇总:")
        
        success_count = 0
        for test_name, result in test_results:
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name}: {status}")
            if result:
                success_count += 1
        
        print(f"\n总计: {success_count}/{len(test_results)} 通过")
        print(f"测试用户: {self.test_username} ({self.test_email})")
        
        if success_count == len(test_results):
            print("🎉 所有测试通过！")
        else:
            print("⚠️ 部分测试失败，请检查相关功能")
        
        # 可选的清理工作
        self.cleanup_test_user()


if __name__ == "__main__":
    # 运行测试
    tester = AccountsAPITest()
    tester.run_all_tests() 