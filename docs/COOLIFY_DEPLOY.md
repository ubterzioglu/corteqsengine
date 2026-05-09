# Coolify Deploy

Recommended setup: one Coolify `Docker Compose` application with two services:
- `frontend`: React build served by Nginx
- `backend`: FastAPI app on port `8001`

Use `docker-compose.coolify.yml` from the repo root as the compose file.

## Why this layout

- The frontend proxies `/api/*` requests to the internal backend service name `backend:8001`.
- That lets the browser use the same public domain with no frontend runtime env required.
- Backend secrets stay only on the backend container.

## Required Coolify envs

Start from `coolify.env.example` and add these in Coolify:

- `CORS_ORIGINS`
- `SUPABASE_URL`
- `SUPABASE_SERVICE_KEY`
- `NEO4J_URI`
- `NEO4J_USER`
- `NEO4J_PASSWORD`
- `NEO4J_DATABASE`
- `ELASTICSEARCH_CLOUD_ID`
- `ELASTICSEARCH_API_KEY`

Optional:

- `EMERGENT_LLM_KEY`
- `SLACK_BOT_TOKEN`
- `GITHUB_TOKEN`
- `GOOGLE_SERVICE_ACCOUNT_JSON`
- `TEST_USER_ID`
- `TEST_EMAIL`
- `TEST_SESSION_TOKEN`

## Coolify steps

1. Create a new `Docker Compose` application from this repo.
2. Set compose path to `docker-compose.coolify.yml`.
3. Expose the `frontend` service publicly.
4. Keep `backend` internal only.
5. Add environment variables from `coolify.env.example`.
6. Deploy.

## Notes

- Backend health check: `GET /api/health`
- Frontend health check: `/`
- Neo4j driver now falls back to `neo4j+ssc://` if strict Aura TLS routing fails in the deployment environment.
- `emergentintegrations` is no longer a hard install dependency, so deploys will not fail if that package is unavailable.
