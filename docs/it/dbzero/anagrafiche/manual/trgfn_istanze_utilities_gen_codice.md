## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_istanze_utilities_gen_codice`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.istanze_utilities](/dbzero/anagrafiche/tabelle/istanze_utilities) — la tabella del codice
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — la configurazione del codice
>
> Approfondimento funzioni:
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice) — il generatore
> * [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice) — chi crea questa funzione e il suo trigger
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco del codice
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — la forma normalizzata del codice

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_istanze_utilities_gen_codice` assegna il codice di un'istanza quando chi scrive non lo
passa, dalla configurazione `istanze_utilities` di `config.sistema_codici`.

---

### Un codice passato vince

Scatta alla nascita della riga e quando una modifica nomina il codice. Un codice assente o di soli spazi si
sostituisce con quello di `script.fn_generate_codice`, che compone prefisso, separatore e numero della
sequenza dedicata (oggi `IFO`, `-` e sette cifre). Un codice passato da chi scrive non si tocca.

In modifica la generazione non cambia l'identità della riga: il blocco di colonna scatta dopo, e un codice
svuotato e rigenerato è un codice cambiato (`E_CODICE_NON_MODIFICABILE`). Con la porta di manutenzione
aperta il blocco tace, e svuotare il codice dà davvero alla riga un codice nuovo.

---

### ⚠️ È generata dalla configurazione

La funzione e il suo trigger li crea il trigger di `config.sistema_codici` dalla riga di configurazione, con
lo stesso corpo per ogni tabella col codice generato.

* Una modifica a mano si perde alla prossima scrittura della riga di configurazione.
* Con `usa_sequenza` spento la funzione e il trigger si tolgono: una nuova istanza senza codice si ferma
  allora sul NOT NULL della colonna, con un errore tecnico.
* Il legame è per nome: senza la riga `istanze_utilities` il generatore risponde `E_SEQUENZA_NON_CONFIGURATA`.

---

### Codici errore

* `E_SEQUENZA_NON_CONFIGURATA` — dal generatore, quando manca la configurazione.

---

{% include-markdown "signature-core.md" %}
