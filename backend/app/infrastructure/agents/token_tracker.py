"""Token usage tracking for per-user cost monitoring and billing."""

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Dict, Optional

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

# Pricing per 1M tokens (as of 2025)
PRICING = {
    "gpt-4o-mini": {"input": 0.150, "output": 0.600},
    "gpt-4o": {"input": 5.00, "output": 15.00},
    "gpt-4o-realtime-preview": {"input": 5.00, "output": 20.00},
}


class TokenTracker:
    """Track token usage per user for cost monitoring and billing."""

    def __init__(self, db_session: "AsyncSession") -> None:
        """Initialize token tracker with database session.

        Args:
            db_session: AsyncSession for database operations
        """
        self.db = db_session

    def calculate_cost(
        self, model: str, input_tokens: int, output_tokens: int
    ) -> float:
        """Calculate cost in USD for token usage.

        Args:
            model: Model name (e.g., 'gpt-4o-mini')
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens

        Returns:
            Cost in USD (float)
        """
        if model not in PRICING:
            return 0.0

        input_cost = (input_tokens / 1_000_000) * PRICING[model]["input"]
        output_cost = (output_tokens / 1_000_000) * PRICING[model]["output"]

        return input_cost + output_cost

    async def track_usage(
        self,
        user_id: int,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        trace_id: Optional[str] = None,
        operation: Optional[str] = None,
        latency_ms: Optional[int] = None,
        status: str = "success",
        error_message: Optional[str] = None,
    ) -> None:
        """Track agent usage and update token counts.

        Args:
            user_id: User ID for tracking
            agent_name: Name of the agent (e.g., 'SummarizationAgent')
            model: Model used (e.g., 'gpt-4o-mini')
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            trace_id: Langfuse trace ID for linking
            operation: Operation type (e.g., 'summarize_post')
            latency_ms: Response latency in milliseconds
            status: Status of the call ('success' or 'error')
            error_message: Error message if status is 'error'
        """
        from sqlalchemy import and_, select, update

        from backend.app.infrastructure.database.models import (
            AgentCall,
            UserTokenUsage,
        )

        today = date.today()
        total_tokens = input_tokens + output_tokens
        cost_usd = self.calculate_cost(model, input_tokens, output_tokens)

        # Update daily aggregate
        stmt = select(UserTokenUsage).where(
            and_(
                UserTokenUsage.user_id == user_id,
                UserTokenUsage.date == today,
                UserTokenUsage.model == model,
            )
        )
        usage_record = await self.db.scalar(stmt)

        if usage_record:
            update_stmt = (
                update(UserTokenUsage)
                .where(UserTokenUsage.id == usage_record.id)
                .values(
                    input_tokens=UserTokenUsage.input_tokens + input_tokens,
                    output_tokens=UserTokenUsage.output_tokens + output_tokens,
                    total_tokens=UserTokenUsage.total_tokens + total_tokens,
                    cost_usd=UserTokenUsage.cost_usd + Decimal(str(cost_usd)),
                    request_count=UserTokenUsage.request_count + 1,
                )
            )
            await self.db.execute(update_stmt)
        else:
            usage_record = UserTokenUsage(
                user_id=user_id,
                date=today,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
                cost_usd=Decimal(str(cost_usd)),
                request_count=1,
            )
            self.db.add(usage_record)

        # Record individual call
        call = AgentCall(
            user_id=user_id,
            trace_id=trace_id,
            agent_name=agent_name,
            operation=operation,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=Decimal(str(cost_usd)),
            latency_ms=latency_ms,
            status=status,
            error_message=error_message,
        )
        self.db.add(call)
        await self.db.commit()

    async def get_user_usage(
        self,
        user_id: int,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict:
        """Get token usage summary for a user.

        Args:
            user_id: User ID to query
            start_date: Start date for query (optional)
            end_date: End date for query (optional)

        Returns:
            Dictionary with usage statistics
        """
        from sqlalchemy import and_, select

        from backend.app.infrastructure.database.models import UserTokenUsage

        stmt = select(UserTokenUsage).where(UserTokenUsage.user_id == user_id)

        if start_date:
            stmt = stmt.where(UserTokenUsage.date >= start_date)
        if end_date:
            stmt = stmt.where(UserTokenUsage.date <= end_date)

        usage_records = await self.db.scalars(stmt)
        usage_list = list(usage_records)

        total_tokens = sum(u.total_tokens for u in usage_list)
        total_cost = sum(float(u.cost_usd) for u in usage_list)
        total_requests = sum(u.request_count for u in usage_list)

        return {
            "total_tokens": total_tokens,
            "total_cost_usd": total_cost,
            "requests": total_requests,
            "by_model": self._group_by_model(usage_list),
            "by_date": self._group_by_date(usage_list),
        }

    @staticmethod
    def _group_by_model(usage_records: list) -> Dict:
        """Group usage records by model."""
        models: Dict = {}
        for u in usage_records:
            if u.model not in models:
                models[u.model] = {"tokens": 0, "cost": 0.0, "requests": 0}
            models[u.model]["tokens"] += u.total_tokens
            models[u.model]["cost"] += float(u.cost_usd)
            models[u.model]["requests"] += u.request_count
        return models

    @staticmethod
    def _group_by_date(usage_records: list) -> Dict:
        """Group usage records by date."""
        dates: Dict = {}
        for u in usage_records:
            date_key = str(u.date)
            if date_key not in dates:
                dates[date_key] = {"tokens": 0, "cost": 0.0, "requests": 0}
            dates[date_key]["tokens"] += u.total_tokens
            dates[date_key]["cost"] += float(u.cost_usd)
            dates[date_key]["requests"] += u.request_count
        return dates
