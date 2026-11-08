## 📘 Documentazione Concettuale – Tabella `dbops.messaggi_errore_codici_legacy`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — il catalogo dei codici
> * [config.messaggi_errore](/dbzero/config/tabelle/messaggi_errore) — le frasi dei codici
> * [dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy) — l'altro registro, da non confondere

---

### 🎯 Scopo Principale

Il registro del debito ereditato sulla convenzione dei nomi dei codici errore (`E_` o `W_`, poi
maiuscole, cifre e trattini bassi): ci va un codice che arriva da fuori già fuori convenzione e che
non conviene rinominare. È a zero righe, e resta.

Il database impedisce di registrarci un codice conforme: nel registro del debito non si mette ciò
che debito non è.

---

### ⭐ A zero righe, e non si toglie

Tolta la tabella il comportamento non cambierebbe, ma:

* bisognerebbe mettere mano al controllo del guardrail dei codici errore che legge questo registro
  — l'unica cosa che tiene la convenzione — in un presidio verde, il momento peggiore per toccarlo;
* sparirebbe il meccanismo già pronto per la prossima eredità di codici.

Un registro vuoto non è un registro inutile: è un registro in pari, ed è l'unico modo per
distinguere «nessun debito» da «nessuno lo sta più misurando».

---

### ⚠️ Non è una whitelist di eccezioni

Una famiglia nuova con una semantica sua si risolve **allargando la convenzione**, non registrandola
qui: è stato così per i warning `W_`, che non sono codici sbagliati ma un'altra categoria.

Per questo non c'è una colonna `motivo`: un'eccezione andrebbe giustificata, un debito ereditato
deve solo essere smaltito. L'orologio è `data_registrazione`.

---

### ⚠️ Da non confondere con l'altro registro

[dbops.codici_errore_senza_policy](/dbzero/dbops/tabelle/codici_errore_senza_policy) misura un
debito diverso: codici conformi senza regola di risposta nel backend. Questo riguarda il **nome**
del codice, quello il suo **trasporto**; i due registri si escludono per vincolo.

---

### Chi lo legge

Il guardrail della CI sui codici errore, `scripts/sql/guardrail_codice_errore_strutturato.sql`:
ogni codice fuori convenzione deve stare qui, e una voce che nel frattempo è stata rinominata va
tolta. Se il registro manca, il guardrail fallisce invece di saltare i controlli. Nessun pgTAP lo
legge.

---

### Note di migrazione

* 2026-08-05 — nasce con 57 voci (`piano-db-classe-codici-errore` §5.5); lo stesso giorno la
  convenzione si allarga ai `W_`.
* 2026-08-07 — arriva a zero, l'ultima voce col rinomino di `MESSAGGIO_NON_DEFINITO` in
  `E_MESSAGGIO_NON_DEFINITO`.
* 2026-08-08 — Tid decide di non toglierla.
* 2026-11-08 — perde `tx_id`, `data_update` e `user_update`, che nessun trigger scriveva: la tabella
  la scrive solo la migrazione, dal CSV (regola dello scrittore, `automazione-db.md` §1.1;
  `brief-db-revisione-dbops`, giro 7-bis). Esce dal registro `dbops.marcatori_automazione_debito`.

---

{% include-markdown "signature-core.md" %}
