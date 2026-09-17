# Piano BE/FE — la distinta cerca le rate: lookup ricco, destinazione visibile, picker delle rate, N righe in un Salva

> **Chi scrive:** backend/frontend (`dev/backend-tid`), 2026-09-15.
> **Origine:** rilievo di Tid sul drawer della distinta (chat, 2026-09-15) →
> decisione **D19** nel brief madre
> ([§2-bis](brief-incassi-riconciliazione-rate-promemoria.md)) → prerequisiti
> DB in [brief-db-distinta-ricerca-rate.md](brief-db-distinta-ricerca-rate.md)
> (P-1 … P-5).
> **Stato:** 📝 **piano scritto il 2026-09-15. Nessun codice.** Il pezzo **B**
> non ha prerequisiti DB e può partire su «vai» di Tid; **A** aspetta P-1;
> **C** aspetta P-2 e P-4; **D** aspetta C. Lo stato per pezzo è in §0-bis.
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
| **B** — destinazione visibile (BE 5 colonne + FE tabella, blocco, `SaldoPanel`, `RataSelect`) | 🔵 | nessuno | §3 |
| **A** — lookup ricco (FE) | ⏳ | P-1 (rev `vw_fatture_lista`) | §2 |
| **C** — `GET /pagamenti/rate/` + `RatePickerDialog` singolo | ⏳ | P-2 (vista), P-4 (seed); P-3 migliora, non blocca | §4 |
| **D** — modalità multipla + `POST …/righe/da-rate/` | ⏳ | C | §5 |
| Residuo per natura (dopo P-5) | ⏳ | P-5 | §3.4, §4.4 |

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
| `solo_aperte` | `qp_bool_optional` | 🔵 **accettato e dichiarato non supportato finché P-3 non c'è**: risponde `400 E_PAGAMENTI_VALIDATION` con `fields=['solo_aperte']`, non lo ignora in silenzio (`feedback_contratto_dichiarato_provalo_intero`) |
| `data_scadenza_da/a` | `qp_iso_date_optional` | |
| `natura_doc_codice` | `qp_str_upper` | per lo scadenzario; il picker non lo passa |
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
- Per ogni riga il service risolve `fattura_id` dalla rata
  (`repository.get_scadenza(scadenza_id)` → sotto RLS; assente ⇒
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
le pagine) con **importo per riga** proposto dal residuo e modificabile; in
testa i fatti comuni (data pagamento = oggi, data valuta, riferimento). Salva →
`da-rate/`.

- **Esito completo** → toast, `emit('create')`, il drawer ricarica.
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
`tieniSolo` sull'esito). ⚠️ **Aspetto l'ok di Tid** su nome e taglio prima di
scriverlo.

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

- `api_pagamenti.md`: §2 (colonne riga), una sezione nuova «4-bis · le rate» (`GET /rate/`, `da-rate/`), §Codici errore (nessuno nuovo: `E_RATA_NON_TROVATA`, `E_PAGAMENTI_VALIDATION`, `E_RIGA_CONTABILE_CAPIENZA_SUPERATA` esistono).
- `api.md` §Endpoint attivi, riga «Pagamenti»: le due rotte.
- Catalogo BB FE: `RatePickerDialog`, `useSelezioneConValore`, `useRigheDaRate`; `FatturaLookup` (opzione a tre righe); `SaldoPanel`/`useSaldi` (`escludiRigaId`).
- Catalogo BB BE: `saldi_service.list_rate` (la quarta lettura della base unica).
- Brief madre §2-bis (D19) e §3.4 (lo scadenzario ha la sua rotta).

## 8. Domande aperte

| | Domanda | La mia proposta |
| --- | --- | --- |
| **Q-1** | Nome e taglio del BB di §5.3 | `useSelezioneConValore` in `core`, sola metà «valore»; `useRigheSelezioneQta` non si tocca ora |
| **Q-2** | Il picker singolo dal form: la rata scelta deve sopravvivere al `watch` immediate di `RataSelect` (§4.3) | `RataSelect` accetta un `modelValue` iniziale e non lo azzera se la fattura non è **cambiata**; test sul componente |
| **Q-3** | Registro anche sulle sei sorelle (P-1, Q-1 del brief DB) | sì, stesso giro — ma è del DB |

## 9. Registro

| Data | Cosa |
| --- | --- |
| **2026-09-17** | ✅ **Lato DB consegnato e applicato su dev** (P-1…P-5 tutti, con Q-1 corretta: il registro va su ddt/ordini/resi, non su contratti/preventivi/offerte). ⚠️ **Prima di C e D leggere [brief-db-distinta-ricerca-rate §4-bis.9](brief-db-distinta-ricerca-rate.md)**: la chiave della vista è `scadenza_id` (`dataKey`), il nucleo dei saldi `pagamenti.fn_get_saldi_rate` vuole **l'array degli id della pagina** in una chiamata (non una `LATERAL` per riga, e non `NULL` per «tutte»: per lo scadenzario c'è `vw_saldi_rate`), «selezionabile» e importo proposto = `saldo − in_lavorazione` (Q-B di Tid), il seed `pagamenti.rate` nasce **spento** e si accende con la proiezione + `WHITELIST_BE`. P-3 c'è: il filtro «solo aperte» non è più «non supportato». P-5 c'è: la NC ha una rata negativa, `RataSelect` «di troppo» → «da rimborsare» per natura (§3.4), e il contesto PDF della NC riceve una rata negativa. Il residuo per rata ora **imputa** anche i movimenti senza rata (Q-A/γ): la riga «fattura sì, rata no» abbassa il residuo delle rate |
| **2026-09-15** | 📝 Piano scritto dopo il «procedi» di Tid. Corretta un'affermazione fatta in chat: il telaio di D è `useSelezioneLista`, non `useRigheSelezioneQta` (§5.3). Nessun codice |
