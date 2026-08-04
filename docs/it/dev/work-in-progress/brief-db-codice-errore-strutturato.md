# Brief DB — far arrivare il codice errore di dominio al backend

**Chi scrive:** backend (`dev/backend-tid`), 2026-08-05.
**Cosa chiede:** una riga in `script.fn_log_and_raise_error` — il codice errore
viaggia in un campo strutturato dell'eccezione invece di essere ripescato dal
testo.
**Origine:** [brief-be-bonifica-riferimenti-morti](brief-be-bonifica-riferimenti-morti.md) §5,
che nasce da [brief-db-bonifica-riferimenti-morti](brief-db-bonifica-riferimenti-morti.md).
**Perimetro:** **una** funzione DB + **un** metodo Python. Ma cambia il
comportamento di ogni errore dell'applicazione: va fatta come slice a sé.

> **Correzione al brief BE §5.** Quel paragrafo concludeva che il codice non
> arriva **mai** e che `error_policies.py` non scatta mai. Misurato sul percorso
> reale: **arriva nel 91% dei casi**, ma per un motivo che non è una difesa. Il
> difetto è più piccolo di come era scritto e più insidioso di come suonava:
> non è un guasto, è una dipendenza da qualcosa che nessuno ha progettato.

---

## 1. Cosa serve al backend, e cosa riceve

Il backend deve sapere **quale** errore è, non cosa dice: da `error_policies.py`
(`codice → HTTP status → azione UI`, centinaia di voci) dipendono il 409 sul
duplicato, il 404 sul non trovato, il 403 sul vietato, e il messaggio che
l'operatore legge.

`script.fn_log_and_raise_error` chiude così:

```sql
RAISE EXCEPTION '%', v_msg
    USING DETAIL = coalesce(v_detail, ''),
          HINT   = coalesce(v_hint, '');
```

Partono tre cose: il messaggio localizzato, `causa` (in `DETAIL`), `soluzione`
(in `HINT`). **Il codice non è in nessuna delle tre.** Misurato:

| Misura | Valore |
|---|---|
| Messaggi `it` che contengono il proprio codice | **0 su 635** |
| `causa` / `soluzione` che lo contengono | **0** |
| SQLSTATE | sempre `P0001` (default di `RAISE EXCEPTION`) |

Lato Python, `ErrorTranslator._extract_app_error_code` lo cerca con una regex
(`\bE_[A-Z][A-Z0-9_]+\b`) nel **testo intero** dell'eccezione, e il commento
dice: *«`fn_log_and_raise_error` include il codice nel RAISE EXCEPTION via
`fn_get_messaggio`»*. Non è vero: `fn_get_messaggio` mette il codice nel testo
**solo nel fallback**, cioè quando la riga manca dal seed.

---

## 2. Perché oggi funziona lo stesso, e perché non basta

Il driver, nel testo dell'eccezione, allega anche **lo statement chiamante**. E
lì il codice c'è, scritto a mano:

```
QUERY: SELECT script.fn_log_and_raise_error(
         'documenti', 'trgfn_template_asset_block_delete',
         'E_DOCUMENTI_ASSET_DELETE_BLOCKED',      <-- la regex trova QUESTO
         jsonb_build_object(...), NULL::uuid)
CONTEXT: funzione PL/pgSQL documenti.trgfn_template_asset_block_delete() riga 14 a PERFORM
```

Il backend sta leggendo il codice dal **sorgente della chiamata**, non dal dato.
Censimento dei **971** call site nei corpi vivi:

| | Call site | Cosa succede |
|---|---:|---|
| **A** | **886** | codice letterale `E_*` → la regex lo trova (per fortuna, non per progetto) |
| **B** | **76** | codice letterale **senza prefisso `E_`** → la regex non lo riconosce |
| **C** | **9** | codice da espressione → nel testo c'è il **nome della variabile** |

**Il gruppo C è il danno vivo.** Sono le guard di cambio stato, cioè gli errori
che l'operatore incontra ogni giorno:

```sql
PERFORM script.fn_log_and_raise_error(..., v_motivi -> 0 ->> 'codice', ...)
```

`vendite.trgfn_ordini_guard_transizione` · `trgfn_commesse_guard_transizione` ·
`trgfn_preventivi_guard_annullamento` · `fn_cambia_stato_preventivo` ·
`fn_riporta_lotto_a_draft` · `fn_annulla_lotto_da_draft` ·
`fn_elimina_fattura_da_lotto` · `fn_riapri_riconsegna_reso` ·
`script.trgfn_lock_columns` (`msgcode`).

Per tutte e nove il translator ripiega su `E_DATABASE`, che è classificato
**tecnico**: il messaggio localizzato viene **scartato** e sostituito da un testo
generico, e il dettaglio è soppresso (*«Dettaglio tecnico non esposto»*). Chi
tenta una transizione non ammessa non legge perché non è ammessa.

⚠️ **Il gruppo A è la parte che preoccupa di più**, proprio perché funziona: se
domani una di quelle 886 chiamate passa il codice per variabile — che è
esattamente ciò che è successo alle nove del gruppo C, una alla volta — smette di
funzionare **in silenzio**, senza che nulla fallisca a DB né in CI.

**E la stessa pesca nel testo è scritta in tre posti diversi**, ognuno col suo
modo: `ErrorTranslator._extract_app_error_code`, `payload_helpers.DB_ERROR_CODE_RE`
(dentro `translate_db_errors`), `ErrorManager.raise_from_database_error`
(substring match sui `known_markers` del chiamante). Il campo strutturato le
riduce a una lettura sola.

---

## 3. La forma proposta

Il codice viaggia in un campo dedicato dell'eccezione. `RAISE ... USING` ne
espone cinque oltre a `DETAIL`/`HINT`; **`CONSTRAINT` è il meno improprio**: il
codice errore *è* il nome della regola violata.

```sql
    -- 5) Sollevamento eccezione con DETAIL/HINT localizzati.
    --    CONSTRAINT porta il CODICE di dominio: e' l'unico campo strutturato
    --    che il backend puo' leggere senza fare parsing del testo. Il codice
    --    NON compare nel messaggio (per scelta: il messaggio e' per l'utente).
    RAISE EXCEPTION '%', v_msg
        USING ERRCODE    = 'P0001',
              DETAIL     = coalesce(v_detail, ''),
              HINT       = coalesce(v_hint, ''),
              CONSTRAINT = p_error_code;
```

`ERRCODE = 'P0001'` è già il default: renderlo esplicito serve a dire che il
contratto è *«P0001 + `CONSTRAINT` valorizzato = errore di dominio»*, che è la
condizione che il backend userà per fidarsi del campo (§5).

### Verificato davvero, non dedotto

Round-trip DB → libpq → psycopg3 → `django.db.DatabaseError` provato su questo
DB (PostgreSQL 18.4). Arrivano **tutti** i campi: `schema_name`, `table_name`,
`column_name`, `datatype_name`, `constraint_name`. E `constraint_name`
sopravvive anche:

* **annidato** in più livelli PL/pgSQL (è il caso normale: trigger → guard → helper);
* attraverso un blocco `EXCEPTION ... RAISE;` che **ri-solleva**.

### Le alternative, e perché no

| Strada | Perché no |
|---|---|
| SQLSTATE custom (classe `U0`) | pulita, ma SQLSTATE è di 5 caratteri: servirebbe una mappa `codice → sqlstate` da mantenere allineata al seed. Un secondo posto da tenere in bolla, cioè il difetto da cui nasce tutto |
| Prefisso convenzionale nel messaggio | sporca il testo che l'operatore legge, e resta parsing |
| `COLUMN` | funziona identico, ma dice una cosa falsa: non è una colonna |
| `DETAIL` in JSON | `DETAIL` è già occupato da `causa`, che è per l'utente |

---

## 4. Compatibilità: nessuna regressione, e migrazione in due tempi

**Il campo non cambia `str(exc)`.** Verificato: con `CONSTRAINT` valorizzato il
testo dell'eccezione resta

```
Username gia' in uso.
DETAIL:  causa
HINT:    soluzione
CONTEXT: funzione PL/pgSQL ...
```

e il codice **non** vi compare. Conseguenza pratica: i tre parser di testo che
esistono oggi continuano a comportarsi **esattamente** come prima. Quindi:

1. **Il DB può andare per primo, da solo.** Applicare il changeSet senza toccare
   il backend non cambia niente per nessuno: nuovo campo ignorato, comportamento
   invariato. Nessuna finestra di rottura, nessuna fase di compatibilità.
2. Il backend adotta il campo subito dopo, con la lettura difensiva del §5.
3. Solo quando i pgTAP e i test Django del §6 sono verdi si valuta se togliere il
   fallback a regex. **Non prima**, perché ci sono funzioni che sollevano con
   `RAISE EXCEPTION` diretto senza passare da `fn_log_and_raise_error`: per
   quelle il campo resta vuoto e la regex è ancora l'unica strada.

---

## 5. Cosa fa il backend (per completezza — lo scriviamo noi)

In `ErrorTranslator._from_database_error`, prima della regex:

```python
        # Codice di dominio dal campo strutturato: e' valido SOLO su P0001.
        # Su una violazione di vincolo vera (classe 23xxx) `constraint_name`
        # contiene il nome del vincolo DB (`uq_...`, `fk_...`): prenderlo per
        # un codice applicativo produrrebbe un codice inesistente, quindi la
        # policy di fallback e un 500 al posto di un 409 parlante.
        app_code = None
        if sqlstate == "P0001":
            app_code = getattr(diag, "constraint_name", None) or None
        if app_code is None:
            app_code = ErrorTranslator._extract_app_error_code(raw_message)
```

⚠️ **Il guard su `sqlstate == 'P0001'` non è prudenza, è necessario.** Senza,
ogni `IntegrityError` porterebbe il nome del vincolo dentro `code`, e
`map_integrity_error` — che oggi traduce quei vincoli in codici di dominio
leggendo `str(exc)` — si troverebbe scavalcato a monte.

Stesso innesto, con la stessa condizione, in `translate_db_errors` e
`ErrorManager.raise_from_database_error`.

---

## 6. Test richiesti

Il giro va asserito **intero**, altrimenti resta un altro presidio che si può
dimenticare di lanciare:

* **pgTAP** su `script.fn_log_and_raise_error`: che il campo `CONSTRAINT` esca
  valorizzato col codice passato, e che `DETAIL`/`HINT` restino `causa`/`soluzione`.
  Da fare su un codice **presente a seed** — un codice mancante fa scattare il
  placeholder di `fn_get_messaggio` e il test passerebbe per il motivo sbagliato
  (è lo stesso inganno di `test-fn-crea-auth-user`, brief BE §4).
* **pgTAP** su almeno **una** delle nove guard del gruppo C — dove il codice
  arriva da `v_motivi` — perché è lì che il vecchio meccanismo non arrivava.
* **test Django** end-to-end: eccezione DB reale → `ApiError.code` giusto →
  HTTP status giusto dalla policy. Non un mock: il mock non vede né i campi diag
  né il testo del driver, che è precisamente ciò che stiamo cambiando.

---

## 7. ⚠️ Nota — la riclassificazione dei codici senza prefisso (gruppo B)

**Non è in questa slice, ed è bene che non lo sia**, ma va deciso: il campo
strutturato risolve A e C, **non risolve B**. Lì il problema non è il trasporto,
è il **nome**.

Nel DB ci sono **57 codici distinti** (su 636) che non seguono la convenzione
`E_{MODULO}_{TIPO}` di `docs/it/dev/api.md`: `PRATICHE_TRANSIZIONE_NON_AMMESSA`,
`PREV_TRANSIZIONE_NON_AMMESSA`, `DEFINIZIONE_*`, `FLUSSI_*`, `TEMPLATE_FLUSSO_*`,
`ERRORE_PARAMETRI` (13 call site), `SEQUENZA_NON_CONFIGURATA`,
`CODICE_NON_MODIFICABILE`, `CF_NON_VALIDO`, `PIVA_NON_VALIDA`… — **76 call site**.
Sono tutti regolarmente a seed in `config.messaggi_errore`.

Col campo strutturato quei codici **arriveranno** al backend. Ma lì incontrano un
secondo muro, tutto lato BE: non sono registrati in `error_policies.py`, e
`ErrorPolicyRegistry.resolve` ha una scorciatoia esplicita solo per i codici che
cominciano per `E_` (→ 400 «errore di validazione»). Tutti gli altri cadono su
`E_GENERICO` → **HTTP 500**. Cioè: un operatore che tenta una transizione di
pratica non ammessa fa apparire al frontend un errore di server.

Le due strade, e nessuna è gratis:

| | Cosa comporta | Chi tocca |
|---|---|---|
| **Rinominare** i 57 a `E_*` | seed `config.messaggi_errore`, tutti i call site, i pgTAP che asseriscono quei codici, `error_policies.py` | DB + BE |
| **Registrarli** così come sono | solo `error_policies.py` (57 voci), ma la convenzione dichiarata in `api.md` resta disattesa e il prossimo codice nascerà di nuovo storto | solo BE |

Decisione di Tid. **Non blocca questa slice**: oggi quei 76 call site sono rotti,
dopo il campo strutturato sono rotti **uguale** — nessun peggioramento, solo un
difetto che diventa visibile invece di restare confuso con l'altro.

---

## 8. ⚠️ Allegato — un difetto vivo sulla stessa funzione (`FP_VARIADIC`)

Emerso misurando per questo brief, **indipendente da esso**, ma sta sulla
funzione che questo brief modifica: conviene guardarli insieme.

La regola v3 del classificatore (`brief-db-bonifica-riferimenti-morti` §3.1)
esenta i 42883 su `fn_log_and_raise_error` se la funzione chiamata *ha* un
parametro `VARIADIC`. Manca un pezzo: in PostgreSQL una funzione
`VARIADIC <tipo>[]` **non può essere chiamata con zero argomenti variadici**.
Solo `VARIADIC "any"` lo permette — per questo `format('x')` funziona:

```
=> select script.fn_log_and_raise_error('t'::text,'p'::text,'E_X'::text,NULL::jsonb,NULL::uuid);
ERRORE: la funzione script.fn_log_and_raise_error(text, text, text, jsonb, uuid) non esiste
=> select script.fn_log_and_raise_error('t'::text,'p'::text,'E_X'::text,NULL::jsonb,NULL::uuid,
                                        VARIADIC ARRAY[]::text[]);
ERRORE: Username gia' in uso.      <- questa risolve
```

Vale identico in PL/pgSQL. Quindi le righe etichettate `FP_VARIADIC` **non sono
rumore**: sono difetti veri, della stessa natura della famiglia F3 già corretta.
Censimento sui corpi vivi: **20 call site a 5 argomenti in 15 funzioni**.

| Funzione | Siti | Trigger |
|---|---:|---|
| `documenti.trgfn_documenti_generati_check_coerenza` | 4 | `documenti_generati` |
| `documenti.trgfn_template_documenti_versioni_block_delete` | 2 | `template_documenti_versioni` |
| `documenti.trgfn_documenti_generati_block_delete` · `_protect_snapshot` · `_eventi_block_delete` · `_eventi_block_update` · `_file_protect_file` · `trgfn_template_asset_block_delete` · `_protect_file` · `trgfn_template_documenti_versioni_protect_pubblicata` | 1 cad. | agganciate |
| `anagrafiche.trgfn_indirizzi_guard_tipo_ruolo_tipi_indirizzo` | 1 | `indirizzi` |
| `dbops.trgfn_prevent_deactivate_if_children` → `fn_log_error_only` | 1 | **343 tabelle** |
| `pratiche.fn_guard_prerequisiti_flusso` · `fn_guard_ripetibilita_flusso` · `script.fn_change_user_emittenti_scope` | 4 | non-trigger |

Prova live (transazione annullata, riga intatta):

```
BEGIN; DELETE FROM documenti.template_asset WHERE id = (SELECT min(id) ...);
ERRORE: la funzione script.fn_log_and_raise_error(unknown,unknown,unknown,jsonb,uuid) non esiste
CONTESTO: funzione PL/pgSQL documenti.trgfn_template_asset_block_delete() riga 14 a PERFORM
ROLLBACK;
```

Cosa costa davvero:

* il codice di dominio non arriva mai (SQLSTATE `42883`, non `P0001`): il backend
  traduce in `E_DATABASE` → 400 generico, dettaglio soppresso. **Il campo
  strutturato di questo brief non li salva**: la funzione non viene nemmeno
  raggiunta;
* `fn_log_error_only` non gira → **nessuna riga di log** per errori che dovevano
  essere tracciati;
* il caso `dbops.trgfn_prevent_deactivate_if_children` è il peggiore per natura:
  lì il contratto è *«logga senza sollevare»*. Un call site a 5 argomenti
  **solleva**, e fa fallire una disattivazione legittima. Ramo stretto (si prende
  quando la `ref_col` esplicita è NULL sul record OLD), ma è armato su 343 tabelle.

**Rimedio ai call site**: il 6° argomento (il messaggio, come fanno gli altri
962) oppure `VARIADIC ARRAY[]::text[]`.
**Rimedio al presidio**, che è il punto se non si vuole tornare qui: nella regola
`FP_VARIADIC` l'esenzione deve valere solo se il call site passa **almeno un**
valore variadico. `provariadic <> 0` da solo non basta.

Nota di metodo: è lo stesso modo di fallire del §3.3 del vostro brief — *«il
check è un setaccio, non una lista»*. Qui però il difetto non era nascosto sotto
un altro difetto: era nascosto **sotto un'etichetta**, come
`test-fn-search-stradario` sotto `ERRORE_FIXTURE`.

---

## 9. Riepilogo

| # | Cosa | Chi | Urgenza |
|---|---|---|---|
| 1 | `CONSTRAINT = p_error_code` in `fn_log_and_raise_error` (nuovo changeSet `runOnChange`, numerazione successiva) | DB | **alta** |
| 2 | pgTAP §6 (campo valorizzato + una guard del gruppo C) | DB | **alta** |
| 3 | Lettura del campo con guard `sqlstate = 'P0001'` nei 3 punti + test Django | BE | **alta** — dopo l'apply |
| 4 | 20 call site variadici a 5 argomenti (§8) | DB | **alta** — difetto vivo, indipendente |
| 5 | Regola `FP_VARIADIC`: esenzione solo con ≥1 valore variadico (§8) | DB | media |
| 6 | Riclassificare o registrare i 57 codici senza prefisso `E_` (§7) | decisione Tid | media |
