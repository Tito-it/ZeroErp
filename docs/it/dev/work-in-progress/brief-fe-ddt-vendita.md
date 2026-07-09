# Brief FE — DDT vendita: lista, drawer, evasione da ordine (gemello ordini)

> **Tipo**: brief frontend (target `dev/backend-tid`) · **Data**: 2026-07-09 · **Owner**: Tid
> **Design-of-record**: [analisi-ddt-vendita-stato-e-sviluppi.md](analisi-ddt-vendita-stato-e-sviluppi.md)
> · **Prerequisiti**: [brief DB](brief-db-ddt-vendita-evasione-e-stati.md) + [brief BE](brief-be-ddt-vendita.md) applicati.
> **Principio guida (D-4)**: **clonare `frontend/src/vendite/ordini/`** — il
> sotto-dominio più moderno e auto-contenuto; stessa impronta, logica DDT diversa.
> Riuso massimo dei BB, mai varianti locali ([[feedback_lista_pattern_standard]],
> [[feedback_vue_reuse]]).

---

## 1. Scopo

Nuova feature FE DDT vendita: **lista personalizzabile** + **drawer master-detail**
(testata trasporto + righe + componenti BoM + note) + **azione "genera DDT" nel drawer
ordine** (evasione) + navigazione. Nessuna logica di business nel FE: solo
presentazione, `available_actions` data-driven dal BE.

## 2. Nuovo dominio — clonare `vendite/ordini/` → `vendite/ddt/`

| Nuovo file `frontend/src/vendite/ddt/` | Clona da (ordini) | Differenze |
|---|---|---|
| `views/DdtView.vue` | `views/OrdiniView.vue` | host: `DdtSearchTable` + `DdtDrawer`, `useReadonlyMode(VENDITE, DDT)` |
| `stores/ddt.js` | `stores/ordini.js` | `defineStore('vendite-ddt', …, {userScoped:true})`; +azioni `emetti`, `cambiaStato`, `push`, `generaDaOrdine` no (sta nel dominio ordine) |
| `api/ddtApi.js` | `api/ordiniApi.js` | `BASE='/vendite/ddt'`; `makeComponentiBomApi(BASE)` |
| `constants.js` | `constants.js` | `STATO_DDT` (DRAFT/EMESSO/SPEDITO/CONSEGNATO/RESO/ANNULLATO), `STATI_DDT_CON_DOCUMENTO` |
| `components/DdtSearchTable.vue` | `OrdiniSearchTable.vue` | §3 |
| `components/DdtDrawer.vue` | `OrdiniDrawer.vue` | §4 |
| `components/DdtForm.vue` | `OrdiniForm.vue` | +campi trasporto (causale, aspetto, vettore, porto, colli/pesi, tracking) |
| `components/DdtRigheTable.vue` | `OrdiniRigheTable.vue` | wrapper su `RigheMasterDetailTable` |
| `components/DdtRigaForm.vue` | `OrdiniRigaForm.vue` | riga: articolo/UoM/qta/prezzo/sconto/IVA + componenti |
| `components/DdtRigaComponentiPanel.vue` | `OrdiniRigaComponentiPanel.vue` | wrapper su `_shared/componenti/ComponentiPanel.vue` (già ddt-ready) |
| `components/DdtNoteDrawer.vue` | `OrdineNoteDrawer.vue` | `VenditeNoteDrawer dominio="ddt"` |
| `components/dialogs/DdtEmissioneDialog.vue` | `OrdineEmissioneDialog.vue` | DRAFT→EMESSO (assegna numero); PDF **predisposto ma non attivo** (D-3) |
| `components/DdtIndirizziPanel.vue` (**nuovo**) | — (nessun gemello ordini) | §4, rimandabile a slice standalone |

## 3. Lista — `DdtSearchTable.vue`

`<ListaConfigurabile codice="vendite.ddt" …>` + scaffolding
`useListaConfigurabilePage(store, { exportFn: exportDdt, getExportParams,
newTooltipKey:'vendite.ddt.nuovo_ddt', onNew, searchTableOptions:{defaultSortField:'data',
defaultSortOrder:'desc'} })`. Filtri via `useStoreFilterBindings(store, applyFilters)`.

Toolbar: `InputText` search + **`LookupSelect rel="config.stati_doc_ddt"
value-field="codice_interno"`** (config table **già registrata** in
`core/config-tables.js:33`) + `UtilityPerRuoloSelect` cliente + 2× `DatePicker`
(`data_da`/`data_a`) + `PageActionsBar` (reload/personalizza/export/**new**) con
`#suffix` = `ListaConfigStatusTag` + `ReadonlyBadge`.

Colonne dal BE (via `codice`); slot custom: `#cell-stato` (Tag +
**`statoDdtSeverity`** nuovo, vedi §7) e `#cell-numero` (mostra "—" se DRAFT: **numero
assegnato solo a EMESSO**, C6). `buildRowActions`: "Gestisci note" (`DdtNoteDrawer`) +
"Documenti PDF" (**disabilitato in questa slice**, D-3). Auto-load al mount
(`data_da` default conta come filtro attivo). `useTabFreshness(store, TAB_ENTITIES.DDT)`.

## 4. Drawer — `DdtDrawer.vue`

`<Drawer position="right" :style="{width: DRAWER_WIDTH.WIDE_PLUS}">`. Struttura mirror ordini:

- `#header`: `DrawerTitle :icon="NAV_ICONS.DDT"`.
- `DrawerEntityHeader`: Tag numero (o "—" in DRAFT), data, **chip provenienza**
  (`sorgente` ordine: link all'ordine origine), `#status` = Tag stato +`statoDdtSeverity`.
- `DrawerActionsBar` (azioni data-driven, §5) con `#suffix` = `EntityPdfButton`
  (**predisposto, nascosto** finché PDF non attivo).
- `DdtForm` (testata + campi trasporto), montata su `contentReady` (`useDrawerContentReady`).
- `DdtRigheTable` (se `hasDetail`) `@changed="loadDetail()"` `@form-aperto`.
- `RiepilogoIvaTable` se righe IVA.
- **`DdtIndirizziPanel`** (nuovo) — sezione indirizzi spedizione/destinatario/vettore
  con snapshot. Per la slice **da-ordine** può essere read-only (snapshot ereditato);
  editing pieno rimandabile a standalone/PDF. Confermare con BE §11.
- `FormFooter` save/cancel o close-only. Fuori Drawer: `DdtNoteDrawer` + `DdtEmissioneDialog`.

Righe master-detail: `DdtRigheTable` = wrapper su `core/components/RigheMasterDetailTable.vue`
(slot `#columns` + `#form` con `DdtRigaForm`); `DdtRigaForm` usa
`_shared/righe/useRigaArticoloComposito.js`. Pannello componenti: `_shared/componenti/*`
(già cita "ddt" tra le 4 sorgenti) via `DdtRigaComponentiPanel` con
`makeComponentiBomApi('/vendite/ddt')` + `:tab-entity="TAB_ENTITIES.DDT"`.

Composable core riusati (invariati): `useApiHandler`, `useNotify`, `useConfirmAction`,
`useDrawerClose`, `useDrawerDetailLoad`, `useDrawerContentReady`,
`useDrawerAutosaveBozza` (auto-save BOZZA), `useEntityCapabilities`,
`useEmittenteFiscaleField`, `useUtilityDefaultId`.

## 5. Azioni data-driven (`available_actions`)

Identico a ordini, cambia solo il dispatch:
`useEntityCapabilities(detail, {editFlag:'can_edit_testata'})` →
`mapAvailableActionsToDrawerActions({availableActions, t, onAction, readonly})` →
`DrawerActionsBar` (`kind:'state'`). label/icona/severity **arrivano dal BE**
(`fn_available_actions_ddt` proietta `meta.ui` di `config.transizioni_stati_ddt`).
`onAction(action)` smista per `action.key`:
- `emetti` → apre `DdtEmissioneDialog` (DRAFT→EMESSO, assegna numero);
- `push_commessa` → confirm + `store.push(id)`;
- `spedisci`/`consegna`/`reso`/`annulla` → `store.cambiaStato(id, action.target_state)`
  (rispetta `requires_confirm`/`requires_motivazione`).

## 6. Azione "genera DDT da ordine" (evasione) — nel dominio ORDINE

Gemello di "genera ordine da preventivo" (`PreventiviSmistamentoPanel.vue`). Va nel
**drawer ORDINE**, non nel DDT:

- Nuovo `frontend/src/vendite/ordini/components/OrdineEvasionePanel.vue` (clona
  `PreventiviSmistamentoPanel.vue`): `DataTable` delle righe ordine con **residuo per
  riga** (`qta_ordinata − qta_evasa`), selezione multipla + input `qta_da_evadere`,
  `Button` "Genera DDT" (`icon="pi pi-send"`). Su click → `confirmAction({message, onAccept})`.
- All'accept: `generaDdtFromOrdine(ordineId, righe)` (nuovo in `ordiniApi.js` → POST
  `/vendite/ordini/<id>/genera-ddt/` `{righe:[{ordine_riga_id, qta_da_evadere}]}`).
- Risultato `{ddt_id}` → `notify.success('ddt_generato')` +
  `emitDataChanged(TAB_ENTITIES.DDT, ddtId)` (refresha il tab DDT se aperto) + reload
  residui. **Nessun router-push** (come lo smistamento): il DDT nasce DRAFT, si apre dal
  suo tab.
- Nel `OrdiniDrawer.vue`: filtrare via l'azione `genera_ddt` dalla header bar
  (`.filter(a => a.key !== 'genera_ddt')`) per non duplicare il percorso (come i
  preventivi fanno con `genera_ordine`/`push_commessa`), montando invece il pannello nel
  contenuto quando l'ordine è evadibile (trigger SPEDITO/CONSEGNATO + stato CONFERMATO/
  PARZIALMENTE_EVASO).

## 7. Aggiunte ai file core (nuove chiavi)

| File | Aggiunta |
|---|---|
| `core/navigation.js` | voce `{key:'ddt', icon:NAV_ICONS.DDT, to:'/vendite/ddt'}` in `DOMAIN_MENUS.vendite` (dopo `ordini`). `NAV_ICONS.DDT` + CSS `app-nav-icon-ddt` **già esistono** |
| `router/index.js` | rotta `vendite/ddt` → `DdtView.vue`, `meta:{domain:'vendite', menuKey:'ddt'}` |
| `core/constants.js` | `TAB_ENTITIES.DDT`, `READONLY_MODELS.DDT` |
| `core/utils/severity.js` | `statoDdtSeverity` (mirror `statoOrdineSeverity`; mappa DRAFT/EMESSO/SPEDITO/CONSEGNATO/RESO/ANNULLATO) |
| `documenti/constants.js` | `SORGENTE_CODES.DDT = 'DDT_VENDITA'` (per PDF futuro) |
| `locales/it.json` + `en.json` | blocco `vendite.ddt.*` (sotto-chiavi come `vendite.ordini.*`) + `nav_menu.vendite.ddt` |

## 8. i18n

Blocco `vendite.ddt.*` gemello di `vendite.ordini.*`: `titolo/ddt/nuovo_ddt`,
`search_placeholder`, `filtro_*`, `field_*` (testata + trasporto), `section_righe`,
`riga_*`, `componenti_*` (namespace shared già esistente `vendite.componenti.*`),
`emissione_*`, `azione_*`/`conferma_cambio_stato`/`stato_cambiato`, `evasione_*`
(pannello nel drawer ordine), `col_*`. Mai stringhe hardcoded.

## 9. Ordine di lavoro (concentrico)

1. Core (navigation/router/constants/severity/i18n scheletro) + `ddtApi.js` + `ddt.js` store.
2. `DdtSearchTable` (lista) — verificabile appena c'è `vw_ddt_lista` + config lista `vendite.ddt`.
3. `DdtDrawer` + form testata + righe + componenti + note (CRUD standalone).
4. `OrdineEvasionePanel` (genera DDT da ordine) + azioni stato data-driven.
5. Indirizzi + PDF: slice successiva (predisposti header/`EntityPdfButton`/`SORGENTE_CODES.DDT`).

## 10. Punti aperti

- **Config lista `vendite.ddt`** (`ui.lista_definizione` + colonne): serve il seed della
  definizione lista lato DB/config perché `<ListaConfigurabile codice="vendite.ddt">`
  renda le colonne. Coordinare col team DB/UI (gemello `vendite.ordini`).
- **`DdtIndirizziPanel`**: editing pieno vs snapshot read-only nella prima slice (vedi BE §11).
- **PDF**: componenti header (`EntityPdfButton`) montati ma nascosti finché la fase PDF non è attiva (D-3).
</content>
