## 📘 Documentazione Concettuale – Funzione `dbops.fn_conta_presidio`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [dbops.presidi](/dbzero/dbops/manual/presidi) — *il catalogo da cui questa funzione legge tutto*
>
**Approfondimento guide:**
>
• [Presidi e registri del debito](/guide/presidi-e-registri-del-debito)
> • [Row Level Security](/postgresql/row-level-security)
>

### 🎯 Scopo Principale
(latest review 10-09-2026)

Dice **quante righe di una vista di controllo chiedono un intervento**.

Una riga sola, in apparenza. Esiste per un difetto che non si vede guardando il
codice, e che avrebbe reso bugiardo tutto il resto.

---

### 🔴 Il difetto: uno zero può essere una cecità, non un dato

Il database filtra le righe che un utente può vedere in base a **chi è**. Tre
delle viste di controllo attraversano tabelle protette così, e sono scritte per
rispettare quel filtro — è giusto che lo facciano.

Ma il programma che manda l'avviso è un **comando lanciato da un timer**: non ha
un utente, non ha una veste. Per quelle tre viste il filtro non trova nessuno a
cui dare il permesso, e restituisce **zero righe**.

⛔ E su una vista che *deve restare vuota*, «zero righe» e «non ho potuto vedere»
**si scrivono nello stesso modo**.

> Il programma che sorveglia i controlli riferirebbe *«tutto a posto»* **proprio
> perché è cieco.**

È il difetto peggiore della famiglia: non fa rumore, e dà la sensazione della
copertura senza averla.

---

### ⭐ Come lo risolve, e perché è accettabile

La funzione appartiene al **proprietario** delle tabelle, e in questo database il
proprietario legge fuori dal filtro per righe. Quindi conta quello che c'è
davvero.

È lo stesso identico meccanismo, con la stessa identica motivazione, di
`config.fn_accoda_email_sistema`, che esiste perché il reset della password deve
poter scrivere anche senza un utente in sessione.

Due limiti la rendono sicura, e sono la sostanza:

**1. Torna un numero, mai le righe.** Attraversa i perimetri per dire *quanti*,
non *quali*. Il dettaglio lo va a guardare una persona con il suo perimetro, e in
un messaggio di posta non finisce nessun dato fuori scope.

**2. Conta solo ciò che è a catalogo.** Il nome della vista lo risolve dentro
[`dbops.presidi`](/dbzero/dbops/manual/presidi), e se non lo trova **rifiuta**.
Non è prudenza: è ciò che le impedisce di diventare una porta per leggere il
conteggio di qualunque tabella del database aggirando i filtri.

⚠️ **E rifiuta, non torna zero.** Uno zero sarebbe indistinguibile da una vista
sana: è la stessa forma del difetto che la funzione è nata per chiudere.

⭐ L'alternativa era un ruolo tecnico che scavalca i filtri. Sarebbe stata più
larga — avrebbe letto tutto, righe comprese — e sarebbe comparsa come riga in
`dbops.vw_processi_che_bypassano`: un debito nuovo su uno dei controlli che
questo lavoro sta censendo.

---

### Che cosa conta, esattamente

Dipende da cosa dice il catalogo per quella vista:

* **senza colonna di stato** → conta la vista **intera**. È il caso normale: una
  vista che deve restare vuota, e ogni riga è un allarme;
* **con una colonna di stato** → conta le righe **diverse dallo stato atteso**.

Il secondo caso serve alle viste dove una riga può essere lì **di proposito**,
perché qualcuno ha dichiarato quel debito. Contarle tutte suonerebbe su una cosa
già decisa.

⛔ **Si conta «diverso dall'atteso» e non «uguale a uno degli allarmi»**, ed è la
scelta portante: uno stato **nuovo**, aggiunto domani alla vista, con la seconda
forma non sarebbe nell'elenco e cadrebbe nel silenzio. Con questa cade
nell'allarme, e chi lo aggiunge deve venire a decidere.

⚠️ Il confronto è *è distinto da* e non *è diverso da*: un valore assente non è
«atteso», e con il confronto secco quella riga uscirebbe dal conteggio **in
silenzio**.

---

### ⚠️ Una cosa da non confondere

Il conteggio passa da questa funzione per **tutte** le viste, non solo per le
tre. Così l'allarme è onesto ovunque e chi chiama non deve scegliere.

La colonna `perimetro` del catalogo dice **un'altra cosa**: se chi legge può
anche **elencare** le righe, oltre a contarle. Per le tre viste protette la
risposta è no.

---

*Brief: `docs/it/dev/work-done/brief-db-un-destinatario-per-i-presidi.md`.*
