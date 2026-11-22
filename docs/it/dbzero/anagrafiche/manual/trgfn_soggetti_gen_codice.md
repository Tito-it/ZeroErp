## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_soggetti_gen_codice`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.soggetti](/dbzero/anagrafiche/tabelle/soggetti) — la tabella di cui scrive `codice`
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — prefisso, separatore e lunghezza del codice
>
> Approfondimento funzioni:
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice) — il codice, dalla configurazione e dalla sequenza
> * [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice) — chi crea questa funzione e il suo trigger
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco del codice scritto
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — il codice in maiuscolo

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_soggetti_gen_codice` assegna il codice interno a un soggetto scritto senza codice (o con un
codice vuoto). Un codice dato da chi scrive, per esempio da un'importazione, resta com'è.

---

### Il codice viene dalla configurazione

Il trigger non calcola niente: chiede il codice a `script.fn_generate_codice` per la voce `soggetto` di
`config.sistema_codici`, che dice prefisso, separatore e lunghezza del numero (`SGT-` e sette cifre) e consuma
la sequenza della tabella. Il legame con la configurazione è il nome della voce, non una chiave esterna.

---

### ⚠️ La funzione è generata

La funzione, la sequenza e il trigger li crea `script.trgfn_config_sistema_codici_sync_gen_codice` quando la
voce di `config.sistema_codici` nomina tabella e colonna e chiede la sequenza. Tutte le funzioni di generazione
del codice del progetto hanno lo stesso corpo per questo motivo. Ne seguono tre cose:

* **un ritocco a mano non dura**: la funzione si riscrive dal modello a ogni scrittura della voce;
* **non si toglie cancellandola**: si spegne dalla configurazione (la sequenza non più richiesta), che toglie da
  sé trigger e funzione;
* **cambiare tabella o colonna della voce sposta gli oggetti**, senza avvisi.

---

### Il codice scritto non si cambia

In modifica il trigger scatta solo quando la scrittura nomina `codice`. Il codice è bloccato da
`script.trgfn_lock_columns`, che per nome viene dopo: chi svuota il codice ne riceve uno nuovo, e il blocco
rifiuta il cambio (`E_CODICE_NON_MODIFICABILE`). Con la porta di manutenzione aperta il blocco non parla, e
svuotare il codice ne assegna davvero uno nuovo, consumando un numero della sequenza.

---

### ⚠️ Che cosa oggi non copre

* **Un soggetto può nascere senza codice.** La colonna ammette NULL: con la voce di configurazione spenta il
  trigger non c'è, nessuno genera il codice, e nessun vincolo ferma la riga.

---

### Codici errore

Il trigger non ne solleva di suoi.

* `E_SEQUENZA_NON_CONFIGURATA` — da `script.fn_generate_codice`: la voce `soggetto` manca, non nomina tabella e
  colonna, o la sequenza non esiste.
* `E_CODICE_NON_MODIFICABILE` — dal blocco: il codice scritto cambia.

---

{% include-markdown "signature-core.md" %}
