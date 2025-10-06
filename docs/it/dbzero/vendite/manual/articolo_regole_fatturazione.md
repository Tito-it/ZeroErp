## 📘 Documentazione Concettuale – Tabella `vendite.articolo_regole_fatturazione`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**   
>
> • [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)    
> • [catalogo.articoli_componenti](/dbzero/catalogo/tabelle/articoli_componenti)   
> • [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)   
> • [vendite.ordini_righe](/dbzero/vendite/tabelle/ordini_righe)   
> • [vendite.fatture_righe](/dbzero/vendite/tabelle/fatture_righe)   

---

### 🎯 Scopo Principale

Questa tabella definisce, **per ciascun articolo**, le regole di business che governano:

* **Visibilità delle componenti** nei documenti (preventivi, ordini, DDT, fatture) per articoli **kit/BOM**.
* **Calcolo della quantità del padre** (se fissa o calcolata dalla somma delle componenti flaggate).
* **Arrotondamenti** (numero di decimali e metodo) per **importi** e **quantità**.

Il vincolo `UNIQUE (articolo_id)` garantisce una relazione **1:1** tra articolo e policy: ogni articolo ha una sola configurazione di regole attiva.

---

### 🧭 Collocazione nel flusso

Le regole vengono lette dal motore documentale durante:

1. **Generazione righe documento** (preventivo → ordine → DDT → fattura).
2. **Esplosione kit/BOM**: determinano se mostrare solo il **padre**, il **padre + componenti**, o **solo le componenti**.
3. **Determinazione quantità padre**:

   * `fissa` → quantità del padre invariata.
   * `somma_componenti_flaggate` → quantità padre calcolata come somma di componenti selezionate.
4. **Calcolo importi e totali**: applica i decimali e i metodi di arrotondamento configurati.

> I valori utilizzati nei documenti vengono **copiati** nelle righe in fase di generazione, così eventuali modifiche successive alla policy non alterano i documenti già emessi.

---

### 🔑 Campi chiave

* `visibilita_componenti`: `solo_padre` | `padre_componenti` | `solo_componenti`
  → controlla la visibilità dei componenti.
* `calcolo_qta_padre`: `fissa` | `somma_componenti_flaggate`
  → stabilisce la logica di calcolo della quantità padre.
* `arrotondamento_importi_dec`, `metodo_arrotondamento_importi`: precisione e metodo per gli importi.
* `arrotondamento_quantita_dec`, `metodo_arrotondamento_quantita`: precisione e metodo per le quantità.
* `meta`: campo estensibile (criteri speciali, regole di esclusione, override per canale, ecc.).
* `trg_articolo_regole_fatturazione_upd_audit_data_user_generic`: trigger che aggiorna `data_update` e `user_update` (audit standard).

---

### 🧪 Esempi d’uso

* **Esplosione kit (visibilità)**

  * `solo_padre`: una sola riga riepilogativa.
  * `padre_componenti`: mostra il padre e i componenti.
  * `solo_componenti`: solo righe componenti in stampa e calcolo.
* **Quantità padre**

  * `fissa`: la quantità del padre rimane quella richiesta.
  * `somma_componenti_flaggate`: la quantità padre è la somma delle componenti definite come rilevanti.
* **Arrotondamenti**

  * Importi: `arrotondamento_importi_dec` e `metodo_arrotondamento_importi`.
  * Quantità: `arrotondamento_quantita_dec` e `metodo_arrotondamento_quantita`.

---

### 🔗 Relazioni e dipendenze

* **FK** → `catalogo.articoli(id)` (ON UPDATE CASCADE, ON DELETE RESTRICT).
  Previene l’eliminazione di articoli con regole definite.

---

### ✅ Aspetti positivi

* Coerenza 1:1 con `catalogo.articoli`.
* Check constraint completi su domini e range (0–6 decimali).
* Audit aggiornamento gestito da trigger.
* Default coerenti e semantica chiara (`solo_padre` / `fissa` / `HALF_UP`).

---

### ⚠️ Osservazioni e possibili migliorie

1. **Storicizzazione** – L’unicità su `articolo_id` impedisce versioning delle regole (ok se gestisci snapshot nei documenti).
2. **Campo `meta`** – Valutare `NOT NULL` per coerenza con altri schemi.
3. **HALF_EVEN** – Non supportato nativamente da PostgreSQL; richiede funzione custom.
4. **Precisione quantità** – Allineare con i decimali ammessi in `catalogo.unita_misura`.
5. **Flag componenti** – Definire la logica di selezione componenti “flaggate” (es. in `catalogo.articoli_componenti`).


---

### 👓 Importanza nel sistema

Tabella cruciale per la **consistenza dei calcoli** e la **leggibilità dei documenti**.
Stabilisce come un articolo composito viene visualizzato e valorizzato, garantendo uniformità nei calcoli di quantità e importi in tutto il ciclo documentale (`preventivo → ordine → DDT → fattura`).

