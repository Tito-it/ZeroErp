# Risposta DB al brief BE — Refactor `DEFAULT_UTILITY_ID` → framework FK-surrogata parametrico

> **Status**: ✅ DB-side completo, in attesa apply su `dev/db-tid` -> `Tito-dev`.
>
> **Origine**: brief BE rev2 (sessione 2026-05-02) "Refactor DEFAULT_UTILITY_ID → codice_interno"
> **Esecutore**: DB agent su `dev/db-tid`
> **Data**: 2026-05-02

---

## TL;DR per il backend

Il rename `DEFAULT_UTILITY_ID -> DEFAULT_UTILITY` e' stato implementato come **caso d'uso del nuovo framework parametrico FK-surrogata**, non come trigger ad-hoc. Il framework:

* generalizza il guard precedente `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*` (droppato),
* copre **anche `config.parameter_overrides`** (lacuna nota chiusa),
* permette di aggiungere nuovi pattern via riga seed nel registry, senza nuovo codice DB.

**Interfacce per il BE**:

* **Parametro rinominato**: `DEFAULT_UTILITY_ID` -> `DEFAULT_UTILITY`. `default_value` resta NULL (nessun seed valore di default oggi). I quattro drawer FE (in realta' due — vedi §5) devono usare il nuovo `code` e risolvere via `useParameterDefaults(['DEFAULT_UTILITY'])`.
* **Codice errore per `error_policies.py`**: due nuovi codici generici, uno per default e uno per override. Mappa per `parameter_code` in JSONB context (vedi §3 sotto).
* **Validazione coerente su override**: ora il dispatcher copre anche `POST /api/v1/core/parameters/settings/override/`. Il test BE `value='XYZ_INESISTENTE' -> 400` dovrebbe ora funzionare via DB (era bloccante nel brief originale).

---

## 1. Files creati / modificati

### 00_schema (1 file)

| File | Scopo |
|---|---|
| `00_schema/config/20260502-03-create-parameter-fk-surrogate-mctit.yaml` | Tabella registry `config.parameter_fk_surrogate` |

### 20_code (6 file)

| File | Oggetto creato / droppato |
|---|---|
| `20_code/script/20260502-04-create-fn-check-parameter-fk-surrogate-mctit.yaml` | `script.fn_check_parameter_fk_surrogate(text, text) RETURNS boolean` (riusabile da entrambi i dispatcher) |
| `20_code/config/20260502-05-create-trgfn-parameters-fk-surrogate-dispatch-mctit.yaml` | `config.trgfn_parameters_fk_surrogate_dispatch()` + trigger `trg_parameters_a10_fk_surrogate_dispatch_ins_upd` |
| `20_code/config/20260502-06-create-trgfn-parameter-overrides-fk-surrogate-dispatch-mctit.yaml` | `config.trgfn_parameter_overrides_fk_surrogate_dispatch()` + trigger speculare su `parameter_overrides` |
| `20_code/config/20260502-07-drop-trgfn-parameters-guard-default-tipo-soggetto-dettaglio-mctit.yaml` | DROP function + trigger legacy DEFAULT_TIPO_SOGGETTO_DETTAGLIO (sostituito dal dispatcher) |
| `20_code/dbops/20260502-09-create-vw-parameter-fk-surrogate-dangling-mctit.yaml` | Vista diagnostica `dbops.vw_parameter_fk_surrogate_dangling` per righe orfane post-DELETE target |

### 80_data (3 modifiche)

| File | Modifica |
|---|---|
| `80_data/sql/config/parameter_fk_surrogate.csv` | **Nuovo CSV seed** con 2 righe: pattern LIKE `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_%` -> `tipi_soggetto_dettaglio.codice_interno`, pattern EXACT `DEFAULT_UTILITY` -> `utilities.codice_interno` |
| `80_data/changelog/20260502-08-load-parameter-fk-surrogate-mctit.yaml` | Loader runOnChange per il CSV sopra |
| `80_data/sql/config/parameters.csv` | **Riga id=12 modificata in place**: `code` da `DEFAULT_UTILITY_ID` a `DEFAULT_UTILITY`, `description` aggiornata. `default_value` resta NULL |
| `80_data/sql/config/messaggi_errore.csv` | **Append 2 codici**: `E_PARAMETER_DEFAULT_VALUE_INVALID` (id 422) e `E_PARAMETER_OVERRIDE_VALUE_INVALID` (id 423) |

### pgTAP (3 file)

| File | Test |
|---|---|
| `db/pgtap/config/test-parameter-fk-surrogate-dispatch-v1.sql` | 14 test su dispatcher `parameters` (registry seed, fn_check unit, dispatcher INSERT/UPDATE valid+invalid+OF clause) — sostituisce `test-parameters-guard-default-tipo-soggetto-dettaglio-v1.sql` (eliminato) |
| `db/pgtap/config/test-parameter-overrides-fk-surrogate-dispatch-v1.sql` | 7 test su dispatcher `parameter_overrides` (chiusura della lacuna nota) |
| `db/pgtap/dbops/test-vw-parameter-fk-surrogate-dangling-v1.sql` | 4 test sulla vista diagnostica (esistenza + 0 dangling iniziali + bypass trigger via session_replication_role per simulare riga orfana + colonne attese) |

### Doc (5 file aggiornati / creati)

| File | Tipo |
|---|---|
| `docs/it/linee-guida-sql.md` | **Nuova sezione §6b** "Riferimenti esterni a tabelle di catalogo (chiave naturale stabile)" — formalizza il principio + tech debt esplicito su `DEFAULT_IVA_ID` |
| `docs/it/dbzero/config/manual/parameter_fk_surrogate.md` | Manuale registry |
| `docs/it/dbzero/config/manual/trgfn_parameters_fk_surrogate_dispatch.md` | Manuale dispatcher su parameters |
| `docs/it/dbzero/config/manual/trgfn_parameter_overrides_fk_surrogate_dispatch.md` | Manuale dispatcher su parameter_overrides |
| `docs/it/dbzero/script/manual/fn_check_parameter_fk_surrogate.md` | Manuale fn riusabile |
| `docs/it/dbzero/dbops/manual/vw_parameter_fk_surrogate_dangling.md` | Manuale vista diagnostica |
| `docs/it/dbzero/config/manual/trgfn_parameters_guard_default_tipo_soggetto_dettaglio.md` | Aggiornato: marcato DEPRECATA con redirect al framework |

### Autogen rigenerato

`changelog-autogen.yaml` rigenerato con `python3 scripts/gen_master_autogen.py`. Tutti i 6 nuovi file 00_schema/20_code inclusi correttamente, ordering 03 -> 04 -> 05 -> 06 -> 07 -> 09 (numero 08 e' nel folder 80_data/changelog incluso via includeAll, non autogen).

---

## 2. Cosa cambia per il BE — operativamente

### 2.1 Rename del code parametro

| Prima | Adesso |
|---|---|
| `DEFAULT_UTILITY_ID` | `DEFAULT_UTILITY` |

L'API `GET /api/v1/core/parameters/defaults/?codes=DEFAULT_UTILITY_ID` post-deploy ritornera' **niente** per `DEFAULT_UTILITY_ID`. Il FE deve aggiornare il code richiesto a `DEFAULT_UTILITY`. Stessa shape di payload, diverso `code`.

`default_value` resta NULL (nessun seed value scelto centralmente). Quando un admin inserira' un valore di default lato `parameter_overrides` (scope emittente/user/group), il valore dovra' essere un `codice_interno` di `config.utilities` (es. `ENERGIA`, `GAS`, `IDRICO`, `FONIA`, `BASE`).

### 2.2 Lookup applicativo lato BE

Il FE chiede via API il valore risolto (text) -> deve poi convertirlo in `id` per gli INSERT su tabelle che richiedono `utility_id`:

```python
# Pseudo BE: dato il valore risolto (codice_interno), risolvere a id
codice = resolved["DEFAULT_UTILITY"]  # es. "ENERGIA"
util_id = (
    UtilitySomething  # repo / cursor su config.utilities
    .objects.filter(codice_interno=codice)
    .values_list("id", flat=True).first()
)
```

In alternativa, esporre direttamente l'id via composable FE che combina parameter + lookup `utilities` (vedi §5 "FE side").

### 2.3 Il nuovo dispatcher copre anche `parameter_overrides`

Il test BE rev2 §1/§2 (POST override con codice valido / inesistente) ora gira interamente lato DB:

```
POST /api/v1/core/parameters/settings/override/
{ "parameter_code": "DEFAULT_UTILITY", "value": "ENERGIA" }
-> 200

POST /api/v1/core/parameters/settings/override/
{ "parameter_code": "DEFAULT_UTILITY", "value": "XYZ_INESISTENTE" }
-> 400  (E_PARAMETER_OVERRIDE_VALUE_INVALID, P0001 dal DB)
```

Il middleware `apps.core.middleware.api_exception_middleware` gia' propaga le exception DB con `error_code` nel context JSONB; basta mappare i due nuovi codici in `error_policies.py` (vedi §3).

---

## 3. Codici errore da gestire in `error_policies.py`

Due codici **generici** (no per-pattern), discriminabili tramite `parameter_code` nel JSONB context.

| Codice | HTTP | Origine | UI action consigliata |
|---|---|---|---|
| `E_PARAMETER_DEFAULT_VALUE_INVALID` | 400 | dispatcher BEFORE INSERT/UPDATE su `parameters` | toast: `"Valore di default per ${parameter_code} non valido: deve esistere in ${target}"` |
| `E_PARAMETER_OVERRIDE_VALUE_INVALID` | 400 | dispatcher BEFORE INSERT/UPDATE su `parameter_overrides` | toast: `"Override per ${parameter_code} non valido: il valore deve esistere in ${target}"` |

**Context JSONB sollevato** (chiavi disponibili nel detail dell'exception):

```json
// E_PARAMETER_DEFAULT_VALUE_INVALID
{
  "parameter_id":  12,
  "code":          "DEFAULT_UTILITY",
  "default_value": "XYZ",
  "target":        "config.utilities.codice_interno"
}

// E_PARAMETER_OVERRIDE_VALUE_INVALID
{
  "override_id":      42,
  "parameter_id":     12,
  "code":             "DEFAULT_UTILITY",
  "overridden_value": "XYZ",
  "target":           "config.utilities.codice_interno"
}
```

**Codice errore precedente `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID` (id 399)**: deprecato, mantenuto in `messaggi_errore` per non rompere chi lo referenzia ancora. Verificare se `error_policies.py` lo cita: se si', sostituirlo con `E_PARAMETER_DEFAULT_VALUE_INVALID` (la mappatura UI sul `code` JSONB resta corretta).

---

## 4. Cosa NON e' stato fatto (e perche')

### 4.1 `DEFAULT_IVA_ID` resta legacy (intenzionale)

`config.iva` **non espone `codice_interno`**. Per applicare il framework dovremmo prima:

1. ALTER TABLE config.iva ADD COLUMN codice_interno (NOT NULL, UNIQUE)
2. Backfill (es. id=16 IVA 22% -> codice_interno = 'IVA_22')
3. Il runner `dbops.fn_run_automations_lock_columns` provisiona automaticamente il trigger di lock (nessuna riga in `automation_lock_columns`)
4. Rinominare `DEFAULT_IVA_ID` -> `DEFAULT_IVA` (analogo a UTILITY)
5. Aggiungere riga al registry

**Decisione**: questo PR **non tocca `config.iva`**. La modifica e' tracciata come tech debt esplicito in `linee-guida-sql §6b` ("Tech debt riconosciuto"). Quando si decidera' di farla, il framework e' pronto: e' una migration in piu', zero codice DB nuovo.

### 4.2 Vista diagnostica anziche' guard BEFORE DELETE sul target

Se viene cancellata una riga di `config.utilities` o `config.tipi_soggetto_dettaglio` referenziata da un parametro/override, il valore resta "appeso". Soluzioni possibili:

* **Hard**: guard BEFORE DELETE su utilities/tipi_soggetto_dettaglio che cerca riferimenti via registry.
* **Soft (scelta nostra)**: vista `dbops.vw_parameter_fk_surrogate_dangling` che lista le righe orfane. Diagnostica, non blocca.

Motivazione "soft": le tabelle target sono di catalogo seed, le DELETE sono eccezionali; un guard BEFORE DELETE generico costerebbe overhead a tutte le DELETE (anche legittime). Vista periodica + alert oncall e' sufficiente.

### 4.3 Niente generalizzazione del framework oltre `parameters`

Il pattern (registry + dispatcher) e' replicabile in futuro a qualunque tabella che abbia "valori-stringa che devono esistere in un'altra tabella ma senza FK fisica". **Non lo abbiamo esteso ora**: avrebbe ampliato il PR senza casi d'uso concreti. Il principio §6b della linee-guida copre l'estensione futura.

---

## 5. FE side — cosa cambiare

### 5.1 Drawer effettivamente coinvolti

Verificato: solo **2 drawer** consumano `DEFAULT_UTILITY_ID` (il brief originale diceva 4):

* [`frontend/src/anagrafiche/components/ClienteDrawer.vue:51`](../../../../frontend/src/anagrafiche/components/ClienteDrawer.vue#L51)
* [`frontend/src/vendite/preventivi/components/PreventiviDrawer.vue:86`](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue#L86)

`ListinoDrawer` e `ContrattoDrawer` (citati nel brief) **non** lo usano: il loro `utility_id` viene da altri input.

### 5.2 Refactor proposto (lasciato al BE/FE)

```js
// 1) Rinominare i code richiesti
const { defaults, load } = useParameterDefaults(['DEFAULT_IVA_ID', 'DEFAULT_UTILITY'])

// 2) Risoluzione id: il valore risolto e' un codice_interno, non un id.
//    Composable opzionale che combina parameter + lookup utilities:
const { id: defaultUtilityId } = useUtilityDefaultId()  // wraps DEFAULT_UTILITY + lookup utilities by codice_interno

// 3) Form prefill
form.value.utility_id = defaultUtilityId.value
```

In alternativa (se non si vuole nuovo composable): leggere il codice e fare lookup nelle utilities gia' caricate dal drawer.

---

## 6. Apply order Liquibase

```
00_schema/config/20260502-03                 -> CREATE TABLE config.parameter_fk_surrogate
20_code/script/20260502-04                   -> script.fn_check_parameter_fk_surrogate
20_code/config/20260502-05                   -> trgfn_parameters_fk_surrogate_dispatch + trigger
20_code/config/20260502-06                   -> trgfn_parameter_overrides_fk_surrogate_dispatch + trigger
20_code/config/20260502-07                   -> DROP guard legacy
20_code/dbops/20260502-09                    -> vw_parameter_fk_surrogate_dangling
80_data/changelog/20250715-01 (re-run)       -> reload parameters.csv (id=12 rinominato a DEFAULT_UTILITY, default_value=NULL)
80_data/changelog/20250717-22 (re-run)       -> reload messaggi_errore.csv (2 nuovi codici)
80_data/changelog/20260502-08                -> seed parameter_fk_surrogate.csv
```

**Ordering safety**: il dispatcher su `parameters` viene creato prima del reload del CSV. Al reload, `default_value=NULL` per la riga rinominata -> short-circuit del dispatcher. Per `DEFAULT_TIPO_SOGGETTO_DETTAGLIO_*` il CSV non e' modificato (no re-run del 20250717-23). Il seed registry (08) viene dopo: nei reload precedenti il dispatcher trova registry vuoto e fa no-op (ritorna true sempre). Nessuna finestra vulnerabile.

**Ambiente non-produzione**: come da indicazioni utente, non c'e' produzione attiva. Il deploy puo' essere fatto in singolo apply su `dev/db-tid` -> `Tito-dev`. Coordinamento col FE: rilascio insieme.

---

## 7. Test pgTAP (in attesa di run)

Suite preparata. Run consigliato post-apply:

```bash
scripts/testpgtap.sh db/pgtap/config/test-parameter-fk-surrogate-dispatch-v1.sql
scripts/testpgtap.sh db/pgtap/config/test-parameter-overrides-fk-surrogate-dispatch-v1.sql
scripts/testpgtap.sh db/pgtap/dbops/test-vw-parameter-fk-surrogate-dangling-v1.sql
```

Coverage:

* **dispatcher parameters (14 test)**: registry seed, fn_check unit (NULL, code fuori registry, EXACT/LIKE valid+invalid), trigger INSERT/UPDATE valid+invalid, OF clause su description, code fuori registry no-op.
* **dispatcher parameter_overrides (7 test)**: INSERT/UPDATE valid+invalid su DEFAULT_UTILITY (EXACT) e DEFAULT_TIPO_SOGGETTO_DETTAGLIO_CL (LIKE), parametro fuori registry, UPDATE.
* **vista dangling (4 test)**: existence, count zero su DB pulito, simulazione dangling via `session_replication_role=replica`, schema colonne.

---

## 8. Lookup runtime per il BE (utility query pratiche)

```sql
-- Lista pattern abilitati (per UI admin / debug)
SELECT code_pattern, match_mode, target_schema, target_table, target_column
  FROM config.parameter_fk_surrogate
 WHERE enabled
 ORDER BY code_pattern;

-- Validazione manuale (utile in test BE)
SELECT script.fn_check_parameter_fk_surrogate('DEFAULT_UTILITY', 'ENERGIA');
-- => true

-- Diagnostica righe orfane
SELECT * FROM dbops.vw_parameter_fk_surrogate_dangling;
-- atteso: 0 righe in stato pulito
```

---

## 9. Per il backend — checklist post-merge DB

* [ ] `error_policies.py`: aggiungere mappatura `E_PARAMETER_DEFAULT_VALUE_INVALID` -> 400 + UI action su `parameter_code` (JSONB context). Idem per `E_PARAMETER_OVERRIDE_VALUE_INVALID`. Rimuovere/redirect `E_PARAMETER_DEFAULT_TIPO_SOGGETTO_INVALID` se presente (deprecato, mantenuto a livello DB per retro-compat).
* [ ] (Opzionale) Pre-validation BE in `parameters_service` prima di chiamare il DB su `POST /override/` (UX migliore, risparmia un round-trip). Il DB resta autorita' per il vincolo.
* [ ] FE: aggiornare `useParameterDefaults` chiamato in `ClienteDrawer.vue` e `PreventiviDrawer.vue` da `DEFAULT_UTILITY_ID` a `DEFAULT_UTILITY`. Aggiungere lookup `utilities.codice_interno -> id` nel composable (o inline nel drawer).
* [ ] (Opzionale) Test E2E: drawer cliente con override `DEFAULT_UTILITY = ENERGIA` -> form precompilato con `utility_id = 1` (ENE).

---

*Generato dal DB agent il 2026-05-02 in risposta al brief BE rev2 "DEFAULT_UTILITY_ID -> codice_interno".*
*Spostare in `work-done/` post-landing.*
