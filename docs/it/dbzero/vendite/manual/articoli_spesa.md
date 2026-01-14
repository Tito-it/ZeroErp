## 📘 Documentazione Concettuale – Tabella `vendite.articoli_spesa`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> * [vendite.articoli_gruppi](/dbzero/vendite/tabelle/articoli_gruppi)
> * [vendite.articoli_tipologie](/dbzero/vendite/tabelle/articoli_tipologie)
>

La tabella **`vendite.articoli_spesa`** mappa gli **articoli** su specifiche **voci di spesa** (es. energia, gas, oneri, servizi), consentendo di categorizzare le righe di documento per finalità **gestionali, fiscali e di stampa**. Include una **descrizione per fattura** dedicata, utile a migliorare la leggibilità del documento verso il cliente.

---

### 🎯 Scopo Principale

(latest review 14-01-26)
* Definire un **catalogo centralizzato** delle voci di spesa utilizzabili in fatturazione.
* Abilitare **riepiloghi e totalizzazioni** per voce di spesa nei documenti (es. bolletta, fattura).
* Offrire un **testo di stampa** specifico per la voce di spesa, distinto dalla descrizione interna
  
**L'utilizzo della descrizione come testo di stampa può essere più utile nel mondo Utilities.Resta sempre la possibilità di utilizzo come totalizzatore aggiuntivo/alternativo al gruppo.**

---

### 🔒 Vincoli e Logiche Aziendali

* **Unicità**: ogni voce di spesa è identificata da un `codice` univoco.
* **Obbligatorietà**: `descrizione` deve essere sempre valorizzata.
* **Gestione documentale**: `descrizione_fattura` (se presente) è il testo mostrato nei documenti; in alternativa viene usata la descrizione estesa.
* **Ciclo di vita**: il flag `attivo` consente di dismettere una voce senza cancellare lo storico.
* **Audit automatico**: i campi di audit vengono mantenuti aggiornati dal trigger standard.

---

### 🔗 Relazioni e Indici

* **Relazioni**: utilizzata come riferimento in `vendite.articoli` per associare ogni articolo alla propria voce di spesa.
* **Indice univoco**: `uq_articoli_spesa_codice` garantisce l’unicità del codice.
* **Indice funzionale**: `ix_articoli_spesa_codice_upper` abilita ricerche **case-insensitive** su `codice`.


---

### 💡 Vantaggi Operativi

* **Totalizzazione semplice**: consente di stampare subtotali per categoria di spesa.
* **Chiarezza verso il cliente**: con `descrizione_fattura` ottimizzata per il documento.
* **Governance**: controllo centralizzato delle voci utilizzabili e del loro ciclo di vita.
* **Interoperabilità**: naming coerente e indicizzazione facilitano integrazioni e query.

---

> 🧠 **“La voce di spesa è la lente con cui il cliente legge la fattura: governa descrizioni e raggruppamenti per una comunicazione chiara e professionale.”**
