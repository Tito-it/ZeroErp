## 📘 Documentazione Concettuale – Tabella `anagrafiche.emittenti_fiscali`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**    
>
> • [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    
> • [anagrafiche.emittenti_fiscali_billing_account](/dbzero/anagrafiche/manual/emittenti_fiscali_billing_account)    
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)    
>

---

### 🎯 Scopo Principale

(last review)
`anagrafiche.emittenti_fiscali` rappresenta l’anagrafica **degli emittenti fiscali** disponibili
nel sistema. Ogni emittente e` un ruolo (`soggetti_ruoli`) con dati fiscali e configurazioni
utili al ciclo di fatturazione.

Questa tabella **non** definisce il default per i billing account: la scelta dell’emittente
avviene tramite la tabella di mapping `anagrafiche.emittenti_fiscali_billing_account`.

---

### 🧱 Ruolo nel processo

* Fornisce l’**identita` fiscale** che compare nei documenti.
* Consente la gestione **multi‑emittente** (piu` soggetti emittenti nello stesso gestionale).
* Centralizza regole e parametri fiscali legati all’emittente.

---

### 🔗 Regola di selezione (richiamo)

* L’emittente **effettivo** per una fattura e` risolto dal mapping
  `billing_account → emittente fiscale`.
* Se non esiste un mapping specifico, si usa l’emittente **di default globale**
  definito nel mapping (non in questa tabella).

---

### ✅ Best practice operative

* Popolare questa tabella con **tutti gli emittenti fiscali** gestiti dal sistema.
* Mantenere il mapping separato per garantire flessibilita` e fallback.
* Deve esistere **almeno un emittente fiscale**: alla creazione del primo viene generato
  automaticamente il default nel mapping con `billing_account_id = NULL`.

---

{% include-markdown "signature-core.md" %}
