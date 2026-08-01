# ADR-006: HTTP 307 (Temporary Redirect) for short-link redirection

**Status:** Accepted

**Context:** FR-02 requires "a temporary redirect suitable for the prototype." Common choices are 301 (permanent), 302 (found/temporary, historically GET-only semantics), 307 (temporary, method-preserving), 308 (permanent, method-preserving).

**Decision:** Use 307.

**Alternatives considered:**
- 301/308 (permanent) — would encourage browsers/clients to cache the redirect target, which is actively wrong for this system: a link can be disabled or can expire, at which point it must stop redirecting. A cached permanent redirect could keep sending users to the original URL from their browser cache even after the link is disabled.
- 302 — commonly used for short links in practice, but its method-handling semantics are historically inconsistent across clients; 307 gives the same "temporary, don't cache long-term" behavior with unambiguous semantics.

**Consequences:** Slightly less common than 302 in the wild, but correct for a system where redirect targets are mutable (disable/expire), which is exactly this system's behavior (FR-05, FR-06).
