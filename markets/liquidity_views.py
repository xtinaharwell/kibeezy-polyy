"""
Liquidity API Views

REST endpoints for liquidity provider operations:
- POST /api/liquidity/deposit/ - Deposit liquidity
- POST /api/liquidity/withdraw/ - Withdraw liquidity  
- POST /api/liquidity/claim-fees/ - Claim accumulated fees
- GET /api/liquidity/positions/ - Get user's LP positions
- GET /api/liquidity/pool-stats/ - Get pool statistics
"""

import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal

from .models import Market, LiquidityPool, LiquidityProvider
from .liquidity_service import (
    deposit_liquidity,
    withdraw_liquidity,
    claim_fees,
    get_pool_stats,
    get_lp_performance,
    calculate_impermanent_loss,
    calculate_pool_risk_score,
    get_fee_analytics,
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def deposit_liquidity_view(request):
    """
    Deposit liquidity into a market.
    
    Request:
    {
        "market_id": int,
        "amount_kes": float
    }
    """
    market_id = request.data.get('market_id')
    amount_kes = request.data.get('amount_kes')
    
    if not market_id or not amount_kes:
        return Response(
            {'error': 'market_id and amount_kes required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        amount_kes = float(amount_kes)
    except (ValueError, TypeError):
        return Response(
            {'error': 'amount_kes must be a number'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        market = Market.objects.get(id=market_id)
    except Market.DoesNotExist:
        return Response(
            {'error': f'Market {market_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    result = deposit_liquidity(market, request.user, amount_kes)
    
    if not result.get('success'):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    lp_provider = result.pop('lp_provider')
    
    return Response({
        **result,
        'lp_provider_id': lp_provider.id,
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def withdraw_liquidity_view(request):
    """
    Withdraw all liquidity from a position.
    
    Request:
    {
        "lp_provider_id": int
    }
    """
    lp_provider_id = request.data.get('lp_provider_id')
    
    if not lp_provider_id:
        return Response(
            {'error': 'lp_provider_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lp_provider = LiquidityProvider.objects.get(
            id=lp_provider_id,
            user=request.user
        )
    except LiquidityProvider.DoesNotExist:
        return Response(
            {'error': 'LP position not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    result = withdraw_liquidity(lp_provider)
    
    if not result.get('success'):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def claim_fees_view(request):
    """
    Claim accumulated fees from an LP position.
    
    Request:
    {
        "lp_provider_id": int
    }
    """
    lp_provider_id = request.data.get('lp_provider_id')
    
    if not lp_provider_id:
        return Response(
            {'error': 'lp_provider_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lp_provider = LiquidityProvider.objects.get(
            id=lp_provider_id,
            user=request.user
        )
    except LiquidityProvider.DoesNotExist:
        return Response(
            {'error': 'LP position not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    result = claim_fees(lp_provider)
    
    if not result.get('success'):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    return Response(result)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_lp_positions(request):
    """
    Get all liquidity provider positions for current user.
    
    Response: [
        {
            "id": int,
            "market_id": int,
            "market_question": str,
            "capital_provided": float,
            "yes_shares": float,
            "no_shares": float,
            "total_fees_earned": float,
            "unclaimed_fees": float,
            "fees_claimed": float,
            "lp_share_percent": float,
            "estimated_apy": float,
            "days_invested": int,
            "entry_date": str,
        }
    ]
    """
    positions = LiquidityProvider.objects.filter(user=request.user).select_related('pool__market')
    
    data = []
    for pos in positions:
        performance = get_lp_performance(pos)
        data.append({
            'id': pos.id,
            'market_id': pos.pool.market.id,
            'market_question': pos.pool.market.question,
            'capital_provided': float(pos.capital_provided),
            'yes_shares': pos.yes_shares_owned,
            'no_shares': pos.no_shares_owned,
            'total_fees_earned': float(pos.total_fees_earned),
            'unclaimed_fees': float(pos.unclaimed_fees),
            'fees_claimed': float(pos.fees_claimed),
            'lp_share_percent': performance['lp_share_percent'],
            'estimated_apy': performance['estimated_apy'],
            'days_invested': performance['days_invested'],
            'entry_date': pos.entry_date.isoformat(),
        })
    
    return Response(data)


@api_view(['GET'])
def get_liquidity_pool_stats(request):
    """
    Get statistics for a liquidity pool.
    
    Query params:
    - market_id: int
    
    Response: {
        "market_id": int,
        "market_question": str,
        "num_providers": int,
        "total_unclaimed_fees": float,
        "total_fees_collected": float,
        "total_liquidity_yes_shares": float,
        "total_liquidity_no_shares": float,
        "fee_percent": float,
        "providers": [...]
    }
    """
    market_id = request.query_params.get('market_id')
    
    if not market_id:
        return Response(
            {'error': 'market_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        market = Market.objects.get(id=market_id)
        pool = market.liquidity_pool
    except (Market.DoesNotExist, LiquidityPool.DoesNotExist):
        return Response(
            {'error': 'Market or pool not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    stats = get_pool_stats(pool)
    return Response(stats)


# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_lp_analytics(request):
    """
    Get comprehensive analytics for a specific LP position.
    
    Query params:
    - lp_provider_id: int
    
    Response: {
        "il": {...},
        "fee_analytics": {...},
    }
    """
    lp_provider_id = request.query_params.get('lp_provider_id')
    
    if not lp_provider_id:
        return Response(
            {'error': 'lp_provider_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        lp_provider = LiquidityProvider.objects.get(
            id=lp_provider_id,
            user=request.user
        )
    except LiquidityProvider.DoesNotExist:
        return Response(
            {'error': 'LP position not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    return Response({
        'il': calculate_impermanent_loss(lp_provider),
        'fee_analytics': get_fee_analytics(lp_provider),
    })


@api_view(['GET'])
def get_pool_risk_score(request):
    """
    Get risk score and analysis for a liquidity pool.
    
    Query params:
    - market_id: int
    
    Response: {
        "risk_score": int (1-10),
        "risk_label": str,
        "factors": {...},
    }
    """
    market_id = request.query_params.get('market_id')
    
    if not market_id:
        return Response(
            {'error': 'market_id required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        market = Market.objects.get(id=market_id)
        pool = market.liquidity_pool
    except (Market.DoesNotExist, LiquidityPool.DoesNotExist):
        return Response(
            {'error': 'Market or pool not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    risk_data = calculate_pool_risk_score(pool)
    return Response(risk_data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_fee_analytics_dashboard(request):
    """
    Get comprehensive fee analytics across all LP positions.
    
    Response: {
        "total_fees_all_positions": float,
        "avg_daily_fees": float,
        "estimated_monthly": float,
        "positions_fee_breakdown": [
            {
                "position_id": int,
                "market": str,
                "total_fees": float,
                "daily_avg": float,
            }
        ]
    }
    """
    positions = LiquidityProvider.objects.filter(user=request.user).select_related('pool__market')
    
    total_fees = 0
    total_daily = 0
    breakdown = []
    
    for pos in positions:
        analytics = get_fee_analytics(pos)
        total_fees += analytics['total_fees_earned']
        total_daily += analytics['avg_fee_per_day']
        
        breakdown.append({
            'position_id': pos.id,
            'market': pos.pool.market.question[:50],
            'total_fees': analytics['total_fees_earned'],
            'daily_avg': analytics['avg_fee_per_day'],
        })
    
    breakdown.sort(key=lambda x: x['total_fees'], reverse=True)
    
    return Response({
        'total_fees_all_positions': round(total_fees, 2),
        'avg_daily_fees': round(total_daily, 2),
        'estimated_monthly': round(total_daily * 30, 2),
        'positions_fee_breakdown': breakdown,
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_portfolio_il_analysis(request):
    """
    Get overall impermanent loss analysis across all positions.
    
    Response: {
        "total_il": float,
        "total_fees_offset": float,
        "net_il": float,
        "positions": [...]
    }
    """
    positions = LiquidityProvider.objects.filter(user=request.user).select_related('pool__market')
    
    total_il = 0
    total_fees = 0
    total_net = 0
    position_breakdown = []
    
    for pos in positions:
        il_data = calculate_impermanent_loss(pos)
        total_il += il_data['il_amount']
        total_fees += il_data['fees_earned']
        net = il_data['il_amount'] - il_data['fees_earned']
        total_net += net
        
        position_breakdown.append({
            'position_id': pos.id,
            'market': pos.pool.market.question[:50],
            'il_amount': il_data['il_amount'],
            'il_percent': il_data['il_percent'],
            'fees_earned': il_data['fees_earned'],
            'net': net,
        })
    
    position_breakdown.sort(key=lambda x: x['il_percent'], reverse=True)
    
    return Response({
        'total_il': round(total_il, 2),
        'total_fees_offset': round(total_fees, 2),
        'net_il': round(total_net, 2),
        'positions': position_breakdown,
    })


# ============================================================================
# CONVENIENCE ENDPOINT: Market-specific add liquidity
# ============================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_liquidity_to_market(request, market_id):
    """
    Convenience endpoint to add liquidity to a specific market.
    
    URL: POST /api/markets/{market_id}/add-liquidity/
    
    Request:
    {
        "amount_kes": float
    }
    
    Response: Same as deposit_liquidity_view
    """
    amount_kes = request.data.get('amount_kes')
    
    if not amount_kes:
        return Response(
            {'error': 'amount_kes required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        amount_kes = float(amount_kes)
    except (ValueError, TypeError):
        return Response(
            {'error': 'amount_kes must be a number'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        market = Market.objects.get(id=market_id)
    except Market.DoesNotExist:
        return Response(
            {'error': f'Market {market_id} not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    result = deposit_liquidity(market, request.user, amount_kes)
    
    if not result.get('success'):
        return Response(result, status=status.HTTP_400_BAD_REQUEST)
    
    lp_provider = result.pop('lp_provider')
    
    return Response({
        **result,
        'lp_provider_id': lp_provider.id,
    })
