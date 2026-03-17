## 📘 Documentazione Concettuale – Tabella `config.causali_trasporto`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:   
>
[config.aspetti_beni](/dbzero/config/tabelle/aspetti_beni)    
> [vendite.ddt_testata](/dbzero/vendite/tabelle/ddt_testata)     
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)    
>
Approfondimenti funzioni/trigger generici:   
>
[script.trgfn_upd_audit_data_user_generic](/dbzero/script/funzioni/trgfn_upd_audit_data_user_generic)  

---

La tabella **`config.causali_trasporto`** contiene il catalogo delle **causali di trasporto** utilizzate nei **Documenti di Trasporto (DDT)** e, più in generale, in tutti i documenti che prevedono una movimentazione fisica di beni.

Le causali di trasporto descrivono il *motivo* del movimento (es. vendita, conto visione, reso da cliente, reso a fornitore, trasferimento interno, conto lavorazione, ecc.) e possono essere utilizzate sia a fini logistici che amministrativi.

---

### 🎯 Scopo Principale

* Fornire un **catalogo centralizzato** delle causali di trasporto utilizzabili nei DDT.
* Supportare la **classificazione omogenea** dei flussi di movimentazione in base alla motivazione dell’invio/ritiro dei beni.
* Costituire la base per **regole di processo** (es. fatturazione automatica, valorizzazione, contabilizzazione, statistiche) dipendenti dalla causale utilizzata.

---

### Vincoli e Regole Aziendali

* **Unicità logica**:

  * `codice` è un **codice univoco** per ogni causale di trasporto.
  * Rappresenta la chiave funzionale da usare in configurazioni, integrazioni e mapping verso sistemi esterni.

* **Descrizione estesa**:

  * `descrizione` fornisce il testo leggibile dagli operatori e dagli utenti di front-end.
  * Deve essere chiara e coerente con le procedure operative aziendali (es. "Vendita", "Reso da cliente", "Trasferimento magazzino", ecc.).

* **Stato di attivazione**:

  * `attivo` indica se la causale è utilizzabile nei processi correnti.
  * L’indice `ix_causali_trasporto_attivo` è pensato per velocizzare i filtri sulle causali attive (combo di selezione, ricerche).

* **Estensioni tramite `meta`**:

  * `meta` è un campo `jsonb` utilizzabile per **parametri opzionali**, ad esempio:

    * indicazione se la causale **genera documento di vendita** o meno;
    * flag per distinguere movimenti **in uscita / in entrata / interni**;
    * configurazioni per collegamento con **causali contabili** o **tipologie di fatturazione**;
    * eventuali opzioni specifiche del gestore (es. forzare presenza ordine, vincoli su cliente/fornitore, ecc.).
  * La struttura del JSON deve seguire linee guida condivise per evitare usi non controllati.

* **Audit**:

  * `data_insert`, `user_insert`, `data_update`, `user_update` sono campi di audit standard.
  * Le modifiche al catalogo delle causali di trasporto devono essere tracciabili per motivi di controllo e diagnosi dei processi.

---

### Relazioni

`config.causali_trasporto` è una **tabella di configurazione sorgente** referenziata tipicamente da:

* **DDT**:

  * Campi come `causale_trasporto_id` in `vendite.ddt_testata` (e, se previsto, in altri documenti logistici).
  * La causale selezionata descrive il *motivo operativo* con cui i beni vengono movimentati.

* **Altri documenti di movimento**:

  * Potenzialmente ordini, resi, movimenti interni o trasferimenti tra magazzini che necessitano di una motivazione codificata.

> In molti flussi, la **causale di trasporto** lavora in combinazione con l’**aspetto beni** per definire in dettaglio sia il *motivo* sia la *natura* della movimentazione.

---

### Trigger Associati

1. **Trigger di audit generico** (naming tipico: `trg_upd_causali_trasporto_audit_data_user`)

   * **Quando**: `BEFORE UPDATE`
   * **Cosa fa**:

     * aggiorna automaticamente i campi `data_update` e `user_update` ad ogni modifica della riga.
   * **Come**:

     * invoca la funzione generica `script.trgfn_upd_audit_data_user_generic()` che centralizza la gestione dei campi di audit.

> Questo garantisce che tutte le modifiche al catalogo causali di trasporto siano sempre tracciate in modo uniforme rispetto alle altre tabelle di configurazione.

---

### Vantaggi Operativi

* **Uniformità nei DDT**: tutte le causali utilizzate dagli operatori provengono da un catalogo unico e controllato.
* **Governance dei processi**: la combinazione di `codice`, `attivo` e `meta` permette di modellare facilmente:

  * quali causali sono disponibili per specifici processi (es. solo vendite, solo trasferimenti interni);
  * quali causali possono essere associate a determinate tipologie di documenti o controparti;
  * logiche di inclusione/esclusione in reportistica e processi batch.
* **Tracciabilità e compliance**: l’audit integrato consente di verificare chi ha modificato le causali, quando e con quali parametri.
* **Estendibilità**: l’utilizzo del campo `meta` consente di evolvere il modello senza modificare la struttura fisica della tabella.

---

> **“Un catalogo ben governato delle causali di trasporto rende più chiaro il ciclo logistico e facilita la definizione di regole automatiche su DDT, ordini e fatture.”**
