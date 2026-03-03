# Sviluppi Risorse Umane — WIP

> Documento di lavoro per sviluppi e aggiornamenti relativi al modulo risorse umane.
> Guida di riferimento: `docs/it/guide/risorse-umane-e-accessi.md`
> Dipende da: `docs/it/dev/work-in-progress/permessi-e-autorizzazioni.md` (completato)

---

## Prerequisiti gia' esistenti

- [x] `anagrafiche.risorse_umane` — tabella operativa con `attivo`, `valido_dal`, `valido_al`
- [x] `anagrafiche.risorse_umane_auth_user` — ponte 1:1 con `ruolo_sistema` (ADMIN/OPERATIVO/DISABILITATO)
- [x] `config.ruolo_sistema` — ENUM gia' in uso nella catena permessi
- [x] `config.fn_get_ruolo_sistema(p_auth_user_id)` — funzione SQL di lookup
- [x] `PermissionResolver` — enforcement backend che blocca DISABILITATO a livello API
- [x] `permissions_cache.py` — cache L1/L2 con `invalidate_user()`, `invalidate_department()`, `invalidate_all()`
- [x] `jwt_audit_middleware.py` — propaga `app.current_user_id` in sessione PG
- [x] Trigger `trg_risorse_umane_a10_risorse_umane_auth_user_block_deact_upd` — blocca disattivazione risorsa se ha figli in `risorse_umane_auth_user`

---

## 1. Sync `attivo` / `ruolo_sistema` → `auth_user.is_active`

### Contesto

Oggi `ruolo_sistema = DISABILITATO` blocca l'accesso a livello di risoluzione permessi (403 su ogni endpoint),
ma l'utente puo' ancora autenticarsi e ottenere un token JWT.
Per bloccare il login stesso serve sincronizzare `auth_user.is_active = false`.

Inoltre non esiste un meccanismo che verifichi le finestre temporali (`valido_dal`, `valido_al`)
e disattivi automaticamente utenti scaduti.

### DB

- [x] 1.1 — Funzione `anagrafiche.fn_sync_auth_user_is_active(p_risorsa_umana_id bigint)`
  - Logica: legge `risorse_umane.attivo`, `valido_dal`, `valido_al` e `risorse_umane_auth_user.attivo`
  - Se la risorsa non e' attiva OR fuori finestra temporale OR bridge non attivo → `auth_user.is_active = false`
  - Se tutto valido → `auth_user.is_active = true`
  - Ritorno: boolean (true se ha modificato `auth_user`)
  - **Prerequisiti**: nessuno

- [x] 1.2 — Trigger su `anagrafiche.risorse_umane` AFTER UPDATE OF `attivo`, `valido_dal`, `valido_al`
  - Nome: `trg_risorse_umane_z90_sync_auth_user_active_upd`
  - Chiama `fn_sync_auth_user_is_active(NEW.id)` solo se la risorsa ha un record in `risorse_umane_auth_user`
  - **Prerequisiti**: 1.1

- [x] 1.3 — Trigger su `anagrafiche.risorse_umane_auth_user` AFTER UPDATE OF `attivo`
  - Nome: `trg_risorse_umane_auth_user_z90_sync_auth_user_active_upd`
  - Chiama `fn_sync_auth_user_is_active(NEW.risorsa_umana_id)`
  - **Prerequisiti**: 1.1

- [x] 1.4 — Trigger su `anagrafiche.risorse_umane_auth_user` AFTER INSERT
  - Nome: `trg_risorse_umane_auth_user_z90_sync_auth_user_active_ins`
  - Chiama `fn_sync_auth_user_is_active(NEW.risorsa_umana_id)` per garantire coerenza immediata al primo collegamento
  - **Prerequisiti**: 1.1

- [x] 1.5 — Funzione `anagrafiche.fn_sync_auth_user_expired()`
  - Logica batch: trova tutte le risorse con `valido_al < CURRENT_DATE` ancora collegate a `auth_user.is_active = true` e le disattiva
  - Ritorno: integer (numero di utenti disattivati)
  - Pensata per job schedulato (pgAgent o management command)
  - **Prerequisiti**: nessuno (puo' convivere con 1.1, copre il caso "scadenza overnight")

- [x] 1.6 — Job pgAgent `sync_auth_user_expired_daily` per esecuzione giornaliera di `fn_sync_auth_user_expired()`
  - Frequenza: giornaliera, prima mattina (es. 06:00)
  - **Prerequisiti**: 1.5

### Backend

- [x] 1.7 — Management command `sync_auth_user_active`
  - Wrapper Django per `fn_sync_auth_user_expired()`
  - Utilizzabile da cron/systemd come alternativa a pgAgent
  - Log output: numero utenti disattivati
  - Supporto `--dry-run` per report senza modifiche
  - File: `apps/anagrafiche/management/commands/sync_auth_user_active.py`
  - Repository: `apps/anagrafiche/db/anagrafiche_repository.py` (query + chiamata fn SQL)
  - **Prerequisiti**: DB 1.5

- [x] 1.8 — Invalidazione cache permessi nei trigger path
  - **Scelta: Opzione B** — il management command (1.7) chiama `invalidate_user()` per ogni utente modificato
  - Flusso: raccoglie `auth_user_id` coinvolti *prima* della sync SQL, poi invalida la cache per ciascuno
  - Opzione A scartata: i trigger DB (1.2, 1.3, 1.4) modificano `auth_user` via SQL diretto — i signal Django `post_save` non scattano per modifiche dirette al DB
  - Per il path real-time (trigger), la cache TTL (300s) garantisce eventual consistency; il pattern LISTEN/NOTIFY (sez. 2) offre invalidazione event-driven
  - **Prerequisiti**: DB 1.1 o 1.5 + backend 1.7

### Test DB

- [x] 1.9 — Test pgTAP per `fn_sync_auth_user_is_active`
  - Caso: risorsa attiva + bridge attivo → `is_active = true`
  - Caso: risorsa disattivata → `is_active = false`
  - Caso: `valido_al` scaduto → `is_active = false`
  - Caso: risorsa senza bridge → nessun errore
  - **Prerequisiti**: DB 1.1

- [x] 1.10 — Test pgTAP per trigger sync (1.2, 1.3)
  - Caso: UPDATE `risorse_umane_auth_user.attivo = false` → verifica `auth_user.is_active = false`
  - Caso: UPDATE `risorse_umane_auth_user.attivo = true` → verifica `auth_user.is_active = true`
  - Caso: UPDATE `risorse_umane.valido_al` nel passato → verifica `auth_user.is_active = false`
  - Caso: UPDATE `risorse_umane.attivo = false` (disattivazione child-first) → verifica `auth_user.is_active = false`
  - Caso: Riattivazione parent-first + bridge → verifica `auth_user.is_active = true`
  - I test rispettano i vincoli ATTIVO framework (BLOCK/REQUIRE): disattivazione child-first, riattivazione parent-first
  - Il trigger INSERT (1.4) e' verificato implicitamente nel setup (test 4)
  - **Prerequisiti**: DB 1.2, 1.3, 1.4

- [x] 1.11 — Test pgTAP per `fn_sync_auth_user_expired`
  - Caso: risorsa con `valido_al` nel passato → disattivata
  - Caso: risorsa con `valido_al` nel futuro → non toccata
  - Caso: risorsa senza `valido_al` → non toccata
  - **Prerequisiti**: DB 1.5

### Test Backend

- [x] 1.12 — Test Django per management command `sync_auth_user_active`
  - Mock della funzione SQL, verifica output e invalidazione cache
  - 6 test: sync+count, invalidazione cache, dry-run (2), zero utenti, errore DB
  - File: `apps/anagrafiche/tests/services/test_sync_auth_user_active.py`
  - **Prerequisiti**: backend 1.7

---

## 2. Invalidazione cache automatica al cambio reparto

### Contesto

Quando `risorse_umane.unita_organizzativa_id` cambia, i permessi dell'utente cambiano immediatamente
(eredita il profilo del nuovo reparto). La funzione `permissions_cache.invalidate_department(uo_id)` esiste
ma non viene invocata automaticamente. Oggi l'invalidazione e' manuale.

### DB

- [x] 2.1 — Funzione `anagrafiche.fn_notify_cambio_reparto(p_risorsa_umana_id bigint, p_old_uo_id integer, p_new_uo_id integer)`
  - Emette `NOTIFY cambio_reparto` con payload JSON `{"risorsa_umana_id": ..., "old_uo_id": ..., "new_uo_id": ..., "auth_user_id": ...}`
  - Include lookup `auth_user_id` dal bridge (null se non collegata)
  - Ritorno: void
  - **Prerequisiti**: nessuno

- [x] 2.2 — Trigger su `anagrafiche.risorse_umane` AFTER UPDATE OF `unita_organizzativa_id`
  - Nome: `trg_risorse_umane_z90_notify_cambio_reparto_upd`
  - Trigger function: `trgfn_risorse_umane_notify_cambio_reparto()`
  - Chiama `fn_notify_cambio_reparto(NEW.id, OLD.unita_organizzativa_id, NEW.unita_organizzativa_id)` solo se il valore e' effettivamente cambiato (`IS DISTINCT FROM`)
  - **Prerequisiti**: 2.1

### Test DB

- [x] 2.6 — Test pgTAP per `fn_notify_cambio_reparto` e trigger
  - Caso: fn_notify con uo valide → esegue senza errore
  - Caso: fn_notify con uo NULL → esegue senza errore
  - Caso: fn_notify risorsa senza bridge → esegue senza errore (auth_user_id null nel payload)
  - Caso: trigger presente su risorse_umane
  - Caso: UPDATE unita_organizzativa_id → trigger esegue senza errore
  - Caso: UPDATE senza cambio uo → trigger non interviene (WHEN IS DISTINCT FROM)
  - Nota: NOTIFY consegnato solo al COMMIT; in pgTAP (rollback) non verificabile la ricezione
  - **Prerequisiti**: DB 2.1, 2.2

### Backend

- [x] 2.3 — Listener LISTEN/NOTIFY per canale `cambio_reparto`
  - Management command long-running `listen_cambio_reparto` che ascolta il canale `cambio_reparto`
  - Al ricevimento del payload: chiama `invalidate_user(auth_user_id)` per l'utente spostato
  - Connessione psycopg3 dedicata (autocommit), separata dal pool Django
  - Riconnessione automatica con backoff esponenziale (1s → 60s max) in caso di caduta connessione
  - Guard su payload: JSON non valido, non-dict, `auth_user_id` null — tutti gestiti senza crash
  - Shutdown pulito su SIGINT/SIGTERM
  - Opzione `--poll-interval` per configurare frequenza polling (default 5s)
  - Servizio: `apps/anagrafiche/services/notify_listener.py` (`CambioRepartoListener`)
  - Command: `apps/anagrafiche/management/commands/listen_cambio_reparto.py`
  - Vantaggio: punto unico di intercettazione — qualsiasi path che modifica `unita_organizzativa_id` (API, management command, operazione diretta DB, import bulk) ottiene invalidazione automatica senza dover ricordare di aggiungerla in ogni service method
  - Pattern riusabile: lo stesso meccanismo LISTEN/NOTIFY puo' servire per altri eventi futuri (cambio `ruolo_sistema`, disattivazione risorsa, ecc.)
  - **Prerequisiti**: DB 2.2

- [x] 2.4 — Invalidazione mirata per l'utente spostato
  - `invalidate_user(auth_user_id)` e' sufficiente: invalida la cache dell'utente spostato, che alla prossima richiesta ricalcolera' i permessi dal nuovo profilo reparto
  - Non serve invalidare gli altri utenti del vecchio/nuovo reparto (i loro permessi non cambiano)
  - Integrato nel metodo `_handle_notification` di `CambioRepartoListener`
  - **Prerequisiti**: 2.3

### Test Backend

- [x] 2.5 — Test Django per listener LISTEN/NOTIFY cambio reparto
  - Mock della connessione PG e del payload NOTIFY
  - Verifica che `invalidate_user()` viene invocato con il corretto `auth_user_id`
  - 8 test: invalidazione, skip null auth_user, JSON invalido, payload vuoto, payload non-dict, run+dispatch, riconnessione con backoff, stop
  - File: `apps/anagrafiche/tests/services/test_notify_listener.py`
  - **Prerequisiti**: backend 2.3

---

## 3. Aggiornamento documentazione

### Guida risorse umane (`docs/it/guide/risorse-umane-e-accessi.md`)

- [x] 3.1 — Correggere descrizione `soggetto_id`
  - Attuale: *"soggetto (azienda) a cui la risorsa appartiene"* — **errato**
  - Corretto: `soggetto_id` e' il soggetto-persona (denormalizzato da `soggetto_ruolo_id → soggetti_ruoli.soggetto_id`). Il legame con l'azienda (datore) passa da `anagrafiche.gestori`, non da questo campo
  - Esplicitare: `soggetto_ruolo_id` punta al ruolo RIS_UMANA della persona, `soggetto_id` e' la stessa persona (ridondante per comodita' di join)

- [x] 3.2 — Aggiungere diagramma ER mermaid
  - Entita': `soggetti`, `soggetti_ruoli`, `risorse_umane`, `risorse_umane_auth_user`, `gestori`, `qualifiche`, `unita_organizzative`, `auth_user`
  - Mostrare: la persona (PF) come soggetto, il gestore (PG) come azienda, la catena verso auth_user

- [x] 3.3 — Riscrivere sezione "Autorizzazioni e gruppi" — **obsoleta**
  - Rimuovere riferimenti a `auth_group`, `auth_permission`, mapping qualifica → gruppo
  - Sostituire con il sistema reale: `ruolo_sistema` + profili reparto (`unita_organizzativa_id`) + override utente
  - Linkare a `docs/it/guide/architettura-permessi-e-autorizzazioni.md`

- [x] 3.4 — Aggiornare sezione "Accesso al software"
  - Documentare la mitigazione attuale: `ruolo_sistema = DISABILITATO` blocca a livello API (403)
  - Specificare che la sync `auth_user.is_active` (sez. 1 di questo WIP) e' necessaria per bloccare il login JWT
  - Documentare i trigger di sync (una volta implementati)

- [x] 3.5 — Aggiungere sezione "Ciclo di vita"
  - Flusso: assunzione → cambio reparto → cambio qualifica → cessazione
  - Cambio reparto: impatto immediato sui permessi (ereditarieta'), cache da invalidare
  - Cambio qualifica: nessun impatto sui permessi nel modello attuale
  - Cessazione: disattivazione risorsa → sync auth_user.is_active → invalidazione cache
  - Rientro: riattivazione record esistente (unicita' garantita dalla catena UNIQUE `soggetti_ruoli` + `risorse_umane`)

- [x] 3.6 — Chiarire vincolo di unicita'
  - Spiegare che la catena `soggetti_ruoli(soggetto_id, tipo_ruolo_id)` UNIQUE + `risorse_umane(soggetto_ruolo_id)` UNIQUE garantisce un solo record per persona
  - Conseguenza: rientro = riattivazione, non nuovo record

- [x] 3.7 — Aggiungere paragrafo "Integrazione con il sistema operativo"
  - La risorsa umana e' l'identita' dell'operatore nel sistema
  - `auth_user_id` propagato via middleware (`app.current_user_id`) in sessione PG per audit e defense-in-depth
  - Link a guida permessi e guida fatturazione

- [x] 3.8 — Aggiornare `latest review` e data del documento
