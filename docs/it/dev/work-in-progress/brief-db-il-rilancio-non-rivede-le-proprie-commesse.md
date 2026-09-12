# Brief DB — il rilancio dello step non rivede le proprie commesse

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-12.
>
> **In una riga:** al **rilancio** di un pull fallito, la discovery
> `vendite.fn_list_commesse_emittibili` scarta le commesse le cui righe sono
> `TRATTENUTA` — anche quando a trattenerle è **il lotto stesso che sta
> riprovando**. Il pull visita zero commesse, chiude `COMPLETATO`, ritira le
> proprie segnalazioni e il lotto esce pulito **senza aver emesso niente**.
> L'auto-esclusione del proprio lotto esiste, ma solo nell'emit (`-62`), un
> cancello più a valle che non viene mai raggiunto.
>
> **Origine.** Collaudo in-app, prova 5 (tutto-rosso) di
> [collaudo-in-app-esito-parziale-pull-commessa.md](collaudo-in-app-esito-parziale-pull-commessa.md),
> eseguita da Tid il 2026-09-12: ripristinate le ROOT, «Riprova step» porta il
> lotto a `COMPLETATO` e non genera nessun documento.
>
> **Correlati:** [brief-db-il-trattenuto-passa-lo-stesso](../work-done/brief-db-il-trattenuto-passa-lo-stesso.md)
> (§5.3, §5.4, L3, P-5) · changeSet `20260909-61` e `20260909-62` ·
> `db/pgtap/vendite/test-pull-non-prende-trattenuti-v1.sql`

---

## 1. Che cosa è successo (fatti datati, 2026-09-12)

**LTF-0010972 (13337)** — emissione mirata su due gruppi, commesse 34137 e
36984 guastate (ROOT tolta):

| Quando | Cosa | Traccia |
| --- | --- | --- |
| 11:15:14 | giro: `pull_attivita_da_commessa` tentativo 1 → **`ERRORE`**, `totale 2 · ok 0 · falliti 2`; gli altri tre task dello step DRAFT girano a vuoto; lotto `ERRORE` | task_run 4032; log critici 10069/10070; esiti 1921/1922 `ERRORE` |
| (fra i due) | ROOT ripristinate per `id` (17005, 18375) | `commesse_sorgenti` |
| 11:19:31 | **«Riprova step»**: tentativo 2 del pull → `COMPLETATO` con **`totale 0 · ok 0 · falliti 0`**; log critici **ritirati** (`disabilitato = true`); lotto **`COMPLETATO`**; esiti **ancora `ERRORE`**; zero fatture | task_run 4036 |
| 11:21:40 | annullo del lotto | — |

**LTF-0010973 (13338)** — stessa materia ricostruita e lasciata ferma per la
diagnosi: lotto `ERRORE`, esiti `ERRORE`, ROOT già ripristinate. È il caso su
cui sono state fatte le prove del §2.

## 2. Dov'è il difetto — sul modello, non sul dato

Il pull ha **due cancelli** in serie, e il brief del trattenuto li nomina
entrambi (§5.3: *«`p_gruppi` è applicato in due punti — quali commesse
visitare e quali righe emettere»*):

```text
fn_list_commesse_emittibili           → quali COMMESSE visitare      ⛔ esclude TRATTENUTA, non sa chi chiede
        ↓ per ogni commessa
fn_emit_attivita_fatturabili_da_commessa → quali RIGHE emettere     ✅ eccezione del proprio lotto (v_lotto_corrente)
```

Il §5.4 dello stesso brief decide: *«il filtro esclude sempre il lotto corrente.
Il pull riceve già l'identità del giro (`p_emit_batch_id`)»*. La decisione è
stata scritta nel **secondo** cancello (`-62`) e non nel **primo** (`-61`), che
non riceve nessuna identità: la firma è rimasta invariata («⛔ FIRMA E USCITA
INVARIATE») e il predicato è `classe_emittibilita IN ('PRONTA','RIFIUTATA','NON_APPROVATA')`
secco.

⭐ **E la prova che «funziona» è stata letta dal caso sbagliato.** L3 registra
come *«effetto atteso e verificato»* che *«dalla discovery sparisce 34137, che
ha una sola riga, trattenuta»* — misurato quando la tratteneva **un altro**
lotto (LTF-0010331). La stessa identica sparizione, al rerun, è il difetto.

⚠️ **Il presidio P-5 non poteva vederlo.** Il test 3 di
`test-pull-non-prende-trattenuti-v1.sql` («RERUN: la riga trattenuta dal
PROPRIO lotto viene ripresa») chiama **direttamente l'emit**: la discovery non
è nel percorso. È la forma già pagata altrove — *la whitelist si verifica dal
percorso che la attraversa, non dal nome*.

### La prova a cerchio, sul lotto 13338 (contesto operatore attivo)

| Domanda | Risposta |
| --- | --- |
| classe delle righe di 34137 e 36984 | `TRATTENUTA`, `trattenuta_da_lotti = {13338}` — il lotto stesso |
| `fn_list_commesse_emittibili(competenza 2026-09, emittente 72, p_gruppi = i due gruppi)` — la chiamata esatta del pull | **zero righe** |
| `fn_emit_attivita_fatturabili_da_commessa(34137, …, p_emit_batch_id = lock_batch_id di 13338)` in dry-run, dentro `BEGIN … ROLLBACK` | `total_candidate = 1` — l'emit **la riprenderebbe** |
| stesso emit con `p_emit_batch_id = NULL` | `0` — la risposta prudente, come da contratto |

⇒ L'eccezione del proprio lotto è **corretta e irraggiungibile**: chi la
chiamerebbe non arriva mai a farlo.

## 3. Perché non è un caso di collaudo

Non serve una commessa a riga singola. Dopo un pull fallito su una commessa:

1. il savepoint del fan-out riporta le righe a `NON_EMESSA` — corretto;
2. l'esito `ERRORE` viene scritto **fuori** dal savepoint su **tutti** i
   documenti di quella commessa nel lotto (`_marca_esito_gruppi`) — corretto,
   è la traccia che P-5 del 2026-09-07 esiste per tenere;
3. al rerun, quei documenti risultano `TRATTENUTA` dal proprio lotto, e la
   commessa **non ha più nessuna riga** nella whitelist della discovery.

⇒ **Ogni commessa fallita sparisce dal rerun, per costruzione.** La via
d'uscita D-Q p.1 — *«correggo la commessa → rieseguo lo step → il task ritira le
sue segnalazioni»* — oggi ritira le segnalazioni **senza rieseguire niente**.
È l'esatto contrario di ciò che il cantiere del fan-out esisteva per garantire
(«il rilancio RITENTA, non salta»), ed è silenzioso: nessun errore, un lotto
`COMPLETATO`, e due esiti che dicono `ERRORE` su un documento che il verdetto
non guarda più.

⚠️ La prova 3 del collaudo («il rilancio RITENTA») era passata il 2026-09-09
alle **01:44** su LTF-0010330 — pull tentativo 2 su 34137: `totale 1 ·
falliti 1`, cioè la commessa **rivisitata**. L3 è stato applicato lo stesso
giorno alle **17:12** (`DATABASECHANGELOG`). Da quel momento l'unico rilancio
di un pull fallito è quello di oggi, ed è il primo a rispondere `totale 0`:
la prova non era falsa quando è stata spuntata, lo è diventata sedici ore dopo.

## 4. Che cosa serve — lato DB

### D1 · La discovery riceve l'identità del giro e applica la stessa eccezione

`vendite.fn_list_commesse_emittibili` guadagna **`p_emit_batch_id uuid DEFAULT NULL`**
— stesso nome e stessa semantica del parametro dell'emit, così il backend
consegna **un** dato a **due** funzioni — e il predicato diventa:

```sql
AND (
      e.classe_emittibilita IN ('PRONTA', 'RIFIUTATA', 'NON_APPROVATA')
      -- ⭐ L'AUTO-ESCLUSIONE, la stessa del changeSet -62: al rerun i PROPRI
      --   documenti sono marcati in fatturazione_lotti_esiti, e la commessa
      --   deve essere visitata perche' l'emit possa riprenderli.
      -- ⚠️ `<@` e non `= ANY`: libera solo se TUTTI i lotti che la tengono
      --   sono il mio.
   OR (e.classe_emittibilita = 'TRATTENUTA'
       AND v_lotto_corrente IS NOT NULL
       AND e.trattenuta_da_lotti <@ ARRAY[v_lotto_corrente])
)
```

con `v_lotto_corrente` risolto da `fatturazione_lotti.lock_batch_id` (UNIQUE),
`NULL` = chiamante fuori pipeline = nessuna auto-esclusione (la risposta
prudente, identica all'emit).

⭐ **Sulla forma, una raccomandazione e non una richiesta.** Con D1 la
risoluzione `lock_batch_id → lotto` e il predicato «trattenuta soltanto da me»
esistono in **due** funzioni, e le due copie si sono **già** sfilate una volta
(questo brief). Il commento dell'emit chiama quella riga *«la riga senza la
quale questo changeSet romperebbe più di quanto ripara»*: una riga così vive
meglio in **una sede** (un helper `STABLE` che le due funzioni chiamano), ma la
scelta della forma è vostra. ⛔ Ciò che non regge è ricopiarla a mano e
affidarsi al fatto che oggi coincidono.

⚠️ `RETURNS TABLE` invariato; cambia la sola firma (parametro in coda con
default): i chiamanti che non lo passano non cambiano comportamento. ⚠️ E il
`COMMENT` della funzione va riscritto dove dice *«una commessa con SOLE righe
trattenute … non ha niente da dare»*: è vero solo se a trattenerle è un altro.

### D2 · ⚪ Una domanda: gli esiti `ERRORE` devono contare nel verdetto del lotto?

`vendite.fn_get_lotto_segnalazioni_summary` conta i log critici **attivi** e
`fatturazione_lotti_fatture.stato_esecuzione = 'ERRORE'`; gli esiti li usa
come denominatore e per l'`ESCLUSO`, **non** come segnale. Il runner ritira le
proprie bandiere all'avvio di ogni rerun (*«chi alza la bandiera la abbassa»*),
quindi se il pull non rivede una commessa nessuno le rialza — e l'unica traccia
durevole, l'esito `ERRORE` sul documento, non ferma niente.

Con D1 il caso normale si chiude da sé (il pull rivede la commessa: o riesce e
scrive `COMPLETED`, o fallisce e rialza la critica). Resta il caso in cui la
commessa **non è più visitabile per un motivo legittimo** (righe passate a
`RIFIUTATA`/`ANNULLATA`, o trattenute nel frattempo da un secondo lotto): il
lotto uscirebbe `COMPLETATO` con un documento **preso in carico e ancora in
`ERRORE`**, e nessuno lo vedrebbe.

⭐ **Raccomandazione:** contare `fatturazione_lotti_esiti.stato_esecuzione = 'ERRORE'`
in `is_error` / `blocks_next_step`. È coerente con la via d'uscita già
costruita — «Togli dal giro» porta l'esito a `ESCLUSO`, cioè l'operatore
**dichiara** che quel documento non fa più parte del lavoro — invece di lasciare
che il lotto lo dichiari a posto per sottrazione. È una decisione di modello
(cambia cosa significa «lotto in errore») e la lascio a voi e a Tid.

*Fatto datato, 2026-09-12:* 1 lotto in gioco (13338) con 2 esiti `ERRORE`;
7 lotti `COMPLETATO` e annullati con esiti `ERRORE` rimasti — il caso di
13337 non è il primo.

### Presidi

| | Dove | Prova | Il suo contrario |
| --- | --- | --- | --- |
| **P-5-bis** | `test-pull-non-prende-trattenuti-v1.sql` (estensione) o file gemello sulla discovery | al rerun, la commessa con **sola** riga trattenuta dal **proprio** lotto **è visitata** da `fn_list_commesse_emittibili` | trattenuta da un **altro** lotto in gioco ⇒ **non** visitata; identità `NULL` ⇒ non visitata |
| **P-5-ter** | idem | il percorso **intero** — discovery → emit — con lo stesso `p_emit_batch_id`: la riga esce emessa | — è il test che oggi manca: i due cancelli provati **insieme** |

⛔ I casi si costruiscono (due commesse, due lotti, esiti attaccati a mano),
come già fa il file esistente.

## 5. Lato backend — dopo il DB, non prima

Tre righe, e una regola d'ordine:

1. `CommesseRepository.list_commesse_emittibili` accetta `emit_batch_id` e lo
   binda come `p_emit_batch_id`;
2. `_handle_pull_attivita_da_commessa_task` lo passa (`context.lock_batch_id`),
   come già fa per l'emit;
3. ⚠️ **il guard su `lock_batch_id` assente si sposta PRIMA della discovery**:
   oggi sta dopo (riga ~1231 del step executor), e con D1 una discovery
   chiamata con `NULL` non fallirebbe — scarterebbe i propri documenti in
   silenzio, che è esattamente il difetto di questo brief con un vestito nuovo.

Presidio BE: un test con `richiedi_db_provvisto` che chiami la funzione **vera**
con il parametro nuovo — il binding non lo vede nessun mock
([[feedback_rinomina_db_binding_mockato]]).

## 6. ⛔ Cosa NON si fa

- **non** si riscrive il predicato in Python filtrando `commessa_ids` a valle:
  sarebbe la seconda sede della regola «questo documento è in gioco?»;
- **non** si tocca `fn_list_emittibili_lane`: decide quanti lotti **nascono**,
  non ha un lotto proprio da escludere;
- **non** si sana il dato: 13338 resta com'è — è la materia con cui si prova
  D1 senza ricostruire niente (ROOT già a posto, esiti `ERRORE`, lotto in
  gioco). Dopo l'apply, «Riprova step» su quel lotto **deve** tirare dentro le
  due commesse; se ancora risponde `totale 0`, D1 non è arrivato al percorso.

## 7. Stato

| | |
| --- | --- |
| DB | 🔵 in attesa: D1 · presidi P-5-bis/ter · risposta a D2 |
| BE | ⏸️ attende il DB (§5) |
| Collaudo | 🔴 prova 5 **sospesa** al rilancio; prove 3 e 4 da **rifare** dopo D1 (la 3 era passata il 09-09 alle 01:44, L3 è arrivato alle 17:12) |
