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

### La ricerca universale: tre colonne, tre domande

Il catalogo dice alla ricerca universale come trattare ogni ruolo. Sono tre
domande diverse, e ognuna ha la sua colonna:

| Colonna | Domanda | Esempio |
| --- | --- | --- |
| `ricerca_visibile` | il ruolo si cerca? | sì per cliente e fornitore, no per emittente fiscale e gestore |
| `entita_tabella` (+ `entita_colonna_codice`) | dove si cerca il **codice** dell'entità? | cliente → la vista dei codici di billing account |
| `entita_esistenza` | quale **tabella** fa esistere il soggetto-ruolo per chi guarda? | cliente → `anagrafiche.clienti`, fornitore → `anagrafiche.fornitori` |

* **`ricerca_visibile`**: dal 2026-10-10 lo controlla il database, non solo il menu
  della ricerca. Un ruolo non ricercabile chiesto alla ricerca risponde
  `E_TIPO_RUOLO_NON_RICERCABILE`.
* **`entita_esistenza`**: un soggetto-ruolo si mostra nella ricerca se ha almeno una
  riga di quella tabella che chi guarda vede; il perimetro (per il cliente, quello
  dell'emittente) lo fa la RLS della tabella. Vuota: il soggetto-ruolo si mostra se
  esiste. Accetta **solo tabelle, mai viste**: una vista senza `security_invoker`
  spegnerebbe la RLS senza dirlo. Lo stato dell'entità non conta: un cliente
  chiuso si ritrova.
* `entita_tabella` ed `entita_esistenza` sono due colonne apposta: chi cambia dove si
  cerca il codice non deve cambiare, senza saperlo, chi si vede.

La regola che le legge è una sola, `script.fn_predicato_soggetto_ruolo_visibile`,
per la lista e per il dettaglio della ricerca. Il guard
`config.trgfn_tipi_ruoli_guard_entita_ref` valida le due colonne di tabella in
scrittura.

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
