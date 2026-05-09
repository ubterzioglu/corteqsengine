# CorteQS Test Credentials

## Test User Account
- **User ID**: user_test123456
- **Email**: test@corteqs.com
- **Name**: Test User
- **Session Token**: test_session_corteqs
- **Role**: user

## Production Authentication
- **Method**: Google OAuth via Emergent Auth
- **Provider**: https://auth.emergentagent.com
- **Redirect**: /dashboard

## API Testing
```bash
# Base URL
API_URL="https://27c4ad23-b20f-41cf-b584-cd36c03b1a52.preview.emergentagent.com"

# Auth Header
Authorization: Bearer test_session_corteqs

# Example
curl -X GET "$API_URL/api/auth/me" -H "Authorization: Bearer test_session_corteqs"
```

## Database
- **Database**: corteqs_engine
- **Collections**: users, user_sessions, data_sources, knowledge_nodes, chat_messages, activities, documents

## Connected Services (v2.0)

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
- **Status**: ✅ Connected
- **Service Account**: corteqs-drive-sync@gen-lang-client-0322325978.iam.gserviceaccount.com
- **Note**: Share files/folders with service account email to enable sync

### Elasticsearch Cloud
- **Status**: ✅ Connected
- **Cluster**: adb1c0a104f444d5aa0a2c163e0012f4
- **Version**: 9.4.0
- **Documents Indexed**: 11

## AI Integration
- **Provider**: Gemini (via Emergent LLM Key)
- **Model**: gemini-2.5-pro
