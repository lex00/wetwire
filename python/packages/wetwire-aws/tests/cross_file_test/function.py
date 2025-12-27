"""Lambda function that references role from another file."""

from __future__ import annotations

from graph_refs import Attr

from wetwire_aws import wetwire_aws
from wetwire_aws.intrinsics.refs import ARN
from wetwire_aws.resources.lambda_ import Function

__all__ = ["AppFunction"]


@wetwire_aws
class AppFunction:
    """Lambda function that uses the AppRole."""

    resource: Function
    function_name = "app-function"
    runtime = "python3.12"
    handler = "index.handler"
    # Cross-file reference using Attr annotation
    # AppRole is injected by setup_resources() before this module executes
    role: Attr[AppRole, ARN] = None  # noqa: F821
