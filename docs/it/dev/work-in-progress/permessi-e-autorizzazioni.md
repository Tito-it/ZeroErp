# Permessi e Autorizzazioni — WIP

> Documento di lavoro per pianificazione e avanzamento.
> La guida architetturale di riferimento è `docs/it/guide/architettura-permessi-e-autorizzazioni.md`.

---

## Prerequisiti già esistenti

- [x] `django.auth_user` — schema Django con autenticazione JWT
- [x] `config.unita_organizzative` — reparti con gerarchia `parent_id`
- [x] `config.qualifiche` — qualifiche professionali
- [x] `anagrafiche.risorse_umane` — con FK a `unita_organizzativa_id`
- [x] `anagrafiche.risorse_umane_auth_user` — ponte 1:1 user↔risorsa umana
- [x] `anagrafiche.emittenti_fiscali` — emittenti con utilities e billing account
- [x] `jwt_audit_middleware.py` — propaga `app.jwt_user` in sessione PG

---

## 1. Strutture base e classificazione utente

### DB

- [x] 1.1 — ENUM `config.ruolo_sistema` (`ADMIN`, `OPERATIVO`, `DISABILITATO`)
- [x] 1.2 — ALTER `anagrafiche.risorse_umane_auth_user` ADD `ruolo_sistema` (default `OPERATIVO`)
- [x] 1.3 — ENUM `config.livello_accesso` (`TUTTO`, `LETTURA`, `BLOCCATO`)
- [x] 1.4 — Tabella `config.aree_funzionali` + seed 10 aree
- [x] 1.5 — Tabella `config.azioni_processo` + seed iniziale
- [x] 1.6 — Tabella `config.area_model_overrides`

### Backend

- [ ] 1.7 — Model ORM `AreaFunzionale` (`managed=False`) — atteso DB 1.4
- [ ] 1.8 — Model ORM `AzioneProcesso` (`managed=False`) — atteso DB 1.5
- [ ] 1.9 — Model ORM `AreaModelOverride` (`managed=False`) — atteso DB 1.6
- [ ] 1.10 — Model ORM `RisorseUmaneAuthUser` aggiornato con campo `ruolo_sistema` — atteso DB 1.2

---

## 2. Profili reparto (ereditarietà)

### DB

- [x] 2.1 — Tabella `config.profili_reparto_aree` — atteso DB 1.3, 1.4
- [x] 2.2 — Tabella `config.profili_reparto_azioni` — atteso DB 1.5

### Backend

- [ ] 2.3 — Model ORM `ProfiloRepartoArea` (`managed=False`) — atteso DB 2.1
- [ ] 2.4 — Model ORM `ProfiloRepartoAzione` (`managed=False`) — atteso DB 2.2

---

## 3. Override utente

### DB

- [x] 3.1 — Tabella `config.user_override_aree` — atteso DB 1.3, 1.4
- [x] 3.2 — Tabella `config.user_override_oggetti` — atteso DB 1.3
- [x] 3.3 — Tabella `config.user_override_azioni` — atteso DB 1.5
- [x] 3.4 — Tabella `config.user_emittenti_fiscali` — atteso DB prerequisito emittenti_fiscali

### Backend

- [ ] 3.5 — Model ORM `UserOverrideArea` (`managed=False`) — atteso DB 3.1
- [ ] 3.6 — Model ORM `UserOverrideOggetto` (`managed=False`) — atteso DB 3.2
- [ ] 3.7 — Model ORM `UserOverrideAzione` (`managed=False`) — atteso DB 3.3
- [ ] 3.8 — Model ORM `UserEmittenteFiscale` (`managed=False`) — atteso DB 3.4

---

## 4. Enforcement backend

### Backend

- [ ] 4.1 — `PermissionResolver` in `apps/core/permissions_resolver.py` — atteso backend 1.7, 1.10, 2.3, 3.5, 3.6, 3.7
- [ ] 4.2 — `ZeroERPPermission` (DRF permission class) in `apps/core/permissions.py` — atteso backend 4.1
- [ ] 4.3 — `EmittenteFiscaleScopeMixin` in `apps/core/mixins.py` — atteso backend 3.8
- [ ] 4.4 — Unificare middleware PG session: `app.current_user_id` nel `jwt_audit_middleware.py` esistente — atteso DB 1.1

---

## 5. Defense-in-depth DB

### DB

- [ ] 5.1 — Funzione `config.fn_check_user_emittente_scope()` — atteso DB 3.4
- [ ] 5.2 — Trigger guard su `vendite.fatture` (scope emittente) — atteso DB 5.1
- [ ] 5.3 — Trigger guard su altre tabelle operative (ordini, pagamenti) — atteso DB 5.1

### Backend

- [ ] 5.4 — Test Django enforcement permessi (unit test `PermissionResolver`) — atteso backend 4.1
- [ ] 5.5 — Test Django scope emittente (unit test mixin) — atteso backend 4.3

### Test DB

- [ ] 5.6 — Test pgTAP per `fn_check_user_emittente_scope` — atteso DB 5.1
- [ ] 5.7 — Test pgTAP per trigger guard fatture — atteso DB 5.2

---

## 6. Diagnostica e integrazione

### Backend

- [ ] 6.1 — Endpoint diagnostico `/api/users/{id}/permessi-effettivi/` — atteso backend 4.1
- [ ] 6.2 — Messaggio chiaro quando reparto senza profilo configurato — atteso backend 4.1
- [ ] 6.3 — Applicare `ZeroERPPermission` come default nelle view DRF — atteso backend 4.2
- [ ] 6.4 — Applicare `EmittenteFiscaleScopeMixin` alle view operative — atteso backend 4.3

---

## 7. Caching e performance

### Backend

- [ ] 7.1 — Strategia cache per `PermissionResolver` (session-level o Redis) — atteso backend 4.1
- [ ] 7.2 — Invalidazione cache su modifica profili/override — atteso backend 7.1

---

## 8. Gestione scadenze e audit

### DB

- [ ] 8.1 — Job/funzione per segnalare override con `valido_al` scaduto — atteso DB 3.1, 3.3

### Backend

- [ ] 8.2 — Log storico modifiche profili e override (audit trail permessi) — atteso DB sezione 2, 3

---

## Fasi di rilascio

> Promemoria operativo: in quale ordine le sezioni sopra diventano utilizzabili
> e cosa integrare sulle API/funzioni già esistenti.

### Fase 1 — DB: strutture base

Completare sezioni **1**, **2**, **3** (tutti i punti DB).
Al termine il database ha tutte le tabelle, gli ENUM e i seed necessari.

### Fase 2 — Django: model + enforcement → API vendite protette subito

Completare sezioni **1**, **2**, **3** (punti backend: model `managed=False`)
poi sezione **4** (`PermissionResolver`, `ZeroERPPermission`, middleware).

**Integrazione API esistenti (vendite):**

- [ ] F2.1 — Aggiungere `ZeroERPPermission` ai ViewSet pipeline fatturazione (`apps/vendite/api/`)
- [ ] F2.2 — Aggiungere `EmittenteFiscaleScopeMixin` alle view fatture/lotti con `emittente_field`
- [ ] F2.3 — Verificare che le API lotto (`run_lotto_pipeline`, `reset_lotto`) passino dal check azione
- [ ] F2.4 — Aggiungere `ZeroERPPermission` alle eventuali view di anagrafiche, catalogo, pagamenti già esposte

A questo punto tutte le API esistenti sono protette dal sistema permessi.

### Fase 3 — Azioni di processo: `Meta.permissions` e popolamento

- [ ] F3.1 — Definire `Meta.permissions` custom sui model vendite (es. `genera_fatture_lotti`, `approva_fattura`, `emetti_fattura`)
- [ ] F3.2 — Definire `Meta.permissions` custom sui model pagamenti (es. `approva_rimessa`)
- [ ] F3.3 — Popolare `config.azioni_processo` con i codename definiti (seed o migration data)
- [ ] F3.4 — Collegare le azioni alle view con attributo `<action>_permission` sui ViewSet (es. `run_pipeline_permission = 'genera_fatture_lotti'`)
- [ ] F3.5 — Verificare che `ZeroERPPermission.has_permission` instradi correttamente le azioni custom vs CRUD standard

### Fase 4 — Defense-in-depth, test, diagnostica

Completare sezioni **5**, **6**, **7**, **8**.

---

## Note

- Il documento architetturale (sez. 13) definisce il campo `ruolo_sistema` e la catena di risoluzione aggiornata.
- L'ordine delle sezioni rispecchia le dipendenze: ogni punto backend indica i prerequisiti DB.
- I punti sono sequenziali per sezione: all'interno di una sezione, i numeri DB vengono prima dei backend.
- Le **Fasi di rilascio** indicano quando le API già esistenti (vendite, pipeline) vengono integrate nel sistema permessi.
