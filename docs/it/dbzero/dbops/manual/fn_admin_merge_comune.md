## 📘 Documentazione Concettuale – Funzione `dbops.fn_admin_merge_comune`

> 👀 **Vedi anche**
>
> • [dbops.fn_admin_merge_stradario](/dbzero/dbops/funzioni/fn_admin_merge_stradario)
> • [config.comuni](/dbzero/config/tabelle/comuni)

---
### 🎯 Scopo Principale

(rev 2026-09-12)

**Fonde due comuni**: sposta i riferimenti dal comune di origine a quello di destinazione e
registra l'evento come trasformazione amministrativa in `storico.comune_trasformazioni`.
⚠️ Quella tabella sta nello schema `storico` ma **non è una tabella di storico**: è
il **registro delle fusioni**, scritto solo da qui e letto da
[script.fn_get_vie_discendenti](/dbzero/script/funzioni/fn_get_vie_discendenti). Non ha
una madre, non ha il trigger, non entra nella mappa dello scope.

Serve a un fatto del mondo reale: i comuni si fondono, cambiano nome, vengono soppressi. Gli
indirizzi già registrati devono continuare a essere validi, e le ricerche sul comune nuovo
devono trovare anche ciò che era stato inserito col vecchio.

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
`E_COMUNE_NON_TROVATO` / `E_STRADARIO_NON_TROVATO`) si coniano quando avrà un
chiamante applicativo — non prima, perché un codice senza consumatore è un
registro che non cala.

⚠️ È un'operazione **amministrativa e non reversibile** dall'applicazione: il prefisso
`fn_admin_` lo dichiara. Va eseguita sapendo che cosa tocca.

---

{% include-markdown "signature-core.md" %}
