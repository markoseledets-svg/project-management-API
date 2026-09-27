import pytest
from jobs.cleanup_jobs import daily_cleanup_job, expire_invitations_job
from sqlalchemy import select, inspect
from database.db_model import InvitationModel, InvitationStatus

async def _get_data_by_id(db_session, instance):
    model = type(instance)
    model_pk = inspect(model).primary_key[0]
    pk_value = getattr(instance, model_pk.name)
    result = await db_session.execute(
        select(model_pk)
        .where(model_pk == pk_value)
    )
    return result.scalar_one_or_none()

async def _get_invitation_status(db_session, invitation_public_id):
    status = await db_session.execute(
        select(InvitationModel.status)
        .where(InvitationModel.invitation_public_id == invitation_public_id)
    )
    return status.scalar_one_or_none()

@pytest.mark.asyncio
async def test_cleanup(deleted_user, expired_token, old_rejected_invitation, db_session):
    await db_session.commit()
    await daily_cleanup_job()
    assert await _get_data_by_id(db_session, deleted_user) is None
    assert await _get_data_by_id(db_session, expired_token) is None
    assert await _get_data_by_id(db_session, old_rejected_invitation) is None

@pytest.mark.asyncio
async def test_invitation_expiration(db_session, expired_invitation):
    await db_session.commit()
    await expire_invitations_job()
    assert await _get_invitation_status(db_session, expired_invitation.invitation_public_id) == InvitationStatus.EXPIRED

@pytest.mark.asyncio
async def test_cleanup_valid_data_cleanup(test_user, test_refresh_record, test_invitation, db_session):
    await db_session.commit()
    await daily_cleanup_job()
    assert await _get_data_by_id(db_session, test_user) is not None
    assert await _get_data_by_id(db_session, test_refresh_record) is not None
    assert await _get_data_by_id(db_session, test_invitation) is not None
    
    await db_session.delete(test_invitation)
    await db_session.delete(test_refresh_record)
    await db_session.delete(test_user)
    await db_session.commit()

@pytest.mark.asyncio
async def test_cleanup_valid_invitation(test_invitation, db_session):
    await db_session.commit()
    await expire_invitations_job()
    assert await _get_invitation_status(db_session, test_invitation.invitation_public_id) == InvitationStatus.PENDING

    await db_session.delete(test_invitation)
    await db_session.commit()
    