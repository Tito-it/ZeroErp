# Piano — Lista preventivi configurabile (DEF-8, gemello contratti)

> **Branch lavoro**: `dev/backend-tid` (BE/FE) + brief DB → `dev/db-tid`.
> **Natura**: piano operativo. La **strada implementativa DB** (changeset, ordine
> seed, nomi changelog) la sceglie il team DB nel rispetto del pattern liste già
> rodato (memoria `feedback_db_actions_passaggio_team`).
> **Origine**: richiesta Tid 2026-06-03 — «fare anche la lista preventivi come
> fatto per contratti e renderla configurabile, con la stessa attenzione: nel
> refactor non si devono perdere colonne / funzionalità».
> **Precedente di riferimento (template 1:1)**: lista contratti DEF-8, brief
> [refactor-lista-contratti.md](../work-done/refactor-lista-contratti.md)
> (DB+BE/FE atterrati 2026-06-02/03, commit `1cc906377`).

---

## ✅ Stato DB — ATTERRATO (2026-06-03)

Il **workstream DB (§3) è completato e migrato** su `dev/db-tid`, test pgTAP
verdi. Dettaglio e brief consolidato (preventivi + offerte):
[db-brief-lista-preventivi-offerte.md](../work-done/db-brief-lista-preventivi-offerte.md).

- Vista canonica **`vendite.vw_preventivi_lista`** (`20260603-05`,
  `security_invoker=on`). ⚠️ sorgente **`vendite.vw_preventivi`** (non la tabella):
  `is_revision_attiva` è stata droppata, `is_attiva` è derivata — la vista riusa
  quella derivazione (no logica duplicata).
- Seed `ui.*`: definizione `vendite.preventivi` (lista_id=5), catalogo 21 colonne
  (id 58-78), preset `preventivi_default` (12 visibili + `stato_codice_interno`
  nascosta), `priorita` di dominio (`20260603-07`).
- pgTAP `test-lista-preventivi-seed.sql` 14/14.
- Doc manuale: `manual/vw_preventivi_lista.md` (nuova) + nota deprecazione su
  `manual/vw_preventivi_list.md`.
- Nota correzione vs §4: `rev` seedata `tipo_dato=numeric` (l'ENUM `ui.tipo_dato`
  non ha `integer`).

### ✅ BE + FE ATTERRATI (2026-06-03)

- **BE**: `preventivi_repository.list_preventivi` + `list_revisioni` commutati su
  `vw_preventivi_lista` (nomi canonici, filtro stato su `stato_codice_interno`,
  ricerca su `ragione_sociale_completa`); whitelist `_ORDER_COLS_PREVENTIVI` +
  `order_by`/`order_dir`; split `list_preventivi_rows` (riuso lista+export);
  endpoint `GET /vendite/preventivi/export/` (`ApiPreventiviExportView`, DEF-1) +
  `resolve_filtri_export_label`. Test: `test_preventivi_export_api` 4/4 + suite
  preventivi 129/129 verdi.
- **FE**: `PreventiviList.vue` → `<ListaConfigurabile codice="vendite.preventivi">`
  via `useListaConfigurabilePage`; filtri custom preservati (stato, utility, data,
  **toggle storico revisioni**); slot `#cell-stato` (Tag severity) + `#actions`
  (PDF disabilitato DRAFT + note); totale/date via formatter built-in
  (`currency_eur`/`date_short`). `exportPreventivi` in `preventiviApi.js`. Chiavi
  i18n `preventivi.col_*` aggiunte (it/en). Build FE verde.
- **Drop `vw_preventivi_list` SBLOCCATO**: nessun consumer attivo residuo (solo
  commenti in `permissions_resolver.py`). Resta da creare il changeset di cleanup
  DB (brief §6 ⚠️ NOTA) — azione DB, da passare al team DB.

---

## 0. Obiettivo in una frase

Portare la lista preventivi vendita **dentro il sistema liste configurabili**
(`<ListaConfigurabile codice="vendite.preventivi">`) con ritiro dinamico colonne
(anti-scrollbar all'apertura sidebar), personalizzazione colonne per utente,
export CSV/XLSX — **preservando 1:1 le 12 colonne e tutte le funzionalità
dell'elenco attuale** (filtri stato/utility/data, toggle «mostra storico
revisioni», azioni di riga PDF + note, Tag stato colorato, totale formattato).

Questo è il **secondo** dominio vendite migrato a DEF-8 dopo contratti: vale la
**regola del 2** (memoria `feedback_regola_del_2_estrai_bb`) — i building block
estratti per contratti (`useListaConfigurabilePage`, `CellaConfigurabile`,
`apps.ui.api.export_helpers`, `ListaExportService`) si **riusano senza
duplicare**; se emerge un terzo punto di duplicazione lo si estrae a monte.

---

## 1. Standard e building block governanti (vincolanti)

Il refactor NON inventa pattern: applica quelli già scritti. Riferimenti
obbligatori (CLAUDE.md):

### Backend — [docs/it/dev/api.md](../../api.md)
- §«Base classes per view»: `DomainAPIView` (`area_funzionale='vendite'`).
- §«Endpoint GET / Paginazione»: helper `parse_list_params`, envelope
  `success_response` + `paginated_envelope`; tiebreaker `id` nell'ORDER BY
  (paginazione deterministica).
- §«Ricerca e throttling»: `is_search_endpoint = True` su list + export.
- §«Scope emittente»: `get_scope_user_id(request)` →
  `script.fn_get_emittenti_scope_pk_ids` (PK reale, non sr_id — memoria
  `feedback_emittente_pk_vs_soggetto_ruolo`; già usato da `list_preventivi`).
- §«Tassonomia errori»: `ServiceError`/`ErrorManager`, mai `try/except Exception`
  nelle view.
- Export: helper `apps.ui.api.export_helpers` (`parse_export_format`,
  `build_export_response`) + `apps.ui.services.lista_export_service`
  (`ListaExportService`, `EXPORT_MAX_ROWS`) — DEF-1. Parametro `formato`
  (italiano), MAI `format` (memoria `feedback_drf_format_magic_param`).
- Catalogo BB backend: `UiService.get_lista_config` + `ListaExportService`
  rispettano ordine/visibilità/permessi utente (memoria
  `feedback_export_lista_rispetta_preferenza`).

### Frontend — [frontend-standards.md](../../frontend/frontend-standards.md)
- §«Pattern lista standard» + memoria `feedback_lista_pattern_standard`: toolbar
  UNICA esterna del caller (filtri sx + `PageActionsBar` dx), paginator top.
- §«Ritiro dinamico colonne — `useResponsiveColumns`»: deroga ResizeObserver
  documentata (le media query non vedono la sidebar). Già implementato dentro
  `<ListaConfigurabile>`: ereditato gratis.
- §«Colonna azioni di riga — `RowActionsMenu`»: PDF + note via kebab; modifica =
  click riga (memoria `feedback_row_actions_menu`).
- Building block FE riusati (catalogo BB FE): `ListaConfigurabile`,
  `useListaConfigurabilePage`, `CellaConfigurabile` (formatter built-in
  `currency_eur`/`date_short`/`datetime_short`), `PageActionsBar`,
  `ReadonlyBadge`, `AccessoBloccatoPanel`, `ExportDialog`, `LookupSelect`,
  `UtilityPerRuoloSelect`, `SearchHint`. i18n via `$t()`, mai hardcoded.

### Brief DB di riferimento
- [refactor-lista-contratti.md](../work-done/refactor-lista-contratti.md) §0-bis
  (8 decisioni ratificate) + §3-§4 (vista/catalogo/preset). **Tutte le decisioni
  di principio valgono identiche qui** (priorita globale di catalogo, no
  `larghezza_min`, packing a somma, `sensibile=false`, nomi canonici cliente/
  id.fiscale, vista `security_invoker=on`, convenzione `vw_<entita>_lista`).

---

## 2. Invariante NON-NEGOZIABILE — zero perdita

La lista attuale ([PreventiviList.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviList.vue))
mostra **12 colonne + azioni**. Vanno tutte preservate, **nell'ordine attuale**,
con lo stesso rendering:

| # | Colonna a video oggi | Campo payload attuale | Rendering attuale |
| - | --- | --- | --- |
| 1 | Numero | `numero` | testo, sortable |
| 2 | Rev | `rev` | testo |
| 3 | Data | `data` | `displayDate` |
| 4 | Cliente | `cliente_denominazione` | testo, sortable |
| 5 | Cd. Account (codice bs) | `billing_account_codice` | testo, sortable |
| 6 | Id. Fiscale | `id_fiscale` | testo |
| 7 | Utility | `utility_descrizione` → **`utility_codice`** (uniformato a contratti; descrizione → opt-in) | testo |
| 8 | Cod. Istanza | `istanza_utility_codice` | testo, sortable |
| 9 | Totale | `totale_documento` | `formatCurrency` |
| 10 | Validità | `validita_al` | `displayDate` |
| 11 | Stato | `stato_descrizione` (+ `stato_codice_interno`) | `<Tag>` severity |
| 12 | Azioni | — | `RowActionsMenu` (PDF + note) |

**Funzionalità da preservare oltre alle colonne:**
- Filtro **stato** (`LookupSelect` su `config.stati_doc_preventivi`,
  value-field `codice_interno`).
- Filtro **utility** (`UtilityPerRuoloSelect`, `apply-default`).
- Filtro **data Dal/Al** (`data_da` default anno-1, `data_a`).
- Toggle **«mostra storico revisioni»** (`solo_attiva` invertito) — è un FILTRO,
  resta nella toolbar del caller, NON è una colonna né entra nella config.
- Empty state / `SearchHint` (ereditato).
- Azioni di riga: **PDF** (disabilitato in DRAFT) + **gestisci note** (drawer).
- Tag stato con `statoPreventiveSeverity(stato_codice_interno)`.

⚠️ Differenza chiave vs contratti: il preventivo ha la colonna **`rev`** (numero
revisione) e il toggle **storico revisioni** — pattern assenti in contratti. Non
esistono nel template DEF-8 contratti: vanno gestiti esplicitamente (rev =
colonna ad alta priorità di permanenza; storico = filtro caller).

---

## 3. Workstream DB (brief → team DB su `dev/db-tid`)

Per memoria `feedback_db_actions_passaggio_team` + `feedback_be_fe_attende_prerequisiti_db`:
le azioni DB le esegue il team DB; BE/FE partono **solo** a DB consegnato. DB-A
(attributo `priorita`) **è già atterrato** col refactor contratti → qui serve
solo il workstream **DB-B preventivi**.

### 3.1 Vista sorgente — decisione da ratificare

Oggi la lista legge da **`vendite.vw_preventivi_list`** (esiste già,
[20260502-15](../../../../db/changelog/migrations_v2/20_code/vendite/20260502-15-update-vw-preventivi-list-soggetto-via-istanza-mctit.yaml)),
che però **aliasa** i nomi canonici: `cliente_denominazione` (non
`ragione_sociale_completa`), `id_fiscale` (non `id_fiscale_univoco_cf_piva`). La
lezione DEF-8 (brief contratti §3.4) impone che il `campo_sorgente` del catalogo
combaci col nome **canonico** della colonna in vista (validato dal trigger B2).

**Decisione ratificata §7.1 — opzione (A)** (soluzione assoluta, memoria
`feedback_no_quick_fix_soluzione_assoluta`):
creare la vista canonica **`vendite.vw_preventivi_lista`** (convenzione
ratificata `vw_<entita>_lista`, brief contratti §0-bis #8), `security_invoker=on`,
che espone i nomi **senza alias**:

- `ragione_sociale_completa` (oggi `cliente_denominazione`)
- `id_fiscale_univoco_cf_piva` (oggi `id_fiscale`)
- `stato_descrizione`, `stato_codice_interno` (per Tag severity FE)
- `ba_codice` (oggi `billing_account_codice` — alias legittimo, evita collisione
  `codice`; eccezione `ba_*` ammessa, brief contratti §0-bis #4)
- più: `numero`, `rev`, `data`, `is_attiva` (predicato storico revisioni),
  `utility_codice`, `utility_descrizione`, `istanza_utility_codice`,
  `totale_documento` (+ `totale_imponibile`, `totale_iva`), `validita_dal`,
  `validita_al`, `valuta_codice`, `emittente_fiscale_id`/`_codice`,
  `competenza_mese`, `data_insert`, `billing_account_id`, `id`, `uid`.
- Logica soggetto-via-istanza (1 join, valorizzato anche per prospect) +
  `is_attiva` da preservare 1:1 dalla `vw_preventivi_list` attuale.

**Convergenza consumer (decisione di dominio — vedi §7 Punti aperti):** la
`vw_preventivi_list` attuale è consumata anche da `list_preventivi` (lista),
`list_revisioni` e dal FE detail (`cliente_denominazione`). Due opzioni:
- **(A) Convergere** tutto su `vw_preventivi_lista` canonica e deprecare
  `vw_preventivi_list` (no duplicazione viste; tocca repository + serializer +
  FE detail). **Raccomandata** — niente vista doppia.
- **(B) Creare la nuova vista solo per la lista**, lasciando `vw_preventivi_list`
  per revisioni/detail. Meno churn ora, ma due viste quasi-gemelle (debito).

→ **Scelta (A) ratificata** (§7.1): vista canonica unica, `vw_preventivi_list`
deprecata. `ba.codice` esposto come `ba_codice` (§7.4).

### 3.2 Entry `ui.lista_definizione` (seed CSV)

```
id=5, codice='vendite.preventivi', descrizione='Preventivi',
schema_dati='vendite', vista_sql='vw_preventivi_lista', attivo=t
```
(il trigger `valida_vista_sql` richiede la vista già esistente al momento del seed
→ vista prima della definizione).

### 3.3 Catalogo colonne `ui.lista_colonna` (lista_id=5) + preset di sistema

Catalogo proposto in §4. Seed gemello contratti:
- `ui.lista_colonna` — colonne preset + extra opt-in (con `priorita` valorizzata,
  `larghezza_default` come standard).
- `ui.lista_preset` — `preventivi_default`, `ambito='sistema'`, `is_default=t`,
  `pagina_dimensione=25`, `ordinamento_default=[{"col":"data","dir":"desc"}]`.
- `ui.lista_preset_colonna` — solo le colonne visibili di default (§4 «Preset ✓»);
  le extra restano nel catalogo con `visibile=false` (pool attivabile).
- `priorita` seedata via changelog dedicato (pattern `20260602-16` contratti).
- **Resync sequenze IDENTITY `ui.*`** già risolto a monte da `20260602-17`
  (`runAlways setval`): non si ripresenta.

### 3.4 Lezioni DEF-8 da applicare (brief contratti §3.4)
1. Nomi cliente/id.fiscale **canonici** in vista (vedi §3.1) — il punto che si
   sbaglia ogni volta.
2. `sensibile=false` su tutte le colonne (nessuna restrizione per profilo ora).
3. Ogni `campo_sorgente` deve esistere come colonna della vista (anti-typo,
   trigger B2 + pgTAP).

---

## 4. Catalogo colonne proposto (`vendite.preventivi`, lista_id=5)

> Due assi distinti (brief contratti §4): **`ordine_default`** = ordine visivo
> (= lista attuale 1:1, NON riordinare); **`priorita`** = peso di permanenza nel
> ritiro dinamico (più alto = si ritira per ultima), indipendente dall'ordine.
> `largh_def` = `larghezza_default` (standard, fa anche da soglia packing-a-somma).

**Colonne preset (visibili) — set attuale 12 + azioni:**

| ord | codice | campo_sorgente | tipo_colonna | tipo_dato | formato | largh | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 10 | numero | numero | identificatore | string | — | 130 | 100 (max) | Identificazione |
| 20 | rev | rev | informazione | integer | — | 60 | 88 | Identificazione |
| 30 | data | data | informazione | date | date_short | 110 | 25 | Identificazione |
| 40 | ragione_sociale_completa | ragione_sociale_completa | informazione | string | — | 200 | 95 | Cliente |
| 50 | ba_codice | ba_codice | informazione | string | — | 120 | 40 | Cliente |
| 60 | id_fiscale | id_fiscale_univoco_cf_piva | informazione | string | — | 140 | 75 | Cliente |
| 70 | utility_codice | utility_codice | informazione | string | — | 100 | 70 | Fornitura |
| 80 | istanza_utility_codice | istanza_utility_codice | informazione | string | — | 130 | 55 | Fornitura |
| 90 | totale_documento | totale_documento | informazione | numeric | currency_eur | 130 | 80 | Importi |
| 100 | validita_al | validita_al | informazione | date | date_short | 110 | 60 | Validità |
| 110 | stato | stato_descrizione | informazione | string | — | 120 | 90 | Stato |
| 120 | azioni | (NULL) | azione | string | — | 60 | 100 (max) | — |

**Colonne tecniche nascoste (preset ✗, servono al FE):**

| ord | codice | campo_sorgente | tipo_colonna | note |
| --- | --- | --- | --- | --- |
| 130 | stato_codice_interno | stato_codice_interno | informazione | severity Tag FE (`statoPreventiveSeverity`); `ordinabile=f`, `ricercabile_full=f` |

**Colonne extra opt-in (nel catalogo, `visibile=false` nel preset):**

| ord | codice | campo_sorgente | tipo_dato | formato | priorita | gruppo |
| --- | --- | --- | --- | --- | --- | --- |
| 135 | utility_descrizione | utility_descrizione | string | — | 10 | Fornitura |
| 140 | validita_dal | validita_dal | date | date_short | 20 | Validità |
| 150 | totale_imponibile | totale_imponibile | numeric | currency_eur | 18 | Importi |
| 160 | totale_iva | totale_iva | numeric | currency_eur | 18 | Importi |
| 170 | valuta | valuta_codice | string | — | 12 | Importi |
| 180 | emittente_fiscale_codice | emittente_fiscale_codice | string | — | 15 | Emittente |
| 190 | competenza_mese | competenza_mese | date | date_short | 10 | Validità |
| 200 | data_insert | data_insert | datetime | datetime_short | 5 | Audit |

**Note di dominio (brief contratti §4):**
- `numero` = unico `identificatore` (frozen, non si ritira). `rev` resta
  `informazione` ma con priorità 88 → non si ritira di fatto: `numero`+`rev`
  insieme identificano la riga nello storico revisioni (toggle ON), non vanno mai
  separati a video.
- `ragione_sociale_completa` priorità 95, `stato` 90, `totale` 80 → resistono;
  si ritirano per prime `competenza`/`data` (25) e `ba_codice` (40)…
- `ricercabile_full=t` su: `numero`, `ragione_sociale_completa`, `ba_codice`,
  `id_fiscale` (allineato alla ricerca repo `numero ILIKE OR
  ragione_sociale_completa ILIKE`; valutare estensione a `ba_codice`/`id_fiscale`).
- `stato` + `totale` resi via formatter built-in `CellaConfigurabile`
  (`currency_eur`) e slot custom `#cell-stato` (Tag) nel caller — niente cella
  custom per le date (`date_short` è built-in).

---

## 5. Workstream Backend (`apps/vendite/` + `apps/ui/`) — attende DB

Gemello di `views_contratti.py` / `contratti_repository.py`.

### 5.1 Repository — `preventivi_repository.py::list_preventivi`
- Leggere da **`vw_preventivi_lista`** (vista canonica) invece di
  `vw_preventivi_list`. **⚠️ rename breaking** (brief contratti §0-bis #5):
  `cliente_denominazione`→`ragione_sociale_completa`,
  `id_fiscale`→`id_fiscale_univoco_cf_piva`,
  `billing_account_codice`→`ba_codice`. Vista + consumer BE + FE commutati
  **insieme**.
- Aggiungere **`order_by`/`order_dir`** con whitelist `_ORDER_COLS_PREVENTIVI`
  (gemello `_ORDER_COLS_CONTRATTI`): `numero | data |
  ragione_sociale_completa | ba_codice | utility_codice |
  istanza_utility_codice | totale_documento | validita_al | stato_codice_interno`.
  **`rev` NON ordinabile** (decisione §7.3, = comportamento attuale). Tiebreaker
  `v.id` SEMPRE (frontend-standards «Paginazione deterministica»).
- Preservare la ricerca, lo scope emittente (`fn_get_emittenti_scope_pk_ids`),
  i filtri esistenti (stato, utility, data_da, data_al, `solo_attiva`).

### 5.2 Service — `preventivi_service.py`
- `list_preventivi(...)` passa `order_by`/`order_dir`.
- Aggiungere `resolve_filtri_export_label(...)` (gemello contratti) per la riga
  «filtri applicati» dell'export.

### 5.3 View/API — `preventivi_views.py` + `preventivi_urls.py`
- Nuovo endpoint **`ApiPreventiviExportView`** →
  `GET /api/v1/vendite/preventivi/export/?formato=csv|xlsx` (gemello
  `ApiContrattiExportView`): `DomainAPIView`, `is_search_endpoint=True`,
  `parse_export_format`, `ListaExportService` con `lista_codice='vendite.preventivi'`,
  cap `EXPORT_MAX_ROWS`, `build_export_response`. `@extend_schema` su `get`
  (parametri = stessi del list + `formato`).
- List endpoint esistente: aggiungere `order_by`/`order_dir` a `parse_list_params`
  (default `data`) e propagarli.
- `_LISTA_CODICE_PREVENTIVI = 'vendite.preventivi'`.

### 5.4 Test BE
- `tests/api/test_preventivi_api.py`: estendere per export (csv/xlsx, cap,
  `formato` magic param) + ordinamento whitelist. Mock DB (regole CI AGENTS.md).
- Verde `./manage-test.sh apps.vendite.tests -v 2` + `apps.ui.tests`.

---

## 6. Workstream Frontend (`src/vendite/preventivi/`) — attende DB

Migrazione di [PreventiviList.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviList.vue)
a `<ListaConfigurabile>`, gemello di
[ContrattiSearchTable.vue](../../../../frontend/src/vendite/components/ContrattiSearchTable.vue).

### 6.1 `PreventiviList.vue`
- Sostituire la `<DataTable>` grezza (12 `<Column>` con `width:Npx` inline, che
  violano frontend-standards «Pattern lista») con
  `<ListaConfigurabile codice="vendite.preventivi">`.
- Scaffolding via **`useListaConfigurabilePage(store, {...})`**: `searchText`,
  `onPage/onSort`, `applyFilters`, `paginatorProps`, `tablePage`, `listaRef`,
  `dirty`, `configReady`, `exportDialogVisible`, `onExportConfirm`,
  `onConfigLoaded`, `pageActions`. `exportFn: exportPreventivi`,
  `getExportParams: buildExportParams`, `newTooltipKey: 'preventivi.nuovo_preventivo'`,
  `onNew: () => emit('new')`, `searchTableOptions:{ defaultSortField:'data',
  defaultSortOrder:'desc' }`.
- **Toolbar caller** (UNICA esterna): filtri stato/utility/data + **toggle storico
  revisioni** preservati 1:1; `PageActionsBar` con suffix Tag dirty/salvata
  (`lista_config.stato_temporanea/_salvata`) + `ReadonlyBadge`.
- **Slot `#cell-stato`**: `<Tag :value="data.stato_descrizione"
  :severity="statoPreventiveSeverity(data.stato_codice_interno)" />`.
- **Slot `#actions`**: `RowActionsMenu` con PDF (disabilitato DRAFT via
  `stato_codice_interno`) + gestisci note (`PreventivoNoteDrawer`). `:force-compact`.
- `totale_documento` e date: nessuno slot — formatter built-in `CellaConfigurabile`
  (`currency_eur`, `date_short`). `rev` plain.
- `AccessoBloccatoPanel` + `useInjectBlocked` preservati.

### 6.2 API + store FE
- `preventiviApi.js`: aggiungere `exportPreventivi(params)` →
  `api.get('${BASE}/export/', { params, responseType:'blob' })` (gemello
  `exportContratti`). NB: blob NON passa da `useApiHandler` (memoria
  `feedback_blob_download_no_useapihandler`): gestito da `ExportDialog`/composable.
- `stores/preventivi.js`: aggiungere `order_by`/`order_dir` ai params di
  `fetchList` (oggi ordinamento implicito); preservare `solo_attiva` esplicito.

### 6.3 i18n
- Chiavi colonne `preventivi.col_*` mappate da `etichetta_i18n_key` del catalogo
  (gemello `contratti.col_*`); chiavi export/dialog riusate da `lista_config.*` +
  `common.*`. Verificare assenza orfane.

### 6.4 Build FE verde
`./node_modules/.bin/vite build` (via nvm).

---

## 7. Decisioni RATIFICATE (Tid, 2026-06-03)

1. **Vista → opzione (A) RATIFICATA**: convergenza su `vw_preventivi_lista`
   canonica `security_invoker=on`, **deprecando `vw_preventivi_list`** (no vista
   doppia, memoria `feedback_no_quick_fix_soluzione_assoluta`). Impatta e va
   commutato insieme: `list_preventivi` + `list_revisioni` + serializer/FE detail
   (`cliente_denominazione`→`ragione_sociale_completa`,
   `id_fiscale`→`id_fiscale_univoco_cf_piva`, `billing_account_codice`→`ba_codice`).
2. **Colonna utility → uniformata a contratti (codice)**: preset mostra
   **`utility_codice`** (ord 70, priorità 70); `utility_descrizione` passa a
   **extra opt-in** (ord 135) → zero perdita, l'operatore può riattivarla.
3. **`rev` NON ordinabile**: resta come oggi (fuori dalla whitelist `_ORDER_COLS`).
4. **`ba_codice` rinominato**: il campo vista diventa `ba_codice` (da
   `billing_account_codice`) per uniformità col catalogo contratti; aggiornare i
   consumer FE lista/detail nello stesso lotto del rename (§5.1).

---

## 8. Sequenza consigliata

1. ✅ **Decisioni §7 ratificate** (2026-06-03): vista (A), utility codice, rev
   non ordinabile, rename `ba_codice`.
2. ✅ **DB-B preventivi ATTERRATO (2026-06-03)**: vista canonica
   `vw_preventivi_lista` + definizione + catalogo (id 58-78) + preset + priorita
   + pgTAP 14/14 su `dev/db-tid`. DB-A (`priorita`) già atterrato. Brief:
   [db-brief-lista-preventivi-offerte.md](../work-done/db-brief-lista-preventivi-offerte.md).
3. ✅ **DB consegnato** → BE/FE sbloccati.
4. **BE** (§5): repository su vista canonica + order_by whitelist + export
   endpoint + test. Vista + consumer BE commutati insieme al rename.
5. **FE** (§6): migrazione `PreventiviList.vue` → `<ListaConfigurabile>` + export
   + i18n; build verde.
6. **Smoke E2E**: lista carica, filtri (incl. toggle storico) ok, ritiro colonne
   all'apertura sidebar, personalizzazione colonne, export CSV/XLSX rispetta
   ordine/visibilità, azioni riga PDF+note, Tag stato, totale formattato.
7. Riepilogo a video + attesa OK Tid (memoria `feedback_memoria_solo_su_richiesta`).

---

## 9. Test (cosa verificare)

- **pgTAP**: vista `vw_preventivi_lista` espone tutti i `campo_sorgente` del
  catalogo; `lista_definizione` `vendite.preventivi` risolve via
  `fn_resolve_lista_config`; preset di sistema ritorna le 12 colonne visibili
  nell'ordine atteso + `stato_codice_interno` nascosta; extra opt-in
  `visibile=false`; nessuna colonna filtrata per SUPER_ADMIN (`sensibile=false`).
- **BE Django**: export csv/xlsx, cap righe, magic param `formato`, ordinamento
  whitelist, scope emittente, filtro `solo_attiva`.
- **FE**: build verde + smoke §8.6.
