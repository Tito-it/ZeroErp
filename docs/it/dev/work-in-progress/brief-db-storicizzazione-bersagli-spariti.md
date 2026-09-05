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
> **Stato:** 🟢 **§2.1 e §2.2 fatte** (changeSet `20260905-28` / `-29`, da
> applicare). 🔵 **§2.3 misurata e diagnosticata** — la causa è più precisa di
> quella scritta qui, e sta nel §4. ⚠️ **Non blocca il backend**, e non è di questo cantiere:
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

## 5. Riferimenti

* [brief-db-processi-automatici-residui-be.md](brief-db-processi-automatici-residui-be.md)
  — §1-quinquies, dove R-12 è nato
* [piano-be-fe-processi-automatici-identita-e-perimetro.md](piano-be-fe-processi-automatici-identita-e-perimetro.md)
  — §8, il quadro dei presidi in cui questa riga resta accesa
