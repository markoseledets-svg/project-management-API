from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Index, text
from sqlalchemy import DateTime
from datetime import datetime, timezone, timedelta
from typing import List
from enum import Enum
import uuid
import uuid6

class UserRole(str,Enum):
    OWNER = "owner"
    ADMIN = "admin"
    EDITOR = "editor"
    VIEWER = "viewer"

class ProjectStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    SUSPENDED = "suspended"

class InvitationStatus(str, Enum):
    PENDING = "pending"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    REVOKED = "revoked"
    EXPIRED = "expired"

class Base(DeclarativeBase):
    pass

class UserModel(Base):
    __tablename__ = "users"

    public_id: Mapped[uuid.UUID] = mapped_column(
                                                    primary_key=True,
                                                    nullable=False,
                                                    unique=True,
                                                    default=uuid6.uuid7
                                                  )
    email: Mapped[str] = mapped_column(nullable=False, unique=True)
    password: Mapped[str] = mapped_column(nullable=False)
    
    tokens: Mapped[List["RefreshTokenModel"]] = relationship(back_populates="user", passive_deletes=True)
    project_relation: Mapped[List["UserProjectRelation"]] = relationship(back_populates="user_relation", passive_deletes=True)
    invitation_sender_relation: Mapped[List["InvitationModel"]] = relationship(
        back_populates="sender_relation", 
        passive_deletes=True, 
        foreign_keys='[InvitationModel.sender_public_id]'
        )
    invitation_relation: Mapped[List["InvitationModel"]] = relationship(
        back_populates="invited_user_relation", 
        passive_deletes=True, 
        foreign_keys='[InvitationModel.target_user_public_id]'
        )

class RefreshTokenModel(Base):
    __tablename__ = "refresh_tokens"

    token_public_id: Mapped[uuid.UUID] = mapped_column(
                                                            primary_key = True,
                                                            nullable = False,
                                                            unique = True,
                                                            default=uuid6.uuid7
                                                        )
    user_public_id: Mapped[uuid.UUID] = mapped_column(
                                                        ForeignKey("users.public_id", ondelete="CASCADE"), 
                                                        nullable=False
                                                    )
    created_at: Mapped[datetime] = mapped_column(
                                                    DateTime(timezone=True), 
                                                    default=lambda: datetime.now(timezone.utc)
                                                )
    expired_at: Mapped[datetime] = mapped_column(
                                                DateTime(timezone=True),
                                                default= lambda: datetime.now(timezone.utc) + timedelta(days=14)
                                                )
    family_id: Mapped[uuid.UUID] = mapped_column(nullable=False, default=uuid6.uuid8)
    is_used: Mapped[bool] = mapped_column(nullable=False, default=False)
    user_agent: Mapped[str] = mapped_column(nullable=True)

    user: Mapped["UserModel"] = relationship(back_populates="tokens")

class TaskModel(Base):
    __tablename__ = "tasks"

    task_public_id: Mapped[uuid.UUID] = mapped_column(
                                                        primary_key=True,
                                                        nullable=False,
                                                        unique=True,
                                                        default=uuid6.uuid7
                                                    )
    project_public_id: Mapped[uuid.UUID] = mapped_column(
                                                            ForeignKey("projects.project_public_id", ondelete="CASCADE"),
                                                            nullable=False
                                                        )
    task_name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[bool] = mapped_column(default=False)

    project_relation: Mapped["ProjectModel"] = relationship(back_populates="task_relation")

class ProjectModel(Base):
    __tablename__ = "projects"

    project_public_id: Mapped[uuid.UUID] = mapped_column(
                                                            primary_key=True,
                                                            nullable=False,
                                                            unique=True,
                                                            default=uuid6.uuid7
                                                        )
    project_name: Mapped[str] = mapped_column(nullable=False)
    status: Mapped[ProjectStatus] = mapped_column(
                                                    nullable=False, 
                                                    default=ProjectStatus.ACTIVE
                                                )   
    created_at: Mapped[datetime] = mapped_column(
                                                    DateTime(timezone=True),
                                                    default=lambda: datetime.now(timezone.utc)
                                                )
    updated_at: Mapped[datetime] = mapped_column(
                                                    DateTime(timezone=True),
                                                    onupdate= lambda: datetime.now(timezone.utc),
                                                    default=lambda: datetime.now(timezone.utc)
                                                )
    user_relation: Mapped[List["UserProjectRelation"]] = relationship(back_populates="project_relation", passive_deletes=True)
    task_relation: Mapped[List["TaskModel"]] = relationship(back_populates="project_relation", passive_deletes=True)
    invitation_relation: Mapped[List["InvitationModel"]] = relationship(back_populates="project_relation", passive_deletes=True)

class UserProjectRelation(Base):
    __tablename__ = "user_project_relation"
    __table_args__ = (
        Index(
        "ix_unique_owner_per_project", 
        "project_public_id", 
        unique=True, 
        postgresql_where=text("user_role = 'OWNER'")),
    )
    user_public_id: Mapped[uuid.UUID] = mapped_column(
                                                        ForeignKey("users.public_id", ondelete="CASCADE"),
                                                        primary_key=True
                                                    )
    project_public_id: Mapped[uuid.UUID] = mapped_column( 
                                                            ForeignKey("projects.project_public_id", ondelete="CASCADE"),
                                                            primary_key=True
                                                        )
    user_role: Mapped[UserRole] = mapped_column(nullable=False)

    user_relation: Mapped["UserModel"] = relationship(back_populates="project_relation")
    project_relation: Mapped["ProjectModel"] = relationship(back_populates="user_relation")

class InvitationModel(Base):
    __tablename__ = "invitations"
    __table_args__ = (
        Index(
            "ix_unique_project_invite",
            "project_public_id",
            "target_user_public_id",
            unique=True,
            postgresql_where=text("status = 'PENDING'")
        ),
    )
    invitation_public_id: Mapped[uuid.UUID] = mapped_column(
                                                                primary_key=True,
                                                                nullable=False,
                                                                unique=True,
                                                                default=uuid6.uuid7
                                                            )
    project_public_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.project_public_id", ondelete="CASCADE"))
    sender_public_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.public_id", ondelete="CASCADE"))
    target_user_public_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.public_id", ondelete="CASCADE"))
    sent_at: Mapped[datetime] = mapped_column(
                                                DateTime(timezone=True),
                                                default=lambda: datetime.now(timezone.utc)
                                                )
    expires_at: Mapped[datetime] = mapped_column(
                                                DateTime(timezone=True),
                                                default=lambda: datetime.now(timezone.utc) + timedelta(days=7)
                                                )
    resolved_at: Mapped[datetime] = mapped_column(
                                                    DateTime(timezone=True),
                                                    nullable=True,
                                                    default=None
                                                    )
    status: Mapped[InvitationStatus] = mapped_column(nullable=False, default=InvitationStatus.PENDING)
    user_role: Mapped[UserRole] = mapped_column(nullable=False)

    sender_relation: Mapped["UserModel"] = relationship(
        back_populates="invitation_sender_relation",
        foreign_keys=[sender_public_id]
    )
    invited_user_relation: Mapped["UserModel"] = relationship(
        back_populates="invitation_relation",
        foreign_keys=[target_user_public_id]
    )
    project_relation: Mapped["ProjectModel"] = relationship(back_populates="invitation_relation")
    