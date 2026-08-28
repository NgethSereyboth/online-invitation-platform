# V31 Collaboration Authorization

Server authorization is scoped by workspace, invitation and action. Roles map to owner, manager, designer, content editor, reviewer and viewer. Existing invitation collaborators remain invitation-scoped even when they are not workspace members.

Authority, workspace ownership, permissions, publication state, sessions and secrets are forbidden collaboration paths. Reviewers may comment; content editors may mutate content; designers may mutate design/assets; managers may publish/manage members/backups; owners retain full authority. Hidden UI is never the security boundary.
