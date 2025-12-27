"""Role resource defined in a separate file."""

from __future__ import annotations

from wetwire_aws import wetwire_aws
from wetwire_aws.resources.iam import Role

__all__ = ["AppRole"]


@wetwire_aws
class AppRole:
    """IAM role for the application."""

    resource: Role
    role_name = "app-role"
    assume_role_policy_document: dict = None
