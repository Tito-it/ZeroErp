# Analisi refactor frontend amm-software

<!-- markdownlint-disable MD036 MD031 -->

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
> - `docs/it/dev/api.md` - envelope API, command/read, errori strutturati.
> - `docs/it/dev/frontend/frontend-standards.md` - pattern lista/drawer,
>   readonly, RowActionsMenu, i18n.
> - `docs/it/dev/work-done/frontend/guida-sviluppo-frontend.md` - convenzioni
>   Vue, store, API client.
> - `docs/it/dev/work-in-progress/refactor-operatore-emittenti.md` - evoluzione
>   rapporto operatore/emittente e multi-face auth.
> - `docs/it/dev/work-in-progress/permessi-e-autorizzazioni-v3.md` - modello
>   autorizzativo.
> - `docs/it/dev/work-in-progress/analisi-refactor.frontend-catalogo.md` -
>   pattern `form-defaults`, lookup tecnici e capability di riga.
> - `docs/it/dev/work-in-progress/analisi-refactor.frontend-vendite.md` -
>   pattern `available_actions`, `non_editable_fields`, command data-driven.
>
> Principio: il frontend amm-software deve restare presentazione + UX. Il
> backend/DB decidono contratti auth, capability, ambito emittenti, default
> operativi, invarianti fiscali, fonti audit e policy email.

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
| Audit | `AuditLogView.vue` | Utile per debug admin, ma filtri tabella e summary snapshot sono cablati nel FE. |

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
  "ruolo_applicativo": "OPERATORE",
  "is_super_admin": false,
  "attivo": true,
  "unita_organizzativa_id": 10
}
```

Il backend puo' continuare a tradurre internamente verso campi legacy, ma il FE
non deve piu' conoscere `ruolo_sistema` per nuove scritture.

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

- `frontend/src/amministrazione/constants.js:73`
- `frontend/src/amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:16`
- `frontend/src/amministrazione/components/EmittenteFiscaleUtilitiesTab.vue:84`

`ROUNDING_METHODS` e `ROUNDING_DECIMALI_RANGE` sono allineati ai CHECK DB, ma
questo allineamento e' manuale. Ogni modifica al constraint richiede una patch
frontend.

Pattern proposto:

```text
GET /api/v1/config/lookups/rounding-methods/
GET /api/v1/amm-software/emittenti-fiscali/form-defaults/
```

Il FE puo' mantenere severity/label presentation, ma non il set ammesso e il
range tecnico.

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

Bug immediato: `canSave` non considera `isReadOnlyEffective`. In edit ritorna
sempre `true`, quindi il footer puo' ancora inviare `handleSave()` anche quando
i campi sono disabilitati.

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

- `frontend/src/amministrazione/constants.js:60`
- `frontend/src/amministrazione/views/AuditLogView.vue:36`
- `frontend/src/amministrazione/views/AuditLogView.vue:93`

Le tabelle audit filtrabili sono codificate in JS:

- `user_override_aree`
- `user_override_azioni`
- `user_emittenti_fiscali`
- `risorse_umane_auth_user`
- `profili_reparto_aree`
- `profili_reparto_azioni`

Se cambia il trigger audit o si aggiunge una fonte, il FE resta incompleto. Il
backend deve esporre `audit_sources` con label key.

Anche `snapshotSummary()` e' dominio presentazionale troppo fragile: whitelista
chiavi note e perde informazione appena cambia lo snapshot. Meglio restituire
dal backend:

```json
{
  "summary": "Operatore 42: livello LETTURA su area vendite",
  "diff": [
    {"field": "livello", "old": "BLOCCATO", "new": "LETTURA"}
  ]
}
```

---

## B. Casi da preservare come UX defense-in-depth

| Caso | Diagnosi |
| --- | --- |
| Validazione P.IVA in `EmittenteFiscaleDrawer` | Corretta: il backend deve rifiutare, ma bloccare subito la create migliora UX. Da arricchire con `can_be_emittente_fiscale`. |
| Reset `bollo_soglia` quando `bollo_auto=false` | UX utile per evitare payload incoerenti. La normalizzazione deve restare anche backend/DB. |
| Validazione tipo/valore variazione in matrici listino | Buona UX; il set ammesso e i campi editabili devono pero' essere metadata API. |
| Banner super-admin "accesso totale" | Presentazione corretta se guidata dal detail operatore. |
| Pattern store action senza `useApiHandler.execute()` | Corretto quando lo store ritorna dati gia' unwrappati e l'interceptor gestisce errori. |
| Severity PrimeVue (`success/warn/danger`) | Presentazione pura: puo' restare nel FE. I codici di stato/livello devono invece venire da backend/lookup. |
| Editing inline multi-riga utility | Pattern adatto alla matrice. Va solo data-driven per defaults/capability. |

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
