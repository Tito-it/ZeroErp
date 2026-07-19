# Brief DB — Il DDT non pushabile dice sempre il motivo sbagliato (catch-all)

> **Tipo**: mini-brief al team DB · **Target**: `dev/db-tid` · **Data**: 2026-07-19
> · **Owner**: Tid · **Priorità**: 🟡 MEDIA (nessun dato errato: è un messaggio
> che mente all'utente su una situazione legittima)
> **Stato**: ☐ DA REALIZZARE
> **Origine**: rilievo in-app di Tid (2026-07-19) su **DDT0000326 / ORD0000580**.
> Il DDT è **CONSEGNATO**, ma nel drawer non compare il push a commessa e il
> banner recita *«DDT non ancora inviabile a commessa: dev'essere spedito o
> consegnato»* — cioè chiede una condizione **già soddisfatta**.
> **Stessa famiglia**: [brief-db-push-commessa-gia-inviato.md](brief-db-push-commessa-gia-inviato.md)
> (reason vere al posto di un no-op) ·
> [brief-db-i18n-namespace-reason-ordini.md](brief-db-i18n-namespace-reason-ordini.md)
> (namespace delle reason ordini) · [brief-db-guard-righe-avanzamento-stato.md](brief-db-guard-righe-avanzamento-stato.md)
> (azione non pronta → disabled+reason). ⚠️ **Non è però lo stesso difetto**: qui
> la `reason_key` è nel namespace giusto e il messaggio **si vede** — è il
> *contenuto* a essere falso.

## 1. Il rilievo, verificato sul DB vivo

`ORD0000580` ha **`fatturazione_trigger = 'CONFERMATO'`** (il default di
`billing_account.fatturazione_ordini`) ed è già `EVASO`; il suo `DDT0000326` è
`CONSEGNATO`, causale `VENDITA` fatturabile, BA valorizzato.

**Il comportamento del motore è corretto**: con trigger `CONFERMATO` vale la
regola XOR — fattura l'ordine alla conferma, il DDT non transita **mai** in
commessa (cintura `src_fatturazione_trigger != 'CONFERMATO'` nel lister, che
questo brief **non tocca**).

**È il messaggio a essere sbagliato.** In `script.fn_available_actions_ddt` il
classificatore delle reason ha tre soli esiti:

| condizione | reason |
| --- | --- |
| esiste riga in `fn_list_ddt_da_pushare` | *(azione push offerta)* |
| segmento `ALLOCATA` | `DDT_GIA_INVIATO` |
| segmento `EMESSA` | `DDT_GIA_FATTURATO` |
| **tutto il resto** | `DDT_NON_PUSHABILE` → *«dev'essere spedito o consegnato»* |

L'ultimo ramo è un **catch-all**: assorbe cause tra loro diverse e le racconta
tutte come un problema di stato di spedizione.

## 2. Le cause che oggi finiscono nel catch-all (censimento sul lister)

Dal `WHERE` vivo di `fn_list_ddt_da_pushare`, un DDT non eleggibile può esserlo
per **almeno cinque** ragioni distinte:

| # | causa | il messaggio attuale è… |
| --- | --- | --- |
| 1 | ordine sorgente con `fatturazione_trigger = 'CONFERMATO'` (XOR) | **falso** — condizione già soddisfatta, e non lo sarà mai |
| 2 | causale di trasporto **non fatturabile** (DL-28: solo trasporto) | **falso** — non è questione di stato |
| 3 | stato DDT **prima** dello stato-trigger (merce in viaggio) | **corretto** — è il caso per cui il testo è nato |
| 4 | standalone senza `billing_account` risolvibile | **falso** |
| 5 | contatore a differenza ≤ 0 (merce resa o già fatturata per altra via) | **falso** |

Solo **1 caso su 5** è descritto correttamente. I casi 1 e 2 sono per giunta
**permanenti**: nessuna azione dell'utente li sbloccherà, ma il testo suggerisce
di attendere/avanzare lo stato.

## 3. Cosa serve (NON come)

Il classificatore deve **distinguere le cause**, come già fa il gemello ordini.
Priorità dei rami nuovi:

- **`DDT_FATTURA_DA_ORDINE`** (caso 1) — *«la fatturazione è a carico
  dell'ordine (conferma): questo DDT non transita in commessa»*.
  ⚠️ **Speculare esatto di una reason che esiste già**: `fn_available_actions_ordine`
  espone `ORDINE_FATTURA_DA_DDT` («fattura il DDT, non l'ordine»). Metà della
  regola XOR è spiegata all'utente da giugno, l'altra metà no: è **quella
  asimmetria** il difetto, più del singolo messaggio.
- **`DDT_SOLO_TRASPORTO`** (caso 2) — *«causale non fatturabile: il documento
  accompagna la merce senza generare fatturazione»* (DL-28).
- Gli altri (4, 5) e il residuo: valutate voi se meritano un ramo proprio o se
  restano nel generico — purché il **testo del generico** smetta di affermare una
  condizione di stato, che è vera solo nel caso 3.

**Vincoli sul risultato:**

- **La logica di push non si tocca**: cintura XOR, JOIN causale fatturabile,
  contatore, `ordine >= trigger` restano **identici**. Qui cambia solo *come si
  spiega* un'esclusione già decisa altrove.
- **Fonte unica**: il classificatore deve leggere gli **stessi predicati** del
  lister, non riscriverli — è la regola che questa famiglia di brief ha già
  fissato (`fn_check_ddt_emittibile`, `fn_get_stato_push_segment`). Se serve un
  helper condiviso per «perché questa riga non è eleggibile», meglio quello di
  cinque `EXISTS` ricopiati nella capability.
- **Namespace**: le reason DDT usano già `vendite.ddt.push_commessa_reason.*` —
  corretto, **mantenerlo** (è precisamente ciò che manca agli ordini, brief
  companion i18n).

## 4. Cosa comunicare indietro a BE/FE

- **I codici `reason` e le `reason_key` nuove** (nomi esatti): il FE aggiunge le
  traduzioni it/en. Nessun altro adeguamento — il banner del drawer DDT e il
  tooltip disabled+reason sono già scritti e data-driven, si accendono da soli.
- Se un caso resta nel generico, **il nuovo testo del generico**, così la
  traduzione FE viene riallineata.

## 5. Impatto sulla validazione in corso (contesto utile)

Il rilievo è emerso mentre si validava la slice DDT-resi-dashboard: il giro di
test su `ORD0000580` **non è recuperabile** (con trigger `CONFERMATO` quel DDT
non pusherà mai e la merce è già fatturata via ordine). Il test riparte da un
ordine con `fatturazione_trigger ∈ {SPEDITO, CONSEGNATO}`. Nessun dato da
correggere: la situazione è legittima, era solo mal descritta.

## 6. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | Ramo `DDT_FATTURA_DA_ORDINE` (caso 1) — simmetrico a `ORDINE_FATTURA_DA_DDT` | ☐ |
| 2 | Ramo `DDT_SOLO_TRASPORTO` (caso 2, causale non fatturabile) | ☐ |
| 3 | Testo del generico non più basato sullo stato (o rami per i casi 4/5) | ☐ |
| 4 | pgTAP: un DDT consegnato di ordine `CONFERMATO` → reason `DDT_FATTURA_DA_ORDINE` (oggi darebbe `DDT_NON_PUSHABILE`) | ☐ |
| 5 | Apply dev + rigen doc auto-gen + comunicazione §4 a BE/FE | ☐ |

## 7. Riferimenti

- Caso reale: `DDT0000326` (id 504, CONSEGNATO) / `ORD0000580` (trigger CONFERMATO, EVASO)
- Definizione viva: `docs/it/dbzero/script/funzioni/fn_available_actions_ddt.md`
- Gemella con il ramo già presente: `docs/it/dbzero/script/funzioni/fn_available_actions_ordine.md`
- Predicati di eleggibilità: `docs/it/dbzero/vendite/funzioni/fn_list_ddt_da_pushare.md`
- Consumatore FE: `frontend/src/vendite/ddt/components/DdtDrawer.vue` + `locales/{it,en}.json`
