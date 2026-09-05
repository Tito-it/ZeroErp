## 📘 Documentazione Concettuale – Funzione `dbops.fn_accoda_chiusura_scadenze()`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori)
>
Approfondimenti funzioni:
>
[dbops.fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro) ·
[dbops.fn_apply_chiusura_scadenze](/dbzero/dbops/manual/fn_apply_chiusura_scadenze)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

**Sveglia** la chiusura delle scadenze, non la esegue: mette in coda **un lavoro
per ogni azienda**, ciascuno con l'identità tecnica di quella azienda.

Il lavoro vero lo fa il worker, minuti dopo, dentro le regole di sicurezza e con
un nome.

---

### ⛔ Che cosa cambia rispetto a prima

| | prima | adesso |
| --- | --- | --- |
| chi chiude | il lavoro notturno, dentro pgAgent | il worker della coda |
| con quale identità | **nessuna** | l'utente tecnico dell'azienda |
| su quali aziende | tutte insieme | una per lavoro |
| se qualcosa va storto | non lo sa nessuno | resta scritto nella coda |

---

### ⭐ L'isolamento per azienda è il guadagno principale

Se accodare per l'azienda A fallisce, **B e C vengono accodate lo stesso**.

Prima era un giro unico: un errore su una tabella fermava la chiusura per tutte
le aziende insieme — e non lo diceva a nessuno.

> ⚠️ È anche il motivo per cui la funzione **restituisce un riepilogo** invece di
> interrompersi con un errore: chi la chiama è un lavoro notturno, e un
> riepilogo finisce nel giornale mentre un errore si perde.

---

### ⚠️ Due sveglie nello stesso giorno sono una sveglia sola

Un riavvio, una schedulazione doppia, una mano sul job: la seconda chiamata
**non produce un secondo giro di chiusure**. Restituisce gli stessi lavori.

⛔ La chiave che lo garantisce contiene *azienda* e *giorno*, e **non l'ora**:
due sveglie nello stesso giorno sono la stessa intenzione, non due.

---

### ⚠️ Il perimetro viene congelato al momento dell'accodamento

Nel lavoro messo in coda finisce anche **quale azienda** il worker dovrà
guardare.

Senza, il worker girerebbe in modalità globale: un lavoro chiesto «dentro A»
toccherebbe anche B — **e nessun errore lo direbbe**, perché le righe di B
verrebbero chiuse correttamente, solo da chi non doveva.

---

### Un'azienda senza identità non viene saltata in silenzio

Se il roster non la nomina — utente tecnico mancante o spento — non c'è niente da
accodare, e il riepilogo lo conta.

⭐ Il presidio vero però è un altro e c'è già: `dbops.vw_emittenti_non_serviti`
nomina la coppia scoperta. Qui si evita soltanto che «zero lavori» sembri un
successo.

---

### Che cosa NON è cambiato

`dbops.fn_apply_chiusura_scadenze` — quella che chiude davvero — **non si tocca**:
la chiama il worker per fare il lavoro, un'azienda alla volta.

⇒ Cambia **chi** la chiama e con quale identità, non che cosa fa.

---

### Verifica

`db/pgtap/dbops/test-fn-accoda-chiusura-scadenze.sql` — sei prove, fra cui
l'isolamento per azienda, costruito iniettando un guasto su una sola.
