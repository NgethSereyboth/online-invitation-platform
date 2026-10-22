# Glossary

Domain and architecture vocabulary for the eInvite backend. Kept current when
deepening refactors name new modules.

## Config adapter

**Config adapter** — the single interface (`core/config.py`: `get`, `override`,
`clear`) behind which every `EINVITE_*` setting is read. Two adapters sit
behind it: the **env adapter** (live `os.environ`, with the legacy `SOVAN_*`
fallback) in production, and the **dict adapter** (in-process `override`)
in tests. Precedence, identical through every path:

    override dict > EINVITE_X > legacy SOVAN_X > default

Import-time reads capture constants once (the request-handler module binds
`ROOT/DATA/DB` and friends); the dict adapter therefore must be installed
**before** importing `server` when the test means to change those constants.
