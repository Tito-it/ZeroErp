## 📘 Documentazione Concettuale – Vista `dbops.vw_processi_programmazione`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il catalogo: canale, job dichiarato, contratto di liveness, accensione
> * [maintenance.job_run_log](/dbzero/maintenance/tabelle/job_run_log) — il giornale delle corse
> * [dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi) — il testo per chi agisce, scelto dalla causa
> * [dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause) — a chi tocca ogni causa
>
> Approfondimento viste:
>
> * [dbops.vw_processi_programmazione_da_guardare](/dbzero/dbops/views/vw_processi_programmazione_da_guardare) — il presidio: questo panorama proiettato sui guasti
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — l'altro presidio: le corse che falliscono
> * [dbops.vw_ambiente_non_dichiarato](/dbzero/dbops/views/vw_ambiente_non_dichiarato) — il presidio dell'ambiente, quando `acceso` è vuoto
>
> Approfondimento funzioni:
>
> * [dbops.fn_get_pgagent_job_stato](/dbzero/dbops/funzioni/fn_get_pgagent_job_stato) — lo stato del job letto da pgAgent
> * [dbops.fn_processo_acceso_dichiarato](/dbzero/dbops/funzioni/fn_processo_acceso_dichiarato) — la colonna `acceso`
> * [dbops.fn_conta_presidio](/dbzero/dbops/funzioni/fn_conta_presidio) — il conteggio del digest, che legge da un altro ruolo
>
> Guide:
>
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — chi suona la sveglia e come si vede se è andata bene

---

### 🎯 Scopo Principale

Il panorama dei processi automatici vivi: per ognuno, chi lo sveglia, quando girerà, quando ha
girato secondo lo scheduler e secondo il giornale, e uno `stato` che dice se i conti tornano.
Elenca anche i sani.

Vivo vuol dire ritiro non raggiunto (`script.fn_e_obsoleto`): un processo a ritiro programmato
compare fino al suo giorno, uno a ritiro raggiunto esce.

---

### ⭐ Il confronto fra due fonti

La risposta non viene da una fonte sola. Lo scheduler dice **quando** ha fatto partire un lavoro;
il giornale dice **che cosa** quel lavoro ha fatto. Finché le due si somigliano, va bene; quando si
smentiscono, è successo qualcosa che nessuno ha raccontato.

⭐ Lo stato che vale più di tutti è `GIRA_E_NON_REGISTRA`: lo scheduler dice che il job è girato, il
giornale non lo sa. È la firma di un lavoro che muore prima di riuscire a raccontarlo: un lavoro
settimanale è morto così per sei mesi, con l'ultimo verdetto agli atti a «fatto», e lo si è scoperto
per caso.

Due cose da sapere leggendo la vista:

* il legame col job non è il nome: si legge da `dbops.processi.jobname_pgagent`, perché un job può
  chiamarsi diversamente dal processo;
* il giornale si legge per codice del processo **oppure** per nome del job, perché le corse storiche
  non hanno il processo valorizzato.

---

### Gli stati, in ordine di decisione

L'ordine conta: il primo caso che vale decide lo stato.

| Caso | `stato` | `causa` |
| --- | --- | --- |
| canale `CODA` | `SU_RICHIESTA` | — |
| sveglia spenta su questa installazione | `SPENTO` | — |
| `COMMAND` a `SESSIONE`: c'è una connessione viva col codice del processo | `OK` | — |
| `COMMAND` a `SESSIONE`: non c'è | `MUTO` | `SERVIZIO_GIU` |
| `COMMAND` con tolleranza: nessuna corsa nel giornale | `MAI_PARTITO` | `TIMER_NON_INSTALLATO` |
| `COMMAND` con tolleranza: l'ultima corsa è più vecchia della tolleranza | `MUTO` | `TIMER_FERMO` |
| `COMMAND` con tolleranza: corsa entro la tolleranza | `OK` | — |
| `COMMAND` senza contratto | `FUORI_PORTATA` | — |
| nessun job dichiarato | `NON_PROGRAMMATO` | `NON_PROGRAMMATO` |
| il job dichiarato non esiste in pgAgent | `JOB_ASSENTE` | `JOB_ASSENTE` |
| il job è disabilitato dentro pgAgent | `JOB_SPENTO` | `JOB_SPENTO` |
| il job è girato, e il giornale non ha nessuna corsa dello scheduler più recente di un'ora prima dell'ultima esecuzione di pgAgent | `GIRA_E_NON_REGISTRA` | `GIRA_E_NON_REGISTRA` |
| il job non è mai girato e la corsa dovuta è passata da più di un'ora, o non ce n'è una | `MAI_PARTITO` | `JOB_MAI_PARTITO` |
| il job non è mai girato e la prima corsa è ancora da venire | `IN_ATTESA` | — |
| il job è girato e la corsa dovuta è passata da più di un'ora | `IN_RITARDO` | `JOB_IN_RITARDO` |
| altrimenti | `OK` | — |

I rami dopo `FUORI_PORTATA` valgono per `PGAGENT` e `CODA_AUTOMATICA`, che hanno un job pgAgent.

⭐ **`SPENTO` non è morto.** Una sveglia spenta per il default del suo ambiente o per una scelta a
mano non è un guasto, e viene prima di ogni verdetto di liveness. `JOB_SPENTO` è un'altra cosa: il
job disabilitato dentro pgAgent, fuori dal catalogo, e si guarda.

⭐ **pgAgent: il segnale è la corsa dovuta.** Col demone fermo pgAgent non aggiorna più la prossima
esecuzione, che resta nel passato: è il fatto che dice «il programmatore non gira». Un job nuovo
che aspetta la prima corsa non è un guasto (`IN_ATTESA`); un job che ha già girato e salta la corsa
dovuta lo è (`IN_RITARDO`).

---

### ⚠️ Due stati sani, per ragioni opposte

| Stato | Che cosa vuol dire | Perché non è un guasto |
| --- | --- | --- |
| `FUORI_PORTATA` | il lavoro lo sveglia l'host e il catalogo non dichiara che cosa aspettarsi | è un limite di **vista**: il database non può saperlo, e lo presidia il backend |
| `SU_RICHIESTA` | il lavoro lo accoda una **persona** | una cadenza da confrontare non esiste: è la **natura** del lavoro |

Il primo è un confine che si sposta dichiarando un contratto; il secondo no. ⛔ Dire «tutto bene»
su un lavoro che non si vede sarebbe una bugia, ed è il modo più rapido per far smettere di
guardare.

---

### ⭐ Il contratto dei `COMMAND`

Un `COMMAND` che dichiara un contratto di liveness in `dbops.processi` non è fuori portata:

* `GIORNALE` con tolleranza: il segno di vita è l'ultima corsa nel giornale, chiunque l'abbia
  scritta. `MAI_PARTITO` qui è il timer dichiarato e mai installato; `MUTO` è il timer fermo;
* `SESSIONE`: il segno di vita è una connessione viva sul database corrente col codice del processo
  come `application_name`. Se il servizio muore, o sta riconnettendo, la connessione non c'è, ed è
  vero.

⛔ **Il verdetto `SESSIONE` poggia sull'esistenza della connessione, non sulla sua ora di avvio.**
L'elenco delle sessioni mostra a tutti la riga di ogni sessione, ma ne maschera l'ora di avvio a chi
non è lo stesso utente e non legge le statistiche; e una vista non cambia l'utente con cui quell'elenco
si legge. Un verdetto sull'ora di avvio darebbe `OK` all'applicazione, padrona della sessione, e
`MUTO` a chiunque altro, compreso il conteggio del digest. ⇒ `ultimo_segno_di_vita` per `SESSIONE`
è informazione («da quando»), vuota per chi non può leggerla, non verdetto.

`tolleranza_minuti`, `segno_di_vita` e `ultimo_segno_di_vita` (l'ultima corsa per `GIORNALE`,
l'avvio della sessione per `SESSIONE`) stanno in coda alla riga.

---

### ⛔ Le date del giornale sono due, e il confronto usa la seconda

| Colonna | Che cosa dice |
| --- | --- |
| `giornale_ultima_corsa` | l'ultima corsa registrata sotto questo lavoro, **chiunque** l'abbia scritta |
| `giornale_ultima_corsa_pgagent` | l'ultima corsa registrata con origine pgAgent: la sola che vale come risposta dello scheduler |

La domanda di `GIRA_E_NON_REGISTRA` è «la sveglia dello scheduler ha lasciato traccia?». Una corsa
scritta da qualcun altro, un comando lanciato a mano o il backend sotto lo stesso nome, non risponde
a quella domanda: se contasse, sposterebbe avanti la data e spegnerebbe l'allarme proprio sul lavoro
sorvegliato, e su un lavoro settimanale lo coprirebbe per una settimana.

⭐ Le due date restano tutte e due: quella piena è l'unica informazione utile per i lavori che lo
scheduler non sveglia, e quando le due divergono qualcuno ha registrato sotto questo nome senza
essere lo scheduler.

⚠️ L'origine di una corsa ha come valore predefinito lo scheduler: chi registra senza dichiararsi
finisce lì. Il confronto distingue il backend, che si dichiara sempre, e **non** distingue lo
scheduler da un lavoro lanciato a mano dalla console del database.

---

### ⭐ Le corse saltate: la sveglia sì, l'esito no

Una corsa saltata (il lock della corsia era occupato) non ha fatto lavoro, ma prova che la sveglia è
suonata:

| Colonna | La corsa saltata | Perché |
| --- | --- | --- |
| `ultimo_esito` | esclusa | l'esito è del lavoro, e una saltata non ne ha: più recente di una corsa fallita, la nasconderebbe |
| `giornale_ultima_corsa` | contata | il timer si è svegliato: escluderla darebbe `TIMER_FERMO` a un timer che gira |
| `giornale_ultima_corsa_pgagent` | contata | pgAgent è scattato e il giornale lo sa |

⚠️ Una corsa **appesa** (processo vivo e bloccato, sveglie che saltano) qui risulta `OK`: la sveglia
funziona. Il lavoro fermo lo mostra [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare)
(«presa e mai chiusa»). Uno stato «appeso» in questa vista non c'è, per decisione.

`ultimo_esito` non è filtrato per chi ha scritto la corsa: è contesto, non la prova del verdetto.

---

### ⭐ La causa e `da_guardare`: il criterio del guasto sta in un posto solo

Ogni ramo della decisione consegna la coppia stato e causa insieme: un secondo elenco per le cause
farebbe due elenchi degli stessi casi, che prima o poi smettono di coincidere. La causa serve perché
lo stesso stato può avere rimedi diversi (un timer fermo non si ripara come un servizio caduto): sceglie
il testo che il pannello e il digest mostrano ([dbops.presidi_testi](/dbzero/dbops/tabelle/presidi_testi))
e a chi mandarlo ([dbops.presidi_cause](/dbzero/dbops/tabelle/presidi_cause)).

⇒ `da_guardare` è «la riga ha una causa»: i rami sani non ne hanno, i guasti ce l'hanno per
costruzione. Il presidio [vw_processi_programmazione_da_guardare](/dbzero/dbops/views/vw_processi_programmazione_da_guardare)
la **proietta** invece di ripetere un elenco di stati sani; chi aggiunge uno stato passa di qui e
deve decidere, senza un comportamento predefinito in cui cadere per distrazione.

⛔ **Stato e causa restano scritti nella definizione della vista**, come coppia letterale; uno
stato sano è la coppia con la causa vuota. Il pgTAP delle cause le censisce leggendo la
definizione: una regola spostata in una funzione uscirebbe dal censimento, e i test resterebbero
verdi per sottrazione.

---

### `acceso` e l'ambiente

`acceso` è lo stato della sveglia su questa installazione, da
[fn_processo_acceso_dichiarato](/dbzero/dbops/funzioni/fn_processo_acceso_dichiarato). È vuoto per
i `CODA` e quando l'ambiente non è dichiarato: in quel caso il panorama non solleva, dà il verdetto
di liveness come se la sveglia fosse accesa, e la causa la dice il presidio
[vw_ambiente_non_dichiarato](/dbzero/dbops/views/vw_ambiente_non_dichiarato).

---

### Chi la vede

Nel catalogo dei presidi è un inventario, che non si conta: elenca anche i sani, perché senza sapere
quanti sono i sani un guasto sembra la norma. La vista gira coi privilegi del proprietario.

---

### Test

* `db/pgtap/dbops/test-vw-processi-programmazione.sql` — il legame dichiarato col job; tolto il
  giornale `GIRA_E_NON_REGISTRA`, rimessa una corsa dello scheduler `OK`, rimessa una corsa di un
  altro attore l'allarme resta; ogni canale e ogni origine del giornale hanno un verdetto
  dichiarato; i `COMMAND` con e senza contratto; la sessione viva, assente e di un altro utente
  (questa costruita dove la connessione lo permette, dichiarata con `skip` dove no). Il lavoro su
  cui costruire si sceglie sulla struttura, non sul verdetto di oggi.
* `db/pgtap/dbops/test-presidio-processi-testo-per-causa-v1.sql` — l'elenco delle cause letto dalla
  definizione della vista; ogni causa costruita con lo stato giusto; i tre stati sani senza causa;
  `IN_RITARDO` e `IN_ATTESA` (dove pgAgent c'è); ogni causa ha il suo testo.
* `db/pgtap/maintenance/test-job-run-saltata-v1.sql` — l'esito è quello della corsa vera, e una
  saltata nella tolleranza tiene `OK`.
* `db/pgtap/dbops/test-processi-accensione-v1.sql`, `db/pgtap/dbops/test-processi-accensione-produzione-v1.sql`
  — un processo spento è `SPENTO`, non da guardare; `db/pgtap/dbops/test-installazione-ambiente-v1.sql`
  — senza ambiente il panorama non solleva.
* `db/pgtap/dbops/test-processo-vivo-v1.sql` — il panorama mostra il ritiro programmato e il
  processo vivo con `attivo` falso, non il ritiro raggiunto.

---

### Note di migrazione

* 2026-09-06 — nasce, col legame dichiarato fra processo e job (`brief-db-sveglia-dei-processi`).
* 2026-09-07 — `FUORI_PORTATA` e `SU_RICHIESTA` diventano due stati, e nasce `giornale_ultima_corsa_pgagent`:
  quel giorno un lavoro di amministrazione risultava girato alle 11:11 per sei righe lasciate da una
  prova, mentre lo scheduler l'aveva fatto partire alle 06:00.
* 2026-09-11 — i `COMMAND` con un contratto escono da `FUORI_PORTATA`: nascono `MUTO` e le tre colonne
  del contratto (`brief-db-quattro-processi-senza-presidio`).
* 2026-09-14 — il verdetto `SESSIONE` poggia sull'esistenza della sessione: il primo digest della
  giornata aveva contato `MUTO` un listener vivo da trentuno ore, perché contava da un altro ruolo.
* 2026-10-09 — nasce `causa`, e `da_guardare` diventa «la riga ha una causa» (`brief-db-presidio-processi-testo-per-causa`):
  il testo unico diceva «Esegui ora» a un servizio sempre acceso.
* 2026-10-10 — le corse saltate escono da `ultimo_esito` (`brief-db-corsa-saltata-non-e-una-corsa`).
* 2026-10-14 — per pgAgent il segnale diventa la corsa dovuta: nascono `IN_ATTESA` e `IN_RITARDO`
  (`brief-db-statistiche-tabelle-job-notturno`). Prima un job nuovo era `MAI_PARTITO` fino alla prima
  corsa, e un demone fermo lasciava `OK` ogni job che aveva già girato.
* 2026-10-16 — nascono `SPENTO` e `acceso` (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}
