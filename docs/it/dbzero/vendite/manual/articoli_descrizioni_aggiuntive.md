## 📘 Documentazione Concettuale – Tabella `vendite.articoli_descrizioni_aggiuntive`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
>

La tabella **`vendite.articoli_descrizioni_aggiuntive`** consente di associare agli articoli una o più **descrizioni opzionali** da utilizzare in cataloghi, documenti di vendita o comunicazioni commerciali. Ogni descrizione è **ordinabile** e **attivabile/disattivabile** senza perdita di storico.

---

### 🎯 Scopo Principale

(latest review 19-01-26)
* Estendere le informazioni dell’articolo con **testi aggiuntivi** riutilizzabili.
* Governare la **sequenza di presentazione** tramite un campo di ordinamento.
* Abilitare **varianti di testo** per contesti differenti (catalogo vs. documento fiscale).

---

### Vincoli e Logiche Aziendali

* Ogni riga è riferita a **un articolo valido** (`articolo_id`).
* Il campo `descrizione` è **obbligatorio**.
* Il campo `ordine` definisce la **posizione** di visualizzazione (default `0`).
* Il flag `attivo` permette di **sospendere** una descrizione senza cancellarla.
* I campi di **audit** (`user_insert`, `user_update`, `data_insert`, `data_update`) sono gestiti automaticamente.

---

### Relazioni e Indici

* **FK**: `articolo_id` → `catalogo.articoli.id` (aggiornamento in cascata, cancellazione ristretta).
* **Indice**: `ix_articoli_descrizioni_aggiuntive_articolo_ordine` per ottenere rapidamente le descrizioni di un articolo nell’**ordine definito**.

---

### Vantaggi Operativi

* **Riutilizzo**: un’unica base testi per più documenti/contesti.
* **Ordine e chiarezza**: presentazione controllata tramite `ordine`.
* **Governance**: possibilità di disattivare descrizioni mantenendo lo storico.

---

> **“Separare le descrizioni aggiuntive dall’anagrafica articolo garantisce riuso, ordine e coerenza nella comunicazione verso il cliente.”**
