# Piano solidita` progetto Django (ZeroErp)

Promemoria operativo per far crescere il progetto in modo solido, con priorita` e milestone pratiche.

## Obiettivo
Stabilizzare architettura, qualita` e operativita` del backend Django, mantenendo coerenza con il dominio DB e facilitando la crescita multi-area.

## Fase 1 (Settimana 1) — Fondazioni tecniche

### 1) Architettura e convenzioni
- Confermare standard unico: `api -> service -> repository`.
- Consolidare area `apps/core` per componenti condivisi.
- Bloccare naming esplicito metodi/classi (evitare nomi generici).

Deliverable:
- AGENTS aggiornato e rispettato.
- Verifica naming su `backend/apps/*`.

### 2) Contratto errori/API
- Usare ovunque pattern API core: `handle_post_json(...)`.
- Standardizzare envelope errori via middleware + `ErrorTranslator`.
- Applicare codici errore dominio con `ErrorManager` nei service.

Deliverable:
- Tutte le API nuove seguono il pattern core.
- Doc core aggiornata con regole e checklist.

### 3) Strategia test minima obbligatoria
- Unit test service (regole dominio).
- API contract test (status + payload errore/successo).
- Test middleware/error policy.

Deliverable:
- Suite green su `apps.core.tests` + `apps.vendite.tests`.
- Indice test in testa ai file test.

## Fase 2 (Settimana 2) — Qualita` e controllo crescita

### 4) Quality gate CI
- Pipeline con lint + test + type-check.
- Blocco merge se test/lint falliscono.

Deliverable:
- Workflow CI documentato e attivo.

### 5) Typing progressivo
- Tipizzare payload/DTO con `TypedDict`/dataclass.
- Ridurre `Any` nei moduli core/vendite.

Deliverable:
- Copertura typing su `apps/core` e `apps/vendite/services`.

### 6) Piano migrazione SQL -> Django governato
- Catalogare funzioni SQL: `DB-only`, `Hybrid`, `Migrated`.
- Definire criterio ufficiale:
  - Invarianti/coerenza/set-based in DB
  - Orchestrazione/policy in Django

Deliverable:
- Tabella stato migrazione in doc backend.

## Fase 3 (Settimana 3-4) — Operativita` e robustezza runtime

### 7) Osservabilita`
- Logging strutturato con campi minimi: `code`, `area`, `function_name`, `context`, `tx_id`.
- Endpoint diagnostici core mantenuti per verifica envelope.

Deliverable:
- Linee guida log condivise + esempi.

### 8) Sicurezza API
- Rate limiting su endpoint critici.
- Policy retry/idempotenza per operazioni write.

Deliverable:
- Strategia throttling documentata (nginx/app).

### 9) Workflow sviluppatore
- Script unificati run/test/docs.
- Template endpoint + template test riusabili.

Deliverable:
- Guida rapida “nuova API dominio” in 10 minuti.

## Backlog continuo (sempre attivo)
- Refactor incrementale del codice legacy non conforme al pattern.
- Aggiornamento automatico indici doc backend (`gen_bk_docs.py`).
- Verifica periodica coerenza tra documentazione, test e implementazione.

## KPI consigliati (mensili)
- Percentuale endpoint conformi al pattern core API.
- Numero errori non classificati (`E_GENERICO`) in calo.
- Coverage test su moduli core/dominio critico in aumento.
- Tempo medio onboarding dev su nuova API in diminuzione.

