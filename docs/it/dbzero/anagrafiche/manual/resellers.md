## 📘 Documentazione Concettuale – Tabella `anagrafiche.resellers`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)  
> • [anagrafiche.resellers_billing_account](/dbzero/anagrafiche/manual/resellers_billing_account)  
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
>
🎯 Scopo Principale

(latest review 26-01-2026)
`anagrafiche.resellers` rappresenta l’anagrafica dei **reseller** disponibili nel sistema.
Ogni reseller e` un ruolo (`soggetti_ruoli`) che puo` essere collegato a uno o piu`
**billing_account** tramite la tabella di mapping dedicata.

---

### Ruolo nel processo

* Abilita la gestione di **canali di vendita indiretti**.
* Consente aggregazioni o filtri di fatturazione per reseller.
* Supporta scenari con piu` entita` commerciali che intermediano la vendita.

---

### Regola di collegamento

* Il reseller **non** ha un default globale.
* L’associazione e` sempre esplicita e passa da
  `anagrafiche.resellers_billing_account` (con validita` temporale).

---

### Best practice operative

* Mantenere i reseller **attivi** solo se effettivamente utilizzati.
* Agganciare il reseller al billing account tramite mapping con periodo valido.

---

### Vincoli applicativi (attivo)

* Un reseller **non puo` essere disattivato** se esistono mapping
  in `resellers_billing_account` collegati al suo `soggetto_ruolo_id`.
* Questo vincolo evita di lasciare mapping orfani.

---

{% include-markdown "signature-core.md" %}
