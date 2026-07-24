from pydantic import BaseModel, EmailStr
from uuid import UUID
from datetime import datetime
from database.db_model import InvitationStatus, UserRole

class InvitationPostModel(BaseModel):
    email: EmailStr
    user_role: UserRole

class InvitationWithEmailsModel(BaseModel):
    invitation_public_id: UUID
    status: InvitationStatus
    user_role: UserRole
    sent_at: datetime
    expires_at: datetime
    sender_email: EmailStr

class InvitationDashboardModel(InvitationWithEmailsModel):
    invited_user_email: EmailStr

class InvitationNotificationModel(InvitationWithEmailsModel):
    project_name: str