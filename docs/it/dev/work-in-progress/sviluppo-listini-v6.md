# Sviluppo Listini — Pricing ZeroERP (WIP v6)

> Stato: **RACCOLTA DEBITI TECNICI — addendum a v5.**
>
> Creato: 14 aprile 2026
>
> Questo documento raccoglie interventi di ottimizzazione e refactor
> trasversali emersi durante lo sviluppo di v5 e rimandati a una fase
> successiva per non gonfiare lo scope della PR corrente. Ogni voce e`
> un **debito tecnico identificato ma non bloccante** per la chiusura di
> v5 end-to-end.
>
> Riferimenti:
> * [sviluppo-listini-v5.md](sviluppo-listini-v5.md) — documento padre e
>   piano operativo v5 (Fase 0 → Fase 4)

---

## 1) Scope di questo documento

v5 introduce il nuovo modello di pricing (categoria cliente + contratto +
promo, resolver a 3 stadi). Durante l'implementazione emergono pattern e
ottimizzazioni trasversali che **non** appartengono al solo dominio listini
ma alla catena di building block frontend/backend dell'intero progetto.

Tenerli fuori dal WIP principale evita che v5 si trasformi in un mega-PR
con impatto su aree non correlate. Li indicizziamo qui come "v6" (ordine
cronologico), pronti per essere programmati come sprint tecnici dopo
la chiusura di v5.

---

## 2) Debiti tecnici identificati

### 2.1 Frontend — `useGlobalLookup` modulo-level

**Origine**: Fase 0 Frontend v4 (review `ListiniSearchTable.vue`), categorizzato
come **M3** nel report di review del 14 aprile 2026.

**Problema**:

Il composable `useLookup(fetchFn, { immediate: true })` caricato nelle
SearchTable e` **per-istanza**. Ogni mount del componente (es. riapertura
tab, navigazione avanti/indietro, split-view) rifa` la fetch lookup, anche
se la tabella config non e` cambiata.

Esempio concreto su `ListiniSearchTable`:

```js
const tipologiaLookup = useLookup(
  () => lookupCodici('config.listini_tipologie'),
  { immediate: true }
)
```

Ogni mount del component → 1 chiamata HTTP. Con content tabs multi-entita`
e split-view l'operatore puo` facilmente generare 3-5 fetch inutili della
stessa tabella in un minuto.

**Pattern ripetibile**: lo stesso caso esiste (o esistera` presto) su:

- SearchTable clienti → `config.stati_cliente`
- SearchTable fornitori → `config.stati_fornitore`
- SearchTable pratiche → `config.stati_pratiche`, `config.priorita_pratiche`
- SearchTable preventivi → `config.stati_doc_preventivi`
- SearchTable DDT/ordini → stati documenti fiscali
- Drawer categoria cliente → `anagrafiche.categorie_clienti` (v5)
- Drawer matrice → `anagrafiche.categorie_clienti_listini` (v5)
- Drawer promo → varie lookup articoli/uom (v5)

**Soluzione proposta**: `useGlobalLookup` factory modulo-level in
`frontend/src/core/composables/useGlobalLookup.js`.

```js
// Scopo: Cache di lookup per-chiave, condivisa fra tutte le istanze Vue
//        del processo. Evita fetch duplicate quando piu' SearchTable o
//        Drawer chiamano la stessa tabella codici.
//
// Uso:
//   const { items, loading, load } = useGlobalLookup(
//     'config.listini_tipologie',
//     () => lookupCodici('config.listini_tipologie')
//   )
//
// Politica cache:
//   - cache key = primo parametro (stringa)
//   - primo consumer fa la fetch, i successivi riusano gli items in cache
//   - reload() forza un re-fetch e aggiorna tutti i consumer reattivi
//   - invalidate(key) permette refresh esterno (es. dopo CRUD admin)
//   - TTL opzionale configurabile per-chiave (default: infinito,
//     cache resettata solo a page reload o logout)
```

**Caratteristiche chiave**:

- `items` restituito come `computed` reactive che punta al cache store
- load idempotente: se un altro consumer ha avviato la fetch, attendere
  la promise condivisa (no thundering herd)
- `invalidate(key)` chiamabile dopo mutation CRUD admin della tabella
  sorgente — utile quando l'admin aggiunge/modifica una categoria e la
  lista listini nella stessa sessione deve rinfrescare la dropdown
- integrazione con `useTabEvents` per invalidazione cross-tab dopo
  modifica della tabella sorgente

**Estensione coerente con memoria esistente**:
`feedback_css_centralizzazione.md`, `feedback_componente_riusabile_watch.md`
gia` indicano la direzione di riuso cross-dominio dei building block core.

**Impatto**:

- File nuovo: `frontend/src/core/composables/useGlobalLookup.js`
- Test: `frontend/src/core/composables/__tests__/useGlobalLookup.spec.js`
  (gia` pattern esistente in progetto?)
- Migrazione SearchTable esistenti a `useGlobalLookup` dove applicabile —
  incrementale, nessun breaking change
- Doc: aggiornare
  [catalogo-building-block-frontend.md](/dev/frontend/catalogo-building-block-frontend)
  con la nuova voce

**Priorita`**: Media. v5 Fase 3 (Frontend) genera almeno 3 nuove SearchTable
che beneficerebbero del pattern. Meglio farla prima di Fase 3, oppure
farla come primo sprint v6 subito dopo la chiusura di v5.

---

### 2.2 Backend — `apps/core/services/payload_helpers.py`

**Origine**: Fase 2 Backend v5 F2-BE-01 (review `categorie_clienti_service.py`),
categorizzato come **F1** nel report di review del 14 aprile 2026.

**Problema**:

I service admin CRUD ripetono gli stessi helper di validazione payload in
ogni file. Alla 4ª copia il debito diventa esplicito:

| Service | File |
|---|---|
| `UtilitiesTipiRuoloService` | `apps/config/services/utilities_tipi_ruolo_service.py` |
| `TipiRuoloTipiIndirizzoService` | `apps/config/services/tipi_ruolo_tipi_indirizzo_service.py` |
| `ListiniService` | `apps/vendite/services/listini_service.py` |
| `CategorieClientiService` | `apps/anagrafiche/services/categorie_clienti_service.py` |

Gli helper duplicati (con piccole varianti nei codici errore):

- `_validate_keys(payload, allowed)`
- `_guard_id(value, field)`
- `_extract_required_string(payload, key, max_len)`
- `_extract_required_int(payload, key)` o `_require_positive_int`
- `_extract_optional_bool(payload, key)`
- `_extract_optional_smallint(payload, key, min, max)`
- `_extract_optional_meta(payload)` / `_parse_meta_json`
- `_raise_integrity_error(exc, unique_map, fk_map, fallback_code)`

**Soluzione proposta**: estrazione in `apps/core/services/payload_helpers.py`.

```python
# Scopo: Helper condivisi per la validazione di payload nei service admin.
#        Usati da CRUD generici su tabelle config/anagrafiche con pattern
#        codice/descrizione/flag.

class PayloadValidator:
    """Validator parametrizzato per error_code applicativo del dominio."""

    def __init__(self, *, validation_code: str) -> None:
        self._code = validation_code

    def validate_allowed_keys(self, payload, *, allowed: frozenset[str]) -> None: ...
    def guard_positive_int(self, value, *, field: str) -> None: ...
    def extract_required_string(self, payload, key, *, max_len: int) -> str: ...
    def extract_required_positive_int(self, payload, key) -> int: ...
    def extract_optional_bool(self, payload, key) -> bool | None: ...
    def extract_optional_smallint(self, payload, key, *, min_val: int = 0,
                                   max_val: int = 32767) -> int | None: ...
    def extract_optional_meta(self, payload, key: str = "meta") -> dict | None: ...


def map_integrity_error(
    exc: IntegrityError,
    *,
    unique_constraints: dict[str, tuple[str, str]],
    fk_constraints: dict[str, tuple[str, str]],
    fallback_code: str,
    context: dict,
) -> NoReturn:
    """Traduce IntegrityError in ServiceError con codici parlanti."""
    ...
```

**Caratteristiche chiave**:

- Parametrizzazione `validation_code` per dominio (`E_CONFIG_VALIDATION`,
  `E_ANAG_VALIDAZIONE`, `E_VENDITE_VALIDATION`, ecc.)
- `map_integrity_error` con dizionari `unique_constraints` / `fk_constraints`
  che mappano nome vincolo DB → `(error_code, message)`: ogni service passa
  la sua mappa
- Tipizzazione stringente (TypeError su bool mascherato da int, float su int,
  stringa "true" non accettata per bool stretto)
- Costanti centralizzate: `SMALLINT_MIN = 0`, `SMALLINT_MAX = 32767`,
  `INTEGER_MAX = 2_147_483_647`

**Impatto**:

- File nuovo: `apps/core/services/payload_helpers.py`
- Test: `apps/core/tests/services/test_payload_helpers.py`
- Refactor incrementale dei 4 service: ogni service sostituisce i metodi
  privati con chiamate al helper. Commit separato per service per
  permettere rollback mirato in caso di regressione
- Doc: aggiornare
  [catalogo-building-block-backend.md](/dev/backend/catalogo-building-block-backend)
  con la nuova voce

**Priorita`**: Media-alta. La duplicazione cresce linearmente con ogni
nuovo service CRUD admin. Fase 2 v5 genera altri 4 service nuovi
(matrice, promo, contratti estesi, snapshot commessa) che peggiorano la
situazione. Meglio farlo **prima** della conclusione di Fase 2, come
sprint inline.

---

## 3) Tracking

| ID    | Descrizione                                                      | Area     | Priorita`    | Stato    |
| ----- | ---------------------------------------------------------------- | -------- | ------------ | -------- |
| V6-F1 | `useGlobalLookup` modulo-level per SearchTable/Drawer            | Frontend | Media        | **Chiuso** 2026-04-14 |
| V6-B1 | `apps/core/services/payload_helpers.py` — validazione condivisa | Backend  | Media-alta   | **Chiuso** 2026-04-14 |
| V6-B2 | Estensione `PayloadValidator` con `log_to_db`/`function_name` + migrazione listini_service | Backend | Bassa | **Chiuso** 2026-04-15 |

**Stato v6**: tutti i debiti tecnici rilevati durante v5 sono stati chiusi.
v6 e' completato end-to-end.

Nuove voci possono essere aggiunte a questo documento man mano che emergono
durante v5. Al completamento di ogni intervento, spostare la voce in una
sezione "Chiuso" con riferimento al commit / PR.

---

## 3.1) Chiusi

### V6-F1 — `useGlobalLookup` (2026-04-14)

**Implementato**: sessione 2026-04-14.

File creato:

* [frontend/src/core/composables/useGlobalLookup.js](../../../../frontend/src/core/composables/useGlobalLookup.js)
  — cache modulo-level per-chiave. API: `useGlobalLookup(key, fetchFn, { immediate })`
  ritorna `{ items, loading, loaded, load, reload }` (items/loading/loaded
  sono `computed` sul cache store condiviso). Export modulo:
  `invalidateLookup(key)` per refresh mirato, `invalidateAllLookups()`
  per reset logout. Dedup thundering herd via promise in volo condivisa.

Consumer migrati (pilota):

* [LookupSelect.vue](../../../../frontend/src/core/components/LookupSelect.vue)
  — chiave = `props.rel`. Impatto massimo: tutte le istanze con lo stesso
  `rel` (es. `config.iva`, `config.conti_contabili`) condividono la fetch.
* [ListiniSearchTable.vue](../../../../frontend/src/vendite/components/ListiniSearchTable.vue)
  — chiave `config.listini_tipologie`.
* [MatriceIndirizziDrawer.vue](../../../../frontend/src/anagrafiche/components/MatriceIndirizziDrawer.vue)
  e [MatriceIndirizziSearchTable.vue](../../../../frontend/src/anagrafiche/components/MatriceIndirizziSearchTable.vue)
  — chiave `config.tipi_indirizzi` condivisa tra drawer e tabella: aprire
  il drawer dalla tabella non rifa la fetch.

Lasciati su `useLookup` (migrazione incrementale, non breaking):
SoggettoDrawer/ComuneDrawer/ProvinceDrawer/RegioniDrawer (lookup geografiche),
OperatoreDrawer/OperatoriListView/PermessiRiepilogoView (lookup
amministrazione), ClienteDrawer (utility per ruolo con parametro).
Candidati naturali per adozione opportunistica quando si toccano quei file.

**Test**: vite build OK (nessuna regressione). Frontend non ha vitest
configurato: il composable e' testato operativamente via build + smoke
manuale. Se in futuro si aggiungesse vitest al progetto, `_internalCache`
e' esposto come API privata per facilitare test e reset stato.

Catalogo aggiornato:
[catalogo-building-block-frontend.md](../frontend/catalogo-building-block-frontend.md)
— voce `useGlobalLookup / invalidateLookup / invalidateAllLookups`
aggiunta e `useLookup` annotata con indicazione quando preferire l'una
o l'altra.

### V6-B1 — `apps/core/services/payload_helpers.py` (2026-04-14)

**Implementato**: sessione 2026-04-14 sul branch `dev/backend-tid`.

File creati:

* [apps/core/services/payload_helpers.py](../../../../backend/apps/core/services/payload_helpers.py) —
  `PayloadValidator(validation_code)` con metodi `validate_allowed_keys`,
  `guard_positive_int`, `require_string`, `require_positive_int`,
  `optional_positive_int`, `optional_smallint`, `optional_bool`,
  `optional_meta`. Helper funzionale `map_integrity_error(...)` con mappe
  `unique_constraints` / `fk_constraints` per traduzione vincoli DB in
  `ServiceError`. Costanti `SMALLINT_MIN/MAX`, `SMALLINT_UNSIGNED_MIN`,
  `INTEGER_MAX`.
* [apps/core/tests/services/test_payload_helpers.py](../../../../backend/apps/core/tests/services/test_payload_helpers.py) —
  44 unit test (nessun DB).

Service migrati:

* [apps/anagrafiche/services/categorie_clienti_service.py](../../../../backend/apps/anagrafiche/services/categorie_clienti_service.py)
  (`E_ANAG_VALIDAZIONE`).
* [apps/config/services/utilities_tipi_ruolo_service.py](../../../../backend/apps/config/services/utilities_tipi_ruolo_service.py)
  (`E_CONFIG_VALIDATION` + mapping UNIQUE/FK).
* [apps/config/services/tipi_ruolo_tipi_indirizzo_service.py](../../../../backend/apps/config/services/tipi_ruolo_tipi_indirizzo_service.py)
  (`E_CONFIG_VALIDATION` + mapping UNIQUE/FK).

Catalogo aggiornato:
[catalogo-building-block-backend.md](../backend/catalogo-building-block-backend.md)
— voci `PayloadValidator` e `map_integrity_error` nella sezione Services.

**Deferred**: migrazione di
[apps/vendite/services/listini_service.py](../../../../backend/apps/vendite/services/listini_service.py)
rinviata. Gli helper di listini sono a livello modulo con firma diversa
(`function_name` + `log_to_db` per-chiamata, necessari per orchestrazione
pipeline vendite). Migrazione richiederebbe un overload di
`PayloadValidator` che accetti questi parametri per-chiamata. Creata nuova
voce **V6-B2** (sotto).

**Test**: `./manage-test.sh -v 1` → 1336/1336 OK (dai 1292 pre-sprint,
+44 nuovi test, zero regressioni).

### V6-B2 — migrazione `listini_service.py` a `PayloadValidator` (2026-04-15)

**Implementato**: sessione 2026-04-15.

**Estensione `PayloadValidator`** (retrocompatibile):

* Costruttore accetta `log_to_db: bool = False` e `function_name: str | None = None`
  come default di istanza, propagati a `ErrorManager.require`/`raise_error`.
* Ogni metodo accetta override per-chiamata di `log_to_db` e `function_name`.
* `require_positive_int` / `require_string` accettano `message` per-chiamata
  per permettere messaggi di dominio ("Parametri listino non validi.").
* `require_string` ora accetta `max_len: int | None = None`: quando None
  salta il controllo lunghezza (listini delega il bound alla colonna DB).
* I 3 service gia' migrati non cambiano comportamento: usano i default.

**Service migrato**:

* [apps/vendite/services/listini_service.py](../../../../backend/apps/vendite/services/listini_service.py)
  — validator modulo-level `_V = PayloadValidator("E_VENDITE_VALIDATION",
  log_to_db=True)`. Le funzioni `_validate_payload_keys`, `_require_string`,
  `_require_positive_int` sono ora thin wrapper che delegano al validator
  preservando la firma storica: i ~15 call site del service non cambiano.
  Rimossi ~120 LOC di logica duplicata.

Non migrati (helper genuinamente specifici di listini, restano a livello
modulo): `_extract_nullable_int`, `_extract_string`, `_extract_decimal`,
`_extract_payload_date`, `_extract_payload_uuid`, `_extract_enum_string`.
Usano il sentinel `_MISSING` per distinguere "chiave assente" da
"chiave=None" nei PATCH, pattern non presente nei CRUD admin. La
duplicazione residua e' limitata e non cresce: i prossimi service v5
useranno direttamente `PayloadValidator`.

**Test**: 5 nuovi test in
[test_payload_helpers.py](../../../../backend/apps/core/tests/services/test_payload_helpers.py)
coprono `log_to_db`, `function_name`, override per-chiamata, `message`
custom, `max_len=None`. Suite completa **1341/1341** OK (dai 1336 post-V6-B1,
zero regressioni).

Catalogo backend gia' aggiornato in V6-B1 (estensione retrocompatibile,
stessa voce `PayloadValidator`).

---

## 4) Relazione con v5

v6 **non** modifica il modello dati ne` la logica di pricing di v5. E` puro
consolidamento dei pattern di riuso interni al progetto. v5 e v6 possono
procedere in parallelo dopo la chiusura della Fase 1 DB di v5, con v6 che
interviene su building block gia` stabilizzati.

---

*Sviluppo Listini — ZeroERP (14 aprile 2026, WIP v6 — debiti tecnici trasversali)*
