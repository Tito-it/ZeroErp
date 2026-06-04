# Catalogo Building Block — Frontend

> Inventario dei componenti riutilizzabili nel frontend Vue.
> Prima di implementare logica nuova, verificare se esiste già un building block adatto.
>
> Documento vivo — aggiornare ogni volta che si aggiunge un building block.

---

## Composables (`src/core/composables/`)

| Building Block | File | Descrizione |
|---|---|---|
| `useNotify` | [useNotify.js](../../../../frontend/src/core/composables/useNotify.js) | Toast notifiche (success, warn, error, systemError) |
| `useApiHandler` | [useApiHandler.js](../../../../frontend/src/core/composables/useApiHandler.js) | Wrapper chiamate API con error handling automatico e stato loading |
| `useLoading` | [useLoading.js](../../../../frontend/src/core/composables/useLoading.js) | Stato caricamento con distinzione first load (skeleton) vs successivi (progressbar) |
| `usePagination` | [usePagination.js](../../../../frontend/src/core/composables/usePagination.js) | Paginazione server-side con integrazione PrimeVue DataTable |
| `useSearchTable` | [useSearchTable.js](../../../../frontend/src/core/composables/useSearchTable.js) | Ricerca/paginazione/ordinamento unificato per DataTable con debounce |
| `useDrawerState` | [useDrawerState.js](../../../../frontend/src/core/composables/useDrawerState.js) | Stato drawer centralizzato (create/edit mode) |
| `useFetchVersion` | [useFetchVersion.js](../../../../frontend/src/core/composables/useFetchVersion.js) | **Guard di versione / token anti-race (unificato 2026-06-05, regola del 2).** Unica primitiva per scartare risposte async stantie quando il contesto cambia piu' in fretta del ritorno delle fetch. Closure non reattiva: `tag()` cattura un contatore monotono prima dell'await, `isCurrent(tag)` confronta col valore corrente al ritorno (false = arrivata una fetch piu' nuova, scarta), `invalidate()` bumpa senza emettere nuova fetch (reset/close). Copre due scenari prima biforcati: (1) drawer/lista fire-and-forget (consumer `OffertaDrawer`, `PreventiviDrawer` via `useRevisioniTab`); (2) switch rapido lookup/preview/list (consumer `useRigaComponenti`, `useArticoloUomOptions`). **Ha assorbito `useTokenedFetch`** (gemello bit-identico, ritirato): chi preferiva `nextToken` aliasa in destructuring `{ tag: nextToken, isCurrent, invalidate }`. Non e' un ref reattivo (no rendering). |
| `useDrawerSavedListRefresh` | [useDrawerSavedListRefresh.js](../../../../frontend/src/core/composables/useDrawerSavedListRefresh.js) | Handler standard "salvataggio drawer → refresh lista": `const { onDrawerSaved } = useDrawerSavedListRefresh(store, drawer)`. Reset offset → `fetchList` → se era CREATE riapre la riga in edit (per gestire sotto-entita), altrimenti chiude. Estratto 2026-06-03 (regola del 2). Adottato da: `ClientiView`, `FornitoriView`, `ArticoliView`, `UnitaMisuraView`, `UomTipiView`, `ContrattiListView`, `ListiniView` (7 viste). Variante "refresh+close senza reopen" presente in altre ~6 viste, non ancora unificata. |
| `useDrawerClose` | [useDrawerClose.js](../../../../frontend/src/core/composables/useDrawerClose.js) | Handler standard chiusura drawer: `const onClose = useDrawerClose(emit)` (emette `update:visible=false`). Secondo argomento opzionale per evento secondario di notifica al parent: `useDrawerClose(emit, 'cancelled')` (pratiche, anagrafiche, contratti) o `useDrawerClose(emit, 'annullato')` (SoggettoResolver). Centralizza il pattern (20 drawer adottanti). |
| `useDrawerContentReady` | [useDrawerContentReady.js](../../../../frontend/src/core/composables/useDrawerContentReady.js) | **Refactor UI drawer 2026-05-22.** Centralizza il pattern `feedback_content_ready_after_show`: i LookupSelect/AutoComplete/DatePicker pesanti vengono renderizzati solo dopo l'animazione di slide PrimeVue Drawer (evento `after-show`), per evitare il "blocco e ripartenza" all'apertura. API: `const { contentReady, onAfterShow } = useDrawerContentReady(() => props.visible)`. Il composable gestisce automaticamente il reset di `contentReady` a `false` alla chiusura (niente bisogno di farlo manualmente nel watch su visible). Template: `<Drawer @after-show="onAfterShow"><div class="app-drawer-content"><template v-if="contentReady">...</template></div></Drawer>`. Adottato da: `ContrattoDrawer`, `PreventiviDrawer`, `ArticoloDrawer`, `ListinoDrawer`, `ConversioneUomDrawer`, `PromoArticoloDrawer`. |
| `useDirtyState` | [useDirtyState.js](../../../../frontend/src/core/composables/useDirtyState.js) | Tracciamento modifiche non salvate con beforeunload e tab dirty |
| `useFileDownload` / `isFileSystemAccessSupported` | [useFileDownload.js](../../../../frontend/src/core/composables/useFileDownload.js) | **DEF-1 export liste.** Scarica un Blob (axios `responseType: 'blob'`) e triggera download nel browser con strategia a 2 path: (1) **File System Access API** quando `window.showSaveFilePicker` e' supportato (Chrome/Edge moderni HTTPS) -> dialog NATIVO "Salva con nome" del sistema operativo, l'utente sceglie cartella e nome; AbortError (cancel utente) trattato come "completato" senza errore; (2) **fallback `<a download>`** classico altrove (Firefox/Safari/HTTP), file in cartella download default. `extractFileName` parsa Content-Disposition (RFC 5987 `filename*=UTF-8''...` + fallback `filename="..."`). `buildPickerAccept` deduce MIME ed estensione dal Content-Type. Esporta anche `isFileSystemAccessSupported()` per UX hint dei chiamanti. Building block riusabile per export CSV/XLSX, PDF, log. Adottato da: `ClientiSearchTable` (DEF-1) tramite `ExportDialog`; estensione attesa in DEF-8. |
| `useConfirmAction` | [useConfirmAction.js](../../../../frontend/src/core/composables/useConfirmAction.js) | Dialog conferma standard (delete, save, azione generica) |
| `useConfirmCloseTab` | [useConfirmCloseTab.js](../../../../frontend/src/core/composables/useConfirmCloseTab.js) | Conferma chiusura tab con stato dirty |
| `useLookup` | [useLookup.js](../../../../frontend/src/core/composables/useLookup.js) | Cache dati lookup **per-istanza** (caricamento immediato o lazy). Usare solo per lookup che devono ricaricarsi a ogni mount o con fetchFn non-idempotenti. Per lookup condivisi cross-componente preferire `useGlobalLookup` |
| `useGlobalLookup` / `invalidateLookup` / `invalidateAllLookups` | [useGlobalLookup.js](../../../../frontend/src/core/composables/useGlobalLookup.js) | Cache dati lookup **modulo-level** condivisa per-chiave string. Primo consumer fa la fetch, i successivi riusano stessa `items`/`loading` reattiva + stessa Promise in volo (dedup thundering herd). `invalidateLookup(key)` per refresh mirato post-CRUD admin, `invalidateAllLookups()` per logout/switch tenant. Adottato da `LookupSelect` (chiave = `rel`), `ListiniSearchTable` (`config.listini_tipologie`), `MatriceIndirizzi*` (`config.tipi_indirizzi`). Ref: sviluppo-listini-v6 §2.1 (V6-F1) |
| `useServerAutocomplete` | [useServerAutocomplete.js](../../../../frontend/src/core/composables/useServerAutocomplete.js) | Autocomplete server-side con debounce |
| `useCodiceField` | [useCodiceField.js](../../../../frontend/src/core/composables/useCodiceField.js) | Carica config sequenza codice (auto vs manuale, prefisso, separatore) |
| `useReadonlyMode` | [useReadonlyMode.js](../../../../frontend/src/core/composables/useReadonlyMode.js) | Modalità sola lettura basata su permessi utente (provider/consumer). Accetta `modelName` opzionale per granularita' oggetto v2: `useReadonlyMode('anagrafiche', 'conto_bancario')`. Senza model, fallback al livello area. |
| `useActionPermission` | [useActionPermission.js](../../../../frontend/src/core/composables/useActionPermission.js) | Verifica permesso azione processo (computed reattivo) |
| `useTabLabel` | [useTabLabel.js](../../../../frontend/src/core/composables/useTabLabel.js) | Aggiorna dinamicamente label della content tab |
| `useTabEvents` | [useTabEvents.js](../../../../frontend/src/core/composables/useTabEvents.js) | Event bus inter-tab per invalidazione dati |
| `useTabFreshness` | [useTabFreshness.js](../../../../frontend/src/core/composables/useTabFreshness.js) | Auto-refresh lista quando altre tab modificano entità |
| `useKeyboardShortcuts` | [useKeyboardShortcuts.js](../../../../frontend/src/core/composables/useKeyboardShortcuts.js) | Registra shortcut globali (disabilita su input/textarea) |
| `usePasswordValidation` | [usePasswordValidation.js](../../../../frontend/src/core/composables/usePasswordValidation.js) | Validazione password client-side (min 8 char, match) |
| `useAuthUser` | [useAuthUser.js](../../../../frontend/src/core/composables/useAuthUser.js) | Form auth utente (username, email, password, confirm) |
| `useSoggettoForm` | [useSoggettoForm.js](../../../../frontend/src/core/composables/useSoggettoForm.js) | Form soggetto universale PF/PG/ENTE con campi condizionali |
| `useContattoForm` | [useContattoForm.js](../../../../frontend/src/core/composables/useContattoForm.js) | Form contatto (nominativo, email, telefono, tipo_contatto) |
| `useContoBancarioForm` | [useContoBancarioForm.js](../../../../frontend/src/core/composables/useContoBancarioForm.js) | Form conto bancario (IBAN, BIC, uso, date) |
| `useDatiSocietariForm` | [useDatiSocietariForm.js](../../../../frontend/src/core/composables/useDatiSocietariForm.js) | Form dati societari (forma giuridica, REA, capitale, FE) |
| `useIndirizzoBase` | [useIndirizzoBase.js](../../../../frontend/src/core/composables/useIndirizzoBase.js) | Form indirizzo base (comune, via, civico, CAP) |
| `useIndirizzoDuplicato` | [useIndirizzoDuplicato.js](../../../../frontend/src/core/composables/useIndirizzoDuplicato.js) | Rilevamento indirizzi duplicati via backend |
| `useIndirizzoMultiTipo` | [useIndirizzoMultiTipo.js](../../../../frontend/src/core/composables/useIndirizzoMultiTipo.js) | Gestione snapshot indirizzi multi-tipo |
| `useIndirizzoSoggettoForm` | [useIndirizzoSoggettoForm.js](../../../../frontend/src/core/composables/useIndirizzoSoggettoForm.js) | Compone base + multi-tipo + indirizzo libero (nazionale/estero) |
| `useSearchDetail` | [useSearchDetail.js](../../../../frontend/src/core/composables/useSearchDetail.js) | Caricamento lazy righe dettaglio per espansione ricerca |
| `useAiAssistant` | [useAiAssistant.js](../../../../frontend/src/core/composables/useAiAssistant.js) | Conversazione assistente AI (messaggi, azioni, conferme) |
| `useParameterDefaults` | [useParameterDefaults.js](../../../../frontend/src/core/composables/useParameterDefaults.js) | Carica default da `config.parameters` con override utente. Props: `codes[]`. Metodi: `load()` (con cache, error-safe). Restituisce `defaults` (mappa `{code: valore}`). |
| `useArticoloUomOptions` | [useArticoloUomOptions.js](../../../../frontend/src/core/composables/useArticoloUomOptions.js) | **Fase 4.F1 refactor frontend vendite.** Centralizza il pattern UoM operative articolo (4 consumer: `PromoArticoloDrawer`, `ContrattoRigheDrawer`, `VersioneDrawer`, `PreventiviRigaForm`). Espone `uomOptions` (ref array), `uomLoading` (ref bool), `loadUomPerArticolo(articoloId)` (fetch puro, ritorna lista), `pickBaseUomId(list)` (helper: UoM base, o l'unica disponibile, o null), `resetUomOptions()`. Token pattern interno scarta risposte stantie su cambi articolo veloci. Il caller decide quando applicare l'autopick base via wrapper thin (criterio diverso per consumer: `!isEdit`, `formMode === 'create'`, ecc.). |
| `useEntityCapabilities` | [useEntityCapabilities.js](../../../../frontend/src/core/composables/useEntityCapabilities.js) | **Fase 4.F2 refactor frontend vendite.** Adapter sottile per consumare il blob capabilities BE (Fase 1: `script.fn_available_actions_*`/`fn_capability_promo_articolo`). Consumer: `PreventiviDrawer` + `ContrattoDrawer` (`editFlag='can_edit_testata'` default), `PromoArticoloDrawer` (`editFlag='can_update'`). Ritorna `availableActions` (computed array), `nonEditableFields` (computed Set lookup O(1)), `canEdit` (computed bool sul flag `editFlag`), `isLocked(field)` (check `!canEdit OR Set.has`), `flag(key)` (getter generico per altri `can_*`). Mai logica derivata: lookup puro. |
| `useDrawerActions` (`mapAvailableActionsToDrawerActions`) | [useDrawerActions.js](../../../../frontend/src/core/composables/useDrawerActions.js) | **Refactor UI drawer 2026-05-21.** Helper che trasforma `availableActions` BE (ref/computed/array) nelle azioni `kind:'state'` consumate da `DrawerActionsBar`. Una entry BE → una azione FE con `label=t(label_key)`, `icon`, `severity` copiati; il dettaglio `requires_date`/`requires_confirm` resta opaco al BB e arriva intero al callback `onAction` del drawer. Riduce la ripetizione `<Button v-for="action in availableActions" :icon="action.icon" :label="t(action.label_key)" :severity="action.severity" ...>` presente oggi in `PreventiviDrawer`/`ContrattoDrawer`. |
| `useNavigationFavorites` | [useNavigationFavorites.js](../../../../frontend/src/core/composables/useNavigationFavorites.js) | **Preferiti utente HOME + sidebar.** Centralizza risoluzione preferiti localStorage (`domain`, `path` → voce menu, label i18n, icona, tooltip), filtro permessi runtime coerente con `SidebarDomain`, apertura tab + `router.push` + `nav.setDomain`, e riordino del sottoinsieme visibile preservando eventuali preferiti filtrati. Consumatori: `SidebarHome`, `HomeView`, `FavoriteItem`. Nessuna API/BE: persistenza in `useNavigationStore`. |
| `useEmittenteFiscaleField` | [useEmittenteFiscaleField.js](../../../../frontend/src/core/composables/useEmittenteFiscaleField.js) | Composable di supporto a `EmittenteFiscaleField` (componente sotto). Espone profilo + lookup admin + helper di formatting. Modello 1-a-1 operatore→emittente: il valore e' derivato dal profilo, non scelto, salvo per admin globali. Espone `isAdminMode`, `currentEmittente`, `currentEmittenteDisplay`, **`defaultEmittenteId`** (computed: id profilo per operatore, null per admin — usato dai drawer per autopopulate one-liner), `emittentiOptions`/`emittentiLoading`/`emittentiError`/`loadOptions()` (cache modulo-level via `useGlobalLookup`, chiave `amm.emittenti_fiscali`, fetcher `listEmittentiFiscali` admin-only), helper puri `formatEmittenteOptionLabel` e `formatEmittenteFromRecord`. |
| `useListaConfig` | [useListaConfig.js](../../../../frontend/src/core/composables/useListaConfig.js) | **Blocco D personalizzazioni liste.** Stato per `<ListaConfigurabile>`: `config` (cascata BE), `catalogo` (lazy on first openModal), `dirty` (modifiche non salvate), `colonneNuove` (badge), `loading`. Metodi: `load()`, `ensureCatalogo()`, `applyChange(mutator)`, `save()` (PUT con `Idempotency-Key=crypto.randomUUID()`), `reset()` (DELETE preferenza + reload). Whitelist payload allineata a `ListaPreferenzaService._PAYLOAD_KEYS`. |
| `createCrudListStore` (store factory, `core/stores/`) | [createCrudListStore.js](../../../../frontend/src/core/stores/createCrudListStore.js) | **Factory store Pinia lista+CRUD (2026-06-03, regola del 2).** Costruisce un `useXxxStore` per il pattern lista paginata + dettaglio + create/update con gate "min 3 char / hasFilters" e `emitDataChanged`. Config: `api {list,detail?,create,update}`, `tabEntity`, `filterDefaults`, `gateKeys` (sottoinsieme che gata la lista-vuota; permette filtri inviati-sempre-ma-non-gate come `articoli.attivo`), `orderBy`, `createIdField`, `extraActions` (es. `disattiva`/`riattiva`), `options` passthrough. **`userScoped: true` di default** (reset al logout via `autoResetPlugin`, evita leak cross-user — vedi `feedback_pinia_userscoped`). Adottato da: `clienti`, `fornitori`, `soggetti` (anagrafiche), `articoli` (catalogo). `indirizzi` escluso (no `fetchDetail` + emit su `indirizzo_dettaglio_id`). |
| `useListaConfigurabilePage` | [useListaConfigurabilePage.js](../../../../frontend/src/core/composables/useListaConfigurabilePage.js) | **Scaffolding pagine lista (2026-06-02, estrazione regola del 2).** Centralizza ciò che le SearchTable basate su `<ListaConfigurabile>` (clienti/soggetti/fornitori/contratti) ripetevano identico: `useSearchTable`, ref alla lista (`listaRef`/`dirty`/`colonneNuove`/`configReady`), wiring export (`useFileDownload`+`ExportDialog`: `exportDialogVisible`/`exportLoading`/`onExportConfirm`), `onConfigLoaded` (allinea `store.filters.limit`), le 4 `pageActions` standard (reload/personalizza/export/new) e `tablePage` (pagina 1-based con guard `rows>0`). API: `useListaConfigurabilePage(store, { exportFn, getExportParams, newTooltipKey, onNew, searchTableOptions, extraActions? })`. `getExportParams` è lazy (invocata al click export → può riferire `searchText`/ref filtri definiti dopo il destructuring). Il componente mantiene solo filtri, slot `cell-*`, `buildRowActions` e `onRowClick`. ~70 righe/lista rimosse. |
| `useListaEmptyStateFetch` | [useListaEmptyStateFetch.js](../../../../frontend/src/core/composables/useListaEmptyStateFetch.js) | **Guardia empty-state lista (2026-06-03, estrazione regola del 2).** Centralizza lo stato lista (`items`/`totalRecords`/`loading`/`hasSearched`) + il `fetchList` con la guardia "liste che partono vuote" (frontend-standards §"Empty state"): search < 3 char ignorata, primo caricamento senza filtri resta vuoto, search svuotata torna vuoto — i 3 reset erano duplicati bit-per-bit in 3 store. API: `useListaEmptyStateFetch({ filters, hasActiveFilters(f)->bool, buildParams(f, searchTerm)->object, fetchPage(params)->axios })`. `buildParams` resta caller-owned perché la mappatura filtri→query diverge (preventivi `page/page_size`, offerte/ordini `limit/offset`; rename `data_a`→`validita_dal_max`/`data_al`; `solo_attiva`). Adottato dai 3 store-documento vendite "ricchi" (transizioni+righe+componenti): `useOfferteStore`, `usePreventiviStore`, `useOrdiniStore`. **Relazione con `createCrudListStore`**: la factory CRUD-semplice (clienti/fornitori/soggetti/articoli) **delega la guardia a questo composable** → gate single-source. Layering: questo composable = primitiva gate; la factory ci costruisce sopra (param-builder 1:1 + limit/offset + extraActions). Vedi `analisi-ordini-vendita.md §6.ter`. |
| `useResponsiveColumns` | [useResponsiveColumns.js](../../../../frontend/src/core/composables/useResponsiveColumns.js) | **Ritiro dinamico colonne (2026-06-02).** Packing a somma via `ResizeObserver` sul contenitore: ritira le colonne a `priorita` più bassa in una riga di espansione quando la somma delle `larghezza_default` supera lo spazio reale (es. apertura sidebar) — evita la scrollbar orizzontale senza media query (che sono cieche alla sidebar). identificatore/azione/fissata mai ritirate; tiebreaker `ordine_default`. API: `useResponsiveColumns(containerRef, columns, { hasActions })` → `{ containerWidth, visibleColumns, hiddenColumns }`. Integrato in `<ListaConfigurabile>` (prop `responsive`, default true). Deroga documentata "CSS-first" in [frontend-standards §"Ritiro dinamico colonne"](frontend-standards.md). |
| `useNote` | [useNote.js](../../../../frontend/src/core/composables/useNote.js) | **Building block note partizionate (2026-05-19).** Stato reattivo `notes`/`total`/`page`/`pageSize`/`loading` + comandi `loadAll`/`save`/`remove`/`fetchOne`. Accetta `apiClient` come oggetto statico **oppure** ref/computed (tipicamente costruito con `makeNotesApi('/vendite/preventivi/<id>')`): viene dereffato via `unref` a ogni call, cosi' un cambio di parent id riflette immediatamente senza remount. `save(form)` distingue create vs update guardando `form.id`; in UPDATE rimuove i campi immutabili `target_tipo`/`target_id`/`target_riga_id`. |

---

## Pinia Stores (`src/stores/`)

| Store | File | Descrizione |
|---|---|---|
| `useAuthStore` | [auth.js](../../../../frontend/src/stores/auth.js) | Autenticazione e autorizzazione (token, profilo, permessi, login/logout). Getter permessi: `getLivelloArea(schemaDb)`, `isAreaReadonly(schemaDb)`, `isAreaBlocked(schemaDb)`, `getLivelloOggetto(schemaDb, modelName)`, `isObjectReadonly(schemaDb, modelName)`, `isObjectBlocked(schemaDb, modelName)`, `isActionAllowed(codename)`. |
| `useUiStore` | [ui.js](../../../../frontend/src/stores/ui.js) | Layout responsive, stato UI (sidebar, search drawer, AI drawer), dark/light mode (`isDark`, `toggleDarkMode`) |
| `useTabsStore` | [tabs.js](../../../../frontend/src/stores/tabs.js) | Content tabs tipo browser con split-view e dirty tracking |
| `useNavigationStore` | [navigation.js](../../../../frontend/src/stores/navigation.js) | Stato sidebar dominio/menu e pagine preferite |
| `useContextStore` | [context.js](../../../../frontend/src/stores/context.js) | Contesto globale ricerca (soggetto, tipo_ruolo, entità) |

---

## Utility Functions (`src/core/utils/`)

| Building Block | File | Descrizione |
|---|---|---|
| `displayDate` / `displayTimestamp` / `toDateString` | [date.js](../../../../frontend/src/core/utils/date.js) | Formattazione date (DD/MM/YYYY, timestamp, YYYY-MM-DD) |
| `capitalizeWords` / `capitalizeFirst` | [string.js](../../../../frontend/src/core/utils/string.js) | Capitalizzazione stringhe |
| `blockNonAlphanumeric` | [string.js](../../../../frontend/src/core/utils/string.js) | Blocca input non alfanumerico su keypress |
| `normalizeUpperNoSpaces` / `normalizeUpper` | [string.js](../../../../frontend/src/core/utils/string.js) | Normalizza campo a UPPERCASE (con/senza spazi) |
| `sortByFonte` | [string.js](../../../../frontend/src/core/utils/string.js) | Ordina per gerarchia fonte (soggetto→ruolo→istanza) |
| `formatSize` | [format.js](../../../../frontend/src/core/utils/format.js) | Formatta bytes in B/KB/MB/GB |
| `formatIvaLabel` | [format.js](../../../../frontend/src/core/utils/format.js) | Etichetta IVA compatta per liste/datatable. Aliquota > 0 → `"22%"`; aliquota 0/NULL (esenti) → `iva_codice` (es. `"N1"`, `"ESENTE17"`). Sfrutta il CHECK `chk_iva_zero_requires_natura_or_assogg`: un'aliquota=0 ha sempre codice parlante. Per visualizzazioni ricche (riepilogo IVA, drawer dettaglio) preferire `iva_descrizione` esteso. |
| `isEmailValid` | [validators.js](../../../../frontend/src/core/utils/validators.js) | Validazione formato email/PEC (UX, non RFC) |
| `resolveSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Risolve severity PrimeVue da mappa codice |
| `statoClienteSeverity` / `statoFornitoreSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato cliente/fornitore |
| `statoVersioneListinoSeverity` / `dominioListinoSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato versione (BOZZA/ATTIVA/CHIUSA) e dominio listino (UTILITY/COMMERCIO) |
| `statoPraticaSeverity` / `prioritaPraticaSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato/priorità pratica |
| `statoFlussoSeverity` / `esitoFlussoSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato/esito flusso |
| `azioneGiornaleStyle` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Stile azione giornale (severity + icona) |
| `extractApiError` / `extractApiErrorCode` | [apiError.js](../../../../frontend/src/core/utils/apiError.js) | Estrae messaggio/codice errore da risposta API |
| `paramBool` / `paramNumber` / `paramInt` / `paramString` | [parameterCast.js](../../../../frontend/src/core/utils/parameterCast.js) | Cast con fallback dei valori `config.parameters` (BE ritorna `dict[str, str]`). Riusabili da qualsiasi `defaultForm()` parametrizzato. Adottato da: ArticoloUomDrawer (Fase 1 refactor catalogo). |
| `generateIdempotencyKey` | [idempotency.js](../../../../frontend/src/core/utils/idempotency.js) | Genera UUID v4 da usare come header `Idempotency-Key`. Wrapper su `crypto.randomUUID()` con **fallback** `Date.now()-Math.random().toString(36)` per non-secure context (HTTP su IP LAN / hostname custom, tipico setup VSCode SSH + port forward, dove `crypto.randomUUID` e' `undefined` e tira `TypeError`). Adottato da: `catalogo.js`, stores `uiPreset/Permesso/Definizione/ColonnaAdmin`, `useListaConfig`. |
| `coerceJsonbToObject` / `coerceJsonbToArray` | [meta.js](../../../../frontend/src/core/utils/meta.js) | Coerce difensivo per valori JSONB serializzati da DB. Normalizza un valore `meta`/`snapshot`/`jsonb_agg` ad oggetto JS o ad array. Indispensabile contro la regressione "psycopg ritorna stringa JSON" che fa fallire silenziosamente `value.field` o `:value="arr"` su DataTable. Pass-through se gia' dict/array; parse se stringa JSON valida; fallback `{}` / `[]`. La variante array (2026-05-19) e' usata internamente da `ComponentiPanel` in modalita' data-driven (prop `initialData`) per i `componenti` aggregati nelle preview righe (`fn_contratto_righe_preview`, `fn_preview_riga_componenti`). |

---

## API Client (`src/core/`)

| Building Block | File | Descrizione |
|---|---|---|
| `api` | [api.js](../../../../frontend/src/core/api.js) | Istanza axios con JWT automatico e refresh 401 |
| `lookupCodici` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Lookup generico tabelle codici config |
| `lookupTipiSoggettoDettaglio` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Lista tipi soggetto (PF/PG/ENTE) |
| `lookupTipiRuoliPerNatura` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Tipi ruolo per natura soggetto |
| `lookupFormeGiuridiche` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Forme giuridiche per tipo soggetto |
| `lookupMatriceIndirizzi` / `lookupMatriceIndirizziRuolo` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Matrice tipi indirizzo per soggetto/ruolo |
| `lookupSistemaCodici` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Config sequenza codici (auto/manuale) |
| `searchComuni` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Ricerca comuni |
| `searchStradario` / `searchStradarioGenerale` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Ricerca stradario locale/nazionale |
| `fetchParameterDefaults` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Risolve N parametri di sistema con override utente (`GET /core/parameters/defaults/`) |
| `fetchParameterSettings(options)` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Lista parametri con livelli cascata `user > categoria_cliente > group > emittente > default` (`GET /core/parameters/settings/`). Accetta `options.categoria_cliente_id` o `options.billing_account_id` (post 2026-05-19, migration `20260519-01`): attiva colonna `categoria_cliente_value`/`categoria_cliente_override_id`. BE rifiuta valori non-positivi con `E_PARAMETER_VALIDATION` (400). |
| `upsertParameterOverride(code, value, scope, options)` / `deleteParameterOverride(id, scope, options)` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | CRUD override su `/core/parameters/settings/override/`. Scope: `'user'` (default) / `'emittente'` (admin) / `'categoria_cliente'` (admin, **Phase B 2026-05-19**, richiede `options.categoriaClienteId > 0`). Il BE rifiuta valori non-positivi (`E_PARAMETER_VALIDATION` 400) e accessi non-admin (`E_PERMISSION_DENIED` 403). Lo store `useParametersStore` invalida la cache del code post-write + cross-tab BroadcastChannel. |
| `lookupBillingAccount` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Ricerca BA per autocomplete cross-dominio (`GET /anagrafiche/billing-account/lookup/`). Scope emittente automatico |
| `getBillingAccountLookupById` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Restore singolo BA arricchito per edit (`GET /anagrafiche/billing-account/{id}/lookup/`) |
| `lookupIstanzeUtility` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Ricerca istanze utility per autocomplete cross-dominio (`GET /anagrafiche/istanze-utility/lookup/`). Filtri opzionali `utility_id` (strict) e `soggetto_id`. Scope emittente automatico via BA collegato. |
| `getIstanzaUtilityLookupById` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Restore singola istanza arricchita per edit (`GET /anagrafiche/istanze-utility/{id}/lookup/`) |
| `lookupContiContabili` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Lookup dedicato conti contabili con filtro tipo (`GET /core/lookup/conti-contabili/?tipo=A` o `?tipo=V`). Usato da `ContoContabileSelect`. |
| `lookupUomRoundingModes` | [catalogo.js](../../../../frontend/src/catalogo/api/catalogo.js) | Lookup statico modi di arrotondamento UoM operativa (`GET /catalogo/lookup/rounding-modes/`). Restituisce 5 codici fissi (HALF_UP, HALF_DOWN, HALF_EVEN, UP, DOWN) con descrizione. Single source of truth lato BE: `catalogo_service._ROUNDING_MODE_VALIDI`. Usato da `RoundingModeSelect`. |
| `lookupTipiVariazioneContratto` / `lookupTipiVariazionePromo` | [vendite/api/lookup.js](../../../../frontend/src/vendite/api/lookup.js) | Lookup statici tipi variazione vendite (Fase 2 refactor frontend). Contratto = solo `PERCENTUALE` post 2026-05-18 §3-bis-E; promo aggiunge `VALORE_FISSO` e `PREZZO_FISSO`. Single source of truth lato BE: `vendite_lookups_service`. Usati da `TipoVariazioneSelect`. |
| `lookupAmbitiContratto` | [vendite/api/lookup.js](../../../../frontend/src/vendite/api/lookup.js) | Lookup statico ambiti contratto (`COMMODITY`/`COMMERCIO`). Usato da `AmbitoContrattoSelect`. |
| `lookupListiniSelezionabiliContratto` | [vendite/api/lookup.js](../../../../frontend/src/vendite/api/lookup.js) | **Refactor 2026-05-18 §4.4.** Lookup dinamico listini selezionabili come riferimento contrattuale: filtra `vendite.listini` per esistenza di una versione ATTIVA. Payload `{id, codice, descrizione}` compatibile col pattern lookup generico — sostituisce `LookupSelect rel='vendite.listini'` nel `ContrattoDrawer` (cache via `useGlobalLookup` chiave `vendite.listini_selezionabili_contratto`). Single source of truth lato BE: `ListiniRepository.list_lookup_selezionabili_contratti`. Evita UX a doppio passo (selezione listino senza versione attiva → save rifiutato). |
| `getContrattoContestoPricing` | [vendite/api/contratti.js](../../../../frontend/src/vendite/api/contratti.js) | **Refactor modalita 2026-05-15 — banner contesto pricing contratto.** Ritorna forma derivata (con/senza listino), listino + versione (FISSATA se ATTIVO, CORRENTE se DRAFT), variazione globale, categoria cliente. Mutuato dal pattern preventivi `getContestoPricing`. Usato dal banner header di `ContrattoRigheDrawer`. |

**Refactor modalita 2026-05-15 — drop**:

- `lookupModalitaPricingContratto` **rimosso**. Nel modello unificato la "modalita" non e' piu' una scelta utente ma una forma derivata dai campi testata (listino_id valorizzato vs NULL). Il SelectButton A/B/C in `ContrattoDrawer` e' stato sostituito da campi opzionali (Listino + Variazione globale) con badge `forma_derivata` readonly post-save. Anche il parametro `VENDITE_CONTRATTO_DEFAULT_MODALITA` e' stato droppato.
| `getContrattoFormDefaults` / `getPreventivoFormDefaults` | [vendite/api/formDefaults.js](../../../../frontend/src/vendite/api/formDefaults.js) | **Fase 2.B3-B4 refactor frontend vendite.** Defaults form BA-aware. Param opzionale `billing_account_id`: se presente popola categoria_cliente_id_snapshot/utility (contratti) o valuta/termini/iva dal cliente del BA (preventivi). Sempre presenti `default_data`/`default_valido_dal`/`default_validita_al` da parameter. Single source of truth lato BE: `vendite_form_defaults_service`. |
| `getVersioneNewDefaults` / `getVersioneCloneDefaults` / `getVersioneCloseDefaults` | [vendite/api/formDefaults.js](../../../../frontend/src/vendite/api/formDefaults.js) | **Fase 2.B5a/b/c refactor frontend vendite.** Defaults contestuali alle versioni listino: nuova (existing_drafts + default_valido_dal), clone (codice + suffisso da parameter, min_valido_dal = source.valido_dal), close (default_valido_al = existing oppure oggi+lead_gg). Consumati da `VersioneFormDrawer`/`CloneVersioneDrawer`/`ChiudiVersioneDialog` al posto di `useParameterDefaults` cablato. |
| `getListaConfig` / `getListaCatalogo` / `putListaPreferenza` / `deleteListaPreferenza` | [core/api/ui-api.js](../../../../frontend/src/core/api/ui-api.js) | **Blocco D personalizzazioni liste.** 4 endpoint `/api/v1/ui/liste/{codice}/{config\|catalogo\|preferenza}/`. PUT preferenza richiede `Idempotency-Key` (caller la passa, generata via `crypto.randomUUID()` in `useListaConfig`). Single source of truth per `<ListaConfigurabile>`. |
| `makeNotesApi` | [core/api/notes.js](../../../../frontend/src/core/api/notes.js) | **Building block note partizionate (2026-05-19).** Factory `makeNotesApi(basePath, options?)` produce un set CRUD `{ listNote, getNota, createNota, updateNota, deleteNota }` bindato al basePath del dominio (es. `'/vendite/preventivi/42'`, `'/vendite/contratti/7'`, `'/catalogo/articoli/<uuid>'`). Idempotency-Key generata automaticamente sui POST tramite `generateIdempotencyKey`. Strip trailing slash + guard input. **Opzione `detailBase`** (2026-05-21): per domini con pattern URL "split" (LIST/POST sotto parent, DETAIL su endpoint generico) si passa `{ detailBase: '/catalogo' }` — es. catalogo usa `/catalogo/articoli/<id>/note/` per list/create ma `/catalogo/note/<id>/` per get/patch/delete. Consumato da `useNote` + wrapper di dominio (`PreventivoNoteDrawer`, `ContrattoNoteDrawer`, `ArticoloNoteDrawer`, `ArticoloBomDrawer` note componente). |
| `makeArticoloNotesApi` / `makeComponenteNotesApi` | [catalogo/api/catalogo.js](../../../../frontend/src/catalogo/api/catalogo.js) | **Wrapper di dominio (2026-05-21, Fase 2.B refactor UI drawer).** Producono il set CRUD note via `makeNotesApi` per articolo (`/catalogo/articoli/<uuid>`) o componente articolo (`/catalogo/articoli/<uuid>/componenti/<uuid>`), con `detailBase: '/catalogo'` per il pattern URL "split". Adottati da `ArticoloDrawer` (riepilogo note in panel) + `ArticoloNoteDrawer` + `ArticoloBomDrawer` (note componente). Sostituiscono il vecchio `CatalogoNoteDrawer` ad-hoc allineando catalogo allo standard partizionato `NoteDrawer`. |
| `makeComponentiBomApi` | [core/api/componentiBom.js](../../../../frontend/src/core/api/componentiBom.js) | **Building block componenti BoM di riga (2026-05-31, estrazione "regola del 2").** Factory `makeComponentiBomApi(basePath)` produce il set `{ previewRigaComponenti, listRigaComponenti, updateRigaComponente, deleteRigaComponente }` bindato al path base del dominio (`'/vendite/contratti'`, `'/vendite/preventivi'`). Schema URL identico per ogni dominio (`{base}/{parentId}/righe/[preview-componenti\|{rigaId}/componenti/...]`); nessuna Idempotency-Key (gli endpoint BE non la richiedono). Strip trailing slash + guard input. Gemello FE del pattern BE `make_note_views`/`PartitionedNoteRepository`. **Esclusa l'offerta**: usa path `eccezioni/` (divergenza voluta), resta nei propri metodi in `offerteApi.js`. Ri-esportato con gli stessi nomi da `contratti.js` e `preventiviApi.js` — i consumer (`ContrattoRigheDrawer`, `PreventiviRigaForm`, `PreventiviRigaComponentiPanel`, `usePreventivoRigaComponenti`) sono invariati. |

---

## Costanti (`src/core/constants.js`)

| Costante | Descrizione |
|---|---|
| `DRAWER_WIDTH` | Larghezze drawer per complessità (SIMPLE, STANDARD, COMPLEX, WIDE) |
| `TOAST_DURATION` | Durata toast per tipo (SUCCESS, WARN, ERROR, SYSTEM_ERROR) |
| `TIPO_RUOLO` | Codici interni tipi ruolo (CL, FO, GE, VE, DI, RE, VT, EF, BANK_B, RIS_UMANA, PSP) |
| `PAGINATION` | Paginazione default (`DEFAULT_ROWS` 25, `COMPACT_ROWS` 10 sotto tablet, opzioni [10, 25, 50, 100]) |
| `DATE_FORMAT` | Formato data PrimeVue centralizzato |
| `TABS` | Limite massimo tab aperte (10) |
| `BREAKPOINTS` | Breakpoint responsive (MOBILE, TABLET, DESKTOP_SPLIT) |
| `FIELD_LENGTH` | Vincoli lunghezza campi (IBAN_MAX) |
| `RUOLO_SISTEMA` | Enum ruoli sistema (ADMIN, OPERATIVO, DISABILITATO) |
| `LIVELLO_ACCESSO` | Enum livelli accesso (TUTTO, LETTURA, BLOCCATO) |
| `STATO_PRATICA` | Enum stati pratica (BOZZA, APERTA, SOSPESA, CHIUSA, ANNULLATA) |
| `STATO_FLUSSO` | Enum stati flusso (DA_ESEGUIRE, IN_CORSO, COMPLETATO, ecc.) |
| `MANAGE_ICONS` | Icone gestione riga centralizzate per dominio e azioni trasversali. Categorie: dominio (CONTATTI, INDIRIZZI, CONTI_BANCARI, UOM, BOM, NOTE, CONVERSIONI, VERSIONI, CONTRATTI, LISTINI, RIGHE), trasversali (EDIT, ADD, CONFIRM, CANCEL, PLAY, PUBLISH, CLONE, CLOSE, CLOSE_DATE, PERMISSIONS, BILLING_ACCOUNT, UTILITY, LIST, BUILDING, RELOAD, DOWNLOAD, DELETE, KEBAB), workflow (APPROVE, REJECT), **toggle dinamico (EXPAND `pi-chevron-down` / COLLAPSE `pi-chevron-up`)** per accordion/expansion row/tree — usare sempre dinamicamente: `icon: isExpanded ? COLLAPSE : EXPAND` |
| `SHORTCUTS` | Scorciatoie tastiera (Ctrl+K ricerca, Ctrl+Tab prossima tab, ecc.) |

---

## Navigazione e Storage (`src/core/`)

| Building Block | File | Descrizione |
|---|---|---|
| `DOMAINS` | [navigation.js](../../../../frontend/src/core/navigation.js) | Array configurazione domini (key, icon, path, schemaDb) |
| `DOMAIN_MENUS` | [navigation.js](../../../../frontend/src/core/navigation.js) | Voci menu per dominio (navigazione L2) |
| `resolveTabLabel` / `resolveTabIcon` | [navigation.js](../../../../frontend/src/core/navigation.js) | Risolve label/icona tab da route meta |
| `STORAGE_KEYS` | [storage.js](../../../../frontend/src/core/storage.js) | Chiavi localStorage/sessionStorage centralizzate |
| `local` / `session` | [storage.js](../../../../frontend/src/core/storage.js) | Wrapper localStorage/sessionStorage |
| `i18n` | [i18n.js](../../../../frontend/src/core/i18n.js) | Istanza Vue I18n (italiano default, inglese fallback) |

### Icone ERP custom

Le icone entita' ERP non coperte bene da PrimeIcons sono classi CSS centralizzate
in [main.css](../../../../frontend/src/assets/main.css) e usano `currentColor`:
`app-nav-icon-preventivi`, `app-nav-icon-contratti`, `app-nav-icon-ddt`,
`app-nav-icon-fatture`, `app-nav-icon-listini`. Esporle sempre tramite
`NAV_ICONS` o `MANAGE_ICONS`, non cablare le classi nei componenti.

---

## Classi CSS Utility (`src/assets/`)

I CSS globali sono organizzati in 3 file. Ogni classe è commentata nel sorgente.

### Variabili tema (`theme.css`)

| Gruppo | Variabili | Descrizione |
|---|---|---|
| Sidebar | `--app-sidebar-width`, `--app-sidebar-bg`, `--app-sidebar-item-*` | Dimensioni, colori, stati sidebar |
| Topbar | `--app-topbar-height`, `--app-topbar-bg`, `--app-topbar-breadcrumb-*` | Altezza, colori, breadcrumb |
| Contenuto | `--app-content-bg`, `--app-content-padding` | Sfondo e padding area principale |
| Card dominio | `--app-card-bg`, `--app-card-border`, `--app-card-hover-*` | Card home page |
| Logo | `--app-logo-size`, `--app-logo-radius` | Dimensioni logo |
| Login | `--app-login-card-*`, `--app-login-error-*` | Card e messaggi pagine auth |
| Toolbar | `--app-toolbar-height`, `--app-toolbar-bg`, `--app-toolbar-tab-*` | Barra secondaria sotto topbar |
| Icone | `--app-icon-color` | Colore standard icone informative |
| Drawer | `--app-drawer-gap`, `--app-drawer-section-border`, `--app-drawer-footer-border` | Gap contenuto, bordo sezioni, bordo footer |
| Transizioni | `--app-transition-fast`, `--app-transition-normal` | Durata animazioni |
| Tipografia | `--app-font-size-sm`, `--app-font-size-base`, `--app-font-size-lg` | Dimensioni font app |
| DataTable | `--app-table-font-size`, `--app-table-cell-padding`, `--app-table-stripe-bg`, `--app-table-hover-bg` | Stile tabelle compatte |
| Pulsanti riga | `--app-btn-manage-*`, `--app-btn-edit-*`, `--app-btn-delete-*`, `--app-btn-disabled-color` | Colori pulsanti gestione/modifica/elimina nelle DataTable |
| AI Assistant | `--app-ai-bg`, `--app-ai-border`, `--app-ai-header-bg`, `--app-ai-msg-*`, `--app-ai-shadow` | Widget AI: sfondo, bordi, messaggi, ombra |
| Preview | `--app-preview-bg`, `--app-preview-border`, `--app-preview-radius` | Riquadri anteprima |

**Dark/Light mode**: tutte le variabili sopra hanno un override in `:root:not(.p-dark)` per light mode.
Il toggle e' gestito dallo store `useUiStore` (`isDark`, `toggleDarkMode`) e persistito in `localStorage`.

### Classi layout pagina (`main.css`)

| Classe | Descrizione |
|---|---|
| `app-page` | Wrapper root di ogni view con DataTable — flex column full-height |
| `app-page-toolbar` | Barra filtri + azioni sopra la DataTable |
| `app-page-filters` | Gruppo filtri con flex-wrap |
| `app-page-actions` | Wrapper `PageActionsBar` per azioni pagina/lista |
| `app-page-actions-desktop` | Variante desktop di `PageActionsBar`: utility inline + menu secondarie |
| `app-page-actions-compact` | Variante touch/tablet/mobile di `PageActionsBar`: kebab popup |
| `app-tab-content` | Wrapper contenuto tab per DataTable flex (dentro TabPanel o diretto) |

### Classi form (`main.css`)

| Classe | Descrizione |
|---|---|
| `form-field` | Layout verticale label + input |
| `form-grid` | Colonna singola con gap tra campi |
| `form-grid-2col` | Griglia 2 colonne (collassa a 1 su mobile) |
| `form-grid-3col` | Griglia 3 colonne (collassa a 1 su mobile) |
| `form-row-inline` | Riga inline per affiancare campi (collassa su mobile) |
| `app-input-with-action` | Input con bottone azione affiancato (es. genera CF) |
| `app-field-error` | Messaggio errore sotto campo form |

### Classi drawer (`main.css`)

| Classe | Descrizione |
|---|---|
| `app-drawer-content` | Layout standard contenuto drawer (gap via `--app-drawer-gap`, tipografia h4). Include responsive uniforme: `min-width:0` + `overflow-x:auto` come safety net per contenuto non collassabile (tabelle, righe wide). |
| `app-drawer-section` | Separatore sezione nei drawer (bordo via `--app-drawer-section-border`) |
| `.p-drawer` (globale) | Regola globale `max-width: 100vw`: il drawer non eccede mai il viewport. Le `DRAWER_WIDTH` (`constants.js`) sono richieste massime — sotto soglia mobile/tablet il drawer riempie lo schermo. Vedi [frontend-standards.md §"Drawer"](frontend-standards.md). |
| `app-drawer-header-row` / `app-drawer-header-info` / `app-drawer-header-status` | Wrapper `DrawerEntityHeader`: riga flex con info inline a sinistra e Tag stato a destra |
| `app-drawer-header-muted` | Testo sottotono accanto ai Tag header (es. data documento) |
| `app-drawer-actions` | Wrapper `DrawerActionsBar` — flex row, gap 0.4rem, flex-wrap, margin-top 0.5rem |
| `app-drawer-actions-desktop` | Variante desktop di `DrawerActionsBar`: state+manage inline, secondary in kebab |
| `app-drawer-actions-compact` | Variante touch/<1024px di `DrawerActionsBar`: solo primary inline, resto in kebab |
| `app-drawer-action-wrap` / `app-drawer-action-badge` | Wrapper relative + badge counter sopra un pulsante `kind:'manage'` (es. counter righe) |
| `app-drawer-action-badge-dot` | Variante dot del badge per il kebab compact: segnala presenza counter senza mostrare il numero (il numero resta nella label della voce menu) |
| `app-drawer-footer` | Footer drawer con pulsanti allineati a destra |

### Classi DataTable (`main.css`)

| Classe | Descrizione |
|---|---|
| `app-datatable` | DataTable compatta con header/celle ridotte, righe alternate, hover e scroll orizzontale standard (`overflow: auto` sul container PrimeVue, `width: max-content; min-width: 100%` sulla tabella interna + soglie centralizzate dal root per liste da 8/10/12 colonne) |
| `app-datatable--inner` | Variante per liste annidate in drawer/expansion/sub-pannelli: padding piu' compatto, nessuna soglia larghezza da lista principale, tabella al 100% del contenitore |
| Paginator compatto | Font/padding ridotti — applicato automaticamente dentro `app-datatable` |

### Classi pulsanti (`main.css`)

| Classe | Descrizione | Uso |
| --- | --- | --- |
| `app-action-btn` | Pulsante azione form — icona verde (primary), no sfondo, grigio se disabilitato | "Aggiungi", pulsanti azione generici nei form |
| `app-manage-btn` | Pulsante gestione riga — icona blu (info), hover su sfondo blue-50 | Pulsanti "Gestisci" nelle colonne azione DataTable (UoM, BoM, Note) |
| `app-edit-btn` | Pulsante modifica riga — icona matita verde (primary), hover su sfondo primary-50 | Matita nelle DataTable e card liste |
| `app-delete-btn` | Pulsante elimina riga — icona cestino rosso, hover su sfondo red-50 | Cestino nelle DataTable e card liste |
| `app-reload-btn` | Pulsante ricarica lista — icona verde coerente | Refresh nelle toolbar lista |

**Pattern standard per pulsanti riga:**

```html
<!-- Gestione (apre sub-drawer) -->
<Button icon="pi pi-box" text rounded size="small" class="app-manage-btn" @click="onManage(data)" />
<!-- Modifica -->
<Button icon="pi pi-pencil" text rounded size="small" class="app-edit-btn" @click="onEdit(data)" />
<!-- Elimina -->
<Button :icon="MANAGE_ICONS.DELETE" text rounded size="small" class="app-delete-btn" @click="onDelete(data)" />
```

### Classi stato (`main.css`)

| Classe | Descrizione |
|---|---|
| `app-readonly` | Modalità sola lettura — blocca interazione, permette copia testo |
| `app-blocked` | Livello BLOCCATO — nasconde completamente il contenuto |
| `app-loading` | Spinner centrato |
| `app-empty-state` | Stato vuoto con icona grande + messaggio |
| `app-preview-box` | Riquadro anteprima (email, code, HTML) |

### Classi lookup dropdown multi-riga (`main.css`)

| Classe | Descrizione |
|---|---|
| `app-lookup-option` | Wrapper voce AutoComplete/Dropdown multi-riga. Layout column con gap via `--app-lookup-option-gap`, padding via `--app-lookup-option-padding` |
| `app-lookup-option__primary` | Riga principale (nome entita'). Font bold, supporta tag/badge inline con `flex-wrap` |
| `app-lookup-option__secondary` | Riga secondaria (codice, ruolo). Font 0.85rem |
| `app-lookup-option__meta` | Riga meta (id fiscale, PDP). Font 0.8rem, colore `--app-text-muted`, separatore `·` automatico tra span multipli |
| `app-lookup-hint` | Messaggio "affina la ricerca" sotto l'autocomplete quando `total > limit`. Border-top, colore muted |

**Uso tipico** (`BillingAccountLookup` e futuri lookup ricchi):

```html
<div class="app-lookup-option">
  <div class="app-lookup-option__primary">Rossi Mario <span class="p-tag">GAS</span></div>
  <div class="app-lookup-option__secondary">BA-000123</div>
  <div class="app-lookup-option__meta">
    <span>RSSMRA80A01H501U</span>
    <span>PDP: IT001E00012345</span>
  </div>
</div>
```

### Classi spacing (`main.css`)

| Classe | Descrizione |
|---|---|
| `mt-025` / `mt-05` / `mt-1` | Margin-top utility (0.25rem / 0.5rem / 1rem) |

### Pagine auth (`auth-pages.css`)

| Classe | Descrizione |
|---|---|
| `login-page` | Layout pagina auth — centrato, sfondo scuro |
| `login-card` / `login-card--large` | Card circolare login (390px / 430px) |
| `login-form` / `login-form--wide` | Form login (240px / 250px max-width) |
| `login-error` / `login-success` | Messaggi feedback rosso/verde |
| `back-link` / `forgot-link` | Link secondari pagine auth |

---

## Componenti Condivisi (`src/core/components/`)

### Layout

| Componente | File | Descrizione |
|---|---|---|
| `AppLayout` | [AppLayout.vue](../../../../frontend/src/core/components/AppLayout.vue) | Layout principale applicazione |
| `AppSidebar` | [AppSidebar.vue](../../../../frontend/src/core/components/AppSidebar.vue) | Sidebar responsive (desktop inline, mobile drawer) |
| `AppTopbar` | [AppTopbar.vue](../../../../frontend/src/core/components/AppTopbar.vue) | Topbar con ricerca e menu utente |
| `AppToolbar` | [AppToolbar.vue](../../../../frontend/src/core/components/AppToolbar.vue) | Toolbar secondaria con breadcrumb e azioni |
| `AppBreadcrumb` | [AppBreadcrumb.vue](../../../../frontend/src/core/components/AppBreadcrumb.vue) | Breadcrumb dinamico |
| `ContentTabs` | [ContentTabs.vue](../../../../frontend/src/core/components/ContentTabs.vue) | Tab tipo browser con split-view |
| `SidebarHome` | [SidebarHome.vue](../../../../frontend/src/core/components/SidebarHome.vue) | Stato home sidebar |
| `SidebarDomain` | [SidebarDomain.vue](../../../../frontend/src/core/components/SidebarDomain.vue) | Stato dominio sidebar con menu L2 |
| `SidebarItem` | [SidebarItem.vue](../../../../frontend/src/core/components/SidebarItem.vue) | Voce menu sidebar riutilizzabile |
| `FavoriteItem` | [FavoriteItem.vue](../../../../frontend/src/core/components/FavoriteItem.vue) | **Preferiti utente HOME + sidebar.** Render atomico di un preferito in variante `sidebar` o `tile`. Props principali: `domain`, `path`, `variant`, `collapsed`, `draggable`. Risolve label/icona/tooltip e navigazione tramite `useNavigationFavorites`; rimozione tramite `useNavigationStore`. Usato da `SidebarHome` e `HomeView` per evitare duplicazione UI/logica. |
| `SplitReadonlyPanel` | [SplitReadonlyPanel.vue](../../../../frontend/src/core/components/SplitReadonlyPanel.vue) | Pannello split-view con readonly forzato |
| `LogoBrand` | [LogoBrand.vue](../../../../frontend/src/core/components/LogoBrand.vue) | Logo e brand applicazione |

### Form

| Componente | File | Descrizione |
|---|---|---|
| `SoggettoForm` | [SoggettoForm.vue](../../../../frontend/src/core/components/SoggettoForm.vue) | Form soggetto universale PF/PG/ENTE |
| `IndirizzoSoggettoForm` | [IndirizzoSoggettoForm.vue](../../../../frontend/src/core/components/IndirizzoSoggettoForm.vue) | Form indirizzo multi-tipo per soggetti |
| `ContattoForm` | [ContattoForm.vue](../../../../frontend/src/core/components/ContattoForm.vue) | Form contatto (nominativo, email, telefono) |
| `DatiSocietariForm` | [DatiSocietariForm.vue](../../../../frontend/src/core/components/DatiSocietariForm.vue) | Form dati societari (REA, capitale, FE) |
| `ContoBancarioForm` | [ContoBancarioForm.vue](../../../../frontend/src/core/components/ContoBancarioForm.vue) | Form conto bancario (IBAN, BIC, uso) |
| `AuthUserForm` | [AuthUserForm.vue](../../../../frontend/src/core/components/AuthUserForm.vue) | Form auth utente (username, email, password) |

### Drawer

| Componente | File | Descrizione |
|---|---|---|
| `AppDrawer` | [AppDrawer.vue](../../../../frontend/src/core/components/AppDrawer.vue) | Wrapper drawer generico (create/edit). Footer = `FormFooter` integrato. |
| `AppDialog` | [AppDialog.vue](../../../../frontend/src/core/components/AppDialog.vue) | **Building block 2026-05-27.** Wrapper standard per Dialog modali "azione" (conferma, form one-shot). Mirror di `AppDrawer` per le Dialog. Incapsula chrome uniforme (modal/closable/closeOnEscape/dismissableMask), width da scala centralizzata `DIALOG_WIDTH` (`sm`/`md`/`lg`/`xl`, niente px hardcoded), `v-model:visible`, e **FormFooter integrato** di default (icone ←/✓, responsive icon-only, Ctrl+S). Props footer pass-through: `saveLabel`, `cancelLabel`, `saveSeverity` (`danger`/`warn` per azioni gravi), `saveDisabled`, `loading`, `closeOnly`. Slot `#footer` per override (terzo bottone, wizard); `hideFooter` per dialog informativi/viewer. Emits: `update:visible`, `save`, `cancel`. Adottato da ~16 dialog (offerte, listini, preventivi, componenti BoM, export, ecc.). |
| `DrawerTitle` | [DrawerTitle.vue](../../../../frontend/src/core/components/DrawerTitle.vue) | Titolo drawer + icona + chiudi |
| `FormFooter` | [FormFooter.vue](../../../../frontend/src/core/components/FormFooter.vue) | **Rinominato da `DrawerFooter` 2026-05-27.** Footer standard "Annulla/Salva" agnostico al contenitore (Drawer e Dialog). Icone ← (back) / ✓ (check), collapse responsive icon-only sotto 1024px, Ctrl+S, readonly-aware. Props: `saveLabel`, `cancelLabel`, `saveSeverity`, `loading`, `disabled`, `closeOnly`, `action`. |
| `DrawerEntityHeader` | [DrawerEntityHeader.vue](../../../../frontend/src/core/components/DrawerEntityHeader.vue) | **Refactor UI drawer 2026-05-21.** Header informativo standard dei drawer **di entità testata** (`ContrattoDrawer`, `PreventiviDrawer`, `OffertaDrawer`): numero/codice + badge contesto + data + Tag stato a destra. Puramente strutturale: default slot = info inline a sinistra, slot `#status` = Tag stato a destra. Espone la classe utility `.app-drawer-header-muted` per il testo data sottotono. Per i drawer di **figli/righe** (`ContrattoRigheDrawer`, `OffertaEccezioniDrawer`) usare invece `DrawerContextHeader` (sotto). |
| `DrawerContextHeader` | [DrawerContextHeader.vue](../../../../frontend/src/core/components/DrawerContextHeader.vue) | **Building block 2026-05-29 (regola del 2 — estratto da `ContrattoRigheDrawer` + `OffertaEccezioniDrawer`).** Header standard dei drawer **di figli/righe** che mostrano il contesto del padre. Layout 2-righe: **primary row** = Tag identificativo (numero/codice con contorno) + `items[0]` (es. Cliente) + slot `#status` per Tag stato a destra; **secondary row** = `items[1..N]` in griglia 2 colonne (es. valido_dal / valido_al). Ogni item è `{label muted + valore bold}`. Responsive: a `<768px` la primary row diventa column. Props: `tagValue` (string, default `null` → niente Tag), `tagSeverity` (default `'secondary'`), `items` (array di `{label, value, fallback?}`; `value` null/empty → `fallback` o `'—'`). Default slot opzionale per Tag identificativo custom (override del Tag generato). Pattern uniformato cross-dominio: numero+cliente+valido_dal+valido_al con label esplicite sempre visibili. |
| `DrawerActionsBar` | [DrawerActionsBar.vue](../../../../frontend/src/core/components/DrawerActionsBar.vue) | **Refactor UI drawer 2026-05-21.** Barra azioni di processo del drawer (sotto l'header), responsive CSS-first. Mirror di `PageActionsBar` per il contesto drawer + `kind:'state'` (transizioni `availableActions`) e `kind:'manage'` (sub-drawer con badge counter, es. "Gestisci righe (5)"). Desktop ≥1024px: `state`+`manage` inline con label, `secondary` nel kebab; touch/<1024px: solo `primary` inline, tutto il resto nel kebab unico. Applica `class="app-escape"` automaticamente a tutti i bottoni (compatibilità modalità readonly AS/400). Props: `actions`, `disabled`, `menuTooltip`. Slot `#prefix`/`#suffix`. Schema azione: `{ key, kind: 'primary'\|'state'\|'manage'\|'secondary', label, icon, severity?, badge?, tooltip?, visible?, disabled?, hideWhenReadonly?, action?, command }`. |
| `GenericConfigDrawer` | [GenericConfigDrawer.vue](../../../../frontend/src/core/components/GenericConfigDrawer.vue) | Drawer generico tabelle config **metadata-driven** (`information_schema` via `/core/config/tables/{rel}/metadata/`, CRUD generico, label = nome colonna grezzo). Per entità descrittive con store tipizzato + i18n + FK usare invece `EntityFormDrawer` (sotto). |
| `EntityFormDrawer` / `EntityFormField` | [EntityFormDrawer.vue](../../../../frontend/src/core/components/EntityFormDrawer.vue) / [EntityFormField.vue](../../../../frontend/src/core/components/EntityFormField.vue) | **Drawer CRUD schema-driven (2026-06-05, estrazione regola del 2 — 6 drawer geografici).** Per entità descrittive con **store tipizzato + label i18n + widget FK**, distinto da `GenericConfigDrawer` (metadata-driven). `EntityFormDrawer` orchestra form/`watch(visible)`/validazione required/`handleSave` (`execute` create\|update + `emit('saved')`/close + `store.fetchList()` se `refreshOnSave`); `EntityFormField` rende un campo per tipo (`text`/`select` via `useLookup`/`autocomplete` componente custom/`toggle`), riusato anche nei gruppi `form-grid-2col`. Props drawer: `store`, `mode`, `item`, `fields[]`, `titleKey`, `icon`, `width` (def SIMPLE), `successKeys{create,update}`, `refreshOnSave` (def true; `false` per liste con refresh via `useTabFreshness`). Schema campo: `{ name, type, labelKey, required?, maxlength?, lookupFn?, optionLabel?, optionValue?, placeholderKey?, component?, disabledInEdit?, editOnly?, default? }`; gruppo 2-col: `{ group:true, fields:[…] }`. Wrapper di dominio ~30 righe (es. `ProvinceDrawer`, `StatiDrawer`, `CodiciPostaliDrawer`, …). |
| `ContattiSoggettoDrawer` | [ContattiSoggettoDrawer.vue](../../../../frontend/src/core/components/ContattiSoggettoDrawer.vue) | Drawer contatto per soggetto |
| `IndirizziSoggettoDrawer` | [IndirizziSoggettoDrawer.vue](../../../../frontend/src/core/components/IndirizziSoggettoDrawer.vue) | Drawer indirizzo per soggetto |
| `ContiBancariDrawer` | [ContiBancariDrawer.vue](../../../../frontend/src/core/components/ContiBancariDrawer.vue) | Drawer conto bancario per soggetto |
| `ExportDialog` | [ExportDialog.vue](../../../../frontend/src/core/components/ExportDialog.vue) | **DEF-1 export liste — dialog modale generico**. Chiede all'utente il formato file (default CSV/Excel via `SelectButton` con icone) ed emette `@export(format)` al parent, che resta responsabile della chiamata API + download. Il dialog NON chiama il backend e NON gestisce il blob — separazione di responsabilita': il parent costruisce la query string con i filtri attivi, il dialog e' solo "form di scelta formato". Mostra hint UX coerente sul comportamento di salvataggio (dialog nativo OS via FS Access API su Chrome/Edge HTTPS, o cartella download default su Firefox/Safari) tramite `isFileSystemAccessSupported()`. Props: `visible` (v-model), `formati` (default `[csv, xlsx]`), `loading`. Dialog resta aperto su errore (es. 422 cap superato) per consentire all'utente di raffinare i filtri e riprovare. Pattern adottato da: `ClientiSearchTable` (DEF-1); riusabile in DEF-8. |
| `NoteDrawer` | [NoteDrawer.vue](../../../../frontend/src/core/components/NoteDrawer.vue) | **Building block note partizionate (2026-05-19).** Drawer riusabile cross-dominio per CRUD note su qualunque partizione `vendite.note_*` (preventivo, contratto, e in prospettiva ordini/DDT/fatture/AF). Pattern formMode (lista DataTable + form sotto, scope-ambito/posizione/seq decorati come Tag e colonne). Props: `visible`, `apiClient` (oggetto da `makeNotesApi(...)`), `title`, `supportsRiga` (abilita select RIGA nel form), `righeOptions` (array `{value, label}` per popolare il select riga). Default applicativi minimi (anchor_tipo/posizione governati dal BE); operatore tocca: testo (Textarea markdown), stile (`LookupSelect rel="config.note_stili"`), riga opzionale, switch visibile + solo_stampa. Watch reattivo a `[visible, apiClient]` per ricaricare quando il padre cambia parent id. Page size `PAGE_SIZE_DEFAULT=200` (cap BE). |
| `PreventivoNoteDrawer` / `ContrattoNoteDrawer` | [PreventivoNoteDrawer.vue](../../../../frontend/src/vendite/components/PreventivoNoteDrawer.vue) / [ContrattoNoteDrawer.vue](../../../../frontend/src/vendite/components/ContrattoNoteDrawer.vue) | Wrapper thin (~30 righe) sul building block `NoteDrawer`. Costruiscono `makeNotesApi('/vendite/preventivi/<id>')` o `'/vendite/contratti/<id>'` via computed (reattivo a cambio id padre) + adapter righe -> opzioni select `{value:id, label:"<codice_articolo> — <descrizione>"}`. Aggiungere un nuovo dominio note = clonare 30 righe e cambiare 4 token (basePath + titolo i18n). |

### Autocomplete

| Componente | File | Descrizione |
|---|---|---|
| `ComuneAutocomplete` | [ComuneAutocomplete.vue](../../../../frontend/src/core/components/ComuneAutocomplete.vue) | Autocomplete comune server-side |
| `StradarioAutocomplete` | [StradarioAutocomplete.vue](../../../../frontend/src/core/components/StradarioAutocomplete.vue) | Autocomplete stradario locale |
| `StradarioGeneraleAutocomplete` | [StradarioGeneraleAutocomplete.vue](../../../../frontend/src/core/components/StradarioGeneraleAutocomplete.vue) | Autocomplete stradario nazionale |

### Lookup e Select

| Componente | File | Descrizione |
|---|---|---|
| `LookupSelect` | [LookupSelect.vue](../../../../frontend/src/core/components/LookupSelect.vue) | Select generico per tabelle lookup whitelisted (`id, codice, descrizione`). Prop `rel` mappa alla whitelist in `dbops_repository.py` (~45 tabelle). Sostituisce il pattern `useLookup(() => lookupCodici(...))` + `<Select>`. Props: `rel` (obbligatorio), `placeholder`, `label-field` (default `descrizione`), `value-field` (default `id`), `show-clear`, `filter` (default true), `disabled`, `show-code` (mostra `"descrizione (codice)"` sia in display che dropdown — usa gli slot PrimeVue `#option` e `#value`). Emette `@change`. |
| `IvaSelect` | [IvaSelect.vue](../../../../frontend/src/core/components/IvaSelect.vue) | **Wrapper standard IVA.** Incapsula `LookupSelect rel="config.iva"` con `show-code` attivo. Da usare ovunque servano combo IVA per garantire display uniforme (`"descrizione (codice)"`). Props: `modelValue`, `placeholder`, `disabled`, `showClear` (default true). Usato da: ArticoloDrawer, ClienteDrawer, PreventiviRigaForm. |
| `ContoContabileSelect` | [ContoContabileSelect.vue](../../../../frontend/src/core/components/ContoContabileSelect.vue) | **Wrapper standard conti contabili** filtrati per tipo. Usa l'endpoint dedicato `GET /core/lookup/conti-contabili/?tipo=A` o `?tipo=V` (non il lookup generico, perche' espone `tipo_conto`). Props: `modelValue`, `tipo` (obbligatorio, `'A'` acquisto o `'V'` vendita, validator), `placeholder`, `disabled`, `showClear`. Display `"descrizione (codice)"`. Un'unica combo gestisce entrambi i tipi tramite la prop. Usato da: ArticoloDrawer (conto vendita V + conto acquisto A). |
| `UtilityPerRuoloSelect` | [UtilityPerRuoloSelect.vue](../../../../frontend/src/core/components/UtilityPerRuoloSelect.vue) | Select riusabile per scegliere una utility ammessa per un dato tipo ruolo (filtro strict da `config.utilities_tipi_ruolo`). Endpoint: `GET /core/lookup/tipi-ruolo/<codice>/utilities/`. Props: `tipoRuoloCodice` (obbligatorio, es. `'EF'`/`'FO'`/`'CL'`), `placeholder`, `showClear`, `filter`, `disabled`, `labelField`. Emette `@change`. Usa `lookupUtilitiesPerRuolo` da `apiCore.js`. |
| `ArticoloLookup` | [ArticoloLookup.vue](../../../../frontend/src/core/components/ArticoloLookup.vue) | Autocomplete articolo server-side cross-dominio. Props: `modelValue`, `filtri` (oggetto contestuale), `soloAttivi` (default `true`), `placeholder`, `disabled`. Emette `@select` e `@update:modelValue`. Usa `optionLabel` PrimeVue 4, `minLength: 3`. **Prop `filtri`**: shape `{ soloComponenti?, compositi? }`, enum tri-stato `'qualsiasi' \| 'escludi' \| 'solo'` (default `'qualsiasi'` = nessun filtro). Mappato a `is_solo_componente` / `is_composito` lato BE `fn_lookup_articoli`. Valori sconosciuti → warn console + fallback a `'qualsiasi'`. Usato da: `PreventiviRigaForm` + `ContrattoRigheDrawer` (AGGIUNTA) + `PromoArticoloDrawer` (`soloComponenti:'escludi'`), `VersioneDrawer` righe listino (`soloComponenti:'escludi'` + `compositi:'escludi'`), `ArticoloBomDrawer` figlio BoM (`compositi:'escludi'`), `TestResolverDialog` ×2 (target libero + padre contesto `compositi:'solo'`). Cablaggio: piano [piano-filtri-articolo-lookup](../work-done/piano-filtri-articolo-lookup.md). |
| `BillingAccountLookup` | [BillingAccountLookup.vue](../../../../frontend/src/core/components/BillingAccountLookup.vue) | Autocomplete BA server-side cross-dominio con ricerca ricca (codice, ragione sociale, id fiscale, PDP). Dropdown a 3 righe via classe `app-lookup-option`. Props: `utilityId`, `soloValidi` (default `true`), `validAt`, `placeholder`, `disabled`. Emette `@select`, `@clear`. Footer "affina la ricerca" quando `total > limit`. `minLength: 2`. Scope emittente automatico lato backend. Usato da: righe listino associazioni; esteso a preventivi/ordini/fatture/pratiche. |
| `IstanzaUtilityLookup` | [IstanzaUtilityLookup.vue](../../../../frontend/src/core/components/IstanzaUtilityLookup.vue) | Autocomplete istanze_utilities server-side cross-dominio. Ricerca multi-campo (codice istanza, ragione sociale soggetto, indirizzo normalizzato). Dropdown a 3 righe (primary: ragione sociale + tag utility + badge "Solo istanza"/"Fittizia"; secondary: codice istanza; meta: indirizzo + codice BA campione). Props: `utilityId` (strict, post Strategia C), `soggettoId` (UUID), `placeholder`, `disabled`. Emette `@select`, `@clear`. Auto-reset selezione al cambio di `utilityId` se l'istanza dichiara utility incoerente. `minLength: 2`. Scope emittente automatico lato backend (via BA collegato). Usato da: `PreventiviForm` (drawer prospect senza BA); riusabile in future utility-aware flows. |
| `EmittenteFiscaleField` | [EmittenteFiscaleField.vue](../../../../frontend/src/core/components/EmittenteFiscaleField.vue) | **Campo emittente fiscale auto-adattivo** (3 rami: edit→testo read-only dal record; create+admin globale→Select dal lookup admin; create+operatore→testo read-only dal profilo). Lazy load del lookup gestito internamente (parte solo nel ramo Select). Espone errore di fetch via Message inline. Props: `modelValue` (id), `record` (per leggere `emittente_fiscale_codice`/`descrizione` denormalizzati in edit), `isEdit`, `disabled`, `noneI18nKey`/`placeholderI18nKey`/`errorI18nKey` (overridable). Il consumer non gestisce direttamente l'autopopulate: usa `useEmittenteFiscaleField().defaultEmittenteId` come default form. Adottato da: `TemplateDocumentoDrawer`, `TemplateAssetDrawer`. |
| `ListaConfigurabile` | [ListaConfigurabile.vue](../../../../frontend/src/core/components/ListaConfigurabile.vue) | **Blocco D personalizzazioni liste — wrapper PrimeVue DataTable parametrizzato dalla config BE.** Prop `codice` + `rows`/`total`/`loading`/`page`/`sortField`/`sortOrder` controllati dal caller. Costruisce le colonne dinamicamente da `useListaConfig().config.colonne` ordinate; applica `tipo_colonna='azione'` come Column separata via slot `actions`; `fissata=true` come `frozen`; `esportabile=false` esclude dall'export PrimeVue. Lo stato configurazione (badge `Temporanea — non salvata`) lo mostra il wrapper SearchTable via `<ListaConfigStatusTag>`; pulsante personalizza con badge `colonne_nuove`. Slot dinamico `cell-{codice}` per body cell custom; fallback formatter built-in da `formato` (`date_short`, `currency_eur`, `percent_2`, `yesno`, ecc.). Slot `filters` e `actions-extra` per la toolbar. Eventi: `@page`, `@sort`, `@row-click`, `@config-loaded`. |
| `ListaConfigStatusTag` | [ListaConfigStatusTag.vue](../../../../frontend/src/core/components/ListaConfigStatusTag.vue) | **Badge stato configurazione lista (2026-06-03, estrazione regola del 2 + UX).** `<ListaConfigStatusTag :dirty />` nel suffix della `PageActionsBar` delle SearchTable. Mostra il Tag warn "Temporanea — non salvata" **solo** quando `dirty` (modifiche personalizzazione colonne non salvate). Il precedente Tag success "Configurazione salvata" (permanente, non azionabile) è stato **rimosso**: nello stato di riposo nessun badge. Centralizza il blocco prima duplicato in 7 SearchTable (clienti/fornitori/soggetti/contratti/offerte/ordini/preventivi). |
| `CellaConfigurabile` | [CellaConfigurabile.vue](../../../../frontend/src/core/components/CellaConfigurabile.vue) | **Rendering cella di `<ListaConfigurabile>` (2026-06-02, estrazione regola del 2).** Render-function component: se il caller fornisce lo slot `cell-{codice}` lo invoca direttamente (prop `cellSlot` = `$slots['cell-<codice>']`), altrimenti applica il formatter built-in da `formato` (`date_short`, `datetime`/`datetime_short`, `currency_eur`, `number`, `percent_2`, `yesno`). Estratto perché lo stesso blocco era duplicato fra Column `#body` e riga di espansione `#expansion`. Props: `col`, `data`, `cellSlot`. |
| `ListaColonneModal` | [ListaColonneModal.vue](../../../../frontend/src/core/components/ListaColonneModal.vue) | **Blocco D — modale di personalizzazione colonne.** PrimeVue Drawer right 520px. Props: `visible`, `config`, `catalogo`, `colonneNuove`, `loading`, `codice`. Lavora su copia locale `localColonne` — propaga al genitore solo a "Salva" (emit `apply` con `{colonne}`). Reset preferenza tramite `useConfirmAction.confirmAction` con `danger=true`. Toggle visibilità disabilitato per `tipo_colonna IN ('identificatore','azione')` (tooltip esplicativo). Riordino tramite ▲/▼ (no drag-and-drop esterno: zero dipendenze). Edit larghezza inline via `InputNumber`. Colonne raggruppate per `gruppo`/`gruppo_ordine` del catalogo. |

### Ricerca

| Componente | File | Descrizione |
|---|---|---|
| `SearchDrawer` | [SearchDrawer.vue](../../../../frontend/src/core/components/SearchDrawer.vue) | Ricerca universale full-text con selezione contesto |
| `GeoSearchTable` | [GeoSearchTable.vue](../../../../frontend/src/core/components/GeoSearchTable.vue) | **Lista "semplice" parametrica (2026-06-05, estrazione regola del 2 — 6 SearchTable geografiche).** Per le liste paginate di base **senza** personalizzazione colonne (pre-blocco-D), distinta da `useListaConfigurabilePage` (liste "ricche" con `<ListaConfigurabile>`). Incapsula `useSearchTable` + toolbar (InputText ricerca + `PageActionsBar` con `reloadAction()` che porta il disable-su-lista-vuota + azione "Nuovo") + `useTabFreshness` + `onMounted(fetchList)` + DataTable `app-datatable`. Props: `store`, `columns` (`[{field,headerKey,sortable?}]`), `searchPlaceholderKey`, `newTooltipKey`, `tabEntity` (valore `TAB_ENTITIES`), `defaultSortField` (def `descrizione`), `rowClickable` (def true; `false` per liste sola-creazione). Emette `row-click`/`new`. Slot scoped: `filters` (espone `applyFilters`, per filtri extra es. `ComuneAutocomplete`), `cell-<field>` (cella custom, es. `AttivoTag`). Wrapper di dominio ~20 righe (`RegioniSearchTable`, `ComuniSearchTable`, `CodiciPostaliSearchTable`, …). |
| `ConfigTablePanel` | [ConfigTablePanel.vue](../../../../frontend/src/core/components/ConfigTablePanel.vue) | Pannello tabella config generico |
| `SearchHint` | [SearchHint.vue](../../../../frontend/src/core/components/SearchHint.vue) | Hint per campi di ricerca |
| `PaginationInfo` | [PaginationInfo.vue](../../../../frontend/src/core/components/PaginationInfo.vue) | Metadata paginazione (es. "1-25 di 100") |
| `SearchDetailTable` | [details/SearchDetailTable.vue](../../../../frontend/src/core/components/details/SearchDetailTable.vue) | Tabella dettaglio espandibile per ricerca |
| `DetailActions` | [details/DetailActions.vue](../../../../frontend/src/core/components/details/DetailActions.vue) | Pulsanti azione per vista dettaglio |

### Supporto

| Componente | File | Descrizione |
|---|---|---|
| `PageActionsBar` | [PageActionsBar.vue](../../../../frontend/src/core/components/PageActionsBar.vue) | Barra azioni pagina/lista responsive. Props: `actions`, `disabled`, `menuTooltip`. Ogni azione espone `key`, `kind`, `label`, `icon`, `tooltip`, `visible`, `disabled`, `hideWhenReadonly`, `action`, `command`. Standard per `refresh + nuovo` e toolbar con utility extra. |
| `NewButton` | [NewButton.vue](../../../../frontend/src/core/components/NewButton.vue) | Pulsante "Nuovo" specializzato legacy/non-toolbar; nelle liste usare `PageActionsBar` |
| `RowActionsMenu` | [RowActionsMenu.vue](../../../../frontend/src/core/components/RowActionsMenu.vue) | Azioni di riga responsive. Props: `actions`, `row`, `tooltip`, `disabled`, `disableWhenInactive`. Se `row.attivo === false` o `row.is_active === false`, disabilita automaticamente le azioni operative salvo `allowWhenInactive: true` sulla singola azione (es. riattiva/storico/modifica quando la matita e' l'entrypoint del form). |
| `StatusPage` | [StatusPage.vue](../../../../frontend/src/core/components/StatusPage.vue) | Pagine errore/forbidden/not-found |
| `TagList` | [TagList.vue](../../../../frontend/src/core/components/TagList.vue) | Lista tag/label riutilizzabile |
| `AttivoTag` | [AttivoTag.vue](../../../../frontend/src/core/components/AttivoTag.vue) | **Tag stato Attivo/Non attivo (2026-06-05, estrazione regola del 2 — 26 siti).** Sostituisce il ternario inline `<Tag :value="x.attivo ? active : inactive" :severity="x.attivo ? 'success' : 'warn'" />` ripetuto in liste e drawer. Props: `active` (Boolean, **booleano già risolto** dal caller — non il path del campo, che varia `attivo`/`emittente_attivo`/`is_active`/`row.attivo`), `activeLabel`/`inactiveLabel` (default `t('common.active')`/`t('common.inactive')`; il caller passa `t(...)` già tradotto per le famiglie i18n diverse: `common.yes/no`, `amm.email_*`, `indirizzi.*`, `config_panel.*`, `search.status_*`, `portale.profile.*`), `inactiveSeverity` (default `'warn'`; usato `'danger'` da `SearchDetailTable`, `'secondary'` da `ProfileView`). Severity attiva sempre `'success'`. NB: non copre il caso `<Badge>` (es. `EmittentiFiscaliListView`, elemento diverso). |
| `SoggettoResolver` | [SoggettoResolver.vue](../../../../frontend/src/core/components/SoggettoResolver.vue) | Mostra nome soggetto da ID |
| `SoggettoPreviewBadges` | [SoggettoPreviewBadges.vue](../../../../frontend/src/core/components/SoggettoPreviewBadges.vue) | Badge preview soggetto (chip tipo_ruolo) |
| `SoggettoMessageBanner` | [SoggettoMessageBanner.vue](../../../../frontend/src/core/components/SoggettoMessageBanner.vue) | Banner messaggi stato soggetto |
| `SessioniAttivePanel` | [SessioniAttivePanel.vue](../../../../frontend/src/core/components/SessioniAttivePanel.vue) | Pannello sessioni attive (readonly) |
| `AiAssistantDrawer` | [AiAssistantDrawer.vue](../../../../frontend/src/core/components/AiAssistantDrawer.vue) | Interfaccia chat assistente AI |

### Lookup geografico (condivisi)

| Componente | File | Descrizione |
|---|---|---|
| `ComuneDrawer` | [ComuneDrawer.vue](../../../../frontend/src/core/components/ComuneDrawer.vue) | Drawer comune |
| `ProvinceDrawer` | [ProvinceDrawer.vue](../../../../frontend/src/core/components/ProvinceDrawer.vue) | Drawer provincia |
| `RegioniDrawer` | [RegioniDrawer.vue](../../../../frontend/src/core/components/RegioniDrawer.vue) | Drawer regione |
| `StatiDrawer` | [StatiDrawer.vue](../../../../frontend/src/core/components/StatiDrawer.vue) | Drawer stato/nazione |
| `CodiciPostaliDrawer` | [CodiciPostaliDrawer.vue](../../../../frontend/src/core/components/CodiciPostaliDrawer.vue) | Drawer codice postale |
| `ToponomasticaDrawer` | [ToponomasticaDrawer.vue](../../../../frontend/src/core/components/ToponomasticaDrawer.vue) | Drawer tipo strada |

---

## Componenti Dominio Catalogo (`src/catalogo/components/`)

### Drawer articolo e sub-drawer

| Componente | File | Descrizione |
| --- | --- | --- |
| `ArticoloDrawer` | [ArticoloDrawer.vue](../../../../frontend/src/catalogo/components/ArticoloDrawer.vue) | Drawer crea/modifica articolo. Combo conti contabili vendita/acquisto, auto-propose IVA da parameters. In edit: riepilogo UoM/BoM/Note con pulsante "Gestisci" che apre sub-drawer. Contenuto deferito (`@after-show`) per evitare rimbalzi. |
| `ArticoloUomDrawer` | [ArticoloUomDrawer.vue](../../../../frontend/src/catalogo/components/ArticoloUomDrawer.vue) | Sub-drawer UoM operative. Pattern formMode (null=lista DataTable, 'new'=aggiungi, 'edit'=modifica). Props: `visible`, `articolo-id`. Emette `@saved`. |
| `ArticoloBomDrawer` | [ArticoloBomDrawer.vue](../../../../frontend/src/catalogo/components/ArticoloBomDrawer.vue) | Sub-drawer distinta base. Lista componenti sempre visibile + form inserimento sotto. `valido_al` editabile inline nella DataTable. Lookup articoli via `ArticoloLookup`. Props: `visible`, `articolo-id`. Emette `@saved`. |
| `ArticoloNoteDrawer` | [ArticoloNoteDrawer.vue](../../../../frontend/src/catalogo/components/ArticoloNoteDrawer.vue) | **Refactor 2026-05-21 (Fase 2.B).** Wrapper thin (~35 righe) sul building block `NoteDrawer` + `makeArticoloNotesApi`. Pattern simmetrico a `PreventivoNoteDrawer`/`ContrattoNoteDrawer`. Sostituisce il vecchio drawer ad-hoc (`CatalogoNoteDrawer`, droppato). Props: `visible`, `articolo-id` (UUID). Emette `@saved`. |
| `RoundingModeSelect` | [RoundingModeSelect.vue](../../../../frontend/src/catalogo/components/RoundingModeSelect.vue) | **Wrapper standard modi arrotondamento UoM operativa.** Usa `useGlobalLookup` (chiave `catalogo.uom_rounding_modes`) sul lookup statico `lookupUomRoundingModes` con cache modulo-level. Display `"descrizione (codice)"`. Props: `modelValue` (string codice), `placeholder`, `disabled`, `showClear`. Sostituisce il vecchio `roundingOptions` hardcoded. Usato da: ArticoloUomDrawer (Fase 1 refactor catalogo). |


---

## Componenti Dominio Vendite (`src/vendite/components/`)

### Wrapper select per enum di dominio (Fase 2 refactor frontend)

| Componente | File | Descrizione |
| --- | --- | --- |
| `TipoVariazioneSelect` | [TipoVariazioneSelect.vue](../../../../frontend/src/vendite/components/TipoVariazioneSelect.vue) | **Wrapper standard tipo_variazione.** Prop `scope` discrimina `'contratto'` (PERCENTUALE/VALORE_FISSO) vs `'promo'` (+ PREZZO_FISSO). Cache modulo-level via `useGlobalLookup` con chiavi `vendite.tipi_variazione.<scope>`. Display `"descrizione (codice)"`. Sostituisce `tipoVariazioneOptions` cablato in `ContrattoDrawer` e `PromoArticoloDrawer`. |
| `AmbitoContrattoSelect` | [AmbitoContrattoSelect.vue](../../../../frontend/src/vendite/components/AmbitoContrattoSelect.vue) | **Wrapper standard ambito contratto** (COMMODITY/COMMERCIO). Cache `vendite.ambiti_contratto`. Sostituisce `ambitoOptions` cablato. |

### Building block Componenti BoM shared (`src/vendite/_shared/componenti/`)

Famiglia di 3 building block riusabili dalle 4 sorgenti documento composito (preventivi, contratti, ordini, ddt) + listini bundle. Modello unificato 2026-05-13 (padre = SUM figli × coeff_qta). Estratti in Fase H 2026-05-14 per evitare duplicazione cross-sorgente.

| Componente | File | Descrizione |
| --- | --- | --- |
| `ComponentiDialog` | [ComponentiDialog.vue](../../../../frontend/src/vendite/_shared/componenti/ComponentiDialog.vue) | **CREATE.** Dialog modale per pre-popolare prezzi componenti BoM prima del save della riga padre composita. Auto-apertura su selezione articolo composito + UoM + qta valida. Props: `articolo`, `documentoId`, `uomOperativaId`, `quantita`, `apiPreview` (callback sorgente-specific), `initialPayload`, `showPrezzoSuggerito` (default true; false per listino bundle), `i18nPrefix`, `emitAllPrices`. Emette `@confirm(payload)` con `{overrides, summary}`. |
| `ComponentiPanel` | [ComponentiPanel.vue](../../../../frontend/src/vendite/_shared/componenti/ComponentiPanel.vue) | **Panel unificato BoM** (fetch-driven + data-driven, refactor 2026-05-19). Tre modalita' di uso decise al setup in base alle prop passate: (1) **fetch-driven readonly** (expander DataTable righe persistite): apiList(documentoId, rigaId, {soloAttivi}) → tabella read-only; (2) **fetch-driven editabile** (drawer riga, `readonly=false`): apiList + apiUpdate per edit inline prezzo per componente + apiDelete; (3) **data-driven readonly** (prop `initialData` valorizzata): salta la fetch e rende direttamente l'Array o la stringa JSON aggregata da DB (`fn_contratto_righe_preview`, `fn_preview_riga_componenti`). In data-driven le api callback non sono obbligatorie e `readonly` e' forzato. Normalizer interno mappa lo shape JSONB preview (`prezzo`, `coeff_qta`, `componente_id`) sullo shape persistito (`prezzo_unitario`, `quantita`, `id`); le colonne metadata (origine/approvazione/IVA) si auto-nascondono quando nessuna riga visibile ha quei campi (preview = solo dati base). La label della colonna q.ta' diventa "Coeff." quando viene dal preview, "Q.tà" quando viene da snapshot persistito. Props: `documentoId`, `rigaId`, `readonly`, `initialData`, `apiList/apiUpdate/apiDelete`, `tabEntity`, `i18nPrefix`. |
| `rowComponenti` / `hasBundleComponenti` | [rowComponenti.js](../../../../frontend/src/vendite/_shared/componenti/rowComponenti.js) | **Helper puri (2026-05-31, estrazione "regola del 2").** Funzioni pure sulla shape `{ is_composito, componenti }` delle preview vendite (`fn_contratto_righe_preview`, `fn_preview_riga_componenti`): `rowComponenti(row)` normalizza il `jsonb_agg` figli ad array via `coerceJsonbToArray` (coerce difensivo anti "psycopg ritorna stringa JSON"); `hasBundleComponenti(row)` discrimina il chevron expander (bundle composito con ≥1 figlio). Erano duplicati identici in `ContrattoRigheDrawer` e `OffertaEccezioniDrawer`. Util e non composable: nessuno stato reattivo. |
| `useComponentiDialog` | [useComponentiDialog.js](../../../../frontend/src/vendite/_shared/componenti/useComponentiDialog.js) | **Composable orchestrazione ComponentiDialog (2026-05-31, estrazione "regola del 2" #3).** Centralizza per i 3 drawer riga (preventivi, offerte, contratti) lo stato dialog (`componentiDialogVisible`/`componentiPayload`), `showComponentiDialog` (auto-apertura in CREATE su articolo composito + UoM + qta valida), watch auto-open su `[articolo_id, uom_operativa_id]` con guardia anti-riapertura, `onComponentiConfirm` (anteprima prezzo padre `total/qtaPadre`), `apriComponentiDialog`, `resetComponentiDialog`. Differenze di dominio come **getter** dal chiamante: `isCreate` (`!isEdit` \| `formMode==='create'`), `isComposito`, `isPadreComposito` (CASO A o is_composito \| is_composito), `qtaValida` (default `qta_operativa <> 0`; offerte passano `()=>true` perché la qta può essere null per CONSUMO/LETTURE). Abilitato dal refactor `qta_operativa` che ha reso uniforme il campo quantità sorgente nei 3 drawer (vedi `refactor-quantita-qta-operativa.md`). |
| `PreventivoNoteDrawer` / `ContrattoNoteDrawer` wrapper note | (vedi sezione Componenti Condivisi → Drawer) | — |

---

## Documenti / Stampa (`src/documenti/`)

Building block trasversali per la **stampa PDF** di qualunque entità documentale
(motore `documenti` lato BE). Oggi consumati da preventivi, offerte commerciali,
contratti e **ordini di vendita** (sorgente `ORDINE_VENDITA`, 2026-06-04). Per
cablare un nuovo dominio sorgente bastano 3 mosse, **senza nuovi componenti**:
(1) aggiungere il codice a `SORGENTE_CODES`; (2) creare un client con
`buildSorgenteClient(basePathFn)` + entry in `SORGENTE_CLIENT_MAP`; (3) montare
`EntityPdfButton` nel drawer. Regola del 2 (memoria
`feedback_regola_del_2_estrai_bb`): il pulsante è stato estratto dall'unione dei
tre cloni `*PdfButton.vue`.

### Componenti (`src/documenti/components/`)

| Componente | File | Scopo |
| --- | --- | --- |
| `EntityPdfButton` | [EntityPdfButton.vue](../../../../frontend/src/documenti/components/EntityPdfButton.vue) | Pulsante PDF **stato-aware**. Props: `sorgenteCode`, `entityId`, `statoCodice`, `statiPreview` (→ modalità *preview*: anteprima on-the-fly via `store.anteprima`, no persist), `statiConDocumento` (→ modalità *scarica*: apre `PdfDocumentiSorgenteDialog` con l'archivio), `statiAppendAllegati` (abilita append nel dialog), `i18nPrefix` (es. `'vendite.ordini.pdf'` → risolve `label_anteprima`/`tooltip_anteprima`/`label_scarica`/`tooltip_scarica`), `dialogTitle` (già t-formattato). Stato fuori dai due set → bottone *disabled*. Blob via `downloadBlob` (fuori da `useApiHandler`). |
| `PdfDocumentiSorgenteDialog` | [PdfDocumentiSorgenteDialog.vue](../../../../frontend/src/documenti/components/PdfDocumentiSorgenteDialog.vue) | Wrapper `AppDialog` attorno a `DocumentiGeneratiSorgenteList` (con `defaultExpanded`). Props: `visible` (v-model), `sorgenteCode`, `sorgenteId`, `title` (default `documenti.lista.title`), `allowAllegati`. UX picker: mostra subito principale + allegati. |
| `DocumentiGeneratiSorgenteList` | [DocumentiGeneratiSorgenteList.vue](../../../../frontend/src/documenti/components/DocumentiGeneratiSorgenteList.vue) | Lista timeline documenti generati (`generato_at DESC`). Azioni di riga via `RowActionsMenu`: download PDF; append allegati se `allowAllegati`. Row-expand lazy → file (principale + allegati) con cache `filesPerDoc`. Props: `sorgenteCode`, `sorgenteId`, `autoFetch` (def true), `hideHeaderWhenEmpty`, `allowAllegati`, `defaultExpanded`. v1: niente azioni stato/eliminazione (trigger DB block_delete). |

### Store, API, costanti (`src/documenti/`)

| BB | File | Scopo |
| --- | --- | --- |
| `useDocumentiPerSorgenteStore` | [stores/documentiPerSorgente.js](../../../../frontend/src/documenti/stores/documentiPerSorgente.js) | Store Pinia **`userScoped: true`** (PDF/progressivi legati a una sorgente, no leak al cambio account). Stato scoped alla coppia `(sorgenteCode, sorgenteId)`: il caller chiama `setSorgente(code,id)` al cambio. Azioni: `fetchList`, `genera` (persiste + `emitDataChanged` + refetch), `anteprima`/`download`/`downloadFile` (ritornano `{blob, fileName}` da Content-Disposition), `listFiles`, `aggiungiAllegati`. `getClient()` risolve via `SORGENTE_CLIENT_MAP` (throw sincrono se il codice non è mappato — bug FE). |
| `buildSorgenteClient` + client per sorgente | [api/documentiPerSorgente.js](../../../../frontend/src/documenti/api/documentiPerSorgente.js) | Factory client API su path nidificato `basePathFn(id)` (es. `/vendite/ordini/<id>/documenti`). Metodi: `list`, `genera`, `anteprima`/`download`/`downloadFile` (`responseType:'blob'`), `listFiles`, `aggiungiAllegati` (multipart). Istanze esportate: `preventivoDocumenti`, `contrattoDocumenti`, `offertaDocumenti`, `ordineDocumenti`. |
| `SORGENTE_CODES` | [constants.js](../../../../frontend/src/documenti/constants.js) | Enum codici sorgente documentale (`PREVENTIVO`/`CONTRATTO`/`OFFERTA_COMMERCIALE`/`ORDINE_VENDITA`), allineati al registry BE e a `config/constants/documentiContextBuilders.js` (whitelist editor template, voci `registered:true`). |

---

## Componenti Dominio UI (`src/ui/components/`)

Personalizzazioni liste — admin (Blocco F). I componenti runtime FE
(`ListaConfigurabile`, `ListaColonneModal`) e il composable `useListaConfig`
sono nei "Componenti Condivisi → Lookup e Select" e nei "Composables".
Qui sono catalogati i pannelli e drawer della pagina admin.

### Fase 1 — Preset + permessi colonne (`/config/personalizzazioni-liste`)

| Componente | File | Descrizione |
| --- | --- | --- |
| `ListaCorrenteSelect` | [ListaCorrenteSelect.vue](../../../../frontend/src/ui/components/ListaCorrenteSelect.vue) | Select header "Lista corrente" condiviso da tutti i tab admin (Fase 1 + Fase 2). Lookup via `useUiAdminStore.loadListe()` (idempotente, single-flight). Visibile a SUPER_ADMIN o utenti con almeno una delle 2 azioni `ui_preset_manage`/`ui_permesso_manage`. |
| `ListaPresetPanel` | [ListaPresetPanel.vue](../../../../frontend/src/ui/components/ListaPresetPanel.vue) | Tab "Preset" — DataTable preset filtrata per `listaCorrenteId`, kebab actions (gestisci composizione + elimina), drawer testata. |
| `ListaPresetDrawer` | [ListaPresetDrawer.vue](../../../../frontend/src/ui/components/ListaPresetDrawer.vue) | Drawer crea/modifica preset (testata). Refs profilo/emittente condizionali ad ambito (`sistema`/`ruolo`/`emittente_fiscale`), CHECK ambito_refs DB rispettato lato form. |
| `ListaPresetColonneDrawer` | [ListaPresetColonneDrawer.vue](../../../../frontend/src/ui/components/ListaPresetColonneDrawer.vue) | Sub-drawer composizione preset (`lista_preset_colonna`): replace atomico via PUT con `Idempotency-Key`. Catalogo colonne grezzo come pool, riordino ▲▼ + flag visibile/fissata + larghezza inline. |
| `ListaColonnaPermessoPanel` | [ListaColonnaPermessoPanel.vue](../../../../frontend/src/ui/components/ListaColonnaPermessoPanel.vue) | Tab "Permessi colonne" — DataTable permessi (colonna × profilo × livello), drawer create/edit. |
| `ListaColonnaPermessoDrawer` | [ListaColonnaPermessoDrawer.vue](../../../../frontend/src/ui/components/ListaColonnaPermessoDrawer.vue) | Drawer UPSERT permesso colonna su `(colonna_id, profilo_accesso_id)` — Idempotency-Key per la POST. Livello accesso enum `LIVELLO_ACCESSO` (TUTTO/LETTURA/BLOCCATO). |

### Fase 2 — DEF-5b CRUD definizioni + colonne (`/amm-software/personalizzazioni-liste-tecniche`, SUPER_ADMIN)

| Componente | File | Descrizione |
| --- | --- | --- |
| `ListaDefinizionePanel` | [ListaDefinizionePanel.vue](../../../../frontend/src/ui/components/ListaDefinizionePanel.vue) | Tab "Definizioni" — DataTable globale `ui.lista_definizione` (incluse disattivate), kebab actions edit/delete, drawer create/edit. Emette `@definizione-changed` per sincronizzare il `ListaCorrenteSelect` header del tab "Catalogo colonne" condiviso. |
| `ListaDefinizioneDrawer` | [ListaDefinizioneDrawer.vue](../../../../frontend/src/ui/components/ListaDefinizioneDrawer.vue) | Drawer crea/modifica definizione lista. Form 6 campi (codice, descrizione, schema_dati, vista_sql, note, attivo). Workflow draft: `attivo=false` o `vista_sql` vuoto bypassano il trigger `valida_vista_sql` per registrare prima della creazione DDL. |
| `ListaColonnaPanel` | [ListaColonnaPanel.vue](../../../../frontend/src/ui/components/ListaColonnaPanel.vue) | Tab "Catalogo colonne" — master-detail su `listaCorrenteId` del Select header. DataTable colonne (incluse disattivate, campi completi: ordine, codice, etichetta, tipo_colonna Tag, tipo_dato, campo_sorgente, gruppo, attivo). Empty state "seleziona prima una lista". |
| `ListaColonnaDrawer` | [ListaColonnaDrawer.vue](../../../../frontend/src/ui/components/ListaColonnaDrawer.vue) | Drawer crea/modifica colonna. 17 campi distribuiti in 3 sotto-tab `<Tabs>` PrimeVue 4: **Generale** (codice, etichette + i18n_key, tipo_colonna, tipo_dato, campo_sorgente), **Comportamento** (filtrabile, ordinabile, esportabile, ricercabile_full, sensibile, attivo), **Layout** (ordine_default, larghezza_default, allineamento, formato, gruppo, gruppo_ordine). UX vincolo: `tipo_colonna='azione'` disabilita e forza off `esportabile` (CHECK `chk_ui_lista_colonna_azione_non_esportabile`). Snapshot `drawerListaId` all'apertura per evitare drift se l'utente cambia il Select header con drawer aperto. Width `DRAWER_WIDTH.WIDE`. |

### Stores Pinia (`src/ui/stores/`)

| Store | File | Descrizione |
| --- | --- | --- |
| `useUiAdminStore` | [uiAdmin.js](../../../../frontend/src/ui/stores/uiAdmin.js) | Stato condiviso fra i tab admin: lookup definizioni `liste`, selezione `listaCorrenteId`, `loadListe(force)` idempotente. `userScoped: true`. |
| `useUiPresetAdminStore` | [uiPresetAdmin.js](../../../../frontend/src/ui/stores/uiPresetAdmin.js) | CRUD `ui.lista_preset` + composizione (`lista_preset_colonna` replace atomico). Emette `TAB_ENTITIES.UI_PRESET` post-write. |
| `useUiPermessoAdminStore` | [uiPermessoAdmin.js](../../../../frontend/src/ui/stores/uiPermessoAdmin.js) | UPSERT/DELETE permessi colonna. Emette `TAB_ENTITIES.UI_PERMESSO`. |
| `useUiDefinizioneAdminStore` | [uiDefinizioneAdmin.js](../../../../frontend/src/ui/stores/uiDefinizioneAdmin.js) | **DEF-5b.** CRUD `ui.lista_definizione`. `fetchAll()`, `getById(id)`, `create/update/destroy`. Emette `TAB_ENTITIES.UI_DEFINIZIONE`. `userScoped: true`. |
| `useUiColonnaAdminStore` | [uiColonnaAdmin.js](../../../../frontend/src/ui/stores/uiColonnaAdmin.js) | **DEF-5b.** CRUD `ui.lista_colonna`. `fetchByLista(listaId)`, `getById(id)`, `create/update/destroy`. Emette `TAB_ENTITIES.UI_COLONNA`. `userScoped: true`. |
