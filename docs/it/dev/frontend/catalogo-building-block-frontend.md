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
| `useDirtyState` | [useDirtyState.js](../../../../frontend/src/core/composables/useDirtyState.js) | Tracciamento modifiche non salvate con beforeunload e tab dirty |
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
| `isEmailValid` | [validators.js](../../../../frontend/src/core/utils/validators.js) | Validazione formato email/PEC (UX, non RFC) |
| `resolveSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Risolve severity PrimeVue da mappa codice |
| `statoClienteSeverity` / `statoFornitoreSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato cliente/fornitore |
| `statoVersioneListinoSeverity` / `dominioListinoSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato versione (BOZZA/ATTIVA/CHIUSA) e dominio listino (UTILITY/COMMERCIO) |
| `statoPraticaSeverity` / `prioritaPraticaSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato/priorità pratica |
| `statoFlussoSeverity` / `esitoFlussoSeverity` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Colori stato/esito flusso |
| `azioneGiornaleStyle` | [severity.js](../../../../frontend/src/core/utils/severity.js) | Stile azione giornale (severity + icona) |
| `extractApiError` / `extractApiErrorCode` | [apiError.js](../../../../frontend/src/core/utils/apiError.js) | Estrae messaggio/codice errore da risposta API |
| `paramBool` / `paramNumber` / `paramInt` / `paramString` | [parameterCast.js](../../../../frontend/src/core/utils/parameterCast.js) | Cast con fallback dei valori `config.parameters` (BE ritorna `dict[str, str]`). Riusabili da qualsiasi `defaultForm()` parametrizzato. Adottato da: ArticoloUomDrawer (Fase 1 refactor catalogo). |

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
| `lookupBillingAccount` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Ricerca BA per autocomplete cross-dominio (`GET /anagrafiche/billing-account/lookup/`). Scope emittente automatico |
| `getBillingAccountLookupById` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Restore singolo BA arricchito per edit (`GET /anagrafiche/billing-account/{id}/lookup/`) |
| `lookupIstanzeUtility` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Ricerca istanze utility per autocomplete cross-dominio (`GET /anagrafiche/istanze-utility/lookup/`). Filtri opzionali `utility_id` (strict) e `soggetto_id`. Scope emittente automatico via BA collegato. |
| `getIstanzaUtilityLookupById` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Restore singola istanza arricchita per edit (`GET /anagrafiche/istanze-utility/{id}/lookup/`) |
| `lookupContiContabili` | [apiCore.js](../../../../frontend/src/core/apiCore.js) | Lookup dedicato conti contabili con filtro tipo (`GET /core/lookup/conti-contabili/?tipo=A` o `?tipo=V`). Usato da `ContoContabileSelect`. |
| `lookupUomRoundingModes` | [catalogo.js](../../../../frontend/src/catalogo/api/catalogo.js) | Lookup statico modi di arrotondamento UoM operativa (`GET /catalogo/lookup/rounding-modes/`). Restituisce 5 codici fissi (HALF_UP, HALF_DOWN, HALF_EVEN, UP, DOWN) con descrizione. Single source of truth lato BE: `catalogo_service._ROUNDING_MODE_VALIDI`. Usato da `RoundingModeSelect`. |
| `lookupTipiVariazioneContratto` / `lookupTipiVariazionePromo` | [vendite/api/lookup.js](../../../../frontend/src/vendite/api/lookup.js) | Lookup statici tipi variazione vendite (Fase 2 refactor frontend). Contratto = `PERCENTUALE`/`VALORE_FISSO`; promo aggiunge `PREZZO_FISSO`. Single source of truth lato BE: `vendite_lookups_service`. Usati da `TipoVariazioneSelect`. |
| `lookupAmbitiContratto` | [vendite/api/lookup.js](../../../../frontend/src/vendite/api/lookup.js) | Lookup statico ambiti contratto (`COMMODITY`/`COMMERCIO`). Usato da `AmbitoContrattoSelect`. |
| `lookupModalitaPricingContratto` | [vendite/api/lookup.js](../../../../frontend/src/vendite/api/lookup.js) | Lookup statico modalita pricing contratto (`A`/`B`/`C`). Astrazione UI (non colonna DB) esposta lato BE per single-source. Usato da `ContrattoDrawer` per popolare il `SelectButton`. |
| `getContrattoFormDefaults` / `getPreventivoFormDefaults` | [vendite/api/formDefaults.js](../../../../frontend/src/vendite/api/formDefaults.js) | **Fase 2.B3-B4 refactor frontend vendite.** Defaults form BA-aware. Param opzionale `billing_account_id`: se presente popola categoria_cliente_id_snapshot/utility (contratti) o valuta/termini/iva dal cliente del BA (preventivi). Sempre presenti `default_data`/`default_valido_dal`/`default_validita_al` da parameter. Single source of truth lato BE: `vendite_form_defaults_service`. |
| `getVersioneNewDefaults` / `getVersioneCloneDefaults` / `getVersioneCloseDefaults` | [vendite/api/formDefaults.js](../../../../frontend/src/vendite/api/formDefaults.js) | **Fase 2.B5a/b/c refactor frontend vendite.** Defaults contestuali alle versioni listino: nuova (existing_drafts + default_valido_dal), clone (codice + suffisso da parameter, min_valido_dal = source.valido_dal), close (default_valido_al = existing oppure oggi+lead_gg). Consumati da `VersioneFormDrawer`/`CloneVersioneDrawer`/`ChiudiVersioneDialog` al posto di `useParameterDefaults` cablato. |

---

## Costanti (`src/core/constants.js`)

| Costante | Descrizione |
|---|---|
| `DRAWER_WIDTH` | Larghezze drawer per complessità (SIMPLE, STANDARD, COMPLEX, WIDE) |
| `TOAST_DURATION` | Durata toast per tipo (SUCCESS, WARN, ERROR, SYSTEM_ERROR) |
| `TIPO_RUOLO` | Codici interni tipi ruolo (CL, FO, GE, VE, DI, RE, VT, EF, BANK_B, RIS_UMANA, PSP) |
| `PAGINATION` | Paginazione default (25 righe, opzioni [10, 25, 50, 100]) |
| `DATE_FORMAT` | Formato data PrimeVue centralizzato |
| `TABS` | Limite massimo tab aperte (10) |
| `BREAKPOINTS` | Breakpoint responsive (MOBILE, TABLET, DESKTOP_SPLIT) |
| `FIELD_LENGTH` | Vincoli lunghezza campi (IBAN_MAX) |
| `RUOLO_SISTEMA` | Enum ruoli sistema (ADMIN, OPERATIVO, DISABILITATO) |
| `LIVELLO_ACCESSO` | Enum livelli accesso (TUTTO, LETTURA, BLOCCATO) |
| `STATO_PRATICA` | Enum stati pratica (BOZZA, APERTA, SOSPESA, CHIUSA, ANNULLATA) |
| `STATO_FLUSSO` | Enum stati flusso (DA_ESEGUIRE, IN_CORSO, COMPLETATO, ecc.) |
| `MANAGE_ICONS` | Icone gestione riga centralizzate per dominio (CONTATTI, INDIRIZZI, CONTI_BANCARI, UOM, BOM, NOTE, CONVERSIONI) |
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
| `app-page-actions` | Gruppo pulsanti azione toolbar (refresh + new) |
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
| `app-drawer-content` | Layout standard contenuto drawer (gap via `--app-drawer-gap`, tipografia h4) |
| `app-drawer-section` | Separatore sezione nei drawer (bordo via `--app-drawer-section-border`) |
| `app-drawer-footer` | Footer drawer con pulsanti allineati a destra |

### Classi DataTable (`main.css`)

| Classe | Descrizione |
|---|---|
| `app-datatable` | DataTable compatta con header/celle ridotte, righe alternate, hover |
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
<Button icon="pi pi-trash" text rounded size="small" class="app-delete-btn" @click="onDelete(data)" />
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
| `AppDrawer` | [AppDrawer.vue](../../../../frontend/src/core/components/AppDrawer.vue) | Wrapper drawer generico (create/edit) |
| `DrawerTitle` | [DrawerTitle.vue](../../../../frontend/src/core/components/DrawerTitle.vue) | Titolo drawer + icona + chiudi |
| `DrawerFooter` | [DrawerFooter.vue](../../../../frontend/src/core/components/DrawerFooter.vue) | Pulsanti salva/annulla per drawer |
| `GenericConfigDrawer` | [GenericConfigDrawer.vue](../../../../frontend/src/core/components/GenericConfigDrawer.vue) | Drawer generico tabelle config |
| `ContattiSoggettoDrawer` | [ContattiSoggettoDrawer.vue](../../../../frontend/src/core/components/ContattiSoggettoDrawer.vue) | Drawer contatto per soggetto |
| `IndirizziSoggettoDrawer` | [IndirizziSoggettoDrawer.vue](../../../../frontend/src/core/components/IndirizziSoggettoDrawer.vue) | Drawer indirizzo per soggetto |
| `ContiBancariDrawer` | [ContiBancariDrawer.vue](../../../../frontend/src/core/components/ContiBancariDrawer.vue) | Drawer conto bancario per soggetto |

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
| `ArticoloLookup` | [ArticoloLookup.vue](../../../../frontend/src/core/components/ArticoloLookup.vue) | Autocomplete articolo server-side cross-dominio. Props: `voce-utility`, `solo-componenti`, `solo-attivi`, `placeholder`, `disabled`. Emette `@select`. Usa `optionLabel` PrimeVue 4, `minLength: 3`. Usato da: righe listino, distinta base, test resolver. |
| `BillingAccountLookup` | [BillingAccountLookup.vue](../../../../frontend/src/core/components/BillingAccountLookup.vue) | Autocomplete BA server-side cross-dominio con ricerca ricca (codice, ragione sociale, id fiscale, PDP). Dropdown a 3 righe via classe `app-lookup-option`. Props: `utilityId`, `soloValidi` (default `true`), `validAt`, `placeholder`, `disabled`. Emette `@select`, `@clear`. Footer "affina la ricerca" quando `total > limit`. `minLength: 2`. Scope emittente automatico lato backend. Usato da: righe listino associazioni; esteso a preventivi/ordini/fatture/pratiche. |
| `IstanzaUtilityLookup` | [IstanzaUtilityLookup.vue](../../../../frontend/src/core/components/IstanzaUtilityLookup.vue) | Autocomplete istanze_utilities server-side cross-dominio. Ricerca multi-campo (codice istanza, ragione sociale soggetto, indirizzo normalizzato). Dropdown a 3 righe (primary: ragione sociale + tag utility + badge "Solo istanza"/"Fittizia"; secondary: codice istanza; meta: indirizzo + codice BA campione). Props: `utilityId` (strict, post Strategia C), `soggettoId` (UUID), `placeholder`, `disabled`. Emette `@select`, `@clear`. Auto-reset selezione al cambio di `utilityId` se l'istanza dichiara utility incoerente. `minLength: 2`. Scope emittente automatico lato backend (via BA collegato). Usato da: `PreventiviForm` (drawer prospect senza BA); riusabile in future utility-aware flows. |

### Ricerca

| Componente | File | Descrizione |
|---|---|---|
| `SearchDrawer` | [SearchDrawer.vue](../../../../frontend/src/core/components/SearchDrawer.vue) | Ricerca universale full-text con selezione contesto |
| `ConfigTablePanel` | [ConfigTablePanel.vue](../../../../frontend/src/core/components/ConfigTablePanel.vue) | Pannello tabella config generico |
| `SearchHint` | [SearchHint.vue](../../../../frontend/src/core/components/SearchHint.vue) | Hint per campi di ricerca |
| `PaginationInfo` | [PaginationInfo.vue](../../../../frontend/src/core/components/PaginationInfo.vue) | Metadata paginazione (es. "1-25 di 100") |
| `SearchDetailTable` | [details/SearchDetailTable.vue](../../../../frontend/src/core/components/details/SearchDetailTable.vue) | Tabella dettaglio espandibile per ricerca |
| `DetailActions` | [details/DetailActions.vue](../../../../frontend/src/core/components/details/DetailActions.vue) | Pulsanti azione per vista dettaglio |

### Supporto

| Componente | File | Descrizione |
|---|---|---|
| `NewButton` | [NewButton.vue](../../../../frontend/src/core/components/NewButton.vue) | Pulsante "Nuovo" con controllo permessi |
| `RowActionsMenu` | [RowActionsMenu.vue](../../../../frontend/src/core/components/RowActionsMenu.vue) | Azioni di riga responsive. Props: `actions`, `row`, `tooltip`, `disabled`, `disableWhenInactive`. Se `row.attivo === false` o `row.is_active === false`, disabilita automaticamente le azioni operative salvo `allowWhenInactive: true` sulla singola azione (es. riattiva/storico/modifica quando la matita e' l'entrypoint del form). |
| `StatusPage` | [StatusPage.vue](../../../../frontend/src/core/components/StatusPage.vue) | Pagine errore/forbidden/not-found |
| `TagList` | [TagList.vue](../../../../frontend/src/core/components/TagList.vue) | Lista tag/label riutilizzabile |
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
| `ArticoloNoteDrawer` | [ArticoloNoteDrawer.vue](../../../../frontend/src/catalogo/components/ArticoloNoteDrawer.vue) | Sub-drawer note articolo. Pattern formMode con card layout. Stile nota via `LookupSelect rel="config.note_stili"`. Props: `visible`, `articolo-id`. Emette `@saved`. |
| `RoundingModeSelect` | [RoundingModeSelect.vue](../../../../frontend/src/catalogo/components/RoundingModeSelect.vue) | **Wrapper standard modi arrotondamento UoM operativa.** Usa `useGlobalLookup` (chiave `catalogo.uom_rounding_modes`) sul lookup statico `lookupUomRoundingModes` con cache modulo-level. Display `"descrizione (codice)"`. Props: `modelValue` (string codice), `placeholder`, `disabled`, `showClear`. Sostituisce il vecchio `roundingOptions` hardcoded. Usato da: ArticoloUomDrawer (Fase 1 refactor catalogo). |


---

## Componenti Dominio Vendite (`src/vendite/components/`)

### Wrapper select per enum di dominio (Fase 2 refactor frontend)

| Componente | File | Descrizione |
| --- | --- | --- |
| `TipoVariazioneSelect` | [TipoVariazioneSelect.vue](../../../../frontend/src/vendite/components/TipoVariazioneSelect.vue) | **Wrapper standard tipo_variazione.** Prop `scope` discrimina `'contratto'` (PERCENTUALE/VALORE_FISSO) vs `'promo'` (+ PREZZO_FISSO). Cache modulo-level via `useGlobalLookup` con chiavi `vendite.tipi_variazione.<scope>`. Display `"descrizione (codice)"`. Sostituisce `tipoVariazioneOptions` cablato in `ContrattoDrawer` e `PromoArticoloDrawer`. |
| `AmbitoContrattoSelect` | [AmbitoContrattoSelect.vue](../../../../frontend/src/vendite/components/AmbitoContrattoSelect.vue) | **Wrapper standard ambito contratto** (COMMODITY/COMMERCIO). Cache `vendite.ambiti_contratto`. Sostituisce `ambitoOptions` cablato. |
