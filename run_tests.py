#!/usr/bin/env python3
"""
网格交易系统测试运行脚本
提供统一的测试入口和管理功能
"""

import os
import sys
import subprocess
import argparse
from datetime import datetime

def run_command(command, description=""):
    """运行命令并显示结果"""
    print(f"\n{'='*60}")
    print(f"🚀 {description}")
    print(f"命令: {command}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(command, shell=True, capture_output=False, text=True)
        if result.returncode == 0:
            print(f"✅ {description} - 执行成功")
        else:
            print(f"❌ {description} - 执行失败 (退出码: {result.returncode})")
        return result.returncode == 0
    except Exception as e:
        print(f"❌ {description} - 执行异常: {e}")
        return False

def run_api_basic():
    """运行API基础测试"""
    return run_command(
        "python tests/api/test_api_basic.py",
        "API基础连通性测试"
    )

def run_api_complete():
    """运行完整API测试"""
    return run_command(
        "python tests/api/test_api_complete.py", 
        "完整API功能测试"
    )

def run_db_simple():
    """运行简单数据库测试"""
    return run_command(
        "python tests/integration/test_db_simple.py",
        "简单数据库功能测试"
    )

def run_db_complete():
    """运行完整数据库测试"""
    return run_command(
        "python tests/integration/test_database_functions.py",
        "完整数据库功能测试"
    )

def create_test_data():
    """生成测试数据"""
    return run_command(
        "python tests/data/create_test_data.py",
        "生成测试数据"
    )

def run_all_tests():
    """运行所有测试"""
    print(f"\n🎯 开始运行所有测试 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success_count = 0
    total_tests = 5
    
    # 1. 创建测试数据
    if create_test_data():
        success_count += 1
    
    # 2. API基础测试
    if run_api_basic():
        success_count += 1
    
    # 3. 数据库简单测试
    if run_db_simple():
        success_count += 1
    
    # 4. 数据库完整测试
    if run_db_complete():
        success_count += 1
    
    # 5. API完整测试
    if run_api_complete():
        success_count += 1
    
    # 测试总结
    print(f"\n{'='*60}")
    print(f"📊 测试总结")
    print(f"{'='*60}")
    print(f"总测试数: {total_tests}")
    print(f"成功: {success_count}")
    print(f"失败: {total_tests - success_count}")
    print(f"成功率: {success_count/total_tests*100:.1f}%")
    
    if success_count == total_tests:
        print("🎉 所有测试通过！")
    else:
        print("⚠️  部分测试失败，请查看上面的详细信息")

def main():
    parser = argparse.ArgumentParser(description="网格交易系统测试运行器")
    parser.add_argument('--api-basic', action='store_true', help='运行API基础测试')
    parser.add_argument('--api-complete', action='store_true', help='运行完整API测试')
    parser.add_argument('--db-simple', action='store_true', help='运行简单数据库测试')
    parser.add_argument('--db-complete', action='store_true', help='运行完整数据库测试')
    parser.add_argument('--create-data', action='store_true', help='生成测试数据')
    parser.add_argument('--all', action='store_true', help='运行所有测试')
    
    args = parser.parse_args()
    
    # 检查Django服务器是否运行
    print("检查Django开发服务器...")
    server_check = run_command(
        "curl -s http://localhost:8000/api/docs > /dev/null",
        "检查服务器连通性"
    )
    
    if not server_check:
        print("⚠️  Django开发服务器可能未启动")
        print("请先运行: python manage.py runserver")
        if not input("是否继续运行测试？(y/N): ").lower().startswith('y'):
            return
    
    # 根据参数运行对应测试
    if args.all:
        run_all_tests()
    elif args.api_basic:
        run_api_basic()
    elif args.api_complete:
        run_api_complete()
    elif args.db_simple:
        run_db_simple()
    elif args.db_complete:
        run_db_complete()
    elif args.create_data:
        create_test_data()
    else:
        # 没有指定参数，显示菜单
        print("\n🧪 网格交易系统测试运行器")
        print("="*40)
        print("1. 生成测试数据")
        print("2. API基础测试")
        print("3. 简单数据库测试")
        print("4. 完整数据库测试")
        print("5. 完整API测试")
        print("6. 运行所有测试")
        print("0. 退出")
        
        while True:
            try:
                choice = input("\n请选择 (0-6): ").strip()
                if choice == '0':
                    break
                elif choice == '1':
                    create_test_data()
                elif choice == '2':
                    run_api_basic()
                elif choice == '3':
                    run_db_simple()
                elif choice == '4':
                    run_db_complete()
                elif choice == '5':
                    run_api_complete()
                elif choice == '6':
                    run_all_tests()
                else:
                    print("❌ 无效选择，请输入0-6之间的数字")
            except KeyboardInterrupt:
                print("\n\n👋 测试已取消")
                break

if __name__ == '__main__':
    main() 