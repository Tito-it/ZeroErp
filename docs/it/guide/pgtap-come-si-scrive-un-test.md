# Come si scrive un test pgTAP

> **A chi serve**: chiunque aggiunga o modifichi un test in `db/pgtap/`.
> **Da dove viene**: tre giorni di lavoro nell'agosto 2026, e ogni regola qui
> sotto è costata un difetto vero. Storia e misure:
> `docs/it/dev/work-in-progress/brief-db-pgtap-runner-rls-baseline.md`.

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

**Sì, ma solo su `Tito-dev` e su `main`** — la suite costa ~7 minuti, e su ogni
PR di lavoro sarebbe sproporzionata. Sui rami di lavoro gira solo il cancello
statico sul preambolo, che invece costa un secondo.

⚠️ **In CI la baseline è un'altra**: `db/pgtap/baseline-rossi-ci.tsv`. Il
database della CI è **ricostruito da zero**, quello di sviluppo ha dati veri: i
test che dipendono da dati preesistenti falliscono là e non qui. Confrontare le
due popolazioni produrrebbe decine di finte regressioni — lo stesso difetto di
metro disomogeneo da cui è nato tutto.

Quindi: **un rosso in CI non è automaticamente un rosso da te, e viceversa.**
Prima di inseguirlo, guarda quale baseline lo conosce.

## Perché una guida non basta

Chi ha scritto queste regole ne ha violata una **poche ore dopo averla
scritta** — «un requisito che vive in due posti si dimentica in uno dei due» —
duplicando il default del runner in due script.

Per questo l'ordine di efficacia è: **template → cancello → guida**, e questa
pagina è l'ultimo dei tre. Serve per ciò che non si automatizza: *da chi difende
questo guard? cosa vorrebbe dire davvero questa asserzione?* Il resto lo devono
fare il template che copi e il cancello che ti ferma.
