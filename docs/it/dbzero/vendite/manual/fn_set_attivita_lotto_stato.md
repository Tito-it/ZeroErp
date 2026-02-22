## 📘 Documentazione Concettuale – Funzione `vendite.fn_set_attivita_lotto_stato`

> 👀 **Vedi anche**
>
> • [vendite.fn_sync_attivita_stato_esecuzione](/dbzero/vendite/funzioni/fn_sync_attivita_stato_esecuzione)  
>
---

### 🎯 Scopo Principale

(latest review 22-02-2026)
Aggiorna lo stato tecnico del lotto attività (`stato_lotto`) e allinea lo stato operativo (`stato_operativo`), sincronizzando anche `stato_esecuzione` sulle attività collegate.

---

### 🔧 Regole applicate

* Transizioni ammesse:
  * `IN_ESECUZIONE -> COMPLETATO|ERRORE`
  * `ERRORE -> IN_ESECUZIONE`
  * `COMPLETATO -> IN_ESECUZIONE`
* Mapping stato operativo:
  * `IN_ESECUZIONE -> APERTO`
  * `COMPLETATO -> CHIUSO`
  * `ERRORE -> ERRORE`
* A fine aggiornamento invoca `fn_sync_attivita_stato_esecuzione`.

---

### ✅ Output

Non ritorna record (`RETURNS void`).

---

{% include-markdown "signature-core.md" %}
