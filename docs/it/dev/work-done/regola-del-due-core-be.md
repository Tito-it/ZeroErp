# Regola del 2 — caccia duplicazioni nel dominio Core (backend)

> **Data analisi:** 2026-06-04
> **Ambito:** **solo backend** del dominio `core` (`backend/apps/core/`) **+ caccia
> ai BB mancanti** che gli altri domini reinventano e che dovrebbero vivere in core.
> **Profondità:** media
> **Stato:** ✅ **COMPLETATO (2026-06-04).** Tutti i candidati azionabili sono stati
> estratti/promossi: X1 (bug), A1–A6, A2/B1/B2/D1 (famiglia query-param), D2/D3, B3.
> Restano fuori solo le voci **deliberatamente non estratte**, con motivo: 🔴 falsi
> positivi (`dynamic_update`/JSONB in `email_repository`) e 🟡 **B4**
> (`INSERT…RETURNING`, parcheggiato wait-and-accumulate). Committato e spostato in
> `work-done`. Le singole voci sotto riportano lo stato ✅ FATTO con i dettagli.

Terzo capitolo dopo
[regola-del-2-vendite.md](regola-del-2-vendite.md) e
[regola-del-2-anagrafiche.md](regola-del-2-anagrafiche.md). Qui il dominio è
particolare: **core è la casa dei building block**, quindi la regola del 2 ha
**due facce**, ed entrambe sono coperte:

1. **`interno_core`** — duplicazioni *dentro* `apps/core` (due repository/view che
   ripetono lo stesso blocco) → estrazione interna.
2. **`bb_mancante_core`** — un concetto è reinventato *fuori* da core (in
   vendite/catalogo/documenti/config/anagrafiche) mentre core ha già un cugino
   simmetrico o è il posto naturale dove dovrebbe vivere → **promozione a core**.
   Il caso seme che ha innescato questa analisi (`qp_bool_optional_strict` di
   `views_listini`) è esattamente di questo tipo.

> **BE-only deliberato.** Come concordato, prima il backend perché è la superficie
> maggiore (api / db / services). Il lato FE di core (~54 composable, ~78
> componenti) sarà un capitolo separato.

## Com'è stata fatta l'analisi

Workflow dinamico: **6 agenti finder in parallelo**, ciascuno su un angolo diverso
(api validatori/helper, api views, db repository, services parte 1, services
auth/error/middleware, caccia cross-dominio ai BB mancanti). Hanno prodotto **27
candidati grezzi**. Dedup per insieme di file coinvolti → **21 candidati**. Ogni
candidato è passato a un **agente "scettico"** che ha aperto i file alle righe
indicate per stabilire se fosse **vera duplicazione di logica** o solo somiglianza
di forma (parsing param, envelope, try/except: convenzioni standard, *non*
duplicazione). Tutti gli agenti avevano in contesto il
[catalogo BB backend](../backend/catalogo-building-block-backend.md) per non
riproporre estrazioni già fatte.

| Esito | Conteggio |
| --- | --- |
| Candidati grezzi (6 finder) | 27 |
| Verificati (dopo dedup) | 21 |
| **Confermati duplicazione reale** | 16 |
| **Temi distinti dopo consolidamento manuale** | **16** |
| Scartati come falsa duplicazione | 3 |
| Scoperte collaterali (bug / codice morto / BB ignorati) | 4 |

> **Nota di metodo.** Lo sweep multi-angolo ha ri-segnalato gli stessi concetti da
> finder diversi: la **famiglia query-param** (`qp_int_optional`, wrapper strict,
> bool, ISO date) è stata trovata sia dal finder "interno_core" sia da quello
> "bb_mancante_core" → qui sono **consolidati** in voci uniche. Una coppia aveva
> **verdetti opposti** (validazione paginazione service: `real=true` vs
> `red_falso`): risolta leggendo entrambe le motivazioni — la verità è che 2 delle
> 4 occorrenze sono **codice morto** (vedi D3).

---

## ⚠️ Scoperta critica da gestire subito (bug, non solo duplicazione)

> Segnalata in cima per priorità (cfr. `feedback_bug_logici_modello`).

### 🐛 X1. `commesse_service._parse_meta_json` maschera un errore → **500 invece di 400** — ✅ FATTO (2026-06-04)

> **Bug corretto + dedup su BB core.** Rimosso `_parse_meta_json` da **entrambi** i
> service; i 5 call-site (commesse ×3, listini ×2) ora delegano a
> `_V.optional_meta(row, "meta", function_name=…) or {}` (il `or {}` preserva la
> semantica "sempre dict", dato che i call-site fanno subito `.get`/assegnazione).
> commesse ha guadagnato un `_V = PayloadValidator(E_VENDITE_VALIDATION, log_to_db=True)`
> modulo-level (mirror di listini). `import json` rimosso da entrambi (orfano).
> Il fix trasforma il crash silenzioso di commesse (JSON malformato → 500, oppure
> JSON non-dict → audit scartato in silenzio) in `E_VENDITE_VALIDATION` 400
> strutturato. **+1 test di regressione** (`test_variazione_eccezionale_meta_malformato_rifiutata`).
> 122 test commesse+listini (service+api) verdi.

[vendite/services/commesse_service.py:298-303](../../../../backend/apps/vendite/services/commesse_service.py#L298-L303)
normalizza il campo `meta` da stringa JSON a dict ma è **permissivo in modo
difettoso**: non mappa il `ValueError` di `json.loads` né il caso "JSON valido ma
non-dict". Se il client invia un `meta` malformato → **eccezione non gestita =
HTTP 500**, invece del 400 strutturato che il modello prevede.

Il gemello [vendite/services/listini_service.py:70-97](../../../../backend/apps/vendite/services/listini_service.py#L70-L97)
(`_parse_meta_json`) è invece **rigoroso e corretto** (solleva
`E_VENDITE_VALIDATION` con `log_to_db=True`). E soprattutto: **entrambi
reinventano un BB core che esiste già** —
`PayloadValidator.optional_meta` ([core/services/payload_helpers.py:641-677](../../../../backend/apps/core/services/payload_helpers.py#L641-L677)),
identico alla versione rigorosa di listini.

**Azione:** migrare *entrambi* i service a `validator.optional_meta(payload, "meta")`.
La migrazione **corregge automaticamente il bug** di commesse (il BB mappa il
`ValueError` a 400) ed elimina la duplicazione. Contesti d'uso tutti
amministrativi/audit (listini:1894/2062, commesse:480/528/598) → il pattern
rigoroso del BB è appropriato. **Priorità ALTA** per il bug, non solo per il DRY.

---

## 🟢 Candidati puliti — estrazione/promozione consigliata, basso rischio

Occorrenze quasi identiche, differenze trascurabili. Qui la regola del 2 morde nel
modo più netto.

### A1. `qp_int_optional(raw, name)` — query-param intero opzionale strict — **5 occorrenze** — `bb_mancante_core` — ✅ FATTO (2026-06-04)

> **Promosso** `qp_int_optional(raw, name) -> int | None` in
> [core/api/payload_validators.py](../../../../backend/apps/core/api/payload_validators.py)
> (accanto a `qp_int_strict`, con cause-chaining `from exc`). I 5 `_qp_int_optional`
> privati rimossi; le view importano il BB. Registrato nel
> [catalogo BB backend](../backend/catalogo-building-block-backend.md). 1243 test
> vendite+anagrafiche verdi.

Parser **byte-identico** in 5 view: ritorna `None` se assente/vuoto, solleva
`ValueError(f"{name}_invalid")` se non numerico. Core ha `qp_int` (con default) e
`qp_int_strict` (default obbligatorio) ma **manca la variante opzionale-strict**.

- [vendite/api/views_ordini.py:41-47](../../../../backend/apps/vendite/api/views_ordini.py#L41-L47)
- [vendite/api/views_contratti.py:41-47](../../../../backend/apps/vendite/api/views_contratti.py#L41-L47)
- [vendite/api/views_offerte.py:44-50](../../../../backend/apps/vendite/api/views_offerte.py#L44-L50)
- [vendite/api/views_promo_articoli.py:35-41](../../../../backend/apps/vendite/api/views_promo_articoli.py#L35-L41)
- [anagrafiche/api/views_categorie_clienti_listini.py:35-41](../../../../backend/apps/anagrafiche/api/views_categorie_clienti_listini.py#L35-L41)

**Promozione:** `qp_int_optional(raw: str | None, name: str) -> int | None` in
[core/api/payload_validators.py](../../../../backend/apps/core/api/payload_validators.py),
accanto a `qp_int`/`qp_int_strict`/`qp_bool_optional`. Firma pura, stateless, zero
dipendenze da `Request`. I 5 `_qp_int_optional` privati diventano import dal core.

### A2. `qp_bool_optional` request-aware (permissivo) — **2 occorrenze** — `bb_mancante_core` — ✅ FATTO (2026-06-04)

> Unificato in `qp_bool_optional(raw, name)` **strict** (vedi Decisione di design).
> `_optional_qp_bool` rimosso da catalogo/documenti; ora `qp_bool_optional(qp.get(k), k)`.
> ⚠️ cambio comportamento voluto: il garbage prima dava True (permissivo) → ora 400.

`_optional_qp_bool(request, key)` testualmente identico: `None` se key assente,
altrimenti `qp_bool(raw, True)` (parsing permissivo). Core ha `qp_bool_optional`
ma opera su stringa grezza, non su `Request`.

- [catalogo/api/views.py:70-74](../../../../backend/apps/catalogo/api/views.py#L70-L74)
- [documenti/api/views.py:45-49](../../../../backend/apps/documenti/api/views.py#L45-L49)

**Promozione:** wrapper request-aware in core (vedi **nota di design "layer
wrapper"** più sotto — A2/A3/B1/B2 condividono lo stesso dilemma di firma).

> **⚠️ collegato a D1.** Esiste una variante **rigorosa** (`_optional_qp_bool_strict`,
> vendite/views_listini) che NON va confusa con questa permissiva. Decidere la
> famiglia prima di estrarre.

### A3. `fetchone_scalar` — `fetchone + assert + return row[0]` — **11 (+4) occorrenze** — `interno_core` — ✅ FATTO (2026-06-04)

> **Estratto** `fetchone_scalar(cursor) -> Any` in
> [core/db/_helpers.py](../../../../backend/apps/core/db/_helpers.py) (nome
> definitivo, non `safe_fetchone_scalar`). **Scelta di design:** mantenuta la
> semantica `assert` (non un `ServiceError`): sono query `RETURNING`/SELECT a riga
> garantita, l'assert è invariante + type-narrowing, e introdurre `ServiceError`
> in `_helpers.py` (modulo DB di basso livello) accoppierebbe il layer per un caso
> "non può accadere". Migrati gli **11 siti byte-identici** + **bonus 4
> varianti-cast** scoperte accanto (`int(fetchone_scalar(cursor))` ×3 in
> partitioned_note, `str(...)` in anagrafiche_core) per non lasciare estrazione a
> metà. Lasciati fuori i 2 pattern diversi: `core_repository` (ha già `if not row:
> raise ServiceError`) e `config_crud_repository` (RETURNING record completo,
> finding D/INSERT). Registrato nel catalogo BB. 579 test core verdi.

Il candidato più ricorrente. Pattern byte-identico in **11 punti** di
`core/db/`: `cursor.execute(...)`, `row = fetchone()`, `assert row is not None`,
`return row[0]`. Il catalogo ha `row_to_dict`/`rows_to_list` ma **non** la guardia
scalar single-row.

- [auth_repository.py:46-50](../../../../backend/apps/core/db/auth_repository.py#L46-L50)
- [risorse_umane_core_repository.py:56-60](../../../../backend/apps/core/db/risorse_umane_core_repository.py#L56-L60)
- [email_repository.py:153-157](../../../../backend/apps/core/db/email_repository.py#L153-L157), `:343-347`, `:443-447`, `:600-604`, `:745-749`
- [token_repository.py:43-47](../../../../backend/apps/core/db/token_repository.py#L43-L47)
- [parameter_repository.py:176-183](../../../../backend/apps/core/db/parameter_repository.py#L176-L183), `:241-248`, `:312-319`

**Estrazione:** `safe_fetchone_scalar(cursor, error_code="E_DB_EMPTY_RESULT")` in
[core/db/_helpers.py](../../../../backend/apps/core/db/_helpers.py). Sostituisce 11
blocchi con una chiamata. Rischio nullo (pattern isolato in query RETURNING/SELECT).

### A4. `_upsert_override_cte` — UPSERT via CTE in `parameter_repository` — **3 occorrenze** — `interno_core` — ✅ FATTO (2026-06-04)

> Estratto `_upsert_override_cte(parameter_code, scope_col, scope_value, value, *, null_cols)`
> privato in `parameter_repository`; i 3 metodi (`upsert_user`/`emittente`/
> `categoria_cliente_override`) sono wrapper di delega. `scope_col`/`null_cols`
> hardcoded dai chiamanti (no input utente → `# noqa: S608`). ⚠️ preservata la
> divergenza: user/emittente NON filtrano `categoria_cliente_id IS NULL` (scritti
> prima della colonna) → `null_cols` esplicita per fedeltà. 43 test parametri verdi.

Tre metodi (`upsert_user_override`, `upsert_emittente_override`,
`upsert_categoria_cliente_override`) implementano la **stessa** CTE
`WITH target / updated (UPDATE…RETURNING) / inserted (INSERT…WHERE NOT EXISTS…RETURNING) / SELECT UNION ALL`.
Sovrapposizione ~90%, variano solo: nome colonna scope
(`django_user_id`/`emittente_fiscale_id`/`categoria_cliente_id`) e numero di
colonne `IS NULL` nel `WHERE` (3/3/4).

- [parameter_repository.py:141-183](../../../../backend/apps/core/db/parameter_repository.py#L141-L183)
- [parameter_repository.py:206-248](../../../../backend/apps/core/db/parameter_repository.py#L206-L248)
- [parameter_repository.py:277-319](../../../../backend/apps/core/db/parameter_repository.py#L277-L319)

**Estrazione:** helper privato `_upsert_override_cte(scope_col, scope_value, null_cols, insert_col)`
nel modulo stesso; i 3 metodi pubblici delegano. ~70 righe in meno, pattern CTE in
un solo posto.

### A5. `validate_order_params` — validazione order_by/order_dir — **2 (→4) occorrenze** — `interno_core` (cross-dominio) — ✅ FATTO (2026-06-04)

> Promosso `validate_order_params(order_by, order_dir, *, allowed_columns, error_code, function_name)`
> in **nuovo modulo** [core/services/list_helpers.py](../../../../backend/apps/core/services/list_helpers.py).
> Delegano `_validate_order`+`_validate_uom_order` (catalogo) e `_validate_order`+
> `_validate_righe_order` (listini). Rimossi i `_ORDER_DIR_VALIDI` orfani. **Out
> of scope (corretto):** `lookup_service` (5ª occorrenza) usa `order_col` + messaggi
> user-facing divergenti → lasciato locale. Registrato nel catalogo BB.

`_validate_order` identico in catalogo e listini: due `ErrorManager.require` su
whitelist locale + `order_dir ∈ {asc,desc}`. Differenze solo cosmetiche (f-string
vs concat) + `error_code` di dominio. Inoltre **2 varianti gemelle** nello stesso
schema (`_validate_uom_order`, `_validate_righe_order`).

- [catalogo/services/catalogo_service.py:177-199](../../../../backend/apps/catalogo/services/catalogo_service.py#L177-L199) (+ `_validate_uom_order` ~1850)
- [vendite/services/listini_service.py:131-150](../../../../backend/apps/vendite/services/listini_service.py#L131-L150) (+ `_validate_righe_order` ~154)

**Promozione:** `validate_order_params(order_by, order_dir, allowed_columns, error_code, function_name)`
in un nuovo `core/services/list_helpers.py`. ⚠️ **NON** confondere con
`search_validators.validate_order_params` esistente: semantica diversa (ritorna
tuple opzionale, normalizza maiuscole, niente error_code di dominio) → serve un BB
*nuovo*, non riuso del vecchio.

### A6. `extract_string_with_sentinel` — estrazione stringa payload con `_MISSING` — **2 occorrenze** — `bb_mancante_core` — ✅ FATTO (2026-06-04)

> Promosso `PayloadValidator.extract_optional_string(...)` + sentinel condiviso
> `MISSING`/`MissingType` in core. **Scoperta:** il sentinel `_MissingType`/`_MISSING`
> era anch'esso duplicato in entrambi i file (usato da tutta la famiglia di
> extractor) → unificato in core e ri-aliasato nei service (`MISSING as _MISSING`,
> `MissingType as _MissingType`) — i chiamanti fanno `is _MISSING`, quindi serve un
> unico oggetto. catalogo non aveva un `PayloadValidator`: aggiunto `_V`. I due
> `_extract_string` ora delegano. Registrato nel catalogo BB. 180 test verdi.

`_extract_string` identico al 99% in listini e catalogo service: gestisce
`_MISSING` (chiave assente) vs `None` esplicito vs stringa, con `nullable`,
`strip()`, check vuoto. Differisce da `PayloadValidator.optional_string` core (che
ritorna `None` per chiave assente, **senza** sentinel né `nullable`) → **non** già
coperto. Usato attivamente (listini ×4, catalogo ×11).

- [vendite/services/listini_service.py:217-262](../../../../backend/apps/vendite/services/listini_service.py#L217-L262)
- [catalogo/services/catalogo_service.py:253-296](../../../../backend/apps/catalogo/services/catalogo_service.py#L253-L296)

**Promozione:** metodo `PayloadValidator.extract_optional_string(payload, key, *, nullable=False, message=None)`
con sentinel `_MISSING` in
[core/services/payload_helpers.py](../../../../backend/apps/core/services/payload_helpers.py).
Il sentinel è ciò che distingue "campo non fornito" da "campo `None`" → utile per i
PATCH parziali. Mantenere `message` opzionale per override per-chiave.

---

## 🟡 Candidati validi ma con un "ma" — possibile, serve attenzione

### B1. `qp_int_optional_strict` request-aware — **4 occorrenze** — `bb_mancante_core` — ✅ FATTO (2026-06-04)

> Chiuso **senza nuova funzione**: i 4 `_optional_qp_int_strict` (documenti/catalogo/
> config×2) ora usano `qp_int_optional(qp.get(k), k)` (il BB di A1). La semantica
> `""→None` unifica anche l'incoerenza empty-string segnalata nel "ma" sotto.

`_optional_qp_int_strict(request, key)` ~95% identico: estrae da `query_params` →
`qp_int_strict(raw, key, 0)`. Wrapper request-aware del `qp_int_strict` core.

- [documenti/api/views.py:53-57](../../../../backend/apps/documenti/api/views.py#L53-L57)
- [catalogo/api/views.py:78-82](../../../../backend/apps/catalogo/api/views.py#L78-L82)
- [config/api/views_utilities_tipi_ruolo.py:35-39](../../../../backend/apps/config/api/views_utilities_tipi_ruolo.py#L35-L39)
- [config/api/views_tipi_ruolo_tipi_indirizzo.py:31-35](../../../../backend/apps/config/api/views_tipi_ruolo_tipi_indirizzo.py#L31-L35)

> **⚠️ "ma": stringa vuota non uniforme.** I 2 `config` fanno `return None` su
> `raw == ""`; documenti/catalogo lasciano risalire il `ValueError`. **Da decidere
> se è un bug di inconsistenza o feature.** L'estrazione deve esporre il
> comportamento (es. flag `allow_empty_as_none`, default conservativo =
> comportamento documenti/catalogo) oppure standardizzare con fix contestuale.

### B2. `qp_iso_date_optional` — data ISO opzionale da query-param — **3 occorrenze** — `bb_mancante_core` — ✅ FATTO (2026-06-04)

> Promosso `qp_iso_date_optional(raw, name)` in core (firma simmetrica alla
> famiglia, `{name}_invalid` su malformata). Rimossi `_qp_date_optional` (ordini),
> `_qp_iso_date` (contratti), `_optional_qp_iso_date` (catalogo) + import `date` orfani.

Tutte parsano una ISO date opzionale (`None` se assente, `date.fromisoformat`), ma
con **tre firme e tre error-handling diversi**: `views_ordini` solleva `ValueError`
locale, `views_contratti` delega al `parse_iso_date` core (pattern migliore),
catalogo wrappa `optional_iso_date` (pensato per payload JSON, non query-param).

- [vendite/api/views_ordini.py:51-57](../../../../backend/apps/vendite/api/views_ordini.py#L51-L57)
- [vendite/api/views_contratti.py:50-51](../../../../backend/apps/vendite/api/views_contratti.py#L50-L51)
- [catalogo/api/views.py:86-87](../../../../backend/apps/catalogo/api/views.py#L86-L87)

**Promozione:** `qp_iso_date_optional(raw: str | None) -> date | None` in core
(`return parse_iso_date(raw) if raw else None`, delega come views_contratti).

> **⚠️ "ma":** la migrazione di `views_ordini` cambia l'error-handling (da
> `ValueError("{name}_invalid")` locale a delega `parse_iso_date`). Verificare che
> nessun handler dipenda dalla forma del messaggio; se serve, wrapping locale.

### B3. Parsing paginazione ripetuto 6× in `views_tracciamento` — **6 occorrenze** — `interno_core` — ✅ FATTO (2026-06-04)

> Due parti, decisione di Tid (page/page_size vs offset/limit spiegato a chat):
>
> - **Parte B (service):** estratto `validate_pagination(page, page_size, *, error_code, function_name) -> int`
>   in [list_helpers.py](../../../../backend/apps/core/services/list_helpers.py)
>   (page-based, ritorna offset; speculare a `validate_order_params`). `vendite_service`
>   delega; `tracciamento_service` delega **e usa l'offset ritornato**, eliminando i
>   6 ricalcoli manuali `(page-1)*page_size`. Registrato nel catalogo BB.
> - **Parte A (view):** helper **LOCALE** `_parse_page_size(qp, default)` in
>   `views_tracciamento` (cap 200 centralizzato). Niente promozione a core:
>   page/page_size a livello view lo usa solo tracciamento → evita una seconda
>   famiglia di paginazione in core accanto a `parse_list_params`.
>
> 1427 test core+vendite verdi.

Le 6 view (`ApiAuditLog`, `ApiDominiTask`, `ApiTaskRegistry`,
`ApiTaskImplementations`, `ApiJobRuns`, `ApiJobSummary`) ripetono
`page=qp_int(...,1)` + `page_size=min(qp_int(...,SIZE),200)` nello **stesso file**.

- [core/api/views_tracciamento.py:107-108](../../../../backend/apps/core/api/views_tracciamento.py#L107-L108), `:148-149`, `:198-199`, `:252-253`, `:320-321`, `:358-359`

> **⚠️ "ma":** il default size **varia** (50 vs 100: `ApiTaskRegistry`/
> `ApiTaskImplementations` usano 100, le altre 50). Il BB core esistente
> `parse_list_params` è **offset-based**, non `page/page_size` → serve un helper
> `page`-based nuovo (es. `parse_pagination_page_based(qp, default_size, max_size=200)`),
> oppure un helper locale al file. Da decidere se promuovere a core o tenere locale.

### B4. `INSERT … RETURNING id` ripetuto 8× in `core/db` — **8 occorrenze** — `interno_core` — *parcheggiato*

Boilerplate `INSERT…RETURNING` + `fetchone` + `assert` + `return` in 8 punti
(config_crud, email ×5, token, partitioned_note). **Ma** la verifica raccomanda di
**NON estrarre ora**: solo il guscio 4-righe è comune, mentre costruzione
colonne/params, preprocessing (`crypto.encrypt`, `json.dumps`) e scope RETURNING
(id vs record completo) divergono. Basso ROI, alto rischio di nascondere logica.

- config_crud_repository:51-60; email_repository:121-157/315-347/410-447/568-604/724-749; token_repository:25-47; partitioned_note_repository:281-300

**Decisione:** *wait-and-accumulate* — estrarre un BB specifico solo quando 3+
INSERT condivideranno schema/preprocessing/RETURNING. (Nota: il sotto-pattern
`fetchone+assert+return row[0]` è invece **A3**, quello sì da estrarre.)

---

## 🔴 Casi confermati ma da NON estrarre (falsa duplicazione)

La verifica avversariale ha aperto i file e confermato la divergenza: forma simile,
problemi diversi. Unificarli peggiorerebbe la leggibilità.

- **`dynamic_update` in `email_repository`** (update_account / update_template /
  update_outbox). Stesso *template strutturale* ma **vincoli ortogonali
  inviolabili**: account richiede `crypto.encrypt` in app-layer, template richiede
  cast `%s::jsonb` colonna-specifico, outbox aggiunge guardia `AND stato='DRAFT'`.
  Forzarli su `_helpers.dynamic_update` (usato pulito da geo_repository) imporrebbe
  callback crypto (espone secret nell'interfaccia), whitelist JSONB e WHERE extra
  (rompe l'invariante `pk=id` di 7+ callsite). **Convergenza di forma, non logica.**
- **JSONB parse in `email_repository`** (`_parse_jsonb_field` ×6). 3 occorrenze
  **mutano in-place** un dict, 3 **ritornano** il valore: semantica diversa,
  refactor retroattivo cambierebbe firme e cascata sui caller. Tecnico
  (adattamento psycopg), non business logic. *(Eventuale: esporre `parse_jsonb_value`
  pubblico in `_helpers.py` solo per NUOVI repository, on-demand.)*

  > ⚠️ **Aggiornamento 2026-10-28** (brief-modello-documento-vendita §15.17.3): `_parse_jsonb_field` è ritirato. I lettori a dizionari di `apps/core/db/_helpers.py` decodificano da soli le colonne jsonb, dal tipo che il cursore dichiara; le letture per posizione usano `jsonb_out`.

- **Search/pagination in `views_lookup` ×3** — vedi D2: non è duplicazione di
  logica ma debito di *mancata adozione* di un BB esistente.

---

## ⚠️ Scoperte collaterali (debiti: BB ignorati, codice morto, asimmetrie)

### D1. Asimmetria core: manca `qp_bool_optional_strict` (il caso seme) — ✅ FATTO (2026-06-04)

> Risolto rendendo **`qp_bool_optional` stesso strict** (no suffisso `_strict`
> separato): è l'opzionale, simmetrico a `qp_int_optional`. `_optional_qp_bool_strict`
> di vendite/views_listini rimosso → `qp_bool_optional(qp.get("attivo"), "attivo")`.

[vendite/api/views_listini.py:51-60](../../../../backend/apps/vendite/api/views_listini.py#L51-L60)
ha `_optional_qp_bool_strict` (bool opzionale che **solleva `ValueError`** sui
valori non riconosciuti, ≠ `qp_bool_optional` core che li tratta come permissivi).
**Occorrenza singola** → sotto soglia regola-del-2 in senso stretto, già dedupata
localmente (2 chiamanti, righe 222/434). **Ma** rivela un'**asimmetria di
catalogo**: core ha `qp_int_strict` e (con A1) avrà `qp_int_optional`, ma non
l'equivalente bool. Il pattern "optional + strict" emerge anche su int
(`_qp_int_optional` di promo_articoli → A1) → conferma il bisogno di una **famiglia
unificata**.

**Proposta:** promuovere `qp_bool_optional_strict(raw, name) -> bool | None` al core
per simmetria, far delegare `views_listini`. Priorità bassa (1 sito reale), ma
chiude la famiglia. **Già descritto in [regola-del-2-anagrafiche.md](regola-del-2-anagrafiche.md)
come promemoria** — qui ratificato nel contesto core.

### D2. 3 view di `views_lookup` ignorano il BB `parse_list_params` — ✅ FATTO (2026-06-04)

> Rimosso il reinvento inline `(qp.get("search") or "").strip() or None` (= `qp_str`).
> **ApiComuniSearch** (search+limit+offset) → `parse_list_params(qp, default_limit=20, max_limit=100)`
> (calza pieno). **Stradario** + **StradarioGenerale** (param extra `comune_id`/
> `toponomastica_id`, **niente offset**) → `qp_str(qp.get("search"))` (il BB
> reinventato; `parse_list_params` non calza per via dei param extra + assenza
> offset). Response shape invariata (no breaking FE). Comportamento preservato
> (qp_str ≡ vecchia normalizzazione). 128 test lookup/catalogo/listini verdi.

[core/api/views_lookup.py:298-308](../../../../backend/apps/core/api/views_lookup.py#L298-L308),
`:334-343`, `:368-377` fanno parsing manuale di `search`/`limit`/`offset` mentre il
BB `parse_list_params` ([payload_validators.py:66-86](../../../../backend/apps/core/api/payload_validators.py#L66-L86))
è **già vivo in 20+ view** di altri domini. Non è duplicazione di logica (le 3 view
divergono: offset solo nella prima, response shape diverse, default 20/30/30) ma un
**debito di mancata adozione**.

**Azione:** refactor delle 3 view per usare `parse_list_params` + `paginated_envelope`,
allineandole alla convenzione API globale. Rischio basso, valore di coerenza alto.

### D3. Codice morto: `_validate_pagination` mai chiamato (catalogo + listini) — ✅ FATTO (2026-06-04)

> Rimossi i 2 `_validate_pagination` **morti** (catalogo_service + listini_service:
> definiti, zero chiamanti — le liste usano `limit/offset` via `parse_list_params`).
> Lasciati gli **attivi** `vendite_service._validate_pagination` (2 caller) e
> `tracciamento_service._validate_pagination` (6 caller, firma `-> None` diversa):
> non sono codice morto, e con firme/semantiche divergenti l'unificazione resta
> opzionale (vedi B3, paginazione `page`-based).

Risoluzione del verdetto in conflitto. La validazione `page/page_size` esiste in 4
service ma:

- **codice morto** (definito, mai invocato): [catalogo/services/catalogo_service.py:141-160](../../../../backend/apps/catalogo/services/catalogo_service.py#L141-L160)
  e [vendite/services/listini_service.py:108-127](../../../../backend/apps/vendite/services/listini_service.py#L108-L127)
  — le rispettive liste usano `limit/offset` (`parse_list_params`), non `page`.
- **attivi ma divergenti**: [core/services/tracciamento_service.py:19-38](../../../../backend/apps/core/services/tracciamento_service.py#L19-L38)
  (ritorna `None`, offset calcolato dopo nel caller) e
  [vendite/services/vendite_service.py:24-43](../../../../backend/apps/vendite/services/vendite_service.py#L24-L43)
  (ritorna `int` offset).

**Azione:** (1) **rimuovere** i 2 metodi morti (PR "codice morto" dedicato); (2) i 2
attivi hanno firme diverse e solo 2 occorrenze → estrazione **opzionale/debole**,
valutabile solo se si vuole unificare `page`-based in core insieme a B3 (stesso
tema paginazione). Non urgente.

### D4. `_parse_meta_json` reinventa `optional_meta` core + bug commesse → vedi **X1**

Già trattato in cima come scoperta critica (il bug 500 di commesse). Resta qui come
debito di **BB ignorato**: sia listini sia commesse ricopiano
`PayloadValidator.optional_meta` invece di usarlo.

---

## 📐 Nota di design — il "layer wrapper" dei query-param (A1/A2/A3/B1/B2/D1)

La maggioranza dei candidati `bb_mancante_core` appartiene a **un'unica famiglia**:
i parser di query-param. Emergono **due livelli** che oggi i domini reinventano:

1. **Livello puro** `(raw: str | None, name: str)` — già in core
   (`qp_int`, `qp_int_strict`, `qp_bool`, `qp_bool_optional`). Mancano:
   `qp_int_optional` (A1), `qp_iso_date_optional` (B2), `qp_bool_optional_strict` (D1).
2. **Livello wrapper request-aware** `(request: Request, key: str)` — **assente in
   core**, reinventato come `_optional_qp_*` privati in catalogo/documenti/config
   (A2, B1).

### ✅ Decisione di design (Tid, 2026-06-04) — eseguita

- **Firma:** **value-transformer `(raw, name)`**, NON un layer wrapper `(request,
  key)`. Un solo modello mentale per tutta la famiglia `qp_*`; niente foot-gun da
  firme miste (`qp.get(k)` passato dove serve `qp`). I domini chiamano
  `f(qp.get(k), k)`. Il livello wrapper richiesto in origine **non viene
  introdotto**: completare il livello puro è sufficiente.
- **Posizione:** stesso `payload_validators.py` (niente modulo nuovo).
- **Stringa vuota `""`:** → **`None`** (vuoto = filtro assente), simmetrico per
  int e bool. Allineato all'intento della docstring del test bool.
- **Bool garbage:** → **400** (`ValueError(f"{name}_invalid")` → `E_VALIDATION_INPUT`
  via `ApiExceptionMiddleware`). **`qp_bool_optional` diventa STRICT** (era
  permissivo): chiude l'incoerenza cross-dominio (`?attivo=banana` dava False in
  alcuni domini, True in altri). Niente coppia permissivo/strict.

**Eseguito (2026-06-04):** completata la famiglia in core (`qp_bool_optional`
strict, `qp_iso_date_optional`); rimossi 8 `_optional_qp_*`/`_qp_*` privati;
migrati ~30 call-site su ~12 file a `qp_*(qp.get(k), k)`; rimossi import orfani
(`optional_iso_date`, `qp_bool`/`qp_int_strict` dove inutilizzati, `date`);
aggiornati i test stale del contratto bool (vuoto→None) + nuovo test garbage→400.
**2158 test verdi** (core+vendite+anagrafiche+catalogo+documenti+config).

---

## Come procedere (proposta)

Per ogni candidato vale il protocollo della regola del 2
(`feedback_regola_del_2_estrai_bb`): **dichiarare a chat il disegno del BB e
attendere l'OK di Tid** prima di scrivere codice astratto. Inoltre le DDL/azioni DB
non sono toccate qui (solo Python). Ordine suggerito per gravità/valore:

1. ✅ **X1** (bug `commesse` meta → 500) + migrazione a `optional_meta` — **FATTO
   (2026-06-04)**, +1 test di regressione, 122 test verdi.
2. ✅ **A3** (`fetchone_scalar`, 11+4 siti) e ✅ **A1** (`qp_int_optional`, 5 siti) —
   **FATTI (2026-06-04)**, registrati nel catalogo BB. 579 core + 1243
   vendite/anagrafiche verdi.
3. ✅ **A4** (CTE upsert), **A5** (`validate_order_params`), **A6**
   (`extract_optional_string`) — **FATTI (2026-06-04)**, 2158 test verdi.
   (`extract_string_with_sentinel`) — netti.
4. ✅ **Decisione di design + estrazione famiglia query-param** (A2/B1/B2/D1) —
   **FATTO (2026-06-04)**: value-transformer `(raw,name)`, `""→None`, bool strict,
   nessun layer wrapper. 2158 test verdi.
5. ✅ **B3** (paginazione tracciamento) — **FATTO (2026-06-04)**: `validate_pagination`
   in core (service, Parte B) + helper locale `_parse_page_size` (view, Parte A).
6. ✅ **D2** (adozione `parse_list_params`/`qp_str` in views_lookup) e ✅ **D3**
   (rimozione codice morto catalogo+listini) — **FATTI (2026-06-04)**.
7. 🔴 **email_repository** (`dynamic_update`, JSONB) e 🟡 **B4** (INSERT RETURNING) —
   **non** toccare / parcheggiati.

> Stato: **nessuna estrazione eseguita.** Documento di sola mappatura, in attesa
> dell'OK di Tid sui singoli pezzi.
