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
- **Collections**: users, user_sessions, data_sources, knowledge_nodes, chat_messages, activities

## AI Integration
- **Provider**: Gemini (via Emergent LLM Key)
- **Model**: gemini-2.5-pro
