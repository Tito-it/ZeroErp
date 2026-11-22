## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_vettori_gen_codice`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.vettori](/dbzero/anagrafiche/tabelle/vettori) — la tabella di cui genera il codice
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — la riga `vettori`: prefisso, separatore, cifre
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

`anagrafiche.trgfn_vettori_gen_codice` assegna il codice a un vettore che nasce senza, chiedendolo a
`script.fn_generate_codice` per la riga `vettori` di `config.sistema_codici` (forma `VET-0000001`). Un codice
passato da chi scrive resta quello.

---

### Quando genera

Scatta prima di un inserimento e prima di una modifica della colonna `codice`. Genera quando il codice è assente o
fatto di soli spazi; altrimenti lascia la riga com'è.

---

### ⭐ Non è scritta a mano

La funzione, la sequenza `anagrafiche.vettori_codice_seq` e il trigger `trg_vettori_a10_gen_codice_ins_upd` li crea
`script.trgfn_config_sistema_codici_sync_gen_codice` quando nasce o cambia la riga di `config.sistema_codici`. Il
corpo è lo stesso di ogni generatore della famiglia, e cambia solo la riga. Si governa dalla configurazione: con
`usa_sequenza` spento l'automazione toglie funzione e trigger, e una modifica a mano del corpo dura fino alla
prossima scrittura della riga, che lo ricrea dal modello.

---

### Il codice generato non si cambia

Il lock della colonna (`trg_vettori_a10_lock_columns_upd`) rifiuta ogni modifica del codice con
`E_CODICE_NON_MODIFICABILE`. I trigger della stessa fase girano in ordine di nome, e il generatore viene prima del
lock: una modifica che svuota il codice ne riceve uno nuovo, e il lock la rifiuta come cambio. Il codice si salva in
maiuscolo, dal trigger della fase successiva.

---

### Codici errore

* `E_SEQUENZA_NON_CONFIGURATA` — da `script.fn_generate_codice`, quando la riga di configurazione o la sua sequenza
  mancano.

La funzione non solleva codici suoi.

---

### Test

* `db/pgtap/anagrafiche/test-vettori-gen-codice.sql` — la riga di configurazione, la sequenza, la funzione e il
  trigger creati dall'automazione; un vettore senza codice riceve un `VET-` a sette cifre, che poi non si cambia.

---

### Note di migrazione

* 2026-08-21 — nasce con la riga `vettori` di `config.sistema_codici`. La sequenza è partita oltre il più alto dei
  codici `VET-` già scritti a mano, perché il primo numero generato non urtasse `uq_vettori_codice`.

---

{% include-markdown "signature-core.md" %}
