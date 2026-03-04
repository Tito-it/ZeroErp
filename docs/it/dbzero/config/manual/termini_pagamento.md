## 📘 Documentazione Concettuale – Tabella `config.termini_pagamento`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)   
> • [vendite.fatture_scadenze](/dbzero/vendite/tabelle/fatture_scadenze)   

---

### 🎯 Scopo Principale

(latest review 15-01-26)
`config.termini_pagamento` definisce i **termini (piani) di pagamento** riutilizzabili nel sistema. Ogni record rappresenta una regola parametrica per generare **rate/scadenze** a partire dalla data documento (o da altra data base), con controllo su intervalli, fine mese e ripartizione degli importi.

"Termini" qui sostituisce il concetto di *piano rate* ed è richiamabile da **Cliente / Ordine / Preventivo / Fattura** (con eventuale snapshot sulla fattura) per produrre le righe in `vendite.fatture_scadenze`.

---

### 🧭 Flusso di utilizzo

1. **Selezione termini**: a livello Cliente/Documento si indica un `termini_pagamento` (o si usa un default).
2. **Snapshot (opz.)**: in fattura si fotografa la configurazione utilizzata.
3. **Generazione scadenze**: l’engine calcola le rate (date + importi) secondo i parametri e le salva in `vendite.fatture_scadenze`.

---

### 🔑 Semantica campi principali

* `codice` / `codice_interno` → identificativi esterno e interno (quest’ultimo da trattare come **immutabile**).
* `descrizione` → testo descrittivo del termine.
* `numero_rate` (`SMALLINT`, **NOT NULL**) → quante rate generare (es. 1, 2, 3, 12).
* `tipo_offset` (`CHAR(1)`, default `N`) → modalità di calcolo intervalli:

  * `G` = a **giorni**
  * `M` = a **mesi**
  * `F` = a giorni ma con **fine mese**
  * `N` = **nessun intervallo** (rata unica o delega al solo `primo_offset_giorni`)
* `intervallo` (`SMALLINT`) → passo tra una rata e l’altra **quando applicabile** (vedi NOTE).
* `primo_offset_giorni` (`SMALLINT`, opz.) → offset della **prima rata** quando differisce dal passo standard (es. 45/30/30).
* `unita_intervallo` (`CHAR(1)`) → unità dell’intervallo; vedi **anomalie**.
* `ripartizione` (`UGUALI` | `PROPORZIONALE` | `LIBERA`) → come ripartire il totale documento tra le rate.
* `arrotondamento_metodo` (`HALF_UP` | `HALF_DOWN` | `HALF_EVEN`) e `arrotondamento_decimali` → policy di arrotondamento per importi rata.
* `attivo` → abilitazione a catalogo.
* **Audit**: `data_*`, `user_*`.

---

### 🔒 Vincoli e indici

* **PK**: `id` (identity).
* **UNIQUE**: `codice` e `codice_interno`.
* **CHECK**:

  * `chk_termini_pagamento_tipo_offset` → `tipo_offset ∈ {G,M,F,N}`.
  * `chk_termini_pagamento_ripartizione` → ripartizione ammessa.
  * `chk_termini_pagamento_arrotondamento_metodo` → metodi arrotondamento ammessi.
  * `chk_termini_pagamento_intervallo_range` → `0..365` (o `NULL`).
  * `chk_termini_pagamento_intervallo_uso` → lega `tipo_offset` e presenza di `intervallo`.

---

### ⚠️ Anomalie / punti da chiarire

1. **`intervallo` è `NOT NULL` ma i CHECK consentono `NULL`**
   La colonna è definita **`NOT NULL`**, tuttavia i vincoli `chk_termini_pagamento_intervallo_range` e `chk_termini_pagamento_intervallo_uso` fanno riferimento a `intervallo IS NULL` in alcuni casi (`M`, `N`).
   **Azione**: rendere `intervallo` **NULLABLE** e mantenere i CHECK correnti **oppure** eliminare i rami `IS NULL` e impostare un valore convenzionale (es. `0`). La prima opzione è più chiara.

2. **Duplicazione semantica `unita_intervallo` vs `tipo_offset`**
   Entrambi esprimono la granularità; i CHECK usano **solo `tipo_offset`**.
   **Azione**: valutare di **rimuovere `unita_intervallo`** e usare solo `tipo_offset` (`G/M/F/N`). Se serve mantenerla per retrocompatibilità, aggiungere un **trigger** che ne assicuri la coerenza (`G/F → 'G'`, `M → 'M'`, `N → NULL`).

3. **Mancano vincoli su range**

   * `numero_rate` → aggiungere CHECK `numero_rate >= 1` (ed eventualmente un massimo ragionevole, es. `<= 60`).
   * `arrotondamento_decimali` → aggiungere CHECK `0..6` come per altre tabelle.
   * `primo_offset_giorni` → se valorizzato, coerente solo per `G`/`F`; **trigger** o CHECK condizionale.

4. **Immutabilità `codice_interno`**
   Il commento indica “immutabile”, ma **manca** un trigger di lock (come in `config.tipi_indirizzi`).
   **Azione**: aggiungere `script.trgfn_lock_columns('codice_interno', 'CODICE_NON_MODIFICABILE')`.

---

### 🧪 Esempi d’uso (logica applicativa)

* **30/60/90 giorni** → `numero_rate=3`, `tipo_offset='G'`, `intervallo=30`.
* **45/30/30** → `numero_rate=3`, `tipo_offset='G'`, `intervallo=30`, `primo_offset_giorni=45`.
* **Fine mese + 60** → `numero_rate=2`, `tipo_offset='F'`, `intervallo=30` (o 0), `primo_offset_giorni=NULL`, `fine_mese` gestito a livello calcolo per la prima rata, poi passo standard.
* **Rata unica** → `numero_rate=1`, `tipo_offset='N'` (intervallo `NULL`).

> La gestione **fine mese** per `F` si applica all’offset a giorni con round a EOM; per i mesi (`M`) l’allineamento al fine mese va deciso lato algoritmo (es. spostare al mese successivo mantenendo il giorno o clamps a EOM).

---

### ✅ Best practice

* **Idempotenza**: la funzione di generazione scadenze (per fattura) fa `DELETE` + `INSERT` atomici.
* **Ultima rata = ribilanciamento**: applica arrotondamento per rata e ribilancia i centesimi sull’ultima.
* **Snapshot in fattura**: salva i parametri effettivi usati (in caso di modifiche future dei termini).
* **Catalogo coerente**: disattiva (`attivo=false`) i termini non più in uso anziché modificarli in-place.

---


### 👓 Ruolo nel sistema

`config.termini_pagamento` è il **motore parametrico** per generare piani di scadenza coerenti, riutilizzabili e governati. Allineato a `vendite.fatture_scadenze`, consente di standardizzare politiche di incasso e mantenerne la **storicità** tramite snapshot in documento.
