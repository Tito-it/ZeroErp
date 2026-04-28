# Analisi refactor frontend vendite

<!-- markdownlint-disable MD036 MD031 -->

> Obiettivo: identificare cosa nel frontend vendite e' logica di dominio
> mascherata da presentazione, cosa e' UX defense-in-depth legittima e cosa
> richiede un contratto API piu' ricco.
>
> L'area vendite e' piu' articolata delle altre: non e' una singola CRUD area,
> ma un insieme di sottodomini collegati da pricing, stati documento,
> validita' temporale e integrazioni operative.
>
> Riferimenti vincolanti:
>
> - `docs/it/dev/api.md` — envelope API, command/read, errori strutturati.
> - `docs/it/dev/frontend/frontend-standards.md` — pattern lista/drawer,
>   readonly, RowActionsMenu, i18n.
> - `docs/it/dev/work-done/frontend/guida-sviluppo-frontend.md` — convenzioni
>   Vue, store, API client.
> - `docs/it/dev/work-in-progress/analisi-refactor.frontend-catalogo.md` —
>   pattern condivisi per defaults, metadata API, capability di riga.
> - `docs/it/dev/work-done/analisi-refactor.frontend-anagrafiche.md` —
>   pattern `non_editable_fields`, `evento_stato_corrente`,
>   `classify EMPTY/PARTIAL/VALID`.
>
> Principio: il frontend vendite deve restare presentazione + UX. Il DB/backend
> decidono pricing, stati, transizioni, capability, campi editabili, default
> operativi e invarianti temporali.

---

## Mappa sottodomini frontend

| Sottodominio | File principali | Stato architetturale |
| --- | --- | --- |
| Preventivi | `frontend/src/vendite/preventivi/*` | Funzionale ma ancora acerbo: form testata troppo tecnico, transizioni cablate in FE, bug import `LookupSelect`. |
| Listini e versioni | `frontend/src/vendite/components/ListinoDrawer.vue`, `Versione*`, `ListiniSearchTable.vue` | Buona separazione comando/API, ma defaults temporali e capability versioni sono ancora decisi dal FE. |
| Righe listino | `VersioneDrawer.vue`, `ApplicaVariazioneDialog.vue`, `stores/listiniRighe.js` | Pattern master-detail coerente. Mancano metadata API per `can_edit`, `can_delete`, `can_apply_variazione`. |
| Contratti | `ContrattoDrawer.vue`, `ContrattoRigheDrawer.vue`, `ContrattiSearchTable.vue` | Sottodominio piu' maturo: molte regole sono gia' DB/backend-first, ma il FE replica modalita', transizioni e whitelist. |
| Promo articoli | `PromoArticoloDrawer.vue`, `PromoArticoliSearchTable.vue` | Buon modello data-driven lato backend, ma il FE ricalcola stato temporale e enum. Serve detail piu' ricco. |
| Approvazioni prezzo | `ApprovazioniPrezzoListView.vue`, `api/approvazioniPrezzo.js` | Workflow command-style corretto, ma UI lista e azioni non usano ancora capability/reason da API. |
| Pricing diagnostico | `TestResolverDialog.vue`, `useLimitiPricing.js` | Lecito come strumento diagnostico. Da isolare come read/diagnostic, non come regola di business. |

---

## Sintesi priorita'

| Priorita' | Tema | Diagnosi |
| --- | --- | --- |
| P0 | `PreventiviForm.vue` usa `LookupSelect` senza import | Bug reale di build/runtime. Da correggere subito prima di refactor concettuali. |
| P0 | Transizioni preventivo cablate in FE | Rischio drift col DB (`fn_cambia_stato_preventivo`). Serve `available_actions` dal detail. |
| P1 | Metadata capability mancanti | Contratti, promo, listini-versioni e righe listino devono ricevere `can_*`, `*_reason`, `non_editable_fields`. |
| P1 | Defaults temporali e operativi nel FE | `oggi`, `domani`, `oggi+1`, default modalita/listino/prezzo devono arrivare dal backend o da parameters. |
| P1 | Enum e modalita pricing cablati | `PERCENTUALE`, `VALORE_FISSO`, `PREZZO_FISSO`, `A/B/C`, `COMMODITY/COMMERCIO` devono essere lookup/config resolver. |
| P2 | UX lista preventivi | Il form usa ID numerico per billing account; va allineato a `BillingAccountLookup` come contratti. |
| P2 | Duplicazione lookup UoM operative | Pattern ripetuto in contratti, listini e promo. Serve composable condiviso o endpoint form-defaults. |

---

## A. Logica di business da spostare a backend/API

### A1. Transizioni preventivo esposte come `available_actions` (PRIORITA' MASSIMA)

- `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue:144`

Il FE decide il workflow:

- `BOZZA -> EMESSO | ANNULLATO`
- `EMESSO -> ACCETTATO | RIFIUTATO | ANNULLATO`
- `ACCETTATO -> ANNULLATO`

Questa e' logica di dominio. Il backend ha gia' `cambia_stato` delegato alla
funzione DB e il service conosce gli stati modificabili/fatturabili. Il detail
preventivo deve esporre:

```json
{
  "available_actions": [
    {
      "key": "emetti",
      "target_state": "EMESSO",
      "label_key": "preventivi.azione_emetti",
      "severity": "info",
      "icon": "pi pi-send",
      "requires_confirm": false
    }
  ],
  "non_editable_fields": ["utility_id"],
  "can_edit_testata": true,
  "can_edit_righe": true,
  "can_push_commessa": false,
  "can_push_commessa_reason": "Preventivo non accettato"
}
```

Il frontend renderizza azioni e campi usando metadata. La funzione
`transizioni()` sparisce o diventa un mapper puramente visuale da payload API a
bottoni.

### A2. Stato editabilita' preventivo e integrazione non calcolati in Vue

- `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue:43`
- `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue:46`
- `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue:49`

`isModificabile = stato === BOZZA` e `isAccettato = stato === ACCETTATO` sono
regole di processo. Sono corrette per l'UX, ma devono essere lette dal detail:

- `can_edit_testata`
- `can_edit_righe`
- `can_view_integrazione`
- `can_push_commessa`
- `can_create_revisione`

Motivo: le condizioni reali cambieranno facilmente con scadenza, pratica
collegata, approvazioni prezzo pendenti, fatture/commesse gia' generate.
Lasciare `stato === ...` nel FE garantisce drift.

### A3. Modalita pricing contratto A/B/C cablata nel frontend

- `frontend/src/vendite/components/ContrattoDrawer.vue:83`
- `frontend/src/vendite/components/ContrattoDrawer.vue:162`
- `frontend/src/vendite/components/ContrattoDrawer.vue:168`
- `frontend/src/vendite/components/ContrattoDrawer.vue:270`

Il commento del componente dichiara esplicitamente che la modalita e'
"FE-only". E' un odore architetturale: la modalita A/B/C e' dominio pricing,
non presentazione.

Refactor proposto:

- backend/detail contratto espone `pricing_modalita: "A" | "B" | "C"`;
- backend/form-config espone `pricing_modalita_options` con label key e vincoli;
- endpoint update accetta una forma semantica (`pricing_profile`) oppure continua
  ad accettare i campi atomici, ma il FE non deriva piu' la modalita dai null.

Il FE puo' ancora usare `SelectButton`; non deve essere lui a definire che
"assenza listino = C" o "listino senza variazione = B".

### A4. Transizioni contratto cablate in FE

- `frontend/src/vendite/components/ContrattoDrawer.vue:376`

La scelta `DRAFT -> ATTIVO -> CESSATO` e' allineata al service attuale, ma e'
comunque duplicata rispetto al backend (`_CONTRATTO_PATCH_ALLOWED_BY_STATE` e
`cambia_stato`). Come per preventivi, il detail contratto deve esporre:

- `available_actions`
- `can_change_state`
- `state_action_requires_date`
- `default_action_date`
- `min_action_date`

Il dialog di cessazione resta UX, ma data default e semantica programmata devono
essere metadata. Oggi `openCessaDialog()` usa `new Date()` come policy locale.

### A5. Defaults contratto da form-defaults backend

- `frontend/src/vendite/components/ContrattoDrawer.vue:102`

Nel default form sono cablati:

- `ambito: 'COMMODITY'`
- `valido_dal = oggi`
- `data = oggi`
- `modalita = 'A'`
- `tipo_variazione_globale = PERCENTUALE` quando si sceglie A

Questi default non sono solo UI: determinano il comportamento commerciale.
Vanno restituiti da un endpoint tipo:

```text
GET /api/v1/vendite/contratti/form-defaults/?billing_account_id=...
```

Payload minimo:

- `default_ambito`
- `default_data`
- `default_valido_dal`
- `default_modalita_pricing`
- `default_tipo_variazione_globale`
- `categoria_cliente_snapshot_id`
- `utility_tipo_classe_required`
- `pricing_modalita_options`

### A6. Promo articoli: stato temporale e campi editabili devono arrivare dal detail

- `frontend/src/vendite/components/PromoArticoloDrawer.vue:52`
- `frontend/src/vendite/components/PromoArticoloDrawer.vue:69`
- `frontend/src/vendite/components/PromoArticoloDrawer.vue:78`
- `frontend/src/vendite/components/PromoArticoloDrawer.vue:82`
- `frontend/src/vendite/components/PromoArticoloDrawer.vue:225`

Il backend ha gia' una guard matura (`E_PROMO_RETROATTIVA`,
`E_PROMO_INIZIATA_CAMPI_RISTRETTI`, `E_PROMO_SCADUTA_IMMUTABILE`) e droppa i
no-op in update. Il FE pero' ricalcola:

- scaduta;
- iniziata;
- min-date;
- campi editabili;
- validazione segno valore.

Il detail promo deve esporre:

```json
{
  "stato_temporale": "FUTURA|INIZIATA|SCADUTA",
  "non_editable_fields": ["codice", "articolo_id", "uom_id", "valido_dal", "attivo"],
  "can_update": true,
  "can_update_reason": null,
  "min_valido_dal": "2026-04-29",
  "min_valido_al": "2026-04-28",
  "tipo_variazione_options": [...]
}
```

Il FE mostra banner e disabilita campi in base a questi metadata. La guard
backend resta l'unica difesa reale.

### A7. Enum `tipo_variazione` promo e contratti/listini da lookup tecnico

- `frontend/src/vendite/components/PromoArticoloDrawer.vue:91`
- `frontend/src/vendite/components/ContrattoDrawer.vue:92`

`PERCENTUALE`, `VALORE_FISSO`, `PREZZO_FISSO` non devono essere ripetuti nei
componenti. Come indicato nell'analisi catalogo per `roundingOptions`, non serve
per forza una tabella DB: basta un endpoint lookup statico che legge la
whitelist Python/DB single source of truth.

Endpoint proposti:

- `GET /api/v1/vendite/lookup/tipi-variazione-contratto/`
- `GET /api/v1/vendite/lookup/tipi-variazione-promo/`
- `GET /api/v1/vendite/lookup/ambiti-contratto/`

### A8. Defaults e vincoli versioni listino da backend

- `frontend/src/vendite/components/VersioneFormDrawer.vue:34`
- `frontend/src/vendite/components/CloneVersioneDrawer.vue:150`
- `frontend/src/vendite/components/ChiudiVersioneDialog.vue` (default chiusura oggi)

Oggi il FE decide:

- nuova versione: `valido_dal = oggi`;
- clone versione: `valido_dal = domani`;
- codice clone: suffisso `-clone`;
- chiusura versione: default oggi;
- retroattivo: warning se `valido_dal < oggi`.

Alcuni sono suggerimenti UX, ma devono essere metadata del comando:

```text
GET /api/v1/vendite/listini/{id}/versioni/form-defaults/
GET /api/v1/vendite/listini/{id}/versioni/{ver_id}/clone-defaults/
GET /api/v1/vendite/listini/{id}/versioni/{ver_id}/close-defaults/
```

Campi:

- `default_codice_versione`
- `default_valido_dal`
- `min_valido_dal`
- `default_valido_al`
- `min_valido_al`
- `has_existing_draft`
- `existing_drafts`
- `retroactive_warning`

### A9. `can_delete`/`can_edit` per righe listino e versioni

- `frontend/src/vendite/components/VersioneDrawer.vue:116`
- `frontend/src/vendite/components/VersioneDrawer.vue:224`

Il FE decide che solo `BOZZA` abilita modifica/eliminazione righe. Corretto, ma
va esposto dal backend per ogni versione/riga:

- `versione.can_add_righe`
- `versione.can_apply_variazione`
- `riga.can_edit`
- `riga.can_delete`
- `riga.action_reason`

Il pattern e' lo stesso gia' proposto per catalogo: capability di riga invece
di `if (stato === 'BOZZA')`.

### A10. Preventivi: form testata usa ID numerico per billing account

- `frontend/src/vendite/preventivi/components/PreventiviForm.vue:28`

Il form preventivo usa `InputNumber` per `billing_account_id`, mentre contratti
usa `BillingAccountLookup`. Non e' solo UX: un ID manuale permette combinazioni
incoerenti con utility/istanza/emittente finche' il backend non rifiuta.

Refactor:

- usare `BillingAccountLookup`;
- quando selezionato, popolare `billing_account_id`, `utility_id`,
  `istanza_utility_id`;
- idealmente chiedere al backend `preventivi/form-defaults/?billing_account_id=...`
  per valuta, termini pagamento, validita e competenza.

### A11. Preventivi: `LookupSelect` usato senza import (BUG P0)

- `frontend/src/vendite/preventivi/components/PreventiviForm.vue:55`
- `frontend/src/vendite/preventivi/components/PreventiviForm.vue:63`

Il template usa `LookupSelect`, ma lo script importa solo
`UtilityPerRuoloSelect`, `DatePicker`, `InputNumber`, `ToggleSwitch`. Se
`LookupSelect` non e' registrato globalmente da qualche plugin, questo rompe la
pagina preventivi.

Fix immediato:

```js
import LookupSelect from '../../../core/components/LookupSelect.vue'
```

Questo va fatto prima dei refactor piu' ampi.

---

## B. Casi controversi o UX legittima

### B1. Readonly per stato post-DRAFT contratto

- `frontend/src/vendite/components/ContrattoDrawer.vue:58`
- `frontend/src/vendite/components/ContrattoDrawer.vue:250`

La whitelist PATCH e il readonly post-DRAFT sono duplicati, ma intenzionali:
il backend rifiuta comunque, il FE evita round-trip e protegge l'operatore. Non
va rimosso. Va pero' sostituito progressivamente con `non_editable_fields` e
`available_actions` dal detail.

### B2. Preview righe contratto A/B lato backend, filtro articolo lato client

- `frontend/src/vendite/components/ContrattoRigheDrawer.vue:58`
- `frontend/src/vendite/components/ContrattoRigheDrawer.vue:76`

La preview combinata listino + override arriva dal backend; il FE filtra solo
codice/descrizione localmente. Per MVP e liste sotto 100-200 righe e' lecito.
Se i listini diventano massivi, spostare il filtro server-side su
`fetchRighePreview(search=...)`.

### B3. Reset valore variazione quando cambia tipo promo

- `frontend/src/vendite/components/PromoArticoloDrawer.vue:210`

E' UX corretta: il numero cambia semantica tra percentuale, valore fisso e
prezzo fisso. Non e' logica business primaria, e' prevenzione errore. Resta
valida anche quando gli enum arriveranno da lookup.

### B4. UoM operative caricate dall'articolo

- `frontend/src/vendite/components/PromoArticoloDrawer.vue:137`
- `frontend/src/vendite/components/VersioneDrawer.vue:75`
- `frontend/src/vendite/components/ContrattoRigheDrawer.vue:151`

Non e' violazione DB-first: il FE non decide quali UoM sono valide, chiede al
catalogo. Il problema e' duplicazione tecnica. Si puo' estrarre un composable:

```js
useArticoloUomOptions({ preselectBase: true })
```

### B5. Limiti pricing in `useLimitiPricing`

Il composable carica `max_sconto_pct` e `max_maggiorazione_pct` dal backend.
E' corretto: il FE mostra hint e intercetta errori per banner, ma non decide
l'autorizzazione finale. Evitare pero' di usare quei limiti come unica guard di
salvataggio.

### B6. Approvazioni prezzo: command UI semplice

`ApprovazioniPrezzoListView.vue` chiama endpoint command `approva`/`rifiuta`.
Questo e' il pattern corretto. Miglioramento: ogni item coda dovrebbe includere
`can_approve`, `can_reject`, `action_reason`, non farlo derivare solo dal fatto
che la pratica e' nella lista.

---

## C. Bug logici e debito di modello

### C1. Preventivi non allineati agli standard lista/drawer

`PreventiviRigheTable.vue` usa un dialog interno per la riga, azioni inline
manuali e tabella con scroll fisso; il resto vendite usa drawer/master-detail e
`RowActionsMenu`.

Non e' un bug funzionale, ma e' una deviazione dallo standard frontend:

- sostituire bottoni inline con `RowActionsMenu`;
- valutare master-detail inline come `VersioneDrawer` e `ContrattoRigheDrawer`;
- evitare `InputNumber` per FK;
- introdurre `BillingAccountLookup` e `ArticoloLookup` coerenti.

### C2. Detail preventivo carica righe ma il FE le ricarica da endpoint separato

`get_preventivo()` backend ritorna testata + righe + indirizzi, ma
`PreventiviRigheTable` richiama `listRighe(preventivoId)`. Questo non e'
necessariamente sbagliato, ma duplica round-trip e puo' creare mismatch
temporaneo tra totali detail e righe visualizzate.

Decisione consigliata:

- o il detail e' completo e i figli ricevono righe/indirizzi come props;
- o il detail e' solo testata e ogni sezione e' endpoint autonomo.

Per vendite, dove le righe sono mutate spesso e i totali sono trigger-driven,
preferisco endpoint autonomi ma allora il detail non dovrebbe includere righe
pesanti, oppure deve includere `summary`/totali soltanto.

### C3. Capability cross-sottodominio non modellate

Esempi:

- preventivo accettato ma gia' pushato in commessa;
- riga preventivo con approvazione prezzo pendente;
- listino con versione attiva e fatture gia' generate;
- contratto attivo con cessazione programmata;
- promo iniziata con righe commessa gia' snapshottate.

Questi casi non si risolvono con `stato === X` nel FE. Serve un pattern unico
di capability:

```json
{
  "capabilities": {
    "edit": {"allowed": false, "reason": "..."},
    "delete": {"allowed": false, "reason": "..."},
    "change_state": {"allowed": true, "targets": [...]},
    "push": {"allowed": false, "reason": "..."}
  }
}
```

### C4. Errori L2/L3 pricing devono diventare feedback guidato

Il backend ha workflow L2 limiti prezzo e L3 approvazione prezzo. Il FE deve
evitare due derive:

- bloccare a priori con regole locali non aggiornate;
- mostrare solo toast generico su errore strutturato.

Pattern consigliato:

- se backend ritorna `E_PREV_OVERRIDE_NON_AUTORIZZATO`, il form riga mostra
  CTA "Richiedi approvazione";
- il payload invia `richiesta_approvazione=true`;
- dopo salvataggio la riga mostra badge `PENDING`, gia' presente nella tabella.

---

## Piano refactor concentrico

### Fase 0 — Fix P0 e sicurezza build

1. Importare `LookupSelect` in `PreventiviForm.vue`.
2. Eseguire build frontend.
3. Verificare pagina preventivi create/edit.

### Fase 1 — Metadata read-only/capability senza cambiare UX

Backend:

- aggiungere `available_actions`, `non_editable_fields`, `can_*` nei detail di:
  preventivi, contratti, promo, versioni listino;
- aggiungere reason testuali/codici (`*_reason_code`) non solo boolean.

Frontend:

- consumare metadata mantenendo gli stessi componenti;
- lasciare temporaneamente fallback locale per compatibilita'.

### Fase 2 — Form defaults e lookup tecnici

Backend:

- `vendite/contratti/form-defaults/`
- `vendite/preventivi/form-defaults/`
- `vendite/listini/.../versioni/*-defaults/`
- lookup tecnici per enum variazione, ambiti, modalita pricing.

Frontend:

- rimuovere `new Date()` e magic string dai default form dove il valore e'
  operativo;
- conservare solo suggerimenti visuali non vincolanti.

### Fase 3 — Preventivi UI allineata agli standard

1. `BillingAccountLookup` al posto di `InputNumber`.
2. `RowActionsMenu` nelle righe.
3. Gestione riga coerente con master-detail vendite oppure dialog standardizzato.
4. CTA approvazione prezzo guidata da error code backend.

### Fase 4 — Duplicazioni tecniche

1. Estrarre `useArticoloUomOptions`.
2. Estrarre helper `useTemporalCapabilities` solo come adapter metadata, non
   per ricalcolare regole.
3. Uniformare `formatCurrency` e `formatNumber` usando utility core.

---

## Decisioni da non invertire

- Il backend/DB resta fonte unica per pricing, stati, workflow, validita e
  autorizzazioni.
- Il frontend puo' fare defense-in-depth, ma solo leggendo metadata backend o
  replicando temporaneamente con commento esplicito e test.
- Le azioni di stato devono essere command endpoint, mai PATCH generico.
- Date e default operativi non vanno inventati nel componente.
- I componenti vendite devono convergere sugli standard esistenti:
  `NewButton`, `RowActionsMenu`, `DrawerFooter`, `useSearchTable`,
  `BillingAccountLookup`, `ArticoloLookup`, `LookupSelect`.
