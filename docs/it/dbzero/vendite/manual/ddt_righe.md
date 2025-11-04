## 📘 Documentazione Concettuale – Tabella `vendite.ddt_righe`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.ddt](/dbzero/vendite/tabelle/ddt)
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)
> • [dbops.audit_log](/dbzero/dbops/tabelle/audit_log)

---

### 🎯 Scopo principale

`vendite.ddt_righe` rappresenta le **righe dei Documenti di Trasporto di vendita**. Ogni record corrisponde a una **voce di spedizione** associata a una testata DDT (`vendite.ddt`), identificando articolo, quantità, unità di misura e dettagli di tracciabilità (lotto, seriale).

La tabella è concepita per:

* Tracciare con precisione le **quantità effettivamente spedite** per ciascun articolo.
* Mantenere uno **snapshot descrittivo indipendente** dall’anagrafica articoli, così da preservare la descrizione storica al momento della spedizione.
* Consentire la **storicizzazione e audit** completi tramite `tx_id` e campi `data_*` / `user_*`.
* Gestire in modo coerente articoli con **lotti e seriali**, garantendo tracciabilità lungo l’intero ciclo logistico.

---

### 🧭 Collocazione nel flusso documentale

1. **Evasione Ordine** → Le righe DDT derivano da ordini cliente o attività di fulfillment.
2. **Spedizione** → Le quantità sono validate contro la disponibilità di magazzino e le policy articolo.
3. **Fatturazione** → Le righe DDT diventano base per la generazione di righe fattura (`vendite.fatture_righe`).
4. **Storicizzazione** → Ogni modifica genera snapshot storico se `storicizza = true`.

---

### 🧩 Struttura logica e relazioni

* **FK principali:**

  * `ddt_id` → `vendite.ddt`: collega la riga alla testata.
  * `articolo_id` → `catalogo.articoli`: identifica il bene o servizio spedito.
  * `uom_id` → `catalogo.unita_misura`: definisce l’unità di misura coerente con l’articolo.
* **Vincoli logici:**

  * Ogni `ddt_id` ha un progressivo riga (`riga_nr`) univoco.
  * Quantità (`qta`) deve essere strettamente maggiore di zero.
  * Lotto/seriale presenti solo se richiesti dall’articolo.
* **Meta estensibile (`jsonb`)**: supporta dati accessori (es. tag, note, riferimenti esterni) senza modificare lo schema.

---

### 💡 Descrizione d’uso

Le righe DDT sono utilizzate in molteplici processi del ciclo vendite:

* **Gestione spedizioni:** ogni voce rappresenta un’unità logistica, con informazioni necessarie per picking e packing.
* **Integrazione con magazzino:** consente il calcolo dei movimenti effettivi e delle giacenze.
* **Fatturazione automatica:** base per la fatturazione differita o immediata.
* **Tracking normativo:** in caso di lotti o seriali, garantisce la completa rintracciabilità del bene.

---

### ⚙️ Trigger e automazioni

* `trg_a10_dlt_block_ddt` → impedisce la cancellazione di righe DDT se collegate a processi successivi (fatture, storici, fulfillment).
* **Trigger standard ZeroERP consigliati:**

  * `dbops.trgfn_tx_id_managed` → propaga il `tx_id` logico.
  * `dbops.trgfn_audit_columns` → aggiorna audit di inserimento/modifica.
  * `dbops.trgfn_storicizza` → snapshot su update/delete.

---

### 🔒 Vincoli, indici e coerenze

* **Unique Index**: `(ddt_id, riga_nr)` → progressivo univoco per testata.
* **Check suggeriti:**

  * `qta > 0` (quantità sempre positiva).
  * `seriale IS NULL OR qta = 1` per articoli serializzati.
  * `lotto IS NOT NULL` per articoli che richiedono tracciabilità lotto.

---

### 📊 Esempi di utilizzo applicativo

```sql
-- Elenco righe di un DDT
SELECT *
FROM vendite.ddt_righe
WHERE ddt_id = :ddt_id
ORDER BY riga_nr;

-- Ricerca per lotto o seriale
SELECT d.id AS ddt_id, dr.riga_nr, dr.articolo_id, dr.qta
FROM vendite.ddt d
JOIN vendite.ddt_righe dr ON dr.ddt_id = d.id
WHERE dr.lotto = :lotto OR dr.seriale = :seriale;
```

---

### 🧩 Esempio di utilizzo applicativo (DRF)

```python
class DdtRigaSerializer(serializers.ModelSerializer):
    class Meta:
        model = DdtRiga
        fields = '__all__'

    def validate_qta(self, value):
        if value <= 0:
            raise serializers.ValidationError('La quantità deve essere maggiore di zero.')
        return value
```

---

### 🧪 Testing e validazioni

Esempi di test pgTAP suggeriti:

```sql
SELECT ok((SELECT count(*) FROM vendite.ddt_righe WHERE qta <= 0) = 0, 'qta > 0');
SELECT ok((SELECT count(*) FROM vendite.ddt_righe dr JOIN catalogo.articoli a ON a.id = dr.articolo_id WHERE a.richiede_lotto AND dr.lotto IS NULL) = 0, 'lotto obbligatorio');
```

---

### ⚠️ Osservazioni e possibili migliorie

1. **Assenza di vincoli espliciti su `qta`** → aggiungere un **CHECK (qta > 0)** per garantire robustezza.
2. **Gestione lotto/seriale** → introdurre trigger di validazione collegati alle policy articolo (evita incoerenze tra catalogo e righe DDT).
3. **Indicizzazione** → possibile aggiunta indice `(ddt_id)` per ottimizzare le join frequenti.
4. **Performance JSONB** → valutare un indice GIN su `meta` per query semantiche.
5. **Validazione UoM** → utile un controllo di compatibilità con la UoM base dell’articolo tramite funzione.

---

### 👓 Importanza nel sistema

`vendite.ddt_righe` è una tabella **centrale nel ciclo logistico** di ZeroERP.
Funge da ponte tra la movimentazione fisica (spedizioni) e la documentazione fiscale (fatture).
Una gestione accurata di quantità, unità di misura e tracciabilità assicura **consistenza, rintracciabilità e conformità normativa** lungo tutto il processo di vendita.
