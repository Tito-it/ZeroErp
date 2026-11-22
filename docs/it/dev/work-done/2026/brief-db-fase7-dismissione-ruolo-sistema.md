# Brief DB — Fase 7 amm-software: dismissione `config.ruolo_sistema`

> Destinatari: team DB (`dev/db-tid`)
> Origine: refactor frontend amm-software Fase 7 LANDED 2026-04-29 lato Python+FE
> Stato Python+FE: rimosso il campo `ruolo_sistema` da TUTTI i contract pubblici (API, service, modelli, store, view). Resta come implementation detail privato di 2 repository (`amm_software_repository` + `risorse_umane_core_repository`), che lo derivano internamente da `is_super_admin`/`attivo` per chiamare le funzioni DB legacy.
> Prerequisito §4.6.H.2 (cutover RUA→view): **gia' chiuso** (`20260419-91-cutover-rua-view-mctit.yaml`).
> **Scansione cross-repo: completata 2026-04-29 — verdetto sotto.**

---

## ⚠️ Verdetto scansione cross-repo

**Drop di `script.fn_get_ruolo_sistema` NON sicuro adesso.**

La fn e' gia' un wrapper deprecato (versione `20260419-22`) che traduce a `fn_is_super_admin` + `fn_has_identita_attiva` + ha `RAISE WARNING` deprecation (`20260429-10`). Funzionalmente **morta**, ma **ancora invocata da 5 funzioni DB attive** + altre dipendenze documentate sotto.

Inoltre **4 funzioni DB** dichiarano variabili locali tipate via
`anagrafiche.risorse_umane_auth_user.ruolo_sistema%TYPE` — il drop della
colonna sulla vista farebbe fallire il deploy di queste fn al prossimo
`runOnChange`.

La sequenza completa per arrivare al drop e' in 9 migration (vedi
"Sequenza migration consigliata" sotto). Lato Python+FE non e' richiesto
nessun ulteriore refactor pre-drop: la Fase 7 ha gia' chiuso tutti i
caller pubblici.

---

## Inventario dipendenze residue (mappa scansione)

### A. Funzioni DB che chiamano `script.fn_get_ruolo_sistema` (via wrapper)

Ogni fn esegue il pattern `v_ruolo := fn_get_ruolo_sistema(...)` + `IF v_ruolo='ADMIN' THEN ...`. Va sostituito con chiamata diretta a `fn_is_super_admin` + `fn_has_identita_attiva`.

| Fn | Migration corrente (runOnChange) | Catena permessi |
| --- | --- | --- |
| `script.fn_resolve_livello_area` | `20260412-29-update-fn-resolve-livello-area-validita-mctit.yaml` | risolve livello area utente (TUTTO/LETTURA/BLOCCATO) |
| `script.fn_resolve_livello_oggetto` | `20260412-30-update-fn-resolve-livello-oggetto-validita-mctit.yaml` | livello oggetto/model |
| `script.fn_check_azione_processo` | `20260308-04-create-fn-check-azione-processo-mctit.yaml` | check azione di processo |
| `script.fn_check_user_emittente_scope` | `20260308-05-create-fn-check-user-emittente-scope-mctit.yaml` | scope emittente per utente |
| `script.fn_get_emittenti_scope_sr_ids` | `20260308-07-create-fn-get-emittenti-scope-sr-ids-mctit.yaml` | array soggetti_ruoli emittenti scope |

Refactor pattern unificato per ogni fn:

```sql
-- Prima
v_ruolo := script.fn_get_ruolo_sistema(p_auth_user_id);
IF v_ruolo IS NULL OR v_ruolo = 'DISABILITATO' THEN
    RETURN 'BLOCCATO'::config.livello_accesso;
END IF;
IF v_ruolo = 'ADMIN' THEN
    RETURN 'TUTTO'::config.livello_accesso;
END IF;

-- Dopo
IF NOT script.fn_has_identita_attiva(
        p_auth_user_id, 'OPERATORE'::config.ruolo_applicativo) THEN
    RETURN 'BLOCCATO'::config.livello_accesso;
END IF;
IF script.fn_is_super_admin(p_auth_user_id) THEN
    RETURN 'TUTTO'::config.livello_accesso;
END IF;
```

### B. Funzioni DB che leggono direttamente `risorse_umane_auth_user.ruolo_sistema`

Bypassano il wrapper, leggono la colonna sulla vista.

| Fn | Migration | Cosa legge |
| --- | --- | --- |
| `script.fn_get_setup_status` | `20260408-19-create-fn-get-setup-status-mctit.yaml` | `WHERE rau.ruolo_sistema = 'ADMIN'` (count admin) e `<> 'DISABILITATO'` (count operatori). Sostituire con `fn_is_super_admin` + `id.ruolo_applicativo`. |

### C. Funzioni DB che proiettano `ruolo_sistema` nel ritorno (JSONB / TABLE)

Output legacy che il Python **non legge piu'** post Fase 7 (verificato con grep su `backend/`). Possono droppare il field senza impatto applicativo.

| Fn | Migration | Field |
| --- | --- | --- |
| `script.fn_get_user_profile` | `20260421-05-update-fn-get-user-profile-ruolo-guc-aware-mctit.yaml` | chiave JSONB `'ruolo_sistema'` (ricostruita da `is_super_admin`). Python `me_view.py` ora `pop("ruolo_sistema", None)` esplicitamente. Drop sicuro. |
| `script.fn_get_operatore_detail` | `20260429-02-create-fn-get-operatore-detail-mctit.yaml` | colonna `ruolo_sistema TEXT` nella RETURNS TABLE + `script.fn_get_ruolo_sistema(au.id)::text AS ruolo_sistema` nella SELECT. Python `amm_software_repository.get_operatore_detail` fa `dict(zip(cols, row))` e nessun caller usa la chiave. Drop sicuro. |

### D. Funzioni DB con parametro `p_ruolo_sistema config.ruolo_sistema`

Vanno refactorate in firma multi-face. Python compat layer `_legacy_ruolo_from_contract` (privato, repo amm_software + risorse_umane_core) traduce internamente; sara' rimosso quando le fn v2 saranno disponibili.

| Fn | Migration | Firma attuale → proposta v2 |
| --- | --- | --- |
| `anagrafiche.fn_crea_operatore` | doc `dbzero/anagrafiche/funzioni/fn_crea_operatore.md` | `p_ruolo_sistema config.ruolo_sistema DEFAULT 'OPERATIVO'` → rimuovere; aggiungere `p_is_super_admin bool DEFAULT false` + `p_attivo bool DEFAULT true` |
| `anagrafiche.fn_crea_risorsa_umana` | (idem) | idem |

Mappa traduzione (gia' implementata nel wrapper): `attivo=false → DISABILITATO`; `is_super_admin=true AND attivo=true → ADMIN`; altrimenti `OPERATIVO` con binding SUPER_ADMIN INSERT condizionato.

### E. Variabili locali `%TYPE` su `risorse_umane_auth_user.ruolo_sistema`

Il drop della colonna fa fallire il deploy di queste fn (`runOnChange` rieseguito → errore tipo non risolvibile).

| Fn | Migration | Linea |
| --- | --- | --- |
| `script.fn_resolve_livello_area` | `20260412-29-...` | `v_ruolo anagrafiche.risorse_umane_auth_user.ruolo_sistema%TYPE` |
| `script.fn_resolve_livello_oggetto` | `20260412-30-...` | idem |
| `script.fn_get_emittenti_scope_sr_ids` | `20260308-07-...` | idem |
| `script.fn_get_user_profile` (versione vecchia) | `20260318-04-...` | `v_ruolo_sistema anagrafiche.risorse_umane_auth_user.ruolo_sistema%TYPE` (probabilmente gia' superata da `20260421-05` — verificare nel changelog autogen) |

Il refactor (step A) elimina queste dichiarazioni (sostituite con bool/text liberi).

### F. Test pgTAP che leggono/scrivono `ruolo_sistema`

Vanno aggiornati. Scrittura `UPDATE risorse_umane_auth_user SET ruolo_sistema = '...'` non funziona post-drop colonna (la vista e' readonly o richiede INSTEAD OF su `ruolo_sistema` che non esiste piu'). Soluzione: scrivere su `identita_digitali` (per `attivo`/`ruolo_applicativo`) e `profili_accesso_bindings` (per il binding SUPER_ADMIN).

| File pgTAP | Operazioni che usano `ruolo_sistema` |
| --- | --- |
| `db/pgtap/script/test-permessi-funzioni-risoluzione.sql` | molti `UPDATE risorse_umane_auth_user SET ruolo_sistema = ...`, test diretti `fn_get_ruolo_sistema` |
| `db/pgtap/script/test-permessi-fn-check-emittente-scope.sql` | UPDATE + SELECT |
| `db/pgtap/script/test-fn-get-soggetto-dati-and-user-profile.sql` | SELECT `rau.ruolo_sistema` + assertion JSONB key |
| `db/pgtap/script/test-fn-check-operatore-invitabile.sql` | UPDATE + assertion |
| `db/pgtap/script/test-fn-check-user-can-create-ba.sql` | UPDATE/SELECT |
| `db/pgtap/script/test-fn-resolve-emittente-for-user.sql` | UPDATE/SELECT |
| `db/pgtap/script/test-permessi-trigger-guard-emittente.sql` | UPDATE/SELECT |
| `db/pgtap/anagrafiche/test-fn-crea-risorsa-umana.sql` | call `fn_crea_risorsa_umana(p_ruolo_sistema=>...)` |
| `db/pgtap/anagrafiche/test-fn-crea-operatore.sql` | call `fn_crea_operatore(p_ruolo_sistema=>...)` |
| `db/pgtap/anagrafiche/test-risorse-umane-auth-user-view.sql` | SELECT colonna |
| `db/pgtap/anagrafiche/test-billing-account-auto-link-ef.sql` | (probabilmente UPDATE) |
| `db/pgtap/config/test-user-emittenti-fiscali-immutable.sql` | (verificare) |
| `db/pgtap/config/test-permessi-strutture-base.sql` | (verificare) |

### G. Backfill / data already-applied (storico, non da toccare)

- `db/changelog/migrations_v2/80_data/changelog/20260419-80-backfill-identita-digitali-operatori-mctit.yaml`: una-tantum, gia' eseguito al cutover §4.6.H.2. Resta nel changelog.

### H. Vista `risorse_umane_auth_user`

Post-cutover §4.6.H.2 e' una vista su `identita_digitali` con colonna `ruolo_sistema` ricostruita. Drop sicuro **solo dopo** che A+B+E+F sono completati (nessun lettore residuo, nessun `%TYPE` dipendente, pgTAP riallineato).

### I. Enum `config.ruolo_sistema`

Drop possibile **solo dopo** che D + H sono completati (nessuna colonna/parametro tipato, nessun cast `::config.ruolo_sistema` residuo). `DROP TYPE config.ruolo_sistema` finale.

---

## Sequenza migration consigliata (9 step)

| Step | Migration | Cosa fa | Bloccato da | Stato |
| --- | --- | --- | --- | --- |
| 1 | refactor `fn_resolve_livello_area` + `fn_resolve_livello_oggetto` + `fn_check_azione_processo` + `fn_check_user_emittente_scope` + `fn_get_emittenti_scope_sr_ids` | rimpiazzano `fn_get_ruolo_sistema` con `fn_is_super_admin` + `fn_has_identita_attiva` (5 nuovi changeSet `runOnChange`) | — | DB pending |
| 2 | refactor `fn_get_setup_status` | sostituisce `WHERE rau.ruolo_sistema = '...'` con `fn_is_super_admin` + `id.ruolo_applicativo`/`id.attivo` | — | DB pending |
| 3 | update `fn_get_user_profile` + `fn_get_operatore_detail` | rimuovono il field `ruolo_sistema` dall'output (JSONB key + colonna RETURNS TABLE) | step 1 (no piu' caller del wrapper) | DB pending |
| 4 | update test pgTAP (~13 file in `db/pgtap/script/` + `db/pgtap/anagrafiche/` + `db/pgtap/config/`) | rimuovono SELECT/UPDATE su `rau.ruolo_sistema`; sostituiscono con scritture su `identita_digitali` + `profili_accesso_bindings` | step 3 (le fixture chiamavano fn ora cambiate) | DB pending |
| **5** | new `fn_crea_operatore` v2 + `fn_crea_risorsa_umana` v2 | nuova firma `p_is_super_admin bool, p_attivo bool` (in coabitazione con v1) | — | **DB ✓ (dev/db-tid, non mergiato)** |
| **6** | **PR Python (LANDED 2026-04-29)** | sostituisce call alla v1 con call alla v2; rimuove `_legacy_ruolo_from_contract` da entrambi i repo | step 5 | **Python ✓ (dev/backend-tid, non mergiato)** |
| **7** | drop `fn_crea_operatore` v1 + `fn_crea_risorsa_umana` v1 | rimozione fn legacy | step 6 | **DB ✓ (dev/db-tid, non mergiato)** |
| 8 | drop `script.fn_get_ruolo_sistema` + rimozione colonna `ruolo_sistema` da vista `risorse_umane_auth_user` (CREATE OR REPLACE VIEW senza la colonna) | tutto questo insieme: nessun caller, nessun `%TYPE` residuo | step 1, 2, 3, 4 | DB pending |
| 9 | `DROP TYPE config.ruolo_sistema` | enum non piu' referenziato | step 7, 8 | DB pending |

### ⚠️ Coordinazione di merge — invariante atomica

Step 5 + 7 (DB) e step 6 (Python) **devono essere mergiati insieme** (stesso PR consolidato o merge sequenziale rapido nello stesso sprint).

Combinazioni che rompono il sistema in produzione:

- DB merge prima di Python → Python chiama `fn_crea_operatore(... p_ruolo_sistema=...)` ma la v1 e' droppata: errore `function does not exist` su create/update operatore.
- Python merge prima di DB → Python chiama `fn_crea_operatore(... p_is_super_admin=...)` ma la v2 non esiste: stesso errore in direzione opposta.

Il merge atomico evita la finestra di rottura. Lo stato attuale (entrambi i branch chiusi ma non mergiati) e' il prerequisito per applicare insieme i 2 PR.

Ad ogni step:

- Suite **pgTAP** verde
- Suite **Django** verde (`./manage-test.sh -v 0`)
- Vite build verde

### Versione comprimibile (3 macro-migration)

Se si preferisce raggruppare per ridurre il numero di PR, si possono unire:

- **PR1**: step 1 + 2 + 3 (refactor fn permessi + setup_status + user_profile/operatore_detail). Rilasciabile da sola perche' invariate semanticamente.
- **PR2**: step 4 (refactor pgTAP). Va dopo PR1 che ha cambiato il behavior interno delle fn (le fixture pgTAP che si aspettavano `'ADMIN'` come stringa devono usare il nuovo modello).
- **PR3**: step 5 + 6 + 7 (fn_crea_operatore v2 + PR Python + drop v1).
- **PR4**: step 8 + 9 (drop wrapper + colonna vista + enum). Atomica e finale.

### Lato Python rimane solo

Quando le 4 PR DB sono live:

1. PR Python di pulizia: rimuovere `_legacy_ruolo_from_contract` dai 2 repo + chiamata diretta alle fn v2. ~30 righe di diff.
2. Aggiornare `analisi-refactor.frontend-amm-software.md` Fase 7-DB → LANDED.

---

## Memorie progetto correlate

- `feedback_db_actions_passaggio_team` — il backend agent non esegue migration; questo brief e' la consegna formale.
- `project_no_produzione_solo_sviluppo` — breaking change ammessi, niente deprecation window.
- `feedback_no_hardcoded_ids` — nessuna ID legacy da preservare nel refactor enum.

## Nota di prioritizzazione

Fase 7 e' **P2**: il sistema funziona correttamente anche senza queste migration (compat layer Python attivo + deprecation warning DB attivo). La motivazione del brief e' **estetica/architetturale** (single source of truth multi-face, niente codice morto in DB, niente RAISE WARNING su ogni call). Schedulare quando il team DB ha capacita' libera.
