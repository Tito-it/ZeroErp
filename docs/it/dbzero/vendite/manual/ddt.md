## 📘 Documentazione Concettuale – Tabella `vendite.ddt`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
>
[vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)   
> [vendite.ordini_righe_fulfillment](/dbzero/vendite/tabelle/ordini_righe_fulfillment)   
> [vendite.mv_ddt_ordini] – **vista materializzata** delle coppie Testata DDT ↔ Testata Ordine      
> [config.stati_doc_ddt](/dbzero/config/tabelle/stati_doc_ddt)   

---
### 🎯 Scopo Principale
La tabella **`vendite.ddt`** rappresenta la **testata** dei Documenti di Trasporto. È il fulcro del ciclo logistico tra **Ordini** (evasione/spedizione) e **Fatture** (conto vendita / accompagnatoria).

* Traccia i **metadati di spedizione** (data, mittente/destinatario, causale, vettore).
* Collega le **righe** in `vendite.ddt_righe`.
* Espone lo **stato** operativo tramite `config.stati_doc_ddt` (es. *EMESSO → IN_TRANSITO → CONSEGNATO → RESO* – nomenclatura da confermare).
* Partecipa alle ricostruzioni **ordine↔ddt** via fulfillment (riga↔riga) e alla derivazione **ddt↔ordine** (testata↔testata) tramite `mv_ddt_ordini`.

> ℹ️ **Nota**: la definizione SQL della tabella è generata automaticamente dal progetto; qui si documentano struttura concettuale, vincoli e flussi.

---


### Relazioni chiave

* **`vendite.ddt_righe(ddt_id)`** → righe del documento (1–N).
* **`vendite.ordini_righe_fulfillment(ddt_riga_id)`** → mappatura riga DDT con riga Ordine.
* **`vendite.mv_ddt_ordini(ddt_id, ordine_id)`** → coppie testata↔testata derivate.
* **`config.stati_doc_ddt(id)`** → stato del documento.

> 立 **FK policy**: sui legami fulfillment → righe vige `ON DELETE RESTRICT` (no hard delete). Le cancellazioni sono rimpiazzate da flussi di **storno/annullo**.

---

###  Stati del DDT

Gli stati sono definiti in **`config.stati_doc_ddt`**. Mappatura tipica del ciclo:

```
EMESSO → IN_TRANSITO → CONSEGNATO → (RESO opz.)
```

* Gli **stati** sono valori **enum** del dominio; per policy non si effettuano cancellazioni fisiche (no hard delete).
* La logica di avanzamento può dipendere da eventi applicativi (es. conferma vettore, POD, consegna).

>  La funzione di sync degli **stati ordine** legge anche lo stato del DDT per determinare le quantità **consegnate**.

---

### Vincoli e indici

* **PK**: `id`
* **UQ consigliate**: `anno+serie+numero` (o progressivo per gestore)
* **Indici operativi**:

  * `ix_ddt_data_documento (data_documento)`
  * `ix_ddt_stato (stato_doc_ddt_id)`
  * `ix_ddt_destinatario (soggetto_destinatario_id)`

> ℹ️ Gli indici reali possono variare in base ai volumi e all’uso (reporting vs operativo).

---

### Flussi di processo collegati

1. **Evasione da Ordine**

   * Inserimento in `ordini_righe_fulfillment` genera il collegamento riga Ordine ↔ riga DDT.
   * La **MV** `mv_ddt_ordini` riflette le coppie testata↔testata.

2. **Consegna**

   * Al cambio stato del DDT a *CONSEGNATO*, le quantità consegnate possono aggiornare l’**avanzamento ordine** (via trigger di sync).

3. **Push a commessa** (via `fn_list_ddt_da_pushare`)

   * DDT da ordine: eredita billing_account e prezzo via fulfillment; scatta quando `fatturazione_trigger` dell'ordine corrisponde allo stato DDT.
   * DDT autonomo: richiede `billing_account_id` proprio; scatta a SPEDITO/CONSEGNATO.
   * Campi aggiunti: `billing_account_id`, `utility_id`, `valuta_id` (ereditati dall'ordine sorgente via `trgfn_ddt_normalize`), `ddt_righe.prezzo_unitario`.

4. **Fatturazione**

   * Il DDT puo` essere fatturato (fattura differita o accompagnatoria). Le tabelle e logiche di collegamento saranno documentate in un modulo dedicato.

---

###  Regole di coerenza (riassunto)

* **No hard delete** su `ddt` e `ddt_righe`; esistono **trigger** che bloccano la cancellazione diretta delle righe se presenti fulfillment, e in generale **vietano la DELETE** (policy ZeroERP).
* **`storicizza`**: all’operazione di cancellazione (se mai prevista per soli casi tecnici) scatta il trigger che copia in `storico.ddt` / `storico.ddt_righe`. In produzione si preferisce **annullo/storno** a cancellazione.

---

### Query tipiche

* **Selezione DDT per range di date e stato**

  ```sql
  SELECT d.*
    FROM vendite.ddt d
   WHERE d.data_documento BETWEEN :dal AND :al
     AND d.stato_doc_ddt_id = :stato_id
   ORDER BY d.data_documento DESC, d.id DESC;
  ```
* **Ordini collegati a un DDT (via MV)**

  ```sql
  SELECT o.*
    FROM vendite.mv_ddt_ordini m
    JOIN vendite.ordini o ON o.id = m.ordine_id
   WHERE m.ddt_id = :ddt_id;
  ```

---

### Manutenzione MV correlata

* **Refresh manuale**:

  ```sql
  REFRESH MATERIALIZED VIEW CONCURRENTLY vendite.mv_ddt_ordini;
  ```
* **Refresh controllato** (se attivata la funzione di servizio):

  ```sql
  SELECT dbops.fn_refresh_mv_ddt_ordini(true, 3);
  ```

---

### ⚠️ Errori/diagnostica comuni

* `DELETE_BLOCKED_FUL` – tentativo di cancellare riga DDT collegata a fulfillment.
* `DELETE_NOT_ALLOWED` – policy: no hard delete sulle righe DDT/Ordini.
* `STATO_DDT_NON_VALIDO` – cambio stato verso valore non presente in `config.stati_doc_ddt`.

---

### Checklist di conformità

* [ ] UQ corretta su numerazione (o progressivo per gestore)
* [ ] FK a domini/stati coerenti
* [ ] Indici operativi creati
* [ ] Trigger di blocco DELETE attivi su `ddt_righe`
* [ ] MV `mv_ddt_ordini` presente e indicizzata (UNIQUE)
* [ ] Procedure di **storno/annullo** definite nei flussi applicativi

---

### 📘 Note finali

* Questo documento descrive il **comportamento atteso** della tabella `vendite.ddt` nel contesto Zero ERP.
* Gli esempi di query sono indicativi; le implementazioni DRF/Vue 3 riflettono gli stessi vincoli (no hard delete, stati come sorgente della verità).
