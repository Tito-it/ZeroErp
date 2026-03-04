# The Concentric Development Manifesto

### A practical proposal for software design.

*March 2, 2026*

---

## I.

Over the last decades, we have built software with many different approaches: waterfall, agile, modular, microservices, event-driven.

Each approach has delivered value in some contexts and clear limits in others. The issue is not picking a label; it is preserving structural coherence while the system grows.

Concentric Development starts from this point: treat software as layered growth, not as a set of loosely assembled parts.

---

## II.

The image of tree rings helps explain the model.

Each ring grows on top of the previous ones. Inner layers carry the highest load and must remain coherent over time. Outer layers add capabilities without breaking the meaning of the center.

In software terms, this means consolidating a shared core and growing the system through successive rings, with clear dependencies from inside to outside.

---

## III. Principles

**1) Design the core with rigor, and change it only when truly necessary.**
The center defines language, invariants, and shared rules. It should not be unstable, but it should not be untouchable either: evolve it when real limits emerge during growth.

**2) If an outer ring reveals an inner weakness, fix it at the source.**
Workarounds have hidden costs. When possible, improving the inner level is better than adding permanent shortcuts.

**3) Outer layers depend on inner layers, not the other way around.**
Outer rings may use the services of the center; the center should not depend on peripheral details.

**4) Minimize integration overhead, maximize shared vocabulary.**
Integrations do not disappear in every case, but they become simpler when a common protocol exists (names, events, states, rules).

**5) Incremental growth with verifiable coherence.**
Each ring must add concrete value and respect inner-layer contracts.

**6) The core is an operational protocol.**
It is not "the main module." It is where non-negotiable system rules are made explicit.

---

## IV. What Concentric Development Is Not

**It does not automatically replace other methods.**
It can coexist with agile, modular, or service-based practices, as long as they do not compromise core coherence.

**It does not promise zero integrations.**
In real systems, some integrations are unavoidable. The goal is to reduce their number, fragility, and long-term cost.

**It is not a one-size-fits-all theory.**
It is most useful where domain complexity is high, data is central, and long-term system evolution matters.

---

## V. How to Practice It

**Start from the center, concretely.**
Define early: invariants, primary lifecycle, audit/traceability rules, and error model.

**Grow one ring at a time.**
Each increment should close a real end-to-end path, not just "add code."

**When changing the center, do it with discipline.**
Version contracts, assess impact on upper rings, apply migrations, and run regression tests.

**Place critical rules where they cannot be bypassed.**
In a DB-first system, critical constraints belong in the database (constraints, triggers, functions), not only in application code.

**Test coherence, not only correctness.**
Do not ask only "does it work?" Also ask: "does it respect core contracts?" "does it duplicate rules?" "does it move logic to the wrong layer?"

---

## VI. Expected Benefits

When the model is applied well:

- change impact is more predictable;
- onboarding and maintenance improve because the center stays readable;
- local exceptions, redundant adapters, and duplicated logic decrease;
- the system remains evolvable even after years of stratification.

This is not a promise of absolute simplicity. It is a way to avoid unnecessary complexity.

---

## VII. Note on Technical Style

Structural quality is not in conflict with speed and delivery. It is what prevents high technical-debt interest.

Care in naming, data schema, API contracts, error handling, and traceability is not aesthetics; it is operational reliability.

In this view, the "beauty" of a system is clarity, coherence, and the absence of unnecessary elements.

---

## VIII.

Thirty years of enterprise software work teaches that complexity does not disappear, but it can be governed.

Concentric Development is a practical proposal to grow ERP systems without losing long-term integrity: one ring at a time, with a clear center and shared rules.

---

*The Concentric Development methodology was formalized on March 2, 2026, during the design of ZeroERP, an open-source ERP system for Italian companies. It comes from field practice and remains open to improvement through real-world use.*

*Michele Carlo - Author*

---

> *Zero unnecessary complexity. Concentric growth. Coherence across all rings.*
