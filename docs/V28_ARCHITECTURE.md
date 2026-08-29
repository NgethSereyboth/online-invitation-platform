# V28.0 AI Creative Agent Architecture

## Scope

V28.0 adds a project-scoped, multi-turn creative agent without giving a model direct DOM, JavaScript, SQL, filesystem, or arbitrary network authority. Schema version 14 remains unchanged. The agent is layered over the V27.3.5 transaction, target-binding, preview, permissions, optimistic-revision, and lazy-loading foundations.

## Runtime boundaries

1. **Lazy client shell** — `ai-assistant-loader-v27.js` loads `ai-creative-agent-v28.css`, `ai-agent-tool-registry-v28.js`, and `ai-creative-agent-v28.js` only when the user opens the agent.
2. **Conversation UI** — persistent project threads when authenticated; bounded session-only threads when offline. Message types include user, assistant, question, plan, progress, preview, result, error, and cancellation.
3. **Typed client registry** — maps validated tool IDs to `EInviteAgentActionService` actions or declared UI boundaries. All document mutations are previewed and committed through the authoritative document model.
4. **Server orchestration** — `ai_agent/` owns provider adapters, conversation persistence, bounded context, tool schemas, plan validation, rate/concurrency policy, cancellation, retention, and audit-safe events while `server.py` remains the deployment entry point.
5. **Provider boundary** — provider keys stay server-side. Provider responses must be a bounded JSON object containing assistant text, questions, and registered tool calls. Unknown shapes or tool arguments are rejected.

## Core data flow

User message → authorized bounded context → provider-neutral response → strict tool validation → stored proposed plan → side-effect-free client preview → exact-target/revision confirmation → atomic document transaction or declared confirmed side effect → audit-safe completion → one-click Undo AI job.

## Security model

- Invitation text, comments, filenames, asset names, and provider output are untrusted data.
- Context references are resolved to stable invitation/page/object/asset IDs and revalidated against ownership or collaboration permissions.
- Tool input rejects selector, HTML, SQL, script, shell, executable code, filesystem path, arbitrary endpoint, and network-destination fields or values.
- Publish/unpublish, prepared messaging, destructive deletion, export preparation, and local background removal require explicit confirmation.
- Cookies, CSRF tokens, API keys, internal paths, and unrelated account data are excluded from provider context and persisted conversation content.
- Jobs use bounded sizes, timeouts, concurrency limits, cancellation flags, and idempotency keys.

## Persistence

New server tables are additive and separate from invitation schema 14: `ai_preferences`, `ai_conversations`, `ai_messages`, `ai_plans`, `ai_jobs`, and `ai_usage_events`. Retention is user-configurable and project conversations can be archived. Offline conversations use session storage only.

## Accessibility and responsive behavior

Desktop uses an accessible complementary side panel. Mobile uses a modal bottom sheet with focus containment, Escape close, inert background lifecycle, exact opener restoration, safe-area padding, 44-pixel targets, coherent light/dark/system tokens, and reduced-motion behavior.

## Loading and performance

The large agent UI, tool registry, and CSS are not part of the canonical editor route source list. The existing small loader and V27 transaction service remain the only initial-route AI assets.
