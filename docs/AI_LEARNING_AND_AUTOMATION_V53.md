# Governed AI learning and automation (V53)

The platform now has one project-scoped AI agent for editor, event, guest, RSVP,
analytics, materials, account-usage, publishing, and archival workflows. Legacy AI
entry points route to the same agent when it is available. The quick writing API
also receives the same bounded learning context.

## What “learning” means

The system does not silently retrain or modify model weights. It uses auditable,
deletable retrieval from three sources:

- explicit user preferences and corrections;
- helpful/improve ratings and successful/failed registered tool outcomes;
- approved account- or invitation-scoped knowledge sources (text, markdown, CSV,
  JSON, policies, and brand guidance).

The current request always outranks older memory. Retrieved content is treated as
untrusted data, embedded instructions are ignored, and it cannot expand user
permissions or bypass confirmations.

## Safety boundaries

- Only registered typed tools can be proposed.
- Read, edit, and manage permissions are checked against the invitation role.
- Manage actions require owner or manager access.
- High-risk, destructive, external, publishing, and messaging actions require
  explicit confirmation.
- Plans are bound to a document revision and fingerprint.
- Only confirmed plans can report completion and affect tool reliability.
- Provider credentials stay in server environment variables.
- Operational guest/RSVP context is included only for prompts that request it;
  phone numbers and email addresses are not sent in agent context.

## Connected provider setup

Set these on the server (never in browser JavaScript or invitation data):

```env
EINVITE_AI_PROVIDER=external
EINVITE_AI_ENDPOINT=https://your-provider-adapter.example/agent
EINVITE_AI_API_KEY=replace-on-server
EINVITE_AI_MODEL=your-model-id
```

The endpoint must accept the V53 JSON contract and return only
`assistantText`, `toolCalls`, optional `questions`, and optional `usage`.
Without credentials the deterministic offline helper remains available for
built-in checks and templates.

## User controls

Agent settings allow the user to disable AI, feedback learning, explicit memory,
or approved knowledge retrieval independently. Saved memories and sources can be
reviewed and deleted from the agent settings. Conversation retention is bounded
by the selected number of days; zero means keep until manually deleted.
