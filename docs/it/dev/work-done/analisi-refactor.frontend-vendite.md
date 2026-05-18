# Analisi refactor frontend vendite

<!-- markdownlint-disable MD036 MD031 MD028 -->

> **Stato: CHIUSO (2026-05-01)** — Fasi 0+1+2+3+4+5 tutte landed end-to-end
> DB+BE+FE. Documento spostato da `work-in-progress/` a `work-done/` come
> riferimento storico. Per il piano dettagliato di ogni fase + step landed,
> vedi le tabelle "Piano di aggiornamento" in coda al documento (✅ LANDED su
> ogni step).
>
> Output prodotti durante il refactor (riferimenti operativi):
>
> - API doc: `api_vendite_lookups.md` (Fase 2 lookup statici),
>   `api_vendite_form_defaults.md` (Fase 2.B3-B5),
>   `api_preventivi.md` (Fase 1+3+5 capabilities + retryable),
>   `api_approvazioni_prezzo.md` (Fase 5.B1 capability per item)
> - Composable FE: `useArticoloUomOptions`, `useEntityCapabilities` (Fase 4)
> - Service BE: `vendite_lookups_service`, `vendite_form_defaults_service`
> - Modello: 1406 test BE verdi, vite build verde
>
> Obiettivo originale: identificare cosa nel frontend vendite e' logica di dominio
> mascherata da presentazione, cosa e' UX defense-in-depth legittima e cosa
> richiede un contratto API piu' ricco.
>
> L'area vendite e' piu' articolata delle altre: non e' una singola CRUD area,
> ma un insieme di sottodomini collegati da pricing, stati documento,
> validita' temporale e integrazioni operative.
>
> Riferimenti vincolanti:
>
> - `docs/it/dev/api.md` — envelope API, command/read, errori strutturati,
>   grammatica URL, base view, `handle_post_json`, lookup generico/dedicato,
>   `core/parameters/defaults/`.
> - `docs/it/dev/frontend/frontend-standards.md` — pattern lista/drawer,
>   readonly, RowActionsMenu, i18n, transizione a stato terminale con data.
> - `docs/it/dev/backend/catalogo-building-block-backend.md` — inventario
>   building block backend (PayloadValidator, ParameterService,
>   PricingService, BillingAccountRepository, helpers API).
> - `docs/it/dev/frontend/catalogo-building-block-frontend.md` — inventario
>   building block frontend (`useGlobalLookup`, `useParameterDefaults`,
>   `BillingAccountLookup`, `LookupSelect`, `RoundingModeSelect`,
>   `ArticoloLookup`, `RowActionsMenu`).
> - `docs/it/dev/work-done/frontend/guida-sviluppo-frontend.md` — convenzioni
>   Vue, store, API client.
> - `docs/it/dev/work-done/analisi-refactor.frontend-catalogo.md` — pattern
>   condivisi per defaults, metadata API, capability di riga (Fasi 1-5
>   already-landed catalogo).
> - `docs/it/dev/work-done/analisi-refactor.frontend-anagrafiche.md` —
>   pattern `non_editable_fields`, `evento_stato_corrente`,
>   `classify EMPTY/PARTIAL/VALID`.
>
> Principio: il frontend vendite deve restare presentazione + UX. Il DB/backend
> decidono pricing, stati, transizioni, capability, campi editabili, default
> operativi e invarianti temporali.

> **Validazione 2026-04-28** — Il documento e' stato riallineato dopo
> verifica diretta del codice (`backend/apps/vendite/`, `frontend/src/vendite/`)
> e dei building block esistenti. Punti chiave:
>
> - i bug e le diagnosi sono confermati (P0 `LookupSelect`, modalita' A/B/C
>   FE-only, transizioni cablate, defaults `new Date()` cablati);
> - alcune proposte sono state riallineate ai pattern gia' consolidati nel
>   progetto (lookup statico tipo `RoundingModeSelect` invece di endpoint
>   dedicati ad-hoc; building block `BillingAccountLookup` gia' presente in
>   `core/components`; uso di `useParameterDefaults` + `core/parameters/defaults/`
>   per la quota di defaults non dipendenti dal BA);
> - il piano e' stato riscritto in chiave DB / Backend / Frontend in coda al
>   documento, con dipendenze esplicite tra livelli.

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

- `frontend/src/vendite/preventivi/components/PreventiviDrawer.vue:144-158`

Il FE decide il workflow nella funzione `transizioni()`:

- `BOZZA (DRAFT) -> EMESSO | ANNULLATO`
- `EMESSO -> ACCETTATO | RIFIUTATO | ANNULLATO`
- `ACCETTATO -> ANNULLATO`

Inoltre il bottone "Nuova revisione" appare solo per `EMESSO`/`ACCETTATO` —
anche questa e' una capability che dipende dallo stato del documento e non
dovrebbe essere derivata in Vue.

Questa e' logica di dominio. Il backend ha gia' `cambia_stato` delegato alla
funzione DB (`POST /api/v1/vendite/preventivi/<id>/stato/`,
`ApiPreventivoStato`) e il service conosce gli stati modificabili/fatturabili.
Il detail preventivo (`GET /api/v1/vendite/preventivi/<id>/`) deve esporre:

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

- `frontend/src/vendite/components/ContrattoDrawer.vue:376-408`

La whitelist `statiTransizionabili` (DRAFT -> [ATTIVO]; ATTIVO -> [CESSATO];
altrimenti []) duplica `_CONTRATTO_PATCH_ALLOWED_BY_STATE` e la logica
`cambia_stato` del backend
([backend/apps/vendite/services/contratti_service.py:118-122](../../../../backend/apps/vendite/services/contratti_service.py#L118-L122)).
Lo stato terminale `CESSATO` segue il pattern "stato terminale con data"
(frontend-standards §"Transizione a stato terminale con data") — corretto come
UX, ma il dialog usa default locale.

Come per preventivi, il detail contratto deve esporre:

- `available_actions`
- `can_change_state`
- `state_action_requires_date`
- `default_action_date`  ← oggi (cessazione programmata serale)
- `min_action_date`      ← `valido_dal` del contratto

Il dialog di cessazione resta UX, ma data default e semantica programmata devono
essere metadata. Oggi `openCessaDialog()` usa `new Date()` come policy locale
e replica nel computed `cessazioneProgrammata` la regola "data >= oggi -> programmata"
che e' gia' lato backend (`cambia_stato`) e DB (trigger guard +
job notturno `fn_contratti_close_scadute`, vedi memoria progetto
contratti cessazione data-driven).

### A5. Defaults contratto da form-defaults backend

- `frontend/src/vendite/components/ContrattoDrawer.vue:102-125`

Nel `defaultForm()` sono cablati:

- `ambito: 'COMMODITY'`
- `valido_dal = new Date().toISOString().slice(0, 10)`
- `data = new Date().toISOString().slice(0, 10)`
- `modalita = 'A'`
- `tipo_variazione_globale = PERCENTUALE` quando si sceglie A (`onModalitaChange`)

Questi default non sono solo UI: determinano il comportamento commerciale.

Architettura proposta — due livelli, gia' supportati dai BB esistenti:

1. **Defaults non dipendenti dal BA** — esposti via parameters
   (`config.parameters`) e consumati con `useParameterDefaults` (gia' BB
   frontend) + `ParameterService.get_defaults` (gia' BB backend, endpoint
   `GET /api/v1/core/parameters/defaults/?codes=...`). Esempio:
   `VENDITE_CONTRATTO_DEFAULT_AMBITO`, `VENDITE_CONTRATTO_DEFAULT_MODALITA`.
2. **Defaults dipendenti dal BA** — endpoint dedicato che fa lookup contestuale:

```text
GET /api/v1/vendite/contratti/form-defaults/?billing_account_id=...
```

Payload minimo:

- `default_ambito`
- `default_data`
- `default_valido_dal`
- `default_modalita_pricing`
- `default_tipo_variazione_globale`
- `categoria_cliente_snapshot_id`         ← gia' lookup oggi via `onBaSelected`
- `utility_tipo_classe_required`
- `pricing_modalita_options`              ← lookup statico (vedi A7)
- `valuta_id`, `termine_pagamento_id`     ← derivati dal BA quando esistono

Il payload create del FE continua a inviare i campi atomici come oggi; il
servizio si limita a "suggerire" i default. La differenza e' che il FE non
inventa piu' la regola "modalita=A se listino_id valorizzato" (vedi A3).

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

### A7. Enum `tipo_variazione` promo e contratti/listini da lookup statico

- `frontend/src/vendite/components/PromoArticoloDrawer.vue:91-95`
- `frontend/src/vendite/components/ContrattoDrawer.vue:92-100`

`PERCENTUALE`, `VALORE_FISSO`, `PREZZO_FISSO`, `COMMODITY`, `COMMERCIO`,
`A`/`B`/`C` non devono essere ripetuti nei componenti. Pattern gia' consolidato
(refactor catalogo Fase 1 LANDED): **endpoint lookup statico dedicato + wrapper
Vue + cache modulo-level via `useGlobalLookup`**, single source of truth lato
Python/DB.

Riferimento implementativo da copiare 1:1:

- BE: `vendite_service._TIPI_VARIAZIONE_CONTRATTO`/`_TIPI_VARIAZIONE_PROMO`/`_AMBITI_CONTRATTO`/`_MODALITA_PRICING_CONTRATTO`
  (whitelist tuple), endpoint `GET /api/v1/vendite/lookup/<nome>/` che ritornano
  `[{codice, descrizione}]`. **Modello esistente**: `catalogo_service._ROUNDING_MODE_VALIDI`
  e `LookupUomRoundingModesView` (vedi
  [catalogo-building-block-frontend.md](../frontend/catalogo-building-block-frontend.md)
  riga `lookupUomRoundingModes`).
- FE: nuovi wrapper standardizzati (`TipoVariazioneSelect`, `AmbitoContrattoSelect`,
  `ModalitaPricingSelect`) basati su `useGlobalLookup` con chiavi stabili
  (`vendite.tipi_variazione_contratto`, ecc.). Modello: `RoundingModeSelect`.

Endpoint proposti (allineati alla grammatica `api.md`, "Lookup dedicato"):

- `GET /api/v1/vendite/lookup/tipi-variazione-contratto/`
- `GET /api/v1/vendite/lookup/tipi-variazione-promo/`
- `GET /api/v1/vendite/lookup/ambiti-contratto/`
- `GET /api/v1/vendite/lookup/modalita-pricing-contratto/`

> **Nota** — non e' il lookup generico `core/lookup/codici/?rel=...` perche'
> queste enum **non hanno tabella DB di backing** (vivono come whitelist
> Python/DB-side, validate da CHECK constraint o trigger). Il lookup generico
> e' riservato a tabelle config con struttura `id, codice, descrizione`.

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

- `frontend/src/vendite/preventivi/components/PreventiviForm.vue:28-32`

Il form preventivo usa `<InputNumber>` per `billing_account_id`, mentre
contratti usa `BillingAccountLookup` (gia' BB cross-dominio in
`core/components/`, scope emittente automatico, restore arricchito,
endpoint `GET /anagrafiche/billing-account/lookup/` gia' attivo). Non e'
solo UX: un ID manuale permette combinazioni incoerenti con
utility/istanza/emittente finche' il backend non rifiuta.

Refactor (zero sviluppo BE — il BB esiste gia'):

- importare `BillingAccountLookup` da `core/components/BillingAccountLookup.vue`;
- prop `utility-id` legata a `form.utility_id` quando valorizzato (filtra
  per coerenza utility/BA);
- nell'`@select`, popolare `billing_account_id`, `utility_id`,
  `istanza_utility_id` (e `categoria_cliente_id_snapshot` se serve, come gia'
  fa `ContrattoDrawer.onBaSelected`);
- in edit, restore arricchito via `getBillingAccountLookupById(id)` per
  inizializzare `_obj` (pattern restore AutoComplete server-side);
- per gli altri default (valuta, termini pagamento, validita', competenza)
  usare `useParameterDefaults` + `core/parameters/defaults/` con codici
  `VENDITE_PREVENTIVO_DEFAULT_*` (vedi A5); per defaults derivati dal BA,
  endpoint dedicato `vendite/preventivi/form-defaults/?billing_account_id=...`.

### A11. Preventivi: `LookupSelect` usato senza import (BUG P0)

- `frontend/src/vendite/preventivi/components/PreventiviForm.vue:55-65`

Il template usa `<LookupSelect rel="config.valute">` e `<LookupSelect
rel="config.termini_pagamento">`, ma lo script importa solo
`UtilityPerRuoloSelect`, `DatePicker`, `InputNumber`, `ToggleSwitch`.
Verifica eseguita 2026-04-28: `LookupSelect` **non** e' registrato
globalmente in [main.js](../../../../frontend/src/main.js) — il componente
non viene risolto al runtime di Vue 3 e l'autocompletamento sui campi
"Valuta" e "Termini pagamento" non funziona (warning console + dropdown
vuoto). Bug reale, non solo formale.

Fix immediato:

```js
import LookupSelect from '../../../core/components/LookupSelect.vue'
```

Questo va fatto prima dei refactor piu' ampi (Fase 0). Una volta importato,
i due lookup rispettano gia' il pattern api.md "Lookup generico" (whitelist
~45 tabelle config su `dbops_repository.py`) — `config.valute` e
`config.termini_pagamento` devono essere presenti nella whitelist; in caso
negativo aggiungerli (verificare prima di chiudere la Fase 0).

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

- `frontend/src/vendite/composables/useLimitiPricing.js`

Il composable carica i limiti pricing dal backend (`GET
/api/v1/vendite/pricing/limiti-utente/`). E' corretto: il FE mostra hint e
intercetta errori per banner, ma non decide l'autorizzazione finale —
quest'ultima resta lato BE (`PricingService` + workflow L2/L3, vedi C4) e
DB (CHECK + trigger su `preventivi_righe`).

Evitare di usare quei limiti come unica guard di salvataggio: il backend
deve sempre rifiutare i payload non autorizzati con codice errore strutturato
(`E_PRICING_OVERRIDE_NON_AUTORIZZATO`) e il FE intercetta il codice per offrire
la CTA "Richiedi approvazione" (vedi C4).

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

`get_preventivo()` backend
([backend/apps/vendite/services/preventivi_service.py:81-98](../../../../backend/apps/vendite/services/preventivi_service.py#L81-L98))
ritorna testata + righe + indirizzi, ma
[PreventiviRigheTable.vue:31-33](../../../../frontend/src/vendite/preventivi/components/PreventiviRigheTable.vue#L31-L33)
chiama comunque `store.loadRighe(preventivoId)` (che a sua volta chiama
`listRighe` -> `GET /api/v1/vendite/preventivi/<id>/righe/`). Verificato.
Questo non e' necessariamente sbagliato, ma duplica round-trip e puo' creare
mismatch temporaneo tra totali detail e righe visualizzate.

Decisione consigliata:

- o il detail e' completo e i figli ricevono righe/indirizzi come props;
- o il detail e' solo testata + `summary`/totali e ogni sezione e' endpoint
  autonomo.

Per vendite, dove le righe sono mutate spesso e i totali sono trigger-driven,
preferisco endpoint autonomi ma allora il detail non dovrebbe includere righe
pesanti, oppure deve includere `summary`/totali soltanto. Da decidere e
applicare uniformemente (preventivi e contratti — `ContrattoRigheDrawer` ha
gia' endpoint preview dedicato).

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

- se backend ritorna `E_PRICING_OVERRIDE_NON_AUTORIZZATO`, il form riga mostra
  CTA "Richiedi approvazione";
- il payload invia `richiesta_approvazione=true`;
- dopo salvataggio la riga mostra badge `PENDING`, gia' presente nella tabella.

---

## Decisioni da non invertire

- Il backend/DB resta fonte unica per pricing, stati, workflow, validita' e
  autorizzazioni.
- Il frontend puo' fare defense-in-depth, ma solo leggendo metadata backend o
  replicando temporaneamente con commento esplicito e test.
- Le azioni di stato devono essere command endpoint, mai PATCH generico.
- Date e default operativi non vanno inventati nel componente.
- I componenti vendite devono convergere sugli standard esistenti:
  `NewButton`, `RowActionsMenu`, `DrawerFooter`, `useSearchTable`,
  `BillingAccountLookup`, `ArticoloLookup`, `LookupSelect`,
  `useGlobalLookup`, `useParameterDefaults`.

---

## Piano di aggiornamento — DB / Backend / Frontend

> Il piano e' organizzato per livelli (DB -> Backend -> Frontend) con
> dipendenze esplicite. Le fasi seguono il modello concentrico (vedi
> `docs/it/sviluppo-concentrico.md`). Le azioni DB sono brief al team DB
> sul branch `dev/db-tid` (memoria progetto `feedback_db_actions_passaggio_team`):
> non vengono eseguite direttamente dall'agente backend.

### Fase 0 — Fix P0 e sicurezza build (FE-only, no BE/DB)

| # | Livello | Azione | Dipendenze |
| --- | --- | --- | --- |
| 0.1 | FE | Importare `LookupSelect` in `PreventiviForm.vue` | nessuna |
| 0.2 | FE | Verifica `vite build` verde | 0.1 |
| 0.3 | FE | Smoke test manuale lista + drawer create/edit preventivo | 0.2 |
| 0.4 | BE | Verificare whitelist lookup generico in `dbops_repository.py`: `config.valute` e `config.termini_pagamento` presenti; aggiungere se mancanti | nessuna |

Stato uscita Fase 0: pagina preventivi funzionante, niente regressioni
backend, nessuna modifica DB.

### Fase 1 — Metadata capability nel detail (foundation)

Obiettivo: esporre `available_actions` + `non_editable_fields` + `can_*`
nei detail dei 4 sottodomini, senza cambiare la UX. Pattern gia' validato
nel refactor catalogo (Fasi 6-8) e anagrafiche.

**DB**

| # | Azione | Note |
| --- | --- | --- |
| 1.D1 | Nessuna nuova DDL — derivare capability da stato + relazioni gia' in DB | I LEFT JOIN per "ha pratica APPROVAZIONE_PREZZO pendente", "ha commessa pushata", "ha fatture generate" sono gia' fattibili |
| 1.D2 | (opz.) Vista `vw_preventivi_detail_capability` se i JOIN diventano onerosi | brief team DB — solo se profiling richiede |

**Backend**

| # | File / Endpoint | Azione |
| --- | --- | --- |
| 1.B1 | `preventivi_service.get_preventivo` | Aggiungere blocco `capabilities` (testata) + `available_actions` derivate da `script.fn_can_change_state_preventivo` (o equivalente Python su stati). Rifattorizzare `transizioni()` esistente |
| 1.B2 | `contratti_service.get_contratto` | Stesso pattern; `available_actions` per CESSATO include `requires_date=true`, `default_date=today`, `min_date=valido_dal` |
| 1.B3 | `promo_articoli_service.get_promo_articolo` | Esporre `stato_temporale` (FUTURA/INIZIATA/SCADUTA), `non_editable_fields`, `min_valido_dal`, `min_valido_al` derivati dalla guard DB esistente (`E_PROMO_*`) |
| 1.B4 | `listini_service` versioni + righe | `versione.can_add_righe`, `versione.can_apply_variazione`, `riga.can_edit`, `riga.can_delete`, `riga.action_reason` (whitelist su stato BOZZA gia' implementata) |
| 1.B5 | `error_policies.py` | Registrare nuovi codici reason (`E_*_NON_EDITABILE`, `E_*_PUSH_GIA_FATTO`, ecc.) se non gia' presenti |
| 1.B6 | Test service in `apps/vendite/tests/services/` | Nuovi test per ogni capability — fallimenti devono restituire reason_code |

**Frontend**

| # | File | Azione |
| --- | --- | --- |
| 1.F1 | `PreventiviDrawer.vue` | Sostituire `transizioni()` con consumo di `detail.available_actions`; `isModificabile`/`isAccettato` -> `detail.capabilities.edit`/`push` |
| 1.F2 | `ContrattoDrawer.vue` | `statiTransizionabili` legge `detail.available_actions`; data dialog cessazione legge `default_date`/`min_date`/`requires_date` |
| 1.F3 | `PromoArticoloDrawer.vue` | `isPromoScaduta`/`isPromoIniziata`/`validoDalMinDate` legati a `detail.stato_temporale` + `min_valido_dal`; campi disabled da `non_editable_fields` |
| 1.F4 | `VersioneDrawer.vue` | `isBozza` -> `versione.can_add_righe`; `RowActionsMenu` per riga usa `riga.can_edit`/`can_delete` come `visible` |
| 1.F5 | (opz.) `core/composables/useEntityCapabilities.js` | Helper sottile che adatta `detail.capabilities` -> ref booleani per i computed dei drawer (no logica, solo lookup) |

Stato uscita Fase 1: zero ricalcoli di stato/permesso nei drawer Vue.
La UX visibile resta invariata. Test di regressione obbligatori.

### Fase 2 — Form defaults e lookup tecnici

Obiettivo: rimuovere `new Date()`, magic string e regole `if (modalita === 'A')`
dal FE, sostituendo con parameters + lookup statici (pattern `RoundingModeSelect`).

**DB**

| # | Azione | Note |
| --- | --- | --- |
| 2.D1 | Seed `config.parameters` per defaults non-BA | brief team DB. Codici: `VENDITE_PREVENTIVO_DEFAULT_VALIDITA_GG`, `VENDITE_CONTRATTO_DEFAULT_AMBITO`, `VENDITE_CONTRATTO_DEFAULT_MODALITA`, `VENDITE_LISTINI_NEW_VERSIONE_LEAD_GG`, `VENDITE_LISTINI_CLONE_VERSIONE_LEAD_GG`, ecc. |
| 2.D2 | (opz.) View per categoria_cliente_snapshot derivata dal BA | gia' fattibile da Python; non serve view dedicata salvo profiling |

**Backend**

| # | Azione | Note |
| --- | --- | --- |
| 2.B1 | `vendite_service` — whitelist Python per enum: `_TIPI_VARIAZIONE_CONTRATTO`, `_TIPI_VARIAZIONE_PROMO`, `_AMBITI_CONTRATTO`, `_MODALITA_PRICING_CONTRATTO` | Modello: `catalogo_service._ROUNDING_MODE_VALIDI` |
| 2.B2 | 4 endpoint `GET /api/v1/vendite/lookup/<nome>/` | Modello: `LookupUomRoundingModesView` — risposta `[{codice, descrizione}]`, area `vendite` LETTURA |
| 2.B3 ✅ LANDED 30-04 | `GET /api/v1/vendite/contratti/form-defaults/?billing_account_id=...` | Risolve categoria_cliente_id_snapshot, utility/istanza dal BA + default_data/default_valido_dal da parameter. `vendite_form_defaults_service.fn_get_contratto_form_defaults`. |
| 2.B4 ✅ LANDED 30-04 | `GET /api/v1/vendite/preventivi/form-defaults/?billing_account_id=...` | Valuta_id (BA o emittente fallback), termine_pagamento_id/iva_id/modalita_pagamento_id dal cliente del BA via tripletta UNIQUE. `default_validita_al` da parameter. `fn_get_preventivo_form_defaults`. |
| 2.B5a ✅ LANDED 30-04 | `GET /api/v1/vendite/listini/<id>/versioni/form-defaults/` | `default_codice_versione`, `default_valido_dal`, `has_existing_draft`, `existing_drafts`. `fn_get_versione_new_defaults`. |
| 2.B5b ✅ LANDED 30-04 | `GET /api/v1/vendite/listini/<id>/versioni/<ver_id>/clone-defaults/` | `default_codice_versione` (suffisso da parameter), `default_valido_dal`, `min_valido_dal`, `is_retroactive_default`. `fn_get_versione_clone_defaults`. |
| 2.B5c ✅ LANDED 30-04 | `GET /api/v1/vendite/listini/<id>/versioni/<ver_id>/close-defaults/` | `default_valido_al` (existing oppure oggi+lead), `current_valido_al`, `min_valido_al=oggi`. `fn_get_versione_close_defaults`. |
| 2.B6 | `error_policies.py` | Nuovi codici se mancanti |
| 2.B7 | Test service + smoke API | Coverage minima sui nuovi endpoint |

**Frontend**

| # | Azione | Note |
| --- | --- | --- |
| 2.F1 | `core/api/apiCore.js` o `vendite/api/lookup.js` | Aggiungere `lookupTipiVariazioneContratto`, `lookupTipiVariazionePromo`, `lookupAmbitiContratto`, `lookupModalitaPricingContratto` (lookup statici) |
| 2.F2 | Nuovi wrapper in `vendite/components/`: `TipoVariazioneSelect.vue`, `AmbitoContrattoSelect.vue`, `ModalitaPricingSelect.vue` | Modello `RoundingModeSelect.vue` con `useGlobalLookup(chiave-stabile, fetchFn)` |
| 2.F3 | `ContrattoDrawer.vue` | Sostituire `tipoVariazioneOptions`/`ambitoOptions`/`modalitaOptions` cablati con i wrapper |
| 2.F4 | `PromoArticoloDrawer.vue` | Sostituire `tipoVariazioneOptions` cablato con `TipoVariazioneSelect` |
| 2.F5 | `useParameterDefaults` consumer in `defaultForm()` di `ContrattoDrawer.vue`, `PreventiviDrawer.vue`, `VersioneFormDrawer.vue`, `CloneVersioneDrawer.vue`, `ChiudiVersioneDialog.vue` | Codici parameters da Fase 2.D1 |
| 2.F6 ✅ LANDED 30-04 | Endpoint form-defaults integrati: `PreventiviDrawer` watcher su `form.billing_account_id` chiama `getPreventivoFormDefaults` e popola valuta/termini se vuoti; `VersioneFormDrawer`/`CloneVersioneDrawer`/`ChiudiVersioneDialog` sostituiscono `useParameterDefaults` con i nuovi `getVersione*Defaults` (BE risolve codice clone+suffisso, existing_drafts, default_valido_al). `ContrattoDrawer` rimanda l'integrazione: l'attuale `onBaSelected` legge gia' i campi dal lookup BA che sono allineati al payload BE | A5/A8 |
| 2.F7 ✅ LANDED 30-04 | Magic string `'-clone'`/`'COMMODITY'`/`'A'`/`'PERCENTUALE'` rimosse dai `defaultForm()` (Fase 2.F5 originale + 2.F6 per i drawer versioni). I drawer versioni leggono i defaults dal BE; i restanti drawer (Contratto/Preventivo) usano `useParameterDefaults` come fallback dopo BE-failure | Solo dopo che 2.F5/2.F6 sono attivi |

Stato uscita Fase 2: nessun enum di dominio cablato lato FE; nessun
`new Date()` operativo nei `defaultForm()`. La whitelist enum vive in
un solo posto (Python) e arriva al FE via API.

### Fase 3 — Preventivi UI allineata agli standard

Obiettivo: chiudere il debito stile sul sottodominio piu' acerbo.

**DB / Backend**: nessuna nuova azione richiesta (si appoggia a Fase 1+2).

**Frontend**

| # | Azione | Note |
| --- | --- | --- |
| 3.F1 | `PreventiviForm.vue` — `BillingAccountLookup` al posto di `InputNumber` | A10. BB gia' esistente, prop `utility-id`, restore via `getBillingAccountLookupById` |
| 3.F2 | `PreventiviRigheTable.vue` — sostituire bottoni inline con `RowActionsMenu` (kebab + popup) e azioni `visible` da capability di riga | C1 + frontend-standards §"Colonna azioni di riga" |
| 3.F3 | `PreventiviRigheTable.vue` — valutare master-detail inline al posto di Dialog interno (modello `VersioneDrawer`/`ContrattoRigheDrawer`) | Coerenza con il resto vendite |
| 3.F4 | CTA "Richiedi approvazione" in `PreventiviRigaForm.vue` quando l'errore backend e' `E_PRICING_OVERRIDE_NON_AUTORIZZATO` | C4 — payload riga aggiunge `richiesta_approvazione=true` |
| 3.F5 | Rimuovere `scrollHeight="250px"` cablato; allinearsi a `app-datatable` standard | Tipografia/scroll consistenti |
| 3.F6 | Decisione C2: detail = testata + summary, righe via endpoint autonomo (oppure detail include righe e i figli leggono props). Applicare uniformemente | Una sola scelta, documentata |

Stato uscita Fase 3: preventivi indistinguibili come UX dal resto vendite.

### Fase 4 — Duplicazioni tecniche e composables

Obiettivo: estrarre i pattern tecnici ricorrenti.

**Frontend**

| # | Azione | Note |
| --- | --- | --- |
| 4.F1 | `core/composables/useArticoloUomOptions.js` | Centralizza fetch UoM operative + preselect base. Consumer: `PromoArticoloDrawer`, `VersioneDrawer`, `ContrattoRigheDrawer` |
| 4.F2 | `core/composables/useEntityCapabilities.js` | Adapter sottile metadata `detail.capabilities` -> booleani; mai logica derivata. Da Fase 1 |
| 4.F3 | `core/utils/format.js` (o existing) | `formatCurrency`/`formatNumber` unica utility, rimpiazzare le copie locali in `PreventiviDrawer`, `PreventiviRigheTable`, `ContrattoDrawer` |
| 4.F4 | (opz.) `core/composables/useStatoTerminaleConData.js` | Genera `cessazioneProgrammata`/`openCessaDialog`/`onConferma` come hook unico; consumer: ContrattoDrawer, ChiudiVersioneDialog |

**Backend / DB**: nessuna azione.

Stato uscita Fase 4: i pattern tecnici condivisi sono in un solo posto.

### Fase 5 — Diagnostica pricing e approvazioni

Obiettivo: chiudere C3/C4 in modo strutturato.

**Backend**

| # | Azione |
| --- | --- |
| 5.B1 | Lista coda approvazioni espone per ogni item: `can_approve`, `can_reject`, `action_reason` (oggi: derivati da `lista_coda` ma non esposti). |
| 5.B2 | Errore `E_PRICING_OVERRIDE_NON_AUTORIZZATO` mantiene `retryable=true` quando l'utente puo' chiedere approvazione, `retryable=false` quando il limite e' invalicabile per ruolo |

**Frontend**

| # | Azione |
| --- | --- |
| 5.F1 | `ApprovazioniPrezzoListView.vue` — bottoni Approva/Rifiuta legati a capability per riga |
| 5.F2 | `TestResolverDialog.vue` — isolarlo come strumento diagnostico (no consumo nelle pagine operative); spostarlo in vista admin/debug |

---

## Riepilogo dipendenze

```text
Fase 0 (P0 + whitelist lookup)
   |
   v
Fase 1 (capability metadata) — DB (eventuale view) -> BE (detail) -> FE (consumo)
   |
   v
Fase 2 (defaults + lookup statici) — DB (parameters seed) -> BE (endpoint) -> FE (wrapper + consumo)
   |
   v
Fase 3 (preventivi standard) — solo FE; richiede Fase 1 (capability) + Fase 2 (lookup BA)
   |
   v
Fase 4 (composables condivisi) — solo FE; richiede Fase 1+3
   |
   v
Fase 5 (approvazioni/diagnostica) — BE + FE; indipendente dalle altre, ma piu' utile dopo Fase 1
```

Il modello e' compatibile con il principio "no produzione, breaking ammessi"
(memoria progetto `project_no_produzione_solo_sviluppo`): non servono
fasi di compat o feature flag.
