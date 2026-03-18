## 📘 Documentazione Concettuale – Tabella `catalogo.unita_misura`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[catalogo.articoli](/dbzero/catalogo/tabelle/articoli)
>

La tabella **`catalogo.unita_misura`** contiene il catalogo delle unità di misura utilizzabili nel sistema. Ogni unità definisce la modalità di contabilizzazione, movimentazione e fatturazione degli articoli (es. pezzo, chilogrammo, standard metro cubo, kilowattora).

---
### 🎯 Scopo Principale
(latest review 13-01-26)
* Centralizzare le **unità di misura** in un unico repository.
* Fornire sia una **descrizione tecnica interna** sia una **descrizione breve** per la stampa in documenti fiscali e commerciali.
* Garantire la **coerenza** tra articoli, movimenti di magazzino e righe di fattura.

---

### Vincoli e Logiche Aziendali

* **Unicità**: `codice` deve essere univoco e identificare in modo chiaro l’unità (es. `PZ`, `KG`, `SMC`, `KWH`).
* **Obbligatorietà**: `descrizione` deve sempre essere valorizzata.
* **Descrizione fattura**: se presente, sostituisce la descrizione interna nei documenti stampati (fattura, bolletta, ordine). Se assente, viene utilizzata la descrizione estesa.
* **Attivazione/disattivazione**: il flag `attivo` consente di rendere obsoleta un’unità senza cancellarla.

---

### Relazioni e Indici

* **FK**: utilizzata come chiave esterna in `catalogo.articoli` e in tutte le tabelle di movimenti/fatturazione.


---

### Vantaggi Operativi

* **Uniformità**: gli articoli condividono un set standard di unità di misura.
* **Chiarezza documentale**: separazione tra descrizione tecnica e descrizione per stampa migliora la leggibilità delle fatture.
* **Governance**: possibilità di disattivare le unità obsolete mantenendo lo storico.

---

> **“Un’anagrafica unificata delle unità di misura assicura coerenza nei processi di magazzino e fatturazione, riducendo errori e ambiguità.”**
