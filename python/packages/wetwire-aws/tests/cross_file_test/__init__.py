"""
Cross-file reference test package.

This simulates a user project structure where:
- Multiple files define resources with @wetwire_aws
- Files use `from . import *` to import resources
- Resources in one file reference resources from another file

This is the recommended user pattern and MUST work correctly.
"""

from wetwire_aws.loader import setup_resources

setup_resources(__file__, __name__, globals(), generate_stubs=False)
