## 📘 Documentazione Concettuale – Tabella `vendite.fatture_righe`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [config.iva](/dbzero/config/tabelle/iva)   
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)   
> • [catalogo.unita_misura](/dbzero/catalogo/tabelle/unita_misura)   
> • [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account)  

---

### 🎯 Scopo Principale

`vendite.fatture_righe` contiene le **righe economiche** di una fattura: descrizione, articolo (opzionale), UoM, quantità, prezzo, sconti, IVA e **importi congelati** (*snapshot*) al momento della generazione. Ogni riga è ordinata tramite `riga_nr` ed è collegata a una testata `vendite.fatture` (FK `fattura_id`). Supporta la **destinazione a BA diverso** dalla testata e l’idempotenza di import riga‑per‑riga.

Obiettivi principali:

* Conservare **valori definitivi** (imponibile, imposta, totale) per garantire riproducibilità documentale nel tempo.
* Permettere **override di IVA e attributi fiscali** (esigibilità, split payment) a livello riga.
* Mantenere riferimenti all’**articolo di catalogo** e all’**unità di misura** utilizzata per il calcolo.
* Supportare **tracciabilità di origine** (sorgente_tipo / sorgente_uid / sorgente_riga) per import e riconciliazioni.

---

### 🧭 Collocazione nel flusso

1. **Popolamento**: generazione da attività fatturabili, ordini, contratti o input manuale; calcolo `imponibile_riga`, `imposta_riga`, `totale_riga` con snapshot delle regole (incluse `iva_perc`, `iva_natura`).
2. **Ordinamento**: assegnazione `riga_nr` progressivo per fattura; vincolo unico `(fattura_id, riga_nr)`.
3. **Totali testata**: la somma delle righe alimenta i campi `imponibile_tot`, `imposta_tot`, e convergono nei riepiloghi IVA.
4. **Controlli**: normalizzazione/guard tramite trigger `trg_fatture_righe_ins_upd_norm_guard` (coerenze su quantità/prezzo/IVA/UoM/sconti, e allineamento campi snapshot).

---

### 🔑 Campi chiave (semantica)

* **Identità e collegamenti**: `fattura_id` (testata), `riga_nr` (ordine), `articolo_id` (opzionale), `uom_id` (unità misura), `dest_billing_account_id` (attribuzione economica a BA figlio).
* **Dati merce/servizio**: `descrizione`, `qta` (≥ 0), `prezzo_unitario` (≥ 0), `sconto_perc` (0–100).
* **IVA e fiscali**: `iva_id` (aliquota), `iva_perc`, `iva_natura` (snapshot), `esigibilita` (I|D|S), `split_payment`.
* **Importi congelati**: `imponibile_riga`, `imposta_riga`, `totale_riga` (sempre valorizzati al closing della riga).
* **Governance**: `meta` (JSONB, NOT NULL), `storicizza`, `tx_id`, audit `data_*`/`user_*`.
* **Idempotenza import**: `sorgente_tipo_id`, `sorgente_uid`, `sorgente_riga` con **unique parziale** su (sorgente_tipo_id, sorgente_uid).

---

### 🔒 Vincoli, indici e coerenze

* **FK**: fattura, articolo (opz.), UoM, IVA, BA destinatario (opz.), sorgente tipo.
* **CHECK**:

  * `chk_fatture_righe_sconto_perc` → sconto 0..100.
  * `chk_fatr_iva_perc` → iva_perc 0..100 (se valorizzato).
* **UNIQUE**:

  * `uq_fatture_righe_riga_nr` su `(fattura_id, riga_nr)` (per progressivo di stampa/ordinamento).
  * `uq_fatture_righe_v_sorgente_fk` su `(sorgente_tipo_id, sorgente_uid)` **WHERE `sorgente_tipo_id IS NOT NULL`** (idempotenza).
* **INDICI operativi**: per ricerche su fattura, IVA, BA destinatario.

---

### 🧮 Logiche di calcolo (indicative)

* **Base**:
  `imponibile_riga = round(qta * prezzo_unitario * (1 - sconto_perc/100), dec_importi)`
  `imposta_riga    = round(imponibile_riga * (iva_perc/100), dec_importi)`
  `totale_riga     = imponibile_riga + imposta_riga`
* **Rounding**: usare le funzioni centralizzate del modulo vendite (decimali/metodo) per coerenza con testata e policy articolo.
* **Override fiscali**: `iva_id` guida la natura/percentuale; `iva_perc`/`iva_natura` **devono essere snapshot** coerenti al momento di emissione.

---

### 🧪 Esempi d’uso (query applicative)

```sql
-- 1) Righe con imponibile > 0 per una fattura
SELECT r.*
FROM vendite.fatture_righe r
WHERE r.fattura_id = :fattura_id
  AND COALESCE(r.imponibile_riga,0) > 0
ORDER BY r.riga_nr;

-- 2) Somma righe → totali testata
SELECT 
  SUM(r.imponibile_riga) AS imponibile,
  SUM(r.imposta_riga)    AS imposta,
  SUM(r.totale_riga)     AS totale
FROM vendite.fatture_righe r
WHERE r.fattura_id = :fattura_id;

-- 3) Idempotenza import righe
SELECT r.id
FROM vendite.fatture_righe r
WHERE r.sorgente_tipo_id = :src_tipo
  AND r.sorgente_uid = :src_uid;
```

---

### ✅ Best practice operative

* **Snapshot completo**: valorizzare sempre  `iva_natura`, `imponibile_riga`, `imposta_riga`, `totale_riga` al termine del calcolo riga.
* **Progressivo riga**: assegnare `riga_nr` in modo **contiguo** e consolidato prima della numerazione della fattura.
* **Override BA**: usare `dest_billing_account_id` solo quando necessario (es. ripartizioni o refatturazioni intra‑BA).
* **Validazioni**: bloccare quantità negative e prezzi negativi a livello applicativo (qui sono consentiti `≥ 0`).
* **Esigibilità/split**: impostare solo quando differiscono dal default della testata/cliente.

---

### ⚠️ Osservazioni & possibili migliorie

1. **Calcolo automatico importi**: opzionale trigger `BEFORE INSERT/UPDATE` per calcolare e arrotondare `imponibile_riga`, `imposta_riga`, `totale_riga` se non forniti.
3. **Gestione bundle/kit**: se servono righe descrittive non valorizzate, usare `qta = 0` e `totali = 0` con tipo riga in `meta`.

---

### 📘 Note progettuali

> In `vendite.fatture_righe` **non** sono imposti vincoli `qta >= 0` o `prezzo_unitario >= 0`.
> Questa è una **scelta intenzionale**: nei contesti *utilities* o *servizi a consumo* possono esistere righe con valori negativi, ad esempio per:
>
> * Conguagli su stime precedenti.
> * Restituzioni o accrediti al cliente.
> * Rettifiche di acconti o storni tecnici.
> * Bilanciamenti tra letture reali e stimate.
>   Il segno negativo è quindi parte integrante del modello economico e **non invalida la correttezza fiscale** della riga.

---

### 👓 Ruolo nel sistema

Le righe sono il **cuore economico** della fattura: fotografano quantità, prezzi, sconti e IVA **come effettivamente emessi**, garantendo **stabilità fiscale** e ricostruibilità del documento a distanza di tempo. La qualità dei loro snapshot abilita reporting affidabile, controlli IVA corretti e riconciliazioni con le sorgenti.
