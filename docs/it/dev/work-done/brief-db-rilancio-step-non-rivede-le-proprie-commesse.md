# Brief DB — il rilancio dello step non rivede le proprie commesse

> **Destinatario:** team DB (`dev/db-tid`). Aperto il 2026-09-12 dal team BE — ✅ **chiuso il 2026-09-12 sera** (§7).
> ⚠️ Il testo dei §1-§7 è quello ricevuto dal team BE il 12-09, salvato qui dal
> team DB perché non era ancora sul ramo; il lavoro DB è registrato in **§8**.
>
> **Stato (12-09-2026):** ✅ **DB APPLICATO alle 12:44** (`20260912-12…16`
> `EXECUTED`), **pgTAP verdi** (Tid). Sul 13338 vivo: discovery con l'identità
> del lotto → **2** commesse, decimo numero del riepilogo → **2**.
> ✅ **BE + FE CONSEGNATI (12-09 pomeriggio, §9.6)**: discovery con l'identità
> dal repository (verificato sul 13338: `[]` senza, `[34137, 36984]` con),
> verdetto a tre addendi, drawer sul verdetto.
> ✅ **§11 (12-09 sera): i tre rilievi al DB di §9.7/§10** — `20260912-32…35` +
> 2 CSV scritti, provati e **applicati** (in git). ⭐ Trovata una causa sotto quella
> vista: `fn_cleanup_fatture_by_ids` usciva su «zero fatture» e non liberava niente.
> 🔴 **13:46 — «Riprova step» su 13338: D1 ha funzionato (`totale 2 · ok 2`) e
> il lotto è uscito lo stesso senza documenti.** Secondo difetto di modello,
> nell'orchestratore: i task a valle del pull erano `COMPLETATO` (a vuoto) e
> il resolver li ha **saltati**. Corretto alle 13:54 (§10). ⚠️ Il 13338 è
> compromesso come banco di prova: §10.4 dice come uscirne.
> ℹ️ Documento **unico** dal 12-09 pomeriggio: il brief BE originale
> (`brief-db-il-rilancio-non-rivede-le-proprie-commesse.md`, §1-§7 identici)
> è stato cancellato e i suoi link riallineati qui.
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
> **Correlati:** [brief-db-il-trattenuto-passa-lo-stesso](brief-db-il-trattenuto-passa-lo-stesso.md)
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
con il parametro nuovo — il binding non lo vede nessun mock.

## 6. ⛔ Cosa NON si fa

- **non** si riscrive il predicato in Python filtrando `commessa_ids` a valle:
  sarebbe la seconda sede della regola «questo documento è in gioco?»;
- **non** si tocca `fn_list_emittibili_lane`: decide quanti lotti **nascono**,
  non ha un lotto proprio da escludere;
- **non** si sana il dato: 13338 resta com'è — è la materia con cui si prova
  D1 senza ricostruire niente (ROOT già a posto, esiti `ERRORE`, lotto in
  gioco). Dopo l'apply, «Riprova step» su quel lotto **deve** tirare dentro le
  due commesse; se ancora risponde `totale 0`, D1 non è arrivato al percorso.

## 7. Stato — ✅ chiuso il 12-09-2026, sera

| | |
| --- | --- |
| DB | ✅ D1 (`20260912-12…16`), D2, i rilievi di §9.7 e §10 (`20260912-32…35`), pgTAP verdi — applicati su dev e in git |
| BE / FE | ✅ §5, §9.6, §10.3, e il ripiego di §11.6 |
| Collaudo | ✅ prove 3, 4 e 5 rifatte da Tid il 12-09 dopo la consegna: il rilancio **rivede** le proprie commesse; «Annulla» su un lotto fermo al pull riporta da solo le righe a `NON_EMESSA` |

*Com'era il 12-09 mattina, quando il BE lo ha consegnato: DB in attesa di D1 e
della risposta a D2, BE fermo al §5, prova 5 sospesa al rilancio (la 3 era
passata il 09-09 alle 01:44, L3 è arrivato alle 17:12).*

---

## 8. Lavoro DB (12-09-2026) — analisi, decisioni, consegna

### 8.1 La diagnosi regge, riprodotta sul catalogo

Letto il vivo: la discovery aveva la whitelist secca senza identità; l'emit
risolveva `lock_batch_id → v_lotto_corrente` e liberava con
`trattenuta_da_lotti <@ ARRAY[v_lotto_corrente]`. Sul 13338 in `BEGIN…ROLLBACK`
con contesto operatore: discovery coi due gruppi → **0**; emit dry-run su 34137
con l'identità → **1**; con `NULL` → **0**. Il test 3 di P-5 chiama solo l'emit:
la discovery non era nel percorso. Tutto come nel §2.

### 8.2 Le due decisioni

**D1 — la forma.** I due predicati **non sono uguali** e non devono diventarlo:
l'emit prende `NON_APPROVATA`/`RIFIUTATA` solo con `p_only_approved = false`, la
discovery sempre. La parte davvero comune è una sola: *«una riga `TRATTENUTA`
soltanto dal mio giro, per il mio giro è `PRONTA`»* — e nel `CASE` della vista
`TRATTENUTA` viene **dopo** i rami di approvazione, quindi una trattenuta è per
costruzione approvata. ⇒ L'helper è **la classe vista dal giro**,
`vendite.fn_classe_emittibilita_per_giro(classe, trattenuta_da_lotti, lotto)`,
`LANGUAGE sql IMMUTABLE`: il planner la **inlina** (verificato sul piano:
nessuna chiamata di funzione, il `CASE` espanso), quindi la sede unica è
gratis. La risoluzione `lock_batch_id → lotto` in `vendite.fn_lotto_da_emit_batch`
(`STABLE`, `SECURITY INVOKER` come i chiamanti). Ognuno dei due cancelli tiene
la propria whitelist sopra la classe vista dal giro. ⛔ La «raccomandazione» del
§4 è un **requisito**: la terza copia sarebbe la prossima a sfilarsi.

**D2 — sì (Tid, 12-09).** Un esito è un fatto su un documento preso in carico;
un lotto `COMPLETATO` con un documento il cui ultimo fatto è `ERRORE` si dichiara
a posto per sottrazione. Decimo conteggio **in coda** al riepilogo,
`esiti_stato_esecuzione_errore_count` (`ESCLUSO` non conta: è la via d'uscita).

### 8.3 Consegnato

| ChangeSet | Cosa |
| --- | --- |
| `20_code/vendite/20260912-12` | `fn_classe_emittibilita_per_giro` — SQL IMMUTABLE inlinabile, niente STRICT |
| `20260912-13` | `fn_lotto_da_emit_batch` — SQL STABLE, NULL/sconosciuto/fuori perimetro → NULL |
| `20260912-14` | emit: `v_lotto_corrente` dall'helper, predicato sulla classe vista dal giro; firma e identità invariate (`CREATE OR REPLACE`); comportamento identico su P-5 1-4; `COMMENT` nuovo (non ne aveva) |
| `20260912-15` | discovery: **`DROP`** della firma a 7 + `CREATE` a 8 con `p_emit_batch_id uuid DEFAULT NULL` — ⚠️ un default in più è un **overload**, con le due vive una chiamata a 7 argomenti sarebbe «function is not unique»; `RETURNS TABLE` invariato; `COMMENT` riscritto dove diceva «non ha niente da dare» |
| `20260912-16` | summary: `DROP` + `CREATE`, decimo conteggio in coda (`COALESCE(ea.de, 0)`) |
| pgTAP `test-pull-non-prende-trattenuti-v1` 5 → **13** | P-5-bis (5-7: altro lotto, identità NULL, **rerun visita**), P-5-ter (8-9: discovery → emit stessa identità, riga `EMESSA`), 10: la **premessa** dell'helper (una riga in `BOZZA` tenuta da un lotto è `NON_APPROVATA`, non `TRATTENUTA`), 11-12: D2 (mio=1/altrui=0; `ESCLUSO` non conta) |
| pgTAP `test-lotto-segnalazioni-summary-v2` 6 → **7** | la decima colonna esiste ed è **l'ultima** (`proargnames`) |

Chiamanti della firma censiti: `commesse_repository.py:1180` (per nome, 7
argomenti: continua a funzionare), cinque pgTAP per nome, nessuna funzione o
vista DB (`fn_check_commessa_chiudibile` la nomina in un commento).

### 8.4 Prove (SQL **estratto** con `updateSQL` offline, `BEGIN…ROLLBACK`)

* **Caso vivo 13338** coi cinque changeSet: una sola discovery a 8 argomenti;
  tabella di verità dell'helper (solo-mio → `PRONTA`; mio+altro → `TRATTENUTA`;
  senza identità → `TRATTENUTA`; `PRONTA`/`NON_APPROVATA` invariate); discovery
  senza identità **0** (come prima), con l'identità **2** commesse
  (`total_non_emesse` 1+1); percorso intero emit dry-run **1+1**; identità di un
  lotto sconosciuto → **0**; riepilogo: decimo numero **2**, dopo un `ESCLUSO`
  **1**, i primi nove invariati; piano: helper **inlinato**.
* pgTAP col DDL: P-5 **13/13**, summary-v2 **7/7**.
* **Mutazione** — tutto il DDL nuovo ma la discovery col corpo del `-61` sotto la
  firma nuova: rossi **esattamente** i tre del percorso (7, 8, 9), verde il
  resto. Senza, il file sarebbe verde per costruzione come lo era il test 3.
* Sei guardrail statici verdi.

### 8.5 Documentazione

Manuali nuovi `fn_classe_emittibilita_per_giro.md`, `fn_lotto_da_emit_batch.md`;
aggiornati `fn_list_commesse_emittibili.md` (sezione «il rilancio rivede le
proprie commesse»), `fn_emit_attivita_fatturabili_da_commessa.md`,
`fn_get_lotto_segnalazioni_summary.md` (il decimo numero); guida
`gestione-commesse.md` §5 (parametri e criteri); nota 🔴 al brief del trattenuto
su L3 («letto dal caso sbagliato»).

### 8.6 Che cosa resta

| | Cosa | Di chi |
| --- | --- | --- |
| ✅ | Apply `20260912-12…16` (12-09 12:44) e pgTAP verdi — `test-pull-non-prende-trattenuti-v1` (13), `test-lotto-segnalazioni-summary-v2` (7) | fatto (Tid) |
| ✅ | «Riprova step» su **13338** dopo la consegna BE: deve rispondere `totale 2` (la discovery, chiamata con l'identità del lotto, oggi le restituisce) — verificato in-app (Tid, 12-09) |
| ✅ | §5 BE: `list_commesse_emittibili(emit_batch_id)` → `p_emit_batch_id`; il guard su `lock_batch_id` **prima** della discovery; D2: `esiti_stato_esecuzione_errore_count` letto per nome e sommato in `is_error` — fatto il 12-09 pomeriggio, §9.6 | fatto (BE) |
| ✅ | Collaudo: prove 3, 4, 5 rifatte dopo D1 (Tid, 12-09) |
| ✅ | Commit dei file DB e doc (PR #1572) |

---

## 9. Piano di sviluppo BE / FE (12-09-2026, dopo la consegna DB)

> Scritto sul codice **vivo** al 12-09 pomeriggio, DB già applicato (§8.6).
> Ordine vincolante: **B → test BE → F → doc → collaudo**. Il FE non parte
> prima del BE perché legge un verdetto (`blocks_next_step`) che cambia con D2.

### 9.1 Il fatto che il piano deve portare a casa

Con D2 il verdetto del lotto cambia forma: **`is_error` può essere vero con
`critical_count = 0`** (documento preso in carico il cui ultimo esito è
`ERRORE`, nessuna critica viva). Oggi tre punti del frontend **ricalcolano**
il verdetto da `critical_count > 0` invece di leggerlo
(`LottoDrawer.haSegnalazioniCritiche`: banner, `numera`, `avanza_step`).
Fino a ieri le due copie coincidevano per costruzione; D2 è il giorno in cui
si sfilano, e a mentire sarebbe quella del client: **pulsante «Avanza» acceso
su un lotto che il runner rifiuta, nessun banner su un lotto in `ERRORE`**.
⇒ Il piano FE non è «mostrare un numero in più»: è **smettere di ricalcolare
il verdetto** e leggerlo dal backend, come già fa la scheda Segnalazioni
(`v-if="segnalazioni.blocks_next_step"`).

### 9.2 Backend

| # | Cosa | Dove | Nota |
| --- | --- | --- | --- |
| **B1** | `list_commesse_emittibili(…, emit_batch_id: UUID \| None = None)` → `p_emit_batch_id => %s` come **ottavo** argomento nominato | `apps/vendite/db/commesse_repository.py:1159` | Docstring: «senza identità la discovery scarta i propri documenti — il pull DEVE passarla». ⛔ `list_emittibili_lane` **non si tocca** (§6) |
| **B2** | Il guard `E_PIPELINE_SCOPE_INCOMPLETE` su `lock_batch_id` si sposta **prima** della discovery; la discovery riceve `emit_batch_id=context.lock_batch_id` | `pipeline_step_executor.py:1184-1250` | ⚠️ Il guard precede **anche il dry-run**: oggi il `return None` del dry-run sta fra discovery e guard, e una discovery senza identità in dry-run conterebbe **meno** commesse del giro vero — un dry-run che risponde a un'altra domanda. Il commento del guard va riscritto: i consumatori dell'identità sono **due** (discovery + emit), e il difetto che descrive («il lotto nascerebbe VUOTO senza un errore») vale identico per il primo |
| **B3** | D2 nel lettore: decima colonna `esiti_stato_esecuzione_errore_count` letta **per nome** (come i tre del banner), nel ripiego a riga assente e nel `TypedDict` | `pipeline_repository.get_lotto_segnalazioni_summary`, `types.LottoSegnalazioniSummary` | Commento nel `TypedDict`: *un esito è un fatto su un documento preso in carico; `ESCLUSO` non conta perché è la via d'uscita* (§8.2) |
| **B4** | D2 nel verdetto: `LottoSignalStatus` guadagna `esiti_stato_esecuzione_errore_count`; `is_error = critical > 0 OR fatture_stato_esecuzione_errore > 0 OR esiti_errore > 0`; `blocks_next_step = is_error` invariato | `lotto_segnalazioni_service.py:61` | ⭐ Il rilancio dello **stesso** step resta ammesso: `is_rilancio_stesso_step` nel runner non cambia — è proprio la via d'uscita per il caso D2 |
| **B5** | Il verdetto **spiega** il terzo motivo: `detail`/`context` di `E_PIPELINE_LOTTO_CRITICAL` e il payload `PIPELINE_COMPLETED` portano anche `esiti_errore_count` | `pipeline_runner.py:831-850`, `~1004-1030` | ⛔ Senza, un lotto bloccato per soli esiti direbbe `critical_count=0, stato_esecuzione_errore_count=0` — un rifiuto senza motivo, cioè un bug agli occhi di chi legge il log. Il `message` («segnalazioni critiche attive») diventa «segnalazioni critiche o documenti in errore»: il **codice** resta, la reazione del client è la stessa |
| **B6** | L'envelope di `GET lotti/<id>/segnalazioni/summary/` non cambia forma: il decimo numero viaggia dentro `summary` (dict passato intero) | `pipeline_service.fn_get_lotto_segnalazioni_summary` | Nessuna riga da scrivere, ma va **verificato** con un test: è un campo che il FE legge e che nessuno dichiara |

**Test BE**

| Livello | Test | Cosa prova (e il suo contrario) |
| --- | --- | --- |
| unit `test_pipeline_step_executor` | `test_pull_consegna_al_db_l_identita_del_giro` **esteso** | `list_commesse_emittibili` riceve `emit_batch_id == _LOCK_BATCH_GIRO`, non solo l'emit |
| unit | `test_pull_si_ferma_se_il_giro_non_ha_identita` **esteso** | `list_commesse_emittibili.assert_not_called()` — è la **mutazione** che distingue l'ordine nuovo dal vecchio: col guard dopo la discovery il test attuale resta verde |
| unit | dry-run senza identità **solleva** (test nuovo) | il contrario del comportamento di oggi, dichiarato in B2 |
| unit `test_lotto_segnalazioni_service` | `..._blocks_when_esiti_stato_esecuzione_errore` (nuovo); i tre esistenti aggiornati col decimo campo nel mock | `is_error`/`blocks_next_step` veri con `critical = 0`; falsi con tutto a zero |
| unit `test_pipeline_runner` | il `context` di `E_PIPELINE_LOTTO_CRITICAL` porta `esiti_errore_count`; il lotto esce `ERRORE` a fine giro con soli esiti in errore | B5 e B4 dal lato del runner |
| unit `test_pipeline_api` (o gemello) | l'envelope del summary contiene `summary.esiti_stato_esecuzione_errore_count` | B6 — *un campo emesso e non dichiarato non si nota, perché niente fallisce* |
| **DB provvisto** `apps/vendite/tests/db/test_discovery_riceve_l_identita_del_giro.py` (nuovo, `richiedi_db_provvisto` + `apri_contesto_operatore`, in transazione annullata) | (1) `list_commesse_emittibili(emit_batch_id=uuid4())` **lega** sulla funzione vera (nessun «function is not unique»: il `DROP` della firma a 7 è ciò che rende univoca la chiamata per nome); (2) `get_lotto_segnalazioni_summary` di un lotto qualunque torna la decima chiave. | Il binding non lo vede nessun mock: è la regola già pagata sulle rinomine SQL. ⛔ Non ripete P-5-bis/ter (13 pgTAP): il percorso discovery→emit è provato lì, qui si prova che il **Python arrivi** a quel percorso |

### 9.3 Frontend — `LottoDrawer.vue`

| # | Cosa | Dove | Nota |
| --- | --- | --- | --- |
| **F1** | Il gate di `numera` e `avanza_step` legge **`segnalazioni.blocks_next_step`**, non `critical_count > 0` | `LottoDrawer.vue:797`, `:815` | ⛔ È la sede unica del verdetto: il DB non conosce le segnalazioni, il BE le somma agli esiti, il FE **rende**. `haSegnalazioniCritiche` resta solo dove parla davvero di critiche (etichetta della scheda, riga 539); il tooltip `blocca_step` già dice «le segnalazioni bloccano» e va allargato («…o documenti in errore») |
| **F2** | Il banner compare su `blocks_next_step` (`v-if`, riga 1301) e la frase guadagna il **ramo D2**: `documenti = 0 ∧ giro = 0 ∧ esiti_errore > 0` → chiave nuova `vendite.lotti.segnalazioni_bloccanti_esiti` (plurale, `it` + `en`): *«Il giro è fermo per {n} documento/i preso/i in carico il cui ultimo tentativo è fallito e che nessun rilancio ha ripreso: si corregge la causa e si rilancia lo step, oppure si toglie dal giro»* | `fraseBanner`, riga 440 | ⛔ I conteggi **non si sommano**: un documento con critica viva ha anche l'esito `ERRORE` (sovrapposizione sconosciuta al client). Regola: se ci sono critiche vive parlano **quelle** (segnale più fresco, frasi esistenti invariate); il ramo nuovo scatta **solo** quando le critiche sono zero — che è esattamente il caso che D2 esiste per rendere visibile |
| **F2-bis** | La **scelta del ramo** di `fraseBanner` esce dal componente in una funzione **pura**: entrano i numeri (`critiche`, `documenti`, `giro`, `esitiErrore`, `rimediabile`), esce `{chiave, argomenti}`; il componente chiama `t()` su ciò che riceve | nuovo `src/vendite/_shared/lotti/ramoBannerLotto.js` (+ `.spec.js`) | ⭐ Deciso con Tid il 12-09: **cinque** rami su **due** assi (rimediabile × specie del blocco) sono il posto in cui un `if` sbagliato non fallisce — mostra la frase sbagliata, e si vede solo quando capita quel caso a video. Una spec Vitest **un caso per ramo** più i limiti (tutto a zero; congelato con soli esiti). Stesso modello delle `fn_check_*`: la regola in una sede, senza effetti collaterali. ⛔ La funzione non conosce `t`, né il lotto, né lo store: numeri dentro, decisione fuori |
| **F3** | Il link del banner atterra sulla scheda **giusta per il ramo**: critiche → «Segnalazioni» filtrata sulle critiche (oggi); ramo D2 → **«Presi in carico»** (`gruppi`, la lista degli esiti), dove la riga in `ERRORE` porta `ErroreRigaInfo` e il verbo «Togli dal giro»; fatture in errore → «Documenti» | `apriSegnalazioni`, riga 570 | ⛔ Nel ramo D2 la scheda Segnalazioni sarebbe **vuota**, e anche «Documenti»: se il pull è fallito una fattura non è mai nata. Un link che porta su un elenco senza quella riga è il vicolo cieco che le linee guida vietano — ⚠️ corretto in corso d'opera: la prima stesura diceva «Documenti» |
| **F4** | Giro **congelato** (`giroRimediabile = false`): la frase al passato usa `nCritiche`; con zero critiche e soli esiti direbbe «0 segnalazioni critiche». Chiave gemella `segnalazioni_giro_chiuso_esiti` sul numero degli esiti | riga 456 | Stessa regola di F2: critiche se ci sono, esiti altrimenti |
| **F5** | Lista Lotti (`useLottoAzioni`, kebab): **nessuna modifica** — verificato il 12-09: né il composable né `LottiListView` leggono `critical_count`/`blocks_next_step` (la riga di lista non ha il summary), il runner rifiuta da sé | `useLottoAzioni.js` | Il gate nel drawer (F1) resta l'**unica** copia lato client, ed è una lettura, non un calcolo |

**Presidio FE.** Due livelli: la spec di **F2-bis** prova i cinque rami della
frase (un caso ciascuno, senza montare il drawer); il collaudo in-app su
**13338** (§8.6) prova che il ramo D2 arrivi a video con i numeri veri.

### 9.4 Documentazione

| Doc | Cosa |
| --- | --- |
| `docs/it/backend/vendite/manual/api_lotto_segnalazioni_summary.md` | decimo campo di `summary`, la regola di `is_error` con i **tre** addendi, la nota «`ESCLUSO` non conta» |
| `docs/it/dev/api.md` | niente: l'envelope non cambia forma |
| `collaudo-in-app-esito-parziale-pull-commessa.md` | prove 3, 4, 5 da rifare; esito di «Riprova step» su 13338 (deve dire `totale 2`) |
| questo brief | §8.6 aggiornato; a collaudo chiuso → `work-done/` |

### 9.5 Ordine e chiusura

1. B1 → B2 → test unit del pull → **`kill -HUP` sul master gunicorn** (nessun autoreload in dev);
2. «Riprova step» su **13338** (Tid): atteso `totale 2 · ok 2` — se `totale 0`, D1 non è arrivato al percorso e si torna a B2 prima di toccare altro;
3. B3 → B4 → B5 → test service/runner/api → test DB provvisto;
4. F1 → F2 + F2-bis (spec verde) → F3 → F4 → `check_i18n_keys.py` verde;
5. doc §9.4; prove 3, 4, 5 del collaudo; brief in `work-done/`.

⛔ **Cosa non si fa** (in aggiunta al §6): non si tiene `haSegnalazioniCritiche`
come gate «per compatibilità» accanto a `blocks_next_step` — due gate sono la
copia che questo piano toglie.

### 9.6 Consegnato (12-09-2026, pomeriggio)

| # | Dove | Nota |
| --- | --- | --- |
| B1 | `commesse_repository.list_commesse_emittibili(emit_batch_id=…)` → `p_emit_batch_id => %s::uuid` | docstring col perché e il divieto di `None` in pipeline |
| B2 | `pipeline_step_executor._handle_pull_attivita_da_commessa_task`: guard **prima** della discovery (e del `return` dry-run), `emit_batch_id=context.lock_batch_id` alla discovery | commento riscritto sui **due** consumatori dell'identità |
| B3 | `pipeline_repository.get_lotto_segnalazioni_summary` + `types.LottoSegnalazioniSummary`: decima colonna per nome, nel ripiego, nel `TypedDict` | — |
| B4 | `LottoSegnalazioniService`: `is_error` a tre addendi, `LottoSignalStatus.esiti_stato_esecuzione_errore_count` | `blocks_next_step = is_error` invariato; il rilancio dello stesso step resta ammesso |
| B5 | `pipeline_runner`: `E_PIPELINE_LOTTO_CRITICAL` porta `esiti_errore_count` in `detail` e `context`, messaggio «segnalazioni critiche **o documenti in errore**»; `PIPELINE_COMPLETED` porta il terzo conteggio | codice invariato |
| Test BE | `test_pipeline_step_executor` (23e/23f estesi, 23g nuovo: il guard precede la discovery **e** il dry-run dell'handler), `test_lotto_segnalazioni_service` (5, fixture a dieci chiavi), `test_pipeline_runner` (49: blocco per soli esiti, col motivo nel context), `test_pipeline_repository` (tupla a dieci, colonna chiesta per nome), `test_pipeline_service` (5: l'envelope porta il decimo numero) | `apps.vendite.tests`: **1994 verdi** |
| Test DB provvisto | `apps/vendite/tests/db/test_discovery_riceve_l_identita_del_giro.py` (3): la firma a 8 lega, è **una sola** in `pg_proc`, il riepilogo legge la decima chiave dalla funzione vera | 3/3 con `ZEROERP_TEST_DB_E2E=1` |
| Verifica D1 | discovery dal repository sul **13338** in transazione annullata: senza identità `[]`, con identità **`[34137, 36984]`** | è il punto 2 del §9.5, fatto senza aspettare il click |
| F1 | `LottoDrawer`: `lottoFermo = blocks_next_step === true` (fail-closed) governa banner, `numera`, `avanza_step`; `haSegnalazioniCritiche`/`nCritiche` **tolti** (zero residui) | — |
| F2 + F2-bis | `src/vendite/_shared/lotti/ramoBannerLotto.js` (`scegliRamoBanner`, `conteggiDaSegnalazioni`) + `.spec.js` **15 casi** | ⭐ totale sul verdetto: rami per critiche di documento / del giro / del canale fattura / esiti in errore / fatture in errore, su entrambi gli assi; `null` → frase generica `blocca_step` (fail-visible su un quarto addendo) |
| F3 | il link del banner atterra su `ramo.scheda`: Segnalazioni (filtrata) per le critiche, **Presi in carico** (`gruppi`) per gli esiti in errore, Documenti (`fatture`) per le fatture in errore | verificato sui `TabPanel`: gli esiti stanno nella lista `vendite.lotto_gruppi`, non fra le fatture |
| F4 | giro congelato: chiavi gemelle `segnalazioni_giro_chiuso_esiti` / `_fatture` | mai «0 segnalazioni critiche» |
| i18n | 4 chiavi nuove `it`+`en` (`segnalazioni_bloccanti_esiti`, `_fatture`, `segnalazioni_giro_chiuso_esiti`, `_fatture`); `blocca_step` allargato («…o i documenti in errore») | `check_i18n_keys.py` verde |
| Doc | `api_lotto_segnalazioni_summary.md` (decimo campo, verdetto a tre addendi, regola «il client legge, non ricalcola»); catalogo BB FE (`scegliRamoBanner`) | — |
| Runtime | `kill -HUP` sul master gunicorn alle 13:24:57, worker nuovi; `vite build` verde | in-app pronto |

### 9.7 Revisione critica del consegnato (12-09, richiesta da Tid)

Cercati bug, codice fragile o duplicato, valori cablati. Trovati e corretti:

| # | Cosa | Correzione |
| --- | --- | --- |
| 1 | `get_lotto_segnalazioni_summary`: le dieci chiavi scritte **tre** volte (SELECT, ripiego, mapping `row[9]`) — la forma posizionale che il commento della funzione DB dichiara pericolosa | i nomi vengono dal cursore (BB `row_to_dict`); la SELECT è la sola sede; il test del repository dichiara i nomi nell'ordine della SELECT |
| 2 | `pipeline_runner`: la nota «Step completato con **fatture** in errore» scritta **due** volte (`stato_operativo` + `errore` del giro) e **falsa** dopo D2 — un lotto fermato da un pull fallito non ha fatture | `_NOTA_STEP_CON_ERRORI`, una sede, «segnalazioni o documenti in errore» |
| 3 | FE: gli id delle schede (`'gruppi'`, `'fatture'`, `'segnalazioni'`) scritti a mano nel template del drawer **e** nella funzione pura — una rinomina lascia la pagina senza pannello, senza errore | `LOTTO_SCHEDE` in `vendite/constants.js`, usato da `<Tab>`/`<TabPanel>`, dal reset alla chiusura, dal link del banner e da `scegliRamoBanner`; tolte le tre costanti `SCHEDA_*` (erano alias: un nome solo) |
| 4 | test su DB provvisto: data cablata (`date(2026, 9, 1)`) e `skipTest` se non c'è nessun lotto — in CI, dove il DB nasce vuoto, **verde per sottrazione** | primo del mese corrente; il lotto si **costruisce** (`max(id)+1`, la funzione non solleva su un id inesistente) e si asserisce lo zero **e** l'insieme intero delle dieci chiavi contro il `TypedDict` |
| 5 | `test_pipeline_service.py` su `unittest.TestCase`: un mock dimenticato avrebbe parlato col DB di sviluppo restando verde | `SimpleTestCase` — i cinque test passano, quindi non toccano il DB |

⚠️ **Non corretto, da segnalare al DB**: a catalogo (`messaggi_errore.csv`)
`E_PIPELINE_LOTTO_CRITICAL` dice ancora «Lotto con segnalazioni critiche.», e
il ripiego BE (`error_messages_fallback.py`) lo ricopia. Nell'envelope vince il
messaggio Python (codice non tecnico), quindi a video esce la frase nuova; ma
catalogo e ripiego vanno allineati a «…o documenti in errore» — la riga CSV è
del team DB, il ripiego segue.

**Resta a Tid**: «Riprova step» su 13338 (atteso `totale 2 · ok 2`, lotto
`COMPLETATO`, esiti `COMPLETED`); prove 3, 4, 5 del collaudo; commit; brief in
`work-done/`.

---

## 10. Secondo difetto — il rilancio non ripercorre la catena (12-09, 13:46)

### 10.1 Il fatto

«Riprova step» su **13338** alle 13:46:01, col codice nuovo (gunicorn riavviato
alle 13:45:33): task run **4055** `pull_attivita_da_commessa` tentativo 2 →
`COMPLETATO · totale 2 · ok 2 · falliti 0`, esiti 1923/1924 → `COMPLETED`.
**D1 ha funzionato.** Ma dopo 4055 non c'è nessun altro task run: il lotto è
`COMPLETATO` con **zero fatture**.

### 10.2 Dov'è il difetto — sul modello

Lo step DRAFT è una **catena** di quattro task: `pull` → `select_attivita` →
`generate_fatture_righe` → `snapshot_indirizzi`. Al primo giro (11:23) il pull
ha fallito e i tre a valle sono girati **a vuoto** e chiusi `COMPLETATO`
(4038, 4039, 4040). `fn_resolve_lotto_task_execution_mode` decide **per
task**, guardando la sola ultima corsa di quel task: `COMPLETATO → SKIP`. Al
rilancio il pull è stato rieseguito (`RESUME`) e i tre a valle **saltati** come
«già fatti» — su un input che il pull aveva appena cambiato. Le due attività
emesse (AF 26829, 29693, marchio del lotto) non sono mai state lockate né
fatturate.

⭐ Il resolver non è sbagliato: risponde alla domanda che gli si fa. La domanda
che manca — *«qualcosa a monte è stato eseguito in questo giro?»* — la sa solo
l'orchestratore, ed è lì che vive la regola.

### 10.3 La correzione (BE, 13:54)

`PipelineStepExecutor.execute_step`: **a valle di un task eseguito in questo
giro nessun task si salta**. `_run_task` ritorna se ha eseguito l'handler;
il ciclo porta il flag `a_valle_di_task_eseguito` e uno `SKIP` del resolver
si onora solo se nulla a monte è stato eseguito. Un task a valle rieseguito
apre un **nuovo tentativo** (`fn_start_lotto_task_run` conta `max+1`, nessun
guard su `COMPLETATO`).

⚠️ È sicuro perché i task a valle sono **idempotenti per costruzione**:
`fn_select_attivita_fatturabili` prende solo le AF non ancora lockate,
`generate_fatture_righe` legge solo le AF non fatturate con testate
get-or-create, lo snapshot salta le fatture già servite. Un task a valle non
idempotente sarebbe un difetto suo, non una ragione per saltarlo.

Presidio: `test_pipeline_step_executor` 14a (pull `RESUME` + select `SKIP` ⇒
il select **esegue** e apre il suo task run) e 14b, la controprova (tutto
`SKIP` ⇒ niente esegue — la regola non degenera in «non saltare mai»).
`apps.vendite.tests`: **2013 verdi**. Gunicorn ricaricato alle 13:54:31.

📮 **Per il DB, da valutare**: la policy `resume_mode = RESUME_STEP` esiste a
catalogo (`generate_fatture_righe`) e **nessuno la implementa** — il resolver
la usa solo per distinguere `RESUME` da `RESET_REQUIRED`. Con la regola di
catena nell'orchestratore è un valore dichiarato e morto: o gli si dà il
mestiere che il nome promette, o si ritira.

### 10.4 Il 13338 com'è adesso, e come uscirne

| | |
| --- | --- |
| lotto | `COMPLETATO`, stato_doc `DRAFT`, tutti e quattro i task `COMPLETATO` |
| AF 26829 (comm. 34137), 29693 (comm. 36984) | `emit_batch_id` = marchio del lotto, **`lock_batch_id` NULL**, non fatturate |
| righe di commessa 64556, 70299 | `stato_emissione = EMESSA` — classe `EMESSA`, `trattenuta_da_lotti = {13338}` |
| azioni | DB: solo **Annulla**; FE: «Avanza» (porterebbe a EMESSA con zero fatture) |

Un nuovo «Riprova step» sul 13338 **non farebbe niente**: con tutti i task
`COMPLETATO` nulla a monte viene eseguito e la regola nuova non scatta — è il
comportamento corretto su un lotto davvero finito, e il 13338 *sembra* finito.

⇒ **Strada**: «Annulla» il 13338, poi **rifare la prova 5 su un lotto nuovo**
(guasta le ROOT, giro → `ERRORE`, ripristina, «Riprova step»: atteso pull
`totale 2 · ok 2` **e** due fatture in «Documenti»).
⚠️ Le due righe di commessa **non tornano `NON_EMESSA` con l'annullo**, e va
saputo prima di stupirsi: `fn_annulla_lotto_da_draft` libera le AF via
`fn_cleanup_fatture_by_ids` **per `lock_batch_id`** (il lock del `select`), e
queste due un lock non l'hanno mai avuto — sono emesse, non prese in carico.
Compariranno fra i **residui** della Lente 1: «**Riporta da emettere**» le
rimette `NON_EMESSA`, e da lì la prova 5 riparte.

📮 **Per il DB — terzo rilievo, sul modello, e non è teorico**: fra il pull e
il `select` esiste una finestra in cui un'AF è **emessa** (`emit_batch_id`) ma
**non lockata** (`lock_batch_id`). Un giro che cade lì — o, come qui, un
`select` saltato — lascia AF che nessuna delle tre porte di reset (`annulla`,
`riporta_a_draft`, `elimina_fattura`) ripristina, perché tutte liberano per
`lock_batch_id`. **Verificato il 12-09 alle 15:31 sul 13338 annullato da Tid**:
righe di commessa rimaste `EMESSA`, AF libere col marchio del lotto morto, e
**«Riporta da emettere» le rifiuta** (`E_ATTIVITA_GIA_DA_EMETTERE`,
`ATTIVITA_GIA_DISPONIBILE`: `fn_check_attivita_riportabile_da_emettere` guarda
il solo livello AF, che risultava già libero). I due livelli erano divergenti —
esattamente il caso che il commento di `fn_libera_attivita_fatturabili`
descrive («un livello torna in coda e l'altro no, in silenzio») — e nessun giro
le avrebbe mai riprese: il pull le vede `EMESSA`, il `select` di un lotto nuovo
non trova il suo marchio. Riparate a mano con la primitiva
`fn_libera_attivita_fatturabili(ARRAY[26829, 29693])` → `(2, 2)`, righe
`NON_EMESSA`, classe `PRONTA`.
Due cose da valutare: (1) `fn_cleanup_fatture_by_ids` prenda anche
`af.emit_batch_id = p_lock_batch_id AND af.fatturato IS FALSE AND
af.lock_batch_id IS NULL` — è la stessa identità, e il reset globale «libera
anche le attività agganciate al lotto che non sono mai diventate riga», che è
esattamente il loro caso; (2) il check «riportabile» riconosca la divergenza
AF libera / riga `EMESSA` come **riportabile**, non come «già disponibile»:
oggi lo stato rotto è irraggiungibile da ogni verbo.

---

## 11. Lavoro DB sui rilievi di §9.7 e §10 (12-09-2026, sera)

> Richiesti dal team BE, decisi con Tid il 12-09: **A** allineamento del
> catalogo, **B** ritiro di `RESUME_STEP` (non implementazione), **C** le porte
> di reset e il check «riportabile». Stato: ✅ **scritti e provati, in attesa di
> apply**.

### 11.1 A — `E_PIPELINE_LOTTO_CRITICAL` (§9.7)

Una riga di CSV (`messaggi_errore.csv`, id 696; il mirror è `runOnChange`):
messaggio = la frase del BE («Lotto bloccato per segnalazioni critiche o
documenti in errore.»), più `causa` e `soluzione` compilate — la soluzione è la
via d'uscita D-Q p.1 («…o toglierli dal giro, poi rilanciare lo step»). 📮 BE:
il ripiego `error_messages_fallback.py` segue.

### 11.2 B — `RESUME_STEP` ritirato (§10.3)

Letto sulla struttura: il resolver trattava `RESUME_STEP` e `RESUME_TASK` in modo
identico, il BE leggeva il valore e non lo usava; 12 righe su 27. Una distinzione
senza differenza — e **non** da implementare: la ripresa a livello di step vive
nell'orchestratore, darla al resolver (che decide per task) duplicherebbe o
contraddirebbe la regola di catena.

| ChangeSet / file | Cosa |
| --- | --- |
| CSV `fatturazione_pipeline_task_policy.csv` | 12 righe → `RESUME_TASK` |
| `00_schema/vendite/20260912-32` | bonifica `UPDATE` + CHECK `{RESET_STEP, RESUME_TASK}` **nello stesso changeSet** (`00_schema` gira prima del mirror: senza la bonifica l'ADD CONSTRAINT fallirebbe su dev); `COMMENT` della colonna |
| `20_code/vendite/20260912-33` | resolver senza `RESUME_STEP` nella lista; `COMMENT` nuovo che dice dove vive la regola di catena |
| pgTAP `test-fatturazione-pipeline-task-runtime` 18 → **19** | il CHECK respinge `RESUME_STEP` (`23514`) — sul vincolo, non sull'assenza di righe |

### 11.3 C — le porte di reset e «Riporta da emettere» (§10.4)

**C.1 `fn_cleanup_fatture_by_ids` (`20260912-34`)** — due correzioni, e la
seconda non era nel rilievo:

1. il perimetro del reset globale include le attività **emesse e non lockate**:
   `emit_batch_id = p_lock_batch_id AND lock_batch_id IS NULL AND fattura_riga_id
   IS NULL` — la stessa identità del giro letta dal marchio (la `select` lockа
   solo attività col proprio marchio, quindi nessun giro le riprendeva);
2. 🔴 **l'uscita anticipata su «zero fatture»**: la funzione usciva subito se
   l'elenco fatture era vuoto — e un lotto fermo prima di `generate_fatture_righe`
   (il 13338, ogni pull fallito) non ha fatture. Il reset non liberava **nessuna**
   attività, nemmeno quelle lockate dalla `select`. L'ha preso il pgTAP nuovo
   alla prima corsa (`updated_attivita = 0` da `fn_annulla_lotto_da_draft` col
   ramo nuovo già dentro). Ora esce solo senza fatture **e** senza giro.

**C.2 `fn_check_attivita_riportabile_da_emettere` (`20260912-35`)** — la `vis`
legge i due livelli (`stato_emissione` della riga; lotto del marchio in gioco via
`fn_lotto_da_emit_batch` + `vw_lotti_fase`): libera + `NON_EMESSA` → motivo 3
com'era; libera + `EMESSA` + lotto **in gioco** → **motivo 5** nuovo
(`E_ATTIVITA_IN_LAVORAZIONE`, `reason` `ATTIVITA_EMESSA_IN_GIRO_VIVO`, stessa
`reason_key`: il transito fra pull e `select` non si libera da sotto un giro
vivo); libera + `EMESSA` + lotto morto/senza marchio → **nessun motivo**,
riportabile. Firma e uscita invariate; il verbo non cambia.

**Presidio** `db/pgtap/vendite/test-af-emessa-non-lockata-reset-e-riporto-v1` (9):
la finestra si costruisce col **pull vero**; in giro vivo → in lavorazione;
«Annulla» riporta la riga a `NON_EMESSA` e l'attività a `PRONTA`; la divergenza
costruita (lotto morto) è riportabile e il verbo la riallinea; controprove: libera
+ `NON_EMESSA` → «già da emettere», e il reset per-fattura (`NULL`) non tocca il
ramo nuovo.

### 11.4 Prove (SQL **estratto** con `updateSQL` offline, `BEGIN…ROLLBACK`)

`test-af-emessa-non-lockata…` **9/9**; `test-fatturazione-pipeline-task-runtime`
**19/19**; P-5 **13/13** (invariato). Mutazione — DDL di B ma **senza** `-34`/`-35`:
rossi 2, 3, 4, 5 e il verbo esplode con `E_ATTIVITA_GIA_DA_EMETTERE`, cioè il
comportamento di oggi. Sei guardrail verdi. ⚠️ Prove da owner.

### 11.5 Documentazione

Manuali: `fatturazione_pipeline_task_policy` (vocabolario), `fn_resolve_lotto_task_execution_mode`
(«non cercare qui la regola di catena»), `fn_cleanup_fatture_by_ids` (le due
correzioni), `script/fn_check_attivita_riportabile_da_emettere` (cinque motivi);
guida `analisi-tracciamento-processi-e-job`.

### 11.6 Che cosa resta

| | Cosa | Di chi |
| --- | --- | --- |
| ✅ | Apply `20260912-32…35` + CSV (su dev il 12-09, in git); pgTAP `vendite/test-af-emessa-non-lockata-reset-e-riporto-v1` (9), `vendite/test-fatturazione-pipeline-task-runtime` (19), `vendite/test-pull-non-prende-trattenuti-v1` (13) | fatto |
| ✅ | `error_messages_fallback.py`: frase di `E_PIPELINE_LOTTO_CRITICAL` allineata al catalogo (12-09 sera); `RESUME_STEP` non e' nominato da nessun codice BE — restava in un solo commento di test, riscritto su `RESUME_TASK` | BE |
| ✅ | Collaudo: prova 5 su un lotto nuovo (§10.4) e «Annulla» su un lotto fermo al pull che riporta le righe a `NON_EMESSA` da solo — fatti da Tid il 12-09 |
| ⏳ | Commit degli ultimi tre file BE (ripiego, commento di test, questo brief) e dello spostamento in `work-done/` | **Tid** |
