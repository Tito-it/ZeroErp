## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_fornitori_gen_codice`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.fornitori](/dbzero/anagrafiche/tabelle/fornitori) — la tabella di cui genera il codice
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — la riga `fornitori`: prefisso, separatore, cifre
>
> Approfondimento funzioni:
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice) — il generatore, a cui delega
> * [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice) — l'automazione che crea questa funzione, la sequenza e il trigger
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il lock che rende il codice immutabile
>
> Guide:
>
> * [Automazione DB](/guide/automazione-db) — gli oggetti che il database crea da una riga di configurazione

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_fornitori_gen_codice` assegna il codice a un fornitore che nasce senza, chiedendolo a
`script.fn_generate_codice` per la riga `fornitori` di `config.sistema_codici` (forma `FORN0000001`, senza
separatore). Un codice passato da chi scrive resta quello.

---

### Quando genera

Scatta prima di un inserimento e prima di una modifica della colonna `codice`. Genera quando il codice è assente o
fatto di soli spazi; altrimenti lascia la riga com'è. Il legame con la configurazione è per nome: la funzione chiede
la riga `fornitori`, e una riga rinominata non si trova più (`E_SEQUENZA_NON_CONFIGURATA`).

---

### ⭐ Non è scritta a mano

La funzione, la sequenza e il trigger `trg_fornitori_a10_gen_codice_ins_upd` li crea
`script.trgfn_config_sistema_codici_sync_gen_codice` quando nasce o cambia la riga di `config.sistema_codici`. Il
corpo è lo stesso di ogni generatore della famiglia, e cambia solo la riga. Si governa dalla configurazione: con
`usa_sequenza` spento l'automazione toglie funzione e trigger, e una riga che punta a un'altra tabella li sposta.
Una modifica a mano del corpo dura fino alla prossima scrittura della riga, che lo ricrea dal modello.

---

### Il codice generato non si cambia

Il lock della colonna (`trg_fornitori_a10_lock_columns_upd`) rifiuta ogni modifica del codice con
`E_CODICE_NON_MODIFICABILE`. I trigger della stessa fase girano in ordine di nome, e il generatore viene prima del
lock: una modifica che svuota il codice ne riceve uno nuovo, e il lock la rifiuta come cambio. Il codice si salva in
maiuscolo, dal trigger della fase successiva.

La porta di manutenzione del lock (`zeroerp.allow_lock_columns_override`) lascia passare il cambio, ma solo fuori
dall'applicazione: lì svuotare il codice dà davvero un codice nuovo e consuma un numero della sequenza.

---

### Codici errore

* `E_SEQUENZA_NON_CONFIGURATA` — da `script.fn_generate_codice`, quando la riga `fornitori` o la sua sequenza
  mancano.

La funzione non solleva codici suoi.

---

### Test

* `db/pgtap/anagrafiche/test-fn-crea-fornitore-v1.sql` — un fornitore creato senza codice, o con la chiave del
  codice a null, lo riceve dal trigger.

---

{% include-markdown "signature-core.md" %}
