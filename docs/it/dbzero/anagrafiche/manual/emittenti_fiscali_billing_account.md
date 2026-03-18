## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali_billing_account`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**    
>
• [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)    
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)    
>
### 🎯 Scopo Principale
(latest review 23-01-2026)
La tabella `anagrafiche.emittenti_fiscali_billing_account` definisce l’associazione tra **billing account**
e **emittente fiscale** (ruolo), garantendo che ogni documento abbia un emittente coerente e deterministico.

Il modello prevede un **emittente di default globale** utilizzato quando non esiste una
associazione specifica per il billing account.

---

### Regole principali

* **Unicita` per billing account**: una sola riga per `billing_account_id`.
* **Default globale**:
  * `is_default = true` ammesso **una sola volta**.
  * la riga di default ha `billing_account_id` **NULL**.
* **Coerenza**:
  * se esiste una riga specifica per BA, essa prevale sul default.
  * in assenza di mapping, si usa il default.

---

### Collocazione nel processo di fatturazione

1. Durante la generazione delle fatture, l’emittente fiscale viene risolto tramite questa tabella.
2. Se non esiste un mapping specifico per il BA, viene applicato il default globale.
3. Questo garantisce coerenza e riduce la configurazione manuale quando l’emittente e` unico.

---

### Best practice operative

* Inserire sempre un **emittente di default** appena si abilita il modulo fatturazione.
* Creare mapping specifici per BA solo quando necessario (multi‑emittente).

---

{% include-markdown "signature-core.md" %}
