# CorteQS Test Credentials

## Test User Account (Seeded in Supabase)
- **User ID**: `user_test123456`
- **Email**: `test@corteqs.com`
- **Name**: Test User
- **Session Token**: `test_session_corteqs`
- **Role**: user
- **Seed script**: `python3 /app/backend/seed_test_user.py`

## Production Authentication
- **Method**: Google OAuth via Emergent Auth
- **Provider**: https://auth.emergentagent.com
- **Redirect**: `/dashboard`

## API Testing
```bash
API_URL=$(grep REACT_APP_BACKEND_URL /app/frontend/.env | cut -d= -f2)
# Use Authorization Bearer header with the session token above:
curl -X GET "$API_URL/api/auth/me" -H "Authorization: Bearer test_session_corteqs"
```

## Primary Database (Supabase / PostgreSQL)
- **URL**: https://hvzkpkhptgdbowucvypt.supabase.co
- **Schema**: `/app/backend/sql/schema.sql`
- **Tables**: `users`, `user_sessions`, `data_sources`, `knowledge_nodes`, `chat_messages`, `activities`, `documents`
- **Auth**: Service role key (RLS bypassed for backend-only access)

## Connected Services

### Slack
- **Workspace**: CorteQS
- **Team ID**: T0B3CRXTQD6
- **Bot User**: corteqssocial
- **Token Type**: xoxe (user token)

### GitHub
- **User**: @ubterzioglu
- **Repos**: 67 total
- **Token Type**: Fine-grained PAT

### Neo4j Aura
- **Instance**: corteqs
- **URI**: neo4j+s://2874d84c.databases.neo4j.io
- **Database**: neo4j
- **User**: neo4j

### Google Drive
- **Status**: Connected
- **Service Account**: corteqs-drive-sync@gen-lang-client-0322325978.iam.gserviceaccount.com

### Elasticsearch Cloud
- **Status**: Connected
- **Cluster**: adb1c0a104f444d5aa0a2c163e0012f4
- **Version**: 9.4.0

## AI Integration
- **Provider**: Gemini (via Emergent LLM Key)
- **Model**: gemini-2.5-pro
