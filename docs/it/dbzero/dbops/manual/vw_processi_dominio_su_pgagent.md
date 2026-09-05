## 📘 Documentazione Concettuale – View `dbops.vw_processi_dominio_su_pgagent`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi)
>
Approfondimenti funzioni:
>
[dbops.fn_accoda_chiusura_scadenze](/dbzero/dbops/manual/fn_accoda_chiusura_scadenze)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

Rende **verificabile** una regola presa il 5 settembre 2026:

> ⛔ Nessun processo che tocca i documenti di un'azienda **esegue** dentro
> pgAgent.

Deve restare vuota. Al momento della scrittura lo è.

---

### Perché quella regola

Dentro pgAgent un processo:

* **non ha un'identità** — quindi nessun perimetro: tocca i dati di tutte le
  aziende insieme;
* **non ha un posto dove raccontare un fallimento** — la traccia finisce in una
  tabella di sistema che nessuno guarda.

⭐ Non è una preoccupazione teorica: un lavoro settimanale è morto ogni settimana
per **sei mesi** senza che nessuno lo sapesse.

---

### ⭐ Che un job pgAgent SVEGLI un processo resta lecito

E non è una scappatoia.

| | |
| --- | --- |
| ⛔ **eseguire** dentro pgAgent | tocca i documenti senza identità e senza perimetro |
| ✅ **svegliare** da pgAgent | mette in coda un lavoro e non tocca niente |

Un job che si limita ad accodare, se muore, **non ha fatto danni** — e il lavoro
vero resta tracciato nella coda, che sa dire se è fallito.

⇒ Per questo il registro descrive **il processo**, non chi suona la sveglia: il
canale diventa `CODA_AUTOMATICA`.

---

### ⛔ Perché è una vista e non un vincolo

Un vincolo sarebbe più stretto, e proprio per questo sbagliato:

1. **quando è nata**, la riga da spostare c'era ancora: un vincolo avrebbe fatto
   fallire l'aggiornamento del database **prima** di poterla spostare;
2. **anche dopo**, il registro dei processi è **catalogo** e si cambia da un
   file di configurazione. Un vincolo trasformerebbe un errore di configurazione
   in un aggiornamento rotto — cioè in un problema di tutti, invece che di
   quella riga.

---

### Verifica

`db/pgtap/dbops/test-vw-processi-dominio-su-pgagent.sql` — verifica che sia
vuota **e** che si accenda su un caso costruito: una vista vuota è
indistinguibile da un controllo spento.
