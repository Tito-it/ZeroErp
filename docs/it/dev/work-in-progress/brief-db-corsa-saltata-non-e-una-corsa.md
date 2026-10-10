# Brief DB — Una corsa saltata non è una corsa riuscita

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09, durante la revisione di L4 di
> [brief-be-db-fe-un-solo-fuso-aziendale](brief-be-db-fe-un-solo-fuso-aziendale.md) (T-9).
> **A chi:** team DB (`dev/db-tid`); ricadute BE in §6.
> **Decisione di Tid (2026-10-09):** aprire il brief.
> **Stato:** 🔵 da fare. **Rivisto** dalla sessione DB (`dev/db-tid`) il 2026-10-09: decisioni
> di Tid e lavoro DB nel §8, che prevale sui §3–§5 dove dissente.

## 1. Il fatto

`script.fn_job_run_start`, quando il lock della corsia è occupato, scrive su
`maintenance.job_run_log` una riga **già chiusa** con `ok = TRUE` e
`message = 'skip: another run in progress'` (corpo nella doc auto-generata,
`script/funzioni/fn_job_run_start.md`).

Quella riga non ha fatto il lavoro, ma per il modello è indistinguibile da una corsa riuscita:
l'unica differenza è il **testo** di `message`. Nessuna colonna, nessun CHECK, nessun valore di
`ok` la separa.

## 2. Perché è un difetto del modello (non dei dati)

Ogni lettore che chiede «il lavoro è stato fatto?» o «qual è l'ultima corsa?» conta la skip
come una corsa riuscita. Il caso nasce dalla struttura (lock occupato = riga `ok = TRUE`), non
da una popolazione.

### 2.1 Le sveglie calendariali saltano un periodo intero, senza errore (BE, T-9)

`e_dovuto` (l'`ExecCondition=` dei timer) chiede a `MaintenanceRepository.corsa_riuscita_dal`
se la corsia ha una corsa `ok` dall'inizio del periodo aziendale. Scenario:

1. alle 07:00 scatta il digest giornaliero mentre una corsa avviata da «Esegui ora» tiene il
   lock → riga skip, `ok = TRUE`;
2. la corsa a mano fallisce (`ok = FALSE`);
3. alle 08:00, 09:00, … `e_dovuto` trova la skip delle 07:00 e risponde «già fatto».

Il digest del giorno non parte più. Sulla fatturazione differita il periodo è il **mese**.

### 2.2 Una corsa appesa sparisce dal presidio

Una corsa col processo vivo ma bloccato tiene il lock di sessione. Ogni sveglia successiva
scrive una skip `ok = TRUE`, più recente della corsa appesa:

* `maintenance.vw_job_run_da_guardare` prende **l'ultima** riga per `jobname`
  (`DISTINCT ON … ORDER BY started_at DESC`): l'ultima è la skip, e il ramo «presa e mai
  chiusa: il job è morto senza dire niente» non scatta più;
* `dbops.vw_processi_programmazione` conta la skip come `ultima_corsa` e come `ultimo_esito`:
  il processo risulta **OK** entro la tolleranza, mentre il lavoro è fermo.

Cioè il caso che quei presidi esistono per vedere viene coperto proprio dalla sveglia che lo
dovrebbe far emergere.

## 3. Che cosa si chiede

Un **marcatore strutturale** della corsa saltata, scritto da `fn_job_run_start` sul ramo
del lock occupato, e i lettori del DB che lo rispettano.

**Proposta (A), raccomandata:** colonna `saltata boolean NOT NULL DEFAULT false` su
`maintenance.job_run_log`, `TRUE` sulla sola riga di skip. CHECK di coerenza: una riga
saltata è chiusa (`NOT saltata OR ended_at IS NOT NULL`).

Che cosa resta di `ok` sulla riga saltata va deciso insieme (§5): la proposta è lasciarlo
`TRUE`, perché un salto per sovrapposizione **non è un guasto** e non deve accendere
`vw_job_run_da_guardare` come un fallimento. La distinzione la porta `saltata`, non `ok`.

**Alternativa (B):** `ok = NULL` sulla riga di skip, senza colonna nuova. Scartata nella
proposta: `ok IS NULL` oggi significa «corsa senza esito» (aperta, o chiusa senza esito:
`_helpers.corsa_conclusa` lo dichiara ammesso). Caricarlo di un secondo significato fa
indovinare a ogni lettore quale dei due vale.

⛔ Non basta filtrare `message <> 'skip: …'` nei lettori: è un testo libero, e un filtro sul
testo è la seconda sede della stessa regola.

## 4. I lettori da allineare (lato DB)

Dalla doc auto-generata, 2026-10-09 (`job_run_log` nelle viste e nelle funzioni):

| Oggetto | Che cosa deve escludere `saltata` |
| --- | --- |
| `maintenance.vw_job_run_da_guardare` | la CTE `ultima`: l'ultima corsa **vera** per `jobname` |
| `dbops.vw_processi_programmazione` | `ultima_corsa`, `ultima_corsa_pgagent`, `ultimo_esito` |
| `dbops.vw_run_senza_attore` | da valutare: la skip porta l'attore (rev 2026-09-04), quindi oggi non è un rilievo; verificare che `ultimo_ok` non la scelga |
| `maintenance.fn_run_and_log`, `maintenance.fn_job_run_log_failure` | da verificare: scrivono, non leggono l'ultima corsa |

⚠️ Il censimento dei lettori è del team DB, sul corpo vero: la tabella sopra è un punto di
partenza, non l'elenco chiuso.

## 5. Decisioni da prendere (team DB, poi Tid)

1. (A) o (B) di §3.
2. Con (A): `ok` sulla riga saltata resta `TRUE`?
3. La skip conta come **segno di vita** per la liveness (`vw_processi_programmazione` con
   `segno_di_vita = GIORNALE`)? Proposta: **no**. Il timer che si sveglia è vivo, ma il lavoro
   no, e il segno di vita è un contratto del processo, non della sveglia.

## 6. Ricadute BE (dopo l'applicazione)

* `MaintenanceRepository.corsa_riuscita_dal`: `AND NOT saltata`, con un test sul DB vero che
  **costruisce** la riga di skip (lock preso da una seconda connessione) e prova che il periodo
  resta dovuto (`tests/db/test_corsa_riuscita_dal_db`).
* `MaintenanceRepository.job_liveness` / `list_job_summary` e
  `ProcessiRepository`: da verificare con la stessa domanda, «l'ultima corsa vera».
* `JobRunHandle.acquired` resta com'è: è il BE a sapere di aver saltato, ma la riga la scrive
  il DB.

## 7. pgTAP

* lock occupato → riga con `saltata = TRUE`, chiusa;
* corsa normale → `saltata = FALSE`;
* `vw_job_run_da_guardare`: una corsa aperta da più di un'ora **seguita da** una skip resta
  «presa e mai chiusa»;
* `vw_processi_programmazione`: una sola skip nella finestra di tolleranza non rende OK un
  processo senza corse vere.

## 8. Revisione DB e decisioni (2026-10-09)

Analisi della sessione DB sul corpo vero (doc auto-generata, 2026-10-09), decisioni di Tid lo
stesso giorno. Dove dissente dai §3–§5, vale questo paragrafo.

### 8.1 Che cosa la revisione ha trovato

* **Gli scrittori della skip sono due, non uno.** Anche `maintenance.fn_run_and_log` ha un ramo
  sul lock occupato, e scrive una riga con `ok = TRUE` e **`ended_at` NULL**: «riuscita e mai
  chiusa». Il §4 la dava come «scrive, non legge».
* **`script.fn_job_run_end` chiude qualunque riga** e ne riscrive `ok`: chiamata su una riga
  saltata, la trasformerebbe in una corsa vera e cancellerebbe il marcatore.
* **`vw_processi_programmazione`: le tre colonne fanno tre domande diverse.**
  `ultima_corsa_pgagent` alimenta `GIRA_E_NON_REGISTRA` («pgAgent scatta e il giornale lo
  registra?»): la skip **è** una registrazione. `ultima_corsa` alimenta `TIMER_FERMO`: la skip
  prova che il timer va. Solo `ultimo_esito` parla del lavoro.
* **`vw_run_senza_attore`** non ha una colonna `ultimo_ok`: chiede solo se l'ultima corsa ha un
  attore, e la skip ce l'ha. Non si tocca.

### 8.2 Decisioni (Tid, 2026-10-09)

| # | Decisione |
| --- | --- |
| D1 | Proposta (A): colonna `saltata boolean NOT NULL DEFAULT false` su `maintenance.job_run_log`. |
| D2 | Sulla riga saltata **`ok` è NULL**, non `TRUE` (rettifica del §5.2). Il motivo sul modello: una skip non ha un esito del lavoro, e con `NULL` la domanda «è riuscita?» (`ok IS TRUE`) la scarta da sola, senza un `AND NOT saltata` da ricordare in ogni lettore presente e futuro. `saltata` toglie al `NULL` il doppio significato che il §3 temeva. CHECK di riga: `NOT saltata OR (ended_at IS NOT NULL AND ok IS NULL)`. |
| D3 | La skip **conta** come segno di vita della sveglia (rettifica del §5.3): la corsa appesa la mostra `vw_job_run_da_guardare`, non un `TIMER_FERMO` falso. Nessuno stato `APPESO` nuovo, per ora. |
| D4 | **Nessuna bonifica** delle skip già scritte: restano `saltata = false` col loro testo. Siamo in sviluppo. |

### 8.3 Lavoro DB

1. `maintenance.job_run_log`: colonna `saltata` (D1), CHECK del D2, COMMENT.
2. `script.fn_job_run_start`, ramo lock occupato: `saltata = TRUE`, `ok` NULL, `ended_at`
   valorizzato. Il `message` resta come testo per chi legge, non è più il marcatore.
3. `maintenance.fn_run_and_log`, ramo lock occupato: idem, con `ended_at` (oggi manca).
4. `script.fn_job_run_end`: rifiuta una riga saltata (codice nuovo di classe `TECNICO`: chiudere
   una corsa mai presa è un chiamante rotto; nome da registrare nei due registri, ok Tid).
5. `maintenance.vw_job_run_da_guardare`: la CTE `ultima` esclude `saltata`.
6. `dbops.vw_processi_programmazione`: solo `ultimo_esito` esclude `saltata`; `ultima_corsa` e
   `ultima_corsa_pgagent` restano su tutte le righe (D3).
7. Manual di `job_run_log`, delle due viste e delle tre funzioni.

### 8.4 pgTAP (al posto del §7)

* lock occupato da una seconda sessione (dblink) → riga `saltata`, chiusa, `ok` NULL; idem per
  `fn_run_and_log`;
* corsa normale → `saltata = false`;
* il CHECK rifiuta una riga saltata con `ok` valorizzato o aperta;
* `fn_job_run_end` su una riga saltata → rifiuto;
* `vw_job_run_da_guardare`: corsa aperta da più di un'ora **seguita da** una skip → resta
  «presa e mai chiusa»;
* `vw_processi_programmazione`: una skip nella tolleranza tiene `OK` il timer (niente
  `TIMER_FERMO`), e `ultimo_esito` è quello della corsa vera.
