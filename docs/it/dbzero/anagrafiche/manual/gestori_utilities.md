## 📚 Documentazione Tabella: `anagrafiche.gestori_utilities`

> 👀 **Vedi anche:**
>
> Approfondimento tabelle:
>
> * [anagrafiche.gestori](/dbzero/anagrafiche/gestori)
> * [config.utilities](/dbzero/config/utilities)
> * [anagrafiche.soggetti_ruoli](/dbzero/anagrafiche/soggetti_ruoli)
> * [config.tipi_ruoli](/dbzero/config/tipi_ruoli)
>
> Approfondimento funzioni:
>
> * [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---

## 🎯 Scopo Principale

La tabella `anagrafiche.gestori_utilities` gestisce l'associazione tra i gestori e le utilities disponibili nel sistema Zero ERP. Ogni gestore, identificato dal suo ruolo, può gestire una o più utilities specifiche.

---



---

## ⚙️ Vincoli e Relazioni

* **`gestore_id`**: Foreign key verso la tabella `anagrafiche.gestori` (cancellazione a cascata).
* **`utility_id`**: Foreign key verso la tabella `config.utilities` (cancellazione ristretta).
* **`uq_gest_util`**: Garantisce l'unicità dell'associazione gestore-utility.

---

## 🔍 Considerazioni di Progettazione

* Ogni gestore può essere associato a molteplici utilities.
* L'associazione non contempla ulteriori ruoli interni, in quanto il gestore stesso è già un ruolo specifico.
* Il campo `extra` offre flessibilità per la memorizzazione di dettagli contrattuali o operativi specifici per ciascuna associazione.

---

## 🚨 Gestione Errori e Audit

* Eventuali errori nel gestire la tabella sono loggati tramite la funzione `script.fn_log_and_raise_error`.
* Gli audit sono assicurati tramite i campi standard (date\_insert, user\_insert, date\_update, user\_update).

---

> 🧠 **“Questa struttura garantisce una gestione semplice e chiara delle associazioni tra gestori e utilities, facilitando la manutenibilità e la flessibilità del sistema.”**

---

{% include-markdown "signature-core.md" %}