# Piano BE/FE — la distinta cerca le rate: lookup ricco, destinazione visibile, picker delle rate, N righe in un Salva

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-15.
> **Origine:** rilievo di Tid sul drawer della distinta (chat, 2026-09-15) →
> decisione **D19** nel brief madre
> ([§2-bis](brief-incassi-riconciliazione-rate-promemoria.md)) → prerequisiti
> DB in [brief-db-distinta-ricerca-rate.md](brief-db-distinta-ricerca-rate.md)
> (P-1 … P-5).
> **Stato:** ✅ **B** (17/09, committato), ✅ **A** (17/09 sera, a P-1
> consegnata), ✅ **C** BE + FE (17/09 sera), ✅ **D BE** (17/09 sera), ✅ **D FE**
> (17/09 notte, Q-1 chiusa da Tid); 🔍 **rilettura critica di A/C/D** fatta
> (17/09 notte, 2 — registro §9: un bug sul modello nello spazio, due sul
> contratto, quattro pulizie, un BB di core allargato con l'ok di Tid). Lo
> stato per pezzo è in §0-bis. ✅ **Eredità DB del 18/09** (P-6, P-7,
> `20260918-05`) raccolta lo stesso giorno (registro §9). Resta il collaudo a
> video (copione §7 del brief DB). A, C, D e l'eredità del 18/09 **non
> committati**.
>
> **In una riga.** Il rilievo è uno: *chi digita un incasso non riconosce il
> documento da un contatore, e la domanda vera è «quale rata?»*. Da lì quattro
> pezzi: il lookup fattura mostra il **documento** (A); la riga caricata fa
> **vedere** la sua destinazione, anche in modifica (B); nasce la **lista rate
> paginata** e un picker che la monta, col criterio obbligatorio (C); il picker
> lasciato aperto accumula N rate e al Salva le scrive come **N righe** con
> esito parziale per riga (D — è D1 reso a video).

---

## 0-bis. Stato di avanzamento

> Una riga per pezzo. ✅ fatto · 🟡 in parte · ⏳ in attesa di un prerequisito
> · 🔵 da fare.

| Pezzo | Stato | Prerequisito | Dove |
| --- | --- | --- | --- |
| **B** — destinazione visibile | ✅ (17/09) | nessuno | BE: **sette** colonne (le cinque di §3.1 più `fattura_natura_doc_codice_interno/descrizione` — la natura si segnala, D19-e) e due `LEFT JOIN` in `_RIGA_COLONNE`/`_RIGA_FROM`; `RigaContabileRow`; tre presidi sul DB provvisto in `test_riga_elimina_e_transizioni_db.py` (14-16: le colonne sulla riga e sulla coda, e il numero parlante **dalla sede unica**, non composto). FE: `DistintaDrawer` (colonne «Documento» con Tag natura e «Rata»), `DistintaRigaForm` (blocco «Destinazione» = `DrawerContextHeader` + `SaldoPanel`, nei due modi; riga non identificata dichiarata), `RataSelect` (importo), `useSaldi`/`SaldoPanel` (`escludiRigaId`, dichiarato dove non si applica — `useSaldi.spec.js`), `main.css` (`ml-05`), locales it/en. Verde: 189 test `pagamenti` (DB e2e compresi), 55 FE, lint, build, i18n, ruff. Doc: `api_pagamenti.md` §2, catalogo FE |
| **A** — lookup ricco (FE) | ✅ (17/09 sera) | — | `FatturaLookup`: opzione a tre righe (`numero_documento` + `NaturaDocTag` · registro · data · totale · cliente · id fiscale), `buildDisplay` sul numero parlante; i tre consumatori toccando un file. Presidio visivo (copione) |
| **C** — `GET /pagamenti/rate/` + `RatePickerDialog` singolo | ✅ (17/09 sera) | — | BE: `saldi_service.list_rate` → `list_rate_paginata` (pagina prima, saldo dopo via `get_saldi_rate(ids)`; `solo_aperte` sul perimetro, stessa `FROM`+`WHERE` come funzione dell'alias; numero esatto; scope `pk` + RLS), `ApiRateList` (`lista_codice = pagamenti.rate`), whitelist `RATE_SORT_COLUMNS` (`numero_documento → (numero, serie)`; `stato_descrizione` e `ba_codice` ordinabili per la regola del NUCLEO di `gen_seed_lista`), seed 68 + colonne 750-765 **accesi** (+ 766 su lista 52), `WHITELIST_BE` (con le altre sei liste di `pagamenti`, che non c'erano), `_LISTE`/`_ESERCIZI`, i18n `pagamenti.rate.col_*`. FE: `RatePickerDialog` (AppDialog xl + `DrawerTabLista`, criterio obbligatorio via gate, esaurite visibili e non scelte), `useRateStore`, pulsante nel form, `onSceltaRata`, `RataSelect` con la scelta che sopravvive (Q-2), `spazioSaldo` (Q-B: proposta e selezionabile = residuo − in lavorazione). Verde: 224 pagamenti (19 nuovi, 6 sul DB provvisto col mondo costruito), presidi seed/proiezione/ordinamento, `--verifica-ordinamento pagamenti.rate`, 58 FE, lint, guards, build, i18n, classi morte |
| **D BE** — `POST …/righe/da-rate/` | ✅ (17/09 sera) | — | `pagamenti_service.crea_righe_da_rate` (elenco letto con tetto 200 e duplicato = 400; fattura dalla rata sotto RLS; `crea_riga` così com'è; `run_fan_out` un savepoint per riga; fallite con `ErrorTranslator.to_api_error(exc).to_dict()`), `ApiDistintaRigheDaRate`, `creaRigheDaRate` nel client FE. Presidi: 12 unit + `RigheDaRateDbTests` per intero (PARZIALE, poi il secondo tempo con `forzata` che entra e resta scritta) |
| **D FE** — modalità multipla, area temporanea | ✅ (17/09 notte) | Q-1 → ok Tid («`useSelezioneConValore` in core») | `core/composables/useSelezioneConValore` (la sola metà «valore per riga»: mappa seminata dalla proposta, override, `incompleti`, `buildPayload` che scarta il solo `null` — il segno resta; spec 8 test), `pagamenti/composables/useRigheDaRate` (composizione di `useSelezioneLista` + `useSelezioneConValore`: selezionabile = spazio ≠ 0, fatti comuni, `salva()` con `tieniSolo` sulle fallite, errore per riga, `forza`/`annullaForzatura` + `motivoDi`/`impostaMotivo` sulle sole `confermabile`, `rataEsaurita` esportato; spec 8 test, i BB di core NON mockati), `RatePickerDialog` prop `modalita` (`singola`/`multipla`), `contabileId`, `readonly` esplicito: slot `#selection`/`#selection-header`, **area temporanea** `app-righe-scelte` (main.css — non una DataTable: il registro del guard resta a 45), fatti comuni, Salva `crea_righe` con plurale, chiusura a `COMPLETATO`, conferma sull'abbandono con rate in area; `DistintaDrawer` azione «Righe da rate» accanto a «Nuova riga» (stesso cancello `modificabile`, `severity: primary` inline), `@righe-create → ricarica`. i18n `pagamenti.rate.*` (12 chiavi it/en, tre con plurale). Verde: 74 FE (3 spec), lint, guards (DataTable, i18n, classi morte, icone), build |
| Residuo per natura (dopo P-5) | ✅ (17/09 sera) | — | `useEtichettePagamenti().residuoNegativo(residuo, natura)` — «da rimborsare» sulla NC, «di troppo» sul resto — in `rata(...)`, `RataSelect` (prop `naturaDocCodice`), picker. ✅ **E dal 18/09 anche su `RateFuoriCapienzaSearchTable`** (P-7 consegnata): fino a quel giorno la vista non portava la natura e la lista teneva la sua copia di «di troppo» |
| **Rilievi in-app di Tid sul picker** (18/09) | ✅ (18/09) | nessuno | **Quattro rilievi, quattro interventi.** (1) *Il dialog si presenta stretto e salta quando arrivano le righe* → il blocco lista porta `app-dialog-lista` (altezza **definita**, `--app-dialog-lista-h` ~dieci righe, `main.css`/`theme.css`): vuota o piena è alta uguale; (2) *dieci righe per default* → `useRateStore` nasce a `PAGINATION.COMPACT_ROWS` con l'opzione **`limit`** nuova di `useListaStoreCore` (vale anche in `reset()`; `useListaStoreCore.spec.js`, 4 test — il primo presidio del BB); (3) *niente documenti non numerati* → BE `solo_numerate` su `rate/` (`numero IS NOT NULL` in `_condizioni(alias)`, quindi anche sul perimetro di `solo_aperte`; service `bool()`, view `qp_bool_optional`, OpenAPI), lo store lo manda **di default**; presidi: unit (booleano) + DB provvisto con la **bozza costruita nel test** (non nella fixture: gli altri contano due rate), rosso alla controprova col filtro spento; ⏳ «solo le definitive, inviate a SDI» resta aperta (Q-4); (4) *due bordi a destra sul numero fattura* → `input-style` al posto di `style` sull'`InputNumber` (la larghezza sul wrapper non arriva all'`<input>`, che sbordava sul campo Serie). Verde: 245 `pagamenti` (DB e2e compresi), ruff; 99 FE (10 spec), lint, guards, i18n, classi morte, build. Doc: `api_pagamenti.md`, cataloghi BE/FE, frontend-standards §AppDialog |
| **Eredità DB del 18/09** — P-6 · P-7 · `ha_distinte` | ✅ (18/09) | `20260918-01…-05` applicati su dev (09:50 · 10:25) | **P-6** BE: `get_saldo_documento(fattura_id, *, escludi_riga_id)` → `fn_get_saldo_fattura(%s, %s)`, `saldi_service.saldo_documento(…, escludi_riga_id=)`, `ApiFatturaSaldo` legge `escludi_riga_id` (parametro OpenAPI **condiviso** con la rata: `_PARAM_ESCLUDI_RIGA_ID` + `_escludi_riga_id(request)`, seconda occorrenza); presidi: 2 unit (service + view, garbage = 400), 2 sul DB provvisto (`SaldoPrimaDiSeTests`: 400 → 0 sui due livelli con la stessa riga; id `≤ 0` risale `E_PAGAMENTI_CHIAMATA_NON_VALIDA` nudo — la base non traduce). FE: `getSaldoFattura(id, { escludiRigaId })` (params dalla stessa `paramsEsclusione` della rata), `useSaldi` `LETTORE[DOCUMENTO].esclusione = true`, spec riscritto (il test che asseriva «sul documento non arriva» era giusto fino al 18/09), `SaldoPanel`/`DistintaRigaForm` solo commenti — la nota «comprende anche questa riga» si spegne da sé perché legge `esclusioneSupportata`. **P-7** FE: chiavi `pagamenti.rate_fuori_capienza.col_natura` + `motivo_nota_credito_{sovra_incassata,movimento_contrario}` (it/en), riga **767** `attivo = t` nel CSV (⏳ migrate: Tid), colonna «Natura» via **`formato = natura_doc`** (dalla rilettura: niente slot), `motivoFuoriCapienza(codice, natura)` in `useEtichettePagamenti`, `#cell-residuo` → **`ResiduoCella`** (la copia locale `rate_fuori_capienza.di_troppo` esce). **`ha_distinte`**: chiave `amministrazione.registri_fatturazione.disattiva_blocco.ha_distinte` it/en (`{codice}`, `{quante}`). Verde: 250 BE (pagamenti + presidi seed/proiezione/skip-area, 4 DB e2e nuovi), ruff; 84 FE, lint, guards, classi morte, i18n, build |

---

## 1. Il terreno, misurato sul codice (2026-09-15)

| Fatto | Dove | Cosa ne discende |
| --- | --- | --- |
| Il lookup rende `numero` grezzo + ragione sociale; il footer «mostrate N di M» c'è | [FatturaLookup.vue:62-67](../../../../frontend/src/core/components/FatturaLookup.vue#L62-L67), `#option` | tre consumatori (`AbbinaRigaDialog`, `SistemazioneDrawer`, `DistintaRigaForm`) migliorano toccando **un** file |
| La lista fatture passa `v.*` della vista: la rev P-1 arriva al FE senza BE | [fatture_repository.py:172-178](../../../../backend/apps/vendite/db/fatture_repository.py#L172-L178) | A è **solo FE** |
| La ricerca libera fa `numero::text ILIKE %s`: 101 porta anche 1010 e 2101 | [fatture_repository.py:149-158](../../../../backend/apps/vendite/db/fatture_repository.py#L149-L158) | giusto nel lookup; nel picker il numero è **esatto** |
| La riga contabile porta `fattura_numero/anno/serie`, `scadenza_numero_rata`, `scadenza_data`, BA — i JOIN su `fatture` e `fatture_scadenze` esistono | [pagamenti_repository.py:154-200](../../../../backend/apps/pagamenti/db/pagamenti_repository.py#L154-L200) | B lato BE = cinque colonne e un JOIN |
| Il drawer mostra solo BA e `fattura_numero` grezzo; `scadenza_*` arriva e **non si vede** | [DistintaDrawer.vue:626-663](../../../../frontend/src/pagamenti/components/DistintaDrawer.vue#L626-L663) | |
| In modifica il form nasconde la destinazione (`v-if="!isEdit"`) | [DistintaRigaForm.vue:241](../../../../frontend/src/pagamenti/components/DistintaRigaForm.vue#L241) | R-6 protegge la **scrittura**; la lettura va aggiunta |
| Il form in creazione propone l'importo dal residuo (`proponiImporto`) e tiene `rataScelta` con la rata intera | [DistintaRigaForm.vue:132-160](../../../../frontend/src/pagamenti/components/DistintaRigaForm.vue#L132-L160) | il picker singolo deve **consegnare** fattura e rata nella stessa forma |
| `RataSelect`: «Rata n · scadenza · residuo», tre stati, residuo negativo «di troppo» | [RataSelect.vue:68-74](../../../../frontend/src/pagamenti/components/RataSelect.vue#L68-L74) | manca l'importo della rata; «di troppo» è sbagliato su una NC (P-5) |
| `useSaldi(LIVELLO.RATA)` e `SaldoPanel` esistono; un solo consumatore (`FatturaDrawer`) | catalogo FE | il residuo della riga in B si legge da lì, non da una colonna nuova |
| `useSelezioneLista` è il telaio della selezione su lista **paginata** (prune, `escludiOvunque`, `tieniSolo`) | catalogo FE | D si compone su questo |
| `useRigheSelezioneQta` è la macchina «selezione + quantità» su lista **intera** (`toggleAll`), `righeSelezionabili = residuo > 0` | [useRigheSelezioneQta.js](../../../../frontend/src/vendite/_shared/righe/useRigheSelezioneQta.js) | ⚠️ **non** è il telaio di D (§5.3) |
| `run_fan_out` + `FanOutEsito`; l'archiviazione delle code restituisce `{esito, richieste, riuscite, falliti[]}` con codice e frase per riga | [gestione_service.py:595-655](../../../../backend/apps/core/services/coda_lavori/gestione_service.py#L595-L655) | la forma di D lato BE, più l'errore **intero** |
| `useForzaturaConfermata` ramifica su `ui_action = confirm_and_retry`, cieco ai codici | catalogo FE | il secondo tempo per riga in D riusa lo stesso criterio |
| `createListaStore` + `useListaConfigurabilePage` + `startsEmpty/gateKeys` («la lista parte vuota finché non c'è un filtro») | catalogo FE | il **criterio obbligatorio** del picker è un pattern che esiste già |

---

## 2. Pezzo A — il lookup mostra il documento *(FE, dopo P-1)*

**Che cosa.** L'opzione dell'`AutoComplete` passa a tre righe (classe
`app-lookup-option`, come `IstanzaUtilityLookup`):

```
1234 - R1   [Nota di credito]           ← numero_documento · Tag natura (solo se ≠ FATTURA)
REG-01 · 12/09/2026 · 1.220,00 €        ← registro_codice · data · totale_doc
Rossi Mario SRL · 01234567890           ← ragione_sociale_completa · id fiscale
```

- `buildDisplay` (il testo nel campo dopo la scelta) diventa
  `numero_documento — cliente`; il ripiego «senza numero» resta.
- ⛔ **Nessuna composizione del numero nel FE**: si legge `numero_documento`.
  Finché P-1 non c'è la colonna è `undefined` e il ripiego direbbe «senza
  numero» su tutte: **per questo A aspetta**.
- Il Tag della natura riusa `natura_doc_codice_interno` ≠ `'FATTURA'` con la
  stessa forma del drawer fattura (`naturaNonOrdinaria`).
- i18n: `fattura_lookup.*` (it/en) — nessuna chiave nuova oltre alle etichette
  del terzo rigo, se servono.
- Test: nessun test FE oggi sul componente; il presidio è visivo (copione §6).

---

## 3. Pezzo B — la destinazione si vede *(BE + FE, nessun prerequisito DB)*

### 3.1 BE — cinque colonne sulla riga

In `_RIGA_COLONNE` (`pagamenti_repository.py`), accanto alle tre `fattura_*`
esistenti:

```sql
vendite.fn_numero_documento_fattura(f.numero, f.serie) AS fattura_numero_documento,
f.data             AS fattura_data,
f.totale_doc       AS fattura_totale_doc,
reg.codice         AS fattura_registro_codice,
sc.importo         AS scadenza_importo,
```

e in `_RIGA_FROM` un `LEFT JOIN vendite.registri_fatturazione reg ON reg.id =
f.registro_id`. ⭐ La fn è la **sede unica** del numero parlante: si legge, non
si compone — è la stessa mossa del dettaglio fattura.
⚠️ `_RIGA_COLONNE` alimenta anche la coda (`_RIGA_CODA_SELECT`): le colonne
arrivano **anche lì**, e il seed `pagamenti.righe` può prenderle quando vorrà.
`api_pagamenti.md` §2: cinque righe nell'esempio di `RigaContabileRow`.

### 3.2 FE — la tabella delle righe

`DistintaDrawer`: la colonna `fattura_numero` mostra `fattura_numero_documento`
col ripiego `—`. ⛔ Non `formatFatturaNumero` (`core/utils/format.js`): quella
utility **compone** `anno/serie n. numero`, cioè una terza forma del numero
accanto alla sede unica del DB — è un debito suo, non si allarga. Si aggiunge
la colonna **Rata** = «n. `scadenza_numero_rata` · `scadenza_data`» (vuota
sulla riga senza rata: il fondo fattura è così).
🔵 Debito già dichiarato: è la `DataTable` grezza delle righe nel master
(baseline), non cambia natura.

### 3.3 FE — il blocco «Destinazione» nel form

In `DistintaRigaForm`, **sempre** (creazione e modifica), sotto i campi della
destinazione e sopra i fatti: un blocco in sola lettura con la forma di
`DrawerContextHeader` (Tag = numero documento; items = cliente, registro ·
data · totale, rata n · scadenza · importo rata) + `<SaldoPanel>`:

- in **creazione** compare appena scelta la fattura (dal lookup **o** dal
  picker, §4.3) e si aggiorna alla scelta della rata: `SaldoPanel` livello
  `RATA` con `riferimentoId = scadenzaId` se c'è, altrimenti `DOCUMENTO` con
  `fattura.id`. ⚠️ `SaldoPanel` legge `livello` **una volta**: si monta con
  `:key="livello + id"`.
- in **modifica** si alimenta dalla riga (`fattura_*`, `scadenza_*` di §3.1) e
  resta **sola lettura**: R-6, la destinazione si cambia col verbo `abbina`.
  Una riga `DA_ABBINARE` mostra il blocco vuoto **dichiarato** («non
  identificata»), non un blocco assente.
- ⚠️ Il residuo mostrato in modifica **include la riga stessa** fra le «in
  lavorazione»: `useSaldi` non passa `escludi_riga_id`. Va aggiunto come
  opzione di `leggi` (l'endpoint rata lo accetta già) — altrimenti chi corregge
  500 → 600 legge un «in lavorazione» che conta i 500 che sta cambiando.
  ⭐ È la seconda ragione per cui la base dei saldi è una sola: l'opzione
  entra in `useSaldi` e `SaldoPanel` la riceve come prop.

### 3.4 FE — `RataSelect` con l'importo

Etichetta: «Rata n · scadenza · **importo** · residuo». Il residuo negativo
resta «di troppo» **finché P-5 non c'è**; con P-5 la frase dipende dalla natura
del documento: su una NC «X da rimborsare». La natura arriva dalla fattura
scelta (`natura_doc_codice_interno` — dal lookup, dal picker, o dalla riga in
B: da aggiungere fra le colonne di §3.1 quando serve). ⛔ Non un `if` sul
segno: il segno è lo stesso, cambia **cosa significa**.
✅ **Stato (17/09 sera)**: P-5 c'è; la frase per natura vive in
`useEtichettePagamenti().residuoNegativo`, `RataSelect` riceve
`naturaDocCodice` e la riga in B porta `fattura_natura_doc_codice_interno`.

---

## 4. Pezzo C — la lista rate e il picker *(dopo P-2, P-4)*

### 4.1 BE — `GET /api/v1/pagamenti/rate/`

`DomainAPIView`, `area_funzionale = "pagamenti"`, `is_search_endpoint = True`.
⛔ Niente `skip_area_check`: la consumano solo schermate di `pagamenti` (a
differenza delle quattro `fatture/<id>/…`, che servono il drawer fattura di
`vendite`).

| Param | Forma | Note |
| --- | --- | --- |
| `billing_account_id` | `qp_int_optional` | il cliente |
| `fattura_numero` | `qp_int_optional` | **esatto** su `numero`; con `serie`/`anno` opzionali per disambiguare |
| `serie`, `anno` | `qp_str`, `qp_int_optional` | |
| `search` | `qp_str`, ≥ 3 | cliente / BA / id fiscale — **non** il numero |
| `solo_aperte` | `qp_bool_optional` | ~~accettato e dichiarato non supportato finché P-3 non c'è~~ ✅ **supportato** (P-3 consegnata il 17/09): «aperta» = `residuo <> 0`, il nucleo si chiama sull'array del **perimetro** con la stessa `FROM`+`WHERE` della pagina (funzione dell'alias) |
| `data_scadenza_da/a` | `qp_iso_date_optional` | |
| `natura_doc_codice` | `qp_str` | per lo scadenzario; il picker non lo passa. Il maiuscolo lo mette il service (una sede, provata dal suo test — rilettura 17/09) |
| `limit/offset/order_by/order_dir` | `parse_list_params(qp, default_order="data_scadenza")` + `order_dir=qp_str(...)` grezzo | ⚠️ non `p["order_dir"]` (api.md) |

Envelope `{count, results}`; ogni riga = le colonne della vista P-2 **più**
`residuo · in_lavorazione · incassato · has_movimenti`.

Dove vive: `saldi_service.list_rate(...)` → `PagamentiRepository.list_rate_paginata(...)`.
⭐ **Pagina prima, saldo dopo**: la query pagina la vista (`COUNT(*) OVER ()`,
whitelist di ordinamento chiavata sul `campo_sorgente` del seed P-4, tiebreak
`scadenza_id`, `default_desc` **no** — è una coda, ASC) e la `LATERAL
pagamenti.fn_get_saldo_rata(sc.scadenza_id)` sta in una **seconda** query sugli
id della pagina (o su P-3 (a) quando c'è). ⛔ Non nella stessa query del
`COUNT(*) OVER ()`: girerebbe sul perimetro (fatto letto sul piano il 14/09 per
la `LATERAL` dei motivi). Il conteggio viene dalla stessa `FROM`+`WHERE` della
pagina (`fetch_paged_with_total`).
Scope: `add_emittente_scope_condition(..., column="v.emittente_fiscale_id",
convention="pk")` in aggiunta alla RLS (difesa in profondità, api.md).
Guard di lettura: la RLS della vista è `security_invoker` → la view **deve**
girare con la connessione dell'utente (`_guard_canale_sistema`, come le sorelle
di `pagamenti_repository`).

Test (BE): forma dell'envelope (`results` presente — il difetto del lookup
famiglie); whitelist di ordinamento = colonne del seed (`test_liste_configurabili_seed`);
`solo_aperte` → 400 con `fields`; `fattura_numero=101` **non** porta 1010
(costruito su DB provvisto, `ZEROERP_TEST_DB_E2E`); il saldo è letto sulla
**pagina** (un `EXPLAIN` in transazione, come per `_RIGA_INSERT`).

### 4.2 FE — `RatePickerDialog`

`pagamenti/components/RatePickerDialog.vue`: `AppDialog` **xl**, dentro
`<ListaConfigurabile codice="pagamenti.rate">` montata come una pagina
(`useListaConfigurabilePage` su uno store `createListaStore('pagamentiRate',
{ startsEmpty: true, gateKeys: ['billing_account_id', 'fattura_numero'],
orderBy: 'data_scadenza', orderDir: 'asc' })`).

- Toolbar: `BillingAccountLookup` (cliente), `InputNumber` numero fattura (+
  serie facoltativa), `ToggleNascoste`-like «mostra esaurite» ⛔ **no** — le
  esaurite si vedono e non si scelgono (residuo `= 0` ⇒ non selezionabile, col
  motivo `pagamenti.rate.esaurita`); nascondere una rata saldata è quello che un
  picker dei pagamenti **non** deve fare.
- **Criterio obbligatorio** = il gate della lista (`startsEmpty`): senza
  cliente o numero la lista resta vuota **e lo dice** (`app-empty-state` con la
  frase «indica il cliente o il numero della fattura»).
- Colonne dal catalogo (seed P-4). Slot cella `cell-natura`: Tag se ≠ FATTURA
  (la **segnalazione** di D19-e); `cell-residuo`: negativo detto a parole
  (stessa regola di §3.4).
- Prop `modalita: 'singola' | 'multipla'` (§5). In **singola**: click riga →
  `emit('scelta', rata)` e chiusura. `rata` porta **tutte** le colonne della
  riga: il form ne ricava `fattura` (`{id: fattura_id, billing_account_id,
  numero_documento, ragione_sociale_completa, natura_doc_codice_interno, …}`) e
  `rataScelta` (`{scadenza_id, numero_rata, data_scadenza, importo, residuo,
  …}`) — la stessa forma che oggi arrivano da `FatturaLookup` e `RataSelect`,
  così `proponiImporto` non cambia.

### 4.3 FE — il pulsante nel form

`DistintaRigaForm`, accanto al `FatturaLookup`: `Button` icon-only
`pi pi-search` (tooltip «Cerca fra le rate»), apre il picker in singola. Alla
scelta: `fattura.value = …`, `scadenzaId.value = …`, `rataScelta.value = …`.
⚠️ `RataSelect` ha un `watch` **immediate** su `fatturaId` che azzera la
scelta e ricarica: la sequenza è «prima la fattura, poi — al `select`
successivo — la rata», oppure `RataSelect` accetta un `modelValue` iniziale
senza azzerarlo al primo giro. Da decidere scrivendo, con un test sul
componente (`RataSelect.spec.js`): la rata scelta dal picker **non deve
sparire** un istante dopo.
✅ **Scritto così (17/09 sera)**: la seconda strada — `RataSelect` legge il
`modelValue` **prima** di ricaricare e lo **tiene** se è fra le rate del
documento appena caricato (ri-emettendo `select` con la rata della tendina);
lo azzera solo se non c'è. Nel form `onSceltaRata` scrive fattura, rata e
`scadenzaId` nello stesso tick, e il `watch` sulla fattura azzera `rataScelta`
solo se è di un **altro** documento (`rataScelta.fattura_id !== f.id` — per
questo `list_rate_con_saldo` porta `fattura_id`). ⛔ **Nessun test sul
componente**: `@vue/test-utils` non è fra le dipendenze del frontend, e non si
aggiunge senza decisione di Tid. Il presidio è il copione (§7 del brief DB,
riga 4). Q-2 in §8 lo registra.

### 4.4 Dopo P-5

Con la rata della nota di credito a database: nel picker compare con Tag
natura e residuo negativo «da rimborsare»; selezionabile (`residuo <> 0`); la
riga nasce con importo negativo proposto. ⛔ Nessun `if natura` nei predicati
di selezione: il segno lo porta il numero.

---

## 5. Pezzo D — N rate → N righe *(dopo C)*

### 5.1 BE — `POST /api/v1/pagamenti/distinte/{contabile_id}/righe/da-rate/`

Verbo di **collezione** sulla distinta (grammatica api.md: azione su nested,
nome che dice **cosa** — le righe nate dalle rate scelte). `handle_post_json`,
`Idempotency-Key` obbligatoria, gate come `POST righe/` (`add` d'area).

```json
{ "data_pagamento": "2026-09-15", "data_valuta": null, "riferimento_ente": "TRN 2026…",
  "righe": [ { "scadenza_id": 1301, "importo": "500.00" },
             { "scadenza_id": 1302, "importo": "620.00", "forzata": true, "motivo_forzatura": "…" } ] }
```

- I **fatti comuni** (date, riferimento) valgono per tutte; per riga solo
  `scadenza_id`, `importo`, `forzata`, `motivo_forzatura`. Tetto **200** righe,
  `scadenza_id` **duplicato = 400** con `fields` (da un picker è un difetto del
  client; deduplicare in silenzio butterebbe via un importo).
  ✅ **(rilettura 17/09)** I fatti comuni si leggono **una volta, prima del
  giro**, con gli stessi lettori di `crea_riga`: un fatto comune malformato è
  un **400 col campo** della richiesta, non N righe fallite identiche in un
  200 `ERRORE` (la forma della prima stesura).
- Per ogni riga il service risolve `fattura_id` dalla rata
  (`repository.get_fattura_id_di_rata(scadenza_id)` → sotto RLS; assente ⇒
  `E_RATA_NON_TROVATA` **per quella riga**) e chiama **`crea_riga`** così
  com'è — BA dalla fattura, stato `ABBINATA`, guard DB di coerenza e capienza
  sull'`INSERT`. ⛔ Nessuna seconda strada di inserimento.
- `run_fan_out(righe, _process)`: un savepoint per riga. Risposta:

```json
{ "esito": "PARZIALE", "richieste": 3, "riuscite": 2,
  "creati": [ { "indice": 0, "scadenza_id": 1301, "riga": { …RigaContabileRow… } }, … ],
  "falliti": [ { "indice": 1, "scadenza_id": 1302,
                 "errore": { "code": "E_RIGA_CONTABILE_CAPIENZA_SUPERATA", "message": "…",
                             "hint": "…", "ui_action": "confirm_and_retry", "fields": [], "targets": [] } } ] }
```

  ⭐ `errore` è **`ErrorTranslator.to_api_error(exc)`**, la sede unica delle
  politiche dell'envelope (hint tolto sui tecnici, bersaglio solo dove c'è un
  gesto): la stessa lezione del blob `errore` del runner (api.md, 09/09). Lo
  status è **200** anche su `PARZIALE`/`ERRORE` — chi legge guarda `esito`.
  ✅ **(17/09 notte, ok Tid)** `exc` la porta il BB: `FanOutItemErrore.eccezione`
  — nessun dizionario laterale nel service, e il guasto nato fuori da
  `_process` passa dalla stessa porta (test 11-bis).
- ⚠️ Idempotenza: la chiave copre il **giro**; un secondo invio identico
  rigioca la risposta. Il secondo tempo (§5.2) è un giro **nuovo** con le sole
  righe rimaste: chiave nuova.

Test: `SimpleTestCase` con `crea_riga` finto — esito a tre stati, indici
giusti, duplicato → 400, tetto; e **uno sul DB provvisto** che **costruisce**
il caso: due rate, la seconda con importo oltre la banda ⇒ `PARZIALE`, la prima
inserita, la seconda in `falliti` con `ui_action = confirm_and_retry`; poi il
secondo giro con `forzata` che la fa entrare. È il presidio della regola «venti
righe buone non si perdono per una».

### 5.2 FE — la modalità multipla e l'area temporanea

Dal toolbar delle righe del drawer (`pageActionsRighe`), accanto a «Nuova
riga», l'azione **«Righe da rate»** (visibile con `modificabile`): apre il
picker in `multipla`.

Nel dialog, sotto la lista, l'**area temporanea**: le rate scelte (attraverso
le pagine) con **importo per riga** proposto dallo **spazio** (Q-B) e
modificabile; in testa i fatti comuni (data pagamento = oggi, data valuta,
riferimento). Salva → `da-rate/`.

- **Esito completo** → toast, `emit('righe-create')`, il drawer ricarica, il
  dialog si chiude.
- **Esito parziale** → `tieniSolo(scadenza_id dei falliti)`: le riuscite
  escono dall'area (sono già righe del foglio), le fallite restano ciascuna
  con la **frase** del database; quelle con `ui_action = confirm_and_retry`
  mostrano motivo + «Forza» **per riga**; un nuovo Salva rimanda **solo** le
  rimaste, con `forzata` dove confermato. Il frontend resta cieco ai codici:
  ramifica su `azioneUi`, come `useForzaturaConfermata`.
- Chiusura con righe nell'area → conferma (`useConfirmAction`): un'area
  temporanea persa in silenzio è lavoro perso.

### 5.3 ⭐ Regola del 2 — il composable dell'area temporanea (dichiarazione)

> In chat avevo scritto che il telaio è `useRigheSelezioneQta` da promuovere in
> `core`. **Non regge, e lo correggo qui**: quella macchina lavora su una lista
> **intera** (`toggleAll`, `righeSelezionabili = residuo > 0`) e il picker è
> **paginato** — la selezione attraversa le pagine, serve il prune, e su una NC
> il residuo selezionabile è negativo. Il telaio giusto è **`useSelezioneLista`**
> (core), che esiste dal 04/09 proprio per questo.

Questa è la seconda occorrenza di «selezione + un **valore** per riga proposto
dal residuo + `buildPayloadRighe`» (la prima: `useRigheSelezioneQta`,
`qtaMap`). Schema condiviso: mappa valore-per-chiave seminata dal residuo,
sovrascrivibile, `buildPayload(mapRow)`. Differenze: telaio intera vs
paginata; predicato `> 0` vs `<> 0`; quantità vs importo con segno.
⇒ Propongo **`useSelezioneConValore`** in `core/composables/` — la sola metà
«valore per riga» (`valori`, `proponi(chiave, residuo)`, `valoreDi`,
`buildPayload`), che si compone con **entrambi** i telai
(`useSelezioneToggle` per le liste intere, `useSelezioneLista` per le
paginate). `useRigheSelezioneQta` **non si tocca** in questo giro: ci passa
quando lo si riapre, e il debito è dichiarato qui. Il consumatore di dominio è
`pagamenti/composables/useRigheDaRate.js` (telaio + valori + fatti comuni +
`tieniSolo` sull'esito). ✅ **Ok di Tid il 17/09** («useSelezioneConValore in
core»): scritto così com'è dichiarato qui. Una sola cosa in più rispetto alla
dichiarazione: `sincronizza(righe)` al posto di `proponi(chiave, residuo)` —
il BB riceve l'elenco delle righe scelte e allinea la mappa da solo (entra
chi manca con la proposta, esce chi non c'è più, chi c'è tiene il suo
valore), così il consumatore ha un `watch` di una riga e non una trafila di
aggiunte e rimozioni da tenere in passo col telaio.

---

## 6. Ordine dei passi, con chi fa cosa

| # | Passo | Chi | Aspetta |
| --- | --- | --- | --- |
| 1 | **B** BE: cinque colonne + JOIN; `api_pagamenti.md` §2 | BE | — |
| 2 | **B** FE: tabella righe, blocco «Destinazione», `SaldoPanel` (+ `escludi_riga_id` in `useSaldi`), `RataSelect` con importo | FE | 1 |
| 3 | **A** FE: opzione a tre righe del lookup | FE | **P-1** applicata |
| 4 | **C** BE: `GET /pagamenti/rate/` in `saldi_service` | BE | **P-2** applicata |
| 5 | **C** FE: `RatePickerDialog` singola + pulsante nel form | FE | 4 + **P-4** (seed) |
| 6 | **D** BE: `da-rate/` | BE | 4 |
| 7 | **D** FE: `useSelezioneConValore` (ok Tid) + `useRigheDaRate` + modalità multipla | FE | 5, 6 |
| 8 | Copione di collaudo: le righe di §7 del brief DB | FE | 7 |
| 9 | Dopo **P-5**: residuo per natura (§3.4, §4.4) | FE | P-5 |

Al termine di ogni passo: `manage-test.sh` sull'app toccata, build · lint ·
`check_i18n_keys`; il grep delle `DataTable` grezze **non sale** (il picker è
una `ListaConfigurabile`).

## 7. Documentazione da toccare

> ✅ Tutto toccato (17/09 notte); qui l'elenco resta come indice.

- `api_pagamenti.md`: §2 (colonne riga), una sezione nuova «4-bis · le rate» (`GET /rate/`, `da-rate/`), §Codici errore (nessuno nuovo: `E_RATA_NON_TROVATA`, `E_PAGAMENTI_VALIDATION`, `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` esistono), §Dipendenze DB (`fn_get_saldi_rate`, `vw_fatture_scadenze_lista`, `fn_numero_documento_fattura`), `rate/fuori-capienza/` (`numero_documento`, ordinamento).
- `api.md` §Endpoint attivi, riga «Pagamenti»: le due rotte.
- Catalogo BB FE: `RatePickerDialog`, `useSelezioneConValore`, `useRigheDaRate`; `FatturaLookup` (opzione a tre righe); `SaldoPanel`/`useSaldi` (`escludiRigaId`, `spazioSaldo`); `NaturaDocTag`; `useEtichettePagamenti` (`rata`, `residuoNegativo`).
- Catalogo BB BE: `saldi_service.list_rate` (la quarta lettura della base unica), `get_saldi_rate`, `crea_righe_da_rate`, `FanOutItemErrore.eccezione`.
- Brief madre §2-bis (D19) e §3.4 (lo scadenzario ha la sua rotta).

## 8. Domande aperte

| | Domanda | La mia proposta |
| --- | --- | --- |
| **Q-1** | Nome e taglio del BB di §5.3 | ✅ **Chiusa (Tid, 17/09)**: `useSelezioneConValore` in `core`, sola metà «valore»; `useRigheSelezioneQta` non si tocca ora — debito dichiarato nel BB e nel catalogo |
| **Q-2** | Il picker singolo dal form: la rata scelta deve sopravvivere al `watch` immediate di `RataSelect` (§4.3) | ✅ **Chiusa scrivendo (17/09 sera)**: `RataSelect` tiene il `modelValue` in arrivo se è fra le rate del documento caricato. ⚠️ **Senza test sul componente**: `@vue/test-utils` non è una dipendenza del progetto — aggiungerla è una decisione di Tid (§4.3); presidio a video (copione, riga 4) |
| **Q-3** | Registro anche sulle sei sorelle (P-1, Q-1 del brief DB) | ✅ **Chiusa dal DB (17/09)**: le sorelle col registro sono **tre** (ddt, ordini, resi), non sei — contratti, preventivi e offerte un registro non ce l'hanno (brief DB §4-bis.1) |
| **Q-4** | ⏳ **Quali documenti sono «incassabili» nel picker** (Tid, 18/09: «non i non numerati; in realtà solo le definitive, inviate a SDI — ma faremo poi») | Oggi il picker esclude le **bozze** con `solo_numerate` (`numero IS NOT NULL`), che è il fatto che la vista porta. La regola più stretta è un **predicato di dominio** — «su quale documento si può registrare un incasso?» — e la proposta è che nasca in **una sede a DB** (una `script.fn_check_*`/colonna della vista sullo stato: `INVIATA`/`REGISTRATA`, o `congela_fiscale` a seconda della decisione), letta dalla lista **e** dal guard della riga, così tooltip, filtro e rifiuto non possono divergere — non un secondo booleano `solo_inviate` accanto al primo. ⚠️ Oggi il guard di riga (`trgfn_vendite_contabili_righe_guard_rata`) **non** chiede lo stato del documento: la rata di una bozza si può abbinare — il filtro del picker è una presentazione, non un cancello. Da decidere con Tid e il team DB, quando si apre |

## 9. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-18** («fai i sedici come indicato») | ✅ **I venti store scritti a mano sono entrati in `useListaStoreCore`** — la casa dichiarata nel catalogo la mattina stessa, non una riga cambiata in venti file. Il censimento della mattina diceva **sedici**: erano **venti** (`grep "order_dir || '"` sui `.js`), fra cui `vendite/_shared/listaDocumenti.js`, a sua volta consumato da **quattro** store (ordini/ddt/resi/fatture). Tutti avevano la STESSA forma del `buildParams` del core con **tre** divergenze reali, che il core ora esprime come opzioni — nessuna inventata, ognuna viveva già in ≥2 copie: **`ricercaCorta`** (passthrough: `'svuota'` catalogo/listini/template, `'ignora'` pratiche/righe listino), **`orderDirDefault`** (ripiego del verso, default `'asc'` com'era; `'desc'` su registri e documenti — ⛔ non derivato da `orderDir`: `contratti` e `conversioniUom` aprono `desc` e ripiegano `asc`, ramo dormiente, si conserva), **`paramNames`** (il nome sul filo: offerte `validita_dal_min/max`, preventivi `data_al` — nello store restano `data_da`/`data_a` per `useSearchTable` e i DatePicker). ⭐ Il core espone **`paramsFiltro()`**, la sede unica lista+export che `famiglieDocumento` aveva già scritta nel proprio store (la view la chiama uguale). `createCrudStore` inoltra le opzioni del core tal quali (🔴 `limit`, nato la mattina stessa, **non arrivava**) e passa all'`extend` il core intero (`listini` avvolge `fetchList` per il preload versioni). **Forme**: factory dove lo store è lista/lista+CRUD (`indirizzi`, `conversioniUom`, `listini` → `createCrudStore`; `auditLog`, le tre `email*`, `famiglieDocumento`, `templateAssetDocumenti`, `emittentiFiscaliBA`, `registriNumerazione` → `createListaStore`), chiamata diretta nel `defineStore` dove lo store è quasi tutto dominio (`pratiche`, `operatori`, `contratti`, `listiniRighe`, i sei documenti di vendita) — `unitaMisura`/`uomTipi` inclusi: alla factory chiedevano un aggancio post-write per `invalidateLookup`, ed è **`afterWrite(id, azione)`** in `createCrudStore` (seconda occorrenza, «procedi 3 e 4» di Tid), chiamato prima di `emitDataChanged`, presidiato da `createCrudStore.spec.js` (4 test, il primo della factory). ⚠️ **Allineamenti dichiarati** (non silenziosi): otto liste `amministrazione`/`catalogo` mandavano `search` a qualunque lunghezza e ora partono da tre caratteri (policy `api.md`; con 1-2 caratteri restano piene); `emailLogs` usa il floor standard `defaultFiltroDataDaString()` al posto di «30 giorni fa» a mano; `operatori` ripiegava `'ASC'` maiuscolo → `'asc'`; `pratiche`/`unitaMisura`/`uomTipi`/`conversioniUom` hanno guadagnato `userScoped: true` che mancava. ✅ **`listaDocumenti.js` cancellato** (zero consumatori; ok di Tid, voce barrata nel catalogo). Restano su `useListaEmptyStateFetch` diretto i dieci store page-based / `sort_by`: non sono copie. Verde: **116** FE (`useListaStoreCore.spec.js` da 4 a **14**: `paramsFiltro`, `paramNames`, fetch col padre, le tre `ricercaCorta`), lint, guards, build. Doc: catalogo FE (sei voci), frontend-standards (§Empty state: «uno store-lista non si scrive a mano»; §Factory: nominava `createCrudAdminStore`, eliminata il 2026-06-05). ✅ **Tredici `getExportParams` su `store.paramsFiltro()`**: nove dalla rilettura critica (voce nel catalogo), più le quattro anagrafiche/contratti fatte qui — 🔴 **non mandavano l'ordinamento**, il file usciva nell'ordine di default del BE qualunque colonna fosse stata cliccata. ⚠️ La ricerca dell'export ora viene dallo store (debounced), non dal ref immediato: è quella con cui la lista è stata interrogata. Restano a mano **tre** (`ResiCodaTable`, `FondiFatturaDaDecidereTab`, `LottiListView`): store page-based fuori dal core — convergono col cantiere dei dieci store page-based. Verde finale: **120** FE, lint, guards, build |
| **2026-09-18** (rilievi in-app) | ✅ **Quattro rilievi di Tid sul picker delle rate, chiusi** (riga in §0-bis). Due cose viste facendo: (1) 🔴 la lista in un dialog non aveva un'altezza **definita** — `.p-dialog-content` non è una colonna flex — quindi si rendeva all'altezza del contenuto: è la stessa classe di difetto del blocco lista delle dashboard (`.app-dash-fermi`), nel verso opposto (lì spariva, qui saltava). La regola è scritta in frontend-standards §AppDialog: **lista in dialog = `app-dialog-lista` + store a dieci righe**; (2) `useListaStoreCore` cablava `limit: 25` in **due** sedi (nascita e `reset()`): l'opzione nuova le lega, e lo spec fissa proprio il `reset()` — uno store che rinasce a 25 dopo essere nato a 10 cambia passo alla seconda apertura senza nessun errore. ⚠️ Nel test DB della bozza la prima stesura scriveva fattura e rata in **una** CTE: la policy RLS di `fatture_scadenze` fa `EXISTS` sulla testata e dentro la stessa istruzione la riga della CTE non è ancora visibile — rifiuto «per riga» su una fattura che c'è. Due istruzioni, come la fixture. 📮 **Q-4** aperta (§8): il predicato «incassabile» più stretto di Tid è di dominio e va a DB, in una sede |
| **2026-09-18** (rilievo in-app di Tid) | ✅ **Le righe della distinta sono una lista standard.** Il rilievo: *«la lista della contabile non contiene la paginazione né il refresh, mancano tutte le caratteristiche di una lista standard, anche l'estrazione in CSV/Excel; le DataTable grezze vanno sostituite con lo standard»*. Era `dettaglio.righe` su una `DataTable` grezza, dichiarata «righe di un documento» (Gruppo B) — ma le righe contabili hanno endpoint propri, macchina a stati propria e coda propria: **prima domanda del criterio ⇒ Gruppo A**, come `TitoloIvaDrawer` il 02/09 (piano PrimeVue 5 riclassificato). **DB (dato, non DDL — CSV `ui`)**: lista **69** `pagamenti.distinta_righe` + colonne **768-786** (18 colonne + azioni; visibili di default le 9 che il drawer mostrava, le altre nel «Personalizza» e nel file) + preset 69 (25 righe, nessun `ordinamento_default`: lo decide il BE) + `lista_preset_colonna`. ⏳ **apply del mirror `ui`: Tid** — finché non è applicato, il drawer non trova la lista (`E_UI_LISTA_NON_TROVATA`). **BE**: `_RIGA_COLONNE` porta la natura come `natura_doc_codice_interno`/`natura_doc_descrizione` (senza `fattura_`: è la gemella del `formato = natura_doc`, e col prefisso la colonna «Natura» avrebbe reso `—` su ogni riga senza errore — `types.py`, form FE e test DB allineati); `DISTINTA_RIGHE_SORT_COLUMNS` (12, `fattura_numero_documento → (fattura_numero, fattura_serie)`, `id` ordinabile) + `_COLONNE_DATA`; `list_righe_distinta` su `_lista_paginata`, default **`id DESC`** (l'ultima riga digitata in cima — la scelta di Tid del 02/09 sulle sistemazioni, stessa ragione); `list_righe` service paginato con `validate_order_params(nullable)` e `count` da `COUNT(*) OVER ()` (era `len(righe)`: un'eco); `ApiDistintaRighe.get` con `parse_list_params` + `order_dir` grezzo + `lista_codice`; **`ApiDistintaRigheExport`** (`righe/export/`, stesso `lista_codice`, `EXPORT_MAX_ROWS + 1`); `get_distinta` **non porta più `righe`** (doppia lettura della LATERAL per riga). **FE**: `useDistintaRigheStore` (`createListaStore`, `parentField: contabileId`, `startsEmpty: false`, nessun `orderBy`), `DistintaDrawer` su `useDrawerTabLista` + `<DrawerTabLista>` (`fetchExtra = loadDetail`: «Ricarica» riallinea anche la testata; `extraActions` per «Nuova riga»/«Righe da rate» con la loro condizione; `#cell-stato` col Tag della forzatura; natura via formato, **niente slot**), `ExportDialog`, `listRigheDistinta(id, params)` + `exportRigheDistinta`; il watch di visibilità resta per reset del form e pulizia. i18n: 5 chiavi `pagamenti.righe.col_*` it/en (le altre 13 riusate: stessa entità della coda). Registro DataTable: **44** (era 45). **Presidi**: 8 API (`test_distinta_righe_export_api`: rotta, JWT, formato, cap, envelope, `+1`, ordinamento grezzo, `None` senza ordinamento), 3 service (fuori whitelist = 400, `None` al repository e conteggio vero, dettaglio senza righe), DB e2e 23 (ogni colonna della whitelist nei due versi **e senza**, con la LATERAL — la coppia `(fattura_numero, fattura_serie)` provata sul DB vero), `_LISTE`/`_ESERCIZI`/`WHITELIST_BE` registrati (il presidio di proiezione legge il CSV 69 e conferma ogni `campo_sorgente`, gemella compresa), `--verifica-ordinamento` ok. Verde: 194 pagamenti + 28 presidi core + 49 DB, ruff; 95 FE, lint, guards, i18n, build. ✅ **Regola del 2, ok Tid (18/09, «fai il punto 3»)**: il blocco «l'export segue l'ordinamento a video» era in **dodici** `.vue` (non cinque: il grep completo), più `paramsPagina` e il `buildParams` di `useListaStoreCore` — estratto in **`paramsOrdinamento`** (`core/utils/listParams`, accanto a `paramsPagina`, che ora lo consuma), ripiego a parametro (`asc` sui tre drawer su `useListaStoreCore`, `desc` sui documenti di vendita), zero copie residue nei `.vue`. 🔴 Trovato estraendo: sui **lotti** l'export ripiegava `desc` e lo store `asc` — l'unica copia divergente dalla propria lista, allineata alla fetch (ramo oggi dormiente: `onSort` scrive sempre i due campi). Spec `listParams.spec.js` (7). ⚠️ Fuori perimetro e dichiarati: **sedici** store scritti a mano con lo stesso blocco nel `buildParams` — la loro casa è la migrazione a `useListaStoreCore`. Verde: 106 FE, lint, guards, build. 🔵 **Da decidere**: il verso di apertura `id DESC` (scelto per simmetria con le sistemazioni) contro `id ASC` (l'ordine del foglio di carta): è un default del repository, una riga |
| **2026-09-18** (regola del 2, ok Tid) | ✅ **Le due estrazioni dichiarate alla rilettura, fatte.** **(a) `formato = natura_doc`**: `CellaConfigurabile.formatValue` rende `NaturaDocTag sempre` leggendo la descrizione (il `campo_sorgente`) e la gemella `natura_doc_codice_interno` dalla riga (`formatValue` riceve anche `data`; `testoCella` torna `null` come per `yesno`); le quattro colonne del CSV (493, 531, 751, 767) dichiarano il formato e i **quattro slot** sono usciti (`FattureSearchTable`, `LottoDrawer`, `RatePickerDialog`, `RateFuoriCapienzaSearchTable` — il picker tiene il Tag nell'area temporanea). ⚠️ `CellaConfigurabile` è nel working tree dell'**altra sessione** (`testoCella`, 10:32): edit additivo su ciò che c'è su disco, da sapere prima di un `Write` di là. 🔴 **Presidi, ed erano il buco della strada `yesno`**: (1) `test_liste_configurabili_seed` 9 — ogni `formato` del CSV è uno che `CellaConfigurabile` rende, **letto dal `.vue`** (`case '…'` / `formato === '…'`), non ricopiato: un formato sconosciuto cade su `String(value)` senza errore; 9-bis — la gemella si legge dal sorgente FE (`CAMPO_GEMELLO_NATURA_DOC`) e se la lettura non trova la costante **solleva**, non torna vuota; (2) `test_lista_proiezione_campo_sorgente` 1-ter — la gemella entra fra i campi dichiarati delle liste senza vista (45, 52, 68: provato che la chiede) e 5 — sulle liste con vista (48, `vw_fatture_lista`) si chiede al catalogo PG, con `skip` dichiarato se nessuna lista con vista ha un formato con gemella. **(b) `ResiduoCella`** (`pagamenti/components`): `Tag warn` + `residuoNegativo` sotto zero, altrimenti `formatCurrency`, e prop `nota` per il terzo stato del chiamante — «esaurita» resta del picker (predicato e chiave), la cella non sa cos'è una rata esaurita; `null` → `—`. Adottata dai due consumatori, `formatCurrency`/`residuoNegativo`/`Tag` tolti dove non servono più. ⚠️ Fino al migrate del mirror `ui` le quattro colonne a video escono come **testo** (il `formato` arriva dalla config a DB): la stessa attesa della 767. Doc: catalogo FE (`CellaConfigurabile`, `NaturaDocTag`, `ResiduoCella`), frontend-standards §Sì/No («se una cella si rende allo stesso modo in due liste, è un `formato`, non uno slot»), `api_pagamenti.md`. Verde: 95 FE, lint, guards, classi morte, i18n, build; 18 presidi core (5 DB), ruff |
| **2026-09-18** (rilettura) | 🔍 **Rilettura critica dell'eredità del 18/09 su richiesta di Tid** («bug, codice fragile o duplicato, hardcoded»). Corretto: (1) `views.py` — il nome `escludi_riga_id` era scritto **due volte** (parametro OpenAPI e parsing): `_escludi_riga_id()` lo legge da `_PARAM_ESCLUDI_RIGA_ID.name`; (2) test DB — la fixture «riga piena» era montata in **due** metodi e la copia aveva `cur.fetchone()[0]` senza guard: una funzione di modulo `_monta_riga_piena(cur) → (fattura_id, scadenza_id, riga_id)` per entrambe le classi; (3) `etichette.js` — wrapper `(v) => motivoFuoriCapienza(v)` inutile; (4) 🔴 **presidio assente sulle chiavi dinamiche**: `check_i18n_keys` dichiara «punto cieco» le chiavi `${prefisso}_${valore}` e le due chiavi NC nate oggi non avevano nessun test — nasce `pagamenti/etichette.spec.js` (11 test) che legge i locales veri e prova che ogni valore di ogni vocabolario **risolva** in it e en; ⚠️ la prima stesura asseriva «etichetta ≠ codice» ed è caduta su `tipo_psp` (etichetta legittima «PSP»): il predicato giusto è «`t` è stato chiamato». Controprova rossa con la chiave NC tolta. ⭐ **Regola del 2, DICHIARATE e non fatte — aspettano il tuo ok**: (a) la cella «Natura» è lo **stesso slot in quattro liste** (`FattureSearchTable`, `LottoDrawer`, `RatePickerDialog`, `RateFuoriCapienzaSearchTable`: `<NaturaDocTag :codice :descrizione sempre>`) — la strada è quella di `yesno`/`SiNoTag` (frontend-standards §Sì/No): un `formato = natura_doc` a catalogo reso da `CellaConfigurabile`, così *una natura in lista è una riga di CSV, non uno slot*; ⚠️ vuole `data` (la riga) oltre a `value` nel formatter, e **`CellaConfigurabile` è nel working tree dell'altra sessione** (`testoCella`, 18/09) — non lo tocco; (b) la cella «Residuo a parole» (`Tag` con `residuoNegativo` se `< 0`, altrimenti `formatCurrency`) è in **due** liste (`RatePickerDialog`, che ha in più il ramo «esaurita», e `RateFuoriCapienzaSearchTable`) — candidato `<ResiduoCella>` con slot per il ramo in più. Verde: 95 FE (9 spec), lint; 231 pagamenti + 22 DB e2e, ruff |
| **2026-09-18** (BE/FE) | ✅ **Eredità del 18/09 raccolta** (riga in §0-bis), dopo aver verificato su dbdev che i cinque changeSet fossero **applicati** (`databasechangelog`: `-01…-04` alle 09:50, `-05` alle 10:25) e le firme vive (`pg_proc`: `p_escludi_contabile_riga_id DEFAULT NULL` su entrambe le funzioni; `vw_rate_fuori_capienza` con le due colonne natura; riga 767 a `f`). Tre cose viste facendo: (1) la dichiarazione OpenAPI di `escludi_riga_id` era **scritta sulla rata** e andava ricopiata sul documento — seconda occorrenza, estratta in `_PARAM_ESCLUDI_RIGA_ID` + `_escludi_riga_id(request)` (una frase sola per i due livelli, e il parsing strict in un posto); idem nel client FE (`paramsEsclusione`); (2) la base dei saldi **non traduce** gli errori DB (il 404 di `E_FATTURA_NON_TROVATA` arriva nudo al middleware): il presidio sull'id `≤ 0` asserisce il `DatabaseError` col codice strutturato, non un `ServiceError` — è il contratto che c'è, non uno nuovo; (3) `RateFuoriCapienzaSearchTable` aveva la **propria copia** di «di troppo» (`rate_fuori_capienza.di_troppo`), scritta quando la vista non portava la natura: su una NC avrebbe detto «di troppo» dove il segno è «da rimborsare» — tolta, legge `residuoNegativo` come tendina, form e picker (`feedback_duplicazione_nasconde_il_bug`). ⚠️ `api_pagamenti.md` §5 diceva ancora «`CROSS JOIN` fra le due funzioni» sul saldo documento: il join è uscito il 29/08 (una funzione sola) — corretto nel passaggio. 📮 **Per il DB, due righe**: (a) la riga **767 non ha una riga in `lista_preset_colonna`** (la 766 l'ha, `visibile = f`): senza, `fn_resolve_lista_config` la merge come «colonna nuova» con badge — non blocca, ma è un'asimmetria fra le due sorelle nate dallo stesso brief; (b) ⏳ **migrate del mirror `ui`** per portare `attivo = t` su dev: il CSV è cambiato, l'apply è di Tid. Il ripiego del pannello (`core.saldi.include_riga_corrente`) **resta**: oggi nessun livello vivo lo mostra, il CLIENTE lo mostrerà |
| **2026-09-18** | 📮 **Dal DB: P-6, P-7 e i sei decimali scritti** (`20260918-01 … -04`, [brief §4-bis.10](brief-db-distinta-ricerca-rate.md)) — in attesa dell'apply. Tre cose per BE/FE, **nessuna bloccante per C e D**: (1) **B, il «prima di sé» sul documento**: `fn_get_saldo_fattura(p_fattura_id, p_escludi_contabile_riga_id DEFAULT NULL)` — `saldi_service.saldo_documento` prende `escludi_riga_id` e il repository chiama `fn_get_saldo_fattura(%s, %s)` (la forma di `get_saldo_rata`); `useSaldi`: `esclusione: true` su `DOCUMENTO`, e il pannello smette di dichiarare «non applicata». ⚠️ Semantica identica alla rata: la riga esclusa esce dal dichiarato **e**, se è già registrata, col suo movimento. (2) **Lista 52 — la natura**: `vw_rate_fuori_capienza` porta `natura_doc_codice_interno` e `natura_doc_descrizione` (arrivano già con `v.*`); la riga di seed **767** (`natura`, `campo_sorgente = natura_doc_descrizione`) è `attivo = f` finché non c'è la chiave `pagamenti.rate_fuori_capienza.col_natura` in it/en — si accende nello stesso commit; cella «Natura» con `NaturaDocTag`, e l'etichetta del motivo per natura («sovra-rimborsata» / «entrato invece di uscire» sulla NC) ramifica su `natura_doc_codice_interno`. La colonna **non** è ordinabile (non è in `RATE_FUORI_CAPIENZA_SORT_COLUMNS`). (3) **Decimali**: risolto a DB (`to_char` nel guard: `restano 500.00`), niente da fare — era `fatture_scadenze.importo numeric(18,6)` stampato col `::text`, non il nucleo. 🔵 **P-8** (la scala di `vendite_contabili_righe.importo`) è a Tid, con la raccomandazione del DB nel brief: un `CHECK` a due decimali che rifiuta, non un typmod che arrotonda in silenzio |
| **2026-09-17** (notte, 2) | 🔍 **Rilettura critica di A, C e D su richiesta di Tid** («bug, codice duplicato o fragile, hardcoded»). Trovato e corretto: (1) 🔴 **sul modello** — `spazioSaldo` sottraeva in virgola mobile (`100.30 − 100.00 = 0.29999999999999716`), quel numero era l'importo **proposto** in form e picker, `importo` a DB è `numeric` **senza scala** e il guard confronta `abs(importo) > abs(spazio)`: un importo mai toccato veniva **rifiutato per capienza** → sottrazione in centesimi, spec che ripete il caso; (2) 🔴 su `PARZIALE` il picker restava aperto con la lista **ferma**: le rate appena scritte mostravano lo spazio vecchio, rispuntabili → `reloadAll()` dopo un giro con riuscite; (3) 🔴 BE: i **fatti comuni** si validavano dentro il savepoint di ogni riga — una data malformata era un 200 `ERRORE` con N fallite identiche → letti **una volta** prima del giro con gli stessi lettori di `crea_riga`, 400 col campo (test 5b); (4) `motivi` del dialog **duplicava** `forzature[k].motivo` della macchina e non si azzerava alla riapertura → nella macchina (`motivoDi`/`impostaMotivo`, conferma e testo separati); (5) il predicato «esaurita» in due file → `rataEsaurita` esportato dalla macchina; (6) `RigheDaRateDbTests` nascondeva i test ereditati con `test_x = None` → classe base `_MondoRateDbTests` senza test; (7) descrizioni OpenAPI di `order_by` **ricopiate** (7 colonne su 9; su `fuori-capienza` mancava `numero_documento`) → lette dalla whitelist (`_descrizione_order_by`); «default 50» ma è **25**; natura in maiuscolo in view **e** service → solo nel service; commento orfano in `saldi_service`. ✅ **Regola del 2, ok di Tid (17/09 notte)**: `crea_righe_da_rate` catturava l'eccezione per riga con un dict laterale + `try/except/raise` in `_process` + ripiego `RuntimeError(e.messaggio)` — seconda copia di `gestione_service._esegui_archiviazione`. Ora `FanOutItemErrore.eccezione` (non opzionale) la porta dal BB, valorizzata nello stesso `except` del messaggio; i **due** consumatori leggono `e.eccezione` e i dizionari laterali sono spariti. Presidi: `test_fan_out` 8-bis (la stessa istanza, anche dal savepoint), `test_righe_da_rate` 11-bis (un guasto esce come `E_GENERICO` senza hint), i 60 del service delle code invariati. ⚠️ Visto e **non toccato**: `currency="EUR" locale="it-IT"` cablati sugli `InputNumber` (cinque file, debito preesistente); nessun `RataSelect.spec.js` (Q-2) perché `@vue/test-utils` non è fra le dipendenze; il `.pyc` di `gen_seed_lista` è **tracciato** in git. Verde: 25 FE (3 spec), lint, guards, i18n, classi morte, build; 214 pagamenti + 6 DB e2e + 21 proiezione/repository, ruff, `--verifica-ordinamento pagamenti.rate` |
| **2026-09-17** (notte) | ✅ **D FE scritto** sul BB approvato (Q-1 chiusa). Tre scelte fatte scrivendo, da sapere: (1) l'**area temporanea non è una DataTable** — né grezza (il registro di `check-datatable-baseline` sarebbe cresciuto) né configurabile (non è una lista: è l'anteprima di ciò che il Salva scriverà, con un campo per riga) — è un elenco a griglia `app-righe-scelte` in `main.css`; (2) il picker in multipla passa il **`readonly` da permessi** esplicito ad `AppDialog` (come i dialog d'azione dei drawer locked-by-stato), o il footer nasconderebbe il Salva; l'azione stessa è già filtrata da `modificabile`; (3) il dialog si chiude **da solo solo a `COMPLETATO`**: su `PARZIALE` resta aperto con le fallite e i loro motivi, e chiuderlo a mano con rate in area chiede conferma. Lo spec di `useRigheDaRate` prova la composizione con i due BB di core **veri** (mockati solo `useApiHandler`, `useNotify`, i18n): il caso 🔴 è «riuscita esce, fallita resta, il giro dopo rimanda solo lei con `forzata`». Resta a Tid il collaudo in-app (copione in brief §7) |
| **2026-09-17** (sera) | ✅ **A, C (BE+FE) e D BE scritti** sui prerequisiti consegnati; **D FE** ferma su Q-1. Tre cose viste facendo: (1) `gen_seed_lista.py --verifica-ordinamento` non conosceva **nessuna** delle sei liste di `pagamenti` (le saltava come «NON MAPPATA»): mappate tutte, e la regola del **nucleo** (Tid 2026-07-31: stato e billing account ordinano sempre) ha fatto accendere `stato_descrizione` e `ba_codice` su `pagamenti.rate` — e ha reso visibili **tre liste KO** già esistenti (`righe`: numero/codice e BA; `eccedenze`: totale; `canali_incasso`: utility e stato), che restano da decidere; (2) la prima stesura di `list_rate_paginata` costruiva il perimetro del nucleo con un `replace('v.', 'p.')` sulla `WHERE` — fragile per costruzione: riscritto come **funzione dell'alias**; (3) il messaggio del guard di capienza scrive «restano 0.000000 da regolare» (sei decimali nel `%s`): nota per il DB, non blocca. La proposta dell'importo nel form è passata da `residuo` a **spazio** (Q-B) anche sulla tendina, non solo nel picker: un solo numero proposto per la stessa rata |
| **2026-09-17** | ✅ **Lato DB consegnato e applicato su dev** (P-1…P-5 tutti, con Q-1 corretta: il registro va su ddt/ordini/resi, non su contratti/preventivi/offerte). ⚠️ **Prima di C e D leggere [brief-db-distinta-ricerca-rate §4-bis.9](brief-db-distinta-ricerca-rate.md)**: la chiave della vista è `scadenza_id` (`dataKey`), il nucleo dei saldi `pagamenti.fn_get_saldi_rate` vuole **l'array degli id della pagina** in una chiamata (non una `LATERAL` per riga, e non `NULL` per «tutte»: per lo scadenzario c'è `vw_saldi_rate`), «selezionabile» e importo proposto = `saldo − in_lavorazione` (Q-B di Tid), il seed `pagamenti.rate` nasce **spento** e si accende con la proiezione + `WHITELIST_BE`. P-3 c'è: il filtro «solo aperte» non è più «non supportato». P-5 c'è: la NC ha una rata negativa, `RataSelect` «di troppo» → «da rimborsare» per natura (§3.4), e il contesto PDF della NC riceve una rata negativa. Il residuo per rata ora **imputa** anche i movimenti senza rata (Q-A/γ): la riga «fattura sì, rata no» abbassa il residuo delle rate |
| **2026-09-17** (2) | 🔍 **Rilettura critica di B su richiesta di Tid** («bug, codice fragile o duplicato, hardcoded»). Trovato e corretto: (1) il predicato «natura non ordinaria» era la stessa riga in **tre** file e il Tag della natura in **cinque** → BB **`NaturaDocTag`** (`core/components`), adottato in tutti e cinque (i due nuovi, `FatturaDrawer` da cui la riga era stata copiata, e le due celle di lista con `sempre`); (2) l'etichetta della rata composta in **tre** modi (tendina, blocco, colonna) → `useEtichettePagamenti().rata(...)`, una sede; (3) in `useSaldi` il lettore e la sua capacità (`ESCLUSIONE_SUPPORTATA`) erano **due tabelle** da tenere allineate — accendere una senza l'altra avrebbe fatto sparire l'opzione in silenzio → una riga per livello `{leggi, esclusione}`; (4) il nome del verbo «Abbina a fattura» era **scritto dentro** la frase `destinazione_assente` → parametro `{azione}` dalla chiave del verbo; (5) il presidio BE sul numero parlante teneva un `assertNotIn` su una sola forma di composizione: tolto, resta l'asserzione positiva (dichiarata «presidio sulla forma, non cancello»). ⛔ **Classi morte** (`ml-1`/`ml-2`, sei siti) sanate con `ml-05`; il censimento delle altre (`w-full` ×47 …) è nel catalogo FE alla riga `ml-05`: giro suo, a rischio zero, su decisione di Tid. Verde: 55 FE, 16 DB e2e, lint, build, i18n, ruff |
| **2026-09-17** | ✅ **B scritto** (riga in §0-bis). Due cose viste facendo: (1) il saldo del **documento** non sa escludere una riga (`fn_get_saldo_fattura_contabili(p_fattura_id)` ha un parametro solo) — il pannello lo dichiara invece di sottrarre; 📮 **residuo per il DB**: un `p_escludi_contabile_riga_id` anche lì, come sulla rata, così la modifica di una riga senza rata legge lo stesso «prima di sé»; (2) `ml-1`/`ml-2` in cinque template sono classi **morte** (PrimeFlex non è installato) — nasce `ml-05` in `main.css`, e il censimento è scritto nel catalogo. In creazione il form legge il saldo documento **due volte** (la proposta dell'importo e il pannello): due letture della stessa base, non due formule — accettato |
| **2026-09-15** | 📝 Piano scritto dopo il «procedi» di Tid. Corretta un'affermazione fatta in chat: il telaio di D è `useSelezioneLista`, non `useRigheSelezioneQta` (§5.3). Nessun codice |
