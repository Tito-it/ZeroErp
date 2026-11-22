## 📘 Documentazione Concettuale – Trigger function `anagrafiche.trgfn_billing_account_gen_codice`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.billing_account](/dbzero/anagrafiche/tabelle/billing_account) — la tabella su cui è montata
> * [config.sistema_codici](/dbzero/config/tabelle/sistema_codici) — prefisso, separatore e lunghezza del codice
>
> Approfondimento funzioni:
>
> * [script.fn_generate_codice](/dbzero/script/funzioni/fn_generate_codice) — il generatore comune
> * [script.trgfn_config_sistema_codici_sync_gen_codice](/dbzero/script/funzioni/trgfn_config_sistema_codici_sync_gen_codice) — chi crea questa funzione e il suo trigger
> * [script.trgfn_lock_columns](/dbzero/script/funzioni/trgfn_lock_columns) — il blocco del codice dopo la nascita
> * [script.trgfn_codice_maiuscolo](/dbzero/script/funzioni/trgfn_codice_maiuscolo) — il codice salvato in maiuscolo
>
> Guide:
>
> * [Numerazione dei documenti e codici](/guide/numerazione-documenti-e-codici) — i codici generati delle anagrafiche

---

### 🎯 Scopo Principale

`anagrafiche.trgfn_billing_account_gen_codice` assegna il codice di un billing account quando chi scrive non lo
fornisce, o lo fornisce vuoto: lo chiede a `script.fn_generate_codice('billing_account')`, che compone prefisso
`BAC`, separatore `/` e un numero a sette cifre dalla sequenza della tabella.

Un codice fornito non si tocca; lo porta in maiuscolo un altro trigger, in fascia `a15`.

---

### ⭐ Una funzione generata, non scritta a mano

Funzione, sequenza e trigger nascono da soli dalla riga `billing_account` di `config.sistema_codici`: li crea
con DDL dinamico il trigger di quella tabella, `script.trgfn_config_sistema_codici_sync_gen_codice`, e tutte le
funzioni `trgfn_*_gen_codice` hanno lo stesso corpo. Ne seguono tre cose:

* un ritocco a mano non dura: la funzione si riscrive col modello quando si riscrive la riga di configurazione;
* si spegne dalla configurazione (`usa_sequenza` a falso), non con un `DROP`;
* il legame fra la tabella e la sua riga è il nome `billing_account`, una stringa e non una FK: senza la riga
  ogni inserimento senza codice risponde `E_SEQUENZA_NON_CONFIGURATA`.

---

### Il codice non cambia: lo tiene il blocco

Il trigger scatta anche alla modifica del codice. Il codice però è bloccato dopo la nascita
(`trg_billing_account_a10_lock_columns_upd`, `E_CODICE_NON_MODIFICABILE`), e il blocco gira dopo questo trigger
nella stessa fascia: chi svuota il codice ne riceve uno nuovo, che il blocco rifiuta come modifica. Con
l'override del blocco attivo (manutenzione) questa rete non c'è, e svuotare il codice cambia davvero l'identità
del billing account.

---

### ⚠️ Che cosa oggi non copre

* **Con `usa_sequenza` a falso** il generatore restituisce un valore vuoto senza errore, e la riga senza codice
  urta il NOT NULL della colonna: un errore tecnico, senza un codice di dominio che dica la causa.

---

### Codici errore

La funzione non solleva errori propri.

* `E_SEQUENZA_NON_CONFIGURATA` — da `script.fn_generate_codice`, senza la riga di configurazione o la sequenza.
* `E_CODICE_NON_MODIFICABILE` — dal blocco di colonna, a una modifica del codice.

---

### Test

Nessun file suo. Il codice generato alla nascita lo verifica `db/pgtap/anagrafiche/test-fn-crea-cliente-v1.sql`.

---

{% include-markdown "signature-core.md" %}
