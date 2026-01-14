## 📘 Documentazione Concettuale – Tabella `vendite.articoli_tipologie`

> 👀 **Vedi anche**
>
> Approfondimenti tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
> * [vendite.articoli_gruppi](/dbzero/vendite/tabelle/articoli_gruppi)
> * [vendite.articoli_spesa](/dbzero/vendite/tabelle/articoli_spesa)
>

La tabella **`vendite.articoli_tipologie`** definisce le categorie di appartenenza degli articoli, utili per raggruppamenti omogenei, analisi statistiche e applicazione di regole di fatturazione.

---

### 🎯 Scopo Principale

(latest review 14-01-26)
* Classificare gli articoli secondo **tipologie funzionali** (es. materia prima, servizi, accessori).
* Distinguere tra **descrizione estesa** e **descrizione breve**, per gestire contesti documentali differenti.
* Fornire uno strumento di aggregazione per reportistica e controlli gestionali.

**Rappresenta un modo diverso di raggruppare articoli rispetto a articoli_gruppi/spesa.**

---

### 🔒 Vincoli e Logiche Aziendali

* **Unicità**: `codice` deve essere univoco e identificare in modo chiaro la tipologia.
* **Obbligatorietà**: `descrizione` deve sempre essere valorizzata.
* **Descrizione breve**: opzionale, utilizzata nei documenti con spazio limitato (es. righe fattura sintetiche).
* **Attivazione/disattivazione**: il flag `attivo` consente di rendere obsoleta una tipologia senza cancellarla.

---

### 🔗 Relazioni e Indici

* **FK**: può essere referenziata da `vendite.articoli` per classificare ogni articolo in una tipologia.
* **Indice**: `IX_ARTICOLI_TIPOLOGIE_CODICE_UPPER` su `upper(codice)` per ricerche case-insensitive.

---

### 💡 Vantaggi Operativi

* **Omogeneità**: gli articoli sono classificati in modo coerente e confrontabile.
* **Flessibilità documentale**: gestione della descrizione breve semplifica la comunicazione sui documenti.
* **Governance**: possibilità di disattivare tipologie obsolete mantenendo lo storico.

---

> 🧠 **“La categorizzazione degli articoli tramite tipologie garantisce uniformità nei processi di vendita e facilita analisi gestionali.”**
