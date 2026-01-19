# Authentication Migration Plan: JWT → Clerk/Supabase

## Current State (Phase 2 MVP)

PrepPilot currently uses **JWT-based authentication** with the following components:

### Implementation
- **Password Hashing**: bcrypt via passlib
- **Token Generation**: python-jose for JWT encoding/decoding
- **Token Storage**: Client-side (localStorage or secure cookie)
- **Session Management**: Stateless JWT with 7-day expiration
- **User Model**: Custom User table with email, hashed_password, and basic profile fields

### Files
- [`backend/auth/jwt.py`](../backend/auth/jwt.py) - Token generation and validation
- [`backend/auth/utils.py`](../backend/auth/utils.py) - Password hashing utilities
- [`backend/api/dependencies.py`](../backend/api/dependencies.py) - Auth dependency injection
- [`backend/api/routes/auth.py`](../backend/api/routes/auth.py) - Register, login, /me endpoints
- [`backend/db/models.py`](../backend/db/models.py) - User model with hashed_password field

## Why Migrate?

Moving to **Clerk** or **Supabase Auth** provides:

1. **Security**: Enterprise-grade auth without rolling your own
2. **Features**: MFA, SSO, OAuth providers (Google, GitHub, etc.)
3. **Less Maintenance**: No password reset flows, email verification, etc.
4. **Better UX**: Pre-built UI components and session management
5. **Scalability**: Battle-tested infrastructure

## Migration Path

### Option A: Clerk

**Advantages:**
- Beautiful pre-built React components
- Excellent developer experience
- Built-in user management dashboard
- Strong TypeScript support

**Migration Steps:**
1. Install Clerk SDK: `npm install @clerk/clerk-sdk-node`
2. Replace JWT validation with Clerk's `verifyToken()`
3. Update `get_current_user` dependency to use Clerk session
4. Keep User model but remove `hashed_password` field
5. Add `clerk_user_id` column to User table
6. Migrate existing users:
   - Export user emails
   - Send password reset emails via Clerk
   - Map Clerk IDs to existing User records

**Code Changes:**
```python
# backend/api/dependencies.py
from clerk_backend_api import Clerk

clerk = Clerk(bearer_auth=settings.clerk_secret_key)

async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> User:
    token = authorization.replace("Bearer ", "")

    # Verify with Clerk
    try:
        session = clerk.sessions.verify_session(token)
        clerk_user_id = session.user_id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Find user by Clerk ID
    user = db.query(User).filter(User.clerk_user_id == clerk_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
```

### Option B: Supabase Auth

**Advantages:**
- Integrated with Supabase database (if using Supabase Postgres)
- Open source
- RLS (Row Level Security) policies
- Built-in storage and realtime subscriptions

**Migration Steps:**
1. Install Supabase client: `pip install supabase`
2. Replace JWT validation with Supabase's `auth.get_user()`
3. Update `get_current_user` dependency
4. Add `supabase_user_id` column to User table
5. Migrate existing users similarly to Clerk

**Code Changes:**
```python
# backend/api/dependencies.py
from supabase import create_client

supabase = create_client(settings.supabase_url, settings.supabase_key)

async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_db),
) -> User:
    token = authorization.replace("Bearer ", "")

    # Verify with Supabase
    try:
        user_response = supabase.auth.get_user(token)
        supabase_user_id = user_response.user.id
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid token")

    # Find user by Supabase ID
    user = db.query(User).filter(User.supabase_user_id == supabase_user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user
```

## Database Schema Changes

### Current Schema
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,  -- Remove this
    full_name VARCHAR(255),
    diet_type VARCHAR(50),
    is_active BOOLEAN,
    created_at TIMESTAMP
);
```

### New Schema (Clerk)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    clerk_user_id VARCHAR(255) UNIQUE NOT NULL,  -- Add this
    email VARCHAR(255) UNIQUE NOT NULL,
    -- hashed_password removed
    full_name VARCHAR(255),
    diet_type VARCHAR(50),
    is_active BOOLEAN,
    created_at TIMESTAMP
);
```

### New Schema (Supabase)
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    supabase_user_id UUID UNIQUE NOT NULL,  -- Add this
    email VARCHAR(255) UNIQUE NOT NULL,
    -- hashed_password removed
    full_name VARCHAR(255),
    diet_type VARCHAR(50),
    is_active BOOLEAN,
    created_at TIMESTAMP
);
```

## Files to Update

1. **Remove:**
   - `backend/auth/jwt.py`
   - `backend/auth/utils.py` (password hashing)
   - `backend/api/routes/auth.py` (register/login endpoints)

2. **Update:**
   - `backend/api/dependencies.py` - New auth verification logic
   - `backend/db/models.py` - Remove hashed_password, add external_user_id
   - `backend/config.py` - Add Clerk/Supabase API keys

3. **Alembic Migration:**
   ```bash
   alembic revision -m "Migrate to Clerk auth"
   # Add external_user_id column
   # Remove hashed_password column
   ```

## Frontend Changes

### Current (JWT)
```typescript
// Login flow
const response = await fetch('/auth/login', {
  method: 'POST',
  body: JSON.stringify({ email, password })
});
const { access_token } = await response.json();
localStorage.setItem('token', access_token);
```

### With Clerk
```typescript
import { ClerkProvider, SignIn, useUser } from '@clerk/clerk-react';

// No manual token management!
function App() {
  return (
    <ClerkProvider publishableKey={CLERK_KEY}>
      <SignIn />
      {/* Clerk handles everything */}
    </ClerkProvider>
  );
}
```

### With Supabase
```typescript
import { createClient } from '@supabase/supabase-js';

const supabase = createClient(SUPABASE_URL, SUPABASE_KEY);

// Login
const { data, error } = await supabase.auth.signInWithPassword({
  email,
  password
});
```

## Rollout Strategy

### Phase 1: Dual Auth Support
- Keep JWT auth working
- Add Clerk/Supabase as optional
- Allow users to migrate voluntarily

### Phase 2: Gradual Migration
- New users use Clerk/Supabase only
- Existing users prompted to migrate
- Send migration emails

### Phase 3: Deprecation
- Set sunset date for JWT auth
- Final migration push
- Remove JWT code

## Environment Variables

### Add to `.env`:
```bash
# Clerk
CLERK_SECRET_KEY=sk_test_...
CLERK_PUBLISHABLE_KEY=pk_test_...

# OR Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=eyJh...
SUPABASE_SERVICE_KEY=eyJh...
```

## Testing

1. Create test accounts in Clerk/Supabase dashboard
2. Update integration tests to use new auth flow
3. Test migration script with sample users
4. Verify existing meal plans/fridge items remain accessible

## Recommendation

**Use Clerk** for PrepPilot because:
- Better DX for a solo founder
- Beautiful pre-built UI components
- Simpler integration (don't need full Supabase stack)
- More flexible pricing for MVP

The migration can be done in **Phase 4** (Beta Polish) or later, as the current JWT implementation is sufficient for MVP.

## Resources

- [Clerk FastAPI Guide](https://clerk.com/docs/backend-requests/handling/python)
- [Supabase Python Client](https://supabase.com/docs/reference/python/introduction)
- [FastAPI Security Best Practices](https://fastapi.tiangolo.com/tutorial/security/)
