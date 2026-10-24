# Come si scrive un test pgTAP

> **A chi serve**: chiunque aggiunga o modifichi un test in `db/pgtap/`.
> **Da dove viene**: tre giorni di lavoro nell'agosto 2026, e ogni regola qui
> sotto è costata un difetto vero. Storia e misure:
> `docs/it/dev/work-done/brief-db-pgtap-runner-rls-baseline.md`.
> **Ultimo aggiornamento**: 25 ottobre 2026

## La cosa da sapere per prima

**I test girano come l'applicazione.** `scripts/testpgtap.sh` si connette come
`zeroerp_app` con il contesto operatore, e **le policy RLS sono attive**.

Fino al 2026-08-07 giravano come owner, che la RLS la salta: in pratica nessun
test verificava una policy. Se trovi un documento — una guida, un commento —
che dice «il pgTAP gira come owner», è vecchio.

**Cosa cambia per te.** Un rosso può essere **un permesso** o **una policy**,
non solo una fixture. E una fixture che scrive dove l'applicazione non scrive
non passa più: è un difetto, non un dettaglio.

## Non partire da zero

```bash
cp db/pgtap/_TEMPLATE.sql.txt db/pgtap/<schema>/test-<cosa>.sql
```

Il template porta il preambolo giusto e, accanto a ogni riga, **perché** c'è.
È lo strumento più utile di questa guida: le regole che si applicano da sole
sono le uniche che sopravvivono.

## Le tre righe del preambolo

Sono presidiate da `scripts/guardrail_pgtap_preambolo.py`: se ne manca una senza
dichiararlo, la CI si ferma.

| riga | cosa succede senza |
|---|---|
| `BEGIN;` … `ROLLBACK;` | un fallimento a metà lascia i dati di prova nel database, e **la corsa successiva vede un rosso non suo** |
| contesto applicativo | con la RLS attiva le `SELECT` della fixture leggono **zero righe**: le asserzioni finiscono nei rami `skip` e il file diventa **verde per sottrazione** |
| `SET CONSTRAINTS ALL IMMEDIATE` | i **365 vincoli differiti** scattano al `COMMIT`, che qui non arriva mai: non vengono esercitati, e di nuovo verde per sottrazione |

⚠️ **`SET CONSTRAINTS` non va «sempre in testa»**: va **dove l'unità di lavoro è
completa**. Se la fixture crea un padre in un'istruzione e il suo satellite in
quella dopo, in testa fa scattare il vincolo a metà strada. Si sposta dopo
l'ultima coppia — e comunque **prima** di ogni cleanup, o scatta su righe già
cancellate.

⛔ **E se la sposti, la finestra la dichiari**: subito dopo la riga di contesto,
`SET CONSTRAINTS ALL DEFERRED;`. La finestra differita «di default» non è una
promessa di nessuno: su un database vuoto la riga di contesto **costruisce** il
mondo ed esce con i vincoli IMMEDIATE, come ogni helper (sotto, §«Il mondo si
costruisce»). Un file che fra il contesto e il proprio `SET CONSTRAINTS ALL
IMMEDIATE` costruisce una saga contando sul default è **verde su dev e rosso in
CI** — e lo è solo quando è il primo della corsa, che è il modo peggiore di
esserlo: `anagrafiche/create-cliente` il 2026-09-21, «due volte in due giorni»
senza riprodursi da solo.

### Se una di queste non ci può stare

Si **dichiara**, non si spiega e basta:

```sql
-- pgtap-contesto: escluso — <perché>
-- pgtap-differiti: escluso — <perché>
```

Una ragione in prosa non è leggibile da un cancello, e soprattutto **non
distingue «escluso apposta» da «dimenticato»**. Nell'agosto 2026 la famiglia
`rls/` fu esclusa **in blocco** dal contesto: almeno un file non ne aveva
diritto e girava con 4 asserzioni su 5 in `skip`, per settimane.

## Le fixture

### L'emittente non si pesca, si deriva

Un documento appartiene all'emittente di **chi agisce**, e le policy
`ef_whitelist` lo pretendono. Due convenzioni, due helper:

```sql
emittente_fiscale_id        = script.fn_pgtap_emittente_operatore()      -- preventivi, ordini, ddt, resi
emittente_soggetto_ruolo_id = script.fn_pgtap_emittente_sr_operatore()   -- commesse, fatture, lotti
```

⚠️ **Non è una scorciatoia per far passare la RLS**: rende scrivibile ciò che
l'applicazione scriverebbe. Una fixture che ha bisogno di un emittente *diverso*
sta collaudando la separazione fra emittenti — quella non si aggira, si
costruisce cambiando contesto.

### Il mondo si costruisce, non si cerca — e prima del contesto

Su un database ricostruito dai changelog (la CI, un'installazione nuova) il
**catalogo** c'è tutto e le **anagrafiche** sono a zero: nessun emittente,
nessun operatore, nessun cliente. Una fixture che li *cerca* (`SELECT … FROM
anagrafiche.emittenti_fiscali ORDER BY id LIMIT 1`, «un operatore con
whitelist», «un cliente libero») lì non trova niente e il file muore nel
fixture — copertura **zero**, non parziale. Il 2026-09-12 erano così **21 test
del perimetro** (`script/test-fn-scope-*`, `rls/*`): la proprietà fail-closed
delle funzioni di scope era collaudata solo sulla macchina di sviluppo.

Costruire i casi significa costruire anche **l'azienda e chi ci lavora**:

| Serve | Helper |
| --- | --- |
| **il mondo di un test di dominio**: azienda + operatore + contesto aperto + un cliente fatturabile legato a quell'azienda | `dbops.fn_pgtap_crea_mondo_cliente('<etichetta>')` |
| ⚠️ i builder che ricevono il **billing account di un'altra fixture** non costruiscono un cliente in più: prendono l'azienda di chi agisce (serve un contesto aperto) e verificano il conto | `dbops.fn_pgtap_cliente_del_builder` / `dbops.fn_pgtap_azienda_di_chi_agisce` (building block, non si chiamano dal test) |
| **una fattura** del mondo (registro coerente; nasce in bozza e arriva allo stato chiesto per la matrice, con indirizzi e intestazione scritti come fa la fatturazione) — col quarto e quinto parametro fuori bozza **senza indirizzi** e/o **senza intestazione** | `dbops.fn_pgtap_crea_fattura('<etichetta>'[, '<stato>'[, <ba_id>[, <senza_indirizzi>[, <senza_intestazione>[, <minimo>, <totale_a_pagare>, <termine_pagamento_id>[, <senza_utility>]]]]]])` |
| **un contratto** del mondo, nato dalla madre del dominio (`DRAFT`; `ATTIVO` con un listino del mondo; `ANNULLATO` dal verbo) — col terzo parametro sul cliente di un'altra fixture, per esempio quello di una commessa; col quarto il **figlio di un'offerta** accettata, nato dalla push; dal quinto all'ottavo **periodo, data e listino** del test | `dbops.fn_pgtap_crea_contratto('<etichetta>'[, '<stato>'[, <ba_id>[, <offerta_id>[, <valido_dal>, <valido_al>, <data>, <listino_id>]]]])` |
| **un ordine** di vendita del mondo (emittente del cliente, numero dal dominio; nasce in bozza e arriva allo stato chiesto per la matrice); col quarto parametro la **data dell'ordine**, scritta alla nascita | `dbops.fn_pgtap_crea_ordine('<etichetta>'[, '<stato>'[, <ba_id>[, <data>]]])` |
| **una bolla nata da un ordine** confermato, dalla madre del dominio (con causale e indirizzi che l'emissione pretende), nello stato chiesto — default **consegnata**; `DRAFT` per scriverle qualcosa in bozza e poi portarla avanti; due spedizioni dalla stessa riga con `p_qta_da_evadere` e poi `p_ordine_id`; da un ordine speciale costruito dal test con `p_ordine_id` | `dbops.fn_pgtap_crea_ddt_da_ordine('<etichetta>'[, '<stato>'[, <ba_id>]], p_quantita => …, p_prezzo => …, p_articolo_id => …, p_fatturazione_trigger => …, p_ordine_id => …, p_qta_da_evadere => …, p_righe => …, p_data => …, p_causale_codice => …, p_data_ordine => …)` (per nome) |
| **un preventivo** del mondo (emittente del cliente, numero dal dominio, validità da oggi; nasce in bozza e arriva allo stato chiesto per la matrice) | `dbops.fn_pgtap_crea_preventivo('<etichetta>'[, '<stato>'])` |
| **una testata che cambia stato dopo aver preso le righe** (ogni testata di vendita con una matrice dei passaggi: nasce nello stato iniziale, il test scrive le righe, poi lo stato per le transizioni vere — fuori bozza le righe non si scrivono) | `dbops.fn_pgtap_porta_a_stato('vendite.<testata>', <id>, '<stato>')` (anche `vendite.fatturazione_lotti`, se vuoto) |
| **una commessa** del mondo, aperta dalla madre del dominio (codice ed emittente dal dominio, competenza nel mese corrente) — nello stato chiesto, sul cliente di un'altra fixture; fuori bozza con l'attività approvata che l'uscita pretende; a richiesta con la **sorgente ROOT** | `dbops.fn_pgtap_crea_commessa('<etichetta>'[, '<stato>'[, <ba_id>[, <con_attivita>[, <con_sorgente_root>]]]])` |
| **un lotto di fatturazione** dell'azienda, nato dalla madre e portato allo stato chiesto (vuoto); a richiesta l'esito che trattiene un gruppo | `dbops.fn_pgtap_crea_lotto('<etichetta>'[, '<stato>'[, <ba_id>[, <tipo_doc_id>[, <mese>[, '<gruppo_key>'[, <del_cliente>]]]]]])` |
| **un'attività** approvata su una commessa costruita, scritta dalla madre (articolo costruito, pronta per l'emissione; articolo e listino del chiamante se li dà); con la **sorgente** l'attività che la push di una riga avrebbe scritto — la chiave la compone `script.fn_segment_key`, mai a mano — con quantità, stati e periodo dichiarati | `dbops.fn_pgtap_crea_commessa_attivita(<commessa_id>[, …], p_sorgente_codice => …, p_sorgente_uid => …, p_sorgente_riga_id => …, p_stato_emissione => …)` (per nome) |
| una **filiale bancaria** su cui agganciare un conto | `dbops.fn_pgtap_crea_filiale_bancaria('<etichetta>')` |
| il **gestore** dell'installazione (lo prende se c'è, lo costruisce se non c'è) | `dbops.fn_pgtap_crea_gestore('<etichetta>')` |
| un'azienda con il suo operatore (e identità) | `dbops.fn_pgtap_crea_emittente_operatore()` |
| un **operatore umano** — persona fisica, risorsa umana, identità — **senza azienda**, volendo super admin | `dbops.fn_pgtap_crea_operatore_umano('<etichetta>'[, p_super_admin := true])` |
| un **punto di prelievo** nuovo, su un indirizzo suo | `dbops.fn_pgtap_crea_pdp(['<utility>'])` |
| un **listino** con una versione ATTIVA, dell'azienda di chi agisce (contesto aperto prima) | `dbops.fn_pgtap_crea_listino(<utility_id>[, '<etichetta>'[, valido_dal[, valido_al]]])` |
| l'utente tecnico di un processo, a roster | `dbops.fn_pgtap_crea_roster_processo('<processo>')` |
| un cliente fatturabile (soggetto → CL → istanza → BA) | `dbops.fn_pgtap_crea_cliente_ba('<etichetta>'[, utility, emittente_sr])` |
| un soggetto con un ruolo e basta (CL, FO, BANK_B…) | `dbops.fn_pgtap_crea_soggetto_pg(...)` + `fn_pgtap_crea_soggetto_ruolo(..., 'CL')` |
| un **super admin** (senza azienda, come in produzione) | `dbops.fn_pgtap_crea_operatore_umano('<etichetta>', p_super_admin := true)` — sotto, §«Un super admin non ha un'azienda» |

⛔ **Ordine obbligato: prima il mondo, poi `fn_pgtap_set_contesto_operatore(<auth_user_id>)`.**
Con un operatore già in sessione il legame BA → emittente lo scrive **anche**
il trigger `z90` del billing account, e i due si scontrano su
`uq_emittenti_fiscali_ba`. Da owner si costruisce tutto prima e si lega il BA
con il terzo parametro; come `zeroerp_app` si apre il contesto e si chiama
`fn_pgtap_crea_cliente_ba` **senza** terzo parametro (dalla rev `20260912-38` il
legame lo lascia al trigger, verso l'emittente di chi agisce).

⭐ **La riga di contesto del template lo fa da sola, se serve.** Da
`20260920-01`, `script.fn_pgtap_set_contesto_operatore()` senza argomento —
quando non trova nessun operatore, cioè su un database vuoto — costruisce
azienda + operatore e apre il contesto su quello. Un file che vuole solo «un
operatore su un emittente» non ha altro da fare. Il builder si chiama a mano
quando servono gli **id** del mondo (l'emittente per un registro, il soggetto
ruolo, **due** aziende) o quando il soggetto del test è l'operatore umano.

⭐ **E la composizione ha un helper suo** (rev `20260922-17`): quando a un file
servono *insieme* l'azienda, il contesto e un cliente fatturabile — il caso di
gran lunga più frequente — `dbops.fn_pgtap_crea_mondo_cliente('<etichetta>')` li
costruisce nell'ordine giusto e ne torna tutte le chiavi in una riga. Senza
contesto costruisce e lo apre; **con un contesto già aperto riusa l'azienda di
chi agisce**, e non è un risparmio: un'azienda nuova lascerebbe il cliente legato
a quella vecchia, invisibile sotto RLS. ⛔ Non comprende registro, articolo né i
cataloghi di `80_data`: entra ciò che ha una **trappola d'ordine**, non ciò che
serve spesso.

⭐ **Una FATTURA e' una catena, non un INSERT** (rev `20260923-04`): il cliente
va legato all'azienda di chi agisce, la coppia (emittente, utility) va
configurata, il registro dipende da quell'azienda e la valuta si risolve lungo
la catena «cliente → azienda → gestore». `dbops.fn_pgtap_crea_fattura()` li mette
tutti e quattro; lo **stato si sceglie alla nascita** (la testata ha un guard di
transizione), e il **terzo parametro** e' il billing account di una fattura gia'
costruita, per la seconda dello stesso cliente. ⛔ Righe, scadenze, contabili e
movimenti restano al test: sono il suo caso.

⚠️ **Un super admin non ha un'azienda.** È multi-emittente per modello, e non è
un dettaglio: un billing account senza legame ricade sull'emittente di **chi
agisce** prima che sul gestore globale, quindi un super admin costruito come
utente tecnico (che un'azienda ce l'ha sempre) sposta il ripiego. E toglierla
dopo non si può. Si costruisce con `fn_pgtap_crea_operatore_umano(…,
p_super_admin := true)`, che passa dalla madre di produzione e nasce senza.
Un super admin **lavora** su un'azienda solo se la **sceglie**, come in alto:
`app.current_emittente_id`. Con l'azienda scelta, il mondo e i builder che lo
compongono (fattura, ordine, contratto…) costruiscono su quella, come il trigger
che lega il cliente; senza, il mondo lo rifiuta. È il modo in cui lavorano gli
smoke Python con l'utente `dev.smoke`.

⛔ **Ciò che un builder scrive si legge in un'istruzione SEPARATA.** Un `JOIN`
sulla tabella che il builder ha appena scritto, o una funzione `STABLE`, nella
**stessa istruzione** della chiamata vede la snapshot di prima: la temp table
nasce vuota, o il super admin risulta non esserlo.

⚠️ E `anagrafiche.bank_branches` e' **dato di macchina**, non seed: da zero e'
vuota, e un conto bancario ci sbatte sul NOT NULL. La filiale si costruisce con
`dbops.fn_pgtap_crea_filiale_bancaria()`.

⚠️ Gli helper escono con i vincoli **IMMEDIATE**: un file che li vuole
differiti fino a un punto suo (`pgtap-differiti`, «fattura + atto») li riapre
con `SET CONSTRAINTS ALL DEFERRED` subito dopo.

⛔ **E la riga di contesto, quando costruisce, è un helper.** Senza argomento su
un database vuoto chiama il builder, e ne eredita il contratto: esce IMMEDIATE.
Con argomento, o dove un operatore esiste (dbdev), **non tocca i vincoli** — e
non può fare altrimenti: il modo di una transazione non si legge né si
ripristina, e un setter di contesto che chiudesse i vincoli pendenti li
chiuderebbe *nei panni del nuovo attore* (la trappola RLS di
`rls/test-rls-listini-ef-whitelist-write`). Quindi il contratto è asimmetrico
per costruzione, e la regola per i file è una sola: **dopo la riga di contesto
non si conta sulla finestra differita di default** — se la si vuole, si
dichiara con `SET CONSTRAINTS ALL DEFERRED`. È ciò che il primo file della suite
(`anagrafiche/create-cliente`) non faceva: verde su dev, rosso in CI il
2026-09-21, e da solo mai — il secondo file committa un operatore in autocommit
e da lì in poi nessuno percorre più il ramo che costruisce.

⚠️ E i **rami `skip` spariscono**: con il mondo costruito la precondizione c'è
sempre, e un `CASE WHEN EXISTS(...) THEN ok(...) ELSE skip(...)` diventa un
`ok(...)`. Un test che *può* saltare, su un database vuoto salta.

### ⚠️ «Libera» vuol dire «libera ADESSO»

`dbops.fn_pgtap_piva_libera()` e `dbops.fn_pgtap_cf_libero()` rispondono **la prima
non ancora usata in questo istante**. Non sono generatori: finché nessuno scrive
quel soggetto, la chiamata successiva risponde **lo stesso numero** — anche in
un'altra istruzione (misurato il 2026-09-23).

⇒ Due conseguenze, e sono state due rossi veri:

1. chiederne **due in una volta** per due soggetti diversi dà due volte lo stesso
   valore, e il secondo INSERT muore su `uq_soggetto_idstato_id_fiscale_univoco`;
2. precalcolarla **prima** di costruire il mondo è peggio: la riga di contesto,
   quando costruisce azienda e operatore, prende proprio quella — e il soggetto del
   test collide con il soggetto dell'azienda.

⭐ La regola è una: **la si chiede quando serve, dopo che il mondo esiste**, e una
per volta. In un file a più casi, ogni caso chiede la sua.

### `LIMIT 1` senza `ORDER BY` non verifica, scommette

Quale riga esca dipende dal piano del planner, che cambia coi dati: il test
passa a giorni alterni e nessuno capisce perché.

1. **`ORDER BY` su una chiave stabile** — rende la scelta ripetibile;
2. **la condizione che rende il caso significativo** — spesso una guardia a
   monte (idempotenza, stato) rende irraggiungibile proprio il ramo da provare;
3. **scegli una volta sola.** Se ti servono due valori della stessa riga (id e
   aliquota, id e codice), una CTE o una temp table — due sotto-select
   indipendenti possono pescare righe diverse. È successo: `iva_id` e
   `iva_aliquota` uscivano da due estrazioni su **sette** candidati, e il test
   avrebbe calcolato i totali con l'aliquota sbagliata;
4. **se dipende da chi agisce, derivalo dal contesto** invece di pescarlo.

Lente per censire: `python3 scripts/censimento_limit1.py`. ⚠️ È una lente e non
un cancello: metà delle occorrenze sono su temp table del test stesso, dove il
`LIMIT` non sceglie niente. Un cancello con quel tasso di falsi positivi si
impara a disattivare.

### «Oggi» è il giorno dell'azienda, non quello della sessione

Il codice legge il giorno dal fuso dell'azienda (`script.fn_data_operativa()`), e
il test deve costruire lo **stesso** giorno:

| serve | si scrive |
| --- | --- |
| oggi | `script.fn_data_operativa()` |
| il giorno di un istante (`data_mov`, `data_insert`, …) | `script.fn_giorno_operativo(<istante>)` |
| l'istante in cui comincia un giorno | `script.fn_inizio_giorno_operativo(<data>)` |

⛔ `CURRENT_DATE`, `LOCALTIMESTAMP`, `now()::date` e un `::date` su un istante
danno il giorno della **sessione**, e la sessione dei test gira apposta in un
fuso il cui giorno è **diverso** da quello dell'azienda: `scripts/testpgtap.sh`
sceglie, file per file, fra +14 e −11 quello che adesso cade in un altro giorno.
Così un test che confonde i due giorni è rosso a ogni ora, non solo di notte.
La prima metà della regola la presidia `scripts/guardrail_pgtap_preambolo.py`;
un'eccezione si dichiara con `-- pgtap-oggi: escluso — <perché>`.

⭐ Un rosso da riprodurre nel fuso dell'azienda: `PGTZ=Europe/Rome
scripts/testpgtap.sh …` (il runner rispetta un `PGTZ` già impostato).

### Le chiavi generate devono essere larghe

Un suffisso di **due caratteri esadecimali** sono 256 valori. Con 64 righe
residue in tabella la collisione arriva al **25% delle corse** — ed è così che
un test è oscillato «fra 6 e 0 asserzioni» per mesi senza che nessuno capisse.
Usa il suffisso intero: la colonna quasi sempre lo regge.

### Padre e figlio in due istruzioni, non in una CTE

Le CTE che scrivono condividono **la stessa snapshot**. Una policy che risolve
il perimetro dal padre (`fn_scope_*_via_fattura`) non lo trova e nega
fail-closed. In `LANGUAGE sql` non si può separare: serve `plpgsql`, due
`INSERT` e una variabile in mezzo.

⚠️ L'errore che ottieni parla di RLS sulla tabella **figlia**, e sembra un
problema di permessi. Non lo è.

## Le asserzioni

### Un errore si asserisce, non si spera

`throws_ok(sql, NULL, NULL, 'desc')` verifica **che** sollevi, non **cosa**:
accetta anche il crash del guard che volevi verificare, o un `permesso negato`
che non c'entra niente.

```sql
throws_ok  (sql, 'P0001', NULL, 'desc')   -- errore di dominio (fn_log_and_raise_error)
throws_ok  (sql, '23514', NULL, 'desc')   -- CHECK   ·  '23505' unique  ·  '23503' FK
throws_like(sql, '%frase stabile%', 'desc')
```

⚠️ **`P0001` dice «è un errore di dominio», non QUALE**: tutti i codici passano
da `fn_log_and_raise_error`, che usa quello SQLSTATE per tutti. Per distinguere
fra due codici il discriminante è la **frase**.

⚠️ **E il pattern non deve attraversare un segnaposto.** Il messaggio
`Riga DDT %s non trovata` si matcha con `'%Riga DDT %non trovata%'`, mai con la
frase intera: l'id interpolato la spezza in mezzo.

> **Quanto costa non farlo, misurato.** Su 137 `throws_ok` senza discriminante,
> una sonda ha eseguito lo statement e letto lo SQLSTATE vero: **tre test
> VERDI** collaudavano una cosa diversa da quella dichiarata — un guard che
> **esplodeva** in `format()` invece di parlare (`22023`), un «errore su colonna
> generata» spacciato per guard (`428C9`), una violazione di FK spacciata per
> guard (`23503`).

### I trigger `BEFORE ROW` girano prima dei `CHECK`

Un'asserzione che crede di collaudare un `CHECK` viene spesso intercettata dal
guard e non lo raggiunge mai. Per arrivare davvero al `CHECK` serve un caso che
il guard **lascia passare**.

### Quando togli un `LIMIT 1`, chiediti cosa vorrebbe dire l'asserzione

Spesso la forma giusta è **più severa**, non solo più stabile:

* `SELECT DISTINCT` su un valore di testata **esplode** se le righe dello stesso
  documento ne portano di diversi — asserisce anche l'invarianza;
* `bool_and(...)` su tutte le righe dice «**nessuno** è incoerente», invece di
  «uno a caso va bene».

## Quando il test non può girare come l'applicazione

Prima di tutto: **è quasi sempre un difetto della fixture.** Il marcatore serve
a un caso solo.

> ⭐ **il SOGGETTO del test non è raggiungibile dall'applicazione.**

```sql
-- pgtap-runner: owner
-- pgtap-runner-motivo: <perché, in chiaro>
```

Il motivo è **obbligatorio**: senza, il runner esce con codice 4. Le tre forme
ammesse e — soprattutto — **l'elenco di cosa il criterio esclude** stanno
nell'intestazione di `scripts/testpgtap.sh`.

**In una riga: se l'applicazione quella cosa la fa, il marcatore è sbagliato.**

## Prima di dire «fatto»

```bash
scripts/testpgtap.sh db/<schema>/test-<cosa>.sql   # il tuo test
scripts/pgtap-baseline.sh <schema>                 # nessuna regressione nello schema
python3 scripts/guardrail_pgtap_preambolo.py       # le invarianti di preambolo
```

⚠️ **La baseline è un registro di debito, non una lista di eccezioni**: deve
calare. Un file che fallisce nella *fixture* non esegue **nessuna** asserzione —
la sua copertura vale **zero**, non «parziale», ed è un'area che *sembra*
coperta.

⚠️ **Un test che diventa verde va spiegato prima di essere creduto.** Nel
cantiere è successo tre volte. E vale al contrario: «6 o 0 asserzioni» sembrava
un'oscillazione fra verde e rosso, ed erano **due difetti in fila** con il file
sempre rosso.

## Girano in CI?

**Sì, ma non sempre.** La suite costa ~7 minuti:

| quando | gira? |
|---|---|
| PR verso `main` | ✅ sempre — è il cancello prima dell'integrazione |
| push su `Tito-dev` che tocca `db/` o `scripts/` | ✅ |
| push su `Tito-dev` che **non** tocca il DB | ❌ |
| PR verso `Tito-dev` | ❌ — basta il cancello statico sul preambolo |

Il perché è misurato: sui 30 giorni al 2026-08-07 `Tito-dev` ha avuto **656
commit**, di cui **155** toccano `db/` e **107 solo `backend/`**. È anche il ramo
di scambio fra backend e DB, quindi buona parte del traffico non riguarda il
database — e lì la suite girerebbe per niente. Farla solo verso `main`, invece,
la farebbe arrivare troppo tardi: il rosso spunterebbe mescolato a giorni di
lavoro altrui, e bisecarlo costa più dei minuti risparmiati.

⚠️ **In CI la baseline è un'altra**: `db/pgtap/baseline-rossi-ci.tsv`. Il
database della CI è **ricostruito da zero**, quello di sviluppo ha dati veri: i
test che dipendono da dati preesistenti falliscono là e non qui. Confrontare le
due popolazioni produrrebbe decine di finte regressioni — lo stesso difetto di
metro disomogeneo da cui è nato tutto.

Quindi: **un rosso in CI non è automaticamente un rosso da te, e viceversa.**
Prima di inseguirlo, guarda quale baseline lo conosce.

⭐ **E la baseline della CI si aggiorna DALLA CI** — `--update` su quel file
fuori da GitHub è un cancello (`exit 2`), perché la misura dello scratch non è
la sua: il 14-09 lo scratch dava 33 «verdi non registrati», la CI ne dichiarava
31, e i due elenchi differivano di quattro file. La CI però non committa: stampa
l'elenco RIENTRATI, e per due giorni nessuno l'ha trascritto. Da quel giorno:

```bash
scripts/pgtap-baseline-ci-rientrati.sh            # ultima corsa utile su Tito-dev
scripts/pgtap-baseline-ci-rientrati.sh <run-id>   # una corsa precisa
```

legge il log della corsa di GitHub (`gh`), toglie da `baseline-rossi-ci.tsv`
**quelle** righe e stampa le regressioni senza aggiungerle — un rosso nuovo entra
nel registro solo per decisione. ⚠️ GitHub ritira i log dopo pochi giorni
(`410`): l'elenco si prende dalla corsa mentre c'è.

⚠️ **E un `ERRORE_FIXTURE` in CI si legge, non si indovina.** La baseline stampa
solo l'etichetta: il messaggio vero sta nel **log del container Postgres**, che
GitHub scarica per intero nel passo «Stop containers» del job
(`gh run view <run> --job <job> --log`, poi cercare `ERROR:` con lo `STATEMENT:`
che segue). Il 2026-09-13 quel log ha detto in una riga ciò che due giorni di
confronto con lo scratch non dicevano: **47 × `permission denied for table
auth_user`**, cioè 23 file morti per un privilegio che esisteva solo su dev —
e lo scratch era verde perché **copiava** quel privilegio insieme allo schema
`django` ([linee-guida-sql §11.9](/linee-guida-sql)). Lo scratch è un metro
finché riceve la configurazione dalla stessa sede della CI; quando la copia da
dev, misura dev.

## Perché una guida non basta

Chi ha scritto queste regole ne ha violata una **poche ore dopo averla
scritta** — «un requisito che vive in due posti si dimentica in uno dei due» —
duplicando il default del runner in due script.

Per questo l'ordine di efficacia è: **template → cancello → guida**, e questa
pagina è l'ultimo dei tre. Serve per ciò che non si automatizza: *da chi difende
questo guard? cosa vorrebbe dire davvero questa asserzione?* Il resto lo devono
fare il template che copi e il cancello che ti ferma.

---
{% include-markdown "signature-core.md" %}
