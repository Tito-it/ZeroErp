# Risposta DB al brief preventivi rev2 — implementazione completata

> **Status**: ✅ **COMPLETATO + LANDED** — merge su `dev/backend-tid` 2026-05-02.
> Lavoro BE/FE consumer completato nella stessa data (vedi commit `1f7daf69` + refactor §9 PK vs SR successivo).
>
> ---
>
> **Status originale**: ✅ DB-side completo, in attesa apply su `dev/db-tid`
>
> **Origine**: brief backend rev2 (sessione 2026-05-01)
> **Esecutore**: DB agent su `dev/db-tid`
> **Data**: 2026-05-01

---

## TL;DR per il backend

Tutto il lavoro lato DB è stato implementato come da brief rev2 con **5 deviazioni puntuali** (tutte motivate in §3 sotto). Le strutture API per il BE sono:

- **Colonna nuova**: `vendite.preventivi.emittente_fiscale_id bigint NOT NULL` (FK `anagrafiche.emittenti_fiscali(id)`, indicizzata)
- **Trigger di default**: imposta `emittente_fiscale_id` a INSERT-time da GUC `app.current_user_id`. Skip se valorizzato esplicitamente nel payload (admin globale path).
- **Vista**: `vw_preventivi_list.emittente_fiscale_id` ora è lettura colonna persistita (zero overhead, no più crash su BA NULL).
- **Guard coerenza**: blocca preventivi con coppia `(istanza_utility_id, utility_id)` non dichiarata in nessun satellite.
- **Strategia C**: ogni nuova `istanze_utilities` deve avere ≥1 satellite (BA, IDP, **clienti**) entro la transazione.
- **4 codici errore** registrati in `messaggi_errore.csv`.

L'apply Liquibase rispetta l'ordine fasi 00_schema → 20_code → 80_data → 90_end (single deploy, ordering pulito senza finestre vulnerabili).

---

## 1. File creati

### 00_schema (1 file)

| File | Scopo |
|---|---|
| `00_schema/vendite/20260501-09-add-emittente-fiscale-id-preventivi-mctit.yaml` | ADD COLUMN nullable + FK + indice |

### 20_code (5 file)

| File | Oggetto creato |
|---|---|
| `20_code/anagrafiche/20260501-10-create-trgfn-istanze-utilities-require-utility-dichiarata-mctit.yaml` | Constraint trigger DEFERRABLE su `istanze_utilities` |
| `20_code/script/20260501-11-create-fn-check-utility-istanza-coerenza-mctit.yaml` | `script.fn_check_utility_istanza_coerenza(istanza_id, utility_id) RETURNS boolean` |
| `20_code/vendite/20260501-12-create-trgfn-preventivi-default-emittente-mctit.yaml` | Trigger BEFORE INSERT default emittente |
| `20_code/vendite/20260501-13-create-trgfn-preventivi-guard-utility-istanza-coerenza-mctit.yaml` | Trigger BEFORE INSERT/UPDATE OF (istanza, utility) guard coerenza |
| `20_code/vendite/20260501-14-update-vw-preventivi-list-emittente-persisted-mctit.yaml` | Vista aggiornata: lettura colonna persistita |

### 80_data (3 file + 2 CSV append)

| File | Scopo |
|---|---|
| `80_data/changelog/20260501-15-cleanup-preventivi-malformati-mctit.yaml` | DELETE preventivi con BA NULL + istanza NULL |
| `80_data/changelog/20260501-16-backfill-istanze-dati-precontrattuali-mctit.yaml` | Backfill IDP da BA + report orfane residue |
| `80_data/changelog/20260501-17-backfill-preventivi-emittente-mctit.yaml` | Backfill catena: user_insert → BA → gestore globale |

CSV append:

- `80_data/sql/config/messaggi_errore.csv` → 4 nuovi codici (id 418-421)
- `80_data/sql/dbops/automation_lock_columns.csv` → riga `(vendite, preventivi, emittente_fiscale_id, EMITTENTE_NON_MODIFICABILE)`

### 90_end (1 file)

| File | Scopo |
|---|---|
| `90_end/20260501-18-alter-preventivi-not-null-mctit.yaml` | SET NOT NULL su `istanza_utility_id` e `emittente_fiscale_id` (post-backfill, con preCondition zero NULL) |

### pgTAP tests (3 file)

- `db/pgtap/script/test-fn-check-utility-istanza-coerenza.sql` (6 test)
- `db/pgtap/anagrafiche/test-trgfn-istanze-utilities-require-utility-dichiarata.sql` (3 test, usa `SET CONSTRAINTS ... IMMEDIATE` per validare DEFERRED)
- `db/pgtap/vendite/test-trgfn-preventivi-default-emittente-e-guard-coerenza.sql` (6 test, copre GUC vuota / valida / explicit / admin globale + guard coerenza ok/ko)

### Doc aggiornata

- `docs/it/dbzero/vendite/manual/preventivi.md` — promosso istanza a obbligatoria, aggiunto emittente_fiscale_id, regola coerenza utility/istanza
- `docs/it/guide/gestione-delle-istanze-utility.md` — aggiunta sezione "Strategia C"

### Autogen

`db/changelog/migrations_v2/changelog-autogen.yaml` rigenerato con `python3 scripts/gen_master_autogen.py --root db/changelog/migrations_v2 --out db/changelog/migrations_v2/changelog-autogen.yaml --base db/changelog`. Tutti i 6 file 00_schema/20_code inclusi correttamente. I file 80_data/90_end sono inclusi via `includeAll` nel master.

---

## 2. Contract API per il backend

### 2.1 INSERT preventivo standard (operatore con EF assegnato)

```python
# Il middleware JwtAuditAuthentication popola GUC app.current_user_id automaticamente.
# Il BE non deve toccare emittente_fiscale_id: il trigger lo valorizza.

cursor.execute("""
    INSERT INTO vendite.preventivi (
        numero, data, stato_doc_preventivo_id,
        billing_account_id,        -- opzionale (prospect ammesso)
        istanza_utility_id,        -- OBBLIGATORIO
        utility_id                 -- OBBLIGATORIO, deve essere coerente con istanza
    ) VALUES (...);
""")
# Trigger: emittente_fiscale_id = fn_resolve_emittente_for_user(GUC current_user_id)
```

### 2.2 INSERT preventivo da admin globale (no EF assegnato)

```python
# Admin globale = utente senza riga in config.user_emittenti_fiscali.
# Il payload DEVE specificare emittente_fiscale_id, altrimenti il trigger
# solleva E_PREV_EMITTENTE_NON_RISOLTO.

cursor.execute("""
    INSERT INTO vendite.preventivi (
        numero, data, stato_doc_preventivo_id,
        billing_account_id, istanza_utility_id, utility_id,
        emittente_fiscale_id   -- ESPLICITO, scelto dall'admin
    ) VALUES (...);
""")
# Trigger: skip auto-fill (NEW.emittente_fiscale_id IS NOT NULL)
```

### 2.3 UPDATE preventivo

`emittente_fiscale_id` è **immutabile** post-create (`automation_lock_columns`). Tentativo di UPDATE solleva `EMITTENTE_NON_MODIFICABILE`. Per cambiare l'emittente, usare `vendite.fn_crea_revisione_preventivo` (la nuova revisione nasce con l'emittente dell'operatore corrente).

### 2.4 Codici errore da gestire in `error_policies.py`

| Codice | HTTP suggerito | Origine | UI action |
|---|---|---|---|
| `E_PREV_EMITTENTE_NON_RISOLTO` | 400 | trigger BEFORE INSERT | toast: "Operatore senza emittente fiscale assegnato; specificare nel payload" |
| `E_PREV_UTILITY_ISTANZA_INCOERENTE` | 409 | trigger guard coerenza | highlight campi utility + istanza, suggerire "Selezionare utility coerente con l'istanza" |
| `E_ISTANZA_UTILITY_SENZA_UTILITY` | 409 | constraint trigger DEFERRED su istanze | toast: "Creazione istanza fallita: serve almeno un riferimento (BA/IDP/cliente)" |
| `EMITTENTE_NON_MODIFICABILE` | 409 | lock_columns generic | toast: "L'emittente del preventivo non può essere modificato. Crea una revisione." |

### 2.5 View `vw_preventivi_list` rimane retrocompatibile

Stessa shape, stesso nome colonna `emittente_fiscale_id`. Il BE non deve cambiare nulla nel filtro scope `script.fn_get_emittenti_scope_sr_ids` — rimane il mismatch nome `_sr_ids` vs PK reale segnalato a §9 del brief, **non risolto qui** (vedi §4 sotto).

---

## 3. Deviazioni dal brief rev2 (con motivazione)

### 3.1 Naming trigger: `_a05_` → `_a10_default_emittente_ins`

**Brief diceva**: usare fase `_a05_` per il trigger pre-guard.
**Implementato**: usato `_a10_default_emittente_ins`. Naming alfabetico garantisce firing order corretto (`default` < `guard` quindi default fires first).

**Motivo**: la convention progetto (CLAUDE.md / linee-guida-trigger.md) ha solo `_a10_` (guard) e `_z90_` (final). Inventare `_a05_` richiedeva aggiornamento doc convention. Più pulito sfruttare l'ordine alfabetico dei nomi all'interno della stessa fase `_a10_`.

### 3.2 Backfill emittente: catena user_insert → BA → globale (era solo BA + globale)

**Brief diceva**: backfill da BA, fallback gestore globale.
**Implementato**: 3 step in cascade:

1. Da `user_insert` (username Django) → JOIN `django.auth_user` (schema fully qualified) → `script.fn_resolve_emittente_for_user(au.id)`
2. Da BA via `fn_get_emittente_fiscale_pk` (per residui)
3. Gestore globale `is_default=true` (fallback finale)

**Motivo**: il modello rev2 dice "emittente = quello dell'operatore creatore". Per coerenza concettuale, anche i preventivi storici devono provarci a derivare dall'operatore (informazione che abbiamo via `user_insert`). Il fallback BA-derived rimane per casi edge (operatore disattivato/cancellato). Differenza solo se in futuro qualcuno usa `emittente_fiscale_id` come proxy di "operatore emettitore" su dati storici.

### 3.3 Liste satellite allineate (BA + IDP + **clienti**)

**Brief diceva**: in `fn_check_utility_istanza_coerenza` solo BA + IDP. Trigger require_utility includeva BA + IDP + clienti.
**Implementato**: tutte e 3 le liste includono **clienti** come fonte satellite.

**Motivo**: la mia analisi critica del brief aveva già flaggato questo: incoerenza tra trigger e fn portava al caso "istanza con solo cliente passa al trigger ma fn_check ritorna false → guard preventivi blocca creazione su cliente legittimo". Allineate.

### 3.4 Lock columns via CSV `automation_lock_columns` (era trigger custom)

**Brief diceva**: trigger separato `trg_preventivi_a10_lock_emittente_upd` o estensione del trigger esistente.
**Implementato**: aggiunta riga al CSV `dbops/automation_lock_columns.csv`. Il pgAgent / loader esistente crea/aggiorna automaticamente il trigger generico.

**Motivo**: pattern già consolidato per `numero`, `codice` di articoli, ecc. Zero codice custom, zero trigger duplicato, manutenibile dichiarativamente.

### 3.5 Raise: ultimo arg = solo parametri (no descrizioni duplicate)

**Brief diceva**: messaggi descrittivi nei `concat()` finali del raise.
**Implementato**: ultimi argomenti delle chiamate `script.fn_log_and_raise_error` contengono **solo i valori dinamici** che riempiono i `%s` del messaggio CSV (es. `concat('istanza_utility_id=', NEW.istanza_utility_id::text)`).

**Motivo**: feedback utente diretto in sessione. Il messaggio descrittivo è già nel CSV `messaggi_errore` (single source of truth). Duplicarlo nel codice causa doppio messaggio e drift quando si traduce/aggiorna il CSV.

---

## 4. Punti residui aperti (NON risolti in questo deploy)

### 4.1 Mismatch `fn_get_emittenti_scope_sr_ids` vs PK reale (§9 brief) — RISOLTO 2026-05-02

L'osservazione del backend era valida. Aperta sessione di analisi 2026-05-02 → conclusione documentata in [refactor-emittente-id-canonico.md](refactor-emittente-id-canonico.md):

* Il pattern duale (SR id vs PK reale) **non e' un bug architetturale**: e' una scelta intenzionale uniforme cross-ruolo (emittente, reseller, cliente, fornitore). Refactor "PK ovunque" sconsigliato.
* Il bug locale (filtro PK confrontato con array SR) si risolve aggiungendo `script.fn_get_emittenti_scope_pk_ids` come fn parallela a `_sr_ids`, con `_sr_ids` refactored come wrapper thin (single source of truth dei guard).
* Pattern duale documentato in [guida soggetti-e-ruoli §5b](../../guide/soggetti-e-ruoli-anagrafici.md) — sezione canonica per le scelte future.
* Memoria `feedback_emittente_pk_vs_soggetto_ruolo` aggiornata con la decisione (mantenuta per evitare confusione futura).

Implementazione DB (migration `20260502-01` e `-02`) + test pgTAP parity + manual doc completati nella stessa PR.

Lavoro BE residuo (gestito su `dev/backend-tid`):

* Aggiungere `PermissionResolver.get_emittenti_pk_ids` simmetrico a `get_emittenti_sr_ids`
* Sostituire i filtri PK-vs-SR in [`preventivi_repository.py:81-87`](../../../backend/apps/vendite/db/preventivi_repository.py#L81-L87) e [`vendite_repository.py:39-41`](../../../backend/apps/vendite/db/vendite_repository.py#L39-L41) con `_pk_ids`

### 4.2 Coerenza post-DELETE BA (out of scope)

Se viene cancellato un BA che è l'unica fonte satellite di una coppia `(istanza, utility)` già usata in preventivi, non c'è oggi un trigger che blocca la cancellazione o invalida i preventivi. Tracciato come issue futura — **non bloccante** per il rollout preventivi.

### 4.3 Istanze totalmente orfane storiche

Il backfill (§B) crea IDP solo per istanze con BA esistente. Le istanze totalmente orfane (no BA, no IDP, no cliente) vengono solo segnalate via `RAISE NOTICE` durante l'apply. Vanno valutate manualmente. In dev plausibile sia 0; verificare al primo apply.

### 4.4 GUC contract per contesti non-API

Il trigger `trgfn_preventivi_default_emittente` solleva `E_PREV_EMITTENTE_NON_RISOLTO` se la GUC `app.current_user_id` è vuota. Documentato in fn comment + brief. **Implicazione operativa**: pgAgent jobs / Liquibase data migrations / DBA manuali che inseriscono in `vendite.preventivi` devono passare `emittente_fiscale_id` esplicito (oppure prima `set_config('app.current_user_id', '<id>', false)`).

Per ora nessun caller del genere è noto. Se futuro batch automatico ne richiede uno, valutare un helper `script.fn_set_session_user_for_migration()`.

---

## 5. Apply order Liquibase (single deploy)

```
00_schema/vendite/20260501-09          → ADD COLUMN nullable
20_code/anagrafiche/20260501-10        → trigger require_utility_dichiarata su istanze
20_code/script/20260501-11             → fn_check_utility_istanza_coerenza
20_code/vendite/20260501-12            → trgfn_preventivi_default_emittente (BEFORE INSERT)
20_code/vendite/20260501-13            → trgfn_preventivi_guard_utility_istanza_coerenza
20_code/vendite/20260501-14            → vw_preventivi_list (lettura colonna persistita)
80_data/changelog/20260501-15          → cleanup preventivi malformati
80_data/changelog/20260501-16          → backfill istanze_dati_precontrattuali
80_data/changelog/20260501-17          → backfill preventivi.emittente_fiscale_id
80_data/sql/...messaggi_errore.csv     → loadUpdateData runOnChange (i 4 nuovi codici)
80_data/sql/...automation_lock_columns → loadUpdateData runOnChange (riga emittente)
90_end/20260501-18                     → SET NOT NULL su istanza + emittente
```

Nessuna finestra vulnerabile: ADD COLUMN nasce con il trigger BEFORE INSERT già attivo (file 20_code-12 segue 00_schema-09 nell'autogen). Backfill in 80_data usa fn esistenti già definite in 20_code. NOT NULL solo dopo backfill, con preCondition `expectedResult: 0` come sicurezza.

---

## 6. Cosa fare lato BE quando il deploy DB sarà landed

1. ✅ **Niente**: la view è retrocompatibile, il `INSERT` standard continua a funzionare (l'operatore loggato ha la GUC popolata).
2. **Aggiungere i 4 codici errore in `apps/core/services/error_policies.py`** con le ui_action di §2.4.
3. **Validator pre-trigger nel service `crea_preventivo`** (per UX, non per sicurezza):
   - `ErrorManager.require(istanza_utility_id is not None, ...)` — anche prima del DB
   - controllo coerenza `(istanza, utility)` via fn (chiamata extra) o via lookup repo, per ritornare errore prima del DB
4. **Drawer FE preventivo**:
   - Asterisco `*` su utility_id e istanza_utility_id
   - Picker istanza obbligatorio se BA non selezionato
5. **Admin globale flow**: il drawer admin deve esporre selettore emittente quando l'operatore corrente è admin globale (no EF in scope).

---

*Generato dal DB agent il 2026-05-01 in risposta al brief preventivi rev2.*
*Spostare in `work-done/` post-landing.*
