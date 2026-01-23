## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_emittenti_fiscali_default_guard()`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**    
>
> • [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)    
>

---

### 🎯 Scopo Principale

La funzione `anagrafiche.trgfn_emittenti_fiscali_default_guard()` garantisce che
esista **esattamente un** emittente fiscale di default.

E` eseguita da un trigger **DEFERRABLE** su `anagrafiche.emittenti_fiscali_billing_account`
per validare la coerenza **a fine transazione**.

---

### ✅ Regola applicata

* Il conteggio delle righe con `is_default = true` deve essere **pari a 1**.
* In caso contrario, la funzione logga e blocca tramite `script.fn_log_and_raise_error(...)`.

---

### 🧠 Perche` e` importante

Il default globale e` la **garanzia di fallback** quando un billing account non ha
associazione specifica. Senza questo vincolo, il processo di fatturazione
puo` diventare non deterministico.

---

{% include-markdown "signature-core.md" %}
