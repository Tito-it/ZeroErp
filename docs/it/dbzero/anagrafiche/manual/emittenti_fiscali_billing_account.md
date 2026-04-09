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
(latest review 08-04-2026)
La tabella `anagrafiche.emittenti_fiscali_billing_account` definisce l’associazione tra **billing account**
e **emittente fiscale** (ruolo), garantendo che ogni documento abbia un emittente coerente e deterministico.

Il modello prevede un **emittente di default globale** che, dopo il refactor del 2026-04-08, agisce come
**rete di sicurezza** per i casi residui (seed/bootstrap, scenari "0 emittenti"), mentre il caso normale
prevede che ogni BA venga **auto‑collegato** all'emittente dell'operatore che lo crea, tramite il trigger
[`trgfn_billing_account_link_ef`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_link_ef) sulla tabella
`billing_account`. Vedi [refactor operatore ↔ emittente](/dev/work-in-progress/refactor-operatore-emittenti).

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

* Inserire sempre un **emittente di default** appena si abilita il modulo fatturazione (rete di sicurezza per BA non auto‑collegati).
* Dopo il refactor 2026-04-08, i mapping specifici per BA vengono **creati automaticamente** alla creazione del BA dal trigger di auto‑link, basandosi sull'emittente dell'operatore corrente. Non serve più popolarli manualmente.
* L'admin globale **non può** creare BA quando esistono emittenti fiscali attivi (vincolo a livello DB tramite [`trgfn_billing_account_guard_admin_globale`](/dbzero/anagrafiche/funzioni/trgfn_billing_account_guard_admin_globale)). Per creare un BA, occorre operare come operatore o admin di emittente.

---

{% include-markdown "signature-core.md" %}
