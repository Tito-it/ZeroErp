## 📘 Documentazione Concettuale – View `dbops.vw_emittenti_non_serviti`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi_identita](/dbzero/dbops/manual/processi_identita)
>
Approfondimenti funzioni:
>
[script.fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico)

---
### 🎯 Scopo Principale
(latest review 04-09-2026)

Elenca le coppie **(processo di dominio, azienda emittente)** per cui **non
esiste un utente tecnico**.

> ⚠️ **Deve restare vuota.** Ogni riga è un'azienda che quel processo, di
> fatto, non lavorerà mai.

---

### ⭐⭐ Il guasto che copre NON ASSOMIGLIA A UN ERRORE

È la ragione per cui questa vista esiste, e va letta prima di tutto il resto.

Manca l'utente tecnico per l'azienda X. Che cosa succede quando il lavoro
notturno parte?

1. il lavoro **parte regolarmente**;
2. la row level security, non trovando l'utente nel perimetro di X, mostra
   **zero righe**;
3. il run chiude con **«FATTO, 0 elaborate»**.

⛔ Nessun errore. Nessun allarme. Nessun log rosso. E l'azienda X **non viene
mai fatturata**, finché qualcuno non se ne accorge contando i soldi.

⭐ «Non è successo niente» lo nota solo chi si aspettava qualcosa. Questa vista
è ciò che rende di nuovo visibile un silenzio.

---

### ⚠️ Rev 2026-09-04 — la domanda è cambiata, e la prima versione era inservibile

La prima versione chiedeva: *«a questo utente manca la riga per l'azienda X?»*.

Era scritta sull'idea che un utente tecnico avesse una **lista** di aziende. Il
modello dice il contrario: un utente ha **un solo** emittente. ⇒ Le «righe
mancanti» sarebbero state tutte tranne una, **per costruzione**, e la vista non
sarebbe mai arrivata a zero.

La domanda giusta è l'altra:

> **Per la coppia (processo, azienda), esiste UN UTENTE?**

⇒ Ed è per questo che un processo con **zero** utenti compare una volta per
ogni azienda attiva: non è rumore, è la risposta giusta — dice **quali** aziende
sono scoperte, non solo che manca qualcosa.

---

### Che cosa NON entra

* Le aziende **disattivate**: non vanno servite, e tenerle qui terrebbe la vista
  rossa per sempre.
* I processi su canale **CODA**: girano con l'identità dell'operatore che li
  accoda.

---

### ⚠️ La vista non CONCEDE niente

Elenca ciò che manca; **non crea** utenti e non assegna perimetri. Il perimetro
di un processo automatico lo decide una persona, chiamando
[fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico) con
l'azienda che ha scelto. ⛔ Un sistema che si dà da solo i permessi che gli
mancano non è un sistema che si configura: è un sistema senza perimetro.

---

### Esempio d'uso

```sql
-- Quali aziende nessuno sta servendo, e per quale lavoro
SELECT processo_codice, canale, emittente_codice
FROM dbops.vw_emittenti_non_serviti
ORDER BY processo_codice, emittente_codice;
```

Origine: `docs/it/dev/work-done/brief-db-processi-automatici-identita-e-perimetro.md` §4.5 e §8.

---

{% include-markdown "signature-core.md" %}
