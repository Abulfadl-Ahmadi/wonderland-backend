from .base import WONDERLAND_STAGE


if WONDERLAND_STAGE == "production":
    from .production import *
elif WONDERLAND_STAGE == "development":
    from .local import *
else:
    from .test import *
