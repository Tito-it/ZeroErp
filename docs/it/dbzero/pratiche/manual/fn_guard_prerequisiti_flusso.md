## 📘 Documentazione Concettuale – Funzione `pratiche.fn_guard_prerequisiti_flusso`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.template_flussi_prerequisiti](/dbzero/pratiche/tabelle/template_flussi_prerequisiti) — i prerequisiti dichiarati
>
> Approfondimento funzioni:
>
> * [pratiche.fn_check_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso) — il controllo che dice prerequisito per prerequisito
> * [pratiche.trgfn_flussi_guard_prerequisiti](/dbzero/pratiche/funzioni/trgfn_flussi_guard_prerequisiti) — il trigger che la chiama all'inserimento di un flusso
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error) — registra e solleva l'errore

---

### 🎯 Scopo Principale

La funzione `pratiche.fn_guard_prerequisiti_flusso` è la versione bloccante del controllo dei
prerequisiti: se un passo della pratica non ha tutti i prerequisiti soddisfatti, solleva un errore.

---

### Come decide

Non riscrive la regola: chiede a `pratiche.fn_check_prerequisiti_flusso` l'esito di ogni prerequisito
del template per quella pratica, e se almeno uno non è soddisfatto solleva l'errore con l'elenco dei
codici mancanti. Se sono tutti soddisfatti non restituisce niente.

* La chiama il trigger `pratiche.trgfn_flussi_guard_prerequisiti` all'inserimento di ogni flusso: il
  template è obbligatorio, e non esiste un flusso che salti il controllo.
* Il backend può chiamarla prima di tentare l'inserimento, per avere lo stesso verdetto in anticipo.

---

### Codici errore

* `E_PRATICHE_PREREQUISITI_NON_SODDISFATTI` — almeno un prerequisito non è soddisfatto; il messaggio e
  il contesto portano i codici mancanti.

---

### Test

* `pratiche/test-fn-guard-prerequisiti-flusso` — l'errore sui prerequisiti mancanti e il passaggio
  quando sono soddisfatti.

---

{% include-markdown "signature-core.md" %}
