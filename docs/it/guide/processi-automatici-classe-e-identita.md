# Guida — I lavori automatici: che natura hanno e per conto di chi girano

> (latest review 06-09-2026)
>
> Destinatari: chiunque debba capire, aggiungere o controllare un lavoro che il
> sistema fa da solo — sviluppatori, analisti, e chi guarda se stanotte è andato
> tutto bene.
>
> Vedi anche
>
> * [Gestione delle code di lavoro](/guide/gestione-code-di-lavoro) — come funziona la coda che esegue i lavori
> * [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali) — l'elenco dei lavori a orario
> * [Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job) — dove si leggono le esecuzioni
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come funzionano i controlli che si vedono qui
> * [dbops.processi](/dbzero/dbops/manual/processi) — il registro di cui parla tutta questa guida

---

## In una frase

Ogni lavoro che il sistema fa da solo è **registrato**, ha una **natura
dichiarata**, e se tocca i dati di un'azienda gira **per conto di qualcuno** —
non in incognito.

---

## 1. Il problema, raccontato com'è successo

Un lavoro notturno doveva sistemare alcune tabelle. Ha smesso di funzionare a
febbraio. Ce ne siamo accorti a **settembre**.

Non era un caso raro né un bug esotico. Erano tre cose messe insieme:

* nessuno sapeva **quali lavori automatici esistessero**: non c'era un elenco;
* quando uno falliva, il fallimento **non lasciava traccia** — il registro delle
  esecuzioni restava con l'ultimo esito buono, di sei mesi prima;
* e non c'era modo di chiedersi *«questo lavoro tocca i dati di un'azienda? e
  allora per conto di chi li tocca?»*, perché quella domanda non aveva un posto
  dove essere scritta.

⭐ **Il guasto peggiore di un sistema che lavora da solo non è l'errore: è il
silenzio.** Un errore lo si vede. Un lavoro che non parte assomiglia in tutto e
per tutto a un lavoro che non aveva niente da fare.

Questa guida racconta come è stato chiuso quel silenzio.

---

## 2. Il registro: l'elenco di ciò che esiste

Il punto di partenza è un elenco: [dbops.processi](/dbzero/dbops/manual/processi).

Una riga per ogni lavoro automatico. C'è il suo nome, che cosa fa, e le due cose
che decidono tutto il resto: **di che natura è** e **dove gira**.

Se un lavoro non è in quell'elenco, per il sistema non esiste — e infatti non
riesce nemmeno a firmare le proprie esecuzioni.

---

## 3. Le tre nature, e la domanda che le separa

Prima la divisione era a due: *lavori di manutenzione* e *lavori che toccano il
lavoro vero*. Non bastava, perché metteva nello stesso mucchio cose molto
diverse.

Oggi le nature sono **tre**, e si sceglie rispondendo a una domanda sola:

> **Questo lavoro scrive dati che appartengono a un'azienda in particolare?**

| Natura | Vuol dire | Esempi |
| --- | --- | --- |
| **MANUTENZIONE** | tiene in ordine il database. Non guarda i dati di nessuno in particolare | generare i controlli automatici, pulire ciò che non serve più |
| **AMMINISTRAZIONE** | riguarda le persone e gli accessi, non le aziende | disattivare gli utenti scaduti |
| **DOMINIO** | tocca il lavoro vero: fatture, contratti, listini, email ai clienti | il giro di fatturazione, la chiusura di ciò che è scaduto, l'invio delle email |

⚠️ **Non è un'etichetta di comodo.** Solo i lavori di **DOMINIO** hanno bisogno
di sapere *per conto di chi* stanno lavorando — ed è da questa parola che
discende tutto il capitolo 5.

### Il caso che spiega perché serviva la terza

Un lavoro notturno chiude ciò che è scaduto. La sua natura sembra
«manutenzione»: gira alle cinque del mattino, non lo chiede nessuno.

Ma le cose che chiude sono **contratti** e **versioni di listino** — cioè
documenti di un'azienda precisa. Se sbagliasse perimetro, chiuderebbe i
contratti di qualcun altro.

⇒ È di **DOMINIO**, anche se gira di notte e nessuno lo ha chiesto. *Il momento
in cui parte non dice niente sulla sua natura; dice qualcosa solo ciò che
scrive.*

---

## 4. Dove gira un lavoro — e la regola nuova

Un lavoro può partire da quattro posti diversi:

| Canale | Chi lo fa partire |
| --- | --- |
| **PGAGENT** | un orologio: ogni notte, ogni ora |
| **COMMAND** | un comando lanciato a mano o da uno script |
| **CODA** | una persona che ha premuto un pulsante |
| **CODA_AUTOMATICA** | un orologio che invece di lavorare **mette in coda** un lavoro |

### ⭐ La regola: chi suona la sveglia non è chi fa il lavoro

> **Nessun lavoro di DOMINIO viene eseguito dentro l'orologio.**

L'orologio (pgAgent) può **svegliare**: mette il lavoro in coda e finisce lì il
suo compito. A eseguirlo è la coda, con un'identità vera e con tutti i controlli
accesi.

⛔ Perché non può farlo l'orologio stesso, in due punti:

1. **Dentro l'orologio nessuno ha un nome.** Il lavoro girerebbe senza poter
   dire per conto di chi sta scrivendo, e le protezioni che si basano su quel
   nome non potrebbero fare niente.
2. **Dentro l'orologio un fallimento non arriva a nessuno.** È esattamente com'è
   andata al lavoro fermo da febbraio.

Il passaggio si vede bene sulla chiusura di ciò che è scaduto: l'orologio ora
chiama [fn_accoda_chiusura_scadenze](/dbzero/dbops/manual/fn_accoda_chiusura_scadenze),
che **accoda un lavoro per ogni azienda** invece di farne uno solo per tutte. Se
l'azienda A dà problemi, B e C vengono comunque servite — prima un intoppo su
una fermava tutto, per tutti, in silenzio.

---

## 5. Per conto di chi lavora

Questa è la parte nuova, ed è quella che vale la pena capire anche senza essere
tecnici.

Quando una persona usa il gestionale, il sistema sa chi è e le fa vedere **solo
le aziende di sua competenza**. Non è una cortesia dell'interfaccia: è il
database stesso a filtrare.

Un lavoro automatico, invece, storicamente non era nessuno. Per farlo lavorare
gli si dava un **passe-partout**: un accesso che vede tutto e per cui il filtro
semplicemente non si applica. Funzionava, ma voleva dire che il perimetro di un
lavoro notturno dipendeva soltanto da come era scritta la sua ricerca. Un errore
lì non lo fermava nessuno.

⭐ **Oggi ogni lavoro di DOMINIO ha un suo tesserino**, uno per azienda: è un
utente tecnico, creato da
[fn_crea_utente_tecnico](/dbzero/script/manual/fn_crea_utente_tecnico), a cui è
associato l'elenco delle aziende che quel lavoro può servire.

⇒ Il perimetro non è più una promessa scritta nella ricerca: è il database che
lo garantisce, come per le persone.

L'elenco di chi lavora per chi si legge in un posto solo:
[vw_processi_roster](/dbzero/dbops/manual/vw_processi_roster) — per ogni lavoro,
tutte le aziende che serve e con quale tesserino.

⚠️ **Un tesserino si spegne a quattro livelli diversi** (il legame, l'identità,
il ruolo, l'utente). Basta che se ne spenga uno perché il lavoro si fermi —
quindi guardarne uno solo basta a sbagliare diagnosi. Per questo esiste
[fn_riattiva_utente_tecnico](/dbzero/script/funzioni/fn_riattiva_utente_tecnico),
che li riaccende **tutti insieme**.

⛔ E un tesserino **non è un permesso in più**: quegli utenti non hanno nessun
profilo, nessuna capacità speciale. Il loro potere è soltanto l'elenco delle
aziende che possono toccare. Dare a chi spedisce le email i permessi per
fatturare sarebbe stato regalare potere che nessuno aveva chiesto.

---

## 6. Come si vede se è andata bene

### Il giornale delle esecuzioni

Ogni corsa lascia una riga in
[maintenance.job_run_log](/dbzero/maintenance/manual/job_run_log): quando è
partita, quanto ci ha messo, com'è finita — e adesso anche **chi era**: quale
lavoro, e con quale tesserino.

### ⭐ Il fallimento che spariva

C'era un difetto sottile e va raccontato, perché è il cuore della storia del
capitolo 1.

Quando un lavoro falliva, il sistema scriveva diligentemente la riga «è andata
male» — e subito dopo l'errore **annullava anche quella riga**. Il registro
tornava com'era: nessuna traccia. In sei mesi, nessun lavoro dell'orologio è
mai riuscito a lasciare una riga rossa.

Oggi il verbale del fallimento viene scritto su **una linea separata**
([fn_job_run_log_failure](/dbzero/maintenance/manual/fn_job_run_log_failure)),
che l'annullamento non porta via. Il lavoro fallisce come prima — ma stavolta
lo dice.

### I controlli che guardano il quadro

Non si va a memoria: ci sono viste che rispondono a una domanda ciascuna, e che
**devono poter arrivare a zero**.

| Vista | La domanda a cui risponde |
| --- | --- |
| [vw_processi_dominio_senza_emittente](/dbzero/dbops/manual/vw_processi_dominio_senza_emittente) | c'è un lavoro di dominio che non sa dire di chi sono i dati che tocca? |
| [vw_processi_dominio_senza_difesa](/dbzero/dbops/manual/vw_processi_dominio_senza_difesa) | c'è una tabella toccata da un lavoro di dominio e non protetta? |
| [vw_processi_dominio_senza_identita](/dbzero/dbops/manual/vw_processi_dominio_senza_identita) | c'è un lavoro di dominio senza tesserino? |
| [vw_emittenti_non_serviti](/dbzero/dbops/manual/vw_emittenti_non_serviti) | c'è un'azienda che nessuno sta servendo? |
| [vw_processi_dominio_su_pgagent](/dbzero/dbops/manual/vw_processi_dominio_su_pgagent) | qualcuno sta ancora eseguendo dentro l'orologio? |
| [vw_processi_che_bypassano](/dbzero/dbops/manual/vw_processi_che_bypassano) | è rimasto in giro un passe-partout? |
| [vw_run_senza_attore](/dbzero/dbops/manual/vw_run_senza_attore) | c'è una corsa che non dice chi l'ha fatta? |
| [vw_coda_lavori_da_guardare](/dbzero/dbops/manual/vw_coda_lavori_da_guardare) | c'è un lavoro in coda che si è fermato e nessuno se n'è accorto? |

### ⚠️ Un debito dichiarato non è un allarme

Qualche riga in quelle viste ci resta di proposito. Sono i casi che
**sappiamo** di dover ancora sistemare, e che qualcuno ha messo per iscritto:
compaiono marcate come **debito dichiarato**, con la spiegazione accanto.

⇒ Quello che deve stare a zero non è il totale: è il numero di righe che
**nessuno ha dichiarato**. Una riga con un nome e un motivo è un lavoro in
programma. Una riga che non se l'aspettava nessuno è un allarme.

⚠️ E il prezzo va detto: dichiarare un debito **zittisce** il controllo su quel
caso. Per questo dichiararlo richiede scrivere il perché, e non è un gesto che
si fa distrattamente.

---

## 7. Aggiungere un lavoro nuovo

In ordine, e nessuno dei passi è facoltativo:

1. **Registralo** in [dbops.processi](/dbzero/dbops/manual/processi): nome,
   natura, canale.
2. **Dichiara che cosa tocca** in
   [dbops.processi_bersagli](/dbzero/dbops/tabelle/processi_bersagli): le
   tabelle su cui scrive e, per ciascuna, come si risale all'azienda.
3. **Se è di DOMINIO**, dagli un tesserino per ogni azienda che deve servire, e
   poi controlla che [vw_emittenti_non_serviti](/dbzero/dbops/manual/vw_emittenti_non_serviti)
   sia vuota.
4. **Se deve girare a orario e ha natura di dominio**, l'orologio lo **accoda**,
   non lo esegue: vedi [fn_accoda_lavoro](/dbzero/dbops/manual/fn_accoda_lavoro)
   e la [guida delle code](/guide/gestione-code-di-lavoro).
5. **Fai in modo che firmi le proprie corse**, così non finisce in
   [vw_run_senza_attore](/dbzero/dbops/manual/vw_run_senza_attore).

⚠️ Un lavoro registrato come DOMINIO **non può essere accodato senza operatore**:
il sistema lo rifiuta. Non è una formalità — è la regola che impedisce a un
lavoro di dominio di tornare a girare in incognito.

---

## 8. Che cosa questa guida non dice

* **Come funziona la coda** (chi la svuota, cosa succede a un lavoro che
  fallisce, come si ritenta): [Gestione delle code di lavoro](/guide/gestione-code-di-lavoro).
* **L'elenco dei lavori a orario e le loro schede**:
  [Processi pgAgent funzionali](/guide/processi-pgagent-funzionali).
* **Dove si leggono le esecuzioni, e come si estende il tracciamento**:
  [Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job).
* **Come sono fatti i controlli** che qui si usano soltanto:
  [Presidi e registri del debito](/guide/presidi-e-registri-del-debito).
* **Come si scrivono gli errori e dove finiscono**:
  [Messaggi di errore e generazione log](/guide/Messaggi-di-Errore-e-Generazione-Log).
