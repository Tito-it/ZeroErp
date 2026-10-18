# Brief DB — Il verde che non spegne la spia: «intermittente» e le corse che sono un verdetto completo

## ⏭️ Chi riparte — aggiornato al 2026-10-18

✅ **Chiuso il 2026-10-18** e archiviato in `work-done/`: nessuno riparte.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | ✅ direzione decisa (2026-10-18): proprietà del processo a catalogo; né finestra accorciata, né eccezione per nome | §4 | — |
| 2 | team DB | ✅ censimento fatto (2026-10-18), sul codice | §4.3 | — |
| 3 | Tid | ✅ **D4 = B** (2026-10-18): la colonna spegne solo il rosso già rientrato; la ricaduta resta | §4.4 | — |
| 4 | team DB | ✅ scritto e provato pre-apply (2026-10-18): colonna, CSV, vista, pgTAP, manual | §8 | — |
| 5 | Tid | ✅ apply su dbdev, pgTAP senza regressioni (2026-10-18); verificato dal team DB: lo smoke è uscito dalla vista, che è vuota | §6, §8.2 | — |
| 6 | Tid | ✅ tolte da dbdev le 7 righe di prova (2026-10-18) | §8.4 | — |
| 7 | BE | ✅ (2026-10-18) commenti in `smoke_notturno.py`: l'intestazione e il motivo di `CONSERVA_GIORNI` dicono la regola del verdetto completo | §7 | — |
| 8 | chi chiude | ✅ (2026-10-18) archiviazione in `work-done/`, riga di PROJECT_CONTEXT | — | — |

Decisioni aperte di Tid: nessuna. I file del §8.1 sono committati in `d984ff0cc` (2026-10-18).

---

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-18, su segnalazione di Tid. **A chi:** il
> team DB.
> **Origine:** il 2026-10-18 la spia del digest è accesa sullo smoke notturno, dopo tre giri verdi.
> **Filone:** `maintenance.vw_job_run_da_guardare`, vedi anche
> `brief-db-presidio-job-run-a-chi-tocca` (la causa delle righe) e `brief-db-corsa-saltata-non-e-una-corsa`.
> **Stato:** ✅ chiuso (2026-10-18): DB applicato e verde (§8), commenti BE del §7 fatti, archiviato.

## 1. Il caso

La vista accende una riga per tre motivi: l'ultima corsa è **fallita**, è **presa e mai chiusa**
(aperta da oltre un'ora), oppure è **intermittente** (l'ultima è verde o in corso, ma c'è almeno un
rosso negli ultimi sette giorni).

Il terzo motivo esiste per un guasto preciso: un lavoro che fallisce e passa, fallisce e passa, ha
sempre l'ultima corsa verde, e guardando solo quella nessuno lo direbbe malato
(`sync_auth_user_active`, 29 fallimenti in un giorno, il 2026-09-05). Per quel lavoro i sette giorni
sono giusti.

Lo smoke notturno è un'altra cosa. Ogni corsa **rifà da capo tutti gli smoke** e li confronta con la
baseline: un verde non dice «questa volta è andata bene», dice «oggi non ci sono regressioni». Il
verde di oggi **sostituisce** il rosso di ieri, non lo affianca. Eppure la vista lo tiene acceso per
sette giorni come un lavoro che va e viene.

## 2. Perché è un difetto del modello

Il motivo «intermittente» presuppone che ogni corsa veda **una parte** del lavoro (gli elementi di
quel giro, la coda di quel momento), così che un verde non cancelli quello che un rosso aveva lasciato
indietro. Per questi lavori è vero, e il rosso recente va tenuto in vista.

Per un lavoro la cui corsa è un **verdetto completo** sullo stato (ricontrolla tutto il suo perimetro,
ogni volta), il presupposto è falso: dopo un verde non resta niente di non verificato. Il rosso
precedente è storia, non un guasto aperto.

La vista oggi non può distinguere i due casi, perché il catalogo dei processi non lo dice. È la
stessa forma di `causa_fallimento` e di `tolleranza_minuti`: una proprietà della **natura del
processo** che la vista deve leggere e non indovinare.

Un rosso che non si nasconde, del resto, non ha bisogno della finestra: un verdetto completo che gira
una volta al giorno lascia il rosso come ultima corsa per un giorno intero, e il digest delle 7 lo
mostra. Uno smoke instabile si vede lo stesso: la spia si riaccende ogni mattina in cui torna rosso.

### Le due strade scartate

* **Accorciare i sette giorni.** È la finestra di tutti i lavori, e per quelli che falliscono e
  passano è quella giusta. Tagliarla perché oggi dà fastidio su un processo sarebbe la misura che
  disegna il progetto, e il difetto resterebbe: con tre giorni, la spia resterebbe accesa tre giorni
  dopo il verde.
* **Escludere lo smoke per nome nella vista.** Un'eccezione cablata, che il prossimo processo con la
  stessa natura dovrebbe ricopiare.

## 3. I fatti (2026-10-18, letti dal giornale; fatti datati, non motivo)

| Corsa (`job_run_log.id`) | Inizio (UTC) | Esito |
| --- | --- | --- |
| 198028, 198134, 198273 | 2026-10-13 14:00 / 15:00 / 16:00 | 🔴 `SMOKE_REGRESSIONI` (1 regressione) |
| 199365 | 2026-10-14 01:00 | 🔴 `SMOKE_REGRESSIONI` (1) |
| 202152 | 2026-10-15 01:00 | 🔴 `SMOKE_REGRESSIONI` (2) |
| 205055, 207887, 210468 | 2026-10-16 / 17 / 18 01:00 | 🟢 regressioni 0 |

La vista, il 2026-10-18 alle 08:07: `motivo` = «ultima corsa OK, ma ha fallito di recente:
intermittente», `falliti_ultimi_7_giorni` = 9, `ultimo_rosso_job_run_id` = 202152, `causa` =
`PROGRAMMA`. Con la regola di oggi esce dalla vista il 2026-10-22, dopo sette verdi di fila.

Nella definizione della vista la finestra compare due volte: nel filtro d'ingresso
(`p.started_at >= now() - '7 days'`) e nel conteggio `falliti_ultimi_7_giorni`
(`p.started_at >= g.started_at - '7 days'`).

## 4. La proposta

### 4.1 Catalogo

In `dbops.processi` una colonna booleana, `NOT NULL DEFAULT false`, che dichiara: **«ogni corsa di
questo processo è un verdetto completo: un verde chiude i rossi precedenti»**. Nome a scelta del team
DB (D1); per fissare le idee, `corsa_verdetto_completo`. Nel CSV `processi.csv`, `smoke_notturno` a
`true`, tutti gli altri a `false` salvo il censimento del §4.3.

### 4.2 Vista

Per un lavoro il cui processo ha la colonna a `true`:

* il motivo **intermittente** non scatta: la vista guarda solo l'ultima corsa;
* **fallita** e **presa e mai chiusa** restano come oggi;
* **la corsa in corso non è un verdetto** (D2): finché non chiude, conta l'ultima corsa **chiusa**.
  Se l'ultima chiusa è rossa, la riga resta «fallita» anche mentre il giro nuovo gira; se è verde,
  la vista resta vuota. Oggi un rosso seguito da una corsa in corso diventa «in corso adesso, ma ha
  fallito di recente: intermittente», che per un verdetto completo non è vero (il giro nuovo non ha
  ancora detto niente).

Per i lavori senza processo a catalogo, o con la colonna a `false`: niente cambia.

`falliti_ultimi_7_giorni` resta per tutti: è un dato utile anche su un verdetto completo (quanti
giorni rossi nell'ultima settimana), solo non accende più la riga.

### 4.3 Censimento

Il team DB passa i processi a catalogo e dice, per ciascuno, se la corsa ricontrolla tutto il suo
perimetro o ne lavora una parte. Ipotesi da verificare sul codice, non da prendere per buone:

| Processo | Ipotesi | Perché |
| --- | --- | --- |
| `smoke_notturno` | ✅ verdetto completo | rifà tutti gli smoke contro la baseline |
| digest dei presidi | da verificare | ogni corsa rilegge tutte le viste di presidio; ma un digest non inviato ieri non lo reinvia oggi |
| coda lavori, coda stampa | ❌ | un lavoro fallito resta fallito, la corsa dopo lavora altri lavori |
| fatturazione batch, invio mail | ❌ | gli elementi falliti di una corsa (D9) non sono ripresi dalla successiva |
| job pgAgent di manutenzione | da verificare uno per uno | |

Il criterio, da scrivere nel manuale della colonna: **dopo un verde, resta qualcosa che il rosso
aveva lasciato e il verde non ha ricontrollato?** Se sì, `false`.

#### 4.3.1 Esito del censimento (team DB, 2026-10-18, letto sul codice)

Il legame corsa → processo c'è per tutti i job a catalogo: `fn_run_and_log` scrive
`processo_codice` (dal parametro o, se manca, dal `jobname` uguale al codice), `fn_job_run_start` e
`fn_job_run_log_failure` lo ricevono dal chiamante. La vista raggruppa per `jobname`: un processo con
più corsie (`smoke_notturno:completo`, `digest_presidi:<cadenza>`) ha la colonna su tutte, e ogni
corsia dev'essere un verdetto completo **sul proprio perimetro**. Oggi lo è per entrambi.

| Processo (id) | Verdetto completo? | Perché, dal codice |
| --- | --- | --- |
| `smoke_notturno` (47) | ✅ | `smoke-baseline.sh` rifà tutto il giro normale contro la baseline; la corsia è una sola, `completo`. `c9` è fuori dal giro per scelta, non lasciato indietro |
| `digest_presidi` (26) | ✅ (D3 sciolta) | ogni corsa ricalcola tutte le viste della sua cadenza dal catalogo. Un digest non inviato ieri non si reinvia, ma le viste di presidio sono **stato**: quello che ieri era aperto ed è ancora aperto oggi c'è nel digest di oggi; quello che si è chiuso non è più un guasto. La consegna della mail è di `send_pending_emails`, non sua |
| `guardiano_digest` (44) | ✅ | ogni ora rilegge lo stato del digest dal panorama |
| `analyze_statistiche` (48) | ✅ | `ANALYZE` del database intero e autoverifica di tutte le tabelle |
| `sync_auth_user_expired_daily` (11) | ✅ | `fn_sync_auth_user_expired` riallinea **tutte** le credenziali alla data di oggi, nei due versi |
| `automations_*` (1–6, 42, 43) | ✅ | ogni giro converge tutto il registro; un guasto su un elemento solleva e annulla il giro intero (gestori `WHEN others` → `fn_log_and_raise_error`) |
| `automations_cleanup` (7) | ✅ | ogni giro ripassa tutte le tabelle. ⚠️ Il veto di una tabella si scrive nell'audit come `ERROR` e il giro resta verde, e la purga è a lotti: nessuno dei due è un residuo **di un rosso**, quindi non cambia la risposta |
| `apply_fk_index_policy` (8), `apply_storicizza_weekly` (9), `sync_storico_set_storicizza` (10) | ✅ | convergenza dell'intero registro a ogni giro; i guasti di riga sono isolati e non fanno rosso |
| `chiusura_scadenze_daily` (12) | ✅ | accoda per ogni azienda del roster, idempotente per (azienda, giorno); il lavoro vero e i suoi guasti stanno nella coda lavori e nel suo presidio (`vw_coda_lavori_da_guardare`). ⚠️ Da confermare scrivendo: che `fn_apply_chiusura_scadenze` chiuda tutto ciò che è scaduto fino a oggi, non solo ciò che scade oggi |
| `draina_coda_lavori` (25), `draina_coda_stampa` (21) | ❌ | la corsa dopo lavora altri elementi; un elemento fallito resta fallito |
| `send_pending_emails` (22) | ❌ | un `FAILED` senza tentativi residui non è ripreso |
| `run_fatturazione_batch` (20) | ❌ | gli elementi falliti di una corsa (D9) non sono ripresi |
| `listen_permessi` (46) | ❌ (non pertinente) | segno di vita `SESSIONE`, non giudicato dal giornale |
| `FATTURAZIONE_GIRO` (40), `FATTURAZIONE_NUMERA` (41), `avvio_manuale` (45) | ❌ (non pertinente) | canale `CODA`: sotto di loro non si scrive nessuna corsa |
| `sync_auth_user_active` (23), `listen_cambio_reparto` (24) | ❌ | ritirati |

Il risultato **non è** «solo lo smoke»: quasi tutti i job di manutenzione sono verdetti completi.
Ed è qui che il censimento ha trovato il problema del §4.4.

### 4.4 Il caso che ha fatto nascere i sette giorni era un verdetto completo (D4)

Il §1 giustifica la finestra con `sync_auth_user_active`, 29 fallimenti in un giorno, e il §2 la
attribuisce ai lavori che vedono **una parte**. Ma quel lavoro riallineava **tutti** gli utenti a ogni
corsa (`sync_auth_user_active.py`: «riallinea `auth_user.is_active` alle vesti utilizzabili oggi»): per
il criterio del §4.3 era un verdetto completo, e il suo erede (id 11) lo è.

Il motivo «intermittente» copre quindi **due** guasti, non uno:

1. **il residuo**: la corsa lavora una parte, il rosso ha lasciato qualcosa che il verde non ha
   ripreso. Riguarda solo i lavori a `false`;
2. **l'instabilità**: il lavoro cade, si rialza, ricade. Riguarda **anche** i verdetti completi. Si
   nasconde quando il lavoro gira più spesso di quanto lo si guardi: fra due digest, l'ultima corsa è
   verde e i rossi in mezzo non li vede nessuno. È esattamente quello che faceva `sync_auth_user_active`.

L'argomento del §2 («un rosso che non si nasconde non ha bisogno della finestra») regge solo se il
lavoro gira **non più spesso** del digest. Quella frequenza non è nel catalogo: sta in pgAgent e in
`deploy/sveglie.json`, e può cambiare senza che la vista lo sappia.

**D4 — che cosa spegne la colonna.**

* **A — tutto il motivo «intermittente»** (proposta del §4.2). Semplice; ma l'instabilità di un
  verdetto completo diventa cieca appena la sua sveglia è più fitta del digest, e la colonna andrebbe
  data solo a chi gira al più una volta al giorno — una regola che il catalogo non sa controllare.
* **B — solo il rosso già rientrato (proposta DB).** Per un verdetto completo un rosso che il verde
  ha chiuso **una volta** è storia; se nella finestra il lavoro è **ricaduto dopo essere tornato
  verde** (almeno due tratti rossi separati da un verde), è instabile e resta nella vista,
  intermittente, come oggi. Lo smoke del §3 ha un solo tratto rosso (13 → 15 ottobre): esce al primo
  verde. Uno smoke ballerino, o un `sync` che va e viene ogni dieci minuti, resta acceso. La regola
  non dipende dalla frequenza e non legge conteggi: guarda la forma della storia (un rientro contro
  una ricaduta).

Raccomandazione del team DB: **B**. Costa una CTE in più nella vista (i tratti rossi si contano col
cambio di `ok` fra corse consecutive non saltate, nella stessa finestra di sette giorni) e un caso in
più nel pgTAP; in cambio la colonna si può dare a tutti i ✅ del §4.3.1 senza condizioni.

## 5. Decisioni per Tid (se il team DB non le scioglie scrivendo)

* **D1 — nome e posto della colonna.** Proposta: `dbops.processi.corsa_verdetto_completo`, accanto a
  `tolleranza_minuti` e `causa_fallimento`. ✅ Sciolta (team DB, 2026-10-18): va bene così.
* **D2 — la corsa in corso su un verdetto completo** (§4.2, terzo punto). Proposta: non conta finché
  non chiude. ✅ Sciolta (team DB, 2026-10-18): sì, vale con A e con B.
* **D3 — il digest dei presidi**, se il censimento lo dà ambiguo (inviato o no è una parte, rilettura
  completa è un verdetto). ✅ Sciolta (team DB, 2026-10-18): verdetto completo (§4.3.1).
* **D4 — che cosa spegne la colonna** (§4.4): A o B. ✅ Decisa da Tid il 2026-10-18: **B**.

## 6. Collaudo

pgTAP nuovi in `test-vw-job-run-da-guardare` (o file gemello `-verdetto-completo-v1`), su un processo
di prova con la colonna a `true` e uno a `false`, stessa storia di corse:

1. rosso → verde: verdetto completo **fuori** dalla vista; l'altro **dentro**, intermittente;
2. rosso → in corso (meno di un'ora): verdetto completo **dentro**, motivo «fallita», sull'ultima
   chiusa (D2); l'altro come oggi;
3. verde → in corso: tutti e due fuori;
4. rosso → in corso da più di un'ora: tutti e due «presa e mai chiusa»;
5. verde → rosso: tutti e due «fallita»;
6. lavoro senza processo a catalogo: comportamento di oggi;
7. `falliti_ultimi_7_giorni` invariato su tutti i casi;
8. (solo con B) rosso → verde → rosso → verde: verdetto completo **dentro**, intermittente
   (ricaduto); l'altro **dentro**, intermittente.

Poi i pgTAP della causa (`test-vw-job-run-da-guardare-causa-v1`) e di `processi` senza regressioni.

Sul DB vero, dopo l'apply: lo smoke esce dalla vista se l'ultima corsa è verde.

## 7. Ricadute BE/FE

Nessuna attesa. Il backend non legge il testo del motivo né `falliti_ultimi_7_giorni` (verificato il
2026-10-18 nel codice di `backend/` e `frontend/src`); il digest legge le righe della vista. Se la
colonna entra nel drawer dei processi come dato informativo, è una richiesta a parte. Se il team DB
ne vede un'altra scrivendo, la scrive qui.

**Vista dal team DB (2026-10-18):** solo commenti, in `backend/apps/core/management/commands/smoke_notturno.py`.
L'intestazione dice che la vista mostra la corsa fallita «per 7 giorni»: dopo questo brief la mostra
finché resta l'ultima corsa (e, con B, finché il giro è ricaduto nella finestra). `CONSERVA_GIORNI = 7`
resta giusto, perché la finestra non cambia e una corsa può ancora restare in vista fino a sette giorni;
cambia solo la frase del commento che lo motiva. Da fare nel giro BE che segue, nessuna attesa.

## 8. Il giro DB (team DB, 2026-10-18)

### 8.1 File

| File | Che cosa |
| --- | --- |
| `00_schema/dbops/20261018-01-alter-processi-add-corsa-verdetto-completo` | `dbops.processi.corsa_verdetto_completo boolean NOT NULL DEFAULT false` (D1); default costante, un passo solo |
| `80_data/sql/dbops/processi.csv` + mirror `20260904-13` | colonna in coda: `true` per i 18 processi ✅ del §4.3.1, `false` per gli altri |
| `20_code/maintenance/20261018-02-update-vw-job-run-da-guardare-verdetto-completo` | la vista (B + D2): stesse colonne, `CREATE OR REPLACE` |
| `db/pgtap/maintenance/test-vw-job-run-da-guardare-verdetto-completo-v1.sql` | 17 test: la stessa storia di corse su un processo a `true` e uno a `false` (§6, più «due rossi di fila = un tratto» e «tratto fuori finestra») |
| `db/pgtap/maintenance/test-vw-job-run-da-guardare.sql` | adeguato: la fixture usava `apply_storicizza_weekly`, che ora è un verdetto completo, e il suo test 5 descriveva senza dirlo un verdetto parziale. Ora usa un processo di prova a `false` |
| manual `vw_job_run_da_guardare`, `processi` | la regola e il criterio del censimento |

La regola, nella vista:

* **`ultima`**: per un verdetto completo, la corsa in corso da meno di un'ora è esclusa (D2);
* **`tratti`** (CTE nuova): i tratti rossi di ogni job nei sette giorni, in una passata sola sul
  giornale. Un tratto comincia con un rosso la cui corsa precedente nella finestra non è rossa;
  contano le sole corse chiuse con un esito;
* **filtro**: verdetto parziale → un rosso in sette giorni, come prima; verdetto completo → almeno
  due tratti;
* **motivo**: per un verdetto completo «ultima corsa OK, ma e' ricaduto dopo essere tornato verde:
  instabile».

Il §6.6 (lavoro senza processo a catalogo) non è costruibile in un pgTAP:
`chk_job_run_log_processo_dichiarato` vieta una corsa nuova senza processo. La vista lo tratta come
`false` (`LEFT JOIN` + `COALESCE`), cioè come prima; è dichiarato nell'intestazione del test.

### 8.2 Prova pre-apply (dbdev, come owner, transazione annullata)

SQL estratto dai due YAML + upsert di **tutte** le righe del CSV (linee-guida-sql §11.2) + pgTAP:

| pgTAP | Esito |
| --- | --- |
| `test-vw-job-run-da-guardare-verdetto-completo-v1` | 17/17 |
| con la vista **vecchia** (solo la colonna) | rossi 4, 6, 11, 13, 14: il test distingue |
| `test-vw-job-run-da-guardare` (adeguato) | 6/6 |
| `test-vw-job-run-da-guardare-causa-v1` | 15/15 |
| `test-job-run-saltata-v1` | 11/11 |

Sul giornale vero di dbdev, il 2026-10-18 alle 10:50 (fatto datato): prima `smoke_notturno:completo`
«intermittente», dopo la vista è vuota.

Tempi (fatto datato, stesso giorno): senza JIT la vista nuova costa come la vecchia (~0,35 s contro
~0,37 s). Con la JIT accesa la nuova costa ~1,0-1,1 s contro ~0,55-0,7 s: è tutto tempo di
compilazione (il piano più caro fa partire più ottimizzazione, ~1,5 s di JIT), non lavoro. La JIT
pesa già sulla vista di oggi; non è un difetto di questo giro, ed è scritto qui perché non sembri una
regressione.

Cancelli statici verdi: letterali SQL, `runOnChange`, `preCondition` sul seed, DDL su trigger.

### 8.3 ⚠️ Il mirror è condiviso con un altro cantiere

Lo stesso giorno `brief-db-processi-accensione-per-ambiente` (R-BE-5) ha aggiunto
`accendibile_in_produzione` allo stesso CSV e allo stesso mirror (`20261018-10 … -14`). Il mirror ora
nomina **tutte e due** le colonne: i due cantieri si applicano nello **stesso** migrate, e nessuno dei due
si committa senza l'altro.

### 8.4 ⚠️ Righe di prova lasciate su dbdev

Durante la prova, una corsa diagnostica del pgTAP vecchio è partita **senza** `BEGIN` (un `echo
BEGIN; …` sulla riga di comando: il `;` lo chiude in bash), e la sua fixture è rimasta nel giornale:
7 righe, `maintenance.job_run_log.id` da 211454 a 211460, jobname `PGTAP-*`, processo
`apply_storicizza_weekly`. Nessun trigger sulla tabella, nient'altro toccato. Oggi la vista ne mostra
tre (`PGTAP-ROSSO`, `PGTAP-MAI-CHIUSA`, `PGTAP-INTERMITTENTE`) e il digest di domattina le
manderebbe. Si tolgono con:

```sql
DELETE FROM maintenance.job_run_log
 WHERE id BETWEEN 211454 AND 211460 AND jobname LIKE 'PGTAP-%';   -- 7 righe
```

Le prove del §8.2 le tolgono dentro la loro transazione, quindi non ne dipendono.
