"""Tests for conditional value support."""

from wetwire import Context, match, when
from wetwire.conditions import MatchCondition, WhenCondition


class TestWhenCondition:
    """Tests for when() conditional."""

    def test_when_with_true_condition(self):
        """Test when() with static True condition."""
        result = when(True, then="yes", else_="no")
        assert isinstance(result, WhenCondition)

        ctx = Context()
        assert result.resolve(ctx) == "yes"

    def test_when_with_false_condition(self):
        """Test when() with static False condition."""
        result = when(False, then="yes", else_="no")

        ctx = Context()
        assert result.resolve(ctx) == "no"

    def test_when_with_callable_condition(self):
        """Test when() with callable condition."""
        result = when(
            lambda ctx: ctx.environment == "prod",
            then="large",
            else_="small",
        )

        prod_ctx = Context(environment="prod")
        dev_ctx = Context(environment="dev")

        assert result.resolve(prod_ctx) == "large"
        assert result.resolve(dev_ctx) == "small"

    def test_when_with_complex_values(self):
        """Test when() with complex then/else values."""
        result = when(
            True,
            then={"size": "large", "count": 10},
            else_={"size": "small", "count": 1},
        )

        ctx = Context()
        resolved = result.resolve(ctx)
        assert resolved == {"size": "large", "count": 10}


class TestMatchCondition:
    """Tests for match() conditional."""

    def test_match_with_direct_value(self):
        """Test match() with direct value matching."""
        result = match(
            "prod",
            {
                "prod": "large",
                "staging": "medium",
                "dev": "small",
            },
            default="tiny",
        )

        ctx = Context()
        assert result.resolve(ctx) == "large"

    def test_match_with_callable_value(self):
        """Test match() with callable that returns value."""
        result = match(
            lambda ctx: ctx.environment,
            {
                "prod": "db.r5.large",
                "staging": "db.t3.medium",
                "dev": "db.t3.micro",
            },
            default="db.t3.nano",
        )

        prod_ctx = Context(environment="prod")
        dev_ctx = Context(environment="dev")
        unknown_ctx = Context(environment="unknown")

        assert result.resolve(prod_ctx) == "db.r5.large"
        assert result.resolve(dev_ctx) == "db.t3.micro"
        assert result.resolve(unknown_ctx) == "db.t3.nano"

    def test_match_with_default(self):
        """Test match() falls back to default."""
        result = match(
            "unknown",
            {"a": 1, "b": 2},
            default=0,
        )

        ctx = Context()
        assert result.resolve(ctx) == 0

    def test_match_without_default(self):
        """Test match() with no default returns None."""
        result = match(
            "unknown",
            {"a": 1, "b": 2},
        )

        ctx = Context()
        assert result.resolve(ctx) is None

    def test_match_with_complex_values(self):
        """Test match() with complex mapped values."""
        result = match(
            lambda ctx: ctx.environment,
            {
                "prod": {"replicas": 3, "memory": "4Gi"},
                "dev": {"replicas": 1, "memory": "512Mi"},
            },
            default={"replicas": 1, "memory": "256Mi"},
        )

        prod_ctx = Context(environment="prod")
        resolved = result.resolve(prod_ctx)
        assert resolved == {"replicas": 3, "memory": "4Gi"}


class TestConditionIntegration:
    """Integration tests for conditions with wetwire."""

    def test_when_in_resource(self):
        """Test when() used in a resource definition."""
        from wetwire import wetwire

        @wetwire
        class Database:
            size: WhenCondition = when(
                lambda ctx: ctx.environment == "prod",
                then="large",
                else_="small",
            )

        db = Database()
        # The field stores the conditional, resolution happens at serialization
        assert isinstance(db.size, WhenCondition)

    def test_match_in_resource(self):
        """Test match() used in a resource definition."""
        from wetwire import wetwire

        @wetwire
        class Server:
            instance_type: MatchCondition = match(
                lambda ctx: ctx.environment,
                {
                    "prod": "m5.xlarge",
                    "dev": "t3.micro",
                },
                default="t3.nano",
            )

        server = Server()
        assert isinstance(server.instance_type, MatchCondition)
