# Pannello Config — WIP

> Documento di lavoro per il pannello di gestione tabelle di configurazione.
> Data: 2026-03-15 | Completato: 2026-03-15 | Stato: **COMPLETATO**
> Testato UI: 2026-03-15
>
> **Nota futura:** il pulsante "Programma gestione" (visibile solo ADMIN) per associare
> drawer dedicati alle tabelle non e' ancora implementato. Il mapping drawer generico/dedicato
> funziona gia' nel registro `config-tables.js` — quando servono drawer dedicati, lo sviluppatore
> li crea, li registra, e l'admin potra' associarli dal pulsante. Da implementare quando
> si creano i primi drawer dedicati (forme giuridiche, tipi soggetto dettaglio).
>
> Documenti correlati:
>
> * [Frontend Standards](/frontend/frontend-standards) — regole UI
> * [API Contract](/dev/api) — contratto API (sezione lookup)
> * [Sviluppo Soggetti](sviluppo-soggetti.md) — prerequisito per soggetti (Fase 0)

---

## Obiettivo

Un'unica pagina per gestire tutte le tabelle di configurazione del sistema.
Niente drawer/tab separati per ogni tabella — un elenco navigabile organizzato per schema,
con click → gestione inline.

Il pannello copre tutte le tabelle nella whitelist lookup (~67 tabelle) piu' eventuali
tabelle complesse con drawer dedicato.

---

## Architettura

### Due livelli: lista generica + drawer specifico

**Lista** — uguale per tutte le tabelle:
- Usa l'API lookup generico `GET /core/lookup/codici/?rel=<schema.tabella>`
- Colonne standard: codice, codice_interno (se presente), descrizione
- Paginazione, ricerca, ordinamento — tutto via `useSearchTable`

**Drawer** — due tipi:
- **Generico** (~60 tabelle): campi codice + descrizione + attivo (se presente)
- **Dedicato** (3-4 tabelle): drawer custom con campi specifici

```
┌────────────────────────────────────────────────────────────────┐
│ [🔍 Cerca tabella...]                                          │
├───────────────────┬────────────────────────────────────────────┤
│                   │                                            │
│ CONFIG            │  Qualifiche                   [+ Nuovo]    │
│   Ambiti          │  ┌────────┬──────────┬──────────────────┐  │
│   Aree Funzionali │  │ Codice │ Cod.Int. │ Descrizione      │  │
│   Canali Pratiche │  ├────────┼──────────┼──────────────────┤  │
│  ►Qualifiche      │  │ OPE    │ OPE      │ Operatore        │  │
│   Termini Pag.    │  │ TEC    │ TEC      │ Tecnico          │  │
│   ...             │  │ AMM    │ AMM      │ Amministrativo   │  │
│                   │  └────────┴──────────┴──────────────────┘  │
│ MAGAZZINO         │                                            │
│   Causali         │                                            │
│   ...             │                                            │
│                   │                                            │
│ VENDITE           │                                            │
│   Stati Commessa  │                                            │
│   ...             │                                            │
│                   │                                            │
└───────────────────┴────────────────────────────────────────────┘
```

### Mapping drawer per tabella

```js
// config-tables.js — registro centralizzato
export const CONFIG_TABLES = [
  // schema, rel (per API), label, drawer type
  { schema: 'config', rel: 'config.ambiti', label: 'Ambiti', drawer: 'generic' },
  { schema: 'config', rel: 'config.aree_funzionali', label: 'Aree Funzionali', drawer: 'generic' },
  { schema: 'config', rel: 'config.canali_pratiche', label: 'Canali Pratiche', drawer: 'generic' },
  { schema: 'config', rel: 'config.forme_giuridiche', label: 'Forme Giuridiche', drawer: 'FormeGiuridicheDrawer' },
  { schema: 'config', rel: 'config.iva', label: 'IVA', drawer: 'generic' },
  { schema: 'config', rel: 'config.qualifiche', label: 'Qualifiche', drawer: 'generic' },
  // ... tutte le altre
  { schema: 'magazzino', rel: 'magazzino.causali', label: 'Causali', drawer: 'generic' },
  { schema: 'vendite', rel: 'vendite.stati_commessa', label: 'Stati Commessa', drawer: 'generic' },
  // ...
]
```

Il registro e' la **fonte unica di verita'**: aggiungere una tabella = aggiungere una riga.
La whitelist backend (`_REL_CONSENTITE`) controlla l'accesso; il registro frontend
controlla cosa mostrare nel pannello.

### Programma gestione — configurabile dall'admin

L'admin puo' associare un **drawer dedicato** a qualsiasi tabella tramite un pulsante
"Programma gestione" nella toolbar del pannello. Il drawer si sceglie da una **lista chiusa**
di componenti registrati nel codice — non e' un campo libero (zero rischio injection).

```
┌─────────────────────────────────────────────┐
│ Programma gestione: Forme Giuridiche        │
├─────────────────────────────────────────────┤
│                                             │
│  Drawer corrente: FormeGiuridicheDrawer     │
│                                             │
│  Cambia drawer:                             │
│  [▼ Generico                           ]    │
│  [  FormeGiuridicheDrawer              ]    │
│  [  TipiSoggettoDettaglioDrawer        ]    │
│  [  UnitaOrganizzativeDrawer           ]    │
│                                             │
├─────────────────────────────────────────────┤
│  [Annulla]              [Salva]             │
└─────────────────────────────────────────────┘
```

**Regole:**
- Solo utenti ADMIN vedono il pulsante "Programma gestione"
- La lista drawer disponibili e' **hardcoded nel codice** — lo sviluppatore crea il drawer,
  lo registra, l'admin lo associa
- Il mapping `tabella → drawer` puo' essere persistito nel backend (tabella config o JSON)
  oppure nel registro frontend (piu' semplice per iniziare)
- Default: tutte le tabelle usano il drawer generico
- Se un drawer dedicato viene rimosso dal codice, la tabella torna automaticamente al generico

**Evoluzione futura:**
Il pattern e' lo stesso dell'AS/400 — programmi di gestione associabili a entita'.
La differenza e' che qui i "programmi" sono componenti Vue reattivi con validazione,
lookup, autocomplete, e tutto il framework UI standard. Il concetto e' identico:
l'admin configura, lo sviluppatore costruisce i programmi.

---

## Tabelle complesse (drawer dedicato)

Tabelle che hanno campi oltre il pattern standard e richiedono UI specifica:

| Tabella | Campi extra | Drawer dedicato |
| --- | --- | --- |
| `config.forme_giuridiche` | `attivo`, `rea_policy`, `capitale_sociale_policy`, `stato_id`, `meta` | `FormeGiuridicheDrawer` |
| `config.tipi_soggetto_dettaglio` | `tipo_soggetto_id`, `formato_cf`, `formato_piva`, `dati_societari_policy`, `cf_obbligatorio`, `piva_obbligatoria` | `TipiSoggettoDettaglioDrawer` |
| `config.unita_organizzative` | `parent_id` (gerarchia), `codice_interno` | `UnitaOrganizzativeDrawer` |

Tutte le altre (~64 tabelle) usano il drawer generico.

---

## Implementazione

### Fase 1 — Backend

Il lookup lista gia' esiste (`GET /core/lookup/codici/`).
Manca il CRUD generico (create, detail, update) e i metadata delle tabelle.

**Nessuna modifica DB necessaria** — il backend legge i metadata da `information_schema`
(introspezione tecnica, non logica business — non viola il principio DB-first).

#### BE-1 — Metadata tabelle via `information_schema`

File: `backend/apps/core/db/config_metadata_repository.py`

```python
class ConfigMetadataRepository:
    def get_table_columns(self, schema, table):
        """Legge information_schema — colonne gestibili (esclude audit)."""
        sql = """
            SELECT column_name, data_type, is_nullable, column_default
              FROM information_schema.columns
             WHERE table_schema = %s AND table_name = %s
               AND column_name NOT IN (
                   'data_insert','user_insert','data_update','user_update','tx_id','storicizza'
               )
             ORDER BY ordinal_position
        """
        # Restituisce lista di { name, type, nullable, has_default }
        # Cacheable in memoria — i metadata non cambiano a runtime
```

**Prerequisiti:** nessuno
**Effort:** 30 minuti

#### BE-2 — Endpoint CRUD generico config

File: `backend/apps/core/api/views_config_crud.py`

| Endpoint | Metodo | Scopo |
| --- | --- | --- |
| `config/tables/` | GET | Lista tabelle disponibili (dalla whitelist) |
| `config/tables/<rel>/metadata/` | GET | Metadata colonne (da information_schema, cacheable) |
| `config/tables/<rel>/` | GET | Lista paginata records (riusa lookup esistente) |
| `config/tables/<rel>/` | POST | Crea record (INSERT generico) |
| `config/tables/<rel>/<id>/` | GET | Dettaglio record (`SELECT *` filtrato) |
| `config/tables/<rel>/<id>/` | PATCH | Aggiorna record (UPDATE dinamico) |

Il CRUD generico usa i metadata per costruire INSERT/UPDATE/SELECT dinamici.
Le colonne audit (`data_insert`, `user_insert`, ecc.) sono escluse automaticamente.

**Sicurezza**: protetto da `ZeroERPPermission` con `area_funzionale = "config"`.
Solo utenti con accesso TUTTO a `config` possono modificare.

**Prerequisiti:** BE-1
**Effort:** 1-2 sessioni

### Fase 2 — Frontend infrastruttura

#### FE-1 — Registro tabelle config

File: `frontend/src/core/config-tables.js`

Lista di tutte le tabelle con: schema, rel, label i18n, tipo drawer.
Organizzate per schema. Il pannello legge da qui.

**Prerequisiti:** nessuno
**Effort:** 30 minuti

#### FE-2 — GenericConfigDrawer.vue

File: `frontend/src/core/components/GenericConfigDrawer.vue`

Drawer SIMPLE (480px) per tabelle standard:

```
┌──────────────────────────────────┐
│ Nuovo / Modifica [Nome Tabella]  │
├──────────────────────────────────┤
│                                  │
│  Codice                          │
│  [InputText]                     │
│                                  │
│  Codice Interno                  │
│  [InputText] (se presente)       │
│                                  │
│  Descrizione *                   │
│  [InputText]                     │
│                                  │
│  Attivo (se presente)            │
│  [ToggleSwitch]                  │
│                                  │
├──────────────────────────────────┤
│  [Annulla]          [Salva]      │
└──────────────────────────────────┘
```

I campi si adattano dinamicamente:
- `codice` e `codice_interno` mostrati se presenti nella risposta
- `attivo` mostrato se presente nella risposta
- `descrizione` sempre presente e obbligatorio

**Prerequisiti:** BE-1
**Effort:** 1 sessione

#### FE-3 — ConfigTablePanel.vue

File: `frontend/src/core/components/ConfigTablePanel.vue`

Componente principale — due colonne:
- Sinistra: lista tabelle raggruppate per schema, filtrabile
- Destra: DataTable della tabella selezionata + NewButton

Quando l'utente clicca una tabella:
1. Carica i dati via `GET /core/lookup/codici/?rel=<rel>`
2. Mostra la DataTable a destra
3. Click riga → apre il drawer (generico o dedicato in base al registro)
4. Click Nuovo → apre il drawer in create

**Prerequisiti:** FE-1, FE-2
**Effort:** 1-2 sessioni

### Fase 3 — Vista e navigazione

#### FE-4 — ConfigView.vue

File: `frontend/src/config/views/ConfigView.vue` (nuovo dominio frontend)

Vista che wrappa `ConfigTablePanel` in `app-page`.

**Navigazione:**
- Dominio `config` nella sidebar (oggi e' placeholder)
- Voce menu L2: `tabelle` → `/config/tabelle`
- `DOMAIN_MENUS['config']` aggiornato

```js
'config': [
  { key: 'tabelle', icon: 'pi pi-table', to: '/config/tabelle' }
]
```

**Prerequisiti:** FE-3
**Effort:** 30 minuti

### Fase 4 — Drawer dedicati (solo quelli necessari)

#### FE-5 — FormeGiuridicheDrawer.vue

Drawer con campi specifici: descrizione, codice, stato (select), rea_policy (select),
capitale_sociale_policy (select), attivo (toggle), meta (JSON editor o nascosto).

**Prerequisiti:** FE-3
**Effort:** 1 sessione

#### FE-6 — Altri drawer dedicati (se/quando servono)

`TipiSoggettoDettaglioDrawer`, `UnitaOrganizzativeDrawer` — da fare solo quando
si tocca la gestione specifica. Non bloccare il pannello per questi.

---

## Ordine di esecuzione

```
Passo  Task                                          Prerequisiti    Stato
─────  ────────────────────────────────────────────   ────────────    ──────
 1.1   BE-1  Metadata via information_schema         nessuno         DA FARE
 1.2   BE-2  Endpoint CRUD generico config           BE-1            DA FARE
 2.1   FE-1  Registro tabelle config                 —               DA FARE
 2.2   FE-2  GenericConfigDrawer (dinamico)          BE-2            DA FARE
 2.3   FE-3  ConfigTablePanel                        FE-1, FE-2      DA FARE
 3.1   FE-4  ConfigView + navigazione                FE-3            DA FARE
 4.1   FE-5  FormeGiuridicheDrawer (dedicato)        FE-3            DA FARE
 4.2   FE-6  Programma gestione (admin)              FE-3            DA FARE
 4.3   FE-7  Altri drawer dedicati                   quando serve    FUTURO
```

---

## Vantaggi

1. **Zero componenti per tabelle semplici** — un GenericConfigDrawer per ~60 tabelle
2. **Aggiungere una tabella = una riga** nel registro + una riga nella whitelist
3. **Pattern AS/400 collaudato** — lista navigabile, click → modifica
4. **Dominio config finalmente operativo** — non piu' placeholder nella sidebar
5. **Prerequisito naturale per soggetti** — forme giuridiche, tipi contatti, ecc. gestibili prima di iniziare

---

## Relazione con sviluppo-soggetti.md

Il pannello Config sostituisce la **Fase 0** del documento soggetti.
Invece di creare tab/drawer separati per forme giuridiche e altre config,
tutto converge nel pannello unico.

I soggetti partono dalla **Fase 1** (building block form) con le tabelle
config gia' gestibili dal pannello.

---

*Pannello Config — ZeroERP (15 marzo 2026)*
*Sviluppo Concentrico — Anello 0/1, infrastruttura config*
