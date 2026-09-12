## 📘 Documentazione Concettuale – View `dbops.vw_coda_lavori_da_guardare`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori)
>
Approfondimenti funzioni:
>
[dbops.fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro)

---
### 🎯 Scopo Principale
(latest review 05-09-2026)

Elenca i lavori della coda che **chiedono un occhio**. Deve restare vuota.

---

### ⭐ Tre motivi, perché sono tre guasti diversi

| Motivo | Che cos'è successo | Che cosa si fa |
| --- | --- | --- |
| **fallito** | il lavoro ha esaurito i tentativi e si è arreso | si legge l'errore e si decide |
| **preso e mai chiuso** | qualcuno l'ha preso in carico e non l'ha mai concluso: il worker è morto a metà | si rimette in coda |
| **mai preso** | ⛔ nessuno l'ha nemmeno guardato: **il worker non sta girando** | si riaccende il worker |

> ⚠️ Il terzo è il più importante e il meno visibile. Un worker spento **non
> produce errori: produce assenza.** Non c'è niente da leggere, e proprio per
> questo non se ne accorge nessuno.

---

### ⛔ Perché esiste PRIMA che i processi si spostassero sulla coda

L'argomento per togliere i processi applicativi da pgAgent è che **pgAgent non
racconta i suoi fallimenti**: la traccia finisce in una tabella di sistema che
nessuno guarda e che l'applicazione non vede.

⭐ L'argomento non è teorico: un lavoro settimanale di manutenzione è morto ogni
settimana per **sei mesi**, e lo si è scoperto per caso.

⛔ Ma la coda, senza questa vista, non era meglio: al 5 settembre 2026 conteneva
**quattro lavori falliti e nessuno che li nominasse**. Spostarci il lavoro prima
avrebbe **trasferito il silenzio**, non tolto il silenzio.

⇒ Prima si costruisce il posto dove guardare, poi ci si mette il lavoro.

---

### ⚠️ Le soglie sono una scelta, non una misura

Un'ora per «preso e mai chiuso», un'ora per «mai preso».

Non vengono dai tempi osservati oggi: vengono dal fatto che **il worker gira di
continuo**, quindi un'ora di attesa non è lentezza, è qualcosa che non va.

⛔ Una soglia dedotta dal carico di oggi si taglierebbe addosso al carico di
oggi, e domani direbbe la cosa sbagliata.

---

### Che cosa resta fuori, e perché

* **ANNULLATO** — qualcuno ha deciso che non si fa.
* **archiviato** — qualcuno l'ha già guardato e messo via.

⭐ Un presidio che elenca anche ciò che è già stato visto smette di essere una
lista di cose da fare, e diventa un elenco che nessuno apre. È anche il modo in
cui questa vista **torna vuota**: si archivia ciò che si è risolto.

---

### Verifica

`db/pgtap/dbops/test-vw-coda-lavori-da-guardare.sql` — costruisce i sette casi
(i tre che devono comparire e i quattro che non devono) e li interroga per nome.
