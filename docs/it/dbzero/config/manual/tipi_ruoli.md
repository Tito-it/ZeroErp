## 📘 Documentazione Concettuale – Tabella `config.tipi_ruoli`

>  👀 **Vedi anche** 

> Approfondimento Tabelle:  
>
[anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/tabelle/soggetti_ruoli)    


La tabella **`config.tipi_ruoli`** serve a definire i ruoli che un soggetto (individuo o società) può assumere all'interno del software Zero ERP. In questo modo la tabella `soggetti` rimane generica e memorizza solo i dati anagrafici di base, mentre `tipi_ruoli` specifica in quali ruoli (cliente, fornitore, gestore, ecc.) ciascun soggetto si trova, a seconda delle esigenze aziendali.

---
### 🎯 Scopo Principale
* **Distinzione dei ruoli**: consente di assegnare a ogni record della tabella `soggetti` uno o più ruoli funzionali (es. cliente, fornitore, gestore).
* **Flessibilità operativa**: un soggetto può assumere ruoli differenti in contesti diversi (ad esempio un fornitore che può diventare cliente in altre transazioni).
* **Ruolo "gestore"**: l’azienda stessa che utilizza il software viene registrata in `soggetti` e associata al ruolo interno “gestore” per identificare i dati dell’utente principale o amministratore del sistema.

---

### Collegamenti con Altre Tabelle

* **`anagrafica.soggetti_ruoli`**

  * Un soggetto può avere più righe in `config.tipi_ruoli`, ad esempio:

    * `soggetto_id = 5`, `cd_int_ruolo = "CLIENTE"`
    * `soggetto_id = 5`, `cd_int_ruolo = "FORNITORE"`
* **Constraint di unicità**

  * Il campo `codice_interno` è un codice interno univoco (`UNIQUE`) per ogni riga di `tipi_ruoli`, utilizzato come riferimento stabile nelle logiche applicative.
  * Il campo `codice` identifica il ruolo in modo testuale/abanndonabile (es. "CLIE" per cliente, "FORN" per fornitore), anch’esso unico.

---

### Vantaggi Operativi

* **Invarianza del codice interno**
  Grazie al trigger di lock, il `codice_interno` rimane stabile, semplificando tutte le logiche applicative che fanno riferimento al codice ruolo (es. permessi, reportistica, workflow).

* **Audit automatico**
  Il trigger di audit garantisce la tracciabilità delle modifiche, facilitando la diagnostica storica e la sicurezza: ogni aggiornamento registra data e utente di modifica.

* **Supporto multi-ruolo**
  Un soggetto può ricoprire più ruoli contemporaneamente o nel tempo: ad esempio un partner commerciale che è sia fornitore che cliente, senza dover duplicare i dati anagrafici di base.

* **Estendibilità futura**
  Se in futuro si volessero introdurre ruoli nuovi o specifici (es. “partner logistico”, “rappresentante”), è sufficiente aggiungere una nuova riga in `tipi_ruoli`, senza modificare lo schema della tabella `soggetti`.

---

> **"Una tabella leggera e versatile per gestire, senza duplicazioni, i ruoli operativi dei soggetti nel sistema Zero ERP, garantendo integrità, audit e flessibilità."**
