## 📘 Documentazione Concettuale – Funzione `script.fn_doc_stato_iniziale_id(regclass)`

> 👀 **Vedi anche**
>
> [script.fn_stato_iniziale_id](/dbzero/script/funzioni/fn_stato_iniziale_id) ·
> [script.fn_stato_emissione_id](/dbzero/script/funzioni/fn_stato_emissione_id) ·
> [script.fn_stato_abortito_id](/dbzero/script/funzioni/fn_stato_abortito_id) ·
> [script.fn_doc_stato_modello](/dbzero/script/funzioni/fn_doc_stato_modello) ·
> guida [Il modello del documento di vendita](/guide/modello-documento-di-vendita) §4

### 🎯 Scopo
(27-10-2026 — brief `brief-modello-documento-vendita` §15.13, richiesta del team backend)

**Lo stato iniziale di un documento, a partire dal documento.** Lo stato in cui un documento
nasce lo dice il suo vocabolario degli stati, con la colonna `iniziale`, e lo legge
[`script.fn_stato_iniziale_id`](/dbzero/script/funzioni/fn_stato_iniziale_id), che però vuole
il vocabolario. Chi ha in mano il documento (per esempio il backend, quando «riporta in bozza»
un lotto di fatturazione) non deve sapere quale vocabolario gli corrisponde: chiede qui, con la
testata, e la funzione trova il vocabolario nella mappa del modello.

### Regole

* La regola resta una sola: questa funzione trova il vocabolario e chiede lo stato iniziale a
  `script.fn_stato_iniziale_id`.
* Vuoto se il vocabolario non dichiara uno stato iniziale.
* Una tabella fuori dalla mappa, o nessuna tabella: `E_SCRIPT_CHIAMATA_NON_VALIDA`.
* Gemella di [`script.fn_stato_emissione_id`](/dbzero/script/funzioni/fn_stato_emissione_id)
  e [`script.fn_stato_abortito_id`](/dbzero/script/funzioni/fn_stato_abortito_id), che
  ricevono anche loro la testata.

### Chi la legge

Il backend, per lo stato d'arrivo di «riporta in bozza» del lotto, e i builder dei test che
costruiscono un documento e lo portano avanti dallo stato in cui è nato. Chi ha il vocabolario
e non un documento della mappa resta su `script.fn_stato_iniziale_id`: il trigger della
nascita, che vale anche per i documenti d'acquisto, e il passaggio da preventivo a ordine, per
lo stato delle righe dell'ordine.
