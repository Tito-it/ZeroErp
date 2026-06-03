# Piano — Lista offerte commerciali configurabile (DEF-8, gemello contratti/preventivi)

> **Branch lavoro**: `dev/backend-tid` (BE/FE) + lavoro DB → `dev/db-tid`.
> **Natura**: piano operativo auto-sufficiente (NON serve brief DB separato — questo
> documento è la specifica). Le azioni DB le esegue il team DB (memoria
> `feedback_db_actions_passaggio_team`); BE/FE attendono la consegna DB
> (`feedback_be_fe_attende_prerequisiti_db`).
> **Origine**: richiesta Tid 2026-06-03 — «genera lista-offerte-comm.md con la
> stessa logica» della lista preventivi.
> **Template 1:1**: [refactor-lista-contratti.md](../work-done/refactor-lista-contratti.md)
> (DEF-8, atterrato) + [lista-preventivi.md](lista-preventivi.md) (piano gemello,
> stesse decisioni di principio ratificate).

---

## 0. Obiettivo in una frase

Portare la lista offerte commerciali **dentro il sistema liste configurabili**
(`<ListaConfigurabile codice="vendite.offerte">`) con ritiro dinamico colonne
(anti-scrollbar sidebar), personalizzazione colonne per utente, export CSV/XLSX —
**preservando 1:1 le 11 colonne e tutte le funzionalità** dell'elenco attuale
(filtri stato/utility/data, toggle «mostra storico revisioni», azioni di riga
PDF + note, Tag stato + **badge «scaduta»**, colonna **listino con suffisso
versione**).

Terzo dominio vendite migrato a DEF-8 (dopo contratti e preventivi): **regola del
2** (memoria `feedback_regola_del_2_estrai_bb`) pienamente applicata — building
block riusati senza duplicare (`useListaConfigurabilePage`, `CellaConfigurabile`,
`ListaConfigurabile`, `export_helpers`, `ListaExportService`). Con tre liste
gemelle, attenzione a eventuali pattern di toolbar/filtro da estrarre se emerge
una terza copia identica (es. toolbar «stato + utility + data + storico» comune a
preventivi/offerte → candidato BB se Tid conferma).

---

## 1. Standard e building block governanti (vincolanti)

Identici a [lista-preventivi.md §1](lista-preventivi.md) — non si ripetono per
intero. In sintesi:

- **Backend** — [api.md](../../api.md): `DomainAPIView`, `parse_list_params`,
  `success_response`+`paginated_envelope`, tiebreaker `id`, `is_search_endpoint`,
  scope `get_scope_user_id`→`fn_get_emittenti_scope_pk_ids`, `ServiceError`,
  export via `apps.ui.api.export_helpers` + `ListaExportService` (param `formato`,
  mai `format` — memoria `feedback_drf_format_magic_param`),
  `UiService.get_lista_config` (memoria `feedback_export_lista_rispetta_preferenza`).
- **Frontend** — [frontend-standards.md](../../frontend/frontend-standards.md):
  toolbar UNICA caller (memoria `feedback_lista_pattern_standard`),
  `useResponsiveColumns` (ritiro dinamico, deroga ResizeObserver — ereditato da
  `<ListaConfigurabile>`), `RowActionsMenu` (memoria `feedback_row_actions_menu`),
  `CellaConfigurabile` (formatter built-in `date_short`/`currency_eur`),
  `PageActionsBar`, `ExportDialog`, `ReadonlyBadge`, `AccessoBloccatoPanel`,
  `LookupSelect`, `UtilityPerRuoloSelect`. i18n via `$t()`.

---

## 2. Invariante NON-NEGOZIABILE — zero perdita

La lista attuale ([OfferteSearchTable.vue](../../../../frontend/src/vendite/offerte/components/OfferteSearchTable.vue))
mostra **11 colonne + azioni**. Vanno preservate nell'ordine attuale, stesso
rendering:

| # | Colonna a video oggi | Campo payload attuale | Rendering attuale |
| - | --- | --- | --- |
| 1 | Codice | `codice` | testo, sortable |
| 2 | Rev | `revisione_numero` | testo (non sortable) |
| 3 | Cliente | `billing_account_display` (= `cliente_denominazione`) | testo, sortable |
| 4 | Cd. Account | `ba_codice` | testo, sortable |
| 5 | Id. Fiscale | `id_fiscale` | testo |
| 6 | Utility | `utility_display` (= `utility_descrizione`) → **`utility_codice`** (uniformato a contratti; descrizione → opt-in) | testo, sortable |
| 7 | Listino | `listino_codice` (+ `· v{listino_versione_codice}`) | **cella composita** |
| 8 | Valido dal | `validita_dal` | `displayDate`, sortable |
| 9 | Valido al | `validita_al` | `displayDate` |
| 10 | Emessa | `data_emissione` | `displayDate`, sortable |
| 11 | Stato | `stato_descrizione` + `stato_codice_interno` + `is_scaduta` | `<Tag>` severity **+ badge «scaduta»** |
| 12 | Azioni | — | `RowActionsMenu` (PDF + note) |

**Funzionalità da preservare oltre alle colonne:**
- Filtro **stato** (`LookupSelect` su `config.stati_doc_offerte`, value-field
  `codice_interno`).
- Filtro **utility** (`UtilityPerRuoloSelect`, `apply-default`).
- Filtro **data Dal/Al** (`data_da` default anno-1 → param `validita_dal_min`,
  `data_a`).
- Toggle **«mostra storico revisioni»** (`solo_attiva` invertito) — FILTRO nella
  toolbar caller, non colonna né config.
- Empty state / `SearchHint` (ereditato).
- Azioni di riga: **PDF** (disabilitato in **BOZZA**) + **gestisci note**.
- Tag stato con `statoOffertaSeverity(stato_codice_interno)`.
- **Badge «scaduta»** (`is_scaduta` + `STATI_OFFERTA_SEGNALA_SCADENZA`).

⚠️ Specificità offerte vs preventivi/contratti (da gestire esplicitamente):
1. Identificatore = **`codice`** (non `numero`); rev = **`revisione_numero`**.
2. Colonna **Listino composita**: `listino_codice` + suffisso `· v{versione}` →
   slot custom `#cell-listino` (la versione resta colonna tecnica nascosta).
3. Stato con **badge scaduta**: slot custom `#cell-stato` rende Tag stato + Tag
   warn condizionale → richiede `stato_codice_interno` + `is_scaduta` nel payload.
4. PDF disabilitato in **BOZZA** (non DRAFT).
5. i18n namespace annidato **`vendite.offerte.*`** (non `offerte.*`).

---

## 3. Workstream DB (lavoro team DB su `dev/db-tid`) — attende delivery

`priorita` (DB-A) **già atterrato** con contratti → serve solo DB-B offerte.

### 3.1 Vista canonica `vendite.vw_offerte_commerciali_lista`

Oggi la lista legge da **`vendite.vw_offerte_commerciali_list`**
([20260528-01](../../../../db/changelog/migrations_v2/20_code/vendite/20260528-01-create-vw-offerte-commerciali-list-mctit.yaml)),
ma con **due limiti** per DEF-8:
- aliasa i nomi canonici (`cliente_denominazione`, `id_fiscale`,
  `billing_account_codice`) — il `campo_sorgente` del catalogo deve combaciare
  col nome **canonico** della colonna in vista (trigger B2);
- **NON espone** `listino_codice`, `listino_versione_codice`, `is_scaduta`,
  oggi derivati a valle nel repository (LEFT JOIN `vendite.listini` + calcolo
  scadenza nel SELECT lista).

**Decisione (coerente con preventivi §7.1, opzione A — soluzione assoluta,
memoria `feedback_no_quick_fix_soluzione_assoluta`):** creare/rinominare in
**`vendite.vw_offerte_commerciali_lista`** (convenzione `vw_<entita>_lista`),
`security_invoker=on`, **self-contained**, che espone senza alias:

- `ragione_sociale_completa` (oggi `cliente_denominazione`)
- `id_fiscale_univoco_cf_piva` (oggi `id_fiscale`)
- `ba_codice` (oggi `billing_account_codice`)
- `stato_descrizione`, `stato_codice_interno`
- **`listino_codice`** (oggi LEFT JOIN repo) + **`listino_versione_codice`**
- **`is_scaduta`** (oggi calcolata nel SELECT lista del repo → spostata in vista)
- più: `codice`, `revisione_numero`, `revisione_padre_id`, `is_attiva`,
  `has_next_revisione`, `utility_codice`, `utility_descrizione`,
  `istanza_utility_codice`, `validita_dal`, `validita_al`, `data_emissione`,
  `data_accettazione`, `data_rifiuto`, `data_annullamento`,
  `valore_variazione_globale`, `tipo_variazione_globale`, `emittente_fiscale_id`,
  `valuta_id`/`valuta_codice` (oggi JOIN extra repo → in vista evita il join),
  `data_insert`, `id`, `uid`, `billing_account_id`.
- Logica soggetto-via-istanza + `is_attiva`/`has_next_revisione` preservata 1:1.

→ Convergenza consumer: `list_offerte` legge dalla vista canonica
self-contained; deprecare `vw_offerte_commerciali_list`. Il detail
(`get_offerta`) usa già `_SELECT_COLS_OFFERTA` proprio (non la vista lista):
impatto limitato alla lista.

### 3.2 Entry `ui.lista_definizione` (seed CSV)

```
id=6, codice='vendite.offerte', descrizione='Offerte commerciali',
schema_dati='vendite', vista_sql='vw_offerte_commerciali_lista', attivo=t
```
(vista prima della definizione — trigger `valida_vista_sql`).

### 3.3 Catalogo colonne `ui.lista_colonna` (lista_id=6) + preset di sistema

Catalogo §4. Seed gemello contratti/preventivi:
- `ui.lista_colonna` — preset + extra opt-in (con `priorita` + `larghezza_default`).
- `ui.lista_preset` — `offerte_default`, `ambito='sistema'`, `is_default=t`,
  `pagina_dimensione=25`, `ordinamento_default=[{"col":"validita_dal","dir":"desc"}]`
  (= default attuale lista, `useSearchTable defaultSortField='validita_dal'`).
- `ui.lista_preset_colonna` — colonne visibili di default (§4 «Preset ✓»); extra
  con `visibile=false`.
- `priorita` seedata via changelog dedicato (pattern `20260602-16`).
- Resync sequenze IDENTITY `ui.*` già risolto da `20260602-17` (`runAlways`).

### 3.4 Lezioni DEF-8
1. Nomi cliente/id.fiscale/ba **canonici** in vista (§3.1).
2. `sensibile=false` su tutte le colonne.
3. Ogni `campo_sorgente` esiste come colonna della vista (trigger B2 + pgTAP) —
   include `listino_codice`, `listino_versione_codice`, `is_scaduta`,
   `stato_codice_interno` (che oggi NON sono in vista).

---

## 4. Catalogo colonne proposto (`vendite.offerte`, lista_id=6)

> `ordine_default` = ordine visivo (= lista attuale 1:1, NON riordinare);
> `priorita` = peso di permanenza nel ritiro dinamico; `largh_def` =
> `larghezza_default` (standard + soglia packing-a-somma).

**Colonne preset (visibili) — set attuale 11 + azioni:**

| ord | codice | campo_sorgente | tipo_colonna | tipo_dato | formato | largh | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | codice | codice | identificatore | string | — | 130 | 100 (max) | Identificazione |
| 20 | revisione_numero | revisione_numero | informazione | integer | — | 60 | 88 | Identificazione |
| 30 | ragione_sociale_completa | ragione_sociale_completa | informazione | string | — | 200 | 95 | Cliente |
| 40 | ba_codice | ba_codice | informazione | string | — | 120 | 40 | Cliente |
| 50 | id_fiscale | id_fiscale_univoco_cf_piva | informazione | string | — | 140 | 75 | Cliente |
| 60 | utility_codice | utility_codice | informazione | string | — | 100 | 70 | Fornitura |
| 70 | listino_codice | listino_codice | informazione | string | — | 140 | 45 | Pricing |
| 80 | validita_dal | validita_dal | informazione | date | date_short | 110 | 65 | Validità |
| 90 | validita_al | validita_al | informazione | date | date_short | 110 | 60 | Validità |
| 100 | data_emissione | data_emissione | informazione | date | date_short | 110 | 50 | Ciclo vita |
| 110 | stato | stato_descrizione | informazione | string | — | 130 | 90 | Stato |
| 120 | azioni | (NULL) | azione | string | — | 60 | 100 (max) | — |

**Colonne tecniche nascoste (preset ✗, servono al FE):**

| ord | codice | campo_sorgente | note |
| --- | --- | --- | --- |
| 130 | stato_codice_interno | stato_codice_interno | severity Tag (`statoOffertaSeverity`); `ordinabile=f` `ricercabile_full=f` |
| 140 | is_scaduta | is_scaduta | badge «scaduta» (slot `#cell-stato`); `tipo_dato=boolean`, `ordinabile=f` |
| 150 | listino_versione_codice | listino_versione_codice | suffisso `· v` (slot `#cell-listino`); `ordinabile=f` |

**Colonne extra opt-in (`visibile=false` nel preset):**

| ord | codice | campo_sorgente | tipo_dato | formato | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- |
| 160 | utility_descrizione | utility_descrizione | string | — | 10 | Fornitura |
| 170 | istanza_utility_codice | istanza_utility_codice | string | — | 35 | Fornitura |
| 180 | tipo_variazione_globale | tipo_variazione_globale | string | — | 15 | Pricing |
| 190 | valore_variazione_globale | valore_variazione_globale | numeric | — | 15 | Pricing |
| 200 | valuta | valuta_codice | string | — | 12 | Pricing |
| 210 | emittente_fiscale_codice | emittente_fiscale_codice | string | — | 15 | Emittente |
| 220 | data_accettazione | data_accettazione | date | date_short | 20 | Ciclo vita |
| 230 | data_rifiuto | data_rifiuto | date | date_short | 18 | Ciclo vita |
| 240 | data_annullamento | data_annullamento | date | date_short | 18 | Ciclo vita |
| 250 | data_insert | data_insert | datetime | datetime_short | 5 | Audit |

**Note di dominio:**
- `codice` = unico `identificatore` (frozen). `revisione_numero` priorità 88,
  non ordinabile (= oggi): `codice`+`rev` identificano la riga nello storico.
- `ricercabile_full=t` su `codice`, `ragione_sociale_completa`, `ba_codice`,
  `id_fiscale`.
- **Listino** reso via slot `#cell-listino` che combina `listino_codice` +
  `· v{listino_versione_codice}` (entrambi dalla stessa riga); la versione resta
  colonna tecnica nascosta.
- **Stato** reso via slot `#cell-stato`: Tag severity + Tag warn «scaduta»
  condizionale (`is_scaduta` && `stato_codice_interno ∈ STATI_OFFERTA_SEGNALA_SCADENZA`).
- Date via formatter built-in `date_short`; nessuna colonna currency in lista.

---

## 5. Workstream Backend (`apps/vendite/` + `apps/ui/`) — attende DB

Gemello `views_contratti.py` / `contratti_repository.py`. **Vantaggio offerte**:
`list_offerte` ha **già** `order_by`/`order_dir` + whitelist `_ORDER_COLS_OFFERTE`
→ meno lavoro del preventivi.

### 5.1 Repository — `offerte_repository.py`
- `list_offerte`: leggere dalla **`vw_offerte_commerciali_lista`** self-contained.
  **⚠️ rename breaking**: rimuovere gli alias `cliente_denominazione AS
  billing_account_display`, `utility_descrizione AS utility_display`,
  `billing_account_codice AS ba_codice`; eliminare i LEFT JOIN `vendite.listini`
  (listino_codice) e `offerte_commerciali`/`config.valute` (valuta) — ora in
  vista. Esporre `is_scaduta`, `listino_versione_codice` dalla vista.
- Aggiornare `_ORDER_COLS_OFFERTE`: chiave display →
  `ragione_sociale_completa`; `utility_*` → `utility_codice`; mantenere
  `codice/validita_dal/validita_al/data_emissione/stato_codice`. **`revisione_numero`
  resta fuori dalla whitelist** (non sortable, = oggi). Tiebreaker `v.id`.

### 5.2 Service — `offerte_service.py`
- `resolve_filtri_export_label(...)` (gemello contratti) per la riga «filtri
  applicati» dell'export.

### 5.3 View/API — `views_offerte.py` + `urls_offerte.py`
- Nuovo endpoint **`ApiOfferteExportView`** →
  `GET /api/v1/vendite/offerte/export/?formato=csv|xlsx` (gemello
  `ApiContrattiExportView`): `DomainAPIView`, `is_search_endpoint=True`,
  `parse_export_format`, `ListaExportService` con `lista_codice='vendite.offerte'`,
  cap `EXPORT_MAX_ROWS`, `build_export_response`. `@extend_schema` su `get`.
- `_LISTA_CODICE_OFFERTE = 'vendite.offerte'`.
- List endpoint esistente: già con `order_by`/`order_dir` — nessuna modifica
  sostanziale (solo coerenza nomi colonne post-rename).

### 5.4 Test BE
- `tests/api/test_offerte_api.py` (creare se assente): export csv/xlsx, cap,
  `formato` magic param, ordinamento whitelist, scope, filtro `solo_attiva`.
  Mock DB (regole CI AGENTS.md). Verde `apps.vendite.tests` + `apps.ui.tests`.

---

## 6. Workstream Frontend (`src/vendite/offerte/`) — attende DB

Migrazione di [OfferteSearchTable.vue](../../../../frontend/src/vendite/offerte/components/OfferteSearchTable.vue)
a `<ListaConfigurabile>`, gemello
[ContrattiSearchTable.vue](../../../../frontend/src/vendite/components/ContrattiSearchTable.vue).

### 6.1 `OfferteSearchTable.vue`
- Sostituire `<DataTable>` grezza (11 `<Column>` con `width:Npx` inline) con
  `<ListaConfigurabile codice="vendite.offerte">`.
- Scaffolding via **`useListaConfigurabilePage(store, {...})`**: `exportFn:
  exportOfferte`, `getExportParams: buildExportParams`, `newTooltipKey:
  'vendite.offerte.nuova_offerta'`, `onNew: () => emit('new')`,
  `searchTableOptions:{ defaultSortField:'validita_dal', defaultSortOrder:'desc' }`.
- **Toolbar caller**: filtri stato/utility/data + **toggle storico** preservati
  1:1; `PageActionsBar` con suffix Tag dirty/salvata + `ReadonlyBadge`.
- **Slot `#cell-listino`**: `listino_codice` + `<span muted>· v{listino_versione_codice}</span>`
  (come oggi, righe 291-296).
- **Slot `#cell-stato`**: `<Tag :severity="statoOffertaSeverity(...)">` + Tag warn
  «scaduta» condizionale (`is_scaduta` && `STATI_OFFERTA_SEGNALA_SCADENZA`).
- **Slot `#actions`**: `RowActionsMenu` con PDF (disabilitato BOZZA) + note
  (`OffertaNoteDrawer`). `:force-compact`.
- Date via formatter built-in; `revisione_numero` plain.
- `AccessoBloccatoPanel` + `useInjectBlocked` preservati.

### 6.2 API + store FE
- `offerteApi.js`: aggiungere `exportOfferte(params)` →
  `api.get('${BASE}/export/', { params, responseType:'blob' })` (memoria
  `feedback_blob_download_no_useapihandler`: blob fuori da `useApiHandler`).
- `stores/offerte.js`: già con `order_by`/`order_dir`/`solo_attiva`/
  `validita_dal_min` — nessuna modifica strutturale (solo coerenza).

### 6.3 i18n
- Chiavi colonne `vendite.offerte.col_*` da `etichetta_i18n_key` del catalogo;
  export/dialog da `lista_config.*` + `common.*`. Verificare orfane.

### 6.4 Build FE verde
`./node_modules/.bin/vite build` (via nvm).

---

## 7. Decisioni (allineate a preventivi §7, RATIFICATE 2026-06-03)

1. **Vista → opzione (A)**: `vw_offerte_commerciali_lista` canonica
   self-contained `security_invoker=on`, deprecata `vw_offerte_commerciali_list`.
2. **Utility → `utility_codice`** nel preset (uniformato a contratti);
   `utility_descrizione` extra opt-in.
3. **`revisione_numero` NON ordinabile** (come oggi).
4. **`ba_codice`** nome canonico in vista (da `billing_account_codice`).
5. **[offerte-specifico] Listino composito** `codice · v{versione}` via slot —
   versione = colonna tecnica nascosta. Confermato preservare la resa attuale.
6. **[offerte-specifico] Badge «scaduta»** preservato via slot `#cell-stato` +
   colonna tecnica `is_scaduta` (spostata dal repo alla vista).

---

## 8. Sequenza consigliata

1. ✅ Decisioni §7 (allineate a preventivi).
2. **DB-B offerte**: vista canonica self-contained (incl. `listino_codice`,
   `listino_versione_codice`, `is_scaduta`, nomi canonici) + definizione +
   catalogo lista_id=6 + preset + priorita + pgTAP.
3. **Attendere consegna DB**.
4. **BE** (§5): repository su vista canonica (rimuove JOIN/alias), whitelist
   nomi canonici, export endpoint + test.
5. **FE** (§6): migrazione `OfferteSearchTable.vue` → `<ListaConfigurabile>` +
   slot listino/stato + export + i18n; build verde.
6. **Smoke E2E**: lista carica, filtri (incl. toggle storico), ritiro colonne,
   personalizzazione, export rispetta ordine/visibilità, azioni riga PDF+note,
   Tag stato + badge scaduta, colonna listino+versione.
7. Riepilogo a video + attesa OK Tid (memoria `feedback_memoria_solo_su_richiesta`).

---

## 9. Test (cosa verificare)

- **pgTAP**: vista `vw_offerte_commerciali_lista` espone tutti i `campo_sorgente`
  del catalogo (incl. `listino_codice`, `listino_versione_codice`, `is_scaduta`,
  `stato_codice_interno`); `lista_definizione` `vendite.offerte` risolve via
  `fn_resolve_lista_config`; preset di sistema ritorna le 11 colonne visibili
  nell'ordine atteso + tecniche nascoste; extra opt-in `visibile=false`; nessuna
  colonna filtrata per SUPER_ADMIN (`sensibile=false`).
- **BE Django**: export csv/xlsx, cap, magic param `formato`, ordinamento
  whitelist, scope emittente, filtro `solo_attiva`, `is_scaduta` corretto.
- **FE**: build verde + smoke §8.6.

---

## 10. Stato famiglia liste vendite DEF-8

| Lista | Stato | Doc |
| --- | --- | --- |
| `vendite.contratti` | ✅ atterrato (commit `1cc906377`) | [refactor-lista-contratti.md](../work-done/refactor-lista-contratti.md) |
| `vendite.preventivi` | 📋 piano pronto, decisioni ratificate | [lista-preventivi.md](lista-preventivi.md) |
| `vendite.offerte` | 📋 piano pronto (questo doc) | — |
