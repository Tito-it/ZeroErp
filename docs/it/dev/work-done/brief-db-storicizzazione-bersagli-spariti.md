# Brief DB — un job morto da sei mesi, e il registro che dice «done»

> **Destinatario:** team DB (`dev/db-tid`).
>
> **Origine.** Trovato dal team DB stesso guardando `dbops.vw_run_senza_attore`
> durante il cantiere dei processi automatici, e registrato come **R-12** nel
> vostro registro dei residui
> ([brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md)
> §1-quinquies). Qui c'è la **misura del backend**, che aggiunge tre fatti che
> cambiano la forma del problema.
>
> **Stato:** 🟢 **CHIUSO — §2.1, §2.2 e §2.3 fatte e applicate** il 2026-09-05
> (changeSet `-28`, `-29`, `-35`, `-36`, `-38`, `-39`), test verdi. Resta
> scoperto un solo caso, dichiarato nel §5: **il job che non parte affatto**. ⚠️ **Non blocca il backend**, e non è di questo cantiere:
> lo scriviamo perché è la **sola cosa** che tiene `dbops.vw_run_senza_attore`
> lontana dallo zero, cioè dal criterio con cui voi stessi chiudete **DB-5**.
>
> ⛔ **Questo brief dice che cosa serve e perché, non come farlo.** Forma, DDL e
> changeSet sono decisioni vostre.

---

## 0. In due parole

`apply_storicizza_weekly` gira ogni settimana e muore ogni settimana da **sei
mesi**. Nessuno se n'è accorto, e non per distrazione: muore **prima di
scrivere**, quindi l'ultima cosa che il giornale dice di lui è che è andato
**bene**.

La causa immediata sono tre righe di configurazione che puntano a tabelle che non
esistono più. La causa vera è che quelle righe le mette un'automazione e **non le
toglie nessuno**.

---

## 1. I fatti, misurati il 2026-09-05

### 🔴 Il giornale non tace: dice il falso

```
jobname                 | started_at | ok | message
apply_storicizza_weekly | 2026-02-21 | t  | done
apply_storicizza_weekly | 2026-02-14 | t  | done
apply_storicizza_weekly | 2026-02-07 | t  | done
```

⛔ **Ogni corsa registrata è `ok = true`.** Non c'è una sola riga di errore in
tutta la storia di questo job: muore prima che `fn_run_and_log` scriva, quindi
l'ultimo verdetto agli atti resta *«done»*.

⚠️ **È peggio di un buco.** Un giornale che non dice niente si nota; un giornale
che dice «done» di un job morto **risponde alla domanda sbagliata con sicurezza**.
Chi guardasse quella riga concluderebbe «vecchio ma sano», che è esattamente il
contrario.

⭐ **E non riguarda solo questo job**: qualunque processo che muoia prima della
propria registrazione lascia lo stesso verde. È una proprietà del meccanismo, non
di questa configurazione.

### Le tre righe

`config.storico_set_storicizza` ha **104** righe; **3** puntano a niente:

| `table_name` | esiste? | `insert_manuale` | inserita il | da |
| --- | --- | --- | --- | --- |
| `vendite.attivita_fatturabili_lotti` | ⛔ no | `false` | 2026-01-31 | `postgres` |
| `config.profili_reparto_aree` | ⛔ no | `false` | 2026-03-07 | `postgres` |
| `config.profili_reparto_azioni` | ⛔ no | `false` | 2026-03-07 | `postgres` |

⭐ **Le date raccontano la sequenza**: l'ultima corsa buona è del **2026-02-21**,
e due delle tre righe sono nate il **2026-03-07**. Il primo giro dopo quella data
è quello in cui il job ha smesso di arrivare in fondo.

🔵 **E c'è una quarta riga da guardare, ma non so se sia un problema**:
`anagrafiche.risorse_umane_auth_user` esiste come **vista**, non come tabella. Se
la storicizzazione si aspetta una tabella, è un caso diverso dagli altri tre e
non lo classifico io.

---

## 2. Che cosa serve

### 2.1 Che il job torni a girare

Le tre righe non hanno più un bersaglio. ⚠️ **Toglierle è però il tampone**: se il
problema fosse solo quello, tornerebbe alla prossima tabella ritirata.

### 2.2 ⭐ Che una riga sparisca quando sparisce la sua tabella

`insert_manuale = false` e `user_insert = postgres` dicono che quelle righe le ha
messe un'**automazione** — non una persona. ⇒ Il set si popola da solo e **non si
pota da solo**: sono due metà di uno stesso meccanismo, e ne esiste una.

⛔ **È qui il difetto di modello**, e per questo lo segnaliamo invece di
proporvi una `DELETE` di tre righe: finché la potatura non esiste, la prossima
tabella ritirata rifà lo stesso guasto, e lo rifà **in silenzio per sei mesi**.

**Come si vede che è chiuso.** Si ritira una tabella che era nel set, e il giro
notturno successivo **passa** — o si ferma dicendo perché.

### 2.3 Che un job che muore prima di registrarsi si veda

⚠️ Questa è la più larga delle tre, e forse non è di questo brief. La segnaliamo
perché il cantiere appena chiuso ha comprato **visibilità** — l'attore sui run, i
presidi, la coda che dice chi ha fallito — e questo job è il caso che quella
visibilità **non copre**: non ha fallito nel giornale, ha smesso di comparirci.

🔵 Non proponiamo la forma. Diciamo la domanda: *un job che non arriva a
`fn_run_and_log` come si distingue da un job che non è mai partito?*

---

## 3. Perché al backend interessa

Solo per una ragione, e indiretta: `dbops.vw_run_senza_attore` non può arrivare a
zero finché questo job non gira, perché la sua riga si toglie **alla prossima
corsa** — e la prossima corsa non arriva mai.

⇒ È l'ultimo ostacolo al criterio con cui **DB-5** si dichiara chiusa. Le altre
tre righe della vista hanno ormai `processo_registrato = true` e si tolgono da
sole.

⛔ **Il backend non tocca niente qui**: `config.storico_set_storicizza` e i job
pgAgent sono vostri, e nessuna riga di Python li nomina.

---

## 4. ✅ Risposta del team DB (2026-09-05) — e una diagnosi che corregge il §1

> ⭐ Grazie: la misura è giusta, e la forma del problema è quella che dite. Una
> cosa però va corretta, perché cambia il rimedio.

### ⛔ Il giornale non «non fa in tempo a scrivere»: scrive, e poi butta via

`maintenance.fn_run_and_log` **cattura** l'eccezione, **scrive** la riga
`ok = false` con `error_code` e `error_detail`… e poi fa `RAISE` — con il
commento `-- lascio propagare`.

⇒ Il `RAISE` fa **rollback della transazione**, quindi **anche di quella riga**.

> ⚠️ Il fallimento viene verbalizzato e il verbale viene distrutto nello stesso
> istante. Non è una svista di scrittura: è che *«far propagare l'errore»* e
> *«lasciarne traccia»* sono, dentro una transazione unica, **due desideri
> incompatibili**.

⭐ E questo spiega il dettaglio che vi era sembrato strano — *«ogni corsa
registrata è `ok = true`»*. Non è che le corse fallite manchino: è che **non
possono esistere**. Nessun job che usa `fn_run_and_log` può lasciare una riga
rossa, mai. Il presidio `vw_run_senza_attore` e il giornale sono stati costruiti
sopra un meccanismo che, per come è fatto, **non sa registrare un fallimento**.

⇒ Avete ragione a dire che è una proprietà del meccanismo. È anche **più grave**
di come l'avevate scritta: non riguarda «i job che muoiono prima di
registrarsi», riguarda **tutti e dodici**.

🔵 **Non lo correggiamo in questo giro**, e diciamo perché: le strade sono tre —
non rilanciare (e allora pgAgent vede verde), spezzare in `start` + `COMMIT` +
lavoro (e allora una corsa interrotta resta «iniziata e mai finita», che è la
forma già usata per la coda), oppure scrivere il verbale fuori transazione. La
prima cambia il comportamento di dodici job, la seconda cambia dodici wrapper.
⇒ È una decisione, non un'implementazione, e va presa guardando i dodici insieme.

---

### ✅ §2.2 — la potatura, che è il difetto di modello

`maintenance.proc_sync_storico_set_storicizza` diventa una sincronizzazione
vera: aggiunge **e** pota (`20260905-28`).

⛔ **Si pota una cosa sola**, perché «la derivazione non produce più questa riga»
ha tre cause e solo una giustifica la cancellazione:

| Caso | | Perché |
| --- | --- | --- |
| il nome non risolve a niente, riga **derivata** | ✅ si pota | non può essere vera in nessun senso |
| il nome non risolve, riga **manuale** | ⛔ non si tocca | è una **decisione**: se perde il bersaglio va **detto a qualcuno**, non cancellato di nascosto |
| la tabella c'è ma ha perso il `DEFAULT` | ⛔ non si pota | è il caso **transitorio** che `apply_storicizza_weekly` ripara: potarlo spegnerebbe la storicizzazione di una tabella **viva** |

⚠️ Verificato prima di scrivere: le tre righe morte sono **tutte** derivate, e
l'unica riga manuale del set (`config.user_emittente_attivo`) esiste. Il criterio
non tocca nient'altro.

⭐ **E la prima potatura la fa il changeSet chiamando la procedura**, non una
`DELETE` scritta a mano: la riparazione è lo stesso gesto della correzione. Le
tre righe se ne vanno **come conseguenza**.

---

### ✅ §2.1 — il job torna a girare, e non solo perché il set è pulito

`maintenance.proc_apply_storicizza_defaults` salta ciò che non ha referente e
isola il fallimento di una riga dalle altre (`20260905-29`).

⛔ **Non è ridondante dopo la potatura.** Produttore e consumatore sono **due job
pgAgent su schedulazioni diverse**: se l'apply gira prima del sync — ed è
l'ordine di due sveglie indipendenti — la riga stantia c'è. È una possibilità
**strutturale**, non l'incidente di oggi.

⭐ Misurato: dopo la potatura l'apply completa **101 applicate, 0 saltate, 0
fallite**. Con una riga stantia forzata: **101, 1 saltata, 0 fallite** — e la
salta dicendo quale.

⚠️ Ne approfittiamo per togliere `split_part(nome, '.', 1|2)`: su un nome con più
di un punto o su un identificatore quotato produce due pezzi sbagliati e un
`ALTER TABLE` che colpisce altro. Ora il nome si risolve una volta con
`to_regclass` e **non si smonta mai**.

---

### 🔵 La vostra quarta riga: `anagrafiche.risorse_umane_auth_user`

Avete fatto bene a non classificarla. La risposta misurata:

* è una **vista**, non una tabella ordinaria;
* ⭐ **l'apply non ci si rompe**: PostgreSQL accetta `ALTER TABLE <vista> ALTER
  COLUMN … SET DEFAULT`, e il giro completa;
* ⛔ ma la **derivazione non l'avrebbe mai prodotta** (`relkind = 'r'`), quindi
  quella riga è arrivata da un'altra strada — e la potatura non la toglie,
  perché il nome risolve.

⇒ Non è un guasto e non blocca niente. È una riga il cui `DEFAULT` conta solo se
qualcuno inserisce **attraverso** quella vista. Resta da guardare, con calma,
insieme a chi ha messo la riga.

---

### Il presidio, e una cosa che abbiamo trovato guardandolo

⭐ **Non abbiamo scritto una vista nuova**, ed è deliberato: un presidio per
questa classe di difetto **esiste già** —
`db/pgtap/dbops/test-riferimenti-morti-v1.sql` test 5, *«nessun riferimento
morto nei DATI di configurazione»*.

⛔ **Ed è nato il 2026-08-04 dalla stessa identica tabella morta**,
`vendite.attivita_fatturabili_lotti`, trovata in `config.sistema_codici`. La
stessa tabella era **anche** in `config.storico_set_storicizza`, e lì non ha
guardato nessuno.

> ⚠️ Il presidio ha la forma giusta e il **perimetro sbagliato**: interroga *una*
> tabella di configurazione scritta a mano, invece di chiedere la domanda in
> generale. È lo stesso difetto che questo brief racconta — un elenco che
> qualcuno deve ricordarsi di aggiornare.

🔵 **La forma giusta** sarebbe un registro delle «colonne di configurazione che
contengono un nome di tabella» e un controllo unico che le percorre tutte. È
lavoro suo, tocca un presidio con un brief proprio, e non lo facciamo di
straforo. ⇒ **Nel frattempo** il test di questo cantiere fissa l'invariante su
`config.storico_set_storicizza`, e lo dichiara come perimetro parziale invece di
far finta che sia generale.

**Verifica:** `db/pgtap/maintenance/test-storicizza-set-potatura.sql` — 7 test,
fra cui i tre casi della potatura costruiti uno per uno.

---

## 5. ✅ §2.3 chiusa — e la diagnosi era più grave della domanda (2026-09-05, notte)

### Che cosa è stato fatto

| changeSet | |
| --- | --- |
| `20260905-35` | `maintenance.fn_job_run_log_failure` — scrive il verbale del run fallito su una **connessione separata** (dblink), dove il rollback non arriva |
| `20260905-36` | `fn_run_and_log` la chiama **prima del `RAISE`**. Il `RAISE` resta: il lavoro si annulla, il verbale no |
| `20260905-38` | i due `GRANT` a `zeroerp_log` — `USAGE` su `maintenance`, `INSERT` sul giornale. **Niente `SELECT`** |
| `20260905-39` | `maintenance.vw_job_run_da_guardare` — **il posto dove guardare** |

⭐ **Il canale non è stato inventato: c'era già.** `script.fn_log_error_only`
scrive in `dbops.error_log` fuori transazione dal 2026-02, e le sue 143.000
righe — fra cui 262 di un guard che esiste **solo** per sollevare eccezioni — sono
la prova che sopravvive al `RAISE`.

### 🔴 Due guasti che nessun test avrebbe preso dal lato del chiamante

La funzione è fatta per **non sollevare**: se non riesce a scrivere emette un
`WARNING` e tira dritto, perché non si fa fallire due volte un lavoro già
fallito. ⇒ Un test che guardasse «la chiamata non esplode» sarebbe stato verde
mentre non scriveva niente. **Ed è successo due volte:**

1. la funzione era di `titodb`, non superuser → `dblink` rifiutava la
   connessione (*«password or GSSAPI delegated credentials required»*);
2. `zeroerp_log` non aveva `USAGE` su `maintenance` → *«permesso negato»*.

⇒ Trovati **solo** andando a guardare dove la riga sarebbe dovuta arrivare.
⭐ È la regola che resta: **un canale che tace quando non funziona non si
collauda guardando chi lo chiama, si collauda guardando dove dovrebbe arrivare.**

### ⭐ La misura che dimostra il difetto

| origine | run rossi nel giornale, prima |
| --- | --- |
| **PGAGENT** | **0** |
| CRON | 31 |

Zero contro trentuno: il difetto era **solo** sul percorso pgAgent — i command
Django passano da `fn_job_run_start`/`fn_job_run_end`, dove è Python a governare
la transazione e può committare il fallimento.

### La vista, e la scelta che la tiene leggibile

Si guarda **l'ultima corsa di ogni job**, non tutti i rossi: così un job che
torna a funzionare **esce da solo**, senza colonne «visto» né finestre
arbitrarie.

⛔ Ma la sola «ultima corsa» apriva un buco, e l'ha detto il dato:
`sync_auth_user_active` aveva **29 fallimenti in un giorno e l'ultima corsa
verde** — sarebbe stato invisibile. ⇒ Un terzo motivo prende l'**intermittenza**
(ultima OK, almeno un rosso negli ultimi sette giorni), che si auto-pulisce
anch'esso.

⚠️ Ne segue che il rientro **non è immediato**: ci vogliono sette giorni
tranquilli. Ed è giusto — un job che ha fallito cinque minuti fa ha appena
fallito.

**Test:** `test-vw-job-run-da-guardare.sql` (6) e
`test-job-run-log-failure-out-of-tx.sql` (6), verdi. Il secondo dichiara ciò che
**non** prova: che la riga venga scritta davvero — una scrittura fuori
transazione sopravvive al `ROLLBACK` del test, e quel file sporcherebbe il
giornale a ogni giro.

### ⛔ Che cosa resta scoperto, e non va dimenticato

**Il job che non parte affatto.** Se nessuno lo sveglia non c'è nessuna corsa da
guardare. Servirebbe che ogni processo dichiarasse **ogni quanto** deve girare, e
`dbops.processi` non ce l'ha. ⚠️ È R-12 vista dall'altro lato: la forma di
guasto che questo brief racconta non è chiusa del tutto.

### E la vista non è nata vuota

Alla prima apertura nominava già `sync_auth_user_active` — **29 fallimenti,
l'ultimo alle 22:51 di oggi**, in mezzo a 86 corse riuscite. Nessuno se n'era
accorto, perché non c'era dove accorgersene.
⚠️ È `origine = CRON`, quindi un command del backend: da segnalare a loro, non
nostro da riparare.

---

## 5. Riferimenti

* [brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md)
  — §1-quinquies, dove R-12 è nato
* [piano-be-fe-processi-automatici-identita-e-perimetro.md](piano-be-fe-processi-automatici-identita-e-perimetro.md)
  — §8, il quadro dei presidi in cui questa riga resta accesa
