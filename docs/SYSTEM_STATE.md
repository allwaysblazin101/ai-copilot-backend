# AI Copilot Backend — System State

## Current status
Backend is stabilized and pushed to GitHub.

Stable branch:
- `main`

Stable checkpoint tag:
- `v0.1-stable` (create if not already pushed)

## Verified working

### Core backend
- FastAPI app starts successfully
- Root route `/` responds
- Startup check works
- Backend tests pass

### Messaging / SMS
- Twilio webhook `/sms/webhook` works
- Weather SMS replies work
- Email SMS replies work
- Background follow-up SMS works
- TwiML immediate reply path works
- Direct Twilio REST send works

### Email
- Gmail auth works
- Email inbox reading works
- Email summarization works
- SMS-triggered inbox summary works

### Calendar
- Google Calendar auth works
- Calendar listing works
- Calendar event creation path works

### Brain / planner / tools
- `ToolRouter.execute()` async flow fixed
- `MasterBrain.process_query()` is current interface
- planner/context mismatch cleaned up
- policy/tool guard cleaned up
- weather tool fixed
- web search path works

### Uber Eats sandbox
- sandbox token generation works
- `/v1/eats/stores` works
- test store is provisioned
- store visible to app
- store active
- merchant side login works
- merchant side shows store open / accepting orders

## Known issues / constraints

### Twilio trial limit
- Long outbound SMS failed with Twilio error `30044`
- Cause: Twilio trial message length exceeded
- Fix: keep background summary SMS short (~140 chars)
- Use short follow-up summaries instead of long paragraphs

### Uber Eats
- Merchant-side sandbox integration is working
- Consumer-side sandbox ordering still depends on Uber providing test customer/eater credentials

### SMS behavior
- Fast/simple tasks should return directly via TwiML
- slower tasks (like email summary) should:
  1. acknowledge immediately
  2. do work in background
  3. send short follow-up SMS

## Tests
Current backend test suite status:
- `12 passed`

Run tests with:

```bash
pytest backend/tests -q