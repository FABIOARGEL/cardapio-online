"""
Order repository — centralized database access for Order documents.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone

from bson import ObjectId

from apps.core.base_repository import BaseRepository, PaginatedResult
from apps.orders.documents import Order

logger = logging.getLogger(__name__)


class OrderRepository(BaseRepository[Order]):
    """Repository for Order document queries."""

    document_class = Order

    def find_by_order_number(self, order_number: str) -> Order | None:
        """Find an order by its human-readable order number."""
        return self.find_one(order_number=order_number)

    def find_by_customer(
        self, customer_id: str, page: int = 1, page_size: int = 10,
    ) -> PaginatedResult:
        """List orders for a customer."""
        return self.paginate(
            page=page, page_size=page_size,
            customer_id=ObjectId(customer_id),
        )

    def find_by_restaurant(
        self,
        restaurant_id: str,
        status_filter: str | None = None,
        page: int = 1,
        page_size: int = 20,
    ) -> PaginatedResult:
        """List orders for a restaurant with optional status filter."""
        filters: dict = {'restaurant_id': ObjectId(restaurant_id)}
        if status_filter:
            filters['status'] = status_filter
        return self.paginate(page=page, page_size=page_size, **filters)

    def get_dashboard_stats(self, restaurant_id: str) -> dict:
        """
        Get comprehensive dashboard statistics using a single aggregation.

        Replaces the previous approach of multiple Python-side iterations.
        """
        rid = ObjectId(restaurant_id)
        now = datetime.now(timezone.utc)
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = today_start - timedelta(days=now.weekday())
        month_start = today_start.replace(day=1)

        pipeline = [
            {'$match': {'restaurant_id': rid}},
            {'$facet': {
                # Today stats
                'today': [
                    {'$match': {'created_at': {'$gte': today_start}, 'status': {'$ne': 'cancelled'}}},
                    {'$group': {
                        '_id': None,
                        'revenue': {'$sum': {'$toDouble': '$total'}},
                        'count': {'$sum': 1},
                    }},
                ],
                # Week stats
                'week': [
                    {'$match': {'created_at': {'$gte': week_start}, 'status': {'$ne': 'cancelled'}}},
                    {'$group': {
                        '_id': None,
                        'revenue': {'$sum': {'$toDouble': '$total'}},
                        'count': {'$sum': 1},
                    }},
                ],
                # Month stats
                'month': [
                    {'$match': {'created_at': {'$gte': month_start}, 'status': {'$ne': 'cancelled'}}},
                    {'$group': {
                        '_id': None,
                        'revenue': {'$sum': {'$toDouble': '$total'}},
                        'count': {'$sum': 1},
                    }},
                ],
                # Status breakdown
                'status_counts': [
                    {'$group': {'_id': '$status', 'count': {'$sum': 1}}},
                ],
                # Top products
                'top_products': [
                    {'$match': {'status': {'$ne': 'cancelled'}}},
                    {'$unwind': '$items'},
                    {'$group': {
                        '_id': '$items.name',
                        'quantity': {'$sum': '$items.quantity'},
                    }},
                    {'$sort': {'quantity': -1}},
                    {'$limit': 5},
                    {'$project': {'_id': 0, 'name': '$_id', 'quantity': 1}},
                ],
                # Daily revenue (last 7 days)
                'daily_revenue': [
                    {'$match': {
                        'created_at': {'$gte': today_start - timedelta(days=6)},
                        'status': {'$ne': 'cancelled'},
                    }},
                    {'$group': {
                        '_id': {'$dateToString': {'format': '%Y-%m-%d', 'date': '$created_at'}},
                        'revenue': {'$sum': {'$toDouble': '$total'}},
                        'orders': {'$sum': 1},
                    }},
                    {'$sort': {'_id': 1}},
                ],
                # Recent orders
                'recent_orders': [
                    {'$sort': {'created_at': -1}},
                    {'$limit': 5},
                ],
                # Total count
                'total_count': [
                    {'$count': 'total'},
                ],
            }},
        ]

        result = self.aggregate(pipeline)
        data = result[0] if result else {}

        def _extract_group(key: str) -> dict:
            items = data.get(key, [])
            if items:
                return {'revenue': items[0].get('revenue', 0), 'orders': items[0].get('count', 0)}
            return {'revenue': 0, 'orders': 0}

        today = _extract_group('today')
        week = _extract_group('week')
        month = _extract_group('month')

        status_counts = {s['_id']: s['count'] for s in data.get('status_counts', [])}

        # Format daily revenue with day names
        day_names = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
        daily_map = {d['_id']: d for d in data.get('daily_revenue', [])}
        daily_revenue = []
        for i in range(6, -1, -1):
            day = today_start - timedelta(days=i)
            day_str = day.strftime('%Y-%m-%d')
            entry = daily_map.get(day_str, {})
            daily_revenue.append({
                'date': day.strftime('%d/%m'),
                'day_name': day_names[day.weekday()],
                'revenue': entry.get('revenue', 0),
                'orders': entry.get('orders', 0),
            })

        # Format recent orders
        recent_orders = []
        for o in data.get('recent_orders', []):
            recent_orders.append({
                'id': str(o.get('_id', '')),
                'order_number': o.get('order_number', ''),
                'status': o.get('status', ''),
                'total': float(o.get('total', 0)),
                'created_at': o.get('created_at', ''),
            })

        total_count = data.get('total_count', [])
        total_all = total_count[0]['total'] if total_count else 0

        return {
            'today': today,
            'week': week,
            'month': month,
            'ticket_average': round(month['revenue'] / month['orders'], 2) if month['orders'] else 0,
            'status_counts': status_counts,
            'top_products': data.get('top_products', []),
            'daily_revenue': daily_revenue,
            'recent_orders': recent_orders,
            'total_orders_all_time': total_all,
        }

    def get_order_history(
        self,
        restaurant_id: str,
        page: int = 1,
        page_size: int = 20,
        status_filter: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
    ) -> dict:
        """Get paginated order history with filters and summary stats."""
        filters: dict = {'restaurant_id': ObjectId(restaurant_id)}

        if status_filter:
            filters['status'] = status_filter
        if date_from:
            filters['created_at__gte'] = datetime.fromisoformat(date_from)
        if date_to:
            dt_to = datetime.fromisoformat(date_to) + timedelta(days=1)
            filters['created_at__lt'] = dt_to

        paginated = self.paginate(page=page, page_size=page_size, **filters)

        # Summary via aggregation
        match_stage: dict = {'restaurant_id': rid} if (rid := ObjectId(restaurant_id)) else {}
        if status_filter:
            match_stage['status'] = status_filter
        if date_from:
            match_stage.setdefault('created_at', {})['$gte'] = datetime.fromisoformat(date_from)
        if date_to:
            match_stage.setdefault('created_at', {})['$lt'] = datetime.fromisoformat(date_to) + timedelta(days=1)

        summary_pipeline = [
            {'$match': match_stage},
            {'$facet': {
                'revenue': [
                    {'$match': {'status': {'$ne': 'cancelled'}}},
                    {'$group': {'_id': None, 'total': {'$sum': {'$toDouble': '$total'}}}},
                ],
                'delivered': [
                    {'$match': {'status': 'delivered'}},
                    {'$count': 'total'},
                ],
                'cancelled': [
                    {'$match': {'status': 'cancelled'}},
                    {'$count': 'total'},
                ],
            }},
        ]

        summary_result = self.aggregate(summary_pipeline)
        summary_data = summary_result[0] if summary_result else {}

        revenue_data = summary_data.get('revenue', [])
        delivered_data = summary_data.get('delivered', [])
        cancelled_data = summary_data.get('cancelled', [])

        result = paginated.to_dict()
        result['summary'] = {
            'total_revenue': revenue_data[0]['total'] if revenue_data else 0,
            'total_delivered': delivered_data[0]['total'] if delivered_data else 0,
            'total_cancelled': cancelled_data[0]['total'] if cancelled_data else 0,
        }

        return result
