# Gestione Indirizzi — WIP

> Documento di lavoro per pianificazione e avanzamento dell'area Gestione Indirizzi.
> Data: 2026-03-14 | Stato: **DA INIZIARE**
>
> Documenti correlati:
>
> * [Architettura Building Block](componenti-riutilizzabili.md) — building block riutilizzabili (Sprint 3)
> * [Guida Gestione degli Indirizzi](/guide/gestione-degli-indirizzi) — regole e modello dati
> * [Guida Soggetti e Ruoli Anagrafici](/guide/soggetti-e-ruoli-anagrafici)
> * [Guida Sviluppo Frontend](guida-sviluppo-frontend.md) — convenzioni componenti e CSS
> * [Architettura Permessi e Autorizzazioni](/guide/architettura-permessi-e-autorizzazioni) — sistema permessi
>
> Riferimenti DB:
>
> * `anagrafiche.vw_indirizzi_dettaglio` — vista civici con comune/provincia/CAP
> * `script.vw_indirizzo_completo` — stradario con gerarchia geografica completa
> * `script.vw_stradario_esteso` — toponomastica + nome strada
> * `anagrafiche.fn_get_or_create_indirizzo_dettaglio(...)` — upsert civico con dedup

---

## Posizionamento nello Sviluppo Concentrico

L'area Gestione Indirizzi appartiene all'**Anello 1 — Dati Base e Configurazione**.

```
    Anello 1 (Dati Base)
    ┌────────────────────────────────────────────────────────────┐
    │  Gestione Indirizzi (NUOVO)                                │
    │                                                            │
    │  + API lista/ricerca indirizzi dettaglio                   │
    │  + API CRUD toponomastica                                  │
    │  + API lista comuni (read-only)                            │
    │  + API creazione indirizzo (fn_get_or_create)              │
    │  + Frontend: area Anagrafiche > Indirizzi (3 tab)          │
    └────────────────────────────────────────────────────────────┘
           ↑ usa
    Anello 0 (Nucleo — gia' esistente)
    ┌────────────────────────────────────────────────────────────┐
    │  core                — error_manager, pagination,          │
    │                        search_validators, endpoint_helpers │
    │  config.toponomastica — tipi strada (Via, Piazza...)       │
    │  config.stradario*    — gerarchia geografica               │
    │  config.comuni        — catalogo comuni (protetto)         │
    │  anagrafiche.*        — indirizzi_dettaglio, soggetti      │
    └────────────────────────────────────────────────────────────┘
```

### Perche' Anello 1

1. **Dato base condiviso** — gli indirizzi sono referenziati da tutti i domini:
   soggetti, ruoli, clienti, fornitori, istanze utility, magazzini.
2. **Nessuna logica di processo** — e' pura gestione anagrafica di dati geografici.
3. **DB gia' completo** — tabelle, trigger, funzioni, view e vincoli tutti operativi.
   Serve solo l'esposizione API + interfaccia frontend.
4. **Nessuna dipendenza inversa** — nessun modulo dipende da questa UI.

### Cosa aggiunge al sistema

| Capacita'                                   | Prima                         | Dopo                                                           |
| ------------------------------------------- | ----------------------------- | -------------------------------------------------------------- |
| Ricerca indirizzi dettaglio con filtri       | Solo via SQL                  | DataTable paginata con ricerca per via/comune                  |
| Creazione indirizzo normalizzato             | Solo via funzione DB          | Form guidato: comune → via → civico con dedup automatica       |
| Gestione toponomastica (tipi strada)         | Solo via SQL                  | CRUD da interfaccia con validazione unicita'                   |
| Consultazione comuni con provincia/regione   | Autocomplete gia' esistente   | DataTable read-only con ricerca full, provincia e regione      |
| Creazione via non presente nello stradario   | Solo via SQL multi-step       | Switch "Via non presente" con selezione toponomastica + nome   |

---

## Autorizzazione e controllo accessi

### Stato: PRONTO — nessuna modifica necessaria

Il sistema di permessi ZeroERP e' gia' completamente operativo e l'area `anagrafiche`
e' gia' seedata in `config.aree_funzionali` (codice `anagrafiche`, `schema_db = anagrafiche`).

### Catena di risoluzione permessi

```
Utente → ruolo_sistema?
  ├─ DISABILITATO → 403 (accesso negato)
  ├─ ADMIN        → 200 (bypass totale)
  └─ OPERATIVO    → risolvi livello per area "anagrafiche":
       1. Override utente su oggetto  (config.user_override_oggetti)
       2. Override utente su area     (config.user_override_aree)
       3. Profilo reparto             (config.profili_reparto_aree)
       4. Default                     → BLOCCATO

       Livello risultante:
       ├─ TUTTO    → GET + POST + PATCH (lettura + scrittura)
       ├─ LETTURA  → solo GET (consultazione)
       └─ BLOCCATO → 403 (nessun accesso)
```

### Applicazione nelle API view

Ogni endpoint dichiara `permission_classes = [ZeroERPPermission]` e `area_funzionale = "anagrafiche"`:

```python
from apps.core.api.permissions import ZeroERPPermission

class IndirizziListView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "anagrafiche"

    def get(self, request):   # Richiede LETTURA o TUTTO
        ...

class IndirizziView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [ZeroERPPermission]
    area_funzionale = "anagrafiche"

    def post(self, request):  # Richiede TUTTO
        ...
```

### Effetto pratico sulle operazioni

| Operazione | Metodo HTTP | Livello minimo | Chi puo' |
|------------|-------------|----------------|----------|
| Lista/ricerca indirizzi | GET | LETTURA | Operativi con accesso anagrafiche |
| Dettaglio indirizzo | GET | LETTURA | Operativi con accesso anagrafiche |
| Crea indirizzo | POST | TUTTO | Solo chi ha accesso completo |
| Modifica indirizzo | PATCH | TUTTO | Solo chi ha accesso completo |
| Lista toponomastica | GET | LETTURA | Operativi con accesso anagrafiche |
| Crea/modifica toponomastica | POST/PATCH | TUTTO | Solo chi ha accesso completo |
| Lista comuni | GET | LETTURA | Operativi con accesso anagrafiche |

### Infrastruttura gia' disponibile

- [x] `config.aree_funzionali` — area `anagrafiche` seedata (ordinamento 10)
- [x] `ZeroERPPermission` — permission class DRF operativa
- [x] `PermissionResolver` — risoluzione livello area via funzioni SQL
- [x] Cache L1/L2 — per-request (dict) + Redis (TTL 300s)
- [x] Profili reparto e override utente — tabelle e trigger operativi
- [x] `config.profili_reparto_aree` — configurabile per reparto/UO
- [x] `config.user_override_aree` — override per singolo utente

Non serve creare nuove tabelle, seed, funzioni o trigger.
L'integrazione e' automatica: basta dichiarare `area_funzionale` nelle view.

---

## Prerequisiti gia' esistenti

### DB (tutto operativo, nessuna modifica necessaria)

- [x] `config.toponomastica` — catalogo tipi strada (UNIQUE su descrizione)
- [x] `config.stradario_generale` — registro vie (toponomastica + nome)
- [x] `config.stradario` — via locale (stradario_generale + comune + CAP)
- [x] `config.comuni` — 8098 comuni con provincia, indice GIN trigram
- [x] `config.codici_postali` — CAP per comune
- [x] `config.province` — province con sigla e regione
- [x] `anagrafiche.indirizzi_dettaglio` — civici normalizzati con dedup
- [x] `anagrafiche.fn_get_or_create_indirizzo_dettaglio(...)` — upsert building block
- [x] `anagrafiche.vw_indirizzi_dettaglio` — vista con JOIN comune/provincia/CAP
- [x] `script.vw_indirizzo_completo` — stradario con gerarchia completa
- [x] `script.vw_stradario_esteso` — toponomastica + nome strada concatenati
- [x] Trigger di normalizzazione, protezione, dedup — tutti operativi

### Backend core (gia' esistente, da riusare)

- [x] `apps/core/api/pagination.py` — `paginated_envelope()`
- [x] `apps/core/api/search_validators.py` — validazione parametri search
- [x] `apps/core/api/endpoint_helpers.py` — `handle_post_json()`
- [x] `apps/core/api/views_lookup.py` — pattern di riferimento per le view
- [x] `apps/core/db/lookup_repository.py` — `search_comuni`, `search_stradario` gia' implementati

### Frontend core (gia' esistente, da riusare)

- [x] `src/core/components/ComuneAutocomplete.vue` — autocomplete comuni
- [x] `src/core/components/StradarioAutocomplete.vue` — autocomplete stradario per comune
- [x] `src/core/composables/useLookup.js` — cache generica lookup
- [x] `src/core/composables/useServerAutocomplete.js` — ricerca server con debounce
- [x] `src/core/composables/useApiHandler.js` — wrapper API con toast
- [x] `src/core/composables/usePagination.js` — paginazione server-side
- [x] `src/core/composables/useTabEvents.js` — eventi inter-tab
- [x] CSS utility classes: `app-page`, `app-datatable`, `form-grid`, `form-field`, `app-drawer-content`

---

## Principi di sviluppo componenti

### Ogni sotto-area deve essere un componente riutilizzabile

Non implementare i tab come blocchi inline nella vista. Ogni sotto-area (ricerca comuni,
ricerca toponomastica, ricerca indirizzi) deve essere un **componente autonomo** collocato
in `core/components/` se riusabile cross-dominio, oppure in `anagrafiche/components/` se
specifico del dominio.

| Componente | Collocazione | Riuso previsto |
| --- | --- | --- |
| `ComuniSearchTable.vue` | `core/components/` | Tab comuni qui + futuri filtri in clienti/fornitori/pratiche |
| `ToponomasticaSearchTable.vue` | `core/components/` | Tab toponomastica qui + futura gestione stradario |
| `IndirizziSearchTable.vue` | `anagrafiche/components/` | Tab indirizzi qui (specifico del dominio) |
| `ToponomasticaDrawer.vue` | `core/components/` | Da qui + futura gestione stradario |
| `IndirizzoDrawer.vue` | `anagrafiche/components/` | Da qui (specifico del dominio) |

La `IndirizziView.vue` compone i componenti via TabView, non contiene logica di lista/filtro.

### Pulsanti azione — pattern `app-page-action`

Il pulsante "Nuovo" e' gia' un pattern standard:

```vue
<Button
  class="app-page-action"
  :label="$t('indirizzi.nuovo_indirizzo')"
  icon="pi pi-plus"
  v-tooltip.bottom="$t('indirizzi.nuovo_indirizzo')"
  @click="openDrawer"
/>
```

Comportamento responsive (gia' in `main.css`):
- **Desktop/tablet**: mostra icona + label
- **Mobile** (< 768px): mostra solo icona, il testo dell'azione e' nel `v-tooltip`

### Form responsive e CSS condiviso

Tutti i form (drawer e inline) usano **esclusivamente** le classi CSS globali di `main.css`:

- `.app-drawer-content` — wrapper contenuto drawer (flex column, gap)
- `.form-grid` — contenitore campi (flex column, gap)
- `.form-field` — coppia label + input (flex column, gap ridotto)
- `.app-page-toolbar` / `.app-page-filters` — barra filtri con flex-wrap

**Nessun CSS scoped per layout form** — se serve un nuovo pattern, si aggiunge a `main.css`
come classe globale riutilizzabile. Lo `<style scoped>` resta solo per override PrimeVue
specifici del componente.

Per il layout a 2 colonne nel drawer (campi civico), usare CSS grid o flex con wrap
gia' dentro `.form-grid` — da aggiungere a `main.css` come variante `.form-grid-2col`
se non esiste.

### Checklist componente riutilizzabile

Prima di creare un componente, verificare:

1. **Esiste gia'?** — controllare `core/components/` e `core/composables/`
2. **Servira' altrove?** — se si', collocare in `core/`; se no, in `<dominio>/components/`
3. **Props minimali** — esporre solo cio' che varia tra i contesti d'uso
4. **Emits chiari** — `@saved`, `@selected`, `update:modelValue`
5. **i18n** — tutti i testi tramite `$t()`, mai stringhe hardcoded
6. **Responsive** — testare che il form funzioni su mobile (flex-wrap, no larghezze fisse)

---

## API Endpoints — Riferimento

Base URL: `api/v1/anagrafiche/`

### Indirizzi dettaglio

| Endpoint | Metodo | Auth | Livello min | Scopo |
| --- | --- | --- | --- | --- |
| `indirizzi/` | GET | JWT | LETTURA | Lista paginata con search ILIKE e filtro comune_id |
| `indirizzi/` | POST | JWT | TUTTO | Crea civico via `fn_get_or_create_indirizzo_dettaglio` |
| `indirizzi/<id>/` | GET | JWT | LETTURA | Dettaglio singolo per form edit |
| `indirizzi/<id>/` | PATCH | JWT | TUTTO | Aggiorna civico/dettagli (stradario non modificabile) |
| `codici-postali/?comune_id=N` | GET | JWT | LETTURA | Lista CAP per un comune (dropdown form creazione) |

**GET `indirizzi/`** — Parametri query:

| Parametro | Tipo | Default | Note |
| --- | --- | --- | --- |
| `search` | string | — | ILIKE su indirizzo_normalizzato e descrizione_comune |
| `comune_id` | int | — | Filtro esatto per comune |
| `limit` | int | 25 | Max 200 |
| `offset` | int | 0 | Paginazione |
| `order_by` | string | indirizzo_normalizzato | Colonne: indirizzo_normalizzato, civico, descrizione_comune, cap, provincia, attivo, data_insert |
| `order_dir` | string | asc | asc / desc |

**POST `indirizzi/`** — Due modalita':

```json
// Modalita' 1: via gia' presente nello stradario
{ "stradario_id": 123, "civico": 15, "estensione_civico": "A", "palazzina": null, "scala": "B", "piano": "2", "interno": "3" }

// Modalita' 2: via nuova (crea stradario_generale + stradario)
{ "toponomastica_id": 1, "descrizione_via": "Roma", "comune_id": 456, "codice_postale_id": 789, "civico": 15 }
```

Risposta: dettaglio completo dell'indirizzo creato/trovato (dedup automatica).

### Toponomastica

| Endpoint | Metodo | Auth | Livello min | Scopo |
| --- | --- | --- | --- | --- |
| `toponomastica/` | GET | JWT | LETTURA | Lista paginata con search |
| `toponomastica/` | POST | JWT | TUTTO | Crea tipo strada (UNIQUE su descrizione) |
| `toponomastica/<id>/` | PATCH | JWT | TUTTO | Modifica descrizione / attivo |

**POST `toponomastica/`**: `{ "descrizione": "Viale" }`
**PATCH `toponomastica/<id>/`**: `{ "descrizione": "...", "attivo": true/false }`

### Comuni

| Endpoint | Metodo | Auth | Livello min | Scopo |
| --- | --- | --- | --- | --- |
| `comuni/` | GET | JWT | LETTURA | Lista paginata read-only con provincia e regione |

**GET `comuni/`** — Parametri: `search`, `limit`, `offset`, `order_by` (descrizione, provincia_sigla, regione_descrizione), `order_dir`.

### Envelope risposta standard

Tutte le risposte lista seguono l'envelope paginato:

```json
{
  "data": {
    "count": 150,
    "page": 1,
    "page_size": 25,
    "total_pages": 6,
    "results": [...]
  },
  "meta": { "request_id": "..." }
}
```

Le risposte create/update seguono l'envelope standard:

```json
{ "data": { ... }, "meta": { "request_id": "..." } }
```

### Codici errore

| Codice | Contesto | Descrizione |
| --- | --- | --- |
| `E_ANAG_VALIDAZIONE` | POST/PATCH | Campo obbligatorio mancante o non valido |
| `E_ANAG_DUPLICATO` | POST toponomastica | Descrizione gia' esistente (UNIQUE violation) |
| `E_ANAG_NOT_FOUND` | GET/PATCH dettaglio | ID non trovato |

---

## Gerarchia geografica DB

```
config.toponomastica (Via, Piazza, Corso...)
    ↓ toponomastica_id
config.stradario_generale (Via Roma, Piazza Duomo...)
    ↓ stradario_generale_id
config.stradario (via + comune + CAP)  ←  UNIQUE(comune_id, stradario_generale_id, codice_postale_id)
    ↓ stradario_id
anagrafiche.indirizzi_dettaglio (civico + dettagli)
    ↓ indirizzo_dettaglio_id
anagrafiche.indirizzi / anagrafiche.indirizzi_soggetti (assegnazione a ruolo/soggetto)
```

La funzione `fn_get_or_create_indirizzo_dettaglio` opera sull'ultimo livello:
riceve `stradario_id` (gia' risolto) e i dettagli civico, restituisce `bigint` (id).

Per creare un indirizzo con una via nuova (non presente nello stradario locale),
il backend deve prima:

1. Cercare/creare `stradario_generale` (toponomastica_id + descrizione)
2. Cercare/creare `stradario` (stradario_generale_id + comune_id + codice_postale_id)
3. Chiamare `fn_get_or_create_indirizzo_dettaglio(stradario_id, ...)`

---

## Architettura frontend — Vista unica con TabView

Una sola voce di menu **Indirizzi** sotto il dominio `anagrafiche`,
con **3 tab** nella pagina (TabView PrimeVue):

| Tab | DataTable | CRUD | Drawer |
|-----|-----------|------|--------|
| **Indirizzi** (default) | `vw_indirizzi_dettaglio` — indirizzo, civico, comune, provincia, CAP, attivo | Crea + Edit | IndirizzoDrawer (640px) |
| **Toponomastica** | `config.toponomastica` — descrizione, attivo | Crea + Edit | ToponomasticaDrawer (480px) |
| **Comuni** | `config.comuni + province` — descrizione, provincia sigla, regione | Solo lettura | — |

Ogni tab segue il pattern standard: `app-page-toolbar` + `app-page-filters` + `app-datatable`.

---

## 1. Backend: Repository indirizzi

### BE-1 — `indirizzi_repository.py` (NUOVO)

File: `backend/apps/anagrafiche/db/indirizzi_repository.py`

```python
class IndirizziRepository:
    """Accesso DB per indirizzi, toponomastica e comuni."""

    # -- Indirizzi Dettaglio --

    def list_indirizzi_dettaglio(self, *, search=None, comune_id=None,
                                  limit=25, offset=0,
                                  order_by='indirizzo_normalizzato',
                                  order_dir='asc'):
        # Query su anagrafiche.vw_indirizzi_dettaglio
        # Filtro ILIKE su indirizzo_normalizzato, descrizione_comune
        # Filtro opzionale per comune_id
        # COUNT(*) OVER() per totale
        # Colonne: indirizzo_dettaglio_id, stradario_id,
        #   indirizzo_normalizzato, civico, estensione_civico,
        #   descrizione_comune, cap, provincia, attivo

    def get_indirizzo_dettaglio(self, indirizzo_dettaglio_id):
        # Dettaglio singolo per form edit
        # Include tutti i campi: palazzina, scala, piano, interno

    def create_indirizzo_dettaglio(self, *, stradario_id, civico=None,
                                    estensione_civico=None, palazzina=None,
                                    scala=None, piano=None, interno=None):
        # SELECT anagrafiche.fn_get_or_create_indirizzo_dettaglio(
        #     %s, %s, %s, %s, %s, %s, %s)
        # Restituisce: { id, created } (created=True se nuovo, False se esistente)

    def update_indirizzo_dettaglio(self, indirizzo_dettaglio_id, *,
                                    civico=None, estensione_civico=None,
                                    palazzina=None, scala=None,
                                    piano=None, interno=None, attivo=None):
        # UPDATE anagrafiche.indirizzi_dettaglio SET ... WHERE id = %s
        # Nota: stradario_id NON modificabile (protetto da trigger)

    # -- Toponomastica --

    def list_toponomastica(self, *, search=None, limit=25, offset=0,
                            order_by='descrizione', order_dir='asc'):
        # Query su config.toponomastica con COUNT(*) OVER()
        # Filtro ILIKE su descrizione
        # Colonne: id, descrizione, attivo

    def create_toponomastica(self, *, descrizione):
        # INSERT INTO config.toponomastica (descrizione) VALUES (%s) RETURNING id, descrizione
        # Gestire IntegrityError per UNIQUE violation

    def update_toponomastica(self, toponomastica_id, *, descrizione=None, attivo=None):
        # UPDATE config.toponomastica SET ... WHERE id = %s
        # Gestire errore trigger se in uso e si tenta modifica bloccante

    # -- Comuni --

    def list_comuni(self, *, search=None, limit=25, offset=0,
                     order_by='descrizione', order_dir='asc'):
        # Query su config.comuni c
        #   LEFT JOIN config.province p ON c.provincia_id = p.id
        #   LEFT JOIN config.regioni r ON p.regione_id = r.id
        # Filtro ILIKE su c.descrizione
        # COUNT(*) OVER() per totale
        # Colonne: id, descrizione, provincia_sigla, provincia_descrizione,
        #   regione_descrizione

    # -- Stradario (supporto creazione via nuova) --

    def get_or_create_stradario(self, *, toponomastica_id, descrizione_via,
                                  comune_id, codice_postale_id):
        # 1. SELECT/INSERT config.stradario_generale
        #    (toponomastica_id, descrizione) → stradario_generale_id
        # 2. SELECT/INSERT config.stradario
        #    (stradario_generale_id, comune_id, codice_postale_id) → stradario_id
        # Restituisce stradario_id
        # Gestire IntegrityError per race condition

    def list_codici_postali_by_comune(self, comune_id):
        # SELECT id, codice FROM config.codici_postali
        #   WHERE comune_id = %s ORDER BY codice
        # Per popolare dropdown CAP nel form creazione
```

- **Prerequisiti**: nessuno (tabelle e view DB gia' esistenti)
- **Test**: `apps/anagrafiche/tests/db/test_indirizzi_repository.py` — unittest con mock cursor

---

## 2. Backend: API Views

### BE-2 — `views_toponomastica.py` (NUOVO)

File: `backend/apps/anagrafiche/api/views_toponomastica.py`

| Endpoint | Metodo | View | Scopo |
|----------|--------|------|-------|
| `api/v1/anagrafiche/toponomastica/` | GET | `ToponomasticaListView` | Lista paginata con search |
| `api/v1/anagrafiche/toponomastica/` | POST | `ToponomasticaView` | Crea tipo strada |
| `api/v1/anagrafiche/toponomastica/<id>/` | PATCH | `ToponomasticaDetailView` | Modifica/disattiva |

- Pattern: come `views_lookup.py` — `@extend_schema`, `success_response`, `paginated_envelope`
- POST usa `handle_post_json` per parsing uniforme
- Gestione `IntegrityError` su UNIQUE(descrizione) → `ServiceError` con messaggio chiaro
- **Prerequisiti**: BE-1

### BE-3 — `views_comuni.py` (NUOVO)

File: `backend/apps/anagrafiche/api/views_comuni.py`

| Endpoint | Metodo | View | Scopo |
|----------|--------|------|-------|
| `api/v1/anagrafiche/comuni/` | GET | `ComuniListView` | Lista paginata read-only |

- Solo GET, nessun CRUD (comuni protetti da trigger DB)
- Colonne: descrizione, provincia_sigla, provincia_descrizione, regione_descrizione
- **Prerequisiti**: BE-1

### BE-4 — `views_indirizzi.py` (NUOVO)

File: `backend/apps/anagrafiche/api/views_indirizzi.py`

| Endpoint | Metodo | View | Scopo |
|----------|--------|------|-------|
| `api/v1/anagrafiche/indirizzi/` | GET | `IndirizziListView` | Lista paginata con filtri |
| `api/v1/anagrafiche/indirizzi/` | POST | `IndirizziView` | Crea civico (fn_get_or_create) |
| `api/v1/anagrafiche/indirizzi/<id>/` | GET | `IndirizzoDetailView` | Dettaglio per edit |
| `api/v1/anagrafiche/indirizzi/<id>/` | PATCH | `IndirizziDetailView` | Aggiorna civico/dettagli |
| `api/v1/anagrafiche/codici-postali/` | GET | `CodiciPostaliByComune` | CAP filtrati per comune_id |

Payload POST creazione (due modalita'):

```json
// Modalita' 1 — via esistente nello stradario (StradarioAutocomplete usato)
{
  "stradario_id": 123,
  "civico": 15,
  "estensione_civico": "A",
  "palazzina": null,
  "scala": "B",
  "piano": "2",
  "interno": "3"
}

// Modalita' 2 — via nuova (switch "Via non presente")
{
  "toponomastica_id": 1,
  "descrizione_via": "Roma",
  "comune_id": 456,
  "codice_postale_id": 789,
  "civico": 15,
  "estensione_civico": null,
  "palazzina": null,
  "scala": null,
  "piano": null,
  "interno": null
}
```

La view POST discrimina: se `stradario_id` presente → usa direttamente;
altrimenti chiama `get_or_create_stradario()` prima di `create_indirizzo_dettaglio()`.

- `is_search_endpoint = True` per IndirizziListView (throttling)
- **Prerequisiti**: BE-1

### BE-5 — `urls.py` (MODIFICARE)

File: `backend/apps/anagrafiche/api/urls.py`

```python
from django.urls import path
from .views_indirizzi import (IndirizziListView, IndirizziView,
                               IndirizzoDetailView, IndirizziDetailView,
                               CodiciPostaliByComune)
from .views_toponomastica import (ToponomasticaListView, ToponomasticaView,
                                   ToponomasticaDetailView)
from .views_comuni import ComuniListView

urlpatterns = [
    path('indirizzi/', IndirizziListView.as_view()),
    path('indirizzi/', IndirizziView.as_view()),
    path('indirizzi/<int:pk>/', IndirizzoDetailView.as_view()),
    path('indirizzi/<int:pk>/', IndirizziDetailView.as_view()),
    path('codici-postali/', CodiciPostaliByComune.as_view()),
    path('toponomastica/', ToponomasticaListView.as_view()),
    path('toponomastica/', ToponomasticaView.as_view()),
    path('toponomastica/<int:pk>/', ToponomasticaDetailView.as_view()),
    path('comuni/', ComuniListView.as_view()),
]
```

Verificare che `zeroerp_backend/urls.py` includa:
```python
path("api/v1/anagrafiche/", include("apps.anagrafiche.api.urls")),
```

- **Prerequisiti**: BE-2, BE-3, BE-4

### BE-6 — Test API

File: `backend/apps/anagrafiche/tests/api/test_indirizzi_api.py`
File: `backend/apps/anagrafiche/tests/api/test_toponomastica_api.py`

- `unittest.TestCase` con mock del repository (no DB reale in CI)
- Test per ogni endpoint: status code, envelope response, validazione parametri
- Test gestione errori: UNIQUE violation toponomastica, stradario_id non valido

- **Prerequisiti**: BE-5

---

## 3. Frontend: Infrastruttura

### FE-1 — API client `anagrafiche.js`

File: `frontend/src/anagrafiche/api/anagrafiche.js`

```javascript
import api from '@/core/api'

const BASE = '/api/v1/anagrafiche'

// -- Indirizzi --
export function listIndirizzi(params) {
  return api.get(`${BASE}/indirizzi/`, { params })
}
export function getIndirizzo(id) {
  return api.get(`${BASE}/indirizzi/${id}/`)
}
export function createIndirizzo(payload) {
  return api.post(`${BASE}/indirizzi/`, payload)
}
export function updateIndirizzo(id, payload) {
  return api.patch(`${BASE}/indirizzi/${id}/`, payload)
}
export function listCodiciPostali(params) {
  return api.get(`${BASE}/codici-postali/`, { params })
}

// -- Toponomastica --
export function listToponomastica(params) {
  return api.get(`${BASE}/toponomastica/`, { params })
}
export function createToponomastica(payload) {
  return api.post(`${BASE}/toponomastica/`, payload)
}
export function updateToponomastica(id, payload) {
  return api.patch(`${BASE}/toponomastica/${id}/`, payload)
}

// -- Comuni --
export function listComuni(params) {
  return api.get(`${BASE}/comuni/`, { params })
}
```

- **Prerequisiti**: BE-5

### FE-2 — Pinia stores

File: `frontend/src/anagrafiche/stores/indirizzi.js`

```javascript
// Pattern identico a useUtentiStore
// State: items, totalRecords, loading, filters { search, comune_id, limit, offset, order_by, order_dir }
// Actions: fetchList, create, update
```

File: `frontend/src/anagrafiche/stores/toponomastica.js`

```javascript
// State: items, totalRecords, loading, filters { search, limit, offset, order_by, order_dir }
// Actions: fetchList, create, update
```

File: `frontend/src/anagrafiche/stores/comuni.js`

```javascript
// State: items, totalRecords, loading, filters { search, limit, offset, order_by, order_dir }
// Actions: fetchList (solo lettura)
```

- **Prerequisiti**: FE-1

### FE-3 — Navigazione e routing

File da modificare: `frontend/src/core/navigation.js`

```javascript
// Aggiungere a DOMAIN_MENUS['anagrafiche']:
'anagrafiche': [
  { key: 'indirizzi', icon: 'pi pi-map-marker', to: '/anagrafiche/indirizzi' }
],
```

File da modificare: `frontend/src/router/index.js`

- Spostare `anagrafiche` da `domainPlaceholderRoutes` a `domainsWithRoutes`
- Aggiungere route:

```javascript
{
  path: 'indirizzi',
  name: 'anagrafiche-indirizzi',
  component: () => import('../anagrafiche/views/IndirizziView.vue'),
  meta: { domain: 'anagrafiche', menuKey: 'indirizzi' }
}
```

- **Prerequisiti**: nessuno (puo' procedere in parallelo con FE-1/FE-2)

### FE-4 — Chiavi i18n

File da modificare: `frontend/src/locales/it.json`

```json
{
  "nav_menu": {
    "anagrafiche": {
      "indirizzi": "Indirizzi"
    }
  },
  "indirizzi": {
    "tab_indirizzi": "Indirizzi",
    "tab_toponomastica": "Toponomastica",
    "tab_comuni": "Comuni",
    "search_indirizzo": "Cerca indirizzo o comune...",
    "search_toponomastica": "Cerca tipo strada...",
    "search_comune": "Cerca comune...",
    "filtro_comune": "Filtra per comune",
    "nuovo_indirizzo": "Nuovo Indirizzo",
    "modifica_indirizzo": "Modifica Indirizzo",
    "nuova_toponomastica": "Nuova",
    "modifica_toponomastica": "Modifica Toponomastica",
    "col_indirizzo": "Indirizzo",
    "col_civico": "Civico",
    "col_comune": "Comune",
    "col_provincia": "Provincia",
    "col_regione": "Regione",
    "col_cap": "CAP",
    "col_attivo": "Stato",
    "col_descrizione": "Descrizione",
    "campo_comune": "Comune",
    "campo_via": "Via",
    "campo_toponomastica": "Tipo strada",
    "campo_nome_via": "Nome via",
    "campo_cap": "CAP",
    "campo_civico": "Civico",
    "campo_estensione": "Estensione",
    "campo_palazzina": "Palazzina",
    "campo_scala": "Scala",
    "campo_piano": "Piano",
    "campo_interno": "Interno",
    "via_non_presente": "Via non presente, crea nuova",
    "indirizzo_creato": "Indirizzo creato",
    "indirizzo_salvato": "Indirizzo salvato",
    "indirizzo_esistente": "Indirizzo gia' esistente, associato",
    "toponomastica_creata": "Tipo strada creato",
    "toponomastica_salvata": "Tipo strada salvato",
    "toponomastica_duplicata": "Tipo strada gia' esistente"
  }
}
```

Equivalente in `en.json`.

- **Prerequisiti**: nessuno

---

## 4. Frontend: Componenti e Vista

### FE-5 — `ToponomasticaDrawer.vue`

File: `frontend/src/anagrafiche/components/ToponomasticaDrawer.vue`

Drawer semplice (DRAWER_WIDTH.SIMPLE = 480px):

```
┌─────────────────────────────────┐
│ Nuova Toponomastica / Modifica  │
├─────────────────────────────────┤
│                                 │
│  Descrizione *                  │
│  [InputText ________________]   │
│                                 │
│  Attivo (solo in edit)          │
│  [ToggleSwitch]                 │
│                                 │
├─────────────────────────────────┤
│  [Annulla]          [Salva]     │
└─────────────────────────────────┘
```

- Props: `mode` ('create' | 'edit'), `item` (oggetto da editare)
- Emits: `saved`
- Usa `useApiHandler` per loading/toast
- CSS: `app-drawer-content`, `form-grid`, `form-field`

- **Prerequisiti**: FE-1, FE-2

### FE-6 — `IndirizzoDrawer.vue`

File: `frontend/src/anagrafiche/components/IndirizzoDrawer.vue`

Drawer medio (DRAWER_WIDTH.STANDARD = 640px):

```
┌───────────────────────────────────────────────┐
│ Nuovo Indirizzo / Modifica Indirizzo          │
├───────────────────────────────────────────────┤
│                                               │
│  --- Localizzazione ---                       │
│                                               │
│  Comune *                                     │
│  [ComuneAutocomplete __________________]      │
│                                               │
│  Via *                                        │
│  [StradarioAutocomplete _______________]      │
│                                               │
│  ☐ Via non presente, crea nuova               │
│  ┌─ (visibile se checkbox attivo) ──────────┐ │
│  │  Tipo strada *                            │ │
│  │  [Select toponomastica ▼]                 │ │
│  │                                           │ │
│  │  Nome via *                               │ │
│  │  [InputText ________________________]     │ │
│  │                                           │ │
│  │  CAP *                                    │ │
│  │  [Select CAP ▼] (filtrato per comune)     │ │
│  └───────────────────────────────────────────┘ │
│                                               │
│  --- Civico ---                               │
│                                               │
│  Civico          │ Estensione                 │
│  [InputNumber]   │ [InputText___]             │
│                  │                            │
│  Palazzina       │ Scala                      │
│  [InputText___]  │ [InputText___]             │
│                  │                            │
│  Piano           │ Interno                    │
│  [InputText___]  │ [InputText___]             │
│                                               │
│  Attivo (solo in edit)                        │
│  [ToggleSwitch]                               │
│                                               │
├───────────────────────────────────────────────┤
│  [Annulla]                        [Salva]     │
└───────────────────────────────────────────────┘
```

**Modo CREA:**

- L'utente seleziona prima il comune (ComuneAutocomplete)
- Poi seleziona la via (StradarioAutocomplete, filtrato per comune)
- Se la via non esiste → attiva il checkbox "Via non presente":
  - Appare Select toponomastica (caricata con `useLookup` dall'endpoint toponomastica)
  - Appare InputText nome via
  - Appare Select CAP (caricato dall'endpoint `codici-postali?comune_id=X`)
- Compila i dettagli civico
- Il payload POST discrimina tra le due modalita'

**Modo EDIT:**

- Sezione Localizzazione in sola lettura (indirizzo non rilocabile)
- Solo campi civico/dettaglio editabili + toggle attivo

Componenti riusati:
- `ComuneAutocomplete.vue` (core, gia' esistente)
- `StradarioAutocomplete.vue` (core, gia' esistente)
- `useLookup.js` per dropdown toponomastica
- `useApiHandler.js` per loading/toast

- **Prerequisiti**: FE-1, FE-2, FE-5 (per dropdown toponomastica che condivide dati)

### FE-7 — `IndirizziView.vue`

File: `frontend/src/anagrafiche/views/IndirizziView.vue`

Vista principale con TabView PrimeVue (lazy):

```
┌────────────────────────────────────────────────────────────┐
│ [ Indirizzi ]  [ Toponomastica ]  [ Comuni ]               │
├────────────────────────────────────────────────────────────┤
│                                                            │
│  TAB INDIRIZZI (default):                                  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🔍 Cerca...  │ [ComuneAutocomplete ▼]  [+ Nuovo]    │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ Indirizzo    │ Civico │ Comune  │ Prov │ CAP │ Stato │  │
│  │ Via Roma 1   │ 1      │ Milano  │ MI   │ 201 │ ● att │  │
│  │ Via Roma 3/A │ 3      │ Milano  │ MI   │ 201 │ ● att │  │
│  │ P.zza Duomo  │ 5      │ Torino  │ TO   │ 101 │ ● att │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ « 1 2 3 ... 50 »                     25 per pagina  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  TAB TOPONOMASTICA:                                        │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🔍 Cerca...                              [+ Nuova]   │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ Descrizione              │ Stato                     │  │
│  │ Via                      │ ● attivo                  │  │
│  │ Piazza                   │ ● attivo                  │  │
│  │ Corso                    │ ● attivo                  │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
│  TAB COMUNI:                                               │
│  ┌──────────────────────────────────────────────────────┐  │
│  │ 🔍 Cerca...                                          │  │
│  ├──────────────────────────────────────────────────────┤  │
│  │ Comune       │ Provincia │ Regione                   │  │
│  │ Milano       │ MI        │ Lombardia                 │  │
│  │ Roma         │ RM        │ Lazio                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

- Ogni tab ha il proprio store e gestisce paginazione/sort/filtri indipendentemente
- Row-click su tab Indirizzi → apre IndirizzoDrawer in edit
- Row-click su tab Toponomastica → apre ToponomasticaDrawer in edit
- Tab Comuni → nessun row-click, solo consultazione
- `useTabEvents` per refresh inter-tab dopo creazione

- **Prerequisiti**: FE-3, FE-4, FE-5, FE-6

### FE-8 — Build e verifica

- `vite build` senza errori
- Navigazione sidebar → Anagrafiche → Indirizzi funzionante
- Tutti e 3 i tab si caricano

- **Prerequisiti**: FE-7

---

## Struttura file risultante

### Backend

```
backend/apps/anagrafiche/
  db/
    anagrafiche_repository.py        # (esistente — non modificato)
    indirizzi_repository.py          # NUOVO
  api/
    urls.py                          # MODIFICATO (era vuoto)
    views.py                         # (esistente — non modificato)
    views_indirizzi.py               # NUOVO
    views_toponomastica.py           # NUOVO
    views_comuni.py                  # NUOVO
  tests/
    api/
      test_indirizzi_api.py          # NUOVO
      test_toponomastica_api.py      # NUOVO
    db/
      test_indirizzi_repository.py   # NUOVO
```

### Frontend

```
frontend/src/anagrafiche/
  api/
    anagrafiche.js                   # NUOVO
  stores/
    indirizzi.js                     # NUOVO
    toponomastica.js                 # NUOVO
    comuni.js                        # NUOVO
  components/
    IndirizzoDrawer.vue              # NUOVO
    ToponomasticaDrawer.vue          # NUOVO
  views/
    IndirizziView.vue                # NUOVO
```

---

## Ordine di esecuzione

```
Passo  Task                                          Prerequisiti    Stato
─────  ────────────────────────────────────────────   ────────────    ──────
 1     BE-1  Repository indirizzi                    nessuno         DA FARE
 2     BE-2  Views toponomastica                     BE-1            DA FARE
 3     BE-3  Views comuni                            BE-1            DA FARE
 4     BE-4  Views indirizzi                         BE-1            DA FARE
 5     BE-5  URLs e registrazione                    BE-2..4         DA FARE
 6     BE-6  Test backend                            BE-5            DA FARE
 7     FE-1  API client anagrafiche.js               BE-5            DA FARE
 8     FE-2  Pinia stores (3 file)                   FE-1            DA FARE
 9     FE-3  Navigazione e routing                   —               DA FARE
10     FE-4  Chiavi i18n                             —               DA FARE
11     FE-5  ToponomasticaDrawer                     FE-1, FE-2      DA FARE
12     FE-6  IndirizzoDrawer                         FE-1, FE-2      DA FARE
13     FE-7  IndirizziView (3 tab)                   FE-3..6         DA FARE
14     FE-8  Build e verifica                        FE-7            DA FARE
```

---

## Verifica finale

- [ ] Backend: test passano con `./manage-test.sh apps.anagrafiche.tests -v 2`
- [ ] Frontend: `vite build` senza errori
- [ ] UI: sidebar Anagrafiche mostra voce "Indirizzi"
- [ ] UI: tab Indirizzi carica lista con paginazione e ricerca
- [ ] UI: tab Toponomastica carica lista con CRUD
- [ ] UI: tab Comuni carica lista read-only con ricerca
- [ ] UI: IndirizzoDrawer crea indirizzo (via esistente)
- [ ] UI: IndirizzoDrawer crea indirizzo (via nuova)
- [ ] UI: ToponomasticaDrawer crea e modifica tipo strada
- [ ] UI: filtro ComuneAutocomplete nel tab Indirizzi funziona

---

*Gestione Indirizzi — ZeroERP (marzo 2026)*
*Sviluppo Concentrico — Anello 1, Dati Base*
