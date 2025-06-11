from decimal import Decimal
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db.models import Q, Sum
from django.utils import timezone
from django.contrib.auth.models import AnonymousUser
from ninja import Router
from ninja.security import django_auth

from .models import (
    GridStrategy, GridPlan, GridLevel, GridOrder, 
    GridTradePair, GridPerformanceSnapshot, GridTemplate
)
from .services import GridStrategyService, GridAnalyticsService, GridConfigService, GridTemplateService, GridSimulationService
from .schemas import (
    # 基础Schema
    GridStrategySchema, GridStrategyCreateSchema, GridPlanSchema, 
    GridPlanCreateSchema, GridLevelSchema, GridOrderSchema,
    GridTradePairSchema, GridPerformanceSnapshotSchema,
    
    # 请求/响应Schema
    TriggerLevelsRequest, TriggerLevelsResponse, OrderFillRequest, 
    OrderFillResponse, PerformanceRequest, PerformanceResponse,
    SuggestionsResponse, PressureTestResponse, OptimizationResponse,
    DashboardResponse, BacktestRequest, BacktestResponse,
    StrategyPerformanceResponse, CompareStrategiesRequest,
    MessageResponse, ErrorResponse,
    GridConfigPreviewRequest, GridConfigPreviewResponse,
    GridConfigValidationResponse,
    GridTemplateSchema, GridTemplateCreateSchema, GridTemplateImportRequest,
    ApplyTemplateRequest,
    GridSimulationRequest, GridSimulationListResponse, GridSimulationResponse
)

# 创建路由器
grid_router = Router(auth=django_auth)


# ==================== 网格策略相关API ====================

@grid_router.get("/strategies", response=List[GridStrategySchema])
def list_strategies(request):
    """获取策略列表"""
    return GridStrategy.objects.all()


@grid_router.post("/strategies", response=GridStrategySchema)
def create_strategy(request, payload: GridStrategyCreateSchema):
    """创建网格策略"""
    strategy = GridStrategy.objects.create(**payload.dict())
    return strategy


@grid_router.get("/strategies/{strategy_id}", response=GridStrategySchema)
def get_strategy(request, strategy_id: int):
    """获取策略详情"""
    return get_object_or_404(GridStrategy, id=strategy_id)


@grid_router.put("/strategies/{strategy_id}", response=GridStrategySchema)
def update_strategy(request, strategy_id: int, payload: GridStrategyCreateSchema):
    """更新策略"""
    strategy = get_object_or_404(GridStrategy, id=strategy_id)
    
    for field, value in payload.dict().items():
        setattr(strategy, field, value)
    strategy.save()
    
    return strategy


@grid_router.delete("/strategies/{strategy_id}", response=MessageResponse)
def delete_strategy(request, strategy_id: int):
    """删除策略"""
    strategy = get_object_or_404(GridStrategy, id=strategy_id)
    strategy.delete()
    return {"message": "策略已删除"}


@grid_router.get("/strategies/{strategy_id}/performance", response=StrategyPerformanceResponse)
def get_strategy_performance(request, strategy_id: int, days: int = 30):
    """获取策略性能分析"""
    strategy = get_object_or_404(GridStrategy, id=strategy_id)
    performance = GridAnalyticsService.analyze_strategy_performance(strategy, days)
    return performance


@grid_router.post("/strategies/compare", response=List[StrategyPerformanceResponse])
def compare_strategies(request, payload: CompareStrategiesRequest):
    """比较多个策略性能"""
    results = GridAnalyticsService.compare_strategies(
        payload.strategy_ids, 
        payload.days
    )
    return results


# ==================== 网格计划相关API ====================

@grid_router.get("/plans", response=List[Dict[str, Any]])
def list_plans(request):
    """获取当前用户的网格计划列表"""
    plans = GridPlan.objects.filter(user=request.user).select_related('strategy', 'stock')
    
    result = []
    for plan in plans:
        # 计算统计信息
        active_orders_count = GridOrder.objects.filter(grid_plan=plan, status='pending').count()
        completed_trades_count = GridTradePair.objects.filter(grid_plan=plan, is_completed=True).count()
        current_roi = float(plan.total_profit / plan.total_invested * 100) if plan.total_invested > 0 else 0.0
        
        # 构造响应数据
        plan_data = GridPlanSchema.from_orm(plan).dict()
        plan_data.update({
            'active_orders_count': active_orders_count,
            'completed_trades_count': completed_trades_count,
            'current_roi': current_roi
        })
        result.append(plan_data)
    
    return result


@grid_router.post("/plans", response=GridPlanSchema)
def create_plan(request, payload: GridPlanCreateSchema):
    """创建网格计划"""
    validated_data = payload.dict()
    strategy_data = validated_data.pop('strategy_data', {})
    
    # 获取股票对象
    from stocks.models import Stock
    stock = get_object_or_404(Stock, pk=validated_data.pop('stock'))
    
    # 创建网格计划
    grid_plan = GridStrategyService.create_grid_plan(
        user=request.user,
        stock=stock,
        strategy_data={**strategy_data, **validated_data}
    )
    
    return grid_plan


@grid_router.get("/plans/{plan_id}", response=Dict[str, Any])
def get_plan(request, plan_id: int):
    """获取网格计划详情"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    
    # 计算统计信息
    active_orders_count = GridOrder.objects.filter(grid_plan=plan, status='pending').count()
    completed_trades_count = GridTradePair.objects.filter(grid_plan=plan, is_completed=True).count()
    current_roi = float(plan.total_profit / plan.total_invested * 100) if plan.total_invested > 0 else 0.0
    
    # 构造响应数据
    plan_data = GridPlanSchema.from_orm(plan).dict()
    plan_data.update({
        'active_orders_count': active_orders_count,
        'completed_trades_count': completed_trades_count,
        'current_roi': current_roi
    })
    
    return plan_data


@grid_router.put("/plans/{plan_id}", response=GridPlanSchema)
def update_plan(request, plan_id: int, payload: GridPlanCreateSchema):
    """更新网格计划"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    
    validated_data = payload.dict()
    strategy_data = validated_data.pop('strategy_data', {})
    
    # 更新计划基本信息
    for field, value in validated_data.items():
        if field != 'stock':  # 股票不允许修改
            setattr(plan, field, value)
    
    # 更新策略信息
    if plan.strategy:
        for field, value in strategy_data.items():
            if hasattr(plan.strategy, field):
                setattr(plan.strategy, field, value)
        plan.strategy.save()
    
    plan.save()
    
    return plan


@grid_router.delete("/plans/{plan_id}", response=MessageResponse)
def delete_plan(request, plan_id: int):
    """删除网格计划"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    plan.delete()
    return {"message": "网格计划已删除"}


@grid_router.post("/plans/{plan_id}/pressure-test", response=PressureTestResponse)
def pressure_test(request, plan_id: int):
    """执行压力测试"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    test_result = GridStrategyService.execute_pressure_test(plan)
    return test_result


@grid_router.get("/plans/{plan_id}/performance", response=PerformanceResponse)
def get_plan_performance(request, plan_id: int, current_price: Optional[Decimal] = None):
    """获取计划性能"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    if current_price is None:
        current_price = Decimal(str(plan.base_price))
    performance = GridStrategyService.calculate_plan_performance(plan, current_price)
    return performance


@grid_router.post("/plans/{plan_id}/trigger-levels", response=TriggerLevelsResponse)
def trigger_levels(request, plan_id: int, payload: TriggerLevelsRequest):
    """手动触发网格等级"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    triggered_orders = GridStrategyService.trigger_grid_level(plan, payload.current_price)
    
    return {
        "triggered_count": len(triggered_orders),
        "orders": triggered_orders
    }


@grid_router.get("/plans/{plan_id}/suggestions", response=SuggestionsResponse)
def get_suggestions(request, plan_id: int, current_price: Optional[Decimal] = None):
    """获取交易建议"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    if current_price is None:
        current_price = Decimal(str(plan.base_price))
    suggestions = GridStrategyService.get_trading_suggestions(plan, current_price)
    return suggestions


@grid_router.get("/plans/{plan_id}/optimization", response=OptimizationResponse)
def get_optimization(request, plan_id: int):
    """获取优化建议"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    suggestions = GridAnalyticsService.generate_optimization_suggestions(plan)
    return {"suggestions": suggestions}


@grid_router.post("/plans/{plan_id}/pause", response=MessageResponse)
def pause_plan(request, plan_id: int):
    """暂停网格计划"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    plan.status = 'paused'
    plan.save()
    return {"message": "网格计划已暂停"}


@grid_router.post("/plans/{plan_id}/resume", response=MessageResponse)
def resume_plan(request, plan_id: int):
    """恢复网格计划"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    plan.status = 'active'
    plan.save()
    return {"message": "网格计划已恢复运行"}


@grid_router.post("/plans/{plan_id}/stop", response=MessageResponse)
def stop_plan(request, plan_id: int):
    """停止网格计划"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    plan.status = 'stopped'
    plan.stopped_at = timezone.now()
    plan.save()
    
    # 取消所有待成交订单
    GridOrder.objects.filter(
        grid_plan=plan,
        status='pending'
    ).update(status='cancelled')
    
    return {"message": "网格计划已停止，所有待成交订单已取消"}


# ==================== 网格等级相关API ====================

@grid_router.get("/levels", response=List[GridLevelSchema])
def list_levels(request, plan_id: Optional[int] = None):
    """获取网格等级列表"""
    queryset = GridLevel.objects.filter(
        grid_plan__user=request.user
    ).select_related('grid_plan')
    
    if plan_id:
        queryset = queryset.filter(grid_plan_id=plan_id)
    
    return queryset.all()


@grid_router.get("/levels/{level_id}", response=GridLevelSchema)
def get_level(request, level_id: int):
    """获取网格等级详情"""
    return get_object_or_404(
        GridLevel, 
        pk=level_id, 
        grid_plan__user=request.user
    )


# ==================== 网格订单相关API ====================

@grid_router.get("/orders", response=List[GridOrderSchema])
def list_orders(request, 
                plan_id: Optional[int] = None,
                order_type: Optional[str] = None,
                status: Optional[str] = None):
    """获取订单列表"""
    queryset = GridOrder.objects.filter(
        grid_plan__user=request.user
    ).select_related('grid_plan', 'grid_level')
    
    if plan_id:
        queryset = queryset.filter(grid_plan_id=plan_id)
    if order_type:
        queryset = queryset.filter(order_type=order_type)
    if status:
        queryset = queryset.filter(status=status)
    
    return queryset.order_by('-created_at')


@grid_router.get("/orders/{order_id}", response=GridOrderSchema)
def get_order(request, order_id: int):
    """获取订单详情"""
    return get_object_or_404(
        GridOrder, 
        pk=order_id, 
        grid_plan__user=request.user
    )


@grid_router.post("/orders/{order_id}/fill", response=OrderFillResponse)
def fill_order(request, order_id: int, payload: OrderFillRequest):
    """手动标记订单成交"""
    order = get_object_or_404(
        GridOrder, 
        pk=order_id, 
        grid_plan__user=request.user
    )
    
    if order.status != 'pending':
        return {"error": "只能处理待成交的订单"}
    
    result = GridStrategyService.process_order_fill(
        order, 
        payload.filled_price, 
        payload.filled_quantity
    )
    
    return {
        "message": "订单成交处理完成",
        "order": result['order'],
        "additional_info": {k: v for k, v in result.items() if k != 'order'}
    }


@grid_router.post("/orders/{order_id}/cancel", response=MessageResponse)
def cancel_order(request, order_id: int):
    """取消订单"""
    order = get_object_or_404(
        GridOrder, 
        pk=order_id, 
        grid_plan__user=request.user
    )
    
    if order.status != 'pending':
        return {"error": "只能取消待成交的订单"}
    
    order.status = 'cancelled'
    order.save()
    
    return {"message": "订单已取消"}


# ==================== 网格交易对相关API ====================

@grid_router.get("/trade-pairs", response=List[GridTradePairSchema])
def list_trade_pairs(request, 
                     plan_id: Optional[int] = None,
                     completed: Optional[bool] = None):
    """获取交易对列表"""
    queryset = GridTradePair.objects.filter(
        grid_plan__user=request.user
    ).select_related('grid_plan', 'buy_order', 'sell_order')
    
    if plan_id:
        queryset = queryset.filter(grid_plan_id=plan_id)
    if completed is not None:
        queryset = queryset.filter(is_completed=completed)
    
    return queryset.order_by('-created_at')


@grid_router.get("/trade-pairs/{pair_id}", response=GridTradePairSchema)
def get_trade_pair(request, pair_id: int):
    """获取交易对详情"""
    return get_object_or_404(
        GridTradePair, 
        pk=pair_id, 
        grid_plan__user=request.user
    )


# ==================== 性能快照相关API ====================

@grid_router.get("/snapshots", response=List[GridPerformanceSnapshotSchema])
def list_snapshots(request,
                   plan_id: Optional[int] = None,
                   start_date: Optional[date] = None,
                   end_date: Optional[date] = None):
    """获取性能快照列表"""
    queryset = GridPerformanceSnapshot.objects.filter(
        grid_plan__user=request.user
    ).select_related('grid_plan')
    
    if plan_id:
        queryset = queryset.filter(grid_plan_id=plan_id)
    if start_date:
        queryset = queryset.filter(snapshot_date__gte=start_date)
    if end_date:
        queryset = queryset.filter(snapshot_date__lte=end_date)
    
    return queryset.order_by('-snapshot_date')


@grid_router.get("/snapshots/{snapshot_id}", response=Dict[str, Any])
def get_snapshot(request, snapshot_id: int):
    """获取性能快照详情"""
    snapshot = get_object_or_404(
        GridPerformanceSnapshot, 
        pk=snapshot_id, 
        grid_plan__user=request.user
    )
    
    # 构造响应数据
    snapshot_data = GridPerformanceSnapshotSchema.from_orm(snapshot).dict()
    
    # 添加计划信息
    if snapshot.grid_plan:
        snapshot_data['grid_plan_info'] = {
            'id': snapshot.grid_plan.pk,
            'plan_name': snapshot.grid_plan.plan_name,
            'stock_symbol': snapshot.grid_plan.stock.symbol if snapshot.grid_plan.stock else None
        }
    
    return snapshot_data


# ==================== 仪表板API ====================

@grid_router.get("/dashboard", response=Dict[str, Any])
def get_dashboard(request, enhanced: bool = False):
    """获取仪表板数据"""
    user = request.user
    
    # 用户的网格计划概览
    plans = GridPlan.objects.filter(user=user).select_related('strategy', 'stock')
    active_plans = plans.filter(status='active')
    
    # 总体数据统计
    total_profit = plans.aggregate(Sum('total_profit'))['total_profit'] or Decimal('0.00')
    total_invested = plans.aggregate(Sum('total_invested'))['total_invested'] or Decimal('0.00')
    total_trades = plans.aggregate(Sum('total_trades'))['total_trades'] or 0
    
    # 最近的交易对
    recent_pairs = GridTradePair.objects.filter(
        grid_plan__user=user,
        is_completed=True
    ).select_related('grid_plan', 'grid_plan__stock').order_by('-completed_at')[:10]
    
    # 待处理的订单
    pending_orders = GridOrder.objects.filter(
        grid_plan__user=user,
        status='pending'
    ).count()
    
    # 性能最好的计划
    best_plans = plans.filter(
        total_profit__gt=0
    ).order_by('-total_profit')[:5]
    
    base_data = {
        'summary': {
            'total_plans': plans.count(),
            'active_plans': active_plans.count(),
            'total_profit': float(total_profit),
            'total_invested': float(total_invested),
            'total_trades': total_trades,
            'pending_orders': pending_orders,
            'roi': float(total_profit / total_invested * 100) if total_invested > 0 else 0
        },
        'recent_trades': [
            {
                'id': trade.pk,
                'plan_name': trade.grid_plan.plan_name if trade.grid_plan else '',
                'stock': trade.grid_plan.stock.symbol if trade.grid_plan and trade.grid_plan.stock else '',
                'profit': float(trade.profit_amount),
                'completed_at': trade.completed_at
            } for trade in recent_pairs
        ],
        'best_plans': [
            {
                'id': plan.pk,
                'name': plan.plan_name,
                'stock': plan.stock.symbol if plan.stock else '',
                'profit': float(plan.total_profit),
                'roi': float(plan.total_profit / plan.total_invested * 100) if plan.total_invested > 0 else 0
            } for plan in best_plans
        ],
        'active_plans': [
            {
                'id': plan.pk,
                'name': plan.plan_name,
                'stock': plan.stock.symbol if plan.stock else '',
                'status': plan.status,
                'profit': float(plan.total_profit),
                'invested': float(plan.total_invested)
            } for plan in active_plans
        ]
    }
    
    # 如果需要增强数据
    if enhanced:
        # 策略分布
        strategy_distribution = {}
        for plan in plans:
            if plan.strategy:
                version = plan.strategy.version
                if version not in strategy_distribution:
                    strategy_distribution[version] = {'count': 0, 'profit': 0}
                strategy_distribution[version]['count'] += 1
                strategy_distribution[version]['profit'] += float(plan.total_profit)
        
        # 风险分析
        risk_analysis = {
            'high_risk_plans': len([p for p in active_plans if p.total_invested / p.max_investment > 0.8]),
            'low_activity_plans': len([p for p in active_plans if p.total_trades < 5]),
            'profitable_plans': len([p for p in plans if p.total_profit > 0])
        }
        
        base_data.update({
            'strategy_distribution': strategy_distribution,
            'risk_analysis': risk_analysis
        })
    
    return base_data


# ==================== 回测API ====================

@grid_router.post("/backtest", response=BacktestResponse)
def run_backtest(request, payload: BacktestRequest):
    """执行网格策略回测"""
    result = _run_backtest(payload.strategy, payload.price_data, payload.initial_capital)
    return result


def _run_backtest(strategy_params: Dict, price_data: List[Dict], initial_capital: Decimal) -> Dict:
    """运行回测"""
    # 简化的回测逻辑
    results = {
        'initial_capital': initial_capital,
        'final_capital': initial_capital,
        'total_profit': Decimal('0.00'),
        'total_trades': 0,
        'win_rate': 0,
        'max_drawdown': 0,
        'trades': []
    }
    
    try:
        # 获取策略参数
        grid_percent = Decimal(strategy_params.get('grid_interval_percent', '5')) / 100
        base_investment = Decimal(strategy_params.get('base_investment', '1000'))
        
        # 初始化
        current_capital = initial_capital
        positions = {}  # 持仓记录
        orders = []  # 订单记录
        
        for price_point in price_data:
            current_price = Decimal(str(price_point['price']))
            timestamp = price_point.get('timestamp')
            
            # 检查买入机会
            for i in range(1, 11):  # 模拟10个网格等级
                buy_price = current_price * (1 - grid_percent * i)
                if buy_price not in positions and current_capital >= base_investment:
                    # 买入
                    quantity = base_investment / current_price
                    positions[buy_price] = {
                        'quantity': quantity,
                        'cost': base_investment,
                        'timestamp': timestamp
                    }
                    current_capital -= base_investment
                    results['total_trades'] += 1
                    
                    orders.append({
                        'type': 'buy',
                        'price': current_price,
                        'quantity': quantity,
                        'amount': base_investment,
                        'timestamp': timestamp
                    })
            
            # 检查卖出机会
            to_sell = []
            for buy_price, position in positions.items():
                sell_price = buy_price * (1 + grid_percent)
                if current_price >= sell_price:
                    # 卖出
                    sell_amount = position['quantity'] * current_price
                    profit = sell_amount - position['cost']
                    current_capital += sell_amount
                    results['total_profit'] += profit
                    results['total_trades'] += 1
                    
                    orders.append({
                        'type': 'sell',
                        'price': current_price,
                        'quantity': position['quantity'],
                        'amount': sell_amount,
                        'profit': profit,
                        'timestamp': timestamp
                    })
                    
                    to_sell.append(buy_price)
            
            # 清理已卖出的持仓
            for buy_price in to_sell:
                del positions[buy_price]
        
        # 计算最终结果
        remaining_value = sum(pos['quantity'] * price_data[-1]['price'] for pos in positions.values())
        results['final_capital'] = current_capital + remaining_value
        results['total_profit'] = results['final_capital'] - initial_capital
        results['win_rate'] = len([o for o in orders if o.get('profit', 0) > 0]) / max(len([o for o in orders if 'profit' in o]), 1) * 100
        results['trades'] = orders
        
    except Exception as e:
        results['error'] = f'回测执行失败: {str(e)}'
    
    return results 


# ==================== 网格配置预览和验证API ====================

@grid_router.post("/config/preview", response=GridConfigPreviewResponse)
def preview_grid_config(request, payload: GridConfigPreviewRequest):
    """预览网格配置"""
    try:
        preview_data = GridConfigService.preview_grid_configuration(payload.dict())
        return preview_data
    except Exception as e:
        from ninja.responses import Response
        return Response({"error": f"配置预览失败: {str(e)}"}, status=400)


@grid_router.post("/config/validate", response=GridConfigValidationResponse)
def validate_grid_config(request, payload: GridConfigPreviewRequest):
    """验证网格配置的合理性"""
    try:
        validation_result = GridConfigService.validate_grid_configuration(payload.dict())
        return validation_result
    except Exception as e:
        from ninja.responses import Response
        return Response({"error": f"配置验证失败: {str(e)}"}, status=400)


# ==================== 网格模板管理API ====================

@grid_router.get("/templates", response=List[GridTemplateSchema])
def list_templates(request, category: Optional[str] = None, is_public: Optional[bool] = None):
    """获取模板列表"""
    templates = GridTemplate.objects.all()
    
    if category:
        templates = templates.filter(category=category)
    if is_public is not None:
        templates = templates.filter(is_public=is_public)
    
    # 显示用户自己的模板和公开模板
    templates = templates.filter(
        Q(user=request.user) | Q(is_public=True)
    ).order_by('-usage_count', '-created_at')
    
    return templates


@grid_router.post("/templates", response=GridTemplateSchema)
def create_template(request, payload: GridTemplateCreateSchema):
    """创建配置模板"""
    template = GridTemplate.objects.create(
        user=request.user,
        **payload.dict()
    )
    return template


@grid_router.get("/templates/{template_id}", response=GridTemplateSchema)
def get_template(request, template_id: int):
    """获取模板详情"""
    template = get_object_or_404(GridTemplate, pk=template_id)
    
    # 检查权限
    if not template.is_public and template.user != request.user:
        from ninja.responses import Response
        return Response({"error": "无权访问此模板"}, status=403)
    
    return template


@grid_router.put("/templates/{template_id}", response=GridTemplateSchema)
def update_template(request, template_id: int, payload: GridTemplateCreateSchema):
    """更新模板"""
    template = get_object_or_404(GridTemplate, pk=template_id, user=request.user)
    
    for field, value in payload.dict().items():
        setattr(template, field, value)
    template.save()
    
    return template


@grid_router.delete("/templates/{template_id}", response=MessageResponse)
def delete_template(request, template_id: int):
    """删除模板"""
    template = get_object_or_404(GridTemplate, pk=template_id, user=request.user)
    template.delete()
    return {"message": "模板已删除"}


@grid_router.get("/templates/{template_id}/export")
def export_template(request, template_id: int):
    """导出模板配置"""
    from django.http import JsonResponse
    
    template = get_object_or_404(GridTemplate, pk=template_id)
    
    # 检查权限
    if not template.is_public and template.user != request.user:
        from ninja.responses import Response
        return Response({"error": "无权访问此模板"}, status=403)
    
    export_data = GridTemplateService.export_template_data(template)
    
    response = JsonResponse(export_data, json_dumps_params={'indent': 2, 'ensure_ascii': False})
    response['Content-Disposition'] = f'attachment; filename="grid_template_{template.name}.json"'
    return response


@grid_router.post("/templates/import", response=Dict[str, Any])
def import_template(request, payload: GridTemplateImportRequest):
    """导入模板配置"""
    try:
        import json
        
        template_data = json.loads(payload.template_file)
        
        # 验证模板格式
        if 'template_info' not in template_data or 'config_data' not in template_data:
            return {"success": False, "error": "模板格式不正确"}
        
        # 创建模板
        template = GridTemplate.objects.create(
            user=request.user,
            name=f"导入_{template_data['template_info']['name']}",
            description=template_data['template_info'].get('description', ''),
            template_data=template_data['config_data'],
            category='custom'
        )
        
        result = {"success": True, "template_id": template.pk, "message": "模板导入成功"}
        
        # 如果指定了应用到计划，则应用配置
        if payload.apply_to_plan_id:
            plan = get_object_or_404(GridPlan, pk=payload.apply_to_plan_id, user=request.user)
            GridTemplateService.apply_template_to_plan(plan, template)
            result["applied_to_plan"] = True
        
        return result
        
    except Exception as e:
        return {"success": False, "error": f"导入失败: {str(e)}"}


@grid_router.post("/plans/{plan_id}/apply-template", response=MessageResponse)
def apply_template_to_plan(request, plan_id: int, payload: ApplyTemplateRequest):
    """应用模板到计划"""
    plan = get_object_or_404(GridPlan, pk=plan_id, user=request.user)
    template = get_object_or_404(GridTemplate, pk=payload.template_id)
    
    # 检查模板权限
    if not template.is_public and template.user != request.user:
        from ninja.responses import Response
        return Response({"message": "无权访问此模板"}, status=403)
    
    GridTemplateService.apply_template_to_plan(plan, template)
    template.usage_count += 1
    template.save()
    
    return {"message": "模板应用成功"}


# ==================== 网格模拟API ====================

@grid_router.post("/simulations", response=Dict[str, Any])
def create_simulation(request, payload: GridSimulationRequest):
    """创建网格策略模拟"""
    try:
        from .services import GridSimulationService
        
        simulation_id = GridSimulationService.run_grid_simulation(
            user=request.user,
            config_data=payload.config_data,
            simulation_params={
                'days': payload.simulation_days,
                'volatility': payload.price_volatility,
                'trend_direction': payload.trend_direction,
                'trend_strength': payload.trend_strength
            }
        )
        
        return {
            "success": True,
            "simulation_id": simulation_id,
            "message": "模拟已创建，正在运行..."
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": f"模拟创建失败: {str(e)}"
        }


@grid_router.get("/simulations", response=List[GridSimulationListResponse])
def list_simulations(request, status: Optional[str] = None):
    """获取用户的模拟列表"""
    from .models import GridSimulation
    
    simulations = GridSimulation.objects.filter(user=request.user)
    
    if status:
        simulations = simulations.filter(status=status)
    
    simulations = simulations.order_by('-created_at')
    
    result = []
    for sim in simulations:
        result.append({
            'simulation_id': sim.simulation_id,
            'config_summary': sim.config_data,
            'performance_summary': sim.performance_metrics,
            'status': sim.status,
            'created_at': sim.created_at,
            'completed_at': sim.completed_at
        })
    
    return result


@grid_router.get("/simulations/{simulation_id}", response=GridSimulationResponse)
def get_simulation(request, simulation_id: str):
    """获取模拟详情"""
    try:
        from .models import GridSimulation
        from .services import GridSimulationService
        
        # 验证权限
        simulation = get_object_or_404(GridSimulation, simulation_id=simulation_id, user=request.user)
        
        # 获取完整的模拟结果
        result = GridSimulationService.get_simulation_results(simulation_id)
        
        return result
        
    except Exception as e:
        from ninja.responses import Response
        return Response({"error": f"获取模拟结果失败: {str(e)}"}, status=400)


@grid_router.delete("/simulations/{simulation_id}", response=MessageResponse)
def delete_simulation(request, simulation_id: str):
    """删除模拟记录"""
    from .models import GridSimulation
    
    simulation = get_object_or_404(GridSimulation, simulation_id=simulation_id, user=request.user)
    simulation.delete()
    
    return {"message": "模拟记录已删除"}


# ==================== 批量操作API ====================

@grid_router.post("/plans/batch-create-from-template", response=List[GridPlanSchema])
def batch_create_plans_from_template(request, payload: Dict[str, Any]):
    """从模板批量创建计划"""
    try:
        template_id = payload.get('template_id')
        stock_ids = payload.get('stock_ids', [])
        base_config = payload.get('base_config', {})
        
        from .models import GridTemplate
        from .services import GridTemplateService, GridStrategyService
        from stocks.models import Stock
        
        template = get_object_or_404(GridTemplate, pk=template_id)
        stocks = Stock.objects.filter(pk__in=stock_ids)
        
        created_plans = []
        
        for stock in stocks:
            # 合并模板配置和基础配置
            config_data = {**template.template_data, **base_config}
            config_data['stock'] = stock.pk
            config_data['plan_name'] = f"{stock.name}_网格计划"
            
            # 创建计划
            grid_plan = GridStrategyService.create_grid_plan(
                user=request.user,
                stock=stock,
                strategy_data=config_data
            )
            created_plans.append(grid_plan)
        
        # 增加模板使用次数
        template.usage_count += len(created_plans)
        template.save()
        
        return created_plans
        
    except Exception as e:
        from ninja.responses import Response
        return Response({"error": f"批量创建失败: {str(e)}"}, status=400)


 