## 📘 Documentazione Concettuale – Funzione `anagrafiche.trgfn_emittenti_fiscali_default_bootstrap()`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**    
>
> • [anagrafiche.emittenti_fiscali](/dbzero/anagrafiche/manual/emittenti_fiscali)    
> • [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)    
>

---

### 🎯 Scopo Principale

(latest review 23-01-2026)
La funzione `anagrafiche.trgfn_emittenti_fiscali_default_bootstrap()` crea in modo automatico
la **riga di default** nel mapping emittenti fiscali quando viene inserito il **primo emittente**.

L’obiettivo e` evitare configurazioni incomplete che renderebbero la fatturazione non deterministica.

---

### ✅ Regola applicata

* Se non esiste alcuna riga `is_default = true` in
  `anagrafiche.emittenti_fiscali_billing_account`, la funzione inserisce:
  * `billing_account_id = NULL`
  * `emittente_soggetto_ruolo_id = NEW.soggetto_ruolo_id`
  * `is_default = true`

---

### 🧠 Motivazioni

* Garantire che **esista sempre un default** utilizzabile in assenza di mapping specifici.
* Ridurre l’onere di configurazione iniziale (soprattutto con un solo emittente).
* Evitare errori a runtime nel processo di fatturazione.

---

{% include-markdown "signature-core.md" %}
