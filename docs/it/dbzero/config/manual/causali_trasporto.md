## 📘 Documentazione Concettuale – Tabella `config.causali_trasporto`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:   
>
[config.aspetti_beni](/dbzero/config/tabelle/aspetti_beni)    
> [vendite.ddt](/dbzero/vendite/tabelle/ddt)     
> [vendite.ddt_righe](/dbzero/vendite/tabelle/ddt_righe)    
>

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

* **`fatturabile` (dal 2026-07-18) — la causale dichiara l'intento commerciale**:

  * `boolean NOT NULL`, **default `false`**. Dice se la merce che viaggia con questa causale genera una **vendita da fatturare** (`true`) o è **solo trasporto** (`false`).
  * Seed vivo: **`VENDITA` è l'unica `true`**; `CONTO_VISIONE`, `RESO`, `RIPARAZIONE`, `CAMPIONATURA`, `TRASFERIMENTO`, `CONTO_LAVORO`, `OMAGGIO` sono `false`.
  * **Perché il default è `false`**: una causale nuova nasce non fatturabile, così una dimenticanza produce un DDT che **non entra** nella coda di fatturazione — errore visibile e recuperabile — invece di uno che fattura per sbaglio, che è silenzioso e ha i soldi in mezzo.
  * **Zero `IF` hardcoded**: il vocabolario guida il comportamento (stesso pattern di `tipi_reso.riapre_residuo`). I casi ambigui — l'omaggio, che qualcuno fattura a sconto 100% — si risolvono cambiando **una cella di seed**, senza toccare codice.
  * **Cosa ne dipende**: il gate all'emissione [`trgfn_ddt_guard_causale_emissione`](/dbzero/vendite/manual/trgfn_ddt_guard_causale_emissione) (con causale fatturabile ogni riga attiva deve avere un prezzo risolvibile), il lister di push DDT e i cruscotti di fatturazione, che escludono i DDT di solo trasporto.
  * ⚠️ **La causale è obbligatoria dall'emissione del DDT in poi** (in bozza il valore nullo resta legittimo): senza, il documento sarebbe ambiguo per la fatturazione.

* **Estensioni tramite `meta`**:

  * `meta` è un campo `jsonb` utilizzabile per **parametri opzionali**, ad esempio:

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

  * Campi come `causale_trasporto_id` in `vendite.ddt` (e, se previsto, in altri documenti logistici).
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

     * invoca la funzione generica `script.trgfn_audit_data_user_generic()` che centralizza la gestione dei campi di audit.

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

---

## ⭐ `fatturabile` — la colonna che dice se la merce si sta vendendo

> Aggiunta il 2026-07-17. È la colonna più importante della tabella, e non si
> vede dal nome: decide **se un documento entra nel giro della fatturazione**.

La merce si muove anche quando non si vende: conto visione, campionatura,
riparazione, trasferimento fra depositi, conto lavorazione, omaggio. In quei casi
un prezzo di listino è un dato che **non ha significato** — non manca per
distrazione, semplicemente non si applica.

Il problema è che l'assenza di un prezzo, da sola, è **ambigua**: non distingue
«ho deciso che non si vende» da «me ne sono dimenticato». Per questo l'intento
**non si deduce**, si **dichiara** — e lo si dichiara con il campo che
l'operatore compila comunque, la causale.

| causale (seed) | `fatturabile` |
|---|---|
| VENDITA | ✅ sì |
| CONTO_VISIONE · RESO · RIPARAZIONE · CAMPIONATURA · TRASFERIMENTO · CONTO_LAVORO · OMAGGIO | no |

### Che cosa cambia, in concreto

* **all'emissione**: se la causale dice che si vende, ogni riga — e ogni
  componente di un kit — deve avere un prezzo, altrimenti il documento non esce
  e il messaggio dice **quale riga** manca. Se la causale dice che non si vende,
  il prezzo non viene chiesto a nessuno;
* **dopo l'emissione**: i documenti non fatturabili restano **fuori** dalle liste
  e dai cruscotti della fatturazione — non come «scartati», proprio come non
  pertinenti;
* **la causale non si cambia più** una volta che il documento è uscito dalla
  bozza: è stampata sul documento di trasporto, e cambiarla dopo vorrebbe dire
  che il foglio consegnato al vettore e l'archivio dicono cose diverse.

### Due cose da sapere prima di aggiungere una causale

⚠️ **`fatturabile` è una cella di seed, non codice.** I casi discutibili — e
l'omaggio è il principale — si decidono cambiando un valore nel CSV, non
toccando funzioni. Se un domani l'omaggio dovesse arrivare a fattura (la rivalsa
IVA), quello **non** è un fatto del prezzo né della causale: è la **natura** del
documento, l'asse che vive in `config.nature_doc_fiscale`.

⚠️ **In bozza la causale può mancare, ed è voluto.** L'operatore carica le righe
prima di aver deciso l'intento: pretendere la causale al salvataggio
sposterebbe l'errore su un momento in cui la risposta non c'è ancora. Il
presidio sta **all'emissione**, che è il momento in cui il documento comincia ad
avere effetti.

**Approfondimento**: `docs/it/dev/work-done/brief-ddt-righe-senza-prezzo.md`
· decisione di design DL-28 in
`docs/it/dev/work-done/brief-design-fatturazione-due-lenti.md` §10.
