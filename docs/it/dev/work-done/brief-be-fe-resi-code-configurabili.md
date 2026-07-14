# Brief BE+FE — Code resi (da accreditare / da ri-consegnare) → liste configurabili

> **Tipo**: brief implementativo BE+FE · **Data**: 2026-07-14 · **Owner**: Tid
> **Stato**: ☐ DA REALIZZARE — **BLOCCATO su prerequisito DB**
> **Prerequisito DB**: [brief-db-seed-lista-code-resi.md](brief-db-seed-lista-code-resi.md)
> (due liste config `ui` sulle viste esistenti `vw_resi_da_accreditare` /
> `vw_resi_da_riconsegnare`). Finché i due `codice` lista non esistono a runtime,
> personalizzazione ed export non sono realizzabili né testabili.
> **Movente**: le tab "da accreditare" e "da ri-consegnare" di
> [ResiView](../../../../frontend/src/vendite/resi/views/ResiView.vue) sono `DataTable`
> raw a colonne fisse (componente [ResiCodaTable](../../../../frontend/src/vendite/resi/components/ResiCodaTable.vue)):
> mancano personalizzazione colonne + download, presenti nelle liste standard.
> **Già fatto (fuori-brief, FE puro)**: paginatore delle due code portato in alto
> (`paginator-position="top"`) — allineato alle liste dash/coda.

---

## 0. Perimetro e decisione di fondo

Le due code sono oggi liste di **righe reso** (non documenti), servite da viste dedicate,
e per questo erano state escluse da `<ListaConfigurabile>`. La richiesta è portarle allo
**standard lista** (personalizzazione + export). Si adotta la **strada (A)**: registrarle
come liste configurabili vere (config DB) e riusare l'intero stack standard
(`ListaConfigurabile` + `useListaConfigurabilePage` + `build_export_response`), **senza**
escape-hatch custom. Motivo: coerenza totale con le altre 8 liste esportabili, zero
codice di export ad-hoc da mantenere.

---

## 1. Backend

Tutto in `apps/vendite`. Le due viste sorgente **esistono già** e non si toccano.

### 1a. Sort server-side sulle code — `db/resi_repository.py`

`_list_coda(vista, ...)` (righe ~400-449) oggi ha `ORDER BY v.data DESC, v.reso_id DESC,
v.resi_riga_id ASC` fisso e cap `LIMIT 200`. Serve:

- parametri `order_by` / `order_dir` con **whitelist** di colonne per vista (le colonne
  ordinabili dichiarate nel seed lista). Fallback al default attuale (`data desc`).
- tie-breaker stabile invariato (`reso_id desc, resi_riga_id asc`) appeso all'`order_by`.
- il cap 200 va parametrizzato: gli endpoint list restano paginati; l'export chiede
  `limit = EXPORT_MAX_ROWS + 1` per intercettare l'overflow (come DDT).

Riusare l'helper di whitelist/ordinamento già usato dal repo resi lista se presente
(coerenza con `list_resi`), altrimenti una whitelist locale per le due viste.

### 1b. Search full-text (opzionale, se il seed marca colonne `ricercabile_full`)

Se il brief DB marca `destinatario_denominazione` / `descrizione` / `ddt_numero`
ricercabili, aggiungere a `_list_coda` un filtro `search` ILIKE su quelle colonne (mirror
di `list_resi`). Se il DB le lascia non-ricercabili in questa iterazione, **omettere** la
search e non esporre il campo a FE (niente search box sulle code).

### 1c. Service — `services/resi_service.py`

`list_da_accreditare` / `list_da_riconsegnare` (righe 185-222): aggiungere passthrough di
`order_by`, `order_dir` (+ `search` se 1b), mantenendo i default.

### 1d. View list — `api/views_resi.py`

`ApiResiDaAccreditare` / `ApiResiDaRiconsegnare` (righe 95-162): aggiungere ai parametri
`order_by` / `order_dir` (+ `search` se 1b) via `parse_list_params` (già usato) e
inoltrarli al service. `_extract_coda_filters` resta invariato.

### 1e. View export (nuove) — `api/views_resi.py`

Due nuove view sul modello di `ApiDdtExportView` ([views_ddt.py:98-158](../../../../backend/apps/vendite/api/views_ddt.py)):

- `ApiResiDaAccreditareExport` → `GET /vendite/resi/da-accreditare/export/?formato=csv|xlsx`
- `ApiResiDaRiconsegnareExport` → `GET /vendite/resi/da-riconsegnare/export/?formato=csv|xlsx`

Ognuna: `parse_export_format` → `parse_list_params` + `_extract_coda_filters` → service
con `limit=EXPORT_MAX_ROWS+1, offset=0` → `build_export_response(request,
lista_codice=<codice DB della coda>, results, total, filtri_applicati, fmt)`.
`filtri_applicati`: etichette dei filtri coda (billing_account, data_da/al) — piccolo helper
`resolve_filtri_export_label` per le code (mirror ridotto DDT, senza stato/utility).

Costanti `_LISTA_CODICE_RESI_DA_ACCREDITARE` / `_..._DA_RICONSEGNARE` = i due `codice`
comunicati dal team DB.

### 1f. Routing — `api/urls_resi.py`

Aggiungere, prima di `<int:reso_id>/`:

```
path("da-accreditare/export/", ApiResiDaAccreditareExport.as_view(), name="...-da-accreditare-export"),
path("da-riconsegnare/export/", ApiResiDaRiconsegnareExport.as_view(), name="...-da-riconsegnare-export"),
```

### 1g. Test BE

Mirror dei test export DDT/ordini: export CSV/XLSX 200 + Content-Disposition, guard
`E_UI_EXPORT_LIMIT_EXCEEDED` oltre soglia, `E_UI_EXPORT_FORMAT_INVALID`, sort per colonna
whitelisted, scope emittente rispettato.

---

## 2. Frontend

### 2a. API — `resi/api/resiApi.js`

Aggiungere `exportDaAccreditare(params)` / `exportDaRiconsegnare(params)` (GET blob,
`responseType: 'blob'`, `params` con `formato` + filtri). `listDaAccreditare` /
`listDaRiconsegnare` accettano già `params`: passare `order_by/order_dir` (+ `search`).

### 2b. Stato lista configurabile per coda

Le code oggi usano `usePagedDashFetch` con stato locale al componente. Per lo standard
`ListaConfigurabile` serve lo scaffolding `useListaConfigurabilePage(store, ...)`, che
richiede uno **store** con `items / totalRecords / loading / filters / fetchList` +
supporto sort/paginazione. Due opzioni:

- **(preferita)** estendere lo `useResiStore` con due sezioni coda basate sul pattern
  lista (filters+order+paginazione, `fetchDaAccreditare` / `fetchDaRiconsegnare`), oppure
  due micro-store dedicati `useResiCodaAccreditareStore` / `...Riconsegnare` con lo stesso
  BB del lista resi. `userScoped: true` obbligatorio (memoria `feedback_pinia_userscoped`).
- riusare `buildDocListParams` per i filtri comuni (data_da default anno-1) — le code
  però non hanno `stato` (filtrato via, come già lato BE).

> **Regola del 2 (memoria `feedback_regola_del_2_estrai_bb`)**: due code quasi identiche →
> valutare un BB `useCodaConfigurabile(codice, fetchPage, exportPage)` che incapsula
> store+scaffolding. **Dichiarare a Tid prima di estrarre**, non anticipare.

### 2c. `ResiCodaTable.vue` → `<ListaConfigurabile>`

Riscrivere il componente sul pattern lista standard (memoria
`feedback_lista_pattern_standard`), mantenendo la prop `coda` che seleziona:
`codice` lista, endpoint fetch/export, colonne slot custom.

- **Toolbar unica esterna** (`app-page-toolbar`) con `PageActionsBar`:
  azioni `refresh` + `personalizza-colonne` (`listaRef.openModal`) + **`export`**
  (menu csv/xlsx). Su touch vanno automaticamente nel kebab.
- `<ListaConfigurabile :codice="..." :rows :total :loading :paginator-options
  :page :sort-field :sort-order @page @sort @row-click @config-loaded>`.
- Slot custom: `#cell-stato_riconsegna` → `<Tag>` con `statoRiconsegnaSeverity` (già
  esistente); `#cell-reso_numero` → fallback `—`; quantità via `formatNumber`, date via
  `displayDate` (o lasciare che il formato colonna DB `date_short` le gestisca).
- `@row-click` → `emit('apri-reso', data.reso_id)` (ListaConfigurabile emette `data`).
- Empty-state onesto (`loaded`) invariato nella sostanza.

### 2d. Export FE (download blob)

Bottone export → chiamata `exportDa*` **bypassando `useApiHandler`** (rompe i blob →
memoria `feedback_blob_download_no_useapihandler`): scaricare il blob, `Content-Disposition`
per filename, toast manuali su errore. L'export rispetta la preferenza colonne dell'utente
lato BE (memoria `feedback_export_lista_rispetta_preferenza`): il FE non filtra colonne.

### 2e. i18n

Aggiungere le chiavi `vendite.resi.col_*` delle nuove colonne coda (mirror etichette DB)
nel blocco `vendite.resi.*`, IT + EN. Le etichette azione/export riusano `common.*` /
`lista_config.*` esistenti.

### 2f. Verifica in-app

Giro completo: coda popolata → personalizza colonne (mostra/nascondi, riordina, persistenza
preferenza) → export CSV e XLSX (colonne = preferenza, filtri in metadato) → sort per
colonna → click riga apre il reso. Su entrambe le code. Paginatore in alto (già fatto).

---

## 3. Sequenza consigliata

1. **DB** (prerequisito): brief-db-seed-lista-code-resi.md → ottenere i due `codice` lista.
2. **BE**: sort/search + 2 export view + urls + test.
3. **FE**: store/scaffolding coda → riscrittura `ResiCodaTable` a `ListaConfigurabile` +
   export + i18n.
4. **Verifica in-app** e review (BE+FE) come da standard slice resi.

## 4. Avanzamento

| # | Step | Stato |
|---|---|---|
| 0 | Paginatore code → top | ✅ (FE, fuori-brief) |
| 1 | DB: 2 liste config (brief companion) | ☐ blocca 2-3 |
| 2 | BE: sort/search code + 2 export + urls + test | ☐ |
| 3 | FE: store coda + `ResiCodaTable`→`ListaConfigurabile` + export + i18n | ☐ |
| 4 | Verifica in-app + review | ☐ |
