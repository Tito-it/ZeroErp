## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_attivita_fatturabili_guard_commessa()`

> 👀 **Vedi anche**
>
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)  

---

### 🎯 Scopo Principale

(latest review 24-02-2026)  
La funzione trigger `vendite.trgfn_attivita_fatturabili_guard_commessa()` applica
il guardrail anti-bypass sul dominio `attivita_fatturabili`, impedendo scritture
senza collegamento commessa quando il flag è attivo.

---

### ✅ Regole applicate

* flag funzionale su `config.parameters`:
  * `code='attivita_fatturabili_require_commessa'`
  * `default_value=true|false`
* bypass manutenzione opzionale via GUC:
  * `zeroerp.maintenance_allow_attivita_bypass=true`
* quando il guardrail è attivo:
  * `commessa_id` e `commessa_attivita_id` devono essere valorizzati a coppia;
  * non è consentita la pair vuota (`NULL/NULL`);
  * `commessa_attivita_id` deve esistere;
  * `commessa_attivita_id` deve appartenere alla `commessa_id` indicata.

---

### 🧩 Obiettivo operativo

Rendere obbligatorio il passaggio `commessa -> attivita_fatturabili`
ed evitare inserimenti/aggiornamenti diretti che aggirano il modello v2.

---

{% include-markdown "signature-core.md" %}
