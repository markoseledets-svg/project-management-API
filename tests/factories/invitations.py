from tests.factories.base import BaseFactory
from datetime import datetime, timedelta, timezone

from database.db_model import InvitationModel

class InvitationFactory(BaseFactory):
    __model__ = InvitationModel

    @classmethod
    def expires_at(cls) -> datetime:
        return datetime.now(timezone.utc) + timedelta(days=7)