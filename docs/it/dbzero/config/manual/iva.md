## 📘 Documentazione Concettuale – Tabella `config.iva` 

> 👀 **Vedi anche**
>
Approfondimento tabelle:    
>
[config.iva_assoggetamenti](/dbzero/config/tabelle/iva_assoggettamenti)    
> [config.iva_natura](/dbzero/config/tabelle/iva_natura)    
> [config.conti_contabili](/dbzero/config/tabelle/conti_contabili)    
>
Approfondimenti funzioni:   
>
[config.trgfn_iva_ins_upd_check_conti_iva](/dbzero/config/funzioni/trgfn_iva_guard_conti_iva)   
> [config.fn_get_aliquota_iva](/dbzero/config/funzioni/fn_get_aliquota_iva)    
> [script.trgfn_audit_data_user_generic](/dbzero/script/funzioni/trgfn_audit_data_user_generic)     

La tabella **`config.iva`** fornisce il catalogo dei codici IVA, includendo descrizioni, regole di assoggettamento, split payment e mapping necessari per l’invio delle fatture al Sistema di Interscambio (SDI).

---
### 🎯 Scopo Principale
* Centralizzare i **codici IVA** disponibili in un unico repository configurabile.
* Gestire:

  * Descrizioni estesa e breve
  * Assoggettamento fiscale
  * Aliquota percentuale (quando applicabile)
  * Natura IVA per SDI (`natura_iva_id`)
  * Conti contabili di acquisto e vendita
  * Split payment (`id_iva_split`)

---

### Vincoli e Logiche Aziendali

* **Doppia chiave**: `codice_interno` (dal 2026-08-29) è il nome **stabile**, quello
  con cui il codice si nomina dal codice applicativo; `codice` è l'etichetta che
  l'utente può cambiare. Entrambi univoci.
  ⭐ È la convenzione del progetto, e serve a una cosa sola: **un rename fatto
  dall'utente non deve rompere niente**. Chi cerca un codice IVA per nome usa
  `codice_interno`, mai `codice`.
  ⚠️ `codice_interno` è **bloccato in modifica** da un trigger di lock: cambiarlo
  solleva `E_CODICE_NON_MODIFICABILE`.
* ⛔ **`aliquota_iva` è anch'essa bloccata in modifica** (dal 2026-08-29). Non è
  un capriccio: le righe di fattura ne congelano una copia, e cambiare la
  percentuale sotto un codice già usato farebbe divergere i documenti vivi da
  quelli emessi. Per una percentuale nuova si **conia un codice nuovo**.
  Lo stesso blocco vale per `natura_iva_id` e `assoggettamento_id`, che dicono
  *perché* un codice a 0% non è imponibile. Tutte e tre sollevano
  `E_IVA_TRATTAMENTO_IMMUTABILE`, e il lock è dichiarato nel registro
  `dbops.automation_lock_columns`. Su `assoggettamento_id` la regola esisteva dal
  2025 in un trigger scritto a mano, con un codice poi ritirato; dal 2026-09-23
  passa anche lei dal registro.
* **`storicizza`**: la tabella partecipa allo storico (acceso il 2026-08-29 su
  tutte le righe: la macchina c'era già, il rubinetto era chiuso).
  * …
* **Aliquota vs. assoggettamento**: se `assoggettamento_iva_id` è diverso da vuoto, **l’`aliquota_iva` non può essere valorizzata** (dev’essere zero o lasciata al default).
* **Split payment**: `id_iva_split` può essere valorizzato per indicare che il codice IVA segue la normativa di split payment. In questo caso punta ricorsivamente a un codice “reale” in `config.iva`, definendo a quale aliquota reale si collega il meccanismo di split.
* **Natura IVA per SDI**: `natura_iva_id` fa riferimento a `config.iva_natura(id)`, fornendo il codice natura necessario per la trasmissione al SDI.
* **Conti contabili**:

  * `conto_iva_acquisti_id` → deve essere un conto di tipo acquisto
  * `conto_iva_vendita_id` → deve essere un conto di tipo vendita

---

### Relazioni e Indici

* **FK**:

  * `natura_iva_id` → `config.iva_natura(id)`
  * `conto_iva_acquisti_id` → `config.conti_contabili(id)`
  * `conto_iva_vendita_id` → `config.conti_contabili(id)`
  * `id_iva_split` → `config.iva(id)` (ricorsivo)
* **Indice**: `IX_IVA_DESC` su `desc_iva` per ricerche testuali performanti

---

### Trigger Associati

1. **`trg_iva_ins_upd_check_conti_iva`**

   * **Quando**: `BEFORE INSERT OR UPDATE`
   * **Cosa**: verifica la corretta tipologia dei conti IVA (acquisto vs vendita).
2. **`trg_upd_iva_audit_data_user`**

   * **Quando**: `BEFORE UPDATE`
   * **Cosa**: popola automaticamente i campi `data_update` e `user_update` per l’audit.

---

### Vantaggi Operativi

* **Conformità normativa**: split payment e natura IVA per SDI gestiti automaticamente.
* **Integrità referenziale**: FK e trigger garantiscono correttezza dei conti e dei codici natura.
* **Riduzione degli errori**: constraint e trigger prevengono valori non validi per assoggettamento e aliquota.
* **Velocità di ricerca**: indice su `descrizione` per filtrare rapidamente le descrizioni.

---

> **“Un modello di dati IVA ben governato semplifica la compliance fiscale e riduce i rischi di errore durante la compilazione e trasmissione delle fatture.”**
