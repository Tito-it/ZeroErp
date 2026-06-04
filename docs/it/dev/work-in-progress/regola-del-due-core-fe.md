# Regola del 2 — caccia duplicazioni nel dominio Core (frontend)

> **Data analisi:** 2026-06-05
> **Ambito:** **solo frontend** del dominio `core` (`frontend/src/core/`) **+ caccia
> ai BB mancanti** che gli altri domini reinventano e che dovrebbero vivere in core.
> **Profondità:** media
> **Stato:** 🟡 **MAPPATURA (2026-06-05).** Documento di analisi. **Eseguiti finora:**
> ✅ **X1** (`userScoped` 9 store admin) · ✅ **famiglia guard di versione completa: A1**
> (unificazione `useFetchVersion`/`useTokenedFetch`) **+ A2** (4 drawer `fgVersion`) **+
> B3** (`useArticoloUomOptions`) · ✅ **A4** (`AttivoTag`, 26 siti migrati) · ✅ **A3**
> (`EntityFormDrawer`/`EntityFormField` schema-driven, 6 drawer geo come wrapper) · ✅ **D2**
> (rimosso il double-fetch ridondante nei 5 drawer geo) · ✅ **B1** (`GeoSearchTable`, 6
> SearchTable geo come wrapper). Tutto il resto è ancora sola mappatura: per ogni
> candidato vale il protocollo della regola del 2 (`feedback_regola_del_2_estrai_bb`) —
> dichiarare a chat il disegno del BB e attendere l'OK di Tid prima di scrivere codice
> astratto.

Capitolo FE gemello di
[regola-del-due-core-be.md](../work-done/regola-del-due-core-be.md) (che chiudeva la
faccia backend rimandando esplicitamente: *"Il lato FE di core (~54 composable, ~78
componenti) sarà un capitolo separato"*). Anche qui il dominio è particolare: **core
è la casa dei building block**, quindi la regola del 2 ha **due facce**:

1. **`interno_core`** — duplicazioni *dentro* `frontend/src/core/` (due composable, due
   componenti, due util che ripetono lo stesso blocco) → estrazione interna.
2. **`bb_mancante_core`** — un concetto è reinventato *fuori* da core (in
   vendite/catalogo/anagrafiche/amministrazione/config/ui/pratiche/documenti) mentre
   core ha già un cugino simmetrico o è il posto naturale dove dovrebbe vivere →
   **promozione a core**.

## Com'è stata fatta l'analisi

Workflow dinamico, stesso metodo del BE: **7 agenti finder in parallelo**, ciascuno su
un angolo diverso (composable interni, componenti drawer/form interni, componenti
lookup/tabelle/util interni, caccia BB mancanti in vendite, in anagrafiche/catalogo, in
ui/config/amministrazione/pratiche, pattern inline/CSS/i18n trasversali). Hanno prodotto
**41 candidati grezzi**. Dedup per insieme di file coinvolti + categoria → **33
candidati**. Ogni candidato è passato a un **agente "scettico"** che ha aperto i file
alle righe indicate per stabilire se fosse **vera duplicazione di logica** o solo
somiglianza di forma (scaffolding `defineProps`/`useApiHandler`/`<Drawer>+FormFooter`,
struttura `defaultForm()/load()/save()`: convenzioni standard, *non* duplicazione).
Tutti gli agenti avevano in contesto il
[catalogo BB frontend](../frontend/catalogo-building-block-frontend.md) e gli
[standard frontend](../frontend/frontend-standards.md) per non riproporre estrazioni
già fatte.

| Esito | Conteggio |
| --- | --- |
| Candidati grezzi (7 finder) | 41 |
| Verificati (dopo dedup) | 33 |
| **Confermati duplicazione reale / debito** | 29 |
| 🟢 netti (estrazione/adozione, basso rischio) | 4 |
| 🟡 validi con un "ma" (firma da progettare) | 20 |
| ⚠️ scoperte collaterali (BB ignorato, asimmetria, bug latente) | 5 |
| 🔴 scartati come falsa duplicazione | 4 |

> **Nota di metodo.** Come nel BE, lo sweep multi-angolo ha ri-segnalato gli stessi
> concetti da finder diversi: la **famiglia guard-di-versione** (`useFetchVersion` /
> `useTokenedFetch` / token inline) è stata trovata sia dal finder "composable interni"
> sia da quelli "inline trasversali" → consolidata in voci uniche con una nota di
> design. Una coppia aveva un **verdetto da raddrizzare**: l'asimmetria
> `CodiciPostaliDrawer` (D2) è risultata **invertita** rispetto a come l'aveva vista il
> finder (è l'outlier *corretto*, non quello rotto).

---

## ⚠️ Scoperta critica da gestire (bug latente, non solo duplicazione)

> Segnalata in cima per priorità (cfr. `feedback_bug_logici_modello`).

### 🐛 X1. 9 store admin senza `userScoped: true` → leak dati cross-user al cambio account — ✅ FATTO (2026-06-05)

> **Fix applicato.** Aggiunto `{ userScoped: true }` come terzo argomento di
> `defineStore` ai 9 store hand-rolled (`emailAccounts`, `emailTemplates`, `emailLogs`,
> `operatori`, `emittentiFiscali`, `emittentiFiscaliBA`, `tipiRuoloTipiIndirizzo`,
> `reparti`, `utilitiesTipiRuolo`). Verificato che
> [auto-reset.js:38](../../../../frontend/src/core/pinia-plugins/auto-reset.js#L38)
> legge proprio `options.userScoped`; i 9 store inizializzano con refs vuoti e non
> leggono da localStorage all'init → lo snapshot+restore del plugin li riporta allo
> stato vuoto, nessun `clearUserState()` custom necessario. `node --check` + ESLint
> verdi. `categorieClienti`/`categorieClientiListini` già coperti dalla factory. **Nota
> per B17:** su 6 di questi (i migrabili) la riga verrà rimossa quando la factory la
> fornirà — atteso.

`feedback_pinia_userscoped` è esplicita: uno store Pinia con dati utente **deve**
dichiarare `userScoped: true`, altrimenti `autoResetPlugin` non azzera lo stato al
logout e i residui (liste, filtri, dettagli scoped per emittente/utente) vengono mostrati
al **login successivo sullo stesso browser**. Verifica diretta: dei store in
`amministrazione/stores/`, **9 hand-rolled** non lo dichiarano e non passano da una
factory che lo imposti:

- [emailAccounts.js](../../../../frontend/src/amministrazione/stores/emailAccounts.js),
  [emailTemplates.js](../../../../frontend/src/amministrazione/stores/emailTemplates.js),
  [emailLogs.js](../../../../frontend/src/amministrazione/stores/emailLogs.js),
  [operatori.js](../../../../frontend/src/amministrazione/stores/operatori.js),
  [emittentiFiscali.js](../../../../frontend/src/amministrazione/stores/emittentiFiscali.js),
  [emittentiFiscaliBA.js](../../../../frontend/src/amministrazione/stores/emittentiFiscaliBA.js),
  [tipiRuoloTipiIndirizzo.js](../../../../frontend/src/amministrazione/stores/tipiRuoloTipiIndirizzo.js),
  [utilitiesTipiRuolo.js](../../../../frontend/src/amministrazione/stores/utilitiesTipiRuolo.js),
  [reparti.js](../../../../frontend/src/amministrazione/stores/reparti.js)

I gemelli che passano da `createCrud*Store`
([categorieClienti.js](../../../../frontend/src/amministrazione/stores/categorieClienti.js),
[categorieClientiListini.js](../../../../frontend/src/amministrazione/stores/categorieClientiListini.js))
sono **coperti** perché la factory mette `userScoped: true` di default.

**Azione:** fix minimo `{ userScoped: true }` nelle opzioni `defineStore` dei 9 store,
**indipendentemente** dalla migrazione a factory (B17). Priorità ALTA per la privacy del
dato, non solo per il DRY. Emerso come effetto collaterale del candidato store-admin (B17).

---

## 🟢 Candidati puliti — estrazione/adozione consigliata, basso rischio

Occorrenze quasi identiche, differenze trascurabili. Qui la regola del 2 morde nel modo
più netto.

### A1. `useFetchVersion` e `useTokenedFetch` sono **lo stesso BB biforcato** — `interno_core` — 2 file in core — ✅ FATTO (2026-06-05)

> **Unificato su `useFetchVersion`, `useTokenedFetch` eliminato.** Verificato per grep
> che l'unico consumer reale di `useTokenedFetch` era
> [useRigaComponenti.js:56](../../../../frontend/src/core/composables/useRigaComponenti.js#L56)
> → migrato a `const { tag: nextToken, isCurrent, invalidate } = useFetchVersion()`
> (alias `tag`→`nextToken`, semantica identica) + aggiornato import e commento. Il
> doc-comment di `useFetchVersion` è stato **arricchito** per assorbire i due scenari
> (drawer fire-and-forget + switch rapido lookup/preview/list) e i consumer relativi.
> File `useTokenedFetch.js` **rimosso**; nessun riferimento di codice residuo (resta
> solo la nota storica nel doc-comment superstite). Aggiunta **entry canonica** nel
> [catalogo BB FE](../frontend/catalogo-building-block-frontend.md) (prima nessuno dei
> due era censito per nome — l'asimmetria di catalogo segnalata è sanata). `node --check`
> + ESLint verdi. **B3** (`useArticoloUomOptions` token inline) e **A2** (4 drawer
> `fgVersion`) restano da fare: adottano lo stesso `useFetchVersion`, vedi nota di design.

Due composable in `core/composables/` implementano lo **stesso identico** guard a
contatore monotono anti-race (closure non reattiva: `++counter` catturato prima
dell'await, confronto post-await, terzo metodo che bumpa per invalidare). Verificato
bit-per-bit:

| `useTokenedFetch` | `useFetchVersion` |
| --- | --- |
| `let _token = 0` | `let _v = 0` |
| `nextToken() → ++_token` | `tag: () => ++_v` |
| `isCurrent(tk) → tk === _token` | `isCurrent: (t) => t === _v` |
| `invalidate() → _token++` | `invalidate: () => { _v++ }` |

Stessa filosofia esplicita nei commenti (*"non è un ref reattivo, lo decide il caller"*).
Cambiano solo i nomi e lo stile (function declaration vs arrow in object literal).

- [core/composables/useTokenedFetch.js:37-62](../../../../frontend/src/core/composables/useTokenedFetch.js#L37-L62)
- [core/composables/useFetchVersion.js:34-45](../../../../frontend/src/core/composables/useFetchVersion.js#L34-L45)

**Estrazione:** tenere **un solo** composable (`useFetchVersion`), eliminare l'altro.
Consumer reale unico di `useTokenedFetch`:
[useRigaComponenti.js:56](../../../../frontend/src/core/composables/useRigaComponenti.js#L56)
→ alias `const { tag: nextToken, isCurrent, invalidate } = useFetchVersion()`.
**Asimmetria di catalogo da sanare:** *nessuno dei due* è oggi censito per nome nel
[catalogo BB FE](../frontend/catalogo-building-block-frontend.md) → dopo l'unificazione
aggiungere **una** entry canonica + assorbire i doc-comment stantii di `useTokenedFetch`
(la sua lista consumer non è veritiera). **Caso seme** di questa analisi: vedi nota di
design "guard di versione" più sotto.

### A2. Guard `fgVersion` reimplementato inline in 4 drawer ignorando `useFetchVersion` — `bb_mancante_core` — 4 occorrenze — ✅ FATTO (2026-06-05)

> **Adottato `useFetchVersion` nei 4 drawer.** Migrazione 1:1: `let fgVersion = 0` →
> `const fgFv = useFetchVersion()` (`fv` in ContrattiBillingAccountDrawer); `++fgVersion`
> → `fgFv.tag()`; `v === fgVersion` / `v !== fgVersion` → `fgFv.isCurrent(v)` /
> `!fgFv.isCurrent(v)`; `fgVersion++` (close) → `fgFv.invalidate()`. Lo svuotamento di
> `items`/`statoFilter` (ContrattiBillingAccountDrawer) e il reset di `ready`
> (ClienteDrawer) sul ramo close restano caller-side accanto a `invalidate()`, come da
> caveat. Nessun `fgVersion` residuo. ESLint + `vite build` verdi.

Lo stesso meccanismo di A1, ma scritto a mano col nome `fgVersion` in 4 drawer: `let
fgVersion = 0` + `const v = ++fgVersion` prima della fetch + guard `if (v !== fgVersion)
return` su then/catch/finally + `fgVersion++` nel ramo close del `watch(visible)`. È
**esattamente** ciò che la docstring di `useFetchVersion` dichiara di voler centralizzare.

- [anagrafiche/components/SoggettoDrawer.vue:89-100](../../../../frontend/src/anagrafiche/components/SoggettoDrawer.vue#L89-L100), `:223`
- [anagrafiche/components/ClienteDrawer.vue:203-262](../../../../frontend/src/anagrafiche/components/ClienteDrawer.vue#L203-L262)
- [vendite/components/ContrattiBillingAccountDrawer.vue:87-110](../../../../frontend/src/vendite/components/ContrattiBillingAccountDrawer.vue#L87-L110)
- [vendite/components/ContrattoDrawer.vue:296-325](../../../../frontend/src/vendite/components/ContrattoDrawer.vue#L296-L325)

**Adozione (nessun BB nuovo):** `const fv = useFetchVersion()`; `++fgVersion`→`fv.tag()`;
`v === fgVersion`→`fv.isCurrent(t)`; `fgVersion++` (close)→`fv.invalidate()`. Lo
svuotamento di `items`/filtri e il reset di `ready` sul close restano caller-side accanto
a `fv.invalidate()`. BB già adottato da `OffertaDrawer`/`PreventiviDrawer`: questi 4 sono
i ritardatari.

### A3. 6 drawer CRUD geografici quasi identici → drawer schema-driven — `interno_core` — 6 occorrenze — ✅ FATTO (2026-06-05)

> **Scelta di Tid: nuovo componente schema-driven (Opzione A), non estensione di
> `GenericConfigDrawer`** (che è metadata-driven da `information_schema` — data-layer
> incompatibile con store tipizzato + i18n + widget FK). Creati
> [EntityFormDrawer.vue](../../../../frontend/src/core/components/EntityFormDrawer.vue)
> (orchestratore: form/watch/validazione/save guidati da `fields[]`) +
> [EntityFormField.vue](../../../../frontend/src/core/components/EntityFormField.vue)
> (renderer di un campo: `text`/`select`/`autocomplete`/`toggle`, riusato anche dentro i
> gruppi `form-grid-2col`). I 6 drawer geo riscritti come wrapper ~30 righe (stessi
> filename/props/emits → `IndirizziView` invariata). Schema `fields`: `{ name, type,
> labelKey, required?, maxlength?, lookupFn?, placeholderKey?, component?,
> disabledInEdit?, editOnly?, default? }` + gruppi `{ group:true, fields:[…] }`.
> **Comportamento preservato 1:1**, incluse le divergenze reali: ComuneDrawer create-only,
> StatiDrawer gruppo 2-col + width STANDARD, CodiciPostali `ComuneAutocomplete`
> disabled-in-edit, Toponomastica toggle `attivo` editOnly, Province descrizione+sigla
> required. La prop **`refreshOnSave`** parametrizza il post-save: tutti e 6 i drawer geo
> la passano a `false` (vedi **D2**, eseguito subito dopo) → refresh uniforme via
> `useTabFreshness`, niente fetchList ridondante.
> ESLint + `vite build` verdi. Entry aggiunta al
> [catalogo BB FE](../frontend/catalogo-building-block-frontend.md).

I 6 drawer geografici in `core/components/` condividono un blocco sostanziale (~50 righe):
`defineProps{visible,mode,item}` + emits, `useInjectReadonly`, store di dominio,
`watch(visible)` che popola in edit/resetta in create, `handleSave()` con guard sui
required + `execute(create|update)` + `if (result !== null)` emit/close + `fetchList()`,
template `Drawer + DrawerTitle + form-grid + FormFooter`. Le sole varianti (campi del
form, widget FK, validazione) sono **parametrizzabili da uno schema-campi**.

- [ComuneDrawer.vue](../../../../frontend/src/core/components/ComuneDrawer.vue) (create-only),
  [ProvinceDrawer.vue](../../../../frontend/src/core/components/ProvinceDrawer.vue),
  [RegioniDrawer.vue](../../../../frontend/src/core/components/RegioniDrawer.vue),
  [StatiDrawer.vue](../../../../frontend/src/core/components/StatiDrawer.vue),
  [CodiciPostaliDrawer.vue](../../../../frontend/src/core/components/CodiciPostaliDrawer.vue),
  [ToponomasticaDrawer.vue](../../../../frontend/src/core/components/ToponomasticaDrawer.vue)

**Estrazione:** drawer CRUD descrittivo guidato da `fields:[{name,type,required?,
lookupFn?|autocomplete?,disabledInEdit?,editOnly?}]`. **Preferire** l'estensione di
[GenericConfigDrawer.vue](../../../../frontend/src/core/components/GenericConfigDrawer.vue)
con i field-type `select`/`autocomplete`/`toggle` anziché un secondo BG parallelo
`GeoConfigDrawer` (due drawer schema-driven in core sarebbero essi stessi una
micro-duplicazione). ⚠️ La firma deve gestire: `mode` opzionale (Comune create-only),
width/layout per campo (Stati usa `form-grid-2col`), `titleKey`/`icon`/`successKeys`
per-dominio, required multi-campo (Province: descrizione+sigla). **Rischio medium**:
tocca 6 componenti vivi.

### A4. `<Tag>` attivo/inattivo inline ripetuto **24 volte** → `AttivoTag` — `bb_mancante_core` — 24 occorrenze — ✅ FATTO (2026-06-05)

> **Creato `core/components/AttivoTag.vue` + migrati 26 siti.** Componente presentazionale:
> props `active: Boolean` (riceve il booleano già risolto, non il path del campo →
> nessun coupling), `activeLabel`/`inactiveLabel` (default `common.active`/`common.inactive`,
> il caller passa `t(...)` per le famiglie i18n diverse), `inactiveSeverity` (default
> `'warn'`). Migrazione condotta con script Python deterministico (estrazione robusta di
> `value`/`severity` per gestire indentazione + varianti) per i 25 siti standard + edit
> manuale di `ProfileView` (`value` dopo `severity`, ternario dentro `t()`,
> `inactive-severity="secondary"`). Gestite tutte le varianti: label `common.yes/no`,
> `amm.email_*`, `indirizzi.*`, `config_panel.*`, `search.status_*`, `portale.profile.*`;
> severity `danger` (SearchDetailTable) e `secondary` (ProfileView); campo `attivo` /
> `emittente_attivo` / `detail.attivo` / `row.attivo`. Import `Tag` rimosso nei 15 file
> dove restava inutilizzato, tenuto negli 11 con altri `<Tag>`. **Escluso** di proposito
> `EmittentiFiscaliListView:156` perché usa `<Badge>` (elemento visivamente diverso da
> `Tag`) → Badge→Tag sarebbe un cambio estetico, da decidere a parte. Entry aggiunta al
> [catalogo BB FE](../frontend/catalogo-building-block-frontend.md). ESLint + `vite build`
> verdi.

Micro-blocco identico nella colonna stato di liste/drawer:
`<Tag :value="data.attivo ? t('common.active') : t('common.inactive')" :severity="data.attivo ? 'success' : 'warn'" />`.
Grep conferma **24 file** col ternario severity attivo→success/warn. `core/utils/severity.js`
ha la famiglia `statoClienteSeverity`/`statoFornitoreSeverity`/… ma **non** la variante
booleana `attivo`, e non esiste un componente Tag dedicato.

- Campione: [catalogo/ArticoloUomDrawer.vue:342](../../../../frontend/src/catalogo/components/ArticoloUomDrawer.vue#L342),
  [core/ConfigTablePanel.vue:221-223](../../../../frontend/src/core/components/ConfigTablePanel.vue#L221-L223),
  [catalogo/UnitaMisuraSearchTable.vue:106](../../../../frontend/src/catalogo/components/UnitaMisuraSearchTable.vue#L106),
  [vendite/offerte/.../OffertaEccezioniDrawer.vue:649](../../../../frontend/src/vendite/offerte/components/OffertaEccezioniDrawer.vue) +
  ~20 altre (ListiniSearchTable, PromoArticoli, TemplateDocumenti, ui/ListaPreset/ListaColonna/ListaDefinizione,
  Email*ListView, Indirizzi, ConversioniUom, UomTipi, ecc.)

**Promozione:** `core/components/AttivoTag.vue` con props `{ active: Boolean,
activeLabel?, inactiveLabel?, inactiveSeverity? = 'warn' }`. ⚠️ Il componente riceve il
**booleano già risolto** (`active`), non il path del campo (varia: `attivo` /
`emittente_attivo` / `is_active`), per non reintrodurre coupling. Label override per le
famiglie i18n divergenti (`common.active`, `common.yes/no`, `config_panel.attivo`,
`amm.email_attivo`, …); `inactiveSeverity` per i 2 casi `danger`/`secondary`
(SearchDetailTable, ProfileView). In subordine, esporre anche `statoAttivoSeverity(bool)`
in `core/utils/severity.js` per chi vuole solo il colore.

---

## 🟡 Candidati validi ma con un "ma" — possibile, serve attenzione

> Per ognuno il "ma" è una **divergenza reale** che la firma del BB deve assorbire,
> altrimenti l'astrazione diventa prematura/difettosa (cfr. caveat di
> `feedback_regola_del_2_estrai_bb` e `feedback_concentrico_no_yagni`).

### Famiglia "stack geografico" (B1–B2, vedi anche A3/D2)

I 6 oggetti geografici (comuni/province/regioni/stati/codici-postali/toponomastica)
ripetono l'**intero stack** lista→drawer→store. A3 copre i drawer; qui le tabelle e gli
store.

### B1. 6 SearchTable geografiche con schema lista identico — `interno_core` — 6 occorrenze — ✅ FATTO (2026-06-05)

> **Creato `core/components/GeoSearchTable.vue`** (lista "semplice" pre-blocco-D, distinta
> da `useListaConfigurabilePage`). Le 6 SearchTable riscritte come wrapper ~20 righe
> (stessi filename/eventi → `IndirizziView` invariata). Props: `store`, `columns`,
> `searchPlaceholderKey`, `newTooltipKey`, `tabEntity`, `defaultSortField`, `rowClickable`.
> Le 3 divergenze del caveat assorbite: **`rowClickable:false`** per Comuni (no selection/
> row-click); slot scoped **`filters`** (espone `applyFilters`) per il `ComuneAutocomplete`
> di CodiciPostali; slot scoped **`cell-attivo`** per l'`AttivoTag` di Toponomastica.
> **Miglioria inclusa:** usa `reloadAction()` di `useSearchTable` → il bottone reload ora
> ha il **disable-su-lista-vuota** reattivo che le 6 liste prima non avevano. ESLint +
> `vite build` verdi. Entry al [catalogo BB FE](../frontend/catalogo-building-block-frontend.md).

`useSearchTable(store)` + `pageActions` con le **esatte** 2 voci [reload, new] (~18 righe
bit-per-bit identiche) + `useTabFreshness` + `onMounted(fetchList)` + scaffold DataTable
`app-datatable` (~12 attributi identici).

- [ComuniSearchTable.vue](../../../../frontend/src/core/components/ComuniSearchTable.vue),
  [ProvinceSearchTable.vue](../../../../frontend/src/core/components/ProvinceSearchTable.vue),
  [RegioniSearchTable.vue](../../../../frontend/src/core/components/RegioniSearchTable.vue),
  [StatiSearchTable.vue](../../../../frontend/src/core/components/StatiSearchTable.vue),
  [CodiciPostaliSearchTable.vue](../../../../frontend/src/core/components/CodiciPostaliSearchTable.vue),
  [ToponomasticaSearchTable.vue](../../../../frontend/src/core/components/ToponomasticaSearchTable.vue)

**Estrazione:** `GeoSearchTable.vue` (wrapper leggero, distinto da
`useListaConfigurabilePage` che è per le liste "ricche" con `<ListaConfigurabile>`).
⚠️ La firma deve gestire: `rowClickable?` opt-in (Comuni non ha selection/row-click),
filtro extra reattivo di CodiciPostali (slot `filters` + `applyFilters` esposto, non slot
dumb), `bodySlot` per la cella Tag di Toponomastica. **Miglioria collaterale da
includere:** tutte e 6 riscrivono l'oggetto `reload` invece di usare `reloadAction()`
già esportato da `useSearchTable` (che porta in dote il disable su lista vuota, oggi
mancante).

### B2. 6 store Pinia geografici non adottano `createCrudListStore` — `interno_core` — 6 occorrenze

Copie a mano (~80 righe) della shape che
[createCrudListStore.js](../../../../frontend/src/core/stores/createCrudListStore.js) già
astrae (state + `fetchList` + create/update + `emitDataChanged`), già adottata da
clienti/fornitori/soggetti/articoli.

- [anagrafiche/stores/regioni.js](../../../../frontend/src/anagrafiche/stores/regioni.js),
  [province.js](../../../../frontend/src/anagrafiche/stores/province.js),
  [stati.js](../../../../frontend/src/anagrafiche/stores/stati.js),
  [codiciPostali.js](../../../../frontend/src/anagrafiche/stores/codiciPostali.js),
  [comuni.js](../../../../frontend/src/anagrafiche/stores/comuni.js) (solo create),
  [toponomastica.js](../../../../frontend/src/anagrafiche/stores/toponomastica.js)

⚠️ **"ma" bloccante:** le liste geo partono **piene** (`onMounted → fetchList`), mentre la
factory instrada `fetchList` attraverso `useListaEmptyStateFetch` che con search vuota e
senza `gateKeys` lascia la lista **vuota** finché non si digitano ≥3 char. Adottare la
factory AS-IS **regredirebbe l'UX**. Serve **prima** estendere la factory con un flag
`gated: false` (default true) che bypassa il gate empty-state, + rendere `update`
opzionale (per `comuni`). Si lega a B16/B17/B18 (tema convergenza factory). ⚠️ collegato
a **D2** (asimmetria `CodiciPostaliDrawer`).

### B3. `useArticoloUomOptions` reimplementa il token inline invece del BB — `interno_core` — 1 occorrenza (famiglia A1) — ✅ FATTO (2026-06-05)

> **Adottato `useFetchVersion`.** `let _fetchToken = 0` → `const fv = useFetchVersion()`;
> `++_fetchToken` → `fv.tag()`; `tk !== _fetchToken` / `tk === _fetchToken` →
> `!fv.isCurrent(tk)` / `fv.isCurrent(tk)`; `_fetchToken++` (reset) → `fv.invalidate()`.
> La logica **loading per-fetch** (azzeramento eager di `uomOptions`, toggle di
> `uomLoading` solo se la fetch è corrente) è rimasta caller-side come da caveat — il BB
> copre solo il confronto tag/isCurrent/invalidate. Fatto nello stesso changeset di A1/A2.
> ESLint + `vite build` verdi.

Stesso guard token anti-race di A1, cablato a mano in un file che vive **accanto** ai due
BB in `core/composables/`. Il suo commento cita *"Pattern coerente con
PreventiviDrawer._baDefaultsToken"* e la docstring di `useTokenedFetch` lo elenca pure
tra i consumer — ma non importa nulla.

- [core/composables/useArticoloUomOptions.js:43-82](../../../../frontend/src/core/composables/useArticoloUomOptions.js#L43-L82)

**Adozione:** `const fv = useFetchVersion()` (vedi A1). ⚠️ Mantenere caller-side la logica
**loading per-fetch** aggiuntiva (spegne lo spinner solo se la fetch è ancora corrente),
che il BB non copre. Da fare **nello stesso changeset di A1** per non creare un terzo
allineamento. Sotto-soglia da solo (1 occorrenza), ma è parte della famiglia.

### B4. Backbone master-detail sotto-entità soggetto/ruolo ripetuto — `interno_core` — 2 occorrenze (+1 parziale)

`ContattiSoggettoDrawer` e `ContiBancariDrawer` sono **gemelli pieni** (~120 righe):
resolver `apiFor(context)` soggetto/ruolo, `loadXxx()` con split fonte + `sortByFonte`,
stato `formMode` null/new/edit, `onStartNew/Edit/Cancel/Save/Delete` con
`execute()`+emit+reload, lista card con Tag fonte e azioni nascoste se ereditato.

- [core/components/ContattiSoggettoDrawer.vue:43-166](../../../../frontend/src/core/components/ContattiSoggettoDrawer.vue#L43-L166)
- [core/components/ContiBancariDrawer.vue:53-199](../../../../frontend/src/core/components/ContiBancariDrawer.vue#L53-L199)
- [core/components/IndirizziSoggettoDrawer.vue:64-95](../../../../frontend/src/core/components/IndirizziSoggettoDrawer.vue#L64-L95) — **occorrenza parziale**

**Estrazione:** composable `useSoggettoRuoloCollection({ apiMap, context, ownerId,
istanzaUtilityId, fonteKeys, toCreatePayload, toUpdatePayload, confirmDelete? })`.
⚠️ Tre divergenze da parametrizzare: payload builder (Contatti spread inline vs Conti
`toCreatePayload()`), delete (diretto vs `confirmDelete` con `maskIban`), side-effect di
`onStartNew/Edit` (sub-lookup `tipiContatto.load()` vs `ownerName`). **Falso positivo
parziale su `IndirizziSoggettoDrawer`:** condivide solo `apiFor`+`loadList(split)` — il
resto (matrice tipi, mode `replace`, multi-riga) diverge troppo, **non** forzarlo
nell'astrazione. **Rischio medium**, dichiarare a Tid prima.

### B5. Wrapper `<Select>` su lookup statico per codice — 5 copie quasi identiche — `bb_mancante_core` — 5 occorrenze

5 wrapper Select su whitelist statiche di codici condividono ~40 righe di **logica**
identica: `useGlobalLookup(key, fetcher, { transform: r => r.data.data })`, `formatOption`
`"descrizione (codice)"`, `selectedItem = items.find(i => i.codice === modelValue)`,
`onChange` doppio-emit, template `<Select optionValue="codice">` con slot `#option`/`#value`.

- [vendite/TipoVariazioneSelect.vue](../../../../frontend/src/vendite/components/TipoVariazioneSelect.vue),
  [vendite/AmbitoContrattoSelect.vue](../../../../frontend/src/vendite/components/AmbitoContrattoSelect.vue),
  [catalogo/RoundingModeSelect.vue](../../../../frontend/src/catalogo/components/RoundingModeSelect.vue),
  [amministrazione/EmittenteRoundingModeSelect.vue](../../../../frontend/src/amministrazione/components/EmittenteRoundingModeSelect.vue),
  [amministrazione/EmailLogStatoSelect.vue](../../../../frontend/src/amministrazione/components/EmailLogStatoSelect.vue)

**Promozione:** estendere
[LookupSelect.vue](../../../../frontend/src/core/components/LookupSelect.vue) (che già
implementa showCode/formatOption/selectedItem/valueField) con il path "fetcher esterno +
transform custom + value-by-codice". I 5 wrapper diventano one-liner. ⚠️ Tre punti:
`EmailLogStatoSelect` prepende voce "Tutti" (`includeAllOption`/`allLabel`); i placeholder
i18n restano prop del caller; `transform` esposto come prop **preservando** il default
attuale `r.data.data.results` per i ~45 `rel` esistenti. **Rischio medium**: refactor di
un BB core già largamente adottato → testare la non-regressione dei `rel`.

### B6. Rich server-autocomplete: `_display`/refine-hint/utility-reset — 3 copie interne a core — `interno_core` — 3 occorrenze

3 lookup ricchi condividono tre blocchi distinti (non scaffolding): (1) `displayedModel`
computed che ri-inietta `_display` su un modelValue da restore (evita il bug AutoComplete
`[object Object]`), **identico byte-per-byte**; (2) refine-hint
(`totalCount`/`limitShown`/`onResponse` + footer "affina ricerca"), 2 occorrenze; (3)
`watch(utilityId)` reset selezione, 2 occorrenze. Il commento di `IstanzaUtilityLookup`
ammette *"Stesso pattern di BillingAccountLookup"*.

- [core/components/BillingAccountLookup.vue:76-160](../../../../frontend/src/core/components/BillingAccountLookup.vue#L76-L160)
- [core/components/IstanzaUtilityLookup.vue:81-161](../../../../frontend/src/core/components/IstanzaUtilityLookup.vue#L81-L161)
- [core/components/ArticoloLookup.vue:94-115](../../../../frontend/src/core/components/ArticoloLookup.vue#L94-L115)

**Estrazione (DUE composable, non un componente base monolitico):**
`useLookupDisplayModel(modelValueGetter, buildDisplay)` (3 file) +
`useAutocompleteRefineHint()` (2 file). Il `watch(utilityId)` può diventare un terzo
mini-helper ma è il più borderline (esatte 2 occorrenze, ROI basso). ⚠️ **NON** estrarre un
`RichEntityLookup.vue` base: i 3 template option divergono molto e `ArticoloLookup` ha
invece la macchina filtri tri-stato assente negli altri due. **Bonus:** esportare
`buildDisplay` condiviso così i caller vendite (ContrattoRigheDrawer, PromoArticoloDrawer,
VersioneDrawer) smettono di hardcodare inline `${codice} — ${descrizione}`.

### B7. Util-ombra `dateHelpers.js` duplica `date.js` — `interno_core` — 2 moduli (4 file consumer)

[core/utils/dateHelpers.js](../../../../frontend/src/core/utils/dateHelpers.js)
(`isoToLocalDate`/`localDateToIso`) reimplementa la **stessa** conversione locale-safe
ISO↔Date già in [core/utils/date.js](../../../../frontend/src/core/utils/date.js#L48-L73)
(`parseIsoDate`/`toDateString`, ~110 callsite, già a catalogo). `dateHelpers.js` è un
**BB-ombra non documentato** che la regola del 2 avrebbe dovuto prevenire (4 soli
importer: CategoriaClienteListinoDrawer, TemplateAssetDrawer, TemplateVersioniSection,
PromoArticoloDrawer).

**Eliminazione:** ritirare `dateHelpers.js`, re-import da `date.js` (alias 1:1).
⚠️ Sostituzione **direzionale** `dateHelpers → date.js`, mai il contrario: le versioni di
`date.js` sono superset più robusti (`parseIsoDate` ha guard `instanceof Date` + regex
tollerante; `toDateString` gestisce input già-stringa). Nei 4 consumer si passano sempre
Date/null e stringhe date-only → sostituzione sicura.

### B8. Primitiva download Blob duplicata tra `download.js` e `useFileDownload` — `interno_core` — 2 occorrenze

La primitiva blob-to-disk (`createObjectURL` → `<a download>` → click → `revokeObjectURL`,
~8 righe) è in [core/utils/download.js](../../../../frontend/src/core/utils/download.js#L1-L30)
(`downloadBlob`, esportato, 5 consumer documenti) **e** reimplementata privata dentro
[core/composables/useFileDownload.js:205-219](../../../../frontend/src/core/composables/useFileDownload.js#L205-L219)
(`triggerBrowserDownload`, fallback Path-2). Si toccano ma non si conoscono.

**De-duplicazione:** `useFileDownload` importa `downloadBlob` per il Path-2, elimina
`triggerBrowserDownload`. ⚠️ Due delta benigni: revoke delay 1000ms vs 0ms (il 1000ms è
**più** conservativo per l'edge Safari, non una regressione); guard `if (!blob)` e default
filename innocui (il caller passa sempre un filename risolto).

### B9. `PageActionsBar` e `DrawerActionsBar`: ~7 helper JS identici sotto il mirror — `interno_core` — 2 occorrenze

Il mirror è documentato a livello di **template** in frontend-standards (voluto), ma lo
strato **logico** sotto è duplicato: `isActionVisible` (stesso triplo check
visible+hideWhenReadonly+`auth.isActionAllowed`), `isActionDisabled`, `buttonTooltip`,
`runAction`, `menuTooltipText`, `toggleDesktopMenu/CompactMenu`, `menuItems` — identici
riga-per-riga.

- [core/components/PageActionsBar.vue:14-99](../../../../frontend/src/core/components/PageActionsBar.vue#L14-L99)
- [core/components/DrawerActionsBar.vue:61-177](../../../../frontend/src/core/components/DrawerActionsBar.vue#L61-L177)

**Estrazione:** composable `useActionBar(actions, { disabled, menuTooltip,
defaultMenuItemClass, menuLabel })` che espone il motore filtro/dispatch/menu; le due
barre tengono solo i computed di partizionamento per `kind` + il template (legittimamente
diverso). ⚠️ Parametrizzare `defaultMenuItemClass` (Page `app-menu-item-action` vs Drawer
`app-menu-item-manage`) e `menuLabel` (Drawer appende il badge counter `(N)`). Ortogonale
a `useDrawerActions` (che costruisce i dati, non filtra/dispatcha). **Rischio medium.**

### B10. `OrdiniRigheTable` è un clone di `PreventiviRigheTable` (master-detail inline) — `bb_mancante_core` — 2 occorrenze

Clone quasi byte-identico limitatamente alla logica master-detail inline (>40 righe):
`pageActions`, `loadRighe`, `watch(parentId, immediate)`, `onNuovaRiga/onEditRiga/
chiudiForm/onRigaSaved`, `onComponentiChanged` (re-sync `rigaSelezionata`, commento
identico), `onDeleteRiga`, `buildRowActions`, `defineExpose({loadRighe})`, template
DataTable inner + form inline.

- [vendite/ordini/components/OrdiniRigheTable.vue](../../../../frontend/src/vendite/ordini/components/OrdiniRigheTable.vue)
- [vendite/preventivi/components/PreventiviRigheTable.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviRigheTable.vue) (variante "ricca": badge approvazione prezzo + disabled elimina su PENDING)

**Estrazione:** `core/components/RigheMasterDetailTable.vue` con props `rows-loader`,
`parent-id`, `is-modificabile`, `delete-action`, `i18n-prefix`, `columns`,
`delete-disabled-predicate`, slot `#form`. ⚠️ **Non** forzare anche `ContrattoRigheDrawer`
(~1388 righe, terza variante strutturalmente diversa col form embeddato): astrazione
prematura. Lo standard oggi **prescrive** la copia (frontend-standards §"Master-Detail
inline" rimanda a "copiare la struttura"): la duplicazione è addirittura indotta dalla doc.

### B11. `OrdiniRigaForm` è un clone semplificato di `PreventiviRigaForm` — `bb_mancante_core` — 2 occorrenze

~120 righe di "core riga articolo" duplicate: computeds `isEdit`/`isCasoA`/
`isPadreComposito`, `uomLabel`+`caricaUomConPickBase` (byte-identici), `watch(riga)`,
`onArticoloSelect` (autofill iva + reset uom/prezzo + pickBase), `canSave`,
`buildRigaPayload` (branch edit/create + skip-prezzo su composito), `submitRiga/handleSave`,
template articolo/qta/prezzo/sconto/iva/uom. Le differenze (resolver listino, banner L2,
ComponentiDialog CREATE, campo `ordine`) sono **estensioni additive**, non vincoli
divergenti.

- [vendite/ordini/components/OrdiniRigaForm.vue:36-244](../../../../frontend/src/vendite/ordini/components/OrdiniRigaForm.vue#L36-L244)
- [vendite/preventivi/components/PreventiviRigaForm.vue](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue) (superset)

**Estrazione:** composable `useRigaArticoloForm({ store, parentId, riga, … })` che i form
di dominio compongono. Include (non sostituisce) `useArticoloUomOptions` già estratto.
⚠️ **Drift nome campo da segnalare:** ordini `sconto_perc` vs preventivi
`sconto_percentuale` (probabile incoerenza latente). Hook per il bootstrap resolver
(preventivi). **Path consigliato `vendite/_shared/`** (non core): i gemelli
(`useComponentiDialog`, `useLimitiPricing`, `L2ErrorBanner`) vivono già lì, è logica riga
vendite-specifica. **Rischio medium.**

### B12. Orchestrazione save + richiedi-approvazione L2 ripetuta inline — `bb_mancante_core` — 3 occorrenze

I pezzi atomici (`classifyL2Error`, `L2ErrorBanner`, `useLimitiPricing` con
`L2_ERROR_CODES`) sono **già** condivisi in `vendite/_shared/pricing/`, ma
l'**orchestrazione** (`l2Error = ref(null)` + watch reset + `handleSave` con
classify→banner-vs-toast + `onRichiediApprovazione` retry con `richiesta_approvazione=true`)
è copia-incollata 3 volte. I commenti dichiarano il mirror.

- [vendite/preventivi/.../PreventiviRigaForm.vue:467-509](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue#L467-L509)
- [vendite/components/ContrattoRigheDrawer.vue:835-880](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L835-L880)
- [vendite/offerte/.../OffertaEccezioniDrawer.vue:440-479](../../../../frontend/src/vendite/offerte/components/OffertaEccezioniDrawer.vue#L440-L479)

**Estrazione:** composable `useL2SaveFlow({ persist, buildPayload, onSuccess, watchSources,
messages })` in `vendite/_shared/pricing/` (resta in dominio vendite, non core). ⚠️ Solo la
macchina classify/retry/reset+watch è condivisibile; i side-effect di successo divergono
(emit vs loadPreview+closeForm vs reload+closeForm) → iniettati via `onSuccess(result)`
opzionale; loading-ref e payload builder ricevuti, non posseduti.

### B13. Auto-save BOZZA + "edit-evolved" + abbandono bozza orfana — `bb_mancante_core` — 2 occorrenze

Pattern `feedback_drawer_create_autosave_bozza` (documentato in memoria ma mai estratto):
4 blocchi quasi identici tra i due drawer testata — `autoSaveBozza()`, trigger watch con
guard chain identica, `hasOrphanedDraft` computed, `attemptClose/onVisibleChange` con
`confirmAction` danger → `store.elimina(createdId)`.

- [vendite/ordini/components/OrdiniDrawer.vue:225-353](../../../../frontend/src/vendite/ordini/components/OrdiniDrawer.vue#L225-L353)
- [vendite/preventivi/components/PreventiviDrawer.vue:431-634](../../../../frontend/src/vendite/preventivi/components/PreventiviDrawer.vue#L431-L634)

**Estrazione:** composable `useDrawerAutosaveBozza({ createDraftApi, buildPayload,
fetchDetail, deleteDraft, triggerFields, righeCountGetter, tabEntity, messages })` in
`core/composables/`. ⚠️ Trigger **multi-campo** (Ordini single `billing_account_id` vs
Preventivi tuple); preambolo `applyBaDefaults()` caller-owned (non cablare i default BA nel
BB); `createDraftApi` axios (non `store.create`, cfr. `feedback_useapihandler_solo_axios`);
coordinare con `useBaFormDefaults` già estratto. Esattamente 2 occorrenze = soglia.

### B14. Handler filtri toolbar lista vendite ripetuti — `bb_mancante_core` — 4 occorrenze

Blocco "filtri custom" (~30-40 righe) ripetuto: refs locali da `store.filters`, handler
one-liner `onXChange`, coppia data `onDataDaChange/onDataAlChange` con `toDateString`,
`buildExportParams(format)` che ri-mappa gli stessi campi.

- [vendite/ordini/.../OrdiniSearchTable.vue:54-85](../../../../frontend/src/vendite/ordini/components/OrdiniSearchTable.vue#L54-L85),
  [vendite/offerte/.../OfferteSearchTable.vue:55-97](../../../../frontend/src/vendite/offerte/components/OfferteSearchTable.vue#L55-L97),
  [vendite/components/ContrattiSearchTable.vue:53-109](../../../../frontend/src/vendite/components/ContrattiSearchTable.vue#L53-L109),
  [vendite/preventivi/.../PreventiviList.vue:53-95](../../../../frontend/src/vendite/preventivi/components/PreventiviList.vue#L53-L95)

**Estrazione:** estendere
[useListaConfigurabilePage](../../../../frontend/src/core/composables/useListaConfigurabilePage.js)
(già usato da tutte e 4) con `filterBindings(filterMap)` che genera ref+onChange+
`buildExportParams` dalla stessa mappa. ⚠️ Rename param non uniforme (offerte
`validita_dal_min/max`, preventivi `data_al`, ordini/contratti `data_da/data_a` 1:1) →
`filterMap` per-chiave `{storeKey, paramName, cast}`. **Falso positivo locale** sulla
coppia data contratti (`onDataDaChange` ha un ramo floor anno-1 peculiare) → opzione
`defaultFloor` o tenuto fuori. In subordine, estrarre almeno `bindDateFilter(store, key)`.

### B15. `unitaMisura`/`uomTipi` non usano `createCrudListStore` (gemelli lasciati indietro) — `bb_mancante_core` — 2 occorrenze

Asimmetria di adozione **dentro** catalogo: `articoli.js` usa la factory, i due gemelli
ripetono ~80 righe a mano.

- [catalogo/stores/unitaMisura.js:10-91](../../../../frontend/src/catalogo/stores/unitaMisura.js#L10-L91)
- [catalogo/stores/uomTipi.js:10-85](../../../../frontend/src/catalogo/stores/uomTipi.js#L10-L85)

**Migrazione** a `createCrudListStore(... { filterDefaults:{attivo:true}, gateKeys:[],
extraActions:{disattiva} })`. ⚠️ **Unica differenza reale:** entrambi chiamano
`invalidateLookup(CATALOGO_LOOKUP_RELS.X)` dopo ogni mutazione, e la factory **non** ha
hook di invalidazione. Aggiungere un'opzione `onMutate`/`lookupRel` (preferibile al
wrapping fragile delle api fn), pena bug silente (lookup UoM stale post-CRUD). Estensione
simmetrica da dichiarare a Tid. Si lega a B2/B17/B18.

### B16. Shell lifecycle sub-drawer master-detail (load + watch reset + F5) — `interno_core` — 4 occorrenze

Shell identico: ref loading, `loadX()` con guard su `props.<parentId>` + try/catch
fallback `[]`, `watch(visible){ reset form; loadX() }`, F5 opzionale.

- [catalogo/ArticoloUomDrawer.vue:43-131](../../../../frontend/src/catalogo/components/ArticoloUomDrawer.vue#L43-L131),
  [catalogo/UomConversioniDrawer.vue:48-92](../../../../frontend/src/catalogo/components/UomConversioniDrawer.vue#L48-L92),
  [catalogo/ArticoloBomDrawer.vue:66-272](../../../../frontend/src/catalogo/components/ArticoloBomDrawer.vue#L66-L272),
  [vendite/components/ContrattoRigheDrawer.vue:509-519](../../../../frontend/src/vendite/components/ContrattoRigheDrawer.vue#L509-L519) (fit parziale)

**Estrazione:** composable sottile `useMasterDetailDrawer({ visible, loadFn, resetForm,
onClose?, enableF5=false }) → { listLoading }`. ⚠️ Superficie estraibile sottile (~12-15
righe/sito): `resetForm` deve poter essere **async** (`await loadDefaults()` prima del
reset); il list-ref e il fallback `[]` restano al chiamante (cattura `non_editable_fields`
diversi); `ContrattoRigheDrawer` è fit parziale (due fetch + ramo else su close). **NON**
estrarre l'intero componente (form-body e regole di processo divergono profondamente).

### B17. 8 store admin re-implementano il CRUD lista di `createCrudAdminStore` (+ leak X1) — `bb_mancante_core` — 6 occorrenze nette

La factory [createCrudAdminStore.js](../../../../frontend/src/core/composables/createCrudAdminStore.js)
(usata da categorieClienti/categorieClientiListini/promoArticoli) è ignorata da più store
admin hand-rolled che ne ripetono il corpo (gate 3-char + fetchDetail + create/update +
`emitDataChanged`). **Fit netto su 3:** `tipiRuoloTipiIndirizzo`, `utilitiesTipiRuolo`,
`emittentiFiscali`. **Fit con caveat su 3:** `emailAccounts`/`emailTemplates` (no filtro
attivo/gate, conservano `currentX`/`loadingDetail` che la factory non espone), `operatori`
(override/scope restano custom sul return). **Fuori scope:** `emittentiFiscaliBA` (api con
path param esterno, sub-resource) ed `emailLogs` (read-only).

**Migrazione** dei fit netti + (con refactor del detail-storato) email*/operatori.
⚠️ Indipendentemente, applicare a **tutti** il fix `userScoped: true` → **chiude la
duplicazione e il leak X1 insieme**. Conteggio reale ~6, non 8.

### B18. Store admin "scoped per `lista_id`" (`ui.lista_*`): seconda famiglia di factory mancante — `bb_mancante_core` — 4 occorrenze

`fetchByLista(listaId)` copiato bit-per-bit + `clearUserState` + create-con-
`generateIdempotencyKey`+emit. **Non** è coperto da `createCrudAdminStore` (qui niente
search/pagination, fetch per chiave parent o full, `.data.data` array nudo, create con
Idempotency-Key).

- [ui/stores/uiColonnaAdmin.js:27-103](../../../../frontend/src/ui/stores/uiColonnaAdmin.js#L27-L103),
  [uiPermessoAdmin.js:16-74](../../../../frontend/src/ui/stores/uiPermessoAdmin.js#L16-L74),
  [uiPresetAdmin.js:31-118](../../../../frontend/src/ui/stores/uiPresetAdmin.js#L31-L118),
  [uiDefinizioneAdmin.js:27-95](../../../../frontend/src/ui/stores/uiDefinizioneAdmin.js#L27-L95) (variante `fetchAll`)

**Estrazione:** nuova factory `createScopedAdminStore({ api:{listByKey?|listAll, create,
update?, destroy, upsert?}, emitKey, idempotentCreate=true })` in `core/stores/`.
⚠️ Asimmetrie: variante `fetchByKey(parentKey)+lastKey` vs `fetchAll()` (uiDefinizione
rompe `lastListaId`); azioni custom (`upsert`, `replaceColonne`) richiedono un
escape-hatch/`extend`, non una factory chiusa.

### B19. Due factory CRUD parallele: `createCrudAdminStore` vs `createCrudListStore` — `interno_core` — 2 occorrenze

Stesso scheletro lista+CRUD in due cartelle (`composables/` vs `stores/`).
`createCrudListStore` (più recente) **delega** il gate a `useListaEmptyStateFetch`
(single-source); `createCrudAdminStore` **re-inlina** il gate a mano — proprio la
duplicazione che `useListaEmptyStateFetch` doveva eliminare.

- [core/composables/createCrudAdminStore.js:75-111](../../../../frontend/src/core/composables/createCrudAdminStore.js#L75-L111)
- [core/stores/createCrudListStore.js:64-84](../../../../frontend/src/core/stores/createCrudListStore.js#L64-L84)

**Convergenza:** un'unica factory `createCrudStore` che delega sempre il gate e supporta
sia "flag attivo sempre-inviato" (admin) sia `gateKeys` (list). ⚠️ **"ma" comportamentale
critico:** i due gate **non** sono identici — admin fa **sempre** fetch al mount (tabelle
admin partono piene), `useListaEmptyStateFetch` parte **vuoto** finché search<3 char. Una
fusione ingenua **regredirebbe** le tabelle admin → serve flag esplicito
`startsEmpty/alwaysFetch`. **Questo è il nodo che sblocca B2/B15/B17** (tutti dipendono
dall'estensione gate/onMutate della factory). **Rischio medium.**

---

## 🔴 Casi confermati ma da NON estrarre (falsa duplicazione)

La verifica avversariale ha aperto i file e confermato la divergenza: forma simile,
problemi diversi. Unificarli peggiorerebbe la leggibilità (cfr. caveat C di
`feedback_regola_del_2_estrai_bb`).

- **Form-builder composable** (`useContattoForm`/`useContoBancarioForm`/
  `useDatiSocietariForm`/`useSoggettoForm`/`useIndirizzoBase`). Condividono solo lo
  **scaffolding** convenzionale (`reactive(form)` + `validate()` + `reset()` +
  `populate()`); la logica sostanziale è non-sovrapponibile (classify three-state mirror
  BE; registro-IBAN + payload create/update divergenti; visibilità policy-driven; campi
  condizionali PF/PG; ~200 righe di guard CAP race). Una `createFormComposable` sarebbe
  astrazione prematura (`feedback_concentrico_no_yagni`).
- **`ContoContabileSelect` / `UtilityPerRuoloSelect`** "reimplementano LookupSelect". La
  coppia **collassa**: `ContoContabileSelect` duplica ~10 righe ma per un endpoint
  dedicato non raggiungibile via `rel` (wrapper documentato, gemello di `IvaSelect`);
  `UtilityPerRuoloSelect` **non** è del pattern (Select nudo + orchestrazione
  `useUtilityDefaultId` dominio-specifica). Innestare branching su un BB pulito per
  assorbirli sarebbe un aumento netto di complessità.
- **Wrapper `emitDataChanged` per-action negli store vendite.** Action Pinia idiomatiche
  di 1-3 righe con scope per-action; la varianza è irriducibile (alcune doppio-emit
  OFFERTA+CONTRATTO, altre solo ORDINE, le read-only nessun emit). Una `wrapEmit` factory
  offuscherebbe lo scopo. I dialog emissione e i note drawer citati sono **già** wrapper
  thin corretti. La vera duplicazione lista è già estratta in `useListaEmptyStateFetch`.
- **`PraticaNoteTab` "reinventa il BB note partizionate".** **Modello dati diverso**:
  pratiche usa `note_pratiche` (`tipo_nota_id`/`contenuto`), il BB è costruito sul modello
  `vendite.note_*` con partizionamento `target_tipo/target_id/target_riga_id` + stile/
  lingua/visibile. Contratto API diverso (no Idempotency-Key), UX diversa (tab inline vs
  drawer formMode). Allinearli richiederebbe **prima** una convergenza del *modello* note
  cross-dominio (decisione di dominio, non FE). Inoltre 1 sola occorrenza FE → la regola
  del 2 non scatta.

---

## ⚠️ Scoperte collaterali (debiti: BB ignorati, asimmetrie, bug latente)

### D1. `userScoped` leak in 9 store admin → vedi **X1**

Già trattato in cima come scoperta critica. Resta qui come debito di **convenzione
ignorata** (`feedback_pinia_userscoped`), trasversale a B17.

### D2. Asimmetria `CodiciPostaliDrawer` — verdetto **invertito** dal finder — ✅ FATTO (2026-06-05)

> **Risolto rimuovendo il double-fetch dai 5 fratelli** (non aggiungendolo a CAP).
> Tutti e 6 i drawer geo (ora wrapper di `EntityFormDrawer`, A3) sono passati a
> `:refresh-on-save="false"` → refresh lista uniforme via `emitDataChanged`→
> `useTabFreshness`. **Verifica di sicurezza prima del cambio:** `useTabEvents` usa un
> bus **in-memory module-level** ([useTabEvents.js:17](../../../../frontend/src/core/composables/useTabEvents.js#L17))
> che invoca i listener **sincronamente, anche same-tab** (il nome "inter-tab" è
> fuorviante: è un bus interno alle content-tab dell'SPA, stesso contesto JS); e tutte e
> 6 le coppie store↔SearchTable combaciano (stessa chiave `TAB_ENTITIES`, emit su
> create/update, `useTabFreshness` registrato). Quindi il refresh resta garantito senza
> il `fetchList` esplicito. ESLint + `vite build` verdi.

[CodiciPostaliDrawer.vue](../../../../frontend/src/core/components/CodiciPostaliDrawer.vue)
era l'unico dei 6 drawer geo che **non** chiamava `store.fetchList()` dopo save. Il finder
lo segnalava come bug (lista non aggiornata), **ma la verifica ha invertito il verdetto**:
lo store emette `emitDataChanged(CODICE_POSTALE)` su create/update e la SearchTable
registra `useTabFreshness` → la lista si aggiorna comunque. Quindi `CodiciPostaliDrawer`
era l'outlier **corretto** (single-fetch); gli altri 5 facevano un **double-fetch
ridondante** (tab-events + fetchList esplicito) → ora rimosso.

### D3. Asimmetria catalogo: `unitaMisura` ha `disattiva` ma non `riattiva`

[catalogo/stores/unitaMisura.js:80-90](../../../../frontend/src/catalogo/stores/unitaMisura.js#L80-L90)
espone `disattiva()` ma non `riattiva()` (assente anche in api + BE), a differenza di
`articoli` che ha la coppia simmetrica. ⚠️ **Da chiarire con Tid/BE prima di agire**: una
UoM disattivata è tecnicamente già riattivabile via `update({attivo:true})` (la colonna
`attivo` è nelle update keys), quindi l'asimmetria reale è sul **pattern di azione**
(bottone dedicato vs flag in form), non un blocco. Decisione di dominio
(`feedback_simmetria_modello_no_meta_scope`), non fix meccanico.

### D4. BB formattazione ignorati: `displayTimestamp` / `formatCurrency` reinventati inline

Punti che bypassano util **già** centralizzati e censiti a catalogo:

- **Timestamp** (`new Date(x).toLocaleString()` inline invece di `displayTimestamp` da
  `core/utils/date.js`, output non deterministico):
  [amministrazione/EmailAccountDrawer.vue:90-97](../../../../frontend/src/amministrazione/components/EmailAccountDrawer.vue#L90-L97),
  [documenti/DocumentiGeneratiSorgenteList.vue:231](../../../../frontend/src/documenti/components/DocumentiGeneratiSorgenteList.vue#L231),
  [vendite/views/ApprovazioniPrezzoListView.vue:264](../../../../frontend/src/vendite/views/ApprovazioniPrezzoListView.vue#L264).
- **Valuta** (`Intl.NumberFormat` EUR min2/max6 inline invece di `formatCurrency` da
  `core/utils/format.js`):
  [vendite/preventivi/.../PreventiviRigaForm.vue:127-133](../../../../frontend/src/vendite/preventivi/components/PreventiviRigaForm.vue#L127-L133).

**Azione:** sostituire con i BB esistenti (nessun BB nuovo). ⚠️ Sui timestamp non è una
no-op visiva: `displayTimestamp` forza `DD/MM/YYYY, HH:mm:ss` (l'uniformità desiderata) —
cambio di output da validare. La valuta è invariata.

### D5. `app-lookup-option`: CSS centralizzato, markup ancora hand-rolled

La classe `app-lookup-option` (primary/secondary/meta) è **già** il BB condiviso (CSS, a
catalogo), correttamente riusata da BillingAccountLookup/IstanzaUtilityLookup e ora anche
da [documenti/SceltaTemplateDocumentoDialog.vue](../../../../frontend/src/documenti/components/SceltaTemplateDocumentoDialog.vue)
(terzo consumer). Manca solo la **controparte componente** del markup. ROI sottile (ogni
consumer riempie le 3 righe con campi diversi → sarebbe un passthrough a 3 slot). Da
valutare **solo** se/quando si costruisce un componente lookup ricco (vedi B6); non
un'estrazione a sé.

---

## 📐 Nota di design — la famiglia "guard di versione" (A1/A2/B3) è il caso seme

Come nel BE la maggioranza dei `bb_mancante_core` apparteneva alla famiglia query-param,
qui il filo conduttore più netto è il **guard a contatore monotono anti-race**. Oggi
esiste in **tre forme** che dovrebbero essere una:

1. **`useFetchVersion`** (`core/composables/`) — la forma canonica da tenere. ✅ Eletta.
2. ~~**`useTokenedFetch`**~~ — gemello bit-identico, **ritirato (A1, 2026-06-05)**:
   consumer unico (`useRigaComponenti`) migrato, file eliminato, catalogo aggiornato.
3. **Inline `fgVersion`/`_fetchToken`** — reinventato in 4 drawer (A2) + in
   `useArticoloUomOptions` (B3), che vive *accanto* ai due BB.

**Sequenza eseguita (2026-06-05) — ✅ famiglia chiusa:** (1) eletto `useFetchVersion`,
eliminato `useTokenedFetch`, migrato l'unico callsite, censita **una** entry a catalogo,
assorbiti i doc-comment stantii (A1); (2) adottato `useFetchVersion` nei 4 drawer (A2) +
in `useArticoloUomOptions` (B3). È l'analogo FE della "famiglia query-param" del BE:
completare/unificare il BB esistente è stato sufficiente, niente nuove primitive. ESLint +
`vite build` verdi.

> **Secondo filo: la famiglia "store factory".** B2 + B15 + B17 + B18 + B19 convergono su
> un unico nodo architetturale — l'unificazione/estensione delle factory store
> (`createCrudListStore`/`createCrudAdminStore` + il gate `useListaEmptyStateFetch`). **B19
> è il prerequisito**: finché la factory unica non espone i flag `gated`/`alwaysFetch` +
> hook `onMutate`, le adozioni B2/B15/B17 restano bloccate o regressive. Da progettare come
> **un unico cantiere** prima di toccare i singoli store.

---

## Come procedere (proposta)

Per ogni candidato vale il protocollo della regola del 2
(`feedback_regola_del_2_estrai_bb`): **dichiarare a chat il disegno del BB e attendere
l'OK di Tid** prima di scrivere codice astratto. Ordine suggerito per gravità/valore:

1. ✅ **X1** (`userScoped` su 9 store admin) — **FATTO (2026-06-05)**. Fix minimo, alto
   valore (privacy), basso rischio. Indipendente da tutto il resto.
2. ✅ **A1 + A2 + B3** (famiglia guard di versione) — **FATTO (2026-06-05)**:
   `useTokenedFetch` ritirato e consumer migrato (A1); 4 drawer `fgVersion` +
   `useArticoloUomOptions` migrati su `useFetchVersion` (A2/B3); catalogo aggiornato;
   ESLint + `vite build` verdi.
3. ✅ **A4** (`AttivoTag`, 26 siti) — **FATTO (2026-06-05)**; 🟢 **B7/B8** (util-ombra
   `dateHelpers`/`downloadBlob`) ancora da fare — netti, basso rischio.
4. 🟡 **Cantiere factory store** (**B19** prerequisito → poi B2/B15/B17/B18) — progettare
   la firma unica (`gated`/`alwaysFetch`/`onMutate`) **prima** di migrare i singoli store.
5. ✅ **A3 + B1 + D2** (stack geografico drawer+tabelle) — **FATTI (2026-06-05)**:
   `EntityFormDrawer` schema-driven (6 drawer wrapper); `GeoSearchTable` (6 SearchTable
   wrapper); double-fetch ridondante rimosso (`refreshOnSave:false` su tutti e 6).
6. 🟡 **B5** (`LookupSelect` esteso), **B6** (composable autocomplete ricco), **B9**
   (`useActionBar`), **B4** (collection soggetto/ruolo) — BB core trasversali.
7. 🟡 **Stack righe vendite** (**B10/B11/B12/B13/B14/B16**) — collocare in
   `vendite/_shared/` dove indicato; dichiarare a Tid (rischio medium, drift campi da
   sanare).
8. 🟢 **D4** (BB formattazione ignorati) — sostituzioni puntuali, validare il cambio di
   output timestamp.
9. ⚠️ **D3** (riattiva UoM) e **D5** (markup lookup) — decisioni di dominio / contingenti,
   non urgenti.
10. 🔴 Form-builder, ContoContabile/UtilityPerRuolo, wrapper emit, PraticaNoteTab — **non**
    toccare (falsa duplicazione).

> Stato: **nessuna estrazione eseguita.** Documento di sola mappatura, in attesa dell'OK
> di Tid sui singoli pezzi.
