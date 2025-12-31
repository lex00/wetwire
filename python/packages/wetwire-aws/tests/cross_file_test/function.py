"""Lambda function that references role from another file."""

from __future__ import annotations

from wetwire_aws import wetwire_aws
from wetwire_aws.resources.lambda_ import Function

__all__ = ["AppFunction"]


@wetwire_aws
class AppFunction:
    """Lambda function that uses the AppRole."""

    resource: Function
    function_name = "app-function"
    runtime = "python3.12"
    handler = "index.handler"
    # Cross-file reference using no-parens pattern
    # AppRole is injected by setup_resources() before this module executes
    role = AppRole.Arn  # noqa: F821
