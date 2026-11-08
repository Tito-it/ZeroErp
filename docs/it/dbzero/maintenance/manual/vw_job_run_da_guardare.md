## 📘 Documentazione Concettuale – Vista `maintenance.vw_job_run_da_guardare`

> **Ultimo aggiornamento**: 3 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale da cui legge
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il verdetto completo e la causa dichiarata del processo
> * [dbops.cause_fallimento](/dbzero/dbops/tabelle/cause_fallimento) — il vocabolario della causa
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — a chi tocca ogni causa
> * [config.codici_errore](/dbzero/config/tabelle/codici_errore) — la causa dichiarata da un codice d'errore
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_superuser](/dbzero/maintenance/views/vw_job_run_da_superuser) — la sorella: chi si è collegato all'ultima corsa
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama dei processi, sveglia compresa
> * [dbops.vw_processi_programmazione_da_guardare](/dbzero/dbops/views/vw_processi_programmazione_da_guardare) — il presidio del lavoro che non parte o non registra
>
> Approfondimento funzioni:
>
> * [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure) — il verbale che rende visibile un fallimento
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — la porta dei job del database
> * [script.fn_sqlstate_di_ambiente](/dbzero/script/funzioni/fn_sqlstate_di_ambiente) — gli SQLSTATE che dicono «guasto dell'ambiente»
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Il posto dove guardare: i lavori automatici la cui ultima corsa vera è fallita, è rimasta
appesa, o che falliscono a intermittenza. Deve restare vuota.

---

### ⛔ Perché non basta scrivere i fallimenti

Un lavoro che fallisce lascia una riga rossa nel giornale. Ma **righe rosse in una tabella che
nessuno apre sono un silenzio nuovo**: il guasto smette di essere invisibile e diventa
illeggibile, che per chi deve accorgersene è la stessa cosa. Questa vista è la domanda fatta
al giornale.

---

### ⭐ La domanda è «quale lavoro sta andando male», non «elenca i rossi»

Si guarda l'**ultima corsa** di ogni lavoro, una riga per `jobname`. È la scelta che tiene la
vista capace di **tornare vuota**: un lavoro che ricomincia a funzionare esce da solo. Niente
colonna «visto», niente pulizia a mano. Un lavoro che fallisce molte volte in un giorno
occupa una riga, non una per fallimento.

⛔ **L'ultima corsa è l'ultima corsa vera.** Le corse **saltate** (il lock della corsia era
occupato, il lavoro non è partito) sono escluse. Una corsa appesa tiene il lock, e ogni sveglia
successiva scrive una saltata più recente di lei: se la saltata contasse come ultima corsa, il
motivo «presa e mai chiusa» non scatterebbe più, e il caso che la vista esiste per vedere lo
coprirebbe proprio la sveglia che doveva farlo emergere.

---

### Tre motivi, perché sono tre guasti diversi

| Motivo | Che cos'è successo |
| --- | --- |
| **l'ultima corsa è fallita** | il lavoro è arrivato in fondo e ha detto perché |
| **presa e mai chiusa** | ⛔ non ha parlato nemmeno il gestore d'errore: il processo è morto di colpo |
| **intermittente** | l'ultima è andata bene, oppure è in corso adesso, ma negli ultimi sette giorni il lavoro ha fallito |

⭐ **Il terzo è il più insidioso, e senza di lui la vista sarebbe cieca proprio dove serve.** Un
lavoro che fallisce e passa, fallisce e passa, ha l'ultima corsa verde: guardando solo quella
nessuno lo direbbe malato.

⚠️ Ne segue che il rientro **non è immediato**: servono sette giorni senza rossi. Ed è giusto:
un lavoro che ha fallito cinque minuti fa ha appena fallito. Per i lavori a verdetto completo
la regola è un'altra, nella sezione che segue.

`falliti_ultimi_7_giorni` dice quante **corse** fallite ha avuto il lavoro nei sette giorni che
precedono la sua **ultima corsa vera**, per tutti i lavori, anche quando non accendono più la
riga. ⭐ Conta le corse distinte (`run_uuid`), non le righe rosse: quando il chiamante di
`maintenance.fn_run_and_log` cattura l'eccezione, una corsa fallita lascia nel giornale due righe
rosse con lo stesso `run_uuid`, e contarle tutte direbbe due fallimenti dove ce n'è uno. ⚠️ La
finestra che decide l'intermittenza invece parte da adesso: per un lavoro che non gira da giorni
le due finestre non coincidono.

---

### ⭐ Il verde di un verdetto completo spegne la spia, salvo ricaduta

«Intermittente» tiene insieme **due guasti diversi**:

| Guasto | Che cos'è | Per chi |
| --- | --- | --- |
| **il residuo** | la corsa lavora una parte (una coda, un lotto): un rosso lascia indietro qualcosa che il verde dopo non riprende | i lavori a verdetto parziale |
| **l'instabilità** | il lavoro cade, si rialza, ricade | tutti |

Per un lavoro il cui ogni giro è un **verdetto completo** — ricontrolla tutto il suo
perimetro, come lo smoke notturno, le automazioni, il digest; lo dichiara il processo in
`dbops.processi.corsa_verdetto_completo` — il residuo non esiste: il verde di oggi **sostituisce**
il rosso di ieri.

⇒ Per questi lavori la riga resta accesa solo se il lavoro è **ricaduto**: nei sette giorni ci
sono almeno **due tratti rossi** separati da un verde. Un solo tratto rosso esce al primo verde.
Il motivo dice «ricaduto dopo essere tornato verde: instabile».

⭐ **Si contano i tratti, non i rossi.** Tre rossi di fila e poi verde sono un guasto riparato una
volta; rosso, verde, rosso, verde sono un lavoro che non sta in piedi.

⛔ **Perché non basta l'ultima corsa.** Un verdetto completo instabile si nasconde quando gira più
spesso di quanto lo si guardi: fra due digest l'ultima corsa è verde, e i rossi in mezzo non li
vede nessuno. La regola non legge la frequenza delle corse, che sta nelle sveglie e non nel
catalogo: guarda la forma della storia.

⚠️ **La corsa in corso non è un verdetto.** Per un verdetto completo, una corsa partita da meno di
un'ora non conta finché non chiude: un rosso seguito da un giro nuovo resta «fallita». Oltre l'ora
la corsa è appesa, come per tutti.

---

### ⚠️ La soglia di un'ora è una scelta, non una misura

Una corsa senza fine da meno di un'ora può essere semplicemente **in corso**. L'ora viene dal fatto
che questi lavori durano secondi.

⛔ La soglia vale anche per il **motivo**, non solo per l'ingresso nella vista: una corsa partita
cinque minuti fa, di un lavoro con fallimenti recenti, non è «presa e mai chiusa» ma «in corso
adesso, ma ha fallito di recente».

⛔ Una soglia dedotta dai tempi di oggi si taglierebbe addosso al carico di oggi.

---

### ⭐ A chi tocca: la causa di ogni riga

Le righe di questa vista sono guasti di natura diversa: un disco pieno va a chi gestisce il server,
la regressione di uno smoke allo sviluppo. Un destinatario unico per tutto il presidio manderebbe
metà delle righe alla persona sbagliata.

Per questo ogni riga porta una **causa** (`causa`, vocabolario `dbops.cause_fallimento`), e
`dbops.presidi_cause` dice a chi tocca:

| Causa | Chi agisce |
| --- | --- |
| `AMBIENTE` | chi gestisce il server |
| `PROGRAMMA` | lo sviluppo |
| `CONFIGURAZIONE` | l'amministratore, dalle impostazioni dell'applicazione |

La causa si decide **in quest'ordine**:

1. la corsa è appesa (morta senza chiudersi) → `AMBIENTE`, qualunque lavoro sia;
2. l'errore è passato dal database con un codice di guasto dell'ambiente (connessione, spazio o
   memoria, arresto, errore di sistema, permesso mancante, lock non ottenuto) → `AMBIENTE`. La
   lista ha una sede sola, `script.fn_sqlstate_di_ambiente`, la stessa che usano i gestori
   d'errore delle automazioni: anche loro rilanciano questi errori così come sono, e un permesso
   mancante in un'automazione arriva al sistemista, non allo sviluppo;
3. il codice d'errore dichiara la sua causa (`config.codici_errore.causa_fallimento`) → quella;
4. altrimenti decide il processo, che dichiara la natura dei suoi fallimenti
   (`dbops.processi.causa_fallimento`);
5. una corsa senza processo a catalogo → `PROGRAMMA`.

⭐ Nessuna riga resta senza causa, quindi nessuna finisce fra quelle «senza indicazione di chi
agisce».

⭐ La causa si legge dall'**ultimo fallimento**, non dall'ultima corsa: per un intermittente
l'ultima corsa è andata bene e non ha errore. `ultimo_rosso_job_run_id` dice da quale corsa è
stata letta; `job_run_id` è l'ultima corsa vera.

Una corsa **riuscita con scarti** (`E_JOB_ESITO_CON_SCARTI`: il lavoro è finito, ma alcuni
elementi sono falliti) è rossa come le altre, e il suo codice non dichiara una causa: decide il
processo, al punto 4, perché ogni scarto ha la sua.

⚠️ Per i lavori del backend il punto 2 vede il guasto dell'ambiente solo quando il backend scrive
il codice del database nel giornale (`job_run_log.sqlstate`).

---

### La sorella: `vw_job_run_da_superuser`

`maintenance.vw_job_run_da_superuser` legge lo stesso giornale con un'altra domanda: non
«com'è andata», ma «chi si è collegato». Per questo è diversa in due punti: raggruppa per processo
(il codice del processo, o in mancanza il `jobname`) e non per `jobname`, e **non esclude** le
corse saltate, perché anche una saltata dice con che ruolo la sveglia si è collegata.

---

### ⛔ Che cosa questa vista NON vede

**Il lavoro che non parte affatto.** Se nessuno lo sveglia non c'è nessuna corsa da guardare: la
vista non ha niente su cui accendersi. Lo stesso vale per un processo spento, che per scelta non
scrive nel giornale.

⇒ È scritto qui perché non sembri coperto da questa vista. Il lavoro che non parte, o che gira e
non registra, lo vede il panorama dei processi, che confronta le corse di pgAgent con il giornale
e con la tolleranza che il catalogo dichiara per ogni processo: il suo presidio è
`dbops.vw_processi_programmazione_da_guardare`.

---

### ⚠️ Chi la può vedere

Nessuna regola di riga: un giro di manutenzione **non appartiene a un'azienda**, e un perimetro
qui non vorrebbe dire niente. La vista gira coi privilegi del proprietario.

⇒ Il database la concede in lettura all'applicazione; **chi la vede lo decide il backend** con
l'area funzionale e il profilo, come per le altre viste di presidio. Nel catalogo dei presidi è
un presidio che deve restare vuoto, guardato ogni giorno, con la causa come variante: il testo
e il rimedio cambiano con la causa della riga.

---

### Test

* `db/pgtap/maintenance/test-vw-job-run-da-guardare.sql` — i casi costruiti uno per uno, compreso
  il rientro automatico e la corsa ancora in corso che non deve comparire.
* `db/pgtap/maintenance/test-job-run-saltata-v1.sql`, test 7 — la corsa appesa seguita da una
  saltata resta «presa e mai chiusa».
* `db/pgtap/maintenance/test-vw-job-run-da-guardare-causa-v1.sql` — la causa, ramo per ramo.
* `db/pgtap/maintenance/test-vw-job-run-da-guardare-verdetto-completo-v1.sql` — verdetto completo
  contro parziale, con la stessa storia di corse.
* `db/pgtap/maintenance/test-vw-job-run-da-guardare-corse-distinte-v1.sql` — una corsa fallita con
  due righe rosse dello stesso `run_uuid` conta una volta in `falliti_ultimi_7_giorni`.

---

### Note di migrazione

* 2026-09-05 — nasce, insieme al verbale fuori transazione che per la prima volta lascia nel
  giornale una corsa fallita di un job del database. Quel giorno un comando aveva ventinove
  fallimenti in un giorno: elencandoli tutti la vista sarebbe nata con ventinove righe uguali.
* 2026-10-10 — l'ultima corsa diventa l'ultima corsa vera: escluse le saltate
  (`brief-db-corsa-saltata-non-e-una-corsa`).
* 2026-10-16 — nascono `sqlstate`, `causa` e `ultimo_rosso_job_run_id`; la soglia dell'ora vale
  anche per il motivo; la lista degli SQLSTATE dell'ambiente passa a `script.fn_sqlstate_di_ambiente`
  e si allarga al privilegio mancante e al lock non ottenuto. Prima il presidio aveva un solo
  destinatario per guasti di natura diversa (`brief-db-presidio-job-run-a-chi-tocca`).
* 2026-10-18 — il verdetto completo: per quei lavori l'intermittenza scatta solo sulla ricaduta. Il
  comando del 2026-09-05 riallineava tutti gli utenti a ogni corsa: era un verdetto completo
  instabile (`brief-db-intermittente-e-verdetto-completo`).
* 2026-11-03 — `falliti_ultimi_7_giorni` conta i `run_uuid` distinti. Prima contava le righe
  rosse, e una corsa fallita il cui chiamante catturava l'eccezione contava due volte. Niente
  vincolo unico su `run_uuid`: il verbale fuori transazione resterebbe ad aspettare la
  transazione che lo chiama (`brief-db-revisione-maintenance` D10).
* 2026-11-03 — le corse riuscite con scarti diventano rosse (`E_JOB_ESITO_CON_SCARTI`) e la vista
  le vede: prima risultavano verdi (`brief-db-revisione-maintenance` D5).

---

{% include-markdown "signature-core.md" %}
