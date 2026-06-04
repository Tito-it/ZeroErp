# Piano di governo qualita` backend Django

Questo documento sostituisce il vecchio piano di avvio "settimana 1-4".
Le fondazioni Django sono ormai operative; il piano serve quindi a governare
coerenza, debito tecnico e crescita controllata del backend.

## Fonte di verita`

Per sviluppare o modificare API Django seguire prima questi documenti:

- [`docs/it/dev/api.md`](../api.md): regole vincolanti per URL, layer, base view,
  error envelope, idempotenza, permessi e test API.
- [`docs/it/dev/backend/catalogo-building-block-backend.md`](catalogo-building-block-backend.md):
  inventario vivo dei building block disponibili in `apps/core` e nei domini.
- [`.codex/AGENTS.md`](../../../../.codex/AGENTS.md): regole operative per agenti,
  naming, commenti, test, DB-first e workflow di sicurezza.

Questo piano non duplica quelle regole: le usa come baseline e traccia cosa
controllare nel tempo.

## Stato attuale

### Fondazioni consolidate

- Architettura standard `api -> service -> repository -> PostgreSQL`.
- API esplicite con `APIView` dominio/admin/portale/shop, senza `ModelViewSet`
  o router DRF automatici.
- Base view centralizzate: `DomainAPIView`, `AdminAPIView`, `PortaleAPIView`,
  `ShopAPIView`.
- Error handling centralizzato con `ServiceError`, `ErrorManager`,
  `ErrorTranslator`, `error_policies` e middleware API.
- Helper API core per POST/PATCH JSON, parsing payload/query param, envelope,
  paginazione, ricerca, throttling e idempotenza.
- Test organizzati per app in `tests/api/`, `tests/services/` e, dove serve,
  `tests/db/` o `tests/middleware/`.

### Implicazione pratica

Il piano non deve piu` dire "consolidare apps/core" o "confermare il pattern".
Queste decisioni sono gia` prese. Da ora il lavoro e`:

- usare i building block esistenti prima di crearne nuovi;
- ridurre drift tra documentazione, codice e test;
- individuare endpoint legacy non conformi;
- mantenere chiaro il confine DB-first: invarianti e coerenza nel DB,
  orchestrazione e policy applicative in Django.

## Checklist per nuova API dominio

Prima di implementare una nuova API:

- Verificare se esiste gia` un building block nel catalogo backend.
- Stabilire se l'endpoint e` CRUD controllato o azione di dominio atomica.
- Applicare la grammatica URL di `api.md`: niente verbi nel path CRUD, verbo
  ammesso solo come ultimo segmento per azioni non-CRUD.
- Usare il layer corretto:
  - view: parsing, validazione input, permessi, envelope;
  - service: orchestrazione, transazione, policy applicativa;
  - repository: SQL/raw cursor/chiamate a funzioni PostgreSQL;
  - DB: vincoli, invarianti, trigger, funzioni set-based.
- Scegliere la base view corretta:
  - `DomainAPIView` per domini operativi;
  - `AdminAPIView` per amministrazione software;
  - `PortaleAPIView` per portale clienti/fornitori;
  - `ShopAPIView` per negozio online.
- Dichiarare gli attributi necessari:
  - `area_funzionale` su `DomainAPIView`;
  - `model_permission` quando serve permesso oggetto;
  - `post_permission` per azioni di processo;
  - `is_search_endpoint = True` per endpoint di ricerca;
  - `skip_area_check = True` solo per endpoint cross-dominio motivati.
- Per POST JSON usare `handle_post_json(...)`.
- Per PATCH di dettaglio usare `handle_detail_patch(...)` quando il caso rientra
  nel pattern standard.
- Per operazioni write ritentabili o sensibili valutare
  `require_idempotency_key=True`.
- Per lookup distinguere:
  - lookup generico `core/lookup/codici` per tabelle standard;
  - lookup dedicato solo con JOIN/campi extra;
  - lookup cross-dominio con endpoint separato e `skip_area_check=True` solo se
    il dato e` realmente adatto alla selezione condivisa.
- Registrare codici errore in `error_policies` quando devono produrre status,
  messaggio utente o azione UI specifica.
- Decorare i metodi HTTP pubblici con `@extend_schema`.
- Aggiungere test:
  - API contract test per status e payload;
  - service unit test con DB mockato quando possibile;
  - test repository solo dove il comportamento SQL applicativo non e` gia`
    coperto da pgTAP o da funzioni DB.

## Debito residuo da governare

### Endpoint legacy

Controllare periodicamente che le API esistenti rispettino:

- base view moderne, senza pattern dual-class;
- `handle_post_json`/`handle_detail_patch` dove applicabile;
- nessun `try/except Exception` generico nelle view dominio;
- `extend_schema` sui metodi HTTP esposti;
- `is_search_endpoint` su search/list pesanti;
- permessi area/oggetto/azione dichiarati nel punto giusto.

### SQL -> Django

La migrazione di logica SQL verso Django non e` un obiettivo automatico.
Ogni funzione va classificata solo quando c'e` una ragione concreta:

| Stato | Criterio |
| --- | --- |
| `DB-only` | Invarianti, coerenza dati, trigger, controlli set-based, funzioni chiamate da piu` canali |
| `Hybrid` | Regola nel DB + orchestrazione, policy o UX workflow in Django |
| `Migrated` | Logica applicativa spostata in Django perche' cambia spesso o richiede composizione con servizi |

Regola guida: non duplicare in Django vincoli gia` garantiti dal DB; al massimo
aggiungere pre-validazioni per errori piu` parlanti, mantenendo il DB come difesa
finale.

### Typing

Il typing e` progressivo e va applicato dove riduce rischio reale:

- `TypedDict` per righe repository e payload normalizzati;
- return type espliciti nei service pubblici;
- `assert` dopo `ErrorManager.require(... is not None ...)`;
- guard o assert dopo `cursor.fetchone()` prima di usare `row[...]`;
- riduzione mirata di `Any` nei moduli core e nei domini critici.

### Osservabilita`

Mantenere coerente la diagnostica applicativa:

- codici errore classificati e non generici;
- logging con contesto utile (`code`, `area`, funzione/processo, `tx_id` quando
  disponibile);
- endpoint diagnostici core sempre coperti da test;
- idempotency e retry headers documentati quando usati.

### Workflow sviluppatore

La documentazione operativa deve restare allineata agli strumenti reali:

- build docs con `python scripts/build_docs_zensical.py`;
- test Django con `backend/manage-test.sh` o comando equivalente documentato;
- nessun riferimento a `mkdocs build` diretto come comando primario;
- template e checklist aggiornati quando nasce un nuovo building block.

## KPI mensili

Misure utili per capire se il backend sta restando governabile:

- percentuale endpoint conformi a `api.md`;
- numero endpoint legacy da refactor;
- numero codici errore non classificati o troppo generici;
- copertura test su `apps/core` e domini critici;
- warning OpenAPI/drf-spectacular in CI;
- numero helper duplicati estratti in building block dopo "regola del 2";
- tempo medio per aggiungere una nuova API dominio seguendo checklist.

## Cadenza di revisione

- Aggiornare il catalogo building block ogni volta che nasce un helper riusabile.
- Aggiornare `api.md` solo per regole vincolanti o pattern architetturali.
- Aggiornare questo piano quando cambia il modo di controllare qualita`, debito
  o rischio operativo.
- Non usare questo piano come guida implementativa primaria: per il codice
  operativo valgono `api.md`, il catalogo building block e `.codex/AGENTS.md`.
