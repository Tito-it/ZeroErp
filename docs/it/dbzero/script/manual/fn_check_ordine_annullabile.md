## 📘 Documentazione Concettuale – Funzione `script.fn_check_ordine_annullabile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — il documento di cui si chiede l'annullamento
> * [vendite.ddt](/dbzero/vendite/tabelle/ddt) — le bolle figlie, che portano l'ordine nella provenienza
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe di commessa spinte dall'ordine
>
> Approfondimento funzioni:
>
> * [script.fn_check_sorgente_chiudibile](/dbzero/script/funzioni/fn_check_sorgente_chiudibile) — la primitiva a cui delega il motivo delle righe emesse
> * [script.fn_check_preventivo_annullabile](/dbzero/script/funzioni/fn_check_preventivo_annullabile) — la gemella, sul preventivo
> * [vendite.trgfn_ordini_guard_transizione](/dbzero/vendite/funzioni/trgfn_ordini_guard_transizione) — il guard che ne solleva il primo motivo
> * [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — il verbo che all'annullo ritira le righe non emesse
> * [vendite.fn_riporta_attivita_da_emettere](/dbzero/vendite/funzioni/fn_riporta_attivita_da_emettere) — la via d'uscita per le righe emesse
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza: tipo, documento, riga

---

### 🎯 Scopo Principale

Elenca i motivi che impediscono di **annullare** un ordine: merce già uscita con una bolla figlia viva,
oppure righe di commessa già `EMESSA`. Un elenco vuoto vuol dire che l'annullamento è lecito.

---

### I due motivi

1. **Una bolla figlia viva** (`E_ORD_ANNULLA_CON_DDT`): la merce è già uscita.
2. **Righe di commessa già `EMESSA`** (`E_SORGENTE_CON_RIGHE_EMESSE`): sono in volo verso una fattura.
   Il conteggio non si scrive qui: si delega a `script.fn_check_sorgente_chiudibile`, la stessa che il
   guard generico della chiusura usa. *Una implementazione, due superfici*: questa accende il
   pulsante, quella ferma la scrittura. I motivi della primitiva arrivano già fatti, valori compresi,
   e non si ricompongono.

⭐ Le righe `NON_EMESSA` **non bloccano**: sono legami, l'annullo chiede conferma e il verbo di annullo
le ritira (`vendite.fn_documento_ritira_legami`). Per le righe emesse la via d'uscita c'è, e il
messaggio la nomina: «Riporta da emettere» le riporta a `NON_EMESSA`, e da lì il ritiro le prende.

---

### ⭐ L'ordine si cerca nella provenienza, con le due chiavi

Sia la bolla figlia sia la riga di commessa dicono di nascere dall'ordine con le colonne del modello
della provenienza: il tipo `ORDINE_VENDITA` e la chiave dell'ordine. L'ordine si riconosce dall'id
(il `key_selector` del tipo), quindi la chiave sta in `sorgente_id`.

La funzione cerca con la **regola d'incontro**: vale una provenienza il cui `sorgente_id` è l'id
dell'ordine **oppure** il cui `sorgente_uid` è il suo uid, e alla primitiva passa tutte e due le
chiavi. È la stessa regola della gemella sul preventivo, che cerca gli ordini nati dal preventivo
nella loro provenienza.

⛔ **Una chiave sbagliata non dà un errore: dà zero motivi**, cioè un freno che lascia passare tutto.
Per questo si passano le chiavi del documento, e non se ne sceglie una per simmetria.

---

### Le bolle annullate non contano, quelle rese sì

Una bolla **annullata** non blocca: un figlio morto non deve tenere fermo il padre per sempre e senza
uscita. Il predicato è l'asse uniforme degli stati, `is_abortito`, non il codice dello stato.

⚠️ Esclude **solo** l'annullata. Una bolla in stato `RESO` ha `is_abortito` falso e continua a
bloccare, ed è giusto: la merce è tornata, ma il documento è vissuto.

⭐ Annullare una bolla è un fatto ordinario dell'esercizio (destinatario sbagliato, merce sbagliata,
un duplicato): un ordine il cui unico figlio fosse stato annullato, contato fra i bloccanti,
resterebbe fermo per sempre. La domanda da farsi davanti a una misura che dice «non succede» è
*«può succedere?»*, non *«è successo?»*.

---

### Il pattern `fn_check_*`

**Funzione pura**: `STABLE`, nessuna scrittura, nessun errore di dominio. Ritorna l'elenco dei motivi
in ordine di gravità; chi solleva prende il primo.

⭐ **Sorgente unica** per il guard di transizione (che solleva) e per `script.fn_available_actions_ordine`
(che espone il pulsante spento e i motivi): il pulsante dell'interfaccia e il rifiuto del database
non possono divergere, perché leggono lo stesso verdetto.

⚠️ Unica eccezione alla purezza: un id vuoto o non positivo solleva `E_PARAMETRO_INVALIDO`, errore di
programmazione e non condizione di dominio.

⚠️ **Ordine inesistente vuol dire nessun ostacolo.** La funzione non distingue «annullabile» da «non
esiste»: decide il chiamante. Nel percorso reale il guard gira sull'aggiornamento di una riga che
esiste, quindi il caso non si presenta; chi la chiama da fuori quel percorso deve saperlo.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_ORD_ANNULLA_CON_DDT` | esiste una bolla figlia viva |
| `E_SORGENTE_CON_RIGHE_EMESSE` | ci sono righe di commessa già `EMESSA` (dalla primitiva) |
| `E_PARAMETRO_INVALIDO` | l'id dell'ordine è vuoto o non positivo (sollevato) |

`E_ORD_ANNULLA_IN_COMMESSA` resta a catalogo con `obsoleto_dal` e non viene più sollevato.

---

### Test

* `db/pgtap/vendite/test-ordini-guard-transizione-v1.sql` — il guard di transizione che solleva il
  primo motivo.
* `db/pgtap/vendite/test-ritiro-commessa-attivita-da-sorgente-v1.sql` — il motivo delle righe emesse.
* `db/pgtap/vendite/test-sorgente-testate-due-grammatiche-v1.sql` — la bolla figlia trovata con la
  chiave del modello.
* `db/pgtap/script/test-capability-motivi-e-nessuna-azione-v1.sql` e
  `db/pgtap/script/test-rubinetto-primo-motivo-v1.sql` — i motivi nella capability e il primo nel guard.

---

### Note di migrazione

* 2026-08-15 — le bolle annullate smettono di contare fra i figli che bloccano, come sul preventivo
  dal 2026-08-10.
* 2026-08-26 — `E_ORD_ANNULLA_IN_COMMESSA` si ritira: vietava di annullare un ordine che aveva spinto
  in commessa perché il push non si poteva disfare, e ora alla chiusura il documento ritira le righe
  non emesse. Il motivo delle righe emesse passa alla primitiva `script.fn_check_sorgente_chiudibile`
  (`brief-db-lavoro-che-non-torna-indietro`).
* 2026-11-06 e 2026-11-07 — la bolla figlia e le righe di commessa si cercano nella provenienza del
  modello, con l'id e l'uid dell'ordine; prima la bolla portava l'uid dell'ordine e la riga di commessa
  la chiave in testo (`brief-db-sorgente-documento-e-riga`).

---
{% include-markdown "signature-core.md" %}
