## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_stradario`

> 👀 **Vedi anche**
>
> • [dbops.fn_admin_merge_comune](/dbzero/dbops/funzioni/fn_admin_merge_comune)
> • [script.fn_get_vie_discendenti](/dbzero/script/funzioni/fn_get_vie_discendenti)

---
### 🎯 Scopo Principale

(rev 2026-09-12)

Gemella di `fn_admin_merge_comune`, un livello più in basso: **fonde due vie** dello
stradario, registrando la trasformazione in `storico.stradario_trasformazioni` — che,
come la sorella, è il **registro delle fusioni** e non una tabella di storico (nessuna
madre, nessun trigger, nessuna riga nella mappa dello scope).

Stesso fatto del mondo reale — le vie cambiano nome, vengono accorpate, cambiano numerazione —
e stessa necessità: gli indirizzi esistenti restano validi, e chi cerca la via nuova trova
anche lo storico.

⭐ La catena delle trasformazioni è percorribile con
[script.fn_get_vie_discendenti](/dbzero/script/funzioni/fn_get_vie_discendenti), che risale
ricorsivamente da una via a tutte quelle che ne sono derivate.

⭐ **L'audit si scrive dalla porta, una volta, a fine lavoro** (rev 2026-09-12):
[dbops.fn_audit_log_once](/dbzero/dbops/funzioni/fn_audit_log_once) con esito `OK`,
i parametri ricevuti, il conteggio delle righe ripuntate e la durata. È la stessa
forma di tutte le funzioni di `dbops`, ed è l'unica che l'applicazione può usare.

⛔ **Fino al 2026-09-11 questa scheda diceva il contrario** — *«scrive prima di
operare, così resta traccia del tentativo»* — e il corpo aveva **tre** difetti,
non uno: apriva una riga con status `'STARTED'`, che il `CHECK` del registro non
ammette (la funzione **falliva alla prima riga**, quindi non ha mai fuso niente);
chiudeva con un `UPDATE` del registro, che dal 2026-09-11 l'applicazione non può
più fare; e nel ramo d'errore scriveva una riga `ERROR` che il `RAISE` annullava
comunque. Il ramo `ERROR` resta, perché ha senso con il canale fuori transazione
(dblink); in transazione si annulla col resto, com'era.

⏳ **Debito dichiarato**: le tre validazioni (origine = destinazione, origine non
trovata, destinazione non trovata) sollevano ancora `RAISE EXCEPTION` in chiaro,
senza codice registrato. È uno strumento DBA che oggi nessuno chiama
dall'applicazione; i codici (`E_MERGE_ORIGINE_UGUALE_DESTINAZIONE`,
`E_STRADARIO_NON_TROVATO`) si coniano quando avrà un
chiamante applicativo — non prima, perché un codice senza consumatore è un
registro che non cala.

---

{% include-markdown "signature-core.md" %}
