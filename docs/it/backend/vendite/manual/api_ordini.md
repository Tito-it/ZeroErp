# API Ordini di vendita `vendite.ordini`

## Scopo

CRUD operativo (scheletro) degli **ordini di vendita**, documento del ciclo
attivo che raccoglie le righe articolo da evadere/fatturare. Espone testata,
**righe** con **componenti BoM** (modello unificato), **conferma**
(`DRAFT -> CONFERMATO`) e **push singolo a commessa** (chiusura del giro
ordine → attività fatturabili → pipeline lotto → fattura), oltre a **lista
configurabile DEF-8** + export e **note partizionate**.

Clone strutturale della famiglia vendite (preventivi/offerte) — regola del 2:
pricing via `PricingService`, componenti via `fn_ordine_riga_componenti_*`,
note via `PartitionedNoteRepository`, lista/export via `ListaExportService`.
Rispetto a preventivi/offerte l'ordine **non ha revisioni** né listino in testata.

> Stato: **scheletro BE** (analisi
> [analisi-ordini-vendita.md](../../../dev/work-done/analisi-ordini-vendita.md)
> §5) + stampa PDF (§Documenti) + **conversione preventivo/offerta→ordine**
> (2026-06-04, endpoint `genera-ordine` sui domini upstream — valorizza
> `documento_origine` A1). Fulfillment/DDT: vedi [api_ddt.md](api_ddt.md) (evasione `genera-ddt`). Indirizzi documento: vedi [api_indirizzi_documento.md](api_indirizzi_documento.md).

### Modello

- **Identità**: `(anno, serie, numero)` + `uid`. Il `numero` è generato dal
  trigger `trgfn_ordini_gen_numero` (BEFORE INSERT) via
  `script.fn_generate_codice('ordine')` — **valorizzato già in BOZZA**, immutabile
  dopo (lock colonne). Il campo `numero` **non va nel payload**.
- **Stato iniziale** `DRAFT` (risolto dal service via
  `config.stati_doc_ordini.codice_interno`).
- **`fatturazione_trigger`** (`CONFERMATO` | `SPEDITO` | `CONSEGNATO`): governa
  *quando* l'ordine pusha a commessa. Default ereditato da
  `billing_account.fatturazione_ordini` (trigger `trgfn_ordini_normalize`);
  sovrascrivibile sul payload.
- **`canale_origine`** (`ADMIN` | `PORTALE` | `SHOP`): immutabile post-INSERT; in
  back-office sempre `ADMIN`.
- **Estensioni modello 2026-06-03**: **agente** (`agente_soggetto_ruolo_id`,
  nullable) ed **origine documento** (A1: `documento_origine_tipo` ∈
  {`PREVENTIVO`,`OFFERTA_COMMERCIALE`} + `documento_origine_id`; FK verso
  `config.sorgenti` dal 2026-10-19, brief-db-grammatica-unica-documenti lotto 2b). Valorizzate dalla
  **conversione upstream** (fatte 2026-06-04): `documento_origine = ('PREVENTIVO',
  id)` da `ordini_service.crea_ordine_da_preventivo` (copia 1:1 righe piatte) e
  `('OFFERTA_COMMERCIALE', id)` dal verbo DB `vendite.fn_genera_ordine_da_offerta`
  (dal 2026-10-21, via `crea_ordine_da_offerta`: righe espanse di
  `fn_offerta_righe_espanse`, prezzi negoziati preservati). **Univocità (rev.
  2026-06-07)**: per `OFFERTA_COMMERCIALE` vale **1:1** — un'offerta genera al massimo un
  ordine (UNIQUE parziale `uq_ordini_v_documento_origine_offerta` + guard BE
  `E_ORD_OFFERTA_GIA_CONVERTITA`, **reversal parziale di A1** «senza UNIQUE»);
  `PREVENTIVO` resta **1:N** (split per riga, nessun vincolo). Endpoint sui domini
  upstream (vedi [api_preventivi.md §6c](api_preventivi.md) e api_offerte). La
  CREATE diretta lascia le colonne NULL.
- **Pagamento/valuta**: `modalita_pagamento_id`, `termine_pagamento_id`,
  `valuta_id`, `tasso_cambio` (default 1). `giorni_pagamento`/`fine_mese` e i
  campi trasporto **non sono in testata** (droppati `20251027-01`; vivono su
  BA / DDT a valle).

### State machine

| Da    | A          | Chi la innesca         | Effetto                                                           |
| ----- | ---------- | ---------------------- | ----------------------------------------------------------------- |
| DRAFT | CONFERMATO | operatore (`/emetti/`) | Abilita il push a commessa (se `fatturazione_trigger=CONFERMATO`) |

La transizione si innesca **solo** da `/emetti/` (conferma + generazione
documento, vedi sezione Emetti): la conferma senza PDF (`POST /<id>/conferma/`) è
ritirata dal 2026-10-25 (M-2 e Z-2 di
[brief-modello-documento-vendita](../../../dev/work-in-progress/brief-modello-documento-vendita.md) §9).
Lo stato lo scrive il verbo `vendite.fn_cambia_stato_ordine` (un UPDATE diretto
della colonna lo rifiuta la porta, `E_DOC_STATO_SOLO_DAL_VERBO`), e la
transizione è **autoritativa lato DB** (trigger `trgfn_ordini_guard_transizione`; dal
2026-09-24 la sua Regola 5 rifiuta `DRAFT → CONFERMATO` con componenti BoM attivi
a prezzo `PENDING` o `REJECTED` — `E_DOC_PREZZO_PENDENTE` / `E_DOC_PREZZO_RIFIUTATO`,
building block `script.fn_check_prezzi_autorizzati`): il service legge solo lo stato
corrente (404 / «origine DRAFT»), le righe le conta il guard
(`E_ORDINE_CONFERMA_SENZA_RIGHE`; il fail-fast `E_ORD_NESSUNA_RIGA` della conferma è
ritirato, era la sua copia). I codici `E_ORDINE_*` sollevati dai trigger sono
**estratti dal MESSAGE** via regex (`_DB_ERROR_CODE_RE`) e propagati come
`ServiceError.code` originale (routing UI specifico), con fallback
`E_VENDITE_VALIDATION`.

## Input

Tutti gli endpoint sotto `DomainAPIView` (`area_funzionale='vendite'`, JWT +
`ZeroERPPermission`). Liste/export con `is_search_endpoint=True`.

### Lista ordini `GET /api/v1/vendite/ordini/`

Lista paginata dalla vista canonica `vendite.vw_ordini_lista` (DEF-8, lista
configurabile `vendite.ordini`). Scope emittente automatico (RLS +
`fn_get_emittenti_scope_pk_ids` su `emittente_fiscale_id`).

| Query param | Tipo | Note |
| --- | --- | --- |
| `search` | str | min 3 char; ILIKE su `numero`, `ragione_sociale_completa`, `ba_codice`, `id_fiscale_univoco_cf_piva` |
| `stato_codice_interno` | str | `codice_interno` stato (`DRAFT` \| `CONFERMATO` \| …). Fuori vocabolario `config.stati_doc_ordini` → 400 `E_ORD_VALIDAZIONE` col campo (2026-10-20: prima lista vuota con 200) |
| `billing_account_id` | int | cliente |
| `utility_id` | int | |
| `data_da` / `data_a` | str ISO | filtro su `data` (default lato UI, non backend) |
| `order_by` | str | whitelist: `numero` \| `anno` \| `serie` \| `data` \| `ragione_sociale_completa` \| `ba_codice` \| `id_fiscale_univoco_cf_piva` \| `utility_codice` \| `utility_descrizione` \| `totale_doc` \| `imponibile_tot` \| `iva_tot` \| `fatturazione_trigger` \| `stato_descrizione` \| `data_insert` \| `pratica_numero` \| `fase`. Default `data` |
| `order_dir` | str | `asc` \| `desc`; assente: `desc` sul default `data` («dal più recente», 2026-10-20: prima la view lo perdeva e l'elenco partiva crescente), `asc` sulle altre colonne. Tiebreaker `id` |
| `limit` / `offset` | int | paginazione (limit cap 200) |

### Export lista `GET /api/v1/vendite/ordini/export/?formato=csv|xlsx`

Export DEF-1: stessi filtri della lista, `ListaExportService` + catalogo colonne
`vendite.ordini` (ordine/visibilità/permessi utente rispettati). Cap
`EXPORT_MAX_ROWS`. Parametro **`formato`** (italiano), MAI `format`.
Errori: `E_UI_EXPORT_FORMAT_INVALID` (400), `E_UI_EXPORT_LIMIT_EXCEEDED` (422).

### Form-defaults `GET /api/v1/vendite/ordini/form-defaults/?billing_account_id=<id>`

Sola lettura, per precompilare il drawer di creazione (permesso modello
`("vendite", "ordine")`). Senza `billing_account_id` torna solo la valuta (catena
EF utente → gestore globale, BB `resolve_valuta_default`); con il BA aggiunge
utility e i default di pagamento dell'anagrafica cliente del BA.

```json
{"data": {
  "billing_account_id": 100, "utility_id": 3, "istanza_utility_id": 200,
  "utility_codice": "GAS", "utility_descrizione": "Gas",
  "valuta_id": 1, "valuta_codice": "EUR", "valuta_descrizione": "Euro",
  "termine_pagamento_id": 4, "termine_pagamento_codice": "30GG", "termine_pagamento_descrizione": "...",
  "modalita_pagamento_id": 2, "modalita_pagamento_codice": "BON", "modalita_pagamento_descrizione": "..."
}}
```

La utility di default globale (`DEFAULT_UTILITY`) la risolve il frontend. BA
inesistente → 404 `E_VENDITE_NOT_FOUND`.

### Create testata `POST /api/v1/vendite/ordini/`

Crea un ordine in `DRAFT`. `handle_post_json`.

| Campo | Tipo | Note |
| --- | --- | --- |
| `billing_account_id` | int | cliente, **obbligatorio** (D-1 di brief-db-esecutivi-ba-coppia). `soggetto_ruolo_id` e `utility_id` sono copie del BA: le scrive `trgfn_ordini_normalize` (BB `script.fn_cliente_dal_billing_account`) e non sono nel contratto: inviate sono un 400 |
| `emittente_fiscale_id` | int | opzionale; se omesso, trigger lo valorizza da GUC |
| `valuta_id`, `modalita_pagamento_id`, `termine_pagamento_id` | int | opzionali |
| `fatturazione_trigger` | str | opzionale; default ereditato da BA |
| `agente_soggetto_ruolo_id` | int | opzionale (E) |
| `data` | str ISO | opzionale (default `CURRENT_DATE`) |
| `fatturazione_immediata` | bool | opzionale: corsia di fatturazione decisa prima del push in commessa; dopo il push la rifiuta il guard DB `trgfn_guard_fatturazione_immediata_immutabile` |
| `meta` | obj | opzionale |

`numero`/`canale_origine`/`stato_doc_ordine_id` **non** vanno nel payload: una
chiave fuori contratto è un 400 `E_ORD_VALIDAZIONE` (2026-10-20: prima era
scartata in silenzio).
Ritorna `{id, uid, numero}`.

### Detail `GET /api/v1/vendite/ordini/<id>/`

Testata (dalla vista + `meta`/`storicizza`) + capability **data-driven** da
`script.fn_available_actions_ordine` (matrice `config.transizioni_stati_ordini`),
nella chiave `capabilities`, non fuse nella testata (dal 2026-09-23, [api.md §«Il blob sta SOTTO `capabilities`»](../../../dev/api.md)):
`available_actions[]` (azioni di stato con `key`/`target_state`/`label_key`/
`requires_confirm` — incl. `conferma`, `annulla`, e
`push_commessa` come azione applicativa; icona e colore li sceglie il frontend
dal `key`), `can_edit_testata`, `can_edit_righe`,
`can_push_commessa` (+ `can_push_commessa_reason`/`_reason_key`),
`non_editable_fields`, `stato_codice`, `pdf`; sulla testata `righe_count` e, dal 2026-10-20,
`documento_origine_etichetta` (il nome del tipo d'origine da `config.sorgenti.etichetta`, «Preventivo»,
«Offerta»; `null` senza origine). *(`can_conferma` non è
più un flag: la conferma è un'entry di `available_actions`.)* `contatori` (dal 2026-10-25): `{"note": <n>}`, il numero sul pulsante «Gestisci note» del drawer, dal BB `contatori_documento` — contato **dopo** il cancello di testata, con lo stesso perimetro della lista note. Forma e ragioni in [api_fattura_dettaglio §`contatori`](/backend/vendite/manual/api_fattura_dettaglio). 404
(`E_ORD_NOT_FOUND`) se inesistente o fuori scope (RLS).

### Ordine per pratica `GET /api/v1/vendite/ordini/per-pratica/?pratica_id=<id>`

Risolve l'ordine **COLLEGATO** a una pratica (`pratiche_sorgenti`, sorgente
`ORDINE_VENDITA`, ruolo `COLLEGATO` — aggancio fatto dal `PostSmistamentoHandler`
alla chiusura di SMISTAMENTO). Alimenta gli step a valle del percorso pratica
(`azione_ui` CONFERMA_ORDINE / INVIO_COMMESSA), che aprono l'`OrdiniDrawer` su
quell'ordine. Ritorna `{"ordine_id": <id|null>}` (`null` se nessun ordine
agganciato — preventivo tutto-servizi). `pratica_id` obbligatorio
(`E_PRATICA_ID_OBBLIGATORIO`). Lettura libera (area `vendite`). Se più ordini
(consegne parziali, 1:N) ritorna il più recente. Gemello di
`GET /vendite/preventivi/root-per-pratica/`.

### Riepilogo IVA `GET /api/v1/vendite/ordini/<id>/riepilogo-iva/`

Riepilogo IVA aggregato dell'ordine: **una riga per aliquota** con `imponibile`,
`imposta`, `arrotondamento`, `totale_riga` (più decodifiche `iva_codice`/
`iva_descrizione`/`iva_aliquota`; `natura_id`/`esigibilita`/`split_payment` sempre
`NULL` per gli ordini). Lettura pura dalla vista derivata
`vendite.vw_ordini_riepilogo_iva_dettaglio`: l'IVA è calcolata **per gruppo
aliquota** (`ROUND(SUM(imponibile_riga))`, poi imposta sul gruppo — regola DPR
633/72 art. 21 + DM 24/12/93, identica ai preventivi); nessun calcolo Python. La
vista riflette le righe attive correnti e i totali di testata (`*_tot`) sono
mantenuti coerenti dal trigger `fn_ricalcola_totali_ordine`. Ordinamento
`iva_aliquota NULLS LAST, iva_id NULLS LAST`. Prima la testata: ordine
inesistente o fuori perimetro → 404 `E_ORD_NOT_FOUND`, non una lista vuota. Usato dal pannello "Riepilogo IVA" del drawer e dal context builder PDF.

### Indirizzi documento `GET/POST /<id>/indirizzi/` + `DELETE /<id>/indirizzi/<iid>/`

BB condiviso sui 5 domini vendite (ambito `ORDINI`: CON, FATT; editabile solo
DRAFT): contratto completo in [api_indirizzi_documento.md](api_indirizzi_documento.md).

### Update testata `PATCH /api/v1/vendite/ordini/<id>/`

In bozza tutti i campi; quali colonne si cambiano fuori bozza lo dice il lock di testata del DB (`trgfn_doc_testata_lock_fuori_bozza`, dal 2026-10-10, [brief-db-testata-dopo-emissione](/dev/work-done/brief-db-testata-dopo-emissione)); il 409 del lock (`E_DOC_*`) passa com'e': dopo la conferma restano aperte le note, ferme a ordine fatturato o annullato. `corpo_oggetto(request)` (non `handle_post_json`, api.md). Campi
aggiornabili: `billing_account_id` (vedi sotto), `valuta_id`,
`modalita_pagamento_id`, `termine_pagamento_id`, `fatturazione_trigger`,
`agente_soggetto_ruolo_id`, `data`, `fatturazione_immediata`, `meta`. Una chiave
fuori elenco è un 400 `E_ORD_VALIDAZIONE` (2026-10-20: prima scartata); `{}` →
400. `utility_id` non c'e': e' una copia del BA, che sull'ordine non cambia.
Risposta: `{"ordine_id": <id>, "updated": true}`.

**Cliente immutabile post-creazione** (2026-06-04): un PATCH che **cambia**
`billing_account_id` è rifiutato con 409 `E_ORD_CLIENTE_IMMUTABILE`; lo stesso BA
reinviato **invariato** passa (il form FE lo può rimandare). Regola «cambiare
cliente = nuovo ordine». ⭐ Dal 2026-10-10 lo dice **solo il DB** (lock qui
sotto): il BA arriva al DB e il service non ricopia piu' il controllo.

**Difesa DB autoritativa atterrata** (DB-ORD-LOCK, 2026-06-04): `billing_account_id`
**e** `soggetto_ruolo_id` sono immutabili su UPDATE via lock-columns data-driven
(registro `dbops.automation_lock_columns`, non trigger a mano), che solleva lo
**stesso** codice `E_ORD_CLIENTE_IMMUTABILE` (estratto da `_db_errors` su UPDATE
diretta che bypassa il service). Conseguenza correlata: `trgfn_ordini_normalize`
ora ri-eredita `fatturazione_trigger` dal BA **solo su INSERT** (il ramo UPDATE era
diventato logica morta). Override straordinario:
`SET LOCAL zeroerp.allow_lock_columns_override = 'on'`. Brief:
[db-brief-ordini-lock-cliente.md](../../../dev/work-done/db-brief-ordini-lock-cliente.md).

### Delete `DELETE /api/v1/vendite/ordini/<id>/`

Hard-delete **della sola bozza orfana** (supporto al pattern "abbandono bozza":
il create auto-salva una BOZZA per abilitare le righe; se l'operatore esce senza
inserirne, la bozza vuota va rimossa). Guard (allineato a `elimina_preventivo`,
**niente hard-delete di dati reali**): stato `DRAFT` **e zero righe**. Un ordine
con righe **non si cancella, si annulla** (`cambia-stato → ANNULLATO`):
`E_ORD_STATO_TRANSIZIONE` (409) con messaggio dedicato. Risposta:
`{"ordine_id": <id>, "deleted": true|false}`. Le righe/componenti della bozza
vuota hanno ON DELETE CASCADE; il trigger DB blocca se collegato a DDT.

### Emetti `POST /api/v1/vendite/ordini/<id>/emetti/` (multipart)

**Flusso target della famiglia vendite**
([§6 brief-ordini-stampa.md](../../../dev/work-done/brief-ordini-stampa.md)): emissione =
conferma documentale. Clone di `ApiPreventivoEmetti`/`ApiOffertaEmetti`. Orchestra in
**una transazione atomica** (savepoint annidato):

1. `ordini_service.conferma(id)` — il passaggio allo **stato di emissione**
   dell'ordine (oggi `CONFERMATO`), letto dal vocabolario e non scritto nel codice
   (BB `stato_di_emissione`), dal verbo `vendite.fn_cambia_stato_ordine`;
2. `DocumentGenerationService.genera_documento(...)` sullo stato `CONFERMATO` (lo
   snapshot del context riflette il nuovo stato);
3. allegati multipart opzionali (`allegati`).

Se la generazione fallisce, il rollback dell'atomic **annulla la conferma** → lo stato
resta `DRAFT`, niente record documentale orfano (come preventivi/offerte). Body
multipart: `template_documento_id`, `tipo_documento_output_id`, `allegati` (tutti
opzionali). Risposta: `{ "ordine": <esito conferma>, "documento": <documento generato> }`.
Prerequisito: template `ORDINE_VENDITA` con versione **PUBBLICATA** (vedi Documenti).

**Permesso dell'emissione** (dal 2026-10-25): livello sul documento e l'azione dalla
riga del passaggio verso lo stato di emissione (`emetti_passaggio` della factory;
oggi `emetti_ordine`): 403 prima della transazione a chi non ce l'ha, e il verbo la
controlla di nuovo (`E_PERMESSO_NEGATO`).

⛔ **`POST /<id>/conferma/` è ritirato** (2026-10-25, Z-2): era la conferma senza PDF
(opzione (i) del 2026-06-05, revocata da M-2). La rotta risponde 404.

**Percorso pratica — auto-completamento step `CONFERMA_ORDINE` (9013, bivio rev.3):**
se l'ordine è **COLLEGATO** a una pratica, la conferma completa anche lo step
`CONFERMA_ORDINE` con esito `POSITIVO`, **nella stessa transazione** (atomico:
conferma + completamento). Sblocca `INVIO_COMMESSA` (prereq `POSITIVO`). Riusa
l'azione standalone (la pratica orchestra, non decide al posto dell'operatore);
delega al BB motore `pratiche_service.completa_step_pratica`, **idempotente**
(no-op se lo step è già terminale o l'ordine non nasce da una pratica). L'`user`
del JWT è propagato per l'audit del completamento.

### Cambia stato `POST /api/v1/vendite/ordini/<id>/cambia-stato/`

Transizione di stato **generica data-driven** (es. annulla `DRAFT→ANNULLATO`).
Body: `stato_codice` (= `target_state` dell'azione da `available_actions`).
L'ammissibilità della transizione è validata dal trigger guard DB
`trgfn_ordini_guard_transizione` (matrice `config.transizioni_stati_ordini`):
transizione non ammessa → `E_ORDINE_TRANSIZIONE_NON_AMMESSA`. Lo stato di emissione
(`CONFERMATO`, letto dal vocabolario) è un 400 `E_ORD_VALIDAZIONE` col `field`: si
raggiunge solo da «Emetti». Un passaggio di processo (l'evasione) risponde
`E_DOC_PASSAGGIO_DI_PROCESSO`. Uno stato che il vocabolario non ha lo rifiuta il verbo,
`E_STATO_WORKFLOW_NON_TROVATO` (fino al 2026-10-25 un 400 `E_ORD_VALIDAZIONE` del service). Gli altri passaggi li scrive il verbo
`vendite.fn_cambia_stato_ordine`. Permesso: l'azione dalla riga del passaggio
(`PassaggioDocumento`): l'annullo di un ordine confermato chiede `emetti_ordine`,
quello di una bozza il solo livello sul documento.

Verso `ANNULLATO` passa sempre dal verbo `vendite.fn_annulla_ordine`: su un
ordine con legami (righe di preventivo, offerta d'origine, righe di commessa da
emettere) risponde `E_DOC_ANNULLO_CON_LEGAMI` (409, `confirm_and_retry`) finché
il body non dichiara `legami_confermati` (intero, letto da `…/legami/`).
Confermato, le righe del preventivo si liberano (EVASO → ACCETTATO), l'offerta
torna trasformabile, le righe di commessa da emettere si annullano.

### Legami `GET /<id>/legami/` (factory `build_legami_view`, BB
`_annullo_con_legami.legami_del_documento`): `{documento, id, legami, righe}`,
una riga per legame di `vendite.fn_documento_legami` con `origine` (codice di `config.sorgenti`), `natura`
(CONSUMO/PROVENIENZA), `origine_id` e il nome del documento dall'altra parte
dal lineage (`origine_tipo_codice_interno`, `origine_codice`). `legami` e' il
numero da dichiarare. Alimenta la finestra di conferma dell'annullo.

### Push singolo a commessa `POST /api/v1/vendite/ordini/<id>/push/`

Push del singolo ordine `CONFERMATO` via `fn_list_ordini_da_pushare(…, p_ordine_id)`
+ orchestratore (`pr_run_commesse_push_one`, sorgente `ORDINE_VENDITA`) →
`attivita_fatturabili`. Guard: stato `CONFERMATO` + righe eleggibili.

**Ponte emittibilità (2026-06-10)**: a push `COMPLETATO`, nella stessa
transazione, ogni commessa toccata viene resa **emittibile** — le attività
dell'invio `BOZZA → APPROVATA` + testata `→ PRONTA_FATTURAZIONE` (skip
idempotente se già pronta da una sorgente precedente). Dal 2026-10-12 lo fa una
madre DB, `vendite.fn_rendi_commessa_emittibile` (D-10 di
brief-db-annullo-a-valle-riapre-a-monte): prima erano due passi del backend. Regola di modello: il documento pushato è
già autorizzato (ordine `CONFERMATO`), quindi il push è esso stesso
l'autorizzazione delle attività generate. Il ponte vive in
`pr_run_commesse_push_one` e vale per ogni percorso (preventivi standalone,
ordini, handler pratica; il batch `pr_run_commesse_push` lo applica
best-effort per commessa con errori in `emittibilita_errors`).

**Percorso pratica — auto-completamento step `INVIO_COMMESSA` (9014, bivio rev.3):**
a push `COMPLETATO`, se l'ordine è **COLLEGATO** a una pratica, si completa anche
lo step `INVIO_COMMESSA` con esito `POSITIVO`. È lo step **terminale** del ramo
merce: completandolo (nessun altro flusso aperto, obbligatori fatti) la pratica
**si auto-chiude** (chiusura data-driven del motore). Stesso BB
`pratiche_service.completa_step_pratica` (idempotente, no-op fuori-pratica); gated
su push `COMPLETATO` (PARZIALE/ERRORE non completano lo step). `user` JWT propagato.

**Semantica transazionale (fix analisi-fix-transazioni #4, 2026-07-08)**: push +
chiusura step `INVIO_COMMESSA` avvengono in un **unico** `transaction.atomic()`. Un
fallimento della **chiusura-step pratica** rolla l'**intero push** (commesse + ponte
emittibilità): la pratica non resta mai non-riconciliata con commesse committate. Il
push è idempotente/ri-eseguibile → retry sicuro.

⛔ **L'invio in commessa NON cambia lo stato dell'ordine** (D-6 di
brief-db-annullo-a-valle-riapre-a-monte, 2026-10-12): «Evaso» vuol dire «la merce è
partita», e lo dicono solo le bolle (`vendite.fn_ordine_proietta_stato_evasione`).
Fino a quel giorno il push portava l'ordine a `EVASO` (best-effort, su un savepoint),
e un ordine `PARZIALMENTE_EVASO` mandato in commessa diventava `EVASO` con metà merce
in magazzino. Che l'ordine sia già in commessa lo dicono la lista «da mandare» e le
capability; un secondo invio senza righe libere risponde `E_ORD_NESSUNA_RIGA`.
Annullando la commessa le righe dell'ordine tornano da mandare, e lo stato non cambia
nemmeno allora.

La response espone `commesse_ids` (commesse toccate dal push), oltre a
`stato`/`push_log_id`/`handlers`/`righe_pushable`/`fatturazione_trigger`.

### Genera DDT `POST /api/v1/vendite/ordini/<id>/genera-ddt/`

Evasione: crea un DDT `DRAFT` dall'ordine (verbo DB `vendite.fn_genera_ddt_da_ordine`:
testata, righe e componenti in snapshot, fulfillment riga↔riga, proiezione dello
stato ordine). Corpo opzionale:

```json
{"righe": [{"ordine_riga_id": 10, "qta_da_evadere": "2"}]}
```

- `righe` omesso (o `null`) = tutto il residuo; lista vuota o voce senza
  `ordine_riga_id` → 400 `E_DDT_VALIDAZIONE`. `qta_da_evadere` in unità
  operativa.
- Risposta: `{"ddt_id": <id>, "numero": null, "ordine_id": <id>}` (il numero
  arriva all'emissione del DDT).
- Errori dal DB: `E_DDT_ORDINE_NOT_FOUND`, `E_DDT_ORDINE_STATO_NON_EVADIBILE`,
  `E_DDT_NIENTE_DA_EVADERE`, `E_QTA_SUPERA_RESIDUO`. Dettaglio in [api_ddt.md](api_ddt.md).

### Righe

| Metodo / Path | Scopo |
| --- | --- |
| `GET /<id>/righe/` | TUTTE le righe attive, nell'ordine del documento, dalla vista `vw_ordini_righe_dettaglio` (decodifiche, `importo_riga`, evaso e residuo, `is_composito_caso_a`) |
| `GET /<id>/righe/lista/` (+ `export/`) | La lista configurabile, BB condiviso: [api_righe_documento.md](api_righe_documento.md) |
| `POST /<id>/righe/` | Aggiunge una riga (solo DRAFT). `riga_nr` autoassegnato. Pricing auto-fill via `PricingService` se prezzo assente e articolo non composito; per articolo composito init componenti BoM con override prezzi opzionali (`componenti_overrides`, vedi sotto) |
| `PATCH /<id>/righe/<riga_id>/` | Aggiorna riga (solo DRAFT). Risposta `{ordine_id, riga_id, updated}` |
| `DELETE /<id>/righe/<riga_id>/` | Hard-delete riga (solo DRAFT). Risposta `{ordine_id, riga_id, deleted}` |
| `POST /<id>/righe/<riga_id>/data-consegna-confermata/` | La promessa di consegna **dopo la conferma** (2026-10-10, sotto) |
| `POST /<id>/righe/date-consegna/` | Una data di consegna su **più righe** (2026-10-12, sotto) |

Payload riga (create): `articolo_id` (obbligatorio), `descrizione`, `quantita`,
`qta_operativa`, `uom_operativa_id`, `factor_to_base`, `prezzo_unitario`,
`sconto_percentuale`, `meta`, `componenti_overrides`, e — dal 2026-09-14 — le
due **date di consegna**. PATCH: le stesse senza `articolo_id` e
`componenti_overrides`. **`iva_id` non c'è** (dal 2026-08-31 l'aliquota la decide
il risolutore): inviato, come ogni chiave fuori contratto, è un 400
`E_ORD_VALIDAZIONE` (2026-10-20: prima era scartato in silenzio). «Solo DRAFT»
è il BB `richiedi_righe_in_bozza` → 409 `E_RIGA_DOC_NON_BOZZA`. La doppia quantità operativa/base segue il
pattern standard (input con priorità all'operativa; `quantita` base derivata dal
trigger `trgfn_qta_from_operativa`). I totali testata sono ricalcolati da trigger DB.

⭐ **Le date di consegna della riga** (`brief-db-modifiche-certe-ciclo-vendita-e-articolo`,
Blocco A): `data_consegna_richiesta_cliente` (quando il cliente la vuole) e
`data_consegna_confermata` (quando **noi** ci impegniamo — D-16: non marcato =
nostro, marcato = della controparte). ISO `YYYY-MM-DD`, entrambe nullable:
ometterle resta legittimo; in `PATCH` un `null` esplicito **azzera**. Nessun
CHECK fra le due, ed è una scelta del modello (si può confermare *prima* di
quanto chiesto); una data malformata è un **400** col campo
(`E_ORD_VALIDAZIONE`, `fields`), non un 500 dal DB. Escono da `list_righe` e
`get_riga` (proiezione esplicita). Sulla testata non c'è nessuna colonna: la
lista ordini espone `data_consegna_richiesta_cliente_min` dalla vista
(`vw_ordini_lista`), il `min()` sulle righe attive. Le righe si scrivono solo in
`DRAFT`; la promessa, che si decide alla conferma, ha il verbo suo (sotto).

⭐ **Il verbo della promessa dopo la conferma** (dal 2026-10-10,
[brief-db-testata-dopo-emissione](/dev/work-done/brief-db-testata-dopo-emissione)
fase 1): `POST /<id>/righe/<riga_id>/data-consegna-confermata/`, corpo
`{"data_consegna_confermata": "AAAA-MM-GG" | null}` (`null` toglie la promessa).
Scrive la **sola** colonna; ogni altra chiave è un 400. ⛔ Nessun pre-check di
stato nel backend: in quali stati la data si cambia lo dice il lock delle righe
(`trgfn_doc_righe_lock_fuori_bozza`, oggi `CONFERMATO` e `PARZIALMENTE_EVASO`), e
il 409 `E_RIGA_DOC_NON_BOZZA` passa com'è. Il dettaglio porta sotto `capabilities`
la terna `can_edit_data_consegna_confermata` · `_reason` · `_reason_key`, letta
dallo stesso montaggio: in `DRAFT` è spenta col motivo `ORDINE_IN_BOZZA` (la data
si scrive modificando la riga). Risposta: `{ordine_id, riga_id, data_consegna_confermata}`.
`PATCH /<id>/righe/<riga_id>/` resta «solo in bozza» per tutte le colonne.
⛔ Dal 2026-10-12 una riga **già spedita** (un DDT uscito dalla bozza, anche per
una parte) tiene la sua data: 409 `E_ORDINE_RIGA_DATA_CONSEGNA_SPEDITA` del guard
di riga ([brief-db-date-consegna-righe-in-blocco](/dev/work-done/brief-db-date-consegna-righe-in-blocco) D-7).
Lo si sa prima dalla lista righe: `data_consegna_confermata_blocco` (il `reason`
del primo motivo, `NULL` = si cambia; chiave i18n
`vendite.ordini.data_consegna_confermata_reason.<reason minuscolo>`).

⭐ **Le date in blocco** (dal 2026-10-12, stesso brief §5, §8):
`POST /<id>/righe/date-consegna/`, corpo
`{"colonna": "data_consegna_richiesta_cliente" | "data_consegna_confermata",
"data": "AAAA-MM-GG", "modalita": "TUTTE" | "SOLO_VUOTE", "anteprima": false}`.
Un solo UPDATE sulle righe attive (`SOLO_VUOTE`: le sole senza data). Le righe
già spedite si **saltano e si contano** (solo per la confermata); ogni altro
rifiuto del DB — lo stato che non ammette la colonna (`E_RIGA_DOC_NON_BOZZA`) —
fa fallire il gesto per intero. Nessun pre-check di stato nel backend.
`anteprima: true` esegue lo stesso UPDATE e lo annulla: i numeri sono quelli
della scrittura, un rifiuto del DB arriva già qui, e niente resta scritto. Risposta: `{documento_id, colonna, data,
modalita, anteprima, aggiornate, saltate_spedite}`. Errori: `E_ORD_NOT_FOUND`
(404), `E_ORD_VALIDAZIONE` (400, col campo), `E_RIGA_DOC_NON_BOZZA` (409). La
scrittura è il BB `RigheDocumentoRepositoryMixin.scrivi_data_consegna`, la stessa
del verbo per riga.

### Componenti BoM (CASO A)

| Metodo / Path | Scopo |
| --- | --- |
| `POST /<id>/righe/preview-componenti/` | Preview read-only dei componenti BoM (pre-save). Payload: `articolo_id`, `uom_operativa_id`, `quantita` |
| `GET /<id>/righe/<riga_id>/componenti/` | Lista componenti persistiti (`?solo_attivi=true`) |
| `PATCH /<id>/righe/<riga_id>/componenti/<componente_id>/` | Aggiorna componente (solo DRAFT): whitelist `prezzo_unitario`, `attivo`, `meta` (altro → 400). `prezzo_unitario` non nullo richiede `prezzo_override_manuale` (403 `E_PRICING_OVERRIDE_NON_AUTORIZZATO`); `origine_prezzo` la calcola il server. Il modo di esposizione in fattura è della distinta (`esposizione_in_fattura` in lettura), non della riga |
| `DELETE /<id>/righe/<riga_id>/componenti/<componente_id>/` | Soft-delete componente (`attivo=FALSE`, solo DRAFT) |

**Override prezzi componente pre-save** (CREATE riga composita, simmetria
preventivi/contratti): il `POST /<id>/righe/` accetta `componenti_overrides`
(mappa `{componente_id: prezzo}`) dal dialog FE. È normalizzato
(`normalize_componenti_overrides`) e passato a `fn_ordine_riga_componenti_init`;
i componenti senza override ricadono sul pricing risolto. L'override manuale
richiede il permesso `prezzo_override_manuale` (gate L1
`validate_componenti_overrides_authorization` → `E_PRICING_OVERRIDE_NON_AUTORIZZATO`
se assente). La fn DB rifiuta override prezzo 0 su componente obbligatorio
(`E_PARAMETRO_INVALIDO`). In assenza di `componenti_overrides` l'init usa i prezzi
del resolver (comportamento storico).

### Note `GET/POST /<id>/note/` + `GET/PATCH/DELETE /<id>/note/<note_id>/`

Note partizionate (`vendite.note_ordini`, `target_tipo='ORDINE_VENDITA'`) via building
block `PartitionedNoteRepository` + `make_note_views`. Contratto identico agli
altri cinque domini (testata + riga via `target_riga_id`): payload, filtri,
`Idempotency-Key`, codici errore e permessi stanno in
[api_note_documento](../../core/manual/api_note_documento.md).

### Documenti / Stampa `…/<id>/documenti/…`

Stampa conferma d'ordine via motore `documenti` (sorgente `ORDINE_VENDITA`,
quarto dominio dopo preventivo/offerta/contratto). Flusso **allineato alla famiglia**
([§6 brief-ordini-stampa.md](../../../dev/work-done/brief-ordini-stampa.md)): in `DRAFT` solo anteprima on-demand; la generazione
documentale avviene nel passaggio `DRAFT → CONFERMATO` via `POST /<id>/emetti/`
(vedi sopra). Gli endpoint sotto coprono ristampa e gestione documentale post-bozza.

| Metodo / Path | Scopo |
| --- | --- |
| `POST /<id>/emetti/` | **Emissione**: conferma + genera PDF + allegati, atomica (vedi sezione Emetti) |
| `POST /<id>/documenti/genera/` | Genera e persiste un PDF (`documenti_generati` + evento `GENERATO`). Body opzionale: `template_documento_id`, `tipo_documento_output_id` |
| `POST /<id>/documenti/anteprima/` | Anteprima PDF temporanea (no persist, no evento). Risposta binaria `application/pdf` inline |
| `GET /<id>/documenti/` | Lista a catalogo `documenti.documenti_sorgente` dei documenti generati per l'ordine (`limit`/`offset`/`order_by`/`order_dir`/`search`, `emittente_fiscale_id` per il cancello di perimetro — contratto in [api_documenti_per_sorgente](../../documenti/manual/api_documenti_per_sorgente.md) §3.4) |
| `GET /<id>/documenti/<documento_id>/file/` | Download PDF principale + evento `SCARICATO` |
| `GET/POST /<id>/documenti/<documento_id>/allegati/` | Lista file (principale + allegati) / append allegati (multipart) |
| `GET /<id>/documenti/<documento_id>/file/<file_id>/` | Download di uno specifico file (principale o allegato) + evento `SCARICATO` |

Risoluzione: `_CODICE_SORGENTE_ORDINE = "ORDINE_VENDITA"` →
`resolve_contesto_documentale` risolve `sorgente_tipo_id`; il context è prodotto da
`OrdineDocumentContextBuilder` (`CODE='ORDINE_VENDITA'`). Orchestrazione, scope e
render restano in `DocumentGenerationService` (invariato). Permessi: oggetto
`("vendite", "ordine")`; le letture (lista, download) con `LETTURA`, i `POST`
(`genera`, `anteprima`, allegati) con `TUTTO`, come ogni POST non di ricerca.
`genera/` risponde 200. **Prerequisito**: template `ORDINE_VENDITA` con versione **PUBBLICATA**
(creazione manuale, vedi [documenti-e-stampe.md](../../../guide/documenti-e-stampe.md)):
senza, `genera`/`anteprima` falliscono con `E_DOCUMENTI_*`.

**Contratto di stampa — forma dei dati 3** (dal 2026-10-20,
[brief-db-grammatica-unica-documenti §12.10](../../../dev/work-done/brief-db-grammatica-unica-documenti.md)).
Chiavi di primo livello: `ordine`, `cliente`, `indirizzi`, `righe`, `riepilogo_iva`, `_meta`.
La provenienza è `ordine.origine`, con tre chiavi **sempre presenti** (`null` senza origine, il render gira
con `StrictUndefined`):

| Chiave | Che cosa |
| --- | --- |
| `tipo` | il codice della sorgente d'origine (`PREVENTIVO`, `OFFERTA_COMMERCIALE`): per confrontarlo, non per stamparlo |
| `codice` | il numero del documento d'origine |
| `etichetta` | il nome del tipo come lo legge una persona (`config.sorgenti.etichetta`): è quello che va sulla carta |

Storia della forma: 2 (2026-08-05) il blocco `indirizzi`; 3 (2026-10-20) `origine.etichetta`. Una versione di
modello in forma 2 non stampa più (409 `E_DOCUMENTI_VERSIONE_CONTESTO_DIVERSA`) finché non se ne pubblica una
in forma 3.

## Output

Envelope standard `success_response` (`{"data": …, "meta": {request_id}}`).
Liste: `paginated_envelope` (`count`, `page`, `page_size`, `total_pages`,
`results`).

## Regole

- **Modifiche**: la testata la governa il lock di testata del DB
  (`trgfn_doc_testata_lock_fuori_bozza`, 409 `E_DOC_*` propagato); righe e
  componenti si scrivono **solo in `DRAFT`** (`E_RIGA_DOC_NON_BOZZA`, 409).
  `E_ORD_STATO_TRANSIZIONE` resta per delete della bozza e push.
- **Pricing** sempre via `PricingService.resolve_prezzo` (BB condiviso, mai query
  dirette su listini). Il gate prezzi L2/L3 stile contratti **non** è applicato:
  scelta ratificata (analisi §8.bis) — pricing **stile preventivo** (resolve +
  prezzo dal caller).
- **Cliente immutabile in update**: cambio di `billing_account_id` rifiutato con
  `E_ORD_CLIENTE_IMMUTABILE` dal lock-columns del DB (vedi Update testata).
- **Scope emittente**: la vista è `security_invoker=on` (RLS attiva sulla tabella
  base); il filtro applicativo `fn_get_emittenti_scope_pk_ids` si somma
  (defense-in-depth). Un detail fuori scope torna **404**.
- **Numero**: generato dal trigger all'INSERT (mai NULL), immutabile dopo.

### Lineage / genealogia (brief-be-fe-lineage, 2026-07-15)

- **Colonne lineage in lista** (Fase B): la lista espone anche `fase`
  (proiezione normalizzata dallo stato), `pratica_id`/`pratica_numero`/
  `n_pratiche` (pratica collegata), `frontiera_tipo_id` +
  `frontiera_tipo_codice_interno` e `frontiera_natura_doc_codice_interno`
  (dalla vista, non piu' decodificati dal repository: changeSet `20260829-01/02`
  — ⛔ il nome e' cambiato, e con lui la sorgente),
  `frontiera_codice`/`frontiera_stato_codice_interno`/`frontiera_fase`,
  `n_discendenti_attivi`, `is_transitato` — dalla vista canonica estesa
  (LEFT JOIN `vendite.vw_documento_lineage`). Colonne configurabili
  `pratica`/`fase`/`transito` visibili di default (seed preset). `order_by`
  accetta anche `pratica_numero` e `fase` (la frontiera NON e' ordinabile).
- **Passaggi** `GET /api/v1/vendite/ordini/<id>/passaggi/` — genealogia del
  documento: pratica + frontiera + catena transiti in entrambe le direzioni.
  Contratto completo nel manuale del BB condiviso:
  [api_lineage_passaggi.md](api_lineage_passaggi.md).

## Codici errore

| Codice | HTTP | Quando |
| --- | --- | --- |
| `E_ORD_NOT_FOUND` | 404 | ordine/riga/componente inesistente o fuori scope |
| `E_ORD_VALIDAZIONE` | 400 | payload non valido (cliente mancante, campi vuoti, `billing_account_id` non numerico, chiave fuori contratto su testata o righe, filtro `stato_codice_interno` fuori vocabolario, ecc.) |
| `E_PRICING_OVERRIDE_NON_AUTORIZZATO` | 403 | prezzo manuale (componente o `componenti_overrides`) senza `prezzo_override_manuale` |
| `E_ORD_CLIENTE_IMMUTABILE` | 409 | tentativo di cambiare `billing_account_id`/`soggetto_ruolo_id` in update (lock-columns DB) |
| `E_DOC_CLIENTE_DIVERSO_DA_BA` | 400 | ruolo o utility diversi da quelli del BA (scrittura che li passa a mano; il service non li manda) |
| `E_DOC_EMITTENTE_FUORI_BOZZA` | 409 | cambio di emittente fuori bozza (BB `trgfn_doc_testata_lock_fuori_bozza`) |
| `E_ORD_STATO_TRANSIZIONE` | 409 | operazione non ammessa nello stato (delete fuori DRAFT o bozza con righe → annullare; push da stato non pushabile) |
| `E_RIGA_DOC_NON_BOZZA` | 409 | righe e componenti si aggiungono/modificano/tolgono solo in bozza — dal 2026-09-22 è il codice del BB a DB `trgfn_doc_righe_lock_fuori_bozza` (sugli ordini montato sul solo DELETE) e il pre-check BE lo usa uguale (`richiedi_righe_in_bozza`), con la frase a catalogo |
| `E_ORD_NESSUNA_RIGA` | 409 | push senza righe eleggibili (la conferma senza righe la rifiuta il guard: `E_ORDINE_CONFERMA_SENZA_RIGHE`) |
| `E_ORD_OFFERTA_GIA_CONVERTITA` | 409 | conversione offerta→ordine già avvenuta (univocità 1:1): guard BE fail-fast + rete UNIQUE parziale `uq_ordini_v_documento_origine_offerta` (via `map_integrity_error`) |
| `E_ORDINE_TRANSIZIONE_NON_AMMESSA` | varia | trigger guard: transizione di stato non presente/attiva in `config.transizioni_stati_ordini` (es. `cambia-stato` verso uno stato non ammesso) |
| `E_ORDINE_CONFERMA_SENZA_RIGHE` | varia | trigger guard: `DRAFT→CONFERMATO` senza righe attive (unica sede della regola dal 2026-10-25) |
| `E_PERMESSO_NEGATO` / 403 | 403 | conferma o annullo di un confermato senza `emetti_ordine` (la catena dalla riga del passaggio, poi il verbo) |
| `E_DOC_PASSAGGIO_DI_PROCESSO` | varia | `cambia-stato` verso un passaggio che fa il sistema (l'evasione) |
| `E_CONFIG_MANCANTE` | 500 | il vocabolario non ha uno stato di emissione (errore di cablaggio, non di dati) |
| `E_VENDITE_DUPLICATO` / `E_VENDITE_FK` | 409 / 400 | violazione UNIQUE/FK (via `map_integrity_error`) |
| `E_ORDINE_*` | varia | altri codici sollevati dai trigger DB (estratti via regex) |
| `E_UI_EXPORT_FORMAT_INVALID` / `E_UI_EXPORT_LIMIT_EXCEEDED` | 400 / 422 | export |
| `E_DOCUMENTI_NOT_FOUND` / `E_DOCUMENTI_VALIDATION` / `E_DOCUMENTI_RENDER_FAILED` | 404 / 400 / 500 | stampa: ordine o template/versione non risolti, input invalido, render fallito (`TECNICO`) |

Tutti registrati in `error_policies.py` (gli `E_VENDITE_*` e gli `E_UI_*`
preesistono; gli `E_ORD_*` aggiunti con questo scheletro).

## Dipendenze DB

- Vista lista: `vendite.vw_ordini_lista` (`20260603-14`, `security_invoker=on`,
  espone agente + origine polimorfa).
- Catalogo lista: `ui.lista_definizione` id=7 `vendite.ordini` + colonne/preset
  (`20260603-15` + seed).
- Funzioni: `fn_ordine_riga_componenti_init` / `_preview` (BoM),
  `fn_list_ordini_da_pushare(…, p_ordine_id)` (push singolo).
- Azioni/transizioni data-driven (`20260605-08..12`): matrice
  `config.transizioni_stati_ordini` (DRAFT→CONFERMATO, DRAFT→ANNULLATO attive;
  CONFERMATO→ANNULLATO seedata `attivo=false`); `script.fn_available_actions_ordine`
  (capability del detail: `available_actions` + `can_edit_*` + `can_push_commessa`
  +reason + `non_editable_fields` + `stato_codice`); guard
  `trgfn_ordini_guard_transizione` (`BEFORE UPDATE OF stato_doc_ordine_id`:
  enforce grafo + precondizione righe su conferma). Convive col guard approvazione
  BoM (`20260512-20`).
- Riepilogo IVA / totali (`20260605-01..05`): viste derivate
  `vendite.vw_ordini_righe_iva_base` → `vendite.vw_ordini_riepilogo_iva_dettaglio`
  (entrambe `security_invoker=on`); `fn_ricalcola_totali_ordine` (somma il
  riepilogo, scrive `*_tot` in testata); trigger `trgfn_ordini_righe_ricalcola_totali`
  (statement-level su `ordini_righe` INS/UPD/DLT) e `trgfn_ordini_ricalcola_totali`
  (`UPDATE OF emittente_fiscale_id`, l'aliquota dipende dallo stato emittente).
- Trigger testata: `trgfn_ordini_gen_numero`, `trgfn_ordini_normalize`,
  `script.trgfn_default_emittente_fiscale` (dal 2026-09-15 al posto di
  `trgfn_ordini_default_emittente`), `script.trgfn_doc_guard_emittente_ba` (dal 2026-10-10
  al posto di `trgfn_ordini_guard_emittente_ba`),
  `trgfn_ordini_guard_transizione` (la vecchia
  `trgfn_ordini_guard_transizione_approvazione` è ritirata dal `20260512-28`), lock numero, immutabilità
  `canale_origine`.
- Modello esteso: `agente_soggetto_ruolo_id` (`20260603-12`),
  `documento_origine_tipo`/`_id` (`20260603-13`), fix `chk_ordini_v_r_qta_pos`
  → `quantita > 0` (`20260603-11`).
- Immutabilità cliente (DB-ORD-LOCK, 2026-06-04): `billing_account_id` +
  `soggetto_ruolo_id` lockati su UPDATE via registro `dbops.automation_lock_columns`
  (2 righe → trigger `trg_ordini_a10_lock_columns_upd` con codice
  `E_ORD_CLIENTE_IMMUTABILE`, convive col lock `numero`). `trgfn_ordini_normalize`
  ripulito: eredità `fatturazione_trigger` solo su INSERT (`20260604-01`).
- RLS: 3 policy (`rls_ordini_ef_whitelist` / `_cliente_ownership` / `_shop`).
- Stampa: tipo documento `documenti.tipi_documento_output` `ORDINE_VENDITA`
  (seed, applicato al DB di lavoro 2026-06-04). Template + versione PUBBLICATA =
  creazione manuale (non seed). Tabelle motore `documenti.*` invariate.

## Riferimenti

- Analisi BE/FE: [analisi-ordini-vendita.md](../../../dev/work-done/analisi-ordini-vendita.md)
  (§12 stampa, §8 decisioni)
- Brief DB: [db-brief-ordini-vendita.md](../../../dev/work-done/db-brief-ordini-vendita.md)
  e [db-brief-ordini-lock-cliente.md](../../../dev/work-done/db-brief-ordini-lock-cliente.md)
  (lock cliente)
- Stampa/documenti: [documenti-e-stampe.md](../../../guide/documenti-e-stampe.md)
- Riepilogo IVA ordine (DB + BE + FE): [documenti-non-fiscali-iva-db.md](../../../dev/work-done/documenti-non-fiscali-iva-db.md)
  (§12 modello, §13 sviluppo BE/FE)
- Tabella testata: [vendite.ordini](../../../dbzero/vendite/manual/ordini.md)
- Linee guida API: [api.md](../../../dev/api.md)
