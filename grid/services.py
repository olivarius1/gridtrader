from decimal import Decimal
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime, date, timedelta
from django.db import transaction
from django.utils import timezone
from django.db.models import Sum, Q

from .models import (
    GridStrategy, GridPlan, GridLevel, GridOrder, 
    GridTradePair, GridPerformanceSnapshot
)


class GridStrategyService:
    """网格策略服务 - 实现网格交易的核心业务逻辑"""
    
    @staticmethod
    def create_grid_plan(user, stock, strategy_data: Dict) -> GridPlan:
        """创建网格交易计划"""
        with transaction.atomic():
            # 分离策略参数和计划参数
            strategy_fields = {
                'name', 'description', 'version', 'grid_interval_percent',
                'keep_profit', 'profit_keep_ratio', 'progressive_investment',
                'investment_increase_percent', 'start_increase_from_grid',
                'multi_grid', 'small_grid_percent', 'medium_grid_percent',
                'large_grid_percent', 'small_grid_ratio', 'medium_grid_ratio',
                'large_grid_ratio'
            }
            
            plan_fields = {
                'plan_name', 'description', 'base_price', 'min_price', 'max_price',
                'max_drawdown_percent', 'base_investment', 'max_investment',
                'status', 'total_profit', 'realized_profit', 'kept_profit_shares',
                'total_trades', 'buy_trades', 'sell_trades', 'total_invested',
                'available_funds'
            }
            
            # 提取策略数据
            strategy_params = {k: v for k, v in strategy_data.items() if k in strategy_fields}
            
            # 提取计划数据
            plan_params = {k: v for k, v in strategy_data.items() if k in plan_fields}
            
            # 创建策略
            strategy = GridStrategy.objects.create(**strategy_params)
            
            # 创建网格计划
            grid_plan = GridPlan.objects.create(
                user=user,
                stock=stock,
                strategy=strategy,
                **plan_params
            )
            
            # 生成网格等级
            levels = grid_plan.calculate_grid_levels()
            grid_levels = []
            for level_data in levels:
                grid_levels.append(GridLevel(
                    grid_plan=grid_plan,
                    price=level_data['price'],
                    investment_amount=level_data['investment_amount'],
                    grid_type=level_data['grid_type'],
                    grid_index=level_data.get('grid_index', 0),
                    sell_price=level_data.get('sell_price')
                ))
            
            GridLevel.objects.bulk_create(grid_levels)
            
            return grid_plan
    
    @staticmethod
    def execute_pressure_test(grid_plan: GridPlan) -> Dict:
        """执行压力测试"""
        base_price = grid_plan.base_price
        max_drawdown = grid_plan.max_drawdown_percent / 100
        stress_price = base_price * (1 - max_drawdown)
        
        # 计算在压力测试价格下需要的资金
        levels = grid_plan.calculate_grid_levels()
        total_investment = Decimal('0.00')
        buy_levels = []
        
        for level in levels:
            if level['price'] >= stress_price:
                buy_levels.append(level)
                total_investment += level['investment_amount']
        
        return {
            'stress_price': stress_price,
            'total_investment_needed': total_investment,
            'available_funds': grid_plan.max_investment,
            'is_feasible': total_investment <= grid_plan.max_investment,
            'fund_utilization_rate': (total_investment / grid_plan.max_investment * 100) if grid_plan.max_investment > 0 else 0,
            'buy_levels_count': len(buy_levels),
            'buy_levels': buy_levels
        }
    
    @staticmethod
    def trigger_grid_level(grid_plan: GridPlan, current_price: Decimal) -> List[GridOrder]:
        """触发网格等级，生成订单"""
        triggered_orders = []
        
        # 找到需要触发的网格等级
        levels_to_trigger = GridLevel.objects.filter(
            grid_plan=grid_plan,
            is_triggered=False,
            price__lte=current_price  # 当前价格达到或低于网格价格时触发买入
        ).order_by('price')
        
        for level in levels_to_trigger:
            order = GridStrategyService._create_buy_order(level, current_price)
            if order:
                triggered_orders.append(order)
                level.is_triggered = True
                level.save()
        
        return triggered_orders
    
    @staticmethod
    def _create_buy_order(grid_level: GridLevel, current_price: Decimal) -> Optional[GridOrder]:
        """创建买入订单"""
        try:
            quantity = grid_level.investment_amount / current_price
            
            order = GridOrder.objects.create(
                grid_plan=grid_level.grid_plan,
                grid_level=grid_level,
                price=current_price,
                quantity=quantity,
                amount=grid_level.investment_amount,
                order_type='buy',
                status='pending'
            )
            
            return order
        except Exception as e:
            # 日志记录
            print(f"创建买入订单失败: {e}")
            return None
    
    @staticmethod
    def process_order_fill(order: GridOrder, filled_price: Decimal, filled_quantity: Decimal) -> Dict:
        """处理订单成交"""
        with transaction.atomic():
            order.filled_price = filled_price
            order.filled_quantity = filled_quantity
            order.filled_amount = filled_price * filled_quantity
            order.status = 'filled'
            order.filled_at = timezone.now()
            order.save()
            
            # 更新计划统计
            grid_plan = order.grid_plan
            grid_plan.total_trades += 1
            if order.order_type == 'buy':
                grid_plan.buy_trades += 1
                grid_plan.total_invested += order.filled_amount
            else:
                grid_plan.sell_trades += 1
            
            grid_plan.save()
            
            result: Dict[str, Any] = {'order': order}
            
            # 如果是买入订单成交，创建对应的卖出订单
            if order.order_type == 'buy':
                sell_order = GridStrategyService._create_sell_order_for_buy(order)
                if sell_order:
                    result['sell_order'] = sell_order
                    
                    # 创建交易对
                    trade_pair = GridTradePair.objects.create(
                        grid_plan=grid_plan,
                        buy_order=order
                    )
                    result['trade_pair'] = trade_pair
            
            # 如果是卖出订单成交，处理利润
            elif order.order_type == 'sell':
                GridStrategyService._process_sell_order_profit(order)
                result.update(GridStrategyService._handle_profit_keeping(order))
            
            return result
    
    @staticmethod
    def _create_sell_order_for_buy(buy_order: GridOrder) -> Optional[GridOrder]:
        """为买入订单创建对应的卖出订单"""
        try:
            grid_plan = buy_order.grid_plan
            strategy = grid_plan.strategy
            
            # 根据策略版本计算卖出价格
            if strategy.multi_grid and buy_order.grid_level:
                # 多重网格策略
                sell_price = buy_order.grid_level.sell_price
            else:
                # 单一网格策略
                grid_percent = strategy.grid_interval_percent / 100
                sell_price = buy_order.filled_price * (1 + grid_percent)
            
            sell_order = GridOrder.objects.create(
                grid_plan=grid_plan,
                grid_level=buy_order.grid_level,
                price=sell_price,
                quantity=buy_order.filled_quantity,
                amount=sell_price * buy_order.filled_quantity,
                order_type='sell',
                status='pending'
            )
            
            return sell_order
        except Exception as e:
            print(f"创建卖出订单失败: {e}")
            return None
    
    @staticmethod
    def _process_sell_order_profit(sell_order: GridOrder):
        """处理卖出订单的利润"""
        try:
            # 找到对应的交易对
            trade_pair = GridTradePair.objects.filter(
                buy_order__grid_level=sell_order.grid_level,
                sell_order__isnull=True,
                is_completed=False
            ).first()
            
            if trade_pair:
                trade_pair.sell_order = sell_order
                trade_pair.calculate_profit()
                trade_pair.is_completed = True
                trade_pair.completed_at = timezone.now()
                trade_pair.save()
                
                # 更新计划总利润
                grid_plan = sell_order.grid_plan
                grid_plan.total_profit += trade_pair.profit_amount
                grid_plan.realized_profit += trade_pair.profit_amount
                grid_plan.save()
                
        except Exception as e:
            print(f"处理卖出订单利润失败: {e}")
    
    @staticmethod
    def _handle_profit_keeping(sell_order: GridOrder) -> Dict:
        """处理留利润策略 (2.1)"""
        result = {}
        strategy = sell_order.grid_plan.strategy
        
        if strategy.keep_profit:
            try:
                # 找到对应的交易对
                trade_pair = GridTradePair.objects.get(
                    sell_order=sell_order
                )
                
                # 计算保留的利润份额
                profit_amount = trade_pair.profit_amount
                keep_ratio = strategy.profit_keep_ratio / 100
                
                if profit_amount > 0:
                    # 计算保留的份额数量
                    kept_shares = (profit_amount * keep_ratio) / sell_order.filled_price
                    
                    # 更新订单和交易对
                    sell_order.profit_kept_quantity = kept_shares
                    sell_order.save()
                    
                    trade_pair.kept_profit_shares = kept_shares
                    trade_pair.save()
                    
                    # 更新计划统计
                    grid_plan = sell_order.grid_plan
                    grid_plan.kept_profit_shares += kept_shares
                    grid_plan.save()
                    
                    result['kept_profit_shares'] = kept_shares
                    result['kept_profit_value'] = kept_shares * sell_order.filled_price
                
            except Exception as e:
                print(f"处理留利润策略失败: {e}")
        
        return result
    
    @staticmethod
    def calculate_plan_performance(grid_plan: GridPlan, current_price: Decimal) -> Dict:
        """计算网格计划性能"""
        # 已完成的交易对统计
        completed_pairs = GridTradePair.objects.filter(
            grid_plan=grid_plan,
            is_completed=True
        )
        
        # 实现利润
        realized_profit = completed_pairs.aggregate(
            total=Sum('profit_amount')
        )['total'] or Decimal('0.00')
        
        # 持仓统计
        filled_buy_orders = GridOrder.objects.filter(
            grid_plan=grid_plan,
            order_type='buy',
            status='filled'
        )
        
        total_position = Decimal('0.0000')
        total_cost = Decimal('0.00')
        
        for order in filled_buy_orders:
            # 检查是否已经卖出
            has_sold = GridTradePair.objects.filter(
                buy_order=order,
                is_completed=True
            ).exists()
            
            if not has_sold:
                total_position += order.filled_quantity
                total_cost += order.filled_amount
        
        # 未实现损益
        unrealized_pnl = Decimal('0.00')
        if total_position > 0:
            current_value = total_position * current_price
            unrealized_pnl = current_value - total_cost
        
        # 保留利润价值
        kept_profit_value = grid_plan.kept_profit_shares * current_price
        
        return {
            'realized_profit': realized_profit,
            'unrealized_pnl': unrealized_pnl,
            'total_profit': realized_profit + unrealized_pnl,
            'total_position': total_position,
            'total_cost': total_cost,
            'current_value': total_position * current_price if total_position > 0 else Decimal('0.00'),
            'kept_profit_shares': grid_plan.kept_profit_shares,
            'kept_profit_value': kept_profit_value,
            'completed_trades': completed_pairs.count(),
            'total_invested': grid_plan.total_invested,
            'available_funds': grid_plan.max_investment - grid_plan.total_invested,
            'fund_utilization': (grid_plan.total_invested / grid_plan.max_investment * 100) if grid_plan.max_investment > 0 else 0
        }
    
    @staticmethod
    def create_performance_snapshot(grid_plan: GridPlan, current_price: Decimal, snapshot_date: date | None = None) -> GridPerformanceSnapshot:
        """创建性能快照"""
        if snapshot_date is None:
            snapshot_date = timezone.now().date()
        
        performance = GridStrategyService.calculate_plan_performance(grid_plan, current_price)
        
        snapshot = GridPerformanceSnapshot.objects.create(
            grid_plan=grid_plan,
            snapshot_date=snapshot_date,
            total_profit=performance['total_profit'],
            realized_profit=performance['realized_profit'],
            unrealized_profit=performance['unrealized_pnl'],
            total_position=performance['total_position'],
            kept_profit_position=performance['kept_profit_shares'],
            total_trades=grid_plan.total_trades,
            completed_pairs=performance['completed_trades'],
            invested_amount=performance['total_invested'],
            available_amount=performance['available_funds'],
            current_price=current_price
        )
        
        return snapshot
    
    @staticmethod
    def get_trading_suggestions(grid_plan: GridPlan, current_price: Decimal) -> Dict:
        """获取交易建议"""
        suggestions = {
            'buy_suggestions': [],
            'sell_suggestions': [],
            'alerts': []
        }
        
        # 检查是否有等级需要触发
        levels_to_buy = GridLevel.objects.filter(
            grid_plan=grid_plan,
            is_triggered=False,
            price__gte=current_price * Decimal('0.98'),  # 2%的缓冲
            price__lte=current_price * Decimal('1.02')
        )
        
        for level in levels_to_buy:
            suggestions['buy_suggestions'].append({
                'level': level,
                'trigger_price': level.price,
                'investment_amount': level.investment_amount,
                'distance_percent': abs((current_price - level.price) / current_price * 100)
            })
        
        # 检查待成交的卖出订单
        pending_sell_orders = GridOrder.objects.filter(
            grid_plan=grid_plan,
            order_type='sell',
            status='pending'
        )
        
        for order in pending_sell_orders:
            distance_percent = (order.price - current_price) / current_price * 100
            suggestions['sell_suggestions'].append({
                'order': order,
                'trigger_price': order.price,
                'potential_profit': order.amount - (order.quantity * current_price),
                'distance_percent': distance_percent
            })
        
        # 风险提醒
        performance = GridStrategyService.calculate_plan_performance(grid_plan, current_price)
        if performance['fund_utilization'] > 80:
            suggestions['alerts'].append({
                'type': 'high_utilization',
                'message': f"资金使用率达到 {performance['fund_utilization']:.1f}%，请注意风险控制"
            })
        
        if current_price < grid_plan.min_price * Decimal('1.1'):
            suggestions['alerts'].append({
                'type': 'approaching_min_price',
                'message': f"价格接近最低设定价格 {grid_plan.min_price}，请关注风险"
            })
        
        return suggestions


class GridAnalyticsService:
    """网格分析服务"""
    
    @staticmethod
    def analyze_strategy_performance(strategy: GridStrategy, days: int = 30) -> Dict:
        """分析策略表现"""
        end_date = timezone.now().date()
        start_date = end_date - timedelta(days=days)
        
        plans = GridPlan.objects.filter(strategy=strategy)
        
        total_profit = Decimal('0.00')
        total_trades = 0
        successful_plans = 0
        
        for plan in plans:
            snapshots = GridPerformanceSnapshot.objects.filter(
                grid_plan=plan,
                snapshot_date__gte=start_date,
                snapshot_date__lte=end_date
            ).order_by('-snapshot_date')
            latest = snapshots.first()
            if latest:
                total_profit += latest.total_profit
                total_trades += latest.total_trades
                if latest.total_profit > 0:
                    successful_plans += 1
        
        return {
            'strategy': strategy,
            'total_plans': plans.count(),
            'successful_plans': successful_plans,
            'success_rate': (successful_plans / plans.count() * 100) if plans.count() > 0 else 0,
            'total_profit': total_profit,
            'average_profit_per_plan': total_profit / plans.count() if plans.count() > 0 else Decimal('0.00'),
            'total_trades': total_trades,
            'average_trades_per_plan': total_trades / plans.count() if plans.count() > 0 else 0
        }
    
    @staticmethod
    def compare_strategies(strategy_ids: List[int], days: int = 30) -> List[Dict]:
        """比较多个策略的表现"""
        strategies = GridStrategy.objects.filter(id__in=strategy_ids)
        results = []
        
        for strategy in strategies:
            performance = GridAnalyticsService.analyze_strategy_performance(strategy, days)
            results.append(performance)
        
        # 按成功率排序
        results.sort(key=lambda x: x['success_rate'], reverse=True)
        
        return results
    
    @staticmethod
    def generate_optimization_suggestions(grid_plan: GridPlan) -> List[Dict]:
        """生成优化建议"""
        suggestions = []
        
        # 分析历史表现
        snapshots = GridPerformanceSnapshot.objects.filter(
            grid_plan=grid_plan
        ).order_by('-snapshot_date')[:30]  # 最近30天
        
        if len(snapshots) < 7:
            return [{'type': 'insufficient_data', 'message': '数据不足，无法生成优化建议'}]
        
        # 分析盈利趋势
        recent_profits = [s.total_profit for s in snapshots[:7]]
        older_profits = [s.total_profit for s in snapshots[7:14]] if len(snapshots) >= 14 else []
        
        if older_profits:
            recent_avg = sum(recent_profits) / len(recent_profits)
            older_avg = sum(older_profits) / len(older_profits)
            
            if recent_avg < older_avg:
                suggestions.append({
                    'type': 'declining_performance',
                    'message': '近期表现下降，建议检查策略参数或市场环境变化',
                    'priority': 'high'
                })
        
        # 分析资金使用效率
        latest = snapshots[0]
        if latest.invested_amount > 0:
            roi = (latest.total_profit / latest.invested_amount * 100)
            if roi < 5:
                suggestions.append({
                    'type': 'low_roi',
                    'message': f'投资回报率较低 ({roi:.1f}%)，建议调整网格间距或选择波动性更大的标的',
                    'priority': 'medium'
                })
        
        # 分析交易频率
        trades_per_week = latest.total_trades / max(len(snapshots), 1) * 7
        if trades_per_week < 2:
            suggestions.append({
                'type': 'low_activity',
                'message': '交易频率较低，建议缩小网格间距或选择波动性更大的标的',
                'priority': 'low'
            })
        elif trades_per_week > 20:
            suggestions.append({
                'type': 'high_activity',
                'message': '交易频率过高，建议扩大网格间距以降低交易成本',
                'priority': 'medium'
            })
        
        return suggestions


class GridConfigService:
    """网格配置服务 - 配置预览、验证和优化"""
    
    @staticmethod
    def preview_grid_config(config_data: Dict) -> Dict:
        """预览网格配置 - 兼容方法名"""
        return GridConfigService.preview_grid_configuration(config_data)
    
    @staticmethod
    def preview_grid_configuration(config_data: Dict) -> Dict:
        """预览网格配置"""
        base_price = config_data['base_price']
        min_price = config_data['min_price']
        max_price = config_data['max_price']
        grid_interval = config_data['grid_interval_percent'] / Decimal('100')
        base_investment = config_data['base_investment']
        strategy_config = config_data.get('strategy_config', {})
        
        # 生成买入网格等级
        buy_levels = []
        current_price = base_price
        level_index = 0
        
        # 向下生成买入等级
        while current_price >= min_price:
            investment_amount = GridConfigService._calculate_investment_for_level(
                level_index, base_investment, strategy_config
            )
            
            level_data = {
                'price': current_price,
                'investment_amount': investment_amount,
                'level_index': level_index,
                'distance_from_base': float((current_price - base_price) / base_price * 100),
                'sell_price': current_price * (Decimal('1') + grid_interval),
                'grid_type': 'single'
            }
            buy_levels.append(level_data)
            
            current_price = current_price * (Decimal('1') - grid_interval)
            level_index += 1
        
        # 生成卖出等级（基准价格以上）
        sell_levels = []
        current_price = base_price * (Decimal('1') + grid_interval)
        level_index = 1
        
        while current_price <= max_price:
            level_data = {
                'price': current_price,
                'investment_amount': Decimal('0.00'),  # 卖出等级不需要投资
                'level_index': level_index,
                'distance_from_base': float((current_price - base_price) / base_price * 100),
                'sell_price': None,
                'grid_type': 'single'
            }
            sell_levels.append(level_data)
            
            current_price = current_price * (Decimal('1') + grid_interval)
            level_index += 1
        
        # 所有等级
        all_levels = buy_levels + sell_levels
        
        # 投资分配分析
        total_buy_investment = sum(Decimal(str(l['investment_amount'])) for l in buy_levels)
        max_investment = config_data['max_investment']
        
        investment_distribution = {
            'total_buy_investment': total_buy_investment,
            'max_investment': max_investment,
            'utilization_rate': float(total_buy_investment / max_investment * 100) if max_investment > 0 else 0,
            'remaining_funds': max_investment - total_buy_investment,
            'buy_levels_count': len(buy_levels)
        }
        
        # 风险分析
        risk_analysis = GridConfigService._analyze_configuration_risk(
            config_data, buy_levels, sell_levels
        )
        
        # 可视化数据
        visual_data = {
            'price_range': {
                'min': float(min_price), 
                'max': float(max_price), 
                'base': float(base_price)
            },
            'grid_lines': [float(l['price']) for l in all_levels],
            'investment_bars': [(float(l['price']), float(l['investment_amount'])) for l in buy_levels],
            'risk_zones': GridConfigService._calculate_risk_zones(config_data)
        }
        
        return {
            'levels': all_levels,
            'total_levels': len(all_levels),
            'buy_levels': buy_levels,
            'sell_levels': sell_levels,
            'investment_distribution': investment_distribution,
            'risk_analysis': risk_analysis,
            'visual_data': visual_data
        }
    
    @staticmethod
    def _calculate_investment_for_level(level_index: int, base_investment: Decimal, strategy_config: Dict) -> Decimal:
        """计算每个等级的投资金额"""
        # 基础投资金额
        investment = base_investment
        
        # 逐格加码策略
        if strategy_config.get('progressive_investment', False):
            start_increase_from = strategy_config.get('start_increase_from_grid', 2)
            increase_percent = strategy_config.get('investment_increase_percent', Decimal('5.00')) / 100
            
            if level_index >= start_increase_from - 1:  # level_index从0开始
                increase_times = level_index - start_increase_from + 1
                # 使用Decimal类型进行计算，避免float类型混合
                multiplier = Decimal('1') + increase_percent
                for _ in range(increase_times):
                    investment = investment * multiplier
        
        return investment.quantize(Decimal('0.01'))
    
    @staticmethod
    def _analyze_configuration_risk(config_data: Dict, buy_levels: List, sell_levels: List) -> Dict:
        """分析配置风险"""
        base_price = config_data['base_price']
        min_price = config_data['min_price']
        max_investment = config_data['max_investment']
        
        # 最大下跌风险
        max_drawdown = (base_price - min_price) / base_price * 100
        
        # 资金压力测试
        stress_levels = [l for l in buy_levels if l['price'] <= min_price * Decimal('1.1')]  # 接近最低价的等级
        stress_investment = sum(Decimal(str(l['investment_amount'])) for l in stress_levels)
        
        # 收益潜力评估
        profit_potential = len(buy_levels) * config_data['grid_interval_percent']
        
        return {
            'max_drawdown_percent': float(max_drawdown),
            'stress_investment_needed': float(stress_investment),
            'stress_fund_ratio': float(stress_investment / max_investment * 100) if max_investment > 0 else 0,
            'profit_potential_percent': float(profit_potential),
            'risk_level': GridConfigService._calculate_risk_level(max_drawdown, stress_investment / max_investment * 100 if max_investment > 0 else 0),
            'recommendations': GridConfigService._generate_risk_recommendations(config_data, buy_levels)
        }
    
    @staticmethod
    def _calculate_risk_zones(config_data: Dict) -> List[Dict]:
        """计算风险区域"""
        base_price = config_data['base_price']
        min_price = config_data['min_price']
        
        zones = []
        
        # 安全区域 (基准价格上下5%)
        zones.append({
            'name': '安全区域',
            'min_price': float(base_price * Decimal('0.95')),
            'max_price': float(base_price * Decimal('1.05')),
            'color': 'green',
            'description': '价格波动较小，风险可控'
        })
        
        # 警戒区域 (下跌5%-20%)
        zones.append({
            'name': '警戒区域', 
            'min_price': float(base_price * Decimal('0.8')),
            'max_price': float(base_price * Decimal('0.95')),
            'color': 'yellow',
            'description': '需要密切关注，准备加仓'
        })
        
        # 危险区域 (下跌20%以上)
        zones.append({
            'name': '危险区域',
            'min_price': float(min_price),
            'max_price': float(base_price * Decimal('0.8')),
            'color': 'red',
            'description': '高风险区域，需要充足资金准备'
        })
        
        return zones
    
    @staticmethod
    def _calculate_risk_level(max_drawdown: float, stress_fund_ratio: float) -> str:
        """计算风险等级"""
        if max_drawdown > 50 or stress_fund_ratio > 80:
            return '高风险'
        elif max_drawdown > 30 or stress_fund_ratio > 60:
            return '中等风险'
        else:
            return '低风险'
    
    @staticmethod
    def _generate_risk_recommendations(config_data: Dict, buy_levels: List) -> List[str]:
        """生成风险建议"""
        recommendations = []
        
        base_price = config_data['base_price']
        min_price = config_data['min_price']
        max_investment = config_data['max_investment']
        
        # 检查下跌幅度
        max_drawdown = (base_price - min_price) / base_price * 100
        if max_drawdown > 50:
            recommendations.append("最大下跌幅度超过50%，建议适当提高最低价格或增加资金")
        
        # 检查资金充足性
        total_investment = sum(Decimal(str(l['investment_amount'])) for l in buy_levels)
        if total_investment > max_investment * Decimal('0.9'):
            recommendations.append("资金利用率过高，建议增加最大投资金额")
        
        # 检查网格密度
        grid_count = len(buy_levels)
        if grid_count > 20:
            recommendations.append("网格等级过多，建议适当增大网格间距")
        elif grid_count < 5:
            recommendations.append("网格等级过少，建议适当减小网格间距")
        
        return recommendations
    
    @staticmethod
    def validate_grid_configuration(config_data: Dict) -> Dict:
        """验证网格配置合理性"""
        errors = []
        warnings = []
        suggestions = []
        
        base_price = config_data['base_price']
        min_price = config_data['min_price']
        max_price = config_data['max_price']
        grid_interval = config_data['grid_interval_percent']
        max_investment = config_data['max_investment']
        
        # 基础验证
        if min_price >= base_price:
            errors.append("最低价格必须小于基准价格")
        
        if max_price <= base_price:
            errors.append("最高价格必须大于基准价格")
        
        # 网格间距验证
        if grid_interval < 1:
            warnings.append("网格间距过小，可能导致频繁交易和高手续费")
        elif grid_interval > 20:
            warnings.append("网格间距过大，可能错失较好的交易机会")
        
        # 价格范围验证
        price_range_ratio = (max_price - min_price) / base_price * 100
        if price_range_ratio > 200:
            warnings.append("价格范围过大，建议缩小范围或增加资金")
        
        # 如果没有严重错误，生成预览并进行进一步验证
        if not errors:
            try:
                preview = GridConfigService.preview_grid_configuration(config_data)
                
                # 资金充足性验证
                utilization_rate = preview['investment_distribution']['utilization_rate']
                if utilization_rate > 95:
                    warnings.append("资金利用率过高，建议增加最大投资金额")
                elif utilization_rate < 50:
                    suggestions.append("资金利用率较低，可以考虑增加网格密度或调整投资策略")
                
                # 风险等级验证
                risk_level = preview['risk_analysis']['risk_level']
                if risk_level == '高风险':
                    warnings.append("当前配置为高风险，请确保有足够的风险承受能力")
                
                # 生成优化建议
                if not warnings:
                    suggestions.extend(GridConfigService._generate_optimization_suggestions(config_data, preview))
                
            except Exception as e:
                errors.append(f"配置验证过程中出现错误: {str(e)}")
        
        # 计算配置评分
        score = GridConfigService._calculate_config_score(config_data, errors, warnings)
        
        return {
            'is_valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions,
            'score': score
        }
    
    @staticmethod
    def _generate_optimization_suggestions(config_data: Dict, preview: Dict) -> List[str]:
        """生成优化建议"""
        suggestions = []
        
        # 基于投资分配的建议
        investment_dist = preview['investment_distribution']
        if investment_dist['utilization_rate'] < 70:
            suggestions.append("可以考虑适当增加网格密度或调整投资金额分配")
        
        # 基于风险分析的建议
        risk_analysis = preview['risk_analysis']
        if risk_analysis['profit_potential_percent'] < 20:
            suggestions.append("当前配置的盈利潜力较低，建议优化网格间距或价格范围")
        
        return suggestions
    
    @staticmethod
    def _calculate_config_score(config_data: Dict, errors: Optional[List] = None, warnings: Optional[List] = None) -> float:
        """计算配置评分 (0-100)"""
        base_score = 100.0
        
        # 错误扣分
        if errors:
            base_score -= len(errors) * 20
        
        # 警告扣分
        if warnings:
            base_score -= len(warnings) * 5
        
        # 配置合理性加分
        base_price = config_data['base_price']
        min_price = config_data['min_price']
        grid_interval = config_data['grid_interval_percent']
        
        # 网格间距合理性
        if 3 <= grid_interval <= 10:
            base_score += 5
        
        # 价格范围合理性
        drawdown = (base_price - min_price) / base_price * 100
        if 20 <= drawdown <= 40:
            base_score += 5
        
        return max(0.0, min(100.0, base_score))


class GridSimulationService:
    """网格模拟服务"""
    
    @staticmethod
    def run_grid_simulation(user, config_data: Dict, simulation_params: Dict) -> str:
        """运行网格策略模拟"""
        import uuid
        
        simulation_id = str(uuid.uuid4())
        
        # 创建模拟记录
        from .models import GridSimulation
        simulation = GridSimulation.objects.create(
            simulation_id=simulation_id,
            user=user,
            config_data=config_data,
            simulation_params=simulation_params,
            simulation_results={},
            performance_metrics={},
            status='running'
        )
        
        try:
            # 生成模拟价格数据
            price_data = GridSimulationService._generate_simulation_price_data(
                base_price=config_data['base_price'],
                days=simulation_params['days'],
                volatility=float(simulation_params['volatility']) / 100,
                trend_direction=simulation_params['trend_direction'],
                trend_strength=float(simulation_params['trend_strength']) / 100
            )
            
            # 运行网格策略模拟
            simulation_results = GridSimulationService._run_strategy_simulation(
                config_data, price_data
            )
            
            # 计算性能指标
            performance_metrics = GridSimulationService._calculate_simulation_metrics(
                simulation_results, price_data, config_data
            )
            
            # 更新模拟记录
            simulation.simulation_results = simulation_results
            simulation.performance_metrics = performance_metrics
            simulation.status = 'completed'
            simulation.completed_at = timezone.now()
            simulation.save()
            
            return simulation_id
            
        except Exception as e:
            simulation.status = 'failed'
            simulation.simulation_results = {'error': str(e)}
            simulation.save()
            raise e
    
    @staticmethod
    def _generate_simulation_price_data(base_price: Decimal, days: int, volatility: float, 
                                      trend_direction: str, trend_strength: float) -> List[Dict]:
        """生成模拟价格数据"""
        import numpy as np
        from datetime import datetime, timedelta
        
        # 设置随机种子确保可重复性
        np.random.seed(42)
        
        # 设置趋势参数
        trend_factor = 0
        if trend_direction == 'up':
            trend_factor = trend_strength / days
        elif trend_direction == 'down':
            trend_factor = -trend_strength / days
        
        prices = []
        current_price = float(base_price)
        start_date = datetime.now().date()
        
        for i in range(days):
            # 随机波动 + 趋势
            daily_change = np.random.normal(trend_factor, volatility)
            current_price *= (1 + daily_change)
            
            # 价格边界限制
            min_price = float(base_price) * 0.2   # 最多跌80%
            max_price = float(base_price) * 5.0   # 最多涨400%
            current_price = max(min_price, min(max_price, current_price))
            
            prices.append({
                'date': (start_date + timedelta(days=i)).isoformat(),
                'price': Decimal(str(round(current_price, 4))),
                'volume': np.random.randint(10000, 100000),
                'high': Decimal(str(round(current_price * (1 + abs(np.random.normal(0, volatility/2))), 4))),
                'low': Decimal(str(round(current_price * (1 - abs(np.random.normal(0, volatility/2))), 4))),
            })
        
        return prices
    
    @staticmethod
    def _run_strategy_simulation(config_data: Dict, price_data: List[Dict]) -> Dict:
        """运行策略模拟"""
        # 初始化模拟状态
        position = Decimal('0')  # 持仓
        cash = config_data['max_investment']  # 现金
        total_trades = 0
        trades = []
        
        # 生成网格等级
        preview = GridConfigService.preview_grid_configuration(config_data)
        buy_levels = {Decimal(str(l['price'])): l for l in preview['buy_levels']}
        sell_levels = {}  # 动态管理卖出等级
        
        grid_interval = config_data['grid_interval_percent'] / 100
        
        for price_point in price_data:
            current_price = price_point['price']
            trade_date = price_point['date']
            
            # 检查买入触发
            triggered_buys = []
            for buy_price, level_info in list(buy_levels.items()):
                if current_price <= buy_price and cash >= Decimal(str(level_info['investment_amount'])):
                    triggered_buys.append((buy_price, level_info))
            
            # 按价格排序，优先执行价格更低的买入
            triggered_buys.sort(key=lambda x: x[0], reverse=True)
            
            for buy_price, level_info in triggered_buys:
                investment_amount = Decimal(str(level_info['investment_amount']))
                quantity = investment_amount / current_price
                
                # 执行买入
                position += quantity
                cash -= investment_amount
                total_trades += 1
                
                # 记录交易
                trade = {
                    'date': trade_date,
                    'type': 'buy',
                    'price': current_price,
                    'quantity': quantity,
                    'amount': investment_amount,
                    'level': level_info['level_index']
                }
                trades.append(trade)
                
                # 设置对应的卖出等级
                sell_price = current_price * (1 + Decimal(str(grid_interval)))
                sell_levels[sell_price] = {
                    'quantity': quantity,
                    'buy_price': current_price,
                    'level_index': level_info['level_index']
                }
                
                # 移除已触发的买入等级
                del buy_levels[buy_price]
            
            # 检查卖出触发
            triggered_sells = []
            for sell_price, sell_info in list(sell_levels.items()):
                if current_price >= sell_price:
                    triggered_sells.append((sell_price, sell_info))
            
            # 按价格排序，优先执行价格更高的卖出
            triggered_sells.sort(key=lambda x: x[0])
            
            for sell_price, sell_info in triggered_sells:
                # 执行卖出
                sell_amount = current_price * sell_info['quantity']
                position -= sell_info['quantity']
                cash += sell_amount
                total_trades += 1
                
                # 计算利润
                cost = sell_info['buy_price'] * sell_info['quantity']
                profit = sell_amount - cost
                
                # 记录交易
                trade = {
                    'date': trade_date,
                    'type': 'sell',
                    'price': current_price,
                    'quantity': sell_info['quantity'],
                    'amount': sell_amount,
                    'profit': profit,
                    'level': sell_info['level_index']
                }
                trades.append(trade)
                
                # 重新添加买入等级
                buy_levels[sell_info['buy_price']] = {
                    'price': sell_info['buy_price'],
                    'investment_amount': cost,
                    'level_index': sell_info['level_index']
                }
                
                # 移除卖出等级
                del sell_levels[sell_price]
        
        # 计算最终状态
        final_price = price_data[-1]['price']
        position_value = position * final_price
        total_value = cash + position_value
        initial_capital = config_data['max_investment']
        
        # 计算已实现和未实现盈亏
        realized_profit = sum(Decimal(str(t.get('profit', 0))) for t in trades if t['type'] == 'sell')
        invested_amount = initial_capital - cash
        unrealized_pnl = position_value - invested_amount if invested_amount > 0 else Decimal('0')
        
        return {
            'trades': trades,
            'total_trades': total_trades,
            'final_position': position,
            'final_cash': cash,
            'position_value': position_value,
            'total_value': total_value,
            'initial_capital': initial_capital,
            'realized_profit': realized_profit,
            'unrealized_pnl': unrealized_pnl,
            'total_return': total_value - initial_capital,
            'roi_percent': float((total_value - initial_capital) / initial_capital * 100),
            'buy_trades': len([t for t in trades if t['type'] == 'buy']),
            'sell_trades': len([t for t in trades if t['type'] == 'sell']),
        }
    
    @staticmethod
    def _calculate_simulation_metrics(simulation_results: Dict, price_data: List[Dict], config_data: Dict) -> Dict:
        """计算模拟性能指标"""
        trades = simulation_results['trades']
        
        if not trades:
            return {
                'total_return': 0,
                'roi_percent': 0,
                'win_rate': 0,
                'avg_profit_per_trade': 0,
                'max_drawdown': 0,
                'sharpe_ratio': 0,
                'trade_frequency': 0
            }
        
        # 计算胜率
        profitable_trades = [t for t in trades if t['type'] == 'sell' and t.get('profit', 0) > 0]
        total_sell_trades = len([t for t in trades if t['type'] == 'sell'])
        win_rate = len(profitable_trades) / total_sell_trades * 100 if total_sell_trades > 0 else 0
        
        # 计算平均每笔交易利润
        total_profit = sum(Decimal(str(t.get('profit', 0))) for t in trades if t['type'] == 'sell')
        avg_profit_per_trade = float(total_profit / total_sell_trades) if total_sell_trades > 0 else 0
        
        # 计算最大回撤
        price_changes = []
        for i in range(1, len(price_data)):
            change = (price_data[i]['price'] - price_data[i-1]['price']) / price_data[i-1]['price']
            price_changes.append(float(change))
        
        max_drawdown = 0
        if price_changes:
            cumulative = 0
            peak = 0
            for change in price_changes:
                cumulative += change
                if cumulative > peak:
                    peak = cumulative
                drawdown = peak - cumulative
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
        
        # 计算交易频率
        simulation_days = len(price_data)
        trade_frequency = len(trades) / simulation_days if simulation_days > 0 else 0
        
        # 简化的夏普比率计算
        returns = [float(t.get('profit', 0)) for t in trades if t['type'] == 'sell']
        if len(returns) > 1:
            import statistics
            avg_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            sharpe_ratio = avg_return / std_return if std_return > 0 else 0
        else:
            sharpe_ratio = 0
        
        return {
            'total_return': float(simulation_results['total_return']),
            'roi_percent': simulation_results['roi_percent'],
            'win_rate': win_rate,
            'avg_profit_per_trade': avg_profit_per_trade,
            'max_drawdown': max_drawdown * 100,  # 转换为百分比
            'sharpe_ratio': sharpe_ratio,
            'trade_frequency': trade_frequency,
            'total_trades': simulation_results['total_trades'],
            'profitable_trades': len(profitable_trades),
            'loss_trades': total_sell_trades - len(profitable_trades)
        }
    
    @staticmethod
    def get_simulation_results(simulation_id: str) -> Dict:
        """获取模拟结果"""
        from .models import GridSimulation
        
        try:
            simulation = GridSimulation.objects.get(simulation_id=simulation_id)
            
            # 生成建议
            recommendations = []
            if simulation.status == 'completed':
                recommendations = GridSimulationService._generate_simulation_recommendations(
                    simulation.config_data,
                    simulation.simulation_results,
                    simulation.performance_metrics
                )
            
            return {
                'simulation_id': simulation.simulation_id,
                'config_summary': GridSimulationService._summarize_config(simulation.config_data),
                'simulation_results': simulation.simulation_results,
                'performance_metrics': simulation.performance_metrics,
                'trade_history': simulation.simulation_results.get('trades', []),
                'price_chart_data': [],  # 价格数据可以单独获取
                'recommendations': recommendations,
                'status': simulation.status,
                'created_at': simulation.created_at,
                'completed_at': simulation.completed_at
            }
            
        except GridSimulation.DoesNotExist:
            raise ValueError(f"模拟记录不存在: {simulation_id}")
    
    @staticmethod
    def _summarize_config(config_data: Dict) -> Dict:
        """总结配置信息"""
        return {
            'base_price': float(config_data['base_price']),
            'price_range': {
                'min': float(config_data['min_price']),
                'max': float(config_data['max_price'])
            },
            'grid_interval_percent': float(config_data['grid_interval_percent']),
            'investment': {
                'base': float(config_data['base_investment']),
                'max': float(config_data['max_investment'])
            },
            'strategy_type': config_data.get('version', '1.0')
        }
    
    @staticmethod
    def _generate_simulation_recommendations(config_data: Dict, simulation_results: Dict, 
                                           performance_metrics: Dict) -> List[str]:
        """生成模拟建议"""
        recommendations = []
        
        # 基于收益率的建议
        roi = performance_metrics.get('roi_percent', 0)
        if roi < 5:
            recommendations.append("收益率较低，建议优化网格间距或调整价格范围")
        elif roi > 50:
            recommendations.append("收益率较高，但请注意这是模拟结果，实际交易中可能存在滑点和手续费")
        
        # 基于胜率的建议
        win_rate = performance_metrics.get('win_rate', 0)
        if win_rate < 60:
            recommendations.append("胜率偏低，建议调整网格策略参数")
        
        # 基于交易频率的建议
        trade_frequency = performance_metrics.get('trade_frequency', 0)
        if trade_frequency > 2:
            recommendations.append("交易频率较高，请考虑手续费对实际收益的影响")
        elif trade_frequency < 0.1:
            recommendations.append("交易频率过低，建议减小网格间距增加交易机会")
        
        # 基于最大回撤的建议
        max_drawdown = performance_metrics.get('max_drawdown', 0)
        if max_drawdown > 20:
            recommendations.append("最大回撤较大，建议增加风险控制措施")
        
        return recommendations


class GridTemplateService:
    """网格模板服务"""
    
    @staticmethod
    def get_user_templates(user):
        """获取用户的模板列表"""
        from .models import GridTemplate
        
        # 获取用户的私有模板和公开模板
        templates = GridTemplate.objects.filter(
            Q(user=user) | Q(is_public=True)
        ).order_by('-created_at')
        
        return templates
    
    @staticmethod
    def apply_template_to_plan(grid_plan, template):
        """应用模板到网格计划"""
        template_data = template.template_data
        
        with transaction.atomic():
            # 更新计划基本信息
            if 'plan_name' in template_data:
                grid_plan.plan_name = f"{template_data['plan_name']}_应用模板"
            
            # 更新网格参数
            for field in ['base_price', 'min_price', 'max_price', 'base_investment', 'max_investment']:
                if field in template_data:
                    setattr(grid_plan, field, Decimal(str(template_data[field])))
            
            # 更新策略参数
            strategy = grid_plan.strategy
            for field in ['grid_interval_percent', 'keep_profit', 'progressive_investment']:
                if field in template_data:
                    setattr(strategy, field, template_data[field])
            
            strategy.save()
            grid_plan.save()
            
            # 重新生成网格等级
            grid_plan.levels.all().delete()
            levels = grid_plan.calculate_grid_levels()
            
            grid_levels = []
            for level_data in levels:
                grid_levels.append(GridLevel(
                    grid_plan=grid_plan,
                    price=level_data['price'],
                    investment_amount=level_data['investment_amount'],
                    grid_type=level_data.get('grid_type', 'single'),
                    grid_index=level_data.get('grid_index', 0),
                    sell_price=level_data.get('sell_price')
                ))
            
            GridLevel.objects.bulk_create(grid_levels)
    
    @staticmethod
    def export_template_data(template):
        """导出模板数据"""
        return {
            'template_info': {
                'name': template.name,
                'description': template.description,
                'category': template.category,
                'export_date': timezone.now().isoformat(),
                'version': '1.0'
            },
            'config_data': template.template_data,
            'export_metadata': {
                'usage_count': template.usage_count,
                'created_by': template.user.username if template.user else 'unknown'
            }
        } 