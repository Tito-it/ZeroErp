## Documentazione Concettuale – Funzione `vendite.fn_ddt_push_diagnosi(p_ddt_id)`

> **Vedi anche**
>
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)
> [vendite.fn_list_ddt_da_pushare](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare)
> [script.fn_available_actions_ddt](/dbzero/script/funzioni/fn_available_actions_ddt)
> [script.fn_get_stato_push_segment](/dbzero/script/funzioni/fn_get_stato_push_segment)
> [vendite.vw_contatore_merce](/dbzero/vendite/views/vw_contatore_merce)

---
### 🎯 Scopo Principale

`vendite.fn_ddt_push_diagnosi(...)` risponde a **una sola domanda**, per ogni
riga di un DDT: *perché questa riga non è inviabile a commessa?* Restituisce
`motivo = NULL` se la riga è eleggibile, altrimenti **il** motivo di esclusione
fra sette possibili.

Nasce per sciogliere un catch-all: prima, un DDT non inviabile riceveva sempre lo
stesso messaggio — «dev'essere spedito o consegnato» — vero per **una** causa su
sette e falso per le altre sei. Questa funzione distingue le cause, così la
capability [`script.fn_available_actions_ddt`](/dbzero/script/funzioni/fn_available_actions_ddt)
può spiegare all'utente il motivo giusto.

È la **fonte unica** dei predicati di eleggibilità: la stessa regola che il lister
[`fn_list_ddt_da_pushare`](/dbzero/vendite/funzioni/fn_list_ddt_da_pushare) usa per
*selezionare* le righe pushabili, qui è espressa per *spiegare* perché una riga è
esclusa. Le due funzioni non devono divergere — vedi §Contratto di equivalenza.

---

### Le sette cause (con precedenza)

`motivo_rank` è la precedenza: più basso = più forte. Quando una riga ricadrebbe
in più cause, vince quella di rank minore; quando le righe di uno stesso DDT
ricadono in cause diverse, chi consuma la funzione prende il **minimo** rank.

La precedenza è a **due livelli** (Decisione E del brief): prima le cause di
**documento** (valgono per tutto il DDT), poi le cause di **riga** (possono
differire riga per riga), e fra queste vince la più *azionabile*.

| rank | `motivo` | tipo | significato |
| --- | --- | --- | --- |
| 1 | `DDT_ANNULLATO` | documento | il DDT è annullato (documento morto) |
| 1 | `DDT_RESO` | documento | la merce è tutta tornata indietro |
| 2 | `DDT_SOLO_TRASPORTO` | documento | causale non fatturabile: accompagna la merce senza fatturare (DL-28) |
| 3 | `DDT_SENZA_BA` | documento | nessun billing account risolvibile |
| 4 | `DDT_ROUTED` | riga | riga già instradata (in attesa di fatturazione o già fatturata) |
| 5 | `DDT_MERCE_IN_VIAGGIO` | riga | lo stato è precedente al trigger: dev'essere spedito o consegnato |
| 6 | `DDT_FATTURA_DA_ORDINE` | riga | l'ordine sorgente fattura alla conferma (regola XOR): il DDT non transita mai in commessa |
| 7 | `DDT_CONTATORE` | riga | quantità già coperta per altra via (merce resa o già fatturata) |

Chi consuma la funzione decide quali cause meritano un messaggio proprio: la
capability dà un ramo a `SOLO_TRASPORTO`, `MERCE_IN_VIAGGIO`, `FATTURA_DA_ORDINE`
e raccoglie le altre in un generico neutro. `DDT_ROUTED` (rank 4) è intercettato
prima dalla capability (che distingue *già inviato* da *già fatturato*) e non
arriva al ramo generico.

---

### Come è costruita (staging)

Il calcolo riproduce **esattamente** l'ordine del lister, ed è questo che
garantisce l'equivalenza:

1. **Motivo pre-contatore, per riga** — si valutano le cause 1-6 con una scala di
   priorità: la prima che si verifica è il motivo della riga. Le righe senza
   motivo a questo stadio sono *superstiti*.
2. **Distribuzione del contatore, solo sui superstiti** — la quantità residua di
   partita viene distribuita fra le righe superstiti con lo stesso algoritmo
   greedy del lister (più vecchia prima). ⚠️ È essenziale che la distribuzione
   veda **solo i superstiti**: se contasse anche righe già escluse per altre
   cause, l'allocazione slitterebbe e il risultato divergerebbe dal lister.
3. **Caso contatore** — fra i superstiti, chi resta con quantità distribuita ≤ 0
   è escluso per `DDT_CONTATORE`; gli altri hanno `motivo = NULL` (eleggibili).

---

### Contratto di equivalenza (la rete di sicurezza)

La funzione **non riscrive** il lister e **non tocca** la logica di push: è una
lettura parallela degli stessi predicati. Perché le due non possano mai
divergere, esiste un test pgTAP che asserisce:

> l'insieme delle righe con `motivo = NULL` **coincide** con l'output di
> `fn_list_ddt_da_pushare`.

`test-fn-available-actions-ddt-reason-catch-all-v1.sql` (test 1). Se qualcuno
modifica l'eleggibilità in una sola delle due funzioni, il test diventa rosso e
forza l'allineamento: è così che «fonte unica» resta vero nel tempo senza dover
fisicamente fondere le due funzioni.

---

### Input / Output

- **Input**: `p_ddt_id` (opzionale). Se valorizzato, diagnostica solo quel DDT
  (uso tipico della capability). Se `NULL`, tutte le righe DDT del sistema (uso
  del test di equivalenza).
- **Output**: una riga per ogni riga DDT considerata — `ddt_id`, `riga_id`,
  `motivo_rank` (`NULL` se eleggibile), `motivo` (`NULL` se eleggibile).

---

### Consumatori

- [`script.fn_available_actions_ddt`](/dbzero/script/funzioni/fn_available_actions_ddt)
  — prende il motivo a rank minimo fra le righe del DDT e lo mappa alla `reason` +
  chiave i18n del tooltip «invia a commessa».

---

> **Brief**: `brief-db-ddt-reason-push-catch-all.md` §3 (Decisione A).
> **Changeset**: `20260719-15` (questa funzione), `20260719-16` (capability).
