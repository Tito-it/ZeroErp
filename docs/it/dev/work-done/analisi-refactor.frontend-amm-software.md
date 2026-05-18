# Analisi refactor frontend amm-software

<!-- markdownlint-disable MD036 MD031 MD028 -->

> Obiettivo: identificare cosa nel frontend Amm. Software e' logica di dominio
> o sicurezza mascherata da presentazione, cosa e' UX defense-in-depth legittima
> e cosa richiede un contratto API piu' ricco.
>
> Questa area e' piu' delicata delle CRUD standard: gestisce identita',
> permessi, emittenti fiscali, matrici di configurazione, email operative e
> audit. Un drift tra frontend e backend qui non produce solo un errore UX:
> puo' aprire azioni admin sbagliate, policy fiscali incoerenti o ambiguita'
> nei permessi.
>
> Riferimenti vincolanti:
>
> - `docs/it/dev/api.md` - envelope API, command/read, errori strutturati,
>   handle_post_json, base view AdminAPIView, codici errore strutturati.
> - `docs/it/dev/frontend/frontend-standards.md` - pattern lista/drawer,
>   readonly, RowActionsMenu, i18n, transizioni a stato terminale con data,
>   permessi v2 livello oggetto.
> - `docs/it/dev/backend/catalogo-building-block-backend.md` - inventario
>   building block riusabili (PayloadValidator, map_integrity_error,
>   ParameterService, PermissionResolver, IsAdminZeroERP, EmailDispatchService).
> - `docs/it/dev/frontend/catalogo-building-block-frontend.md` - inventario
>   composable e componenti FE riusabili (useParameterDefaults, LookupSelect,
>   RoundingModeSelect, RowActionsMenu, useReadonlyMode, useGlobalLookup).
> - `docs/it/dev/work-done/frontend/guida-sviluppo-frontend.md` - convenzioni
>   Vue, store, API client.
> - `docs/it/dev/work-done/refactor-operatore-emittenti.md` - evoluzione
>   rapporto operatore/emittente e multi-face auth.
> - `docs/it/dev/work-in-progress/permessi-e-autorizzazioni-v3.md` - modello
>   autorizzativo.
> - `docs/it/dev/work-in-progress/analisi-refactor.frontend-catalogo.md` -
>   pattern `form-defaults`, lookup tecnici e capability di riga
>   (Fasi 1..8 LANDED 2026-04-28).
> - `docs/it/dev/work-in-progress/analisi-refactor.frontend-vendite.md` -
>   pattern `available_actions`, `non_editable_fields`, command data-driven.
>
> Principio: il frontend amm-software deve restare presentazione + UX. Il
> backend/DB decidono contratti auth, capability, ambito emittenti, default
> operativi, invarianti fiscali, fonti audit e policy email.

> **Note di revisione 2026-04-28**: il documento e' stato riallineato
> dopo lettura di `agents.md`, `api.md`, dei building block backend/frontend
> e di `frontend-standards.md`. Punti emersi di rilievo:
>
> - L'inventario sottodomini era incompleto: aggiunti `OperatorePermessiDrawer`,
>   `OperatoriNonAssegnatiBanner`, override oggetti (permessi v2) e
>   `EmailLogsListView` (vedi A14, A15, A16).
> - L'endpoint per i metodi rounding va modellato come **lookup statico
>   per dominio** (`/<dominio>/lookup/rounding-modes/`), non come lookup
>   generico `core/lookup/codici/?rel=...`: rounding mode resta enum tecnico
>   Python con single source of truth lato BE (precedente landed: catalogo
>   Fase 1, `lookupUomRoundingModes`, vedi A6 corretto).
> - Gli endpoint `POST /operatori/<id>/disabilita/` e `/riattiva/` esistono
>   gia' (`amm_software/api/urls_v1.py:14-15`) ma il FE non li usa: oggi
>   passa da PATCH `attivo` (vedi C7).
> - Il drawer operatore in CREATE non deve ricevere `ruolo_applicativo`
>   nel payload: per l'amm-software interno e' implicitamente `OPERATORE`.
>   La proposta payload A1 e' stata corretta in tal senso.
> - `TipoRuoloTipoIndirizzoDrawer.vue` usa gia' `isReadOnlyEffective` su
>   tutti i campi (riga 33, 126, 132..152): il bug A10 e' meno grave del
>   descritto — riguarda solo il return `true` di `canSave` in edit mode,
>   che resta defense-in-depth incompleta.

---

## Mappa sottodomini frontend

| Sottodominio | File principali | Stato architetturale |
| --- | --- | --- |
| Operatori e identita | `OperatoriListView.vue`, `OperatoreDrawer.vue`, `stores/operatori.js` | Transizione multi-face avviata ma create/update hanno ancora contratti diversi. Capability invito/disabilitazione calcolate in parte nel FE. |
| Permessi operatore | `OperatorePermessiTab.vue`, `OperatorePermessiDrawer.vue`, `PermessiRiepilogoView.vue` | Buona separazione store/API, ma readonly incompleto e scope emittenti ambiguo tra single/global/multi. |
| Profili reparto | `RepartiProfiloView.vue`, `RepartoProfiloEditor.vue` | Area relativamente pulita; valgono gli stessi pattern metadata degli override utente. |
| Emittenti fiscali | `EmittentiFiscaliListView.vue`, `EmittenteFiscaleDrawer.vue` | Validazioni UX corrette, ma default fiscali/rounding e campi non editabili devono arrivare dal backend. |
| Mapping billing account | `EmittenteFiscaleBillingAccountTab.vue`, `EmittenteFiscaleBillingAccountDrawer.vue` | Pattern lista buono, ma il default mapping viene rilevato solo sulla pagina corrente: bug UX su liste paginate. |
| Utility emittente fiscale | `EmittenteFiscaleUtilitiesTab.vue`, `EmittenteFiscaleUtilitiesDrawer.vue` | Matrice data-driven valida; rounding/range e capability riga ancora cablati nel FE. |
| Matrici configurazione | `UtilitiesTipiRuolo*`, `TipiRuoloTipiIndirizzo*` | Buona struttura, ma lookup fallback e impatti di disattivazione devono essere guidati da API. |
| Categorie clienti/listini | `CategoriaCliente*`, `CategoriaClienteListino*` | CRUD/matrice coerente; enum variazione e campi immutabili vanno esposti come lookup/metadata. |
| Email operative | `EmailAccountDrawer.vue`, `EmailTemplateDrawer.vue`, `EmailLogsListView.vue` | Funzionale ma acerbo: default SMTP cablati, readonly non effettivo, titoli hardcoded, preview HTML da blindare. |
| Audit | `AuditLogView.vue` | Utile per debug admin, ma filtri tabella e summary snapshot sono cablati nel FE. La whitelist chiavi snapshot include ancora `ruolo_sistema` (legacy multi-face). |
| Drawer permessi standalone | `OperatorePermessiDrawer.vue` | Apre `OperatorePermessiTab` in drawer indipendente dalla lista operatori. Eredita gli stessi bug readonly/scope del tab (A4/A3). |
| Banner non-assegnati | `OperatoriNonAssegnatiBanner.vue` | Banner di transizione refactor operatore-emittenti: dipende dall'endpoint `setup-status/` (gia' attivo lato BE). UX corretta. |
| Email log | `EmailLogsListView.vue` | Lista paginata read-only. Stati `PENDING/SENT/FAILED/RETRY` cablati in `constants.js`: vanno esposti come lookup statico per coerenza (vedi A16). |

---

## Sintesi priorita'

| Priorita' | Tema | Diagnosi |
| --- | --- | --- |
| P0 | Readonly non effettivo in tab permessi/email e matrice indirizzi | Alcuni bottoni e save restano attivabili anche dentro contenitori `app-readonly`. Va corretto prima dei refactor concettuali. |
| P0 | Preview template email con `v-html` | HTML renderizzato direttamente dentro la shell admin. Va sandboxato o sanificato. |
| P0 | Default mapping BA rilevato solo sulla pagina corrente | `hasDefault` guarda `store.items`; con paginazione/search puo' riabilitare "default" anche se esiste gia'. |
| P1 | Contratto operatore create/update disallineato | Update usa `{is_super_admin, attivo}`, create invia ancora `ruolo_sistema` legacy. |
| P1 | Capability admin non data-driven | Invito, disabilitazione, demote super-admin, override e scope emittenti devono arrivare come `can_*` + reason. |
| P1 | Defaults fiscali/email/rounding nel frontend | `attivo=true`, `bollo_auto=false`, SMTP 587/TLS, rounding method/range sono policy operative. |
| P1 | Scope emittenti ambiguo | Il tab salva lista, ma UI permette una sola emittente e il testo parla di "vuoto = tutte". Serve contratto esplicito. |
| P1 | Audit e lookup tecnici cablati | Tabelle audit, stati email log, metodi rounding e tipi variazione devono arrivare da lookup/config API. |
| P2 | Residui legacy ruolo | `PermessiRiepilogoView` e `buildRuoloOptions()` usano ancora `ruolo_sistema`. Va chiuso dopo completamento multi-face. |
| P2 | Standard frontend | `EmailAccountDrawer.vue` e `EmailTemplateDrawer.vue` mancano `// Scopo:` e hanno titoli visibili non i18n. |

---

## A. Logica di business/sicurezza da spostare a backend/API

### A1. Contratto operatore unico per create/update

- `frontend/src/amministrazione/components/OperatoreDrawer.vue:156`
- `frontend/src/amministrazione/components/OperatoreDrawer.vue:187`

L'update usa gia' il nuovo contratto multi-face:

```json
{
  "is_super_admin": true,
  "attivo": true
}
```

La create invece invia ancora:

```json
{
  "ruolo_sistema": "ADMIN|OPERATIVO"
}
```

Il commento nel codice dice esplicitamente che e' una fase temporanea. Va chiusa:
un solo contratto API deve gestire create e update.

Contratto proposto:

```json
{
  "soggetto_id": 123,
  "username": "m.rossi",
  "email": "m.rossi@example.test",
  "password": "...",
  "is_super_admin": false,
  "attivo": true,
  "qualifica_id": 4,
  "unita_organizzativa_id": 10
}
```

`ruolo_applicativo` **non** appartiene al payload del drawer Operatore: per
amm-software interno e' implicitamente `OPERATORE` (la classificazione e'
una proprieta' della veste, decisa dal namespace API + dal binding identita
digitale). Le vesti `CLIENTE_PORTALE`, `FORNITORE_PORTALE`, `SHOP_CUSTOMER`
nascono da flussi di invito dedicati (`/anagrafiche/clienti|fornitori/<id>/invita-portale|shop/`),
non da questo drawer.

Il backend puo' continuare a tradurre internamente verso campi legacy
(`ruolo_sistema`), ma il FE non deve piu' conoscere `ruolo_sistema` per
nuove scritture. La compat-translation lato BE e' temporanea e va dismessa
quando tutti i consumer admin sono migrati (vedi C4).

### A2. Invito, disable e demote super-admin come capability backend

- `frontend/src/amministrazione/components/OperatoreDrawer.vue:64`
- `frontend/src/amministrazione/components/OperatoreDrawer.vue:232`
- `frontend/src/amministrazione/stores/operatori.js`

`canInvite` e' calcolato con `edit && !last_login && is_active`. E' una buona
euristica UX, ma il dominio reale e' piu' ampio: operatore invitabile, indirizzo
email valido, stato auth, provider, inviti precedenti, eventuali blocchi.

Il detail operatore deve esporre:

```json
{
  "can_invite": true,
  "invite_reason": null,
  "can_disable": false,
  "disable_reason": "Ultimo super admin attivo",
  "can_demote_super_admin": false,
  "demote_reason": "Deve restare almeno un super admin"
}
```

Il frontend renderizza bottoni e messaggi. La protezione resta nel service/DB.
In parallelo, la disabilitazione dovrebbe passare da command espliciti
(`disabilita`, `riattiva`) invece di un generico PATCH `attivo`.

> **Nota — comandi gia' esposti**: `POST /api/v1/amm-software/operatori/<id>/disabilita/`
> e `POST .../riattiva/` esistono in `amm_software/api/urls_v1.py:14-15`
> (`OperatoriDisabilitaView`/`OperatoriRiattivaView`). Mancano solo lato FE
> i wrapper API + il pulsante azione di riga: si tratta quindi di lavoro
> FE-only, non di un nuovo endpoint da progettare. Vedi C7.

### A3. Scope emittenti: dichiarare `GLOBAL|SINGLE|MULTI`

- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:47`
- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:109`
- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:275`

Il modello locale e lo store trattano lo scope come lista (`localEmittentiIds`),
ma il componente renderizza un `Select` singolo e salva `[v]`. Inoltre l'hint
utente dice che vuoto significa "tutte".

Questo e' troppo ambiguo per un'area permessi. Il backend deve esporre lo shape:

```json
{
  "scope_mode": "GLOBAL|SINGLE|MULTI",
  "emittenti_ids": [1],
  "allowed_scope_modes": ["GLOBAL", "SINGLE"],
  "can_change_scope": true,
  "change_scope_reason": null
}
```

Il FE sceglie `Select`, `MultiSelect` o radio "Tutte/Una/Molte" in base al
payload. Non deve dedurre la semantica dal fatto che un array sia vuoto.

### A4. Readonly reale in `OperatorePermessiTab`

- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:119`
- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:147`
- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:204`
- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:285`

Il componente non usa `useInjectReadonly()`: select, toggle, trash, add e save
restano interattivi. Se il tab viene aperto dentro un drawer readonly, la classe
CSS non basta a impedire mutazioni.

Fix minimo:

- iniettare readonly nel tab;
- disabilitare `Select`, `ToggleSwitch`, `Button`;
- nascondere trash/add/save quando readonly;
- short-circuit in `saveAree`, `saveAzioni`, `saveOggetti`, `saveEmittenti`.

Questo e' P0 perche' riguarda un modulo admin permessi.

### A5. Default emittente fiscale e campi editabili da form-defaults/detail

- `frontend/src/amministrazione/components/EmittenteFiscaleDrawer.vue:62`
- `frontend/src/amministrazione/components/EmittenteFiscaleDrawer.vue:127`
- `frontend/src/amministrazione/components/EmittenteFiscaleDrawer.vue:141`

Il form cabla:

- `attivo: true`
- `bollo_auto: false`
- `bollo_soglia: null`
- `rounding_policy: null`

Sono policy fiscali/operative. Inoltre il FE sa che `codice` si invia solo in
create e non in edit. Il backend dovrebbe esporre:

```json
{
  "defaults": {
    "attivo": true,
    "bollo_auto": false,
    "bollo_soglia": null,
    "rounding_policy": "HALF_UP"
  },
  "non_editable_fields": ["codice", "soggetto_id"],
  "rounding_policy_options": [...]
}
```

La validazione P.IVA lato UI (`soggettoHasPartitaIva`) e' corretta come
defense-in-depth, ma il resolver soggetto potrebbe gia' restituire
`can_be_emittente_fiscale` e `reason`.

### A6. Rounding method/range come lookup tecnico, non costante JS

- `frontend/src/amministrazione/constants.js:78` (`ROUNDING_METHODS` 4 codici:
  `HALF_UP/HALF_DOWN/UP/DOWN` — niente `HALF_EVEN`)
- `frontend/src/amministrazione/constants.js:90` (`ROUNDING_DECIMALI_RANGE` 0..6)
- `frontend/src/amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:16`
- `frontend/src/amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:84`
- `frontend/src/amministrazione/components/EmittenteFiscaleDrawer.vue:13`
  (rounding_policy)

`ROUNDING_METHODS` e `ROUNDING_DECIMALI_RANGE` sono allineati ai CHECK DB, ma
questo allineamento e' manuale. Ogni modifica al constraint richiede una patch
frontend.

**Pattern allineato al precedente catalogo (Fase 1 LANDED 2026-04-28)**:
il rounding mode resta un **enum tecnico Python** (single source of truth lato
BE, costante `_ROUNDING_MODE_VALIDI` nel service del dominio), non una tabella
DB con FK-surrogato. Il FE consuma l'enum tramite **lookup statico per dominio**
seguendo la convenzione `/api/v1/<dominio>/lookup/rounding-modes/` gia'
in produzione su `catalogo`.

Endpoint proposti:

```text
# Esistente, gia' landed (catalogo Fase 1) — ritorna 5 codici (incl. HALF_EVEN)
GET /api/v1/catalogo/lookup/rounding-modes/

# Nuovo, per amm-software — ritorna i 4 codici ammessi dal CHECK
# anagrafiche.emittenti_fiscali_utilities + emittenti_fiscali.rounding_policy
GET /api/v1/amm-software/lookup/rounding-modes/

# Form-defaults (max-decimals, default method, ecc.) via parameters cascata
# user → group → emittente → default (esiste gia' ParameterService)
GET /api/v1/amm-software/emittenti-fiscali/form-defaults/
```

Pattern FE atteso (riuso building block catalogo):

- Composable: `useGlobalLookup` chiavato su `amm.emittenti_rounding_modes`
  (cache modulo-level, dedup thundering-herd) — vedi
  `catalogo-building-block-frontend.md` riga 24.
- Componente: nuovo `EmittenteRoundingModeSelect.vue` simmetrico a
  `RoundingModeSelect.vue` (catalogo). Display `"descrizione (codice)"`.
- Consumer: `EmittenteFiscaleDrawer` (rounding_policy) +
  `EmittenteFiscaleUtilitiesTab` (metodo_arrotondamento_importi).

Il FE puo' mantenere severity/label presentation, ma non il set ammesso e il
range tecnico. Il range decimali (0..6) puo' arrivare nello stesso payload
del lookup come metadata della collezione (`{rows: [...], range: {min, max}}`).

### A7. Matrice utility emittente: capability e defaults riga

- `frontend/src/amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:58`
- `frontend/src/amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:100`
- `frontend/src/amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:144`

La matrice e' concettualmente corretta: il backend restituisce tutte le utility
ammesse dal ruolo e il FE mostra configurata/non configurata. Restano pero' tre
decisioni lato FE:

- nuove righe partono con rounding null e `attivo = emittenteAttivo`;
- validazione obbligatori/range e' cablata;
- azioni riga sono derivate solo da `record_id`.

Il payload riga dovrebbe includere:

```json
{
  "utility_id": 7,
  "configured": false,
  "defaults": {
    "arrotondamento_importi_dec": 2,
    "metodo_arrotondamento_importi": "HALF_UP",
    "attivo": true
  },
  "can_configure": true,
  "can_update": false,
  "can_remove": false,
  "reason": null
}
```

Il warning su padre inattivo e' UX utile, ma la capability vera deve arrivare
dalla API.

### A8. Mapping billing account: `has_default` non dalla pagina corrente

- `frontend/src/amministrazione/components/EmittenteFiscaleBillingAccountTab.vue:51`
- `frontend/src/amministrazione/components/EmittenteFiscaleBillingAccountTab.vue:137`

`hasDefault` fa `store.items.some(m => m.is_default)`. Con lista paginata,
ordinata o filtrata, il default puo' esistere fuori dalla pagina corrente e il
pulsante "default" torna abilitato. Il backend probabilmente rifiuta il duplicato,
ma la UX mostra un comando falso.

Soluzioni accettabili:

- list response arricchita con `meta.has_default_mapping`;
- endpoint summary `GET /emittenti-fiscali/{id}/billing-account-mappings/summary/`;
- detail emittente include `billing_account_mapping_summary`.

Le azioni riga dovrebbero inoltre essere `can_delete/delete_reason`, non sempre
"rimuovi".

### A9. Matrice categorie/listini: lookup tipo variazione e metadata immutabilita'

- `frontend/src/amministrazione/components/CategoriaClienteListinoDrawer.vue:47`
- `frontend/src/amministrazione/components/CategoriaClienteListinoDrawer.vue:130`
- `frontend/src/amministrazione/components/CategoriaClienteListinoDrawer.vue:160`

`PERCENTUALE` e `VALORE_FISSO` sono cablati. La regola "tipo e valore devono
essere entrambi presenti o entrambi null" e' corretta come UX, ma il set ammesso
e i campi immutabili devono arrivare dal backend:

```json
{
  "tipo_variazione_options": [
    {"value": null, "label_key": "..."},
    {"value": "PERCENTUALE", "label": "PERCENTUALE"},
    {"value": "VALORE_FISSO", "label": "VALORE_FISSO"}
  ],
  "non_editable_fields": [
    "categoria_cliente_id",
    "utility_id",
    "emittente_soggetto_ruolo_id",
    "classe_utenza_id"
  ]
}
```

### A10. Matrice tipi ruolo/tipi indirizzo: fallback options dal backend

- `frontend/src/amministrazione/components/TipoRuoloTipoIndirizzoDrawer.vue:75`
- `frontend/src/amministrazione/components/TipoRuoloTipoIndirizzoDrawer.vue:145`
- `frontend/src/amministrazione/components/TipoRuoloTipoIndirizzoDrawer.vue:159`

Il drawer permette un fallback generico su `config.tipi_indirizzi`. Il backend
deve comunque validare "non se stesso", cicli e fallback non applicabili; lato
FE sarebbe meglio ricevere `fallback_options` gia' filtrate per ruolo/tipo.

Stato readonly (verificato in codice): tutti i campi usano gia'
`:disabled="isReadOnlyEffective"` (riga 33, 132..152). Il `DrawerFooter`
nasconde Salva quando readonly, per standard. Il bug residuo e' difensivo:
`canSave` ritorna `true` in edit a prescindere dal readonly (riga 76).
Short-circuit consigliato in `handleSave`:

```js
async function handleSave() {
  if (isReadOnlyEffective.value) return
  // ... resto invariato
}
```

Plus: in cima al `canSave` aggiungere `&& !isReadOnlyEffective.value` per
coerenza dichiarativa.

### A11. Email account: defaults e readonly

- `frontend/src/amministrazione/components/EmailAccountDrawer.vue:36`
- `frontend/src/amministrazione/components/EmailAccountDrawer.vue:49`
- `frontend/src/amministrazione/components/EmailAccountDrawer.vue:61`
- `frontend/src/amministrazione/components/EmailAccountDrawer.vue:120`
- `frontend/src/amministrazione/components/EmailAccountDrawer.vue:204`

Il drawer cabla default operativi SMTP:

- `smtp_port: 587`
- `smtp_use_tls: true`
- `smtp_use_ssl: false`
- `attivo: true`

Questi valori devono arrivare da form-defaults/parameters, perche' dipendono da
ambiente e policy IT. La scelta di non inviare `smtp_password` vuota in edit e'
invece corretta.

Bug immediati:

- `canSave` non controlla readonly;
- i campi non usano `:disabled="isReadonly"`;
- il pulsante test connessione resta cliccabile in readonly;
- `DrawerTitle` usa `title="Account Email"` invece di i18n;
- manca il commento `// Scopo:` iniziale richiesto dagli standard frontend.

### A12. Template email: preview HTML sicura e readonly

- `frontend/src/amministrazione/components/EmailTemplateDrawer.vue:34`
- `frontend/src/amministrazione/components/EmailTemplateDrawer.vue:70`
- `frontend/src/amministrazione/components/EmailTemplateDrawer.vue:99`
- `frontend/src/amministrazione/components/EmailTemplateDrawer.vue:154`
- `frontend/src/amministrazione/components/EmailTemplateDrawer.vue:160`

Il preview usa:

```vue
<div v-html="previewHtml" />
```

Anche se l'area e' admin-only, il template e' contenuto modificabile da utente.
Renderizzarlo dentro la stessa shell puo' eseguire HTML/script/event handler o
CSS invasivo. Serve una delle due:

- iframe sandbox con contenuto isolato;
- sanificazione HTML esplicita lato backend/frontend e policy "trusted preview".

Come per gli account, readonly non e' effettivo: `canSave` non lo controlla,
input e textarea restano editabili e il footer puo' salvare. Anche qui titolo
hardcoded e mancanza `// Scopo:`.

### A13. Audit: fonti e summary dal backend

- `frontend/src/amministrazione/constants.js:61` (`buildAuditTabellaOptions`)
- `frontend/src/amministrazione/views/AuditLogView.vue:34`
- `frontend/src/amministrazione/views/AuditLogView.vue:95` (`snapshotSummary`)

Le tabelle audit filtrabili sono codificate in JS:

- `user_override_aree`
- `user_override_azioni`
- `user_emittenti_fiscali`
- `risorse_umane_auth_user`
- `profili_reparto_aree`
- `profili_reparto_azioni`

**Mancanza**: la lista non include `user_override_oggetti` (override permessi
v2 livello model, vedi A14) ne' `identita_digitali` (multi-face auth). Se
cambia il trigger audit o si aggiunge una fonte, il FE resta incompleto. Il
backend deve esporre `audit_sources` con `code`, `label_key`, `area_funzionale`.

Anche `snapshotSummary()` e' dominio presentazionale troppo fragile: whitelista
chiavi note (riga 102: `auth_user_id`, `area_id`, `azione_id`,
`unita_organizzativa_id`, `livello`, `abilitata`, `ruolo_sistema`,
`emittente_fiscale_id`) e perde informazione appena cambia lo snapshot.
Inoltre la chiave `ruolo_sistema` e' **legacy multi-face**: post-cutover il
campo non esiste piu' nel detail e va sostituita con `is_super_admin`,
`attivo`, `ruolo_applicativo`. Vedi anche C6.

Meglio restituire dal backend:

```json
{
  "summary": "Operatore 42: livello LETTURA su area vendite",
  "diff": [
    {"field": "livello", "old": "BLOCCATO", "new": "LETTURA"}
  ]
}
```

### A14. Override oggetti (permessi v2): capability + audit source mancanti

- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:46`
  (`localOggetti`)
- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:147`
  (`saveOggetti`)
- `frontend/src/amministrazione/components/OperatorePermessiTab.vue:241`
  (sezione "Override oggetti")

Il tab espone TRE livelli di override: aree, azioni e **oggetti**
(permessi v2 — granularita' model). Il sottodominio "Override oggetti"
manca completamente nell'analisi originale del documento ed eredita
gli stessi problemi delle altre matrici:

- niente `useInjectReadonly()` → trash/add/save attivi anche in readonly
  (vedi A4 — il fix copre tutte e tre le matrici);
- `getModelOverridesLookup()` (BE attivo, route
  `lookup/model-overrides/`) ritorna l'elenco dei model "catalogati"
  (`config.area_model_overrides`); manca pero' la capability
  `can_override`/`reason` per evitare di proporre model bloccati per
  ragioni di scope (es. tabelle config solo SUPER_ADMIN);
- niente filtro audit per `user_override_oggetti` (vedi A13).

Il payload riga ideale dal lookup model:

```json
{
  "app_label": "anagrafiche",
  "model_name": "conto_bancario",
  "area_descrizione": "Anagrafiche",
  "can_override": true,
  "reason": null
}
```

### A15. Banner operatori non assegnati: capability vs setup-status

- `frontend/src/amministrazione/components/OperatoriNonAssegnatiBanner.vue`
- BE: `amm_software/api/urls_v1.py:24` (`SetupStatusView` su
  `GET /amm-software/setup-status/`)

Il banner e' UX corretta del refactor operatore-emittenti (Q4) ma il
contratto del payload setup-status non e' documentato in `api_amm_software.md`
e i campi `count_unassigned`, `singleton_emittente_id`, `puo_auto_link`
arrivano cablati lato FE. Standardizzare il response shape e renderlo
visibile in `api.md`/`api_amm_software.md`.

### A16. Stati email log come lookup statico

- `frontend/src/amministrazione/constants.js:93` (`EMAIL_LOG_STATO`)
- `frontend/src/amministrazione/constants.js:101` (`buildEmailLogStatoOptions`)
- `frontend/src/amministrazione/views/EmailLogsListView.vue` (filtri stato)

Stessa logica di A6: i 4 stati `PENDING/SENT/FAILED/RETRY` sono enum
tecnici DB, non pertinenti al FE. Esporli via lookup statico dedicato
(`GET /api/v1/amm-software/lookup/email-log-stati/`) e consumarli con
`useGlobalLookup` (chiave `amm.email_log_stati`). Il pattern e' lo stesso
adottato per i rounding modes.

---

## B. Casi da preservare come UX defense-in-depth

| Caso | Diagnosi |
| --- | --- |
| Validazione P.IVA in `EmittenteFiscaleDrawer` | Corretta: il backend deve rifiutare, ma bloccare subito la create migliora UX. Da arricchire con `can_be_emittente_fiscale`. |
| Reset `bollo_soglia` quando `bollo_auto=false` | UX utile per evitare payload incoerenti. La normalizzazione deve restare anche backend/DB. |
| Validazione tipo/valore variazione in matrici listino | Buona UX; il set ammesso e i campi editabili devono pero' essere metadata API. |
| Banner super-admin "accesso totale" | Presentazione corretta se guidata dal detail operatore. |
| Pattern store action senza `useApiHandler.execute()` | Corretto quando lo store ritorna dati gia' unwrappati e l'interceptor gestisce errori. Vedi memoria progetto `feedback_useapihandler_solo_axios`. |
| Severity PrimeVue (`success/warn/danger`) | Presentazione pura: puo' restare nel FE. I codici di stato/livello devono invece venire da backend/lookup. |
| Editing inline multi-riga utility | Pattern adatto alla matrice. Va solo data-driven per defaults/capability. |
| Forced `attivo=false` su utility quando padre disattivo | UX corretta (`EmittenteFiscaleUtilitiesTab.vue:70`): rispetta il vincolo DB padre/figlio (`feedback_disattiva_ordine`). Il trigger DB e' la difesa finale. |
| Banner `OperatoriNonAssegnatiBanner` | UX corretta del refactor operatore-emittenti. Capability deve restare data-driven via `setup-status`. |
| Test connessione email | Pulsante UX utile, ma serve capability `can_test`/`test_reason` dal detail per nascondere/disabilitare quando emittente disattivo o SMTP non configurato. |

---

## C. Bug e debiti frontend immediati

### C1. Readonly non e' una classe CSS

Componenti da correggere subito:

- `OperatorePermessiTab.vue` - non legge readonly e lascia attivi add/save/delete.
- `EmailAccountDrawer.vue` - input, toggle, test e save restano attivi.
- `EmailTemplateDrawer.vue` - input, textarea, preview e save restano attivi.
- `TipoRuoloTipoIndirizzoDrawer.vue` - campi disabilitati, ma footer save ancora abilitabile.

Regola: ogni componente mutante deve avere sia blocco visuale sia blocco logico
nel metodo `save`/`command`.

### C2. Email drawer fuori standard

`EmailAccountDrawer.vue` e `EmailTemplateDrawer.vue`:

- mancano `// Scopo:`;
- usano titoli hardcoded (`Account Email`, `Template Email`);
- hanno placeholder visibili hardcoded (`********`);
- non disabilitano footer in readonly.

Sono fix piccoli e ad alto rendimento.

### C3. Paginazione mapping BA

Il bug `hasDefault` e' riproducibile quando:

1. esiste un mapping default;
2. la lista e' filtrata o paginata in modo da non mostrarlo;
3. il pulsante "aggiungi default" si riabilita.

Il backend puo' rifiutare, ma l'interfaccia mostra un comando non valido.

### C4. Residui `ruolo_sistema`

- `frontend/src/amministrazione/constants.js:14`
- `PermessiRiepilogoView.vue`
- create operatore in `OperatoreDrawer.vue`

Finche' serve compatibilita' va bene, ma il refactor multi-face deve avere una
data di uscita: nuovi filtri e nuove scritture non devono piu' usare
`ADMIN/OPERATIVO/DISABILITATO` come fonte primaria.

### C5. Template email preview

Il preview HTML e' il rischio piu' concreto sul modulo email. Non va lasciato
come semplice `v-html` se l'admin puo' modificare il corpo template.

### C6. Audit snapshot whitelist post multi-face

`AuditLogView.snapshotSummary()` (riga 102) elenca `ruolo_sistema` tra le
chiavi note. Post-cutover multi-face il campo non e' piu' presente sui
nuovi snapshot e va sostituito con la triade `is_super_admin`/`attivo`/
`ruolo_applicativo`. Lasciarlo non rompe nulla (i record vecchi continuano
a contenere il campo) ma fa scomparire i campi nuovi dal riepilogo.

Fix minimo (transitorio): aggiungere le 3 chiavi nuove **senza rimuovere**
`ruolo_sistema`, lasciandolo per gli snapshot storici. Long-term: il summary
arriva dal BE (vedi A13).

### C7. Endpoint `disabilita`/`riattiva` esposti, FE non li usa

Il BE espone gia':

- `POST /api/v1/amm-software/operatori/<id>/disabilita/`
- `POST /api/v1/amm-software/operatori/<id>/riattiva/`

(`amm_software/api/urls_v1.py:14-15`, view `OperatoriDisabilitaView` /
`OperatoriRiattivaView`).

Il `OperatoreDrawer` e la lista non li chiamano: la disabilitazione passa
per PATCH `attivo` nel form. Costo basso: aggiungere wrapper API + due
voci `RowActionsMenu` con `severity:'danger'` (disabilita) e default
(riattiva) gated su `data.is_active` + `auth.isObjectBlocked('amm_software',
'auth_user')`. Il pattern segue A2 (capability `can_disable`/`can_reactivate`)
quando il BE le esporra' nel detail.

---

## Piano refactor concentrico

### Fase 0 - Fix immediati frontend

1. Rendere readonly effettivo in `OperatorePermessiTab`, `EmailAccountDrawer`,
   `EmailTemplateDrawer`, `TipoRuoloTipoIndirizzoDrawer`.
2. Spostare i titoli email drawer su i18n e aggiungere `// Scopo:`.
3. Isolare o sanificare preview template email.
4. Correggere `hasDefault` mapping BA con summary backend o, temporaneamente,
   reload non filtrato dedicato.

### Fase 1 - Capability API admin

1. Detail operatore: `can_invite`, `can_disable`, `can_demote_super_admin`,
   `available_commands`.
2. Scope emittenti: `scope_mode`, `allowed_scope_modes`, `can_change_scope`.
3. Override permessi: capability per add/remove/save e reason.
4. Emittente fiscale/detail righe: `can_update`, `can_delete`,
   `non_editable_fields`.

### Fase 2 - Form defaults e lookup tecnici

1. Endpoint defaults emittente fiscale.
2. Endpoint defaults email account.
3. Lookup rounding methods/range.
4. Lookup stati email log.
5. Lookup tipo variazione listino.
6. Lookup fonti audit.

### Fase 3 - Chiusura legacy auth

1. Create operatore con contratto multi-face.
2. Rimozione `ruolo_sistema` dai nuovi filtri admin.
3. `PermessiRiepilogoView` basata su `is_super_admin`, `ruolo_applicativo`,
   stato identita e scope emittente.
4. Comandi dedicati per disabilita/riattiva invece di PATCH generico.

### Fase 4 - Audit/email hardening

1. Audit summary/diff generati dal backend.
2. Preview email in iframe sandbox.
3. Test email con capability (`can_test`, `test_reason`) e stato ultimo test.
4. Eventuale gestione create/delete template solo se prevista dal modello
   operativo; altrimenti API e FE devono dichiarare esplicitamente "template
   seedati, solo edit".

---

## Decisioni da non invertire

- Il guard route `amm-software` admin-only e' corretto:
  `frontend/src/router/index.js:424`.
- `RowActionsMenu` e pattern lista/drawer sono coerenti con gli standard.
- Le validazioni client-side vanno mantenute come UX, ma non devono essere
  l'unica fonte di verita'.
- La matrice utility emittente con LEFT JOIN configurata/non configurata e'
  il pattern giusto; va solo arricchita da metadata.
- I mapper di severity PrimeVue possono restare frontend: sono presentazione.
- Le API admin devono continuare a validare tutto lato service/DB anche dopo
  l'introduzione di metadata e capability.
- Il rounding mode resta enum tecnico Python (no tabella DB / no FK
  surrogato): single source of truth lato BE, esposto come lookup statico
  per dominio. Allineato a memoria `feedback_no_hardcoded_ids` + precedente
  catalogo Fase 1 LANDED.

---

## Piano di aggiornamento per team (DB / Backend / Frontend)

> Suddivisione operativa delle Fasi 0..4 del piano concentrico.
> Ogni fase elenca le azioni per i tre team (DB/BE/FE), con dipendenze e
> priorita'. Pattern di riferimento: `analisi-refactor.frontend-catalogo.md`
> (Fasi 1..8 LANDED 2026-04-28).
>
> Convenzioni adottate:
>
> - Niente compat fasi: ZeroErp non e' in produzione, breaking ammessi
>   (memoria `project_no_produzione_solo_sviluppo`).
> - Azioni DB sempre via brief al team su `dev/db-tid`
>   (memoria `feedback_db_actions_passaggio_team`): l'agent backend non
>   esegue migrazioni, scrive il brief.
> - Sviluppo concentrico, niente YAGNI: guard progettati per espansione
>   futura (memoria `feedback_concentrico_no_yagni`).

### Fase 0 — Hotfix FE (P0, indipendente)

Lavoro FE-only, nessuna dipendenza DB/BE. Da fare prima di tutto il resto.

**Team Frontend**

- `OperatorePermessiTab.vue`: aggiungere `useInjectReadonly()`; legare
  `:disabled` su tutti i `Select`/`ToggleSwitch`/`InputText` di riga;
  `v-if="!isReadonly"` su pulsanti Add/Save/Trash; short-circuit in
  `saveAree`/`saveAzioni`/`saveOggetti`/`saveEmittenti`. (A4 + A14).
- `EmailAccountDrawer.vue`: aggiungere `// Scopo:` iniziale; sostituire
  `title="Account Email"` con `:title="t('amm.email_account_title')"`;
  `:disabled="isReadonly"` su tutti i campi; nascondere pulsante test
  in readonly; short-circuit in `handleSave`. (A11 + C2).
- `EmailTemplateDrawer.vue`: stessi fix di `EmailAccountDrawer`; preview
  HTML dentro `<iframe sandbox="">` con `srcdoc` invece di `v-html`.
  (A12 + C5).
- `TipoRuoloTipoIndirizzoDrawer.vue`: aggiungere
  `&& !isReadOnlyEffective.value` in `canSave`; short-circuit in
  `handleSave`. (A10 + C1).
- `EmittenteFiscaleBillingAccountTab.vue`: rimpiazzare `hasDefault`
  computed locale con `store.hasDefaultMapping` ricavato dal summary
  esposto dal BE (vedi sotto). Fallback temporaneo: API `summary/`
  caricata in `watch(emittenteId)`. (A8 + C3).
- i18n: aggiungere chiavi `amm.email_account_title`,
  `amm.email_template_title`, `amm.email_smtp_password_placeholder` in
  `it.json` + `en.json`.

**Team Backend**

- Endpoint summary BA mapping (a supporto del fix C3):
  `GET /api/v1/amm-software/emittenti-fiscali/<id>/billing-account-mappings/summary/`
  → `{has_default: bool, count_specifici: int}`. View `AdminAPIView`,
  `is_search_endpoint=False`. Repository ridusa
  `EmittentiFiscaliBARepository.summary(id)`. Test in
  `apps/amm_software/tests/services/`.

**Team DB**: nessuna migrazione.

### Fase 1 — Capability operatore (P1)

Coerentizza il drawer Operatore con il modello multi-face e con i comandi
gia' esposti.

**Team DB**

- Brief al team DB per estendere `script.fn_get_operatore_detail`
  (o equivalente vista `vw_operatore_dettaglio`) con i campi:
  `can_invite`, `invite_reason`, `can_disable`, `disable_reason`,
  `can_demote_super_admin`, `demote_reason`. Logica: `can_disable=false`
  se l'operatore e' l'ultimo SUPER_ADMIN attivo
  (`script.fn_count_super_admin_attivi() <= 1`); `can_demote=false`
  stessa regola; `can_invite` solo se `last_login IS NULL AND attivo
  AND email IS NOT NULL`.
- pgTAP: 4 test coverage capability (single super-admin, multi
  super-admin, demote bloccato, invite con last_login).

**Team Backend**

- `AmmSoftwareService.update_operatore`: rimuovere traduzione legacy
  `ruolo_sistema → is_super_admin/attivo`. Il payload accettato e'
  ora `{is_super_admin?, attivo?, email?, first_name?, last_name?,
  unita_organizzativa_id?}`. Niente `ruolo_applicativo` (implicito
  OPERATORE).
- `AmmSoftwareService.create_operatore`: stesso payload + `username`,
  `password`, `qualifica_id`, `soggetto_id`. Rifiuta `ruolo_sistema`
  con `E_AMM_VALIDATION` (no compat layer).
- View `OperatoriDetailView` aggiunge nel response detail i 6 campi
  capability (`can_*`/`*_reason`).
- Niente nuovi endpoint: `disabilita/riattiva` esistono gia'.

**Team Frontend**

- `OperatoreDrawer.vue` create: rimuovere `ruolo_sistema` dal payload,
  inviare `is_super_admin/attivo` come l'update (riga 198).
- Sostituire pulsante invito con check `currentOperatore.can_invite`,
  con tooltip su `invite_reason` quando `false`.
- Aggiungere azioni di riga `RowActionsMenu` per disabilita/riattiva
  legate a `can_disable`/`is_active`. Wrapper API in
  `api/amministrazione.js` (`disabilitaOperatore`, `riattivaOperatore`)
  e store actions con `emitDataChanged(TAB_ENTITIES.OPERATORE, id)`.
- Banner `Message info` per "Devi restare almeno un super admin" quando
  `can_demote_super_admin=false` e form prova a togliere il toggle.

### Fase 2 — Scope emittenti dichiarativo (P1)

Risolve l'ambiguita' single/multi/global dello scope emittenti
(`OperatorePermessiTab`). Allinea il contratto API al modello target del
refactor operatore-emittenti (Q1+Q2): SUPER_ADMIN globale = 0 righe,
SUPER_ADMIN di emittente = 1 riga, MULTI architetturalmente chiuso.

> **Decisioni 2026-04-29 (DB+BE)**:
>
> 1. Niente regola "GLOBAL immutabile" come dogma separato: il vincolo reale
>    e' "non puoi rimuovere l'ultimo super-admin attivo" (gia' coperto da
>    `fn_check_ultimo_super_admin_attivo` di Fase 1). `can_change_scope`
>    deriva da quella funzione per i SA, `true` altrimenti.
> 2. **Funzione**, non vista: `script.fn_get_user_emittenti_scope` —
>    consumer e' lookup-by-id (drawer permessi), nessun consumer fa
>    filtro/sort sullo `scope_mode`. Coerente col pattern Fase 1.
> 3. `MULTI` chiuso **applicativamente**: `allowed_scope_modes` ritorna
>    `['GLOBAL','SINGLE']`. L'enum API resta `text` aperto: l'eventuale
>    riapertura in futuro richiederebbe rilassare `UNIQUE(auth_user_id)`,
>    quindi un cambio architetturale separato — non basterebbe toccare il
>    payload.
> 4. Cambio scope atomico via `script.fn_change_user_emittenti_scope` con
>    guard `fn_check_ultimo_super_admin_attivo` integrato. Errore tradotto
>    dal BE in `E_PROFILO_ULTIMO_SUPER_ADMIN` (gia' registrato Fase 1).

**Team DB**

- Brief: nuova `script.fn_get_user_emittenti_scope(p_auth_user_id integer)`
  RETURNS TABLE (singolo row, semantica lookup-by-id):

  ```text
  scope_mode             text         -- 'GLOBAL' | 'SINGLE'
  emittenti_ids          bigint[]     -- [] se GLOBAL, [id] se SINGLE
  allowed_scope_modes    text[]       -- sempre ['GLOBAL','SINGLE'] post Q2
  can_change_scope       boolean      -- NOT fn_check_ultimo_super_admin_attivo
                                      --   per SA; true altrimenti
  change_scope_reason    text         -- it-IT free-form, NULL se can=true
  ```

  Logica: 0 righe in `user_emittenti_fiscali` -> GLOBAL; 1 riga -> SINGLE
  con `emittenti_ids = ARRAY[id]`. La fn delega a Fase 1 per il guard.
  Idioma "lookup-by-id 0 rows" per `p_auth_user_id` non valido (coerente
  con `fn_get_operatore_detail`).

- Brief: nuova `script.fn_change_user_emittenti_scope(p_auth_user_id integer,
  p_emittente_ids bigint[])`. Esegue in transazione atomica:

  1. Validazione `array_length(p_emittente_ids, 1) IN (NULL, 1)` —
     altrimenti `RAISE` con marker `E_AMM_VALIDAZIONE` (no MULTI).
  2. Se l'utente e' SUPER_ADMIN e il nuovo scope diverge dal corrente,
     consulta `fn_check_ultimo_super_admin_attivo`: se positivo, RAISE
     con marker `E_PROFILO_ULTIMO_SUPER_ADMIN`.
  3. `DELETE FROM config.user_emittenti_fiscali WHERE auth_user_id = ...`.
  4. Se `p_emittente_ids` non NULL/non vuoto: INSERT della singola riga.

  Il trigger ultimo-super-admin esistente sta su `profili_accesso_bindings`
  e non si attiva su `user_emittenti_fiscali`: il guard va integrato nella
  funzione orchestratrice.

- pgTAP: 5 test — GLOBAL ↔ SINGLE, rifiuto MULTI (>1 emittente), guard
  ultimo-SA su PUT GLOBAL→SINGLE (demotion), guard su PUT inverso.

**Team Backend**

- `AmmSoftwareService.get_emittenti_scope(auth_user_id)`: rinominata da
  `get_emittenti_scope` (lista grezza) a metodo che ritorna lo shape della
  fn DB. La vecchia funzione resta come `_list_emittenti_scope` interna
  (usata internamente per la lista completa, se serve).

- View `EmittentiScopeView` (GET): risposta = output `fn_get_user_emittenti_scope`.
  PATCH valida `scope_mode IN allowed_scope_modes`, normalizza
  `emittenti_ids` (`[]` se GLOBAL, `[id]` se SINGLE), delega a
  `fn_change_user_emittenti_scope`. Il service avvolge la chiamata in
  `_run_or_raise_super_admin_guard` (gia' presente da Fase 1) per tradurre
  `DatabaseError E_PROFILO_ULTIMO_SUPER_ADMIN` in `ServiceError`.

- Errore strutturato dedicato per shape invalido (es. `MULTI` o array
  con piu' di 1 elemento): `E_AMM_SCOPE_NON_AMMESSO` (HTTP 400). Niente
  override su `E_PROFILO_ULTIMO_SUPER_ADMIN`: si riutilizza Fase 1.

**Team Frontend**

- `OperatorePermessiTab.vue`: leggere `scope_mode`/`allowed_scope_modes`/
  `can_change_scope`/`change_scope_reason` dallo store. Render condizionale:
  - `'GLOBAL'` selezionato: testo "Tutti gli emittenti" + radio attivo.
  - `'SINGLE'` selezionato: `Select` singolo (gia' presente, ora dichiarato).
  - `'MULTI'`: non incluso in `allowed_scope_modes` post Q2 — niente
    branch FE da implementare.
- Radio `GLOBAL/SINGLE` gated su `can_change_scope`; quando `false`, radio
  disabled + tooltip su `change_scope_reason`.
- Pulsante Salva propaga `{scope_mode, emittenti_ids: [...]}`. Il BE
  normalizza: se `scope_mode='GLOBAL'`, `emittenti_ids` viene ignorato.

### Fase 3 — Form-defaults emittente fiscale (P1)

Sposta i defaults fiscali dal FE al BE via `ParameterService` (pattern
catalogo Fase 1 LANDED).

**Team DB**

- Brief: seed in `config.parameters` (codice `EMITTENTE_DEFAULT_*`):
  `EMITTENTE_DEFAULT_ATTIVO=true`, `EMITTENTE_DEFAULT_BOLLO_AUTO=false`,
  `EMITTENTE_DEFAULT_BOLLO_SOGLIA=null`,
  `EMITTENTE_DEFAULT_ROUNDING_POLICY=HALF_UP`. Cascata
  user→group→emittente→default via `script.fn_get_parameter_full`.
  pgTAP: test cascata default + override emittente.
- Brief separato per il lookup statico rounding modes
  (`/amm-software/lookup/rounding-modes/` ritorna 4 codici): nessuna
  tabella; il backend serve l'enum dal codice Python (single source of
  truth, vedi A6).

**Team Backend**

- `AmmSoftwareService.get_emittente_form_defaults(*, django_user_id,
  group_ids, emittente_fiscale_id)`: chiama
  `ParameterService.get_defaults([...])` e ritorna
  `{defaults: {...}, non_editable_fields: ['codice', 'soggetto_id']}`.
- View `ApiEmittentiFormDefaults` su
  `GET /api/v1/amm-software/emittenti-fiscali/form-defaults/`. Riusa
  `get_user_context` (gia' pubblico in catalogo, vedi
  `catalogo-building-block-backend.md`).
- View `ApiEmittenteRoundingModesLookup` simmetrica a
  `ApiUomRoundingModesLookup`. Costante `_ROUNDING_MODE_VALIDI_EMITTENTE
  = ('HALF_UP','HALF_DOWN','UP','DOWN')` nel service.

**Team Frontend**

- `EmittenteFiscaleDrawer.vue`: rimuovere `FORM_DEFAULT` cablato (riga 62);
  sostituire con `getEmittenteFormDefaults()` chiamato in
  `applyFormDefaults()` (pattern catalogo Fase 8). Cast tipi via
  `parameterCast.js` (`paramBool`/`paramString`).
- `EmittenteRoundingModeSelect.vue`: nuovo wrapper riusabile, chiave
  `useGlobalLookup('amm.emittenti_rounding_modes')` su
  `lookupEmittenteRoundingModes` (nuovo in `apiAmministrazione.js`).
- Sostituire `<Select :options="ROUNDING_METHOD_VALUES">` con
  `<EmittenteRoundingModeSelect>` in `EmittenteFiscaleDrawer` e
  `EmittenteFiscaleUtilitiesTab`.
- Rimuovere `ROUNDING_METHODS` + `ROUNDING_METHOD_VALUES` da
  `amministrazione/constants.js`. Lasciare solo
  `ROUNDING_DECIMALI_RANGE` (range tecnico, anche'esso candidato al
  lookup nei follow-up).

### Fase 4 — Capability matrici (P1)

Estende il pattern `non_editable_fields` + capability di riga alle 4
matrici amm-software.

**Team DB**: nessuna migrazione obbligatoria. Le viste esistenti
(`vw_emittente_fiscale_utilities_matrix`,
`vw_categorie_clienti_listini_matrix`,
`vw_tipi_ruolo_tipi_indirizzo`) gia' coprono il LEFT JOIN; basta che il
service BE ne legga le proiezioni.

**Team Backend**

- Helper riusabile `compute_non_editable_fields(record, *, kind)` in
  `apps/amm_software/services/_helpers.py` (pattern catalogo Fase 5).
- Detail emittente fiscale (`fn_get_emittente_dettaglio`): includere
  `non_editable_fields=['codice','soggetto_id']` + capability di riga
  `can_update`, `can_delete` su utilities/BA mapping.
- `CategoriaClienteListinoService.list/detail`: includere
  `tipo_variazione_options` (lookup `config.tipi_variazione_categoria`,
  ammette `PERCENTUALE`/`VALORE_FISSO`/`null`) +
  `non_editable_fields=['categoria_cliente_id', 'utility_id',
  'emittente_soggetto_ruolo_id', 'classe_utenza_id']`.
- `TipoRuoloTipoIndirizzoService`: ritornare
  `fallback_options[]` filtrate per ruolo/tipo (BE applica gia' il
  guard "non se stesso" + ciclo).

**Team Frontend**

- `EmittenteFiscaleUtilitiesTab.vue`: capability di riga
  `data.can_configure`/`can_update`/`can_remove` invece di derivare da
  `record_id`. Defaults riga letti da `data.defaults`, non hardcoded.
- `CategoriaClienteListinoDrawer.vue`: rimuovere `PERCENTUALE`/
  `VALORE_FISSO` cablati (riga 47, 130, 160); usare lookup statico
  `core/lookup/codici/?rel=config.tipi_variazione_categoria`.
- `TipoRuoloTipoIndirizzoDrawer.vue`: filtrare
  `fallback_tipo_indirizzo_id` su `data.fallback_options`.

### Fase 5 — Audit hardening + email log lookup (P1)

**Team DB**

- Brief: vista `vw_audit_sources` espone le tabelle audit con
  `code, label_key, area_funzionale`. Aggiunge `user_override_oggetti`
  (permessi v2) + `identita_digitali` (multi-face).
- Brief funzione `fn_audit_summary(audit_log_id) RETURNS jsonb` che
  ritorna `{summary: text, diff: jsonb[]}` calcolato dal trigger di
  audit (delta vs riga precedente).

**Team Backend**

- View `ApiAuditSourcesLookup` su
  `GET /api/v1/amm-software/lookup/audit-sources/` ritorna le righe
  della vista.
- View `ApiEmailLogStatiLookup` su
  `GET /api/v1/amm-software/lookup/email-log-stati/` (lookup statico
  da costante Python `_EMAIL_LOG_STATI_VALIDI`).
- `ApiAuditLogList`: aggiungere campo `summary` (e opzionalmente
  `diff`) nel response, calcolato via `fn_audit_summary`.

**Team Frontend**

- `AuditLogView.vue`: rimuovere `buildAuditTabellaOptions` (riga 34) e
  `snapshotSummary` locale (riga 95-107); consumare `audit_sources` e
  `summary`/`diff` dal BE. `useGlobalLookup('amm.audit_sources')`.
- `constants.js`: rimuovere `EMAIL_LOG_STATO`, `buildEmailLogStatoOptions`,
  `getEmailLogStatoSeverity` (la severity passa al BE come parte del
  lookup, oppure resta lato FE come mappa pure-presentation di label).
- `EmailLogsListView.vue`: usare nuovo `EmailLogStatoSelect.vue`
  (riusabile cross-app se altri admin lo richiederanno).

### Fase 6 — Email hardening (P0/P1 misto) — LANDED 2026-04-29

**Team DB**: nessuna migrazione. Ultimo esito test SMTP persistito in
`config.email_account.meta` jsonb (chiavi `last_test_outcome`,
`last_test_at`, `last_test_message`) — extension rejected, jsonb
sufficiente per il ritmo di scrittura (1 update per click "test").

**Team Backend** — chiuso

- `apps/core/services/html_sanitizer_service.py` (nuovo): `sanitize_email_html`
  basato su `bleach==6.3` (aggiunto a `requirements.in`). Whitelist
  tag/attr/protocol; rimuove `<script>`/`<style>` con il loro contenuto
  via regex pre-bleach; strip commenti HTML.
- `apps/amm_software/api/email_views.py`:
  - `_derive_test_capability` + `_extract_last_test` + `_enrich_account_with_capability`
    (helper privati): derivano `can_test`/`test_reason` (chiavi i18n
    `amm.email_test_reason_inactive` / `_no_password`); estraggono
    last_test_* dal meta jsonb; rimuovono i campi grezzi dal payload FE.
  - `EmailAccountDetailView.get/patch`: applicano `_enrich_account_with_capability`
    al detail.
  - `EmailAccountTestView.post`: verifica esistenza account, esegue
    `EmailDispatchService.test_connection`, persiste outcome via
    `repo.update_account_last_test`, ritorna detail arricchito (FE
    aggiorna in-place senza GET extra).
  - `EmailTemplatePreviewView.post`: sanifica `corpo_html` con
    `sanitize_email_html` prima del return.
- `apps/core/db/email_repository.py`:
  - `get_account` ora include `has_smtp_password` (derivato) e `meta`
    (decodificato).
  - `update_account_last_test(account_id, *, outcome, tested_at, message)`:
    UPDATE atomico via `meta = COALESCE(meta, '{}'::jsonb) || jsonb_build_object(...)`.

**Team Frontend** — chiuso

- `EmailAccountDrawer.vue`: pulsante test `:disabled="!canTest"`,
  `v-tooltip.top` con `t(testReasonKey)` quando disabilitato; `Tag`
  con `lastTestSeverity` (success/danger/secondary) + timestamp
  formattato. `handleTest` aggiorna `store.currentAccount` con il
  detail arricchito ricevuto dal POST.
- `EmailTemplateDrawer.vue`: gia' usa iframe sandbox (Fase 0); ora il
  `srcdoc` riceve HTML **gia' sanificato BE** (defense-in-depth).
- i18n: 7 nuove chiavi in `it.json` + `en.json` (`email_test_reason_*`,
  `email_last_test_*`).

**Test BE (22 nuovi, 1845/1845 verdi)**

- `apps/core/tests/services/test_html_sanitizer_service.py`: 11 test
  whitelist (script/event/protocol/iframe/style/comment/table/mailto).
- `apps/amm_software/tests/api/test_email_views_fase6.py`: 11 test
  capability detail (4 casi), persistenza outcome (3 casi), preview
  sanitize (2 casi), not-found (1 caso).

### Fase 7 — Cleanup legacy (P2) — LANDED Python+FE 2026-04-29

**Team DB** — brief dedicato (in attesa)

- File: `docs/it/dev/work-in-progress/brief-db-fase7-dismissione-ruolo-sistema.md`.
- Scope: refactor `fn_crea_operatore` + `fn_crea_risorsa_umana` (nuova
  firma `p_is_super_admin`/`p_attivo`); drop `fn_get_ruolo_sistema`;
  rimozione colonna `ruolo_sistema` da vista `risorse_umane_auth_user`;
  `DROP TYPE config.ruolo_sistema`. Sequenza in 4 migration con suite
  pgTAP da aggiornare. Prerequisito §4.6.H.2 gia' chiuso.

**Team Backend** — chiuso

- `apps/amm_software/db/amm_software_repository.py`:
  - `_legacy_ruolo_from_contract` privato (compat layer per fn DB
    legacy). Mai esposto.
  - `list_operatori`/`list_operatori_for_riepilogo`/`get_permessi_riepilogo`:
    rimossi `ruolo_sistema` da filtri+SELECT, sostituiti con
    `is_super_admin`/`ruolo_applicativo`/`is_active`.
  - `update_operatore`: contract `is_super_admin` + `attivo` ortogonali.
  - `crea_operatore`: contract `is_super_admin` + `attivo`; passa
    `p_ruolo_sistema` legacy alla fn DB tramite il translator privato.
- `apps/amm_software/services/amm_software_service.py`: rimosso
  `_ruolo_sistema_from_contract_nuovo` (logica interna al repo).
- `apps/amm_software/api/views.py`: rimossi query param + payload
  `ruolo_sistema` da OperatoriList/OperatoriDetail/PermessiRiepilogo
  (sostituito con `is_super_admin`).
- `apps/amm_software/types.py` + `constants.py`: rimossi
  `ruolo_sistema`/`RUOLO_*`/`DEFAULT_RUOLO_SISTEMA`.
- `apps/core/api/me_view.py` + `apps/core/api/views.py`
  (PermessiEffettiviView): output multi-face puro
  (`is_super_admin`+`ruolo_applicativo`+`is_active`); `is_admin_globale`
  derivato da `is_super_admin` invece di `ruolo_sistema=='ADMIN'`.
- `apps/core/db/risorse_umane_core_repository.py`: refactor simmetrico
  con `_legacy_ruolo_from_contract` privato.
- `apps/anagrafiche/models.py`: rimosso campo `ruolo_sistema` dal modello
  ORM `RisorseUmaneAuthUser` (la vista DB lo espone ancora ma nessun
  reader Python lo legge).
- `apps/ai_assistant/tools/config_tools.py`: tool `cerca_operatori`
  refactor — param `is_super_admin` (bool) sostituisce `ruolo_sistema`
  (str). `_FIELD_MAP` aggiornato.
- `apps/core/services/permissions_resolver.py`,
  `apps/core/api/permissions.py`: aggiornati commenti (no logica).

**Team Frontend** — chiuso

- `core/constants.js`: rimosso enum `RUOLO_SISTEMA`. Resta `RUOLO_APPLICATIVO`.
- `amministrazione/constants.js`: rimossi `buildRuoloOptions` +
  `getRuoloSeverity`. Aggiornati commenti.
- `amministrazione/stores/operatori.js`: rimosso filtro
  `ruolo_sistema`; resta `is_super_admin`/`is_active`/`unita_organizzativa_id`.
- `amministrazione/views/PermessiRiepilogoView.vue`: refactor completo
  multi-face. Filtro `superAdminFilter` con `buildFilterSuperAdminOptions`
  tri-state (tutti/solo super/escludi). Nuova colonna `Stato` con
  `getStatoLabel`/`getStatoSeverity` data-driven da
  `is_super_admin`/`ruolo_applicativo`/`is_active`.
- `OperatoreDrawer.vue` + `OperatoriListView.vue` + `stores/auth.js`:
  aggiornati commenti residui (no logica).
- i18n: rimosse chiavi `amm.ruolo_admin`/`_operativo`/`_disabilitato`/
  `_all`/`permessi_col_ruolo`/`permessi_filter_ruolo`. Aggiunte
  `permessi_col_stato`/`permessi_stato_super_admin`/`_disabilitato`/
  `_operatore` (it.json + en.json).

**Test e verifiche**

- BE: 1845/1845 verdi (suite invariata, 7 test aggiornati per il nuovo
  contract: 5 in `test_amm_software_service` / `test_operatori_views` /
  `test_crea_operatore`, 1 in `test_risorse_umane_core_repository`,
  1 in `test_me_view`).
- FE: `vite build` verde 958ms.

### Fase 7-original — testo originale (storico)

> Il refactor originale prevedeva: brief DB per dismissione campo
> `ruolo_sistema` su `risorse_umane_auth_user` (con backfill verifica +
> deprecate per gli script che lo leggono); rimozione `_ruolo_sistema_from_contract_nuovo`
> da `AmmSoftwareService`; refactor completo `PermessiRiepilogoView`
> basato su `is_super_admin`/`ruolo_applicativo`/`attivo`/scope emittente;
> rimozione `RUOLO_SISTEMA` enum dal core/constants. Tutti gli obiettivi
> del piano originale sono stati raggiunti — la dismissione DB resta
> aperta in attesa del team DB.

### Fase 8 — Override oggetti (permessi v2) — capability lookup — LANDED 2026-04-29

**Team DB**: nessuna migrazione (capability derivata da blacklist Python).

**Team Backend** — chiuso

- `apps/amm_software/db/amm_software_repository.py`:
  - Costante modulo-level `_MODEL_OVERRIDE_RISERVATI` con 11 tuple
    `(app_label, model_name)` del kernel permessi (auth_user,
    identita_digitali, profili_accesso/_bindings, area_model_overrides,
    user_override_aree/azioni/oggetti, user_emittenti_fiscali,
    profili_reparto_aree/azioni).
  - `list_model_overrides`: arricchisce ogni riga con
    `can_override: bool` + `reason: str|None` (chiave i18n
    `amm.model_override_reason_riservato` quando riservato).
- `apps/amm_software/services/amm_software_service.py`
  `put_override_oggetti`: doppia guard — esistenza nel catalogo +
  `can_override=True` (defense-in-depth: il FE filtra il dropdown,
  il BE rifiuta la request crafted).

**Team Frontend** — chiuso

- `OperatorePermessiTab.vue`:
  - `modelOverrideOptions` filtra `m.can_override === true` —
    i model riservati spariscono dal dropdown.
  - `modelOverrideReason(row)` risolve la chiave i18n se la riga
    pre-esistente punta a un model diventato riservato (drift
    storico).
  - Cella `<Select>` wrapped in `<span v-tooltip.top>` + `:disabled`
    quando il model corrente e' riservato — tooltip espone il reason
    tradotto.
- i18n: 1 nuova chiave `amm.model_override_reason_riservato` in
  `it.json` + `en.json`.

**Test e verifiche**

- BE: 1847/1847 verdi (1845 → +2 nuovi):
  - `test_get_model_overrides_lookup_riservato` — capability
    `can_override=False` + reason i18n esposti per il model
    `auth_user`.
  - `test_put_override_oggetti_rifiuta_model_riservato` — guard
    service: scrittura su model riservato → `E_AMM_VALIDAZIONE`.
- FE: `vite build` verde 983ms.

---

### Sintesi tabellare per priorita' e team

| Fase | Punti coperti | Team DB | Team Backend | Team Frontend | Priorita' |
| --- | --- | --- | --- | --- | --- |
| 0 | A4, A8, A10, A11, A12, C1..C3, C5 | nessuna | endpoint summary BA mapping | readonly hotfix 4 file + iframe sandbox + i18n | P0 |
| 1 | A1, A2, C4, C7 | capability operatore (vista/fn) | service create/update + detail capability | drawer payload uniforme + azioni disabilita/riattiva | P1 |
| 2 | A3 | fn_get_user_emittenti_scope + fn_change_user_emittenti_scope (atomica + guard) | service get + PATCH atomico, riuso Fase 1 guard | radio GLOBAL/SINGLE, tooltip reason | P1 |
| 3 | A5, A6 | seed parametri + brief lookup statici | form-defaults + lookup rounding-modes | RoundingModeSelect EF + applyFormDefaults | P1 |
| 4 | A7, A9, A10 metadata | (nessuna) | non_editable_fields + capability riga | drawer/tab data-driven | P1 |
| 5 | A13, A14, A16 | vw_audit_sources + fn_audit_summary | lookup audit-sources + email-log-stati + summary | rimozione constants locali | P1 |
| 6 | A12, B (test email) | (opzionale) | render template sanificato + can_test | iframe sandbox + capability test | P0/P1 |
| 7 | C4 cleanup | dismissione ruolo_sistema | rimozione compat layer | rimozione enum RUOLO_SISTEMA + PermessiRiepilogo | P2 |
| 8 | A14 | (nessuna) | can_override su lookup model | filtro options | P2 |

**Da NON toccare** (falsi positivi del documento originale):

- `EmittenteFiscaleUtilitiesTab.vue:70` forced `attivo=false` se padre
  inattivo: defense-in-depth corretta, allineata al trigger DB
  `feedback_disattiva_ordine`.
- `OperatorePermessiTab.vue:75` pattern store action senza
  `useApiHandler.execute()`: corretto per memoria
  `feedback_useapihandler_solo_axios`.
- `AuditLogView.vue:38` filtro data default ultimo mese: standard di
  progetto (`feedback_filtro_data_liste`).
- `RepartiProfiloView.vue` + `RepartoProfiloEditor.vue`: usano gia' il
  pattern provider/inject readonly correttamente. Niente fix.
- `TipoRuoloTipoIndirizzoDrawer.vue` campi `:disabled`: gia' coperto
  con `isReadOnlyEffective` (riga 132..152). Solo `canSave`/`handleSave`
  da rinforzare.

---

## Dipendenze e ordine di esecuzione

```text
Fase 0 (FE-only) ──► standalone, parte subito

Fase 1 ──► DB capability operatore ──► BE service ──► FE drawer + azioni
Fase 2 ──► DB scope view ──► BE PATCH ──► FE render
Fase 3 ──► DB seed parameters ──► BE endpoint ──► FE wrapper select
Fase 4 ──► (DB no) ──► BE non_editable_fields ──► FE consumer
Fase 5 ──► DB audit + fn_summary ──► BE lookup + summary ──► FE rimozione constants
Fase 6 ──► (DB opz) ──► BE render+sanitize ──► FE iframe sandbox
Fase 7 ──► dipende da chiusura cutover multi-face (Fase 4.6.H.2)
Fase 8 ──► (DB no) ──► BE can_override ──► FE filtro
```

Le Fasi 1..6 sono indipendenti tra loro a livello applicativo: possono
procedere in parallelo se il team DB allinea le viste/seed in tempo. La
Fase 7 deve aspettare la chiusura del cutover multi-face. Fasi 0 e 8
sono FE-light/standalone.

---

## Pattern emersi e memoria progetto

Il piano riusa pattern gia' consolidati (memoria progetto) — niente nuovi
pattern da introdurre:

- `feedback_no_hardcoded_ids` — Fase 3 (rounding modes, defaults).
- `feedback_slot_override_matrix` — Fase 4 (matrici utility/categorie).
- `feedback_classify_payload_three_state` — non applicabile qui.
- `feedback_disattiva_ordine` — Fase 1 (disabilita/riattiva).
- `feedback_payload_helpers_duplicati` — Fase 1, 4 (PayloadValidator).
- `feedback_useapihandler_solo_axios` — Fase 0 (mantenere pattern).
- `feedback_stato_terminale_con_data` — non applicabile (operatore non
  ha workflow stato-terminale-con-data).
- `feedback_drawer_readonly` — Fase 0 (readonly + injecting).

Nessuna nuova memoria pattern necessaria.
