## 📘 Documentazione Concettuale – Trigger function `pratiche.trgfn_flussi_guard_esito_completato`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — la tabella che il guard presidia
> * [config.stati_flussi_pratiche](/dbzero/config/tabelle/stati_flussi_pratiche) — lo stato `COMPLETATO`
> * [config.esiti_flussi_pratiche](/dbzero/config/tabelle/esiti_flussi_pratiche) — il vocabolario degli esiti
>
> Approfondimento funzioni:
>
> * [pratiche.trgfn_flussi_guard_esito_classe](/dbzero/pratiche/funzioni/trgfn_flussi_guard_esito_classe) — il guard che, sullo stesso momento, controlla la classe dell'esito
> * [config.trgfn_stati_doc_guard_esito_verdetto](/dbzero/config/funzioni/trgfn_stati_doc_guard_esito_verdetto) — il guard gemello sugli stati dei documenti
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva gli errori

---

### 🎯 Scopo Principale

La trigger function `pratiche.trgfn_flussi_guard_esito_completato` impedisce che un flusso di pratica
passi allo stato `COMPLETATO` senza un `esito`: nessuna fase si chiude senza verdetto.

Lo stato dice dove si è arrivati, l'esito com'è andata. Un flusso completato senza esito sarebbe una
fase chiusa di cui nessuno sa il risultato, e a valle non ci sarebbe modo di ricostruirlo: il verdetto
non si deriva dallo stato.

---

### La regola

Il guard blocca quando l'esito è vuoto **e** il nuovo stato è quello con codice interno `COMPLETATO`.
Lo stato si riconosce per codice interno, non per id: la matrice degli stati resta configurazione, e il
guard non ne fotografa nessuna chiave tecnica.

Scatta all'inserimento e quando cambia `stato_id`.

---

### ⚠️ Il guard scatta sullo stato, non sull'esito

Svuotare l'esito di un flusso già completato non fa scattare il guard: la regola è presidiata al
momento della chiusura, non in permanenza. Se servisse anche l'immutabilità dell'esito a valle, andrebbe
aggiunta a parte: questo guard non la copre.

---

### Rapporto con il guard gemello di `config`

`config.trgfn_stati_doc_guard_esito_verdetto` presidia un asse diverso: che l'esito usato come
proiezione di uno stato documento sia un vero verdetto. I due si completano:

* **qui**: chiudere un flusso vuol dire avere un esito;
* **là**: un esito usato come proiezione dev'essere un verdetto.

---

### Codici errore

* `E_FLUSSI_ESITO_OBBLIGATORIO` — stato portato a `COMPLETATO` con l'esito vuoto. L'errore porta il
  `tx_id` della riga, ed è correlabile alla transazione applicativa che l'ha causato.

---

### Test

* `pratiche/test-trigger-guard-flussi` — la chiusura di un flusso senza esito è rifiutata.

---

{% include-markdown "signature-core.md" %}
