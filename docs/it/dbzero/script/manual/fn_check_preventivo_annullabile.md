## 📘 Documentazione Concettuale – Funzione `script.fn_check_preventivo_annullabile`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.preventivi](/dbzero/vendite/tabelle/preventivi) — il documento di cui si chiede l'annullo
> * [vendite.ordini](/dbzero/vendite/tabelle/ordini) — gli ordini che dichiarano di nascere dal preventivo
> * [config.stati_doc_ordini](/dbzero/config/tabelle/stati_doc_ordini) — `is_abortito`, che dice quali ordini non contano più
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_preventivi_guard_annullamento](/dbzero/vendite/funzioni/trgfn_preventivi_guard_annullamento) — il guard che solleva il primo motivo
> * [vendite.fn_cambia_stato_preventivo](/dbzero/vendite/funzioni/fn_cambia_stato_preventivo) — la porta dei passaggi di stato, che la chiama
> * [vendite.fn_annulla_preventivo](/dbzero/vendite/funzioni/fn_annulla_preventivo) — il verbo di annullo, che ritira le righe di commessa non emesse
> * [script.fn_check_sorgente_chiudibile](/dbzero/script/funzioni/fn_check_sorgente_chiudibile) — chi conta le righe già emesse in commessa
> * [script.fn_check_ordine_annullabile](/dbzero/script/funzioni/fn_check_ordine_annullabile) — la regola gemella dell'ordine
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — come un ordine dichiara di nascere da un preventivo

---

### 🎯 Scopo Principale

Elenca i motivi che impediscono di **annullare** un preventivo: un ordine vivo già nato da esso,
oppure righe già **emesse** in commessa. È la sede unica della regola: la leggono il guard
dell'annullo, la porta dei passaggi di stato e la capability del preventivo.

---

### I due motivi, in ordine di gravità

1. **Un ordine è già nato dal preventivo** (`E_PREV_ORDINE_GIA_GENERATO`). L'ordine nato dal
   preventivo è quello che lo dichiara come provenienza: tipo `PREVENTIVO` e la chiave del
   preventivo, secondo il modello della sorgente polimorfa. Il motivo porta il numero degli ordini.
2. **Righe già emesse in commessa** (`E_PREV_ANNULLA_COMMESSA_EMESSA`): a valle c'è già un
   documento fiscale. Il conteggio non si fa qui: lo fa `script.fn_check_sorgente_chiudibile`, la
   stessa condizione di tutti gli altri documenti, e qui il motivo si **rietichetta** col codice
   proprio del preventivo, che il frontend già conosce. Una implementazione, due superfici.

⚠️ È anche il motivo per cui sui preventivi **non** si monta il guard generico delle righe emesse:
lo stesso rifiuto uscirebbe con due codici diversi, a seconda di quale trigger parla per primo.

Le righe di commessa **non** ancora emesse non bloccano: sono legami, e all'annullo il verbo li
ritira, dopo aver chiesto conferma.

---

### ⚠️ Gli ordini annullati non bloccano

Il conteggio esclude gli ordini il cui stato è `is_abortito`: altrimenti un documento morto
bloccherebbe il padre per sempre, senza via d'uscita. **Qualunque altro stato blocca, bozza
compresa**: la via d'uscita per un ordine in bozza è abbandonarlo prima.

Il predicato usa `is_abortito` e non il codice dello stato: è l'asse uniforme fra i cataloghi, e non
si rompe se un dominio chiama diversamente il proprio stato terminale.

---

### Il pattern `fn_check_*`

**Funzione pura**: nessuna scrittura, nessun errore di dominio. Restituisce un elenco vuoto se
l'annullo è permesso, altrimenti i motivi in ordine di gravità, ognuno col codice, il motivo, la
chiave di traduzione e il dettaglio: chi solleva prende il **primo**.

⭐ È la **sorgente unica** per il guard di transizione, che solleva, e per la capability, che spegne
l'azione col motivo: il pulsante e il rifiuto del database non possono divergere, perché leggono
lo stesso verdetto.

⚠️ Unica eccezione alla purezza: un identificativo nullo o non positivo solleva
`E_PARAMETRO_INVALIDO`, che è un errore di programmazione e non una condizione di dominio.

⚠️ **Un preventivo inesistente non ha motivi.** La funzione non distingue «annullabile» da «non
esiste»: decide il chiamante. Nel percorso reale il guard gira sull'aggiornamento di una riga che
esiste per definizione, quindi il caso non si presenta, ma chi la chiamasse da fuori quel percorso
deve saperlo.

---

### Codici errore

* `E_PREV_ORDINE_GIA_GENERATO` — esiste un ordine vivo nato dal preventivo (motivo, non sollevato
  qui).
* `E_PREV_ANNULLA_COMMESSA_EMESSA` — righe già emesse in commessa (motivo, non sollevato qui).
* `E_PARAMETRO_INVALIDO` — identificativo del preventivo nullo o non positivo (sollevato).

---

### Test

* `db/pgtap/vendite/test-sorgente-testate-ordini-contratti-v1.sql` — il preventivo con un ordine
  vivo nato da lui, riconosciuto dalla provenienza, non si annulla.
* `db/pgtap/script/test-capability-motivi-e-nessuna-azione-v1.sql` — l'azione della capability è
  accesa esattamente quando la funzione non ha motivi.

---

### Note di migrazione

* 2026-08-04 — assorbe il controllo delle righe emesse in commessa, che prima viveva dentro la porta
  dei passaggi di stato (`brief-db-vie-uscita-operatore`).
* 2026-08-10 — gli ordini annullati smettono di contare.
* 2026-08-21 — il primo motivo non era mai scattato: cercava l'ordine su `ordini.sorgente_uid`, che
  allora era l'origine «import» e nessuno scriveva, mentre il legame vero stava nella coppia
  `documento_origine_tipo` / `documento_origine_id`. Passa a quella coppia.
* 2026-08-26 — si ritira il motivo `E_PREV_GIA_IN_COMMESSA` («il preventivo è entrato in commessa,
  anche se nulla è ancora uscito»): esisteva perché il push non si poteva disfare, e ora le righe non
  emesse si ritirano all'annullo. Il codice resta a catalogo con `obsoleto_dal`. Lo stesso giorno il
  conteggio delle righe emesse passa a `script.fn_check_sorgente_chiudibile`, sulla provenienza
  dichiarata invece che su un prefisso del `segment_key` (`brief-db-lavoro-che-non-torna-indietro`).
* 2026-11-06 — l'ordine nato dal preventivo si cerca dalla sua provenienza del modello
  (`sorgente_tipo_id` con la chiave del preventivo), come per i DDT: le colonne `sorgente_*`
  dell'ordine diventano la sua provenienza, e la coppia parallela `documento_origine_*` si ritira
  (`brief-db-sorgente-documento-e-riga`).

---

{% include-markdown "signature-core.md" %}
