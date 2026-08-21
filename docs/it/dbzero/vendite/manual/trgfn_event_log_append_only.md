## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_event_log_append_only()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [vendite.event_log](/dbzero/vendite/tabelle/event_log)
>
Approfondimento funzioni:
> • [script.fn_log_and_raise_error](/dbzero/script/funzioni/fn_log_and_raise_error)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Rende `vendite.event_log` **append-only**: si può solo inserire. `UPDATE` e `DELETE` sono
rifiutati, sempre, senza eccezioni e senza condizioni.

`event_log` è lo stream temporale degli eventi tecnici e funzionali dei domini vendite —
pipeline, commesse, SDI, fatture. Il suo valore sta interamente nel fatto che sia
**immodificabile**: un registro che si può riscrivere non racconta cosa è successo, racconta
cosa qualcuno preferisce che risulti. Non ci si può appoggiare per una ricostruzione né per
una verifica.

---

### Aggancio

Trigger `trg_event_log_append_only_ud` — `BEFORE UPDATE OR DELETE` su `vendite.event_log`,
`FOR EACH ROW`.

---

### Regole applicate

Nessuna condizione: il corpo è una sola riga.

```sql
RAISE EXCEPTION 'vendite.event_log e'' append-only: operazione % non consentita', TG_OP;
```

`TG_OP` nel messaggio distingue `UPDATE` da `DELETE`. `INSERT` non è agganciato, quindi
l'inserimento passa senza costi.

⚠️ **Non c'è porta di servizio.** Nessuna GUC di bypass, nessun ramo per un utente
privilegiato. Per una manutenzione straordinaria l'unica strada è disattivare il trigger
(`ALTER TABLE ... DISABLE TRIGGER`), che richiede il proprietario della tabella ed è
un'operazione volutamente visibile.

---

### ⚠️ Solleva con `RAISE EXCEPTION` diretta, fuori dalla convenzione

A differenza di tutti gli altri guard del progetto, questa funzione **non** passa da
`script.fn_log_and_raise_error`. Conseguenze concrete, non formali:

* **non esiste un codice errore** per questo rifiuto. Lo SQLSTATE è `P0001` generico, e non
  c'è nulla in `config.codici_errore` da mappare;
* **il tentativo non viene registrato** in `error_log`. Chi prova a cancellare una riga dello
  stream degli eventi non lascia traccia da nessuna parte — il che è particolarmente
  spiacevole proprio per la tabella il cui scopo è tenere traccia;
* **il backend non può mapparlo** a uno stato HTTP e a un'azione UI: gli arriva un errore di
  database con un messaggio in italiano da interpretare a stringa.

È un debito noto della classe «codici errore», documentato qui perché la funzione lo
introduce in un punto insolitamente delicato.

---

### Codici errore

Nessuno registrato. `RAISE EXCEPTION` diretta con SQLSTATE `P0001` e messaggio:
*«vendite.event_log e' append-only: operazione UPDATE|DELETE non consentita»*.

⚠️ Un `throws_ok` pgTAP su questa funzione **deve** asserire sul messaggio
(`throws_like`), non sul solo SQLSTATE: `P0001` da solo accetterebbe qualunque altro errore
di dominio.

---

{% include-markdown "signature-core.md" %}
