## 📘 Documentazione Concettuale – Tabella `maintenance.job_run_log`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.processi](/dbzero/dbops/tabelle/processi) — il registro dei processi a cui ogni corsa nuova appartiene
> * [dbops.coda_lavori](/dbzero/dbops/tabelle/coda_lavori) — dove sta l'operatore del singolo lavoro, che qui non c'è
>
> Approfondimento viste:
>
> * [maintenance.vw_job_run_da_guardare](/dbzero/maintenance/views/vw_job_run_da_guardare) — i lavori la cui ultima corsa vera chiede un occhio
> * [maintenance.vw_job_run_da_superuser](/dbzero/maintenance/views/vw_job_run_da_superuser) — i processi la cui ultima corsa l'ha fatta un superuser
> * [dbops.vw_processi_programmazione](/dbzero/dbops/views/vw_processi_programmazione) — il panorama: ultimo esito e sveglia viva
>
> Approfondimento funzioni:
>
> * [maintenance.fn_run_and_log](/dbzero/maintenance/funzioni/fn_run_and_log) — la porta dei job del database
> * [script.fn_job_run_start](/dbzero/script/funzioni/fn_job_run_start) — apre la corsa di un lavoro del backend
> * [script.fn_job_run_end](/dbzero/script/funzioni/fn_job_run_end) — la chiude
> * [maintenance.fn_job_run_log_failure](/dbzero/maintenance/funzioni/fn_job_run_log_failure) — il verbale di un fallimento, fuori transazione
>
> Guide:
>
> * [Tracciamento processi e job](/guide/analisi-tracciamento-processi-e-job) — il quadro del tracciamento
> * [I lavori automatici: che natura hanno e per conto di chi girano](/guide/processi-automatici-classe-e-identita) — il processo come attore

---

### 🎯 Scopo Principale

Il giornale delle corse dei lavori automatici: una riga per corsa (o per passo) di qualunque
lavoro schedulato o lanciato a mano, job del database o comando del backend. Dice di quale
processo è, quando è partita e finita, con che esito, con che ruolo si è collegata e, se è
fallita, perché.

È un giornale **generico**. Il dettaglio di dominio di una corsa non vive qui: lo tengono i
domini (la fatturazione nelle sue tabelle), agganciato con `run_uuid`. Il `meta` porta solo un
riepilogo generico, come i conteggi per esito.

---

### L'esito del lavoro sta in `meta.esito`

Per i job del database, quando il lavoro è una `SELECT` sola, `maintenance.fn_run_and_log` ne
legge il risultato e lo scrive in `meta`, sotto la chiave `esito`: il riepilogo, il testo o il
conteggio che la funzione del lavoro restituisce. `rows_affected` resta il numero di righe del
risultato. Una corsa che esegue una `CALL` o più istruzioni non ha esito.

⭐ **Una corsa può essere rossa senza essere fallita.** Se l'esito dichiara degli elementi falliti
(la chiave `_falliti` maggiore di zero), la riga si chiude con `ok` falso ed `error_code` =
`E_JOB_ESITO_CON_SCARTI`, ma il lavoro degli elementi riusciti resta: è la riuscita con scarti.
Quale elemento è fallito, e perché, lo dice il riepilogo in `meta.esito`. La riga è una sola: la
transazione non si annulla, e il verbale fuori transazione non serve.

---

### Da dove arriva una corsa: `origine`

`origine` dice come è stato lanciato il lavoro, ed è vincolata da `chk_job_run_log_origine`:

| Valore | Chi la scrive |
| --- | --- |
| `PGAGENT` | il default: ogni corsa registrata da `maintenance.fn_run_and_log` |
| `CRON` | un comando del backend lanciato da una sveglia di sistema |
| `COMMAND` | un comando del backend lanciato a mano |

⚠️ `PGAGENT` è il default, non una prova: lo prende **ogni** corsa che passa da
`fn_run_and_log`, anche quando a chiamare il wrapper è la convergenza del rilascio in CI o una
persona. Il giornale non distingue pgAgent dagli altri chiamanti di un job del database; chi si
è collegato lo dice `ruolo_sessione`.

---

### ⛔ Ogni corsa nuova dice di quale processo è

`processo_codice` è l'**attore** della corsa: il codice del processo in `dbops.processi`, per
tutti i lavori, anche quelli di manutenzione. La FK `fk_job_run_log_processi` respinge un
codice che il registro non conosce, e il CHECK `chk_job_run_log_processo_dichiarato` respinge
una riga nuova **senza** codice: un processo che non sa dire chi è non gira, e fallire
rumorosamente è meglio che lasciare una riga muta.

Il CHECK è `NOT VALID` di proposito, e non si convalida: le corse scritte prima che la colonna
esistesse non hanno attore e non lo avranno mai. Riempirle per far passare un vincolo vorrebbe
dire inventare un attore per corse che non l'avevano. Un `NOT NULL` non si può mettere per la
stessa ragione.

⇒ La regola è il CHECK, e non ha bisogno di un presidio che la misuri: una corsa senza attore non
può più nascere, e quelle di prima restano senza attore per sempre.

`auth_user_id` è l'**utente tecnico** con cui gira il processo, quando ne ha uno. ⚠️ Non è
l'operatore che ha chiesto un singolo lavoro di una coda: quello sta nello scope del lavoro in
`dbops.coda_lavori`, perché un worker registra una corsa ed esegue molti lavori, ognuno col suo
operatore. Non ha FK, di proposito: una riga di giornale non deve poter fallire perché
un'anagrafica è cambiata.

---

### Chi si è collegato: `ruolo_sessione`

`ruolo_sessione` è il ruolo che si è **collegato** per la corsa: pgAgent (`zeroerp_job`), il
migratore nella convergenza del rilascio, una persona. Non è il ruolo con cui il lavoro gira:
le procedure dei job sono `SECURITY DEFINER` del proprietario, e dentro di loro l'utente
corrente sarebbe sempre lui.

⚠️ La colonna **non ha default**, di proposito: la riga di una corsa fallita la scrive
`fn_job_run_log_failure` in un'altra sessione, dove un default direbbe il ruolo del canale di
log. La valorizzano le funzioni che scrivono. È vuota sulle corse registrate prima che
esistesse: «non registrato», non un guasto. La legge `maintenance.vw_job_run_da_superuser`.

---

### ⭐ Una corsa saltata non è una corsa riuscita

Quando il lock della corsia è occupato il lavoro non parte, ma il giornale ne tiene traccia:
la sveglia c'è stata. Quella riga è **saltata**:

| Colonna | Sulla riga saltata |
| --- | --- |
| `saltata` | vera |
| `ok` | vuoto: non ha fatto lavoro, quindi non ha esito |
| `ended_at` | valorizzato: nasce già chiusa |

Il CHECK `chk_job_run_log_saltata` tiene insieme le tre cose. La scrivono solo i rami del
lock occupato di `script.fn_job_run_start` e di `maintenance.fn_run_and_log`, e
`script.fn_job_run_end` rifiuta di chiuderla (`E_JOB_RUN_SALTATA_NON_CHIUDIBILE`): chiuderla le
scriverebbe un esito.

Che cosa ne fa chi legge dipende dalla domanda:

| Domanda | La riga saltata | Dove |
| --- | --- | --- |
| «il lavoro è riuscito?» | si scarta da sola (`ok` vero) | ogni lettore |
| «qual è l'ultima corsa **vera**?» | esclusa | `vw_job_run_da_guardare`, l'ultimo esito di `vw_processi_programmazione` |
| «la sveglia è viva?» | **contata**: prova che il timer si è svegliato | l'ultima corsa del giornale in `vw_processi_programmazione` |

⛔ Il testo `skip: another run in progress` resta nel `message` per chi legge il giornale, ma
non è il marcatore: un filtro sul testo sarebbe una seconda sede della stessa regola.

⚠️ Le corse saltate scritte prima che la colonna esistesse hanno `saltata` falsa e `ok` vero:
il giornale storico non è stato bonificato.

---

### Il codice dell'errore e lo SQLSTATE stanno separati

* **`error_code`** è «il codice più preciso che chi scrive ha»: il codice di dominio (`E_…`) o
  quello del backend, e in mancanza lo SQLSTATE o il nome dell'eccezione. Per una riuscita con
  scarti è `E_JOB_ESITO_CON_SCARTI`, con `sqlstate` vuoto: nessun errore è passato dal database.
* **`sqlstate`** è il codice del database per l'errore che ha fermato la corsa, quando l'errore
  è passato dal database. Il CHECK `chk_job_run_log_sqlstate_forma` pretende la forma di uno
  SQLSTATE: cinque caratteri fra cifre e lettere maiuscole. È vuoto per una corsa riuscita e per
  un errore che il database non ha visto, come un'eccezione Python di un comando.

La classe dello SQLSTATE dice a `vw_job_run_da_guardare` se il guasto è dell'ambiente; il codice
dice se l'errore ha un destinatario suo. Per questo servono tutti e due. `message` resta il
testo per chi legge, `error_detail` il dettaglio tecnico.

⚠️ Per le corse di prima la colonna è stata ricavata dalla forma di `error_code`; il codice di
dominio delle vecchie righe `P0001` non si recupera.

---

### Chi scrive: tre porte, nessuna scrittura diretta

* **I job del database** → `maintenance.fn_run_and_log`, che avvolge l'istruzione del lavoro.
* **I lavori del backend** → `script.fn_job_run_start` e `script.fn_job_run_end`, che aprono e
  chiudono la corsa attorno a un corpo Python. Sono `SECURITY DEFINER`: i ruoli dei comandi non
  hanno scrittura diretta sulla tabella, solo l'esecuzione delle due funzioni. Il lock della
  corsia è facoltativo.
* **Il verbale di un fallimento** → `maintenance.fn_job_run_log_failure`, su una connessione
  separata, come `zeroerp_log`, che sulla tabella ha il solo `INSERT`.

---

### Chi legge: l'applicazione legge e non scrive

| Privilegio | `zeroerp_app` | Perché |
| --- | --- | --- |
| accesso allo schema | sì | risolvere i nomi |
| `SELECT` sulla tabella e sulle viste di presidio | sì | la lista dei processi automatici e delle corse, il riepilogo dei giri e la liveness, gli esiti delle corsie di fatturazione, il digest |
| `INSERT`, `UPDATE`, `DELETE` | **no** | la porta di scrittura sono le funzioni qui sopra; un giornale non si cancella |

La sede è il provisioning (`scripts/sql/provision_zeroerp.sql`, fase `post`, blocco
`maintenance`), con un changeSet gemello per i database già provisionati. ⛔ `maintenance` non
entra nella whitelist del provisioning, che darebbe lettura e scrittura piene su tutto lo
schema per concedere una lettura.

---

### Test

* `db/pgtap/maintenance/test-job-run-registrazione.sql` — `origine` e `meta`, l'apertura e la
  chiusura di una corsa del backend, la postura `SECURITY DEFINER` delle due funzioni.
* `db/pgtap/maintenance/test-job-run-attore.sql` — le colonne dell'attore, la FK che respinge
  un processo non registrato, la derivazione del processo dal `jobname`, il rifiuto di una
  corsa senza processo.
* `db/pgtap/maintenance/test-job-run-saltata-v1.sql` — la colonna `saltata` e il suo CHECK,
  `fn_job_run_end` che rifiuta una saltata, i lettori che la scartano o la contano.
* `db/pgtap/maintenance/test-job-run-ruolo-sessione-v1.sql` — `ruolo_sessione` senza default, e
  scritto da `fn_run_and_log` e da `fn_job_run_start`, anche sulle righe saltate.
* `db/pgtap/maintenance/test-job-run-sqlstate-e-codice-v1.sql` — il CHECK sulla forma dello
  SQLSTATE, e le porte che lo scrivono separato dal codice.
* `db/pgtap/maintenance/test-app-postura-job-run-log-v1.sql` — l'applicazione legge il giornale
  e una sua scrittura diretta è respinta.
* `db/pgtap/maintenance/test-fn-run-and-log-lock-ed-esito-v1.sql` — l'esito in `meta.esito`, la
  riuscita con scarti scritta con `ok` falso ed `E_JOB_ESITO_CON_SCARTI`, `rows_affected` di una
  `SELECT`.

---

### Note di migrazione

* 2026-06-18 — la tabella, nata per i soli job pgAgent, diventa il giornale di ogni lavoro
  schedulato: nascono `origine` (le righe di allora diventano `PGAGENT`) e `meta`.
* 2026-09-04 — nascono `processo_codice`, con la FK verso `dbops.processi`, e `auth_user_id`.
* 2026-09-05 — `chk_job_run_log_processo_dichiarato`: da qui in avanti una corsa senza processo
  non si scrive.
* 2026-09-19 — il `SELECT` dell'applicazione entra nel provisioning. Fino ad allora esisteva solo
  sul database di sviluppo, dato a mano, ed è emerso quando i test Django in CI sono passati a
  collegarsi come `zeroerp_app`.
* 2026-10-10 — nasce `saltata` (`brief-db-corsa-saltata-non-e-una-corsa`). Prima una corsa
  saltata nasceva `ok = true`, e la distingueva da una corsa vera solo il testo del messaggio.
* 2026-10-15 — nasce `ruolo_sessione` (`brief-db-ruoli-di-sistema`).
* 2026-10-16 — nasce `sqlstate`, con la conversione sul posto delle righe di prima
  (`brief-db-presidio-job-run-a-chi-tocca`).
* 2026-11-03 — `meta.esito` e la riuscita con scarti (`E_JOB_ESITO_CON_SCARTI`). Prima
  `fn_run_and_log` scartava il risultato del lavoro, e una corsa con elementi falliti risultava
  verde (`brief-db-revisione-maintenance` D5).
* 2026-11-04 — ritirato il presidio `dbops.vw_run_senza_attore`, che mostrava i lavori la cui
  ultima corsa non aveva processo. Dopo il CHECK del 2026-09-05 il debito che misurava non poteva
  più nascere, e in vista restavano solo lavori con l'ultima corsa anteriore al vincolo: non
  poteva né accendersi né svuotarsi (`brief-db-revisione-dbops`).

---

{% include-markdown "signature-core.md" %}
