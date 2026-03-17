## 📘 Documentazione Concettuale – Tabella `vendite.fatture_arrotondamenti_scope`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  
> • [anagrafiche.utilities](/dbzero/anagrafiche/tabelle/utilities)  
> • [config.tipi_doc_fiscale](/dbzero/config/tabelle/tipi_doc_fiscale)  
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
> • [config.valute](/dbzero/config/tabelle/valute)  
>
🎯 Scopo Principale

(latest review 10-02-2026)  
`vendite.fatture_arrotondamenti_scope` memorizza il **saldo tecnico** degli
arrotondamenti per **ambito di fatturazione**. Serve a produrre arrotondamenti
deterministici e riproducibili tra fatture e note/storni, evitando
scostamenti cumulativi nel tempo.

---

### Chiave di ambito (univoca)

L'ambito e` definito dalla combinazione:

* `billing_account_id`
* `utility_id`
* `tipo_doc_fiscale_id`
* `emittente_soggetto_ruolo_id`
* `valuta_id`

Questa chiave permette di isolare correttamente gli arrotondamenti per
cliente/utility/tipo documento/emittente/valuta.

---

### 🧾 Campi chiave (semantica)

* **Saldo**: `saldo_arrotondamento` = saldo tecnico accumulato per l'ambito.
* **Governance**: audit standard per modifiche e tracciabilita`.

---

### Note operative

* Il saldo non e` un totale fiscale, ma un valore **tecnico** usato per
  determinare `arrotondamento_precedente` e `arrotondamento_attuale` in testata.
* L'ambito e` pensato per mantenere la coerenza tra fattura e storni/NC.
* L’aggiornamento del saldo deve avvenire **in modo deterministico** tramite
  funzioni dedicate (get/set), evitando aggiornamenti manuali.

---

{% include-markdown "signature-core.md" %}
