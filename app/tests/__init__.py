"""
Test modules for the FastAPI application.

This package contains all the test modules for unit testing,
integration testing, and API testing.
"""

# Test for user creation with different roles
if __name__ == "__main__":
    import asyncio
    from sqlmodel import SQLModel, create_engine
    from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
    from app.models.user import UserCreate, UserRole
    from app.services.user_service import create_user

    async def test_create_user_with_roles():
        # Setup in-memory SQLite for testing
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            # Test default role
            user1 = await create_user(
                session,
                UserCreate(email="a@b.com", username="user1", password="passWord1!"),
            )
            assert user1.role == UserRole.USER
            # Test explicit admin role
            user2 = await create_user(
                session,
                UserCreate(
                    email="admin@b.com",
                    username="admin1",
                    password="passWord1!",
                    role=UserRole.ADMIN,
                ),
            )
            assert user2.role == UserRole.ADMIN
            # Test explicit guest role
            user3 = await create_user(
                session,
                UserCreate(
                    email="guest@b.com",
                    username="guest1",
                    password="passWord1!",
                    role=UserRole.GUEST,
                ),
            )
            assert user3.role == UserRole.GUEST
            print("User creation with roles test passed.")

    asyncio.run(test_create_user_with_roles())

    async def test_require_role():
        from fastapi import Depends, FastAPI
        from fastapi.testclient import TestClient
        from fastapi import status
        from app.models.user import User, UserRole
        from app.dependencies import require_role, get_current_active_user
        from datetime import datetime

        app = FastAPI()

        # Helper to create a dependency that returns a user with a given role
        def user_dep(role: UserRole):
            async def _dep():
                return User(
                    id=1,
                    email=f"{role}@b.com",
                    username=f"{role}",
                    hashed_password="x",
                    role=role,
                    is_active=True,
                    is_superuser=False,
                    is_verified=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

            return _dep

        @app.get("/admin")
        async def admin_route(current_user=Depends(require_role(UserRole.ADMIN))):
            return {"message": "admin access granted"}

        @app.get("/user")
        async def user_route(
            current_user=Depends(require_role(UserRole.USER, UserRole.ADMIN))
        ):
            return {"message": "user or admin access granted"}

        client = TestClient(app)

        # Test admin access with admin user
        app.dependency_overrides[get_current_active_user] = user_dep(UserRole.ADMIN)
        response = client.get("/admin")
        assert response.status_code == 200
        assert response.json()["message"] == "admin access granted"

        # Test admin access with user (should fail)
        app.dependency_overrides[get_current_active_user] = user_dep(UserRole.USER)
        response = client.get("/admin")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        # Test user access with user (should succeed)
        response = client.get("/user")
        assert response.status_code == 200
        assert response.json()["message"] == "user or admin access granted"

        # Test user access with guest (should fail)
        app.dependency_overrides[get_current_active_user] = user_dep(UserRole.GUEST)
        response = client.get("/user")
        assert response.status_code == status.HTTP_403_FORBIDDEN

        print("Role-based access control test passed.")

    asyncio.run(test_require_role())

    async def test_unverified_user_cannot_login():
        from app.models.user import User, UserRole
        from app.services.user_service import authenticate_user
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlmodel import SQLModel

        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=True)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        async with AsyncSession(engine) as session:
            # Create an unverified user
            from app.core.security import get_password_hash
            from app.models.user import User

            user = User(
                email="unverified@b.com",
                username="unverified",
                hashed_password=get_password_hash("Password1!"),
                is_active=True,
                is_verified=False,
                role=UserRole.USER,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            # Try to authenticate
            result = await authenticate_user(
                db=session,
                email_or_username="unverified@b.com",
                password="Password1!",
            )
            assert result is None
            print("Unverified user cannot login test passed.")

    asyncio.run(test_unverified_user_cannot_login())

    async def test_me_endpoint_requires_verified_user():
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from app.models.user import User, UserRole
        from app.dependencies import require_verified_user, get_current_active_user
        from datetime import datetime

        app = FastAPI()

        # Helper to create a dependency that returns a user with a given verification status
        def user_dep(is_verified: bool):
            async def _dep():
                return User(
                    id=1,
                    email="test@b.com",
                    username="test",
                    hashed_password="x",
                    role=UserRole.USER,
                    is_active=True,
                    is_superuser=False,
                    is_verified=is_verified,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow(),
                )

            return _dep

        @app.get("/me")
        async def me(current_user=Depends(require_verified_user)):
            return {"email": current_user.email}

        client = TestClient(app)

        # Test with verified user
        app.dependency_overrides[get_current_active_user] = user_dep(True)
        response = client.get("/me")
        assert response.status_code == 200
        assert response.json()["email"] == "test@b.com"

        # Test with unverified user
        app.dependency_overrides[get_current_active_user] = user_dep(False)
        response = client.get("/me")
        assert response.status_code == 403
        assert "Email not verified" in response.json()["detail"]

        print("/me endpoint requires verified user test passed.")

    asyncio.run(test_me_endpoint_requires_verified_user())

    async def test_users_endpoints():
        from fastapi import FastAPI, Depends
        from fastapi.testclient import TestClient
        from app.models.user import User, UserRole, UserUpdate
        from app.dependencies import get_current_active_user, get_db
        from sqlmodel import SQLModel
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from datetime import datetime
        import asyncio

        # Setup in-memory DB and FastAPI app
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        app = FastAPI()

        # Import and mount users router
        from app.api.v1.endpoints.users import router as users_router

        app.include_router(users_router, prefix="/users")

        # Create test users in DB
        async with AsyncSession(engine) as session:
            from app.models.user import User
            from app.core.security import get_password_hash

            admin = User(
                email="admin@b.com",
                username="admin",
                hashed_password=get_password_hash("Password1!"),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
            user = User(
                email="user@b.com",
                username="user",
                hashed_password=get_password_hash("Password1!"),
                role=UserRole.USER,
                is_active=True,
                is_verified=True,
            )
            other = User(
                email="other@b.com",
                username="other",
                hashed_password=get_password_hash("Password1!"),
                role=UserRole.USER,
                is_active=True,
                is_verified=True,
            )
            session.add_all([admin, user, other])
            await session.commit()
            await session.refresh(admin)
            await session.refresh(user)
            await session.refresh(other)
            admin_id, user_id, other_id = admin.id, user.id, other.id

        # Dependency overrides
        def db_dep():
            async def _dep():
                async with AsyncSession(engine) as session:
                    yield session

            return _dep

        def user_dep(user_obj):
            async def _dep():
                return user_obj

            return _dep

        app.dependency_overrides[get_db] = db_dep()

        client = TestClient(app)

        # GET /users/{id} as admin (should succeed for any user)
        app.dependency_overrides[get_current_active_user] = user_dep(admin)
        r = client.get(f"/users/{user_id}")
        assert r.status_code == 200
        assert r.json()["id"] == user_id

        # GET /users/{id} as self (should succeed)
        app.dependency_overrides[get_current_active_user] = user_dep(user)
        r = client.get(f"/users/{user_id}")
        assert r.status_code == 200
        assert r.json()["id"] == user_id

        # GET /users/{id} as other user (should fail)
        app.dependency_overrides[get_current_active_user] = user_dep(other)
        r = client.get(f"/users/{user_id}")
        assert r.status_code == 403

        # PUT /users/{id} as self (should succeed)
        app.dependency_overrides[get_current_active_user] = user_dep(user)
        r = client.put(f"/users/{user_id}", json={"first_name": "Updated"})
        assert r.status_code == 200
        assert r.json()["first_name"] == "Updated"

        # PUT /users/{id} as admin (should succeed)
        app.dependency_overrides[get_current_active_user] = user_dep(admin)
        r = client.put(f"/users/{user_id}", json={"last_name": "AdminEdit"})
        assert r.status_code == 200
        assert r.json()["last_name"] == "AdminEdit"

        # PUT /users/{id} as other user (should fail)
        app.dependency_overrides[get_current_active_user] = user_dep(other)
        r = client.put(f"/users/{user_id}", json={"first_name": "Hacker"})
        assert r.status_code == 403

        # DELETE /users/{id} as self (should succeed)
        app.dependency_overrides[get_current_active_user] = user_dep(user)
        r = client.delete(f"/users/{user_id}")
        assert r.status_code == 200
        assert r.json()["user_id"] == user_id

        # DELETE /users/{id} as admin (should succeed for other user)
        app.dependency_overrides[get_current_active_user] = user_dep(admin)
        r = client.delete(f"/users/{other_id}")
        assert r.status_code == 200
        assert r.json()["user_id"] == other_id

        # DELETE /users/{id} as other user (should fail for admin)
        app.dependency_overrides[get_current_active_user] = user_dep(other)
        r = client.delete(f"/users/{admin_id}")
        assert r.status_code == 403

        print("/users endpoints (GET, PUT, DELETE) tests passed.")

    asyncio.run(test_users_endpoints())

    async def test_password_reset_tokens():
        from app.services.password_reset_service import (
            create_password_reset_token,
            validate_password_reset_token,
            consume_password_reset_token,
        )
        from app.models.user import User, UserRole
        from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
        from sqlmodel import SQLModel
        from datetime import datetime, timedelta

        # Setup in-memory DB
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)

        async with AsyncSession(engine) as session:
            # Create test user
            from app.core.security import get_password_hash

            user = User(
                email="test@b.com",
                username="testuser",
                hashed_password=get_password_hash("Password1!"),
                is_active=True,
                is_verified=True,
                role=UserRole.USER,
            )
            session.add(user)
            await session.commit()
            await session.refresh(user)
            user_id = user.id

            # Test token creation
            token = await create_password_reset_token(session, user.id, user.username)
            assert token is not None
            assert len(token) > 20  # Should be a secure random token

            # Test token validation
            user_info = await validate_password_reset_token(session, token)
            assert user_info is not None
            assert user_info[0] == user_id  # user_id
            assert user_info[1] == "testuser"  # username

            # Test token consumption (single-use)
            consumed_info = await consume_password_reset_token(session, token)
            assert consumed_info is not None
            assert consumed_info[0] == user_id  # user_id
            assert consumed_info[1] == "testuser"  # username

            # Test token cannot be used again
            second_use = await consume_password_reset_token(session, token)
            assert second_use is None

            # Test invalid token
            invalid_info = await validate_password_reset_token(session, "invalid_token")
            assert invalid_info is None

            print("Password reset token tests passed.")

    asyncio.run(test_password_reset_tokens())

    async def test_password_reset_endpoints():
        from fastapi import FastAPI
        from fastapi.testclient import TestClient
        from app.models.user import User, UserRole
        from app.dependencies import get_db
        from sqlmodel import SQLModel
        from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
        from datetime import datetime

        # Setup in-memory DB and FastAPI app
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(SQLModel.metadata.create_all)
        app = FastAPI()

        # Import and mount auth router
        from app.api.v1.endpoints.auth import router as auth_router

        app.include_router(auth_router, prefix="/auth")

        # Create test user in DB
        async with AsyncSession(engine) as session:
            from app.core.security import get_password_hash

            user = User(
                email="test@b.com",
                username="testuser",
                hashed_password=get_password_hash("Password1!"),
                is_active=True,
                is_verified=True,
                role=UserRole.USER,
            )
            session.add(user)
            await session.commit()

        # Dependency overrides
        def db_dep():
            async def _dep():
                async with AsyncSession(engine) as session:
                    yield session

            return _dep

        app.dependency_overrides[get_db] = db_dep()
        client = TestClient(app)

        # Test forgot password endpoint
        response = client.post("/auth/forgot-password", json={"email": "test@b.com"})
        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"]

        # Test forgot password with non-existent email (should still return success)
        response = client.post(
            "/auth/forgot-password", json={"email": "nonexistent@b.com"}
        )
        assert response.status_code == 200
        assert "reset link has been sent" in response.json()["message"]

        # Test reset password with invalid token
        response = client.post(
            "/auth/reset-password",
            json={"token": "invalid_token", "new_password": "NewPassword1!"},
        )
        assert response.status_code == 400
        assert "Invalid or expired reset token" in response.json()["detail"]

        print("Password reset endpoint tests passed.")

    asyncio.run(test_password_reset_endpoints())
