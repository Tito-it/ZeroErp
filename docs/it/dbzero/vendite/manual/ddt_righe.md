## 📘 Documentazione Concettuale – Tabella `vendite.ddt_righe`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.ddt](/dbzero/vendite/tabelle/ddt)     
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)    
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)    
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)    
> • [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)   

> **Approfondimento funzioni:**
> 
• [script.trgfn_qta_from_operativa](/dbzero/script/funzioni/trgfn_qta_from_operativa)

---
### 🎯 Scopo Principale
`vendite.ddt_righe` rappresenta le **righe dei Documenti di Trasporto di vendita**. Ogni record corrisponde a una **voce di spedizione** associata a una testata DDT (`vendite.ddt`), identificando articolo, quantità, unità di misura e dettagli di tracciabilità (lotto, seriale).

La tabella è concepita per:

* Tracciare con precisione le **quantità effettivamente spedite** per ciascun articolo.
* Mantenere uno **snapshot descrittivo indipendente** dall’anagrafica articoli, così da preservare la descrizione storica al momento della spedizione.
* Consentire la **storicizzazione e audit** completi tramite `tx_id` e campi `data_*` / `user_*`.
* Gestire in modo coerente articoli con **lotti e seriali**, garantendo tracciabilità lungo l’intero ciclo logistico.

---

### Collocazione nel flusso documentale

1. **Evasione Ordine** → Le righe DDT derivano da ordini cliente o attività di fulfillment.
2. **Spedizione** → Le quantità sono validate contro la disponibilità di magazzino e le policy articolo.
3. **Fatturazione** → Le righe DDT diventano base per la generazione di righe fattura (`vendite.fatture_righe`).
4. **Storicizzazione** → Ogni modifica genera snapshot storico se `storicizza = true`.

---

### Struttura logica e relazioni

* **FK principali:**

  * `ddt_id` → `vendite.ddt`: collega la riga alla testata.
  * `articolo_id` → `catalogo.articoli`: identifica il bene o servizio spedito.
  * `uom_id` → `catalogo.unita_misura`: definisce l’unità di misura coerente con l’articolo.
* **Vincoli logici:**

  * Ogni `ddt_id` ha un progressivo riga (`riga_nr`) univoco.
  * Quantità (`quantita`) deve essere strettamente maggiore di zero.
  * Lotto/seriale presenti solo se richiesti dall’articolo.
* **Meta estensibile (`jsonb`)**: supporta dati accessori (es. tag, note, riferimenti esterni) senza modificare lo schema.

---

### Descrizione d’uso

Le righe DDT sono utilizzate in molteplici processi del ciclo vendite:

* **Gestione spedizioni:** ogni voce rappresenta un’unità logistica, con informazioni necessarie per picking e packing.
* **Integrazione con magazzino:** consente il calcolo dei movimenti effettivi e delle giacenze.
* **Fatturazione automatica:** base per la fatturazione differita o immediata.
* **Tracking normativo:** in caso di lotti o seriali, garantisce la completa rintracciabilità del bene.

---

### Trigger e automazioni

* `trg_ddt_righe_a05_doc_righe_lock_fuori_bozza_ins_upd_dlt` → **le righe si
  aggiungono, modificano e tolgono solo finché il DDT è in DRAFT**
  (`E_RIGA_DOC_NON_BOZZA`). È il building block
  [`trgfn_doc_righe_lock_fuori_bozza`](/dbzero/vendite/funzioni/trgfn_doc_righe_lock_fuori_bozza),
  in fascia `_a05_` perché il suo rifiuto deve parlare prima di quelli sui
  legami. Nasce il 2026-09-22: fino a quel giorno una riga di DDT emesso — anche
  già instradata alla fatturazione — si poteva disattivare o cambiare senza che
  niente lo fermasse.
* `trg_ddt_righe_a10_block_ddt_dlt` → traduce in una frase il rifiuto di togliere
  una riga con legami a valle (fulfillment, resi, riconsegne); a rifiutare sono le
  FK ([`trgfn_dlt_block_ordrig_ddtrig`](/dbzero/vendite/funzioni/trgfn_dlt_block_ordrig_ddtrig)).

* **Natura di vendita** (dal 2026-10-13, brief-db-articoli-ammessi-per-documento A-4):
  `natura_vendita_id` (NOT NULL) è la natura con cui la riga è stata venduta. La scrive
  [`script.trgfn_righe_natura_vendita`](/dbzero/script/manual/trgfn_righe_natura_vendita) (`…_a10_natura_vendita_ins_upd`, modo CHIAMANTE): quella portata dal verbo che
  copia la riga, `fn_genera_ddt_da_ordine` quella della riga d'ordine che evade e `fn_genera_ddt_riconsegna` quella della riga di bolla resa, altrimenti quella dell'articolo; si riscrive solo quando cambia
  l'articolo. A mano non si cambia (`…_a10_lock_columns_upd`, generato da
  `dbops.automation_lock_columns`, `E_RIGA_NATURA_VENDITA_IMMUTABILE`).

* `trg_a10_ins_upd_ddt_righe_qta_from_operativa`

Chiama script.trgfn_qta_from_operativa('true','false').

Logica attesa (in base alla versione condivisa):

Se uom_operativa_id e qta_operativa sono valorizzati ⇒ calcola quantita in UoM base usando il conversion factor articolo/UoM (es. 1 scatola = 50 pezzi).

Se manca uno dei due ⇒ ricompone i dati operativi a partire dalla UoM base articolo e dalla qta (se presente).

Argomento fill_factor_to_base = true ⇒ forza (o valida) fattore di conversione verso la base.

Argomento fill_uom_id_base = false ⇒ non forza il popolamento di uom_id se già presente; in caso di NULL può valorizzarlo dallo snapshot articolo.

Garantisce coerenza decimali (step, max_dec) rispetto alla policy UoM dell’articolo; in caso contrario → fn_log_and_raise_error.

---

### Vincoli, indici e coerenze

* **Unique Index**: `(ddt_id, riga_nr)` → progressivo univoco per testata.
* **Check suggeriti:**

  * `quantita > 0` (quantità sempre positiva).
  * `seriale IS NULL OR quantita = 1` per articoli serializzati.
  * `lotto IS NOT NULL` per articoli che richiedono tracciabilità lotto.

---
🧭 Flussi tipici

Evasione da ordine

L’utente seleziona righe d’ordine → il sistema propone uom_operativa_id e qta_operativa coerenti (es. 2 scatole).

Il trigger calcola qta in UoM base (es. 100 pezzi).

Si memorizzano eventuali lotto/seriale.

Si registra il collegamento di evasione (ordine→DDT) a livello riga.

DDT libero (senza ordine)

L’operatore inserisce manualmente articolo, uom_operativa_id, qta_operativa (o direttamente qta), più lotto/seriale quando richiesti.

Il trigger assicura coerenza con la UoM base e le policy articolo.

Fatturazione da DDT

Le righe DDT diventano sorgente per vendite.attivita_fatturabili; si trasferiscono articolo_id, descrizione, uom_id base e quantita, oltre a eventuali metadati utili (lotto/seriale) per il corpo documento o per il trace log.

---


### Esempi di utilizzo applicativo

```sql
-- Elenco righe di un DDT
SELECT *
FROM vendite.ddt_righe
WHERE ddt_id = :ddt_id
ORDER BY riga_nr;

-- Ricerca per lotto o seriale
SELECT d.id AS ddt_id, dr.riga_nr, dr.articolo_id, dr.quantita
FROM vendite.ddt d
JOIN vendite.ddt_righe dr ON dr.ddt_id = d.id
WHERE dr.lotto = :lotto OR dr.seriale = :seriale;
```


---

### Testing e validazioni

Esempi di test pgTAP suggeriti:

```sql
SELECT ok((SELECT count(*) FROM vendite.ddt_righe WHERE quantita <= 0) = 0, 'quantita > 0');
SELECT ok((SELECT count(*) FROM vendite.ddt_righe dr JOIN catalogo.articoli a ON a.id = dr.articolo_id WHERE a.richiede_lotto AND dr.lotto IS NULL) = 0, 'lotto obbligatorio');
```

---

### ⚠️ Osservazioni e possibili migliorie

1. **Assenza di vincoli espliciti su `quantita`** → aggiungere un **CHECK (quantita > 0)** per garantire robustezza.
2. **Gestione lotto/seriale** → introdurre trigger di validazione collegati alle policy articolo (evita incoerenze tra catalogo e righe DDT).
3. **Indicizzazione** → possibile aggiunta indice `(ddt_id)` per ottimizzare le join frequenti.
4. **Performance JSONB** → valutare un indice GIN su `meta` per query semantiche.

---

### Importanza nel sistema

`vendite.ddt_righe` è una tabella **centrale nel ciclo logistico** di ZeroERP.
Funge da ponte tra la movimentazione fisica (spedizioni) e la documentazione fiscale (fatture).
Una gestione accurata di quantità, unità di misura e tracciabilità assicura **consistenza, rintracciabilità e conformità normativa** lungo tutto il processo di vendita.
