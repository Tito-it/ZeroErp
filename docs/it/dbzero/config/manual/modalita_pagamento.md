## 📘 Documentazione Concettuale – Tabella `config.modalita_pagamento`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[config.condizioni_pagamento](/dbzero/config/tabelle/condizioni_pagamento)
> [vendite.fatture_testata](/dbzero/vendite/tabelle/fatture_testata)
> [vendite.ddt_testata](/dbzero/vendite/tabelle/ddt_testata)
>
Approfondimenti funzioni/trigger:
>
[script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)

---

La tabella **`config.modalita_pagamento`** contiene il **catalogo delle modalità di pagamento** utilizzabili nei documenti amministrativi e commerciali (fatture, note di credito, ordini, eventuali incassi), come ad esempio: **BONIFICO**, **RID**, **RIBA**, **CONTANTI**, **ASSEGNO**, ecc.

Rappresenta un dominio centrale, da combinare con le condizioni di pagamento per definire come e con quali strumenti il cliente effettua il saldo dei documenti.

---
### 🎯 Scopo Principale
* Definire un elenco **normalizzato e univoco** delle modalità di pagamento disponibili nel sistema.
* Fornire un **codice interno stabile** (`codice`) utilizzabile in configurazioni, mapping e integrazioni.
* Supportare la definizione di **regole di incasso** e gestionali (es. tracciabilità, obbligo di IBAN, circuiti bancari).

---

### Vincoli e Regole Aziendali

* **Identificatore tecnico** (`id`):

  * chiave primaria intera (`PK`), generata automaticamente tramite identity.

* **Codice modalità pagamento** (`codice`):

  * campo `char(10)` univoco (`uq_modalita_pagamento_codice`);
  * rappresenta il **codice funzionale** utilizzabile in:

    * configurazioni di condizioni di pagamento;
    * mapping verso sistemi esterni (es. gestionale contabile, sistemi bancari);
    * logiche di reporting.

* **Descrizione** (`descrizione`):

  * obbligatoria, testo leggibile dagli operatori;
  * usata per combo, stampe (es. “Pagamento con bonifico bancario”), schermate di configurazione.

* **Audit**:

  * `data_insert`, `user_insert`: tracciano la creazione del record.
  * `data_update`, `user_update`: tracciano l’ultima modifica.
  * La coerenza di questi campi è garantita dal trigger `trg_modalita_pagamento_upd_audit_data_user_generic`.

> È buona pratica non cancellare fisicamente le modalità di pagamento utilizzate in documenti storici, ma eventualmente prevedere in futuro un flag di attivazione se necessario.

---

### Relazioni

`config.modalita_pagamento` viene utilizzata come dominio di base per:

* **Condizioni di pagamento**:

  * tabelle come `config.condizioni_pagamento` possono referenziare una o più modalità di pagamento per definire come avviene l’incasso (es. bonifico a 30 giorni, RID a 60 giorni).

* **Documenti di vendita**:

  * campi tipo `modalita_pagamento_id` in `vendite.fatture_testata` o in anagrafiche cliente per definire la **modalità predefinita** di incasso.

* **Processi di incasso / riconciliazione**:

  * le modalità di pagamento possono guidare regole specifiche di allineamento con estratti conto o flussi bancari.

---

### Trigger Associati

1. **`trg_modalita_pagamento_upd_audit_data_user_generic`**

   * **Quando**: `BEFORE UPDATE` sulla tabella `config.modalita_pagamento`.
   * **Cosa fa**:

     * aggiorna automaticamente `data_update` e `user_update` a ogni modifica del record.
   * **Come**:

     * invoca la funzione generica `script.trgfn_upd_audit_data_user_generic()`, che centralizza la logica di aggiornamento campi di audit su più tabelle.

> Questo garantisce che tutte le variazioni apportate alle modalità di pagamento siano sempre tracciate, semplificando audit e diagnostica.

---

### Vantaggi Operativi

* **Coerenza**: un unico catalogo di modalità di pagamento per tutti i moduli (vendite, contabilità, incassi).
* **Semplificazione delle configurazioni**: è possibile combinare la modalità con condizioni di pagamento, listini, profili cliente, ecc.
* **Tracciabilità**: grazie all’audit, ogni cambiamento di descrizione o codice è storicamente rintracciabile.
* **Integrazione**: la presenza di un codice univoco facilita il mapping con sistemi esterni (banche, contabilità generale, CRM).

---

> **“Centralizzare le modalità di pagamento è il primo passo per avere un ciclo attivo/crediti chiaro, configurabile e facilmente integrabile con i sistemi bancari e contabili.”**
