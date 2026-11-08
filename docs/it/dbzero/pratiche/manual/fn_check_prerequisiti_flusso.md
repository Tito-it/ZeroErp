## 📘 Documentazione Concettuale – Funzione `pratiche.fn_check_prerequisiti_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) — i prerequisiti di un template, con l'esito richiesto
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — il codice e la descrizione del prerequisito
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — i passi della pratica che lo soddisfano
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — lo stato `COMPLETATO`
>
> Approfondimento funzioni:
>
> * [pratiche.fn_guard_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_guard_prerequisiti_flusso) — la versione bloccante

---

### 🎯 Scopo Principale

La funzione `pratiche.fn_check_prerequisiti_flusso` dice, per una pratica e un template di flusso, se
ciascun prerequisito del template è soddisfatto: una riga per prerequisito, con il flag `soddisfatto`.

Non solleva errori: è il chiamante a decidere che cosa fare dei prerequisiti mancanti.

---

### Quando un prerequisito è soddisfatto

Un prerequisito è un altro template di flusso. È soddisfatto quando nella stessa pratica esiste
almeno un flusso di quel template in stato `COMPLETATO` **con l'esito giusto**:

* se il prerequisito dichiara un `esito_richiesto`, l'esito del flusso deve coincidere;
* se non lo dichiara, vale qualunque esito.

Un template senza prerequisiti non restituisce nessuna riga: nessun prerequisito vuol dire tutti
soddisfatti.

La funzione è `STABLE`, sola lettura; la usa `pratiche.fn_guard_prerequisiti_flusso` per il controllo
bloccante.

---

### Test

* `pratiche/test-fn-check-prerequisiti-flusso` — i prerequisiti soddisfatti e mancanti.
* `pratiche/test-prerequisiti-esito-aware` — un prerequisito completato con l'esito sbagliato non
  soddisfa; senza esito richiesto vale qualunque esito.

---

### Note di migrazione

* 2026-06-08 — il controllo tiene conto dell'esito del flusso prerequisito (`esito_richiesto`); prima
  bastava che fosse completato.

---

{% include-markdown "signature-core.md" %}
