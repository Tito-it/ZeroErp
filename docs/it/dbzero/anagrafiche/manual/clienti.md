## 📘 Documentazione Concettuale – Tabella `anagrafiche.clienti`


> 👀 **Vedi anche**
>
> Guide generali:
>
>  * [Generazione di un cliente](/guide/generazione-cliente)
>
> Approfondimento tabelle:
>
>   * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities)
>   * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)
>   * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)
>   * [config.modalita_pagamento](/dbzero/config/tabelle/modalita_pagamento)
>   * [config.stati_cliente](/dbzero/config/tabelle/stati_cliente)
>   * [config.iva](/dbzero/config/tabelle/iva)
>   * [config.utilities](/dbzero/config/tabelle/utilities)
>
> Approfondimeto funzioni:
>
> * [script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)
> * [script.trgfn_upd_dlt_storico_generic](/dbzero/script/funzioni/trgfn_upd_dlt_storico_generic)
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice)
> * [dbops.trgfn_tx_id_managed](/dbzero/dbops/funzioni/trgfn_tx_id_managed)


---

### 🎯 Scopo Principale

La tabella `anagrafiche.clienti` memorizza le informazioni contrattuali e di fatturazione di un soggetto per una specifica *istanza* di servizio. Rappresenta la fase in cui un'attivazione (istanza) diventa un cliente ufficiale, includendo dettagli di scadenze, pagamento e classificazioni speciali (PA, split payment).

---

### 🔗 Collegamenti con Altre Tabelle

| Campo                   | Tabella di riferimento              | Azione                                |
| ----------------------- | ----------------------------------- | ------------------------------------- |
| `istanza_utility_id`    | `anagrafiche.istanze_utilities(id)` | ON UPDATE CASCADE, ON DELETE SET NULL |
| `soggetto_ruolo_id`     | `anagrafiche.soggetti_ruoli(id)`    | ON UPDATE CASCADE, ON DELETE RESTRICT |
| `modalita_pagamento_id` | `config.modalita_pagamento(id)`     | ON UPDATE CASCADE, ON DELETE SET NULL |
| `stato_cliente_id`      | `config.stati_cliente(id)`          | ON UPDATE CASCADE, ON DELETE RESTRICT |
| `iva_id`                | `config.iva(id)`                    | ON UPDATE CASCADE, ON DELETE RESTRICT |
| `utility_id`            | `config.utilities(id)`              | ON UPDATE CASCADE, ON DELETE RESTRICT |

---

### 🚩 Regole di Validazione Condizionale

1. **Tipo giorni scadenza (`tipo_gg_scadenza_ft`)**
   Valori ammessi: `G`, `F`, `N`, `M`.

2. **Numero giorni scadenza (`nr_giorni_scadenza`)**

   * Se `tipo_gg_scadenza_ft` = `G` o `F`, **`nr_giorni_scadenza` > 0**.
   * Se `tipo_gg_scadenza_ft` = `N` o `M`, **`nr_giorni_scadenza` = 0**.

3. **Cliente PA (`cliente_pa`)**
   Valori ammessi: `S` (Pubblica Amministrazione), `N` (Privato).

4. **Split payment (`split_payment`)**
   Valori ammessi: `S`, `N`.

5. **Servizio da fatturare (`servizio_da_fatturare`)**
   Valori ammessi: `true`, `false`.

---



---

### 💡 Vantaggi Operativi

* **Univocità del collegamento** tra cliente e istanza, garantita da `istanza_utility_id NOT NULL`.
* **Flessibilità di fatturazione**: possibilità di gestire PA, split payment e modalità diverse.
* **Validazioni integrate** riducono errori in fase di inserimento.

---

### ⚙️ Implementazioni Aggiuntive

* Può essere estesa con **campi di contratto** specifici (es. durata, condizioni).
* I trigger di audit (`trg_upd_clienti_audit_data_user`) mantengono traccia di modifiche.

---

### ✅ Controlli di Coerenza

* **Obbligatorietà** di `istanza_utility_id`, garantisce che ogni cliente derivi da una specifica istanza di servizio.
* **FK e check** impediscono dati fuori standard e assicurano integrità referenziale.

---

### 🧾 Note Finali

* La tabella `clienti` è il **fulcro** della logica di fatturazione: garantisce il passaggio dalla fase precontrattuale (istanza) alla fase contrattuale.
* Il cliente **assume lo stesso** `billing_account` generato in fase di istanza, mantenendo continuità nelle relazioni.

---

###  Diagramma ER relazioni

```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    istanze_utilities ||--o{ clienti : has
    soggetti_ruoli    ||--o{ clienti : has
    utilities         ||--o{ clienti : for
    stati_cliente     ||--o{ clienti : status_of
    iva               ||--o{ clienti : vat_of
    modalita_pagamento||--o{ clienti : pays_with

    istanze_utilities   { int id PK }
    soggetti_ruoli      { int id PK }
    utilities           { int id PK }
    stati_cliente       { int id PK }
    iva                 { int id PK }
    modalita_pagamento  { int id PK }
    clienti             { int id PK }
```

---

###  Diagramma ER attributi

```mermaid
%%{init: {'er': {'layoutDirection': 'TB'}}}%%
erDiagram
    clienti {
        int       id PK
        int       soggetto_ruolo_id FK
        int       istanza_utility_id FK
        char      tipo_gg_scadenza_ft
        int       nr_giorni_scadenza
        int       modalita_pagamento_id FK
        char      cliente_pa
        varchar   codice_cig
        varchar   codice_cup
        varchar   cod_commessa
        char      split_payment
        varchar   cd_cliente_importato
        int       stato_cliente_id FK
        int       iva_id FK
        bool      servizio_da_fatturare
        int       utility_id FK
        uuid      tx_id
        bool      storicizza
        datetime  data_insert
        varchar   user_insert
        datetime  data_update
        varchar   user_update
    }
```

---

{% include-markdown "signature-core.md" %}

---
