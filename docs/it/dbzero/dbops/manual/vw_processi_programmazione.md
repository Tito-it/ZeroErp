## 📘 Documentazione Concettuale – View `dbops.vw_processi_programmazione`

> 👀 **Vedi anche**
>
Approfondimenti tabelle:
>
[dbops.processi](/dbzero/dbops/manual/processi)
>
[maintenance.job_run_log](/dbzero/maintenance/manual/job_run_log)
>
Approfondimenti viste:
>
[dbops.vw_processi_programmazione_da_guardare](/dbzero/dbops/manual/vw_processi_programmazione_da_guardare)

---
### 🎯 Scopo Principale
(latest review 07-09-2026)

È il **panorama** dei lavori che il sistema fa da solo: per ognuno, chi dovrebbe
svegliarlo, quando girerà, e quando ha girato davvero.

Risponde a una domanda che prima non aveva risposta scritta da nessuna parte:

> **Questo lavoro sta ancora girando?**

⭐ E la risposta non viene da una fonte sola: viene dal **confronto** fra due.
Lo scheduler del database dice *quando* ha fatto partire un lavoro; il giornale
delle corse dice *che cosa quel lavoro ha fatto*. Finché le due si somigliano,
va bene. Quando si smentiscono, è successo qualcosa che nessuno ha raccontato.

---

### ⭐ La colonna che vale più di tutte è `stato`

E il valore che conta è **«è girato e non l'ha detto»**: lo scheduler dichiara di
aver fatto partire il lavoro, il giornale non ne sa niente.

È la firma esatta di un lavoro che muore **prima** di riuscire a raccontarlo. Non
è un caso di scuola: un lavoro settimanale di manutenzione è morto ogni settimana
per **sei mesi**, con l'ultimo verdetto agli atti a «fatto», e lo si è scoperto
per caso. Questo confronto lo avrebbe trovato in un giorno.

| stato | che cosa vuol dire |
| --- | --- |
| `OK` | lo scheduler lo sveglia e il giornale lo registra |
| `GIRA_E_NON_REGISTRA` | ⛔ girato secondo lo scheduler, mai arrivato al giornale |
| `MAI_PARTITO` | programmato, acceso, e non è mai partito |
| `IN_ATTESA` | job pgAgent acceso, mai partito, ma la sua prima corsa è ancora da venire: non è un guasto (dal 2026-10-14) |
| `IN_RITARDO` | job pgAgent che ha già girato, ma la corsa dovuta è passata da più di un'ora: il programmatore si è fermato (dal 2026-10-14) |
| `JOB_SPENTO` | il lavoro esiste ma qualcuno l'ha disattivato |
| `JOB_ASSENTE` | il catalogo dichiara un lavoro che lo scheduler non ha |
| `NON_PROGRAMMATO` | nessuno ha dichiarato chi lo sveglia |
| `FUORI_PORTATA` | la sveglia vive fuori dal database |
| `SU_RICHIESTA` | lo sveglia una persona: una cadenza non esiste |

---

### ⚠️ Due stati non sono guasti, e per ragioni **opposte**

È la distinzione entrata il 2026-09-07, e serve perché prima quei due casi
stavano sotto la stessa parola — facendo contare insieme cose diverse.

| | Che cosa vuol dire | Perché non è un guasto |
| --- | --- | --- |
| **`FUORI_PORTATA`** | il lavoro lo fa partire il sistema operativo **e il catalogo non ha dichiarato che cosa aspettarsi** | è un limite di **vista**: il database non può saperlo. ⚠️ Dal 2026-09-11 vale **solo** per i `COMMAND` senza contratto: chi dichiara `tolleranza_minuti` o `segno_di_vita = SESSIONE` non è più fuori portata (sezione sotto) |
| **`SU_RICHIESTA`** | il lavoro lo mette in coda una **persona** | non esiste nessuna cadenza da confrontare: è la **natura** del lavoro, e non cambierà |

Il primo è un confine che un giorno si potrebbe spostare; il secondo no.

⛔ **Dire «tutto bene» su un lavoro che non si vede sarebbe una bugia**, ed è il
modo più efficace di far smettere di guardare. La vista si ferma dove deve.

⚠️ **Il listener sempre acceso era fra i `FUORI_PORTATA` di proposito** (fino al
2026-09-11): scrive una sola corsa — quella di avvio — e presidiarne la vitalità
sull'ultima corsa direbbe «fermo» su un servizio sano acceso da tre settimane.
Ma **che sia un listener il database non lo sapeva**: nessuna colonna lo diceva.
*«Se servirà, è una colonna»* — è servita, ed è `segno_di_vita` (sezione sotto).

---

### ⭐ I `COMMAND` con un contratto non sono più fuori portata

Dal 2026-09-11 `dbops.processi` dichiara il **contratto di liveness** di un
`COMMAND` (decisione di Tid, brief *quattro processi senza presidio* §10.2):

| Colonna | Che cosa dice |
| --- | --- |
| `tolleranza_minuti` | *«se sto bene, lascio un segno almeno ogni N minuti»*. `NULL` = non si presidia da qui |
| `segno_di_vita` | **dove** il database cerca quel segno: `GIORNALE` (una corsa su `job_run_log`) o `SESSIONE` (una connessione viva in `pg_stat_activity` con `application_name = codice`) |

E il panorama, che prima diceva `FUORI_PORTATA` a tutti i `COMMAND`, ora **sa**:

| Contratto | Stati possibili |
| --- | --- |
| `GIORNALE` + tolleranza | `OK` (ultima corsa entro la tolleranza) · **`MUTO`** (più vecchia) · `MAI_PARTITO` (nessuna corsa) |
| `SESSIONE` | `OK` (una connessione col codice del processo è viva) · **`MUTO`** (non c'è) |
| nessuno | `FUORI_PORTATA`, come prima |

**`MUTO` è l'unico stato nuovo**: *«era vivo ed è taciuto»*. È la firma di un
timer morto, di un servizio caduto, di un digest che non gira più. `MAI_PARTITO`
su un `COMMAND` è il timer **dichiarato e mai installato** — il buco «fra
dichiarato e acceso non guarda nessuno» (presidi §11.5), visto dal database.

⭐ **Niente da fare su `da_guardare`**: non cambia forma, quindi `MUTO` e
`MAI_PARTITO` entrano da soli nel presidio, nel pannello e nel digest. E
[maintenance.vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare),
che nel proprio commento dichiarava *«non vede il job che non parte affatto: per
quello servirebbe che ogni processo dichiarasse ogni quanto deve girare»*, ha il
suo complemento.

⚠️ **Il segno di vita a `SESSIONE` è un fatto, non una dichiarazione**: se il
processo muore la sessione sparisce; se sta riconnettendo non c'è — ed è vero.
Nessun battito sul giornale, nessuna tabella nuova. Il backend si presenta con
`application_name = codice del processo` (una riga in `notify_listener`).

⛔ **E il verdetto poggia sull'*esistenza* della sessione, non su `backend_start`**
(rev `20260914-01`). `pg_stat_activity` mostra a **tutti** la riga di ogni
sessione (`pid`, `usename`, `application_name`), ma **maschera** le altre
colonne — `backend_start`, `state`, `query` — a chi non è lo stesso utente della
sessione né membro di `pg_read_all_stats`; e una vista non cambia l'utente che
`pg_stat_get_activity()` guarda. Fino al 14-09 il ramo leggeva `viva_dal IS NOT
NULL`: **OK** per `zeroerp_app` (la sessione del listener è sua) e **MUTO** per
chiunque altro — `titodb` compreso, cioè `fn_conta_presidio`, che conta per il
digest. Il primo digest della giornaliera ha contato 1 su un listener vivo da 31
ore, e il perimetro `LIBERO` del presidio ha protestato: *«il conteggio dice 1 ma
da qui la vista risponde vuota»*. Era la vista a dare due verdetti, e quello vero
era dell'app. ⇒ `ultimo_segno_di_vita` per `SESSIONE` è **informazione** («da
quando»), non verdetto: è `NULL` per chi non può leggerlo, e lo stato dice `OK`
lo stesso. Il caso «sessione di un altro utente» sta nel test 19 del pgTAP
(`dbops/test-vw-processi-programmazione.sql`), costruito con `dblink` dove il
DSN lo permette e **dichiarato** con `skip()` dove no.

⛔ **Il limite, dichiarato**: il catalogo non sa quali processi sono **accesi su
questo host** (`abilita` sta nel deploy). Oggi non morde — ogni sveglia accesa è
universale, e `run_fatturazione_batch` è spento per decisione di prodotto
(tolleranza `NULL`). Un processo acceso su un host e spento su un altro vorrà un
registro di silenziamento, non una colonna nel JSON.

Tre colonne in coda dal 2026-09-11: `tolleranza_minuti`, `segno_di_vita`,
`ultimo_segno_di_vita` (la corsa per `GIORNALE`, l'avvio della sessione per
`SESSIONE`).

---

### ⭐ La causa: non solo *che cosa* non va, ma *perché*

Dal 2026-10-09 la vista porta, accanto allo stato, la **causa** del guasto. Due
stati, da soli, non bastano a dire che cosa fare:

| Stato | Causa | Che cosa è successo | Chi interviene |
| --- | --- | --- | --- |
| `MUTO` | `TIMER_FERMO` | il timer del lavoro ha smesso di girare | chi gestisce il server |
| `MUTO` | `SERVIZIO_GIU` | un servizio sempre acceso è spento, o ha perso la connessione al database | chi gestisce il server |
| `MAI_PARTITO` | `TIMER_NON_INSTALLATO` | il timer è previsto ma non è mai stato installato | chi gestisce il server |
| `MAI_PARTITO` | `JOB_MAI_PARTITO` | il lavoro programmato nel database è acceso, non è mai partito e la sua corsa era dovuta da più di un'ora | chi gestisce il database |
| `IN_RITARDO` | `JOB_IN_RITARDO` | il lavoro ha già girato, ma la corsa dovuta è passata da più di un'ora: il programmatore si è fermato | chi gestisce il database |
| `NON_PROGRAMMATO` | `NON_PROGRAMMATO` | il catalogo non dice quale lavoro lo fa partire | lo sviluppo |
| `JOB_ASSENTE` | `JOB_ASSENTE` | il lavoro programmato nominato dal catalogo non esiste | chi gestisce il database |
| `JOB_SPENTO` | `JOB_SPENTO` | il lavoro programmato è stato spento | chi gestisce il database |
| `GIRA_E_NON_REGISTRA` | `GIRA_E_NON_REGISTRA` | è partito ma non ha lasciato traccia | lo sviluppo |

È la causa a scegliere il **testo** che il pannello e il digest mostrano a chi
deve agire ([`dbops.presidi_testi`](/dbzero/dbops/manual/presidi_testi)) e **a chi**
mandarlo ([`dbops.presidi_cause`](/dbzero/dbops/manual/presidi_cause): la colonna
«chi interviene» qui sopra è quel dato, non una frase): il 9
ottobre 2026 il testo unico diceva *«Esegui ora»* a un servizio sempre acceso,
che quel pulsante non ce l'ha.

⭐ Stato e causa escono **dallo stesso punto** della vista, in coppia: scriverli in
due punti separati vorrebbe dire due elenchi degli stessi casi, che prima o poi
smettono di coincidere.

---

### ⭐ `da_guardare`: il criterio del guasto sta in un posto solo

La vista porta una colonna che dice, per ogni riga, **se quello stato è un
guasto**. Non è una comodità: è la sede unica di quel criterio. Dal 2026-10-09
la regola è una sola: **è un guasto ciò che ha una causa**. I tre casi sani
(`OK`, fuori portata, su richiesta) non ne hanno; ogni guasto ce l'ha per
costruzione — quindi nel presidio non può comparire una riga senza il suo
rimedio.

⛔ La vista di presidio ([vw_processi_programmazione_da_guardare](/dbzero/dbops/manual/vw_processi_programmazione_da_guardare))
la **proietta** invece di ripetere un elenco di stati sani. Se lo ripetesse, il
vocabolario degli stati sarebbe scritto in **due** posti, e il giorno in cui ne
nasce uno nuovo qualcuno dovrebbe *ricordarsi* di andare a decidere da che parte
cade. ⚠️ Un allineamento affidato alla memoria è quello che manca per primo, e
mancherebbe senza dare nessun errore: cambierebbe soltanto ciò che il presidio
smette di mostrare.

⇒ Chi aggiunge uno stato passa di qui, e lì deve decidere. **Non c'è un
comportamento predefinito in cui cadere per distrazione.**

---

### ⚠️ Due cose da sapere leggendo la vista

* **Il legame col lavoro dello scheduler non è il nome.** Si legge da una
  colonna dichiarata (`dbops.processi.jobname_pgagent`), perché due lavori su
  quattordici si chiamano diversamente dal processo che registrano.
* **Il giornale si legge in due modi**, per processo *oppure* per nome del
  lavoro: le corse storiche non hanno il processo valorizzato, e senza il
  ripiego ogni lavoro sembrerebbe non aver mai girato prima di settembre 2026.

---

### ⛔ Le date del giornale sono **due**, e il confronto usa la seconda

Dal 2026-09-07 la vista porta due date di giornale, e la differenza fra loro non
è un dettaglio.

| | Che cosa dice |
| --- | --- |
| `giornale_ultima_corsa` | l'ultima corsa registrata sotto questo lavoro, **chiunque** l'abbia scritta |
| `giornale_ultima_corsa_pgagent` | l'ultima corsa che può valere come **risposta dello scheduler** |

La domanda del confronto è **«la sveglia dello scheduler ha lasciato
traccia?»**. Una corsa scritta da qualcun altro — un comando lanciato a mano, un
programma del backend che registra sotto lo stesso nome — non è una risposta a
quella domanda: parla di un altro fatto. ⛔ Ma prima **contava lo stesso**, e
spostando avanti la data spegneva l'allarme proprio sul lavoro che si stava
sorvegliando.

⚠️ **Non era un'ipotesi.** Il 2026-09-07 un lavoro di amministrazione risultava
«ultima corsa alle 11:11» per via di **sei righe lasciate da una prova**, mentre
lo scheduler l'aveva fatto partire alle 06:00. Su un lavoro *giornaliero* un
equivoco così rientra da solo il giorno dopo; su uno *settimanale* — cioè
esattamente sul lavoro che ha reso famoso questo difetto — copre l'intera
settimana.

⭐ **Le due date restano entrambe, e sono due apposta.** Quella piena serve ai
lavori che lo scheduler non sveglia affatto: per loro è l'unica informazione
utile della riga, e filtrarla la svuoterebbe. E quando le due **divergono**,
quella divergenza è essa stessa un'informazione: vuol dire che qualcuno ha
registrato sotto questo nome senza essere lo scheduler.

⚠️ **Il limite, detto qui e non scoperto dopo.** Chi ha scritto una corsa si
legge da una colonna il cui valore *predefinito* è «lo scheduler»: chi registra
senza dichiararsi finisce lì dentro. ⇒ Il confronto distingue il backend, che si
dichiara sempre, e **non** distingue lo scheduler da un lavoro lanciato a mano
dalla console del database. È meno di quanto sembri, ed è molto più di niente.

⚠️ E l'esito dell'ultima corsa (`ultimo_esito`) **non** è filtrato per chi l'ha
scritta: è contesto, non la prova del verdetto. Le corse andate male hanno un
presidio loro
([maintenance.vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare)).

### ⭐ Le corse saltate: la sveglia sì, l'esito no *(rev 2026-10-10)*

Una corsa **saltata** (`job_run_log.saltata`: il lock della corsia era occupato)
non ha fatto lavoro, ma prova che la sveglia è suonata. Le tre colonne del
giornale la trattano secondo la domanda che fanno:

| colonna | la corsa saltata | perché |
| --- | --- | --- |
| `ultimo_esito` | **esclusa** | l'esito è del lavoro, e una skip non ne ha: più recente di una corsa fallita, la nascondeva |
| `giornale_ultima_corsa` (→ `TIMER_FERMO`) | **contata** | il timer si è svegliato: escluderla darebbe `TIMER_FERMO` a un timer che gira |
| `giornale_ultima_corsa_pgagent` (→ `GIRA_E_NON_REGISTRA`) | **contata** | una skip è una registrazione: pgAgent è scattato e il giornale lo sa |

⚠️ Quindi una corsa **appesa** (processo vivo e bloccato, sveglie che saltano)
qui risulta `OK`: la sveglia funziona. Il lavoro fermo lo mostra
[maintenance.vw_job_run_da_guardare](/dbzero/maintenance/manual/vw_job_run_da_guardare)
(«presa e mai chiusa»). Uno stato `APPESO` in questa vista non c'è, per decisione
di Tid. Brief: `brief-db-corsa-saltata-non-e-una-corsa`.

---

### ⭐ È un panorama, non un presidio

Elenca **anche i sani**, ed è voluto: senza sapere quanti sono i sani, un guasto
sembra la norma. È la tabella che si apre per capire, non la lista delle cose da
fare — quella è la vista di presidio, e sta apposta da un'altra parte.

---

### Verifica

`db/pgtap/dbops/test-vw-processi-programmazione.sql` — i test del panorama.

Quelli che contano **costruiscono** il caso invece di cercarlo fra i dati di
oggi: si toglie il giornale a un lavoro e si pretende «è girato e non l'ha
detto»; gli si rimette una corsa dello scheduler e si pretende che torni sano;
gli si rimette una corsa di **qualcun altro** e si pretende che l'allarme
**resti acceso**.

⚠️ Il lavoro su cui si costruisce si sceglie sulla **struttura** — canale
dichiarato, sveglia accesa, almeno una partenza dello scheduler — e non sul
verdetto che la vista dà oggi. Sceglierlo sul verdetto era il difetto corretto
il 2026-09-07: bastava una rottura che eliminasse tutti i lavori sani perché il
file non trovasse nessun soggetto e **smettesse di verificare senza diventare
rosso**.

Gli ultimi due tengono legati due vocabolari che vivono in posti diversi: i
canali ammessi dal vincolo di tabella e i rami che la vista dichiara, e —
allo stesso modo — i modi in cui una corsa può essere stata registrata e quali
di essi valgono come risposta dello scheduler. Un valore nuovo senza verdetto fa
rosso il test, invece di produrre un falso allarme in produzione.

`db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` costruisce le otto
cause una per una (le tre che vivono nello scheduler del database solo dove
c'è) e pretende per ciascuna lo stato e la causa giusti; e pretende che **ogni**
causa che la vista può produrre abbia il suo testo. L'elenco delle cause si legge
dalla definizione della vista, non dalle righe di oggi: vale anche su un database
appena creato, dove nessun lavoro è guasto.

---

### ⭐ pgAgent: il segnale è la corsa dovuta (rev 2026-10-14)

Il presidio vuole dire *«il programmatore dei lavori del database non gira»*.
Fino al 2026-10-14 lo deduceva da *«il job non ha mai girato»*, e sbagliava due
volte:

* **falso allarme** su ogni job nuovo fino alla sua prima corsa: quel giorno
  `analyze_statistiche`, creato nel pomeriggio e programmato alle 02:30, era
  `MAI_PARTITO` con pgAgent vivo e gli altri quattordici job `OK`;
* **silenzio** sul demone fermo: un job che aveva già girato una volta restava
  `OK` per sempre.

Ora il segnale è **la corsa dovuta e non fatta**: la prossima esecuzione che
pgAgent dichiara (`prossima_corsa`, cioè `jobnextrun`) è passata da più di
un'ora, lo stesso margine di `GIRA_E_NON_REGISTRA`. Col demone fermo pgAgent non
aggiorna più quella data, che resta nel passato.

| Il job | La corsa dovuta | Stato |
| --- | --- | --- |
| non ha mai girato | passata da più di un'ora, o nessuna | `MAI_PARTITO` / `JOB_MAI_PARTITO` |
| non ha mai girato | ancora da venire | `IN_ATTESA`, senza causa |
| ha già girato | passata da più di un'ora | `IN_RITARDO` / `JOB_IN_RITARDO` |
| ha già girato | ancora da venire | `OK` |

⚠️ La regola resta nel `CASE` della vista, nella forma `ARRAY['stato', 'causa']`:
è da lì che `dbops/test-presidio-processi-testo-per-causa-v1` fa il censimento
delle cause. ChangeSet `20261014-54`; brief
`brief-db-statistiche-tabelle-job-notturno` §8.
