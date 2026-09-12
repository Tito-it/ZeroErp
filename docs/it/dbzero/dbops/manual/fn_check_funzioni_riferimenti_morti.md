## 📘 Documentazione Concettuale – Funzione `dbops.fn_check_funzioni_riferimenti_morti()`

> 👀 **Vedi anche**
>
Approfondimento tabelle:
> • [dbops.riferimenti_morti_esenzioni](/dbzero/dbops/tabelle/riferimenti_morti_esenzioni)
>
Approfondimento viste:
> • [dbops.vw_riferimenti_morti_da_sanare](/dbzero/dbops/views/vw_riferimenti_morti_da_sanare)
> • [dbops.vw_riferimenti_morti_rientrati](/dbzero/dbops/views/vw_riferimenti_morti_rientrati)

---
### 🎯 Scopo Principale

(rev 2026-08-21)

Trova i **riferimenti morti** nelle funzioni PL/pgSQL: colonne rinominate o eliminate, tabelle
che non esistono più, campi citati da un corpo che non compilerebbe mai.

Il problema che risolve è specifico di PL/pgSQL: il corpo di una funzione **non viene
validato alla creazione**. Una `CREATE OR REPLACE FUNCTION` che nomina una colonna inesistente
riesce senza un fiato, e il difetto si manifesta solo quando quel ramo viene percorso — spesso
il ramo d'errore, cioè esattamente quando servirebbe funzionare.

Si appoggia a `plpgsql_check_function`, e ne interpreta l'output.

---

### ⭐ Le trigger function si validano contro **ogni tabella** su cui sono agganciate

È il punto meno ovvio. `NEW` e `OLD` non hanno un tipo finché non si sa su quale tabella il
trigger è montato: la stessa trigger function agganciata a due tabelle va quindi controllata
**due volte**, una per tabella.

Da qui la classe **`ORFANA`**: una trigger function agganciata a **zero** tabelle non è
validabile affatto. Non è un riferimento morto — è codice che nessuno può verificare, ed è
segnalato come tale.

---

### ⚠️ Le classi sono SETTE, e tre chiedono attenzione

> ⚠️ **Corretto il 2026-09-12**: questa sezione diceva «due su **cinque**» ed elencava cinque
> classi. Ne mancavano **due** — `FP_VARIADIC` (dal 2026-08-05) e `NON_MISURATO` (dal
> 2026-09-10) — e la seconda è proprio quella che decide se la misura vale qualcosa.

| Classe | Significato | Nelle viste a valle |
|---|---|---|
| `REALE` | riferimento morto vero, da sanare | ✅ sì |
| `ORFANA` | trigger function non agganciata: non validabile | ✅ sì |
| `NON_MISURATO` | ⛔ **non si è potuto controllare**: `plpgsql_check` ha sollevato invece di rispondere | ✅ sì |
| `FP_TRANSITION_TABLE` | falso positivo — tabelle di transizione (`REFERENCING`) | no |
| `FP_RAMO_ALTRA_TABELLA` | falso positivo — ramo che vale per un'altra tabella agganciata | no |
| `FP_SQL_DINAMICO` | falso positivo — `EXECUTE` con SQL costruito | no |
| `FP_VARIADIC` | falso positivo — chiamata `VARIADIC` | no |

⛔ **`NON_MISURATO` non è un difetto e non è un falso positivo: è l'assenza di una misura**, e
va trattata **come un rosso**. È la differenza fra «non ho trovato difetti» e «non ho potuto
guardare», che è la cosa più pericolosa che un presidio possa confondere — e che questa
funzione ha confuso per davvero: fino al `20260910-36` quella forma cadeva nell'`ELSE` e
usciva come `REALE`.
⭐ Ed è **visibile nelle viste a valle di proposito**: filtrarla le farebbe tornare «vuote»,
cioè direbbero «tutto a posto» proprio quando nessuno ha guardato.

⭐ **I falsi positivi sono classificati, non nascosti.** Un filtro li avrebbe fatti sparire
anche quando smettono di essere falsi positivi; una classe li tiene visibili e dice *perché*
si ignorano. Le due viste a valle filtrano su `REALE`/`ORFANA`, ma la funzione restituisce
tutto.

Misura al 2026-08-21: 14 `FP_RAMO_ALTRA_TABELLA`, 5 `FP_TRANSITION_TABLE`, 1 `FP_SQL_DINAMICO`,
**1 `ORFANA`**, zero `REALE`.
Rimisurata il 2026-09-12: 16 · 5 · 1 · **1 `ORFANA`** (coperta dal registro), zero `REALE` —
e da entrambi i percorsi di lettura, che prima non era vero (vedi il `search_path` qui sotto).

---

### Perimetro

Solo funzioni `plpgsql`, esclusi `pg_catalog`, `information_schema`, gli schemi `pg_*` e
**tutto ciò che appartiene a un'estensione** (PostGIS, topology, pgAgent): non è codice
mantenuto qui, e segnalarlo sarebbe rumore permanente.

---

### ⛔ Il `search_path` è PINNATO, e non è una questione di stile

(rev 2026-09-12)

La funzione dichiara il proprio `search_path`: **`pg_catalog, public, pg_temp`**. Senza quel
pin il suo verdetto **cambia a seconda di chi la chiama**, e cambia in silenzio.

Il `search_path` governa **due** cose, e la seconda è quella che sfugge:

| cosa risolve | che succede senza `public` |
|---|---|
| la chiamata a `plpgsql_check_function` (l'estensione sta in `public`) | non si risolve: `42883`, il gestore `EXCEPTION` scrive `error:CHECK-KO:` e **ogni** funzione esce `NON_MISURATO` |
| i riferimenti **dentro le funzioni che si compilano** | `unaccent`, `dblink`, il tipo `geometry` sono nominati senza schema, come è normale: quattro funzioni **sane** escono `REALE` |

⭐ **Perché proprio `public`**: è nel `search_path` reale dell'applicazione
(`zeroerp_app`: `django, public, config, dbops, script, anagrafiche`). *Una misura di
riferimenti morti è fedele solo se compila nel contesto in cui quelle funzioni girano
davvero.*

🔴 **Il caso che l'ha insegnato** (2026-09-12): la funzione girava senza pin dentro
`dbops.fn_conta_presidio`, che è `SECURITY DEFINER` con `search_path = pg_catalog, pg_temp`,
e ne ereditava il path. Il digest dei presidi riferiva **784** «riferimenti morti» mentre la
stessa vista, letta diretta, rispondeva **0**. Storia:
`brief-db-un-destinatario-per-i-presidi §13`.

⚠️ **Chi rifà questa funzione tenga la clausola `SET`**: un `CREATE OR REPLACE` che la
dimentica **non fallisce** — azzera il pin e riporta il presidio a mentire. È la stessa
trappola di `security_invoker` che si azzera su `CREATE OR REPLACE VIEW`. L'unica cosa che lo
prende è il **test 6** del pgTAP, che conta attraverso `fn_conta_presidio`.

---

### ⚠️ È costosa, e usa una temp table condivisa

Gira `plpgsql_check_function` su ogni funzione del database, moltiplicata per le tabelle
agganciate: **non è una query da mettere in un percorso frequente**. Va bene in un guardrail o
in un test, non in una vista consumata da un endpoint.

Internamente usa una temp table `tmp_raw` (`ON COMMIT DROP`, creata con `IF NOT EXISTS` e
svuotata in testa). Chiamandola due volte nella stessa sessione compare la notifica «la
relazione tmp_raw esiste già»: è innocua.

⭐ **Comporre più chiamate nella stessa query è sicuro** — verificato il 2026-08-21: due
`SELECT count(*) FROM dbops.fn_check_funzioni_riferimenti_morti()` nella stessa istruzione
restituiscono entrambe 21 righe. PostgreSQL materializza la set-returning function prima di
usarne il risultato, quindi le chiamate non si pestano sullo stato d'appoggio nonostante il
`DELETE` in testa. Vale anche per le due viste che la richiamano.

⚠️ Resta però vero il costo: comporle significa **eseguire il controllo due volte**.

🔴 **Ma una chiamata da una `SECURITY DEFINER` e una dal ruolo corrente NON convivono**
(trovato il 2026-09-12 scrivendo il test 6 del pgTAP). `tmp_raw` appartiene al ruolo che l'ha
creata, e il `DELETE FROM tmp_raw` in testa alla funzione **non attraversa i ruoli**: chi
chiama per secondo prende `42501 permesso negato`.

⇒ Dentro un test che fa **entrambe** le letture — la scansione diretta e il conteggio via
`dbops.fn_conta_presidio`, che gira come proprietario — ci vuole un
`DROP TABLE IF EXISTS tmp_raw;` fra le due, come istruzione sua.
⛔ **E non è un fastidio cosmetico**: in un pgTAP quel `42501` è un **ERRORE**, che ferma il
file e lascia *tutti* i test senza girare — cioè un `Bad plan`, non un rosso che si legge.

---

### Consumatori

`db/pgtap/dbops/test-riferimenti-morti-v1.sql` e
`scripts/sql/guardrail_riferimenti_morti.sql`.

⚠️ Il guardrail gira **dopo** `manage.py migrate`, non prima: le funzioni devono essere già
nel database perché ci sia qualcosa da controllare.

🔵 **E dal 2026-09-10 c'è un terzo consumatore, che nessuno dei due elenchi nominava**: il
**digest dei presidi**. Non la chiama direttamente — chiede
`dbops.fn_conta_presidio('dbops.vw_riferimenti_morti_da_sanare')`, che passa dalle due viste —
ma è il consumatore la cui lettura arriva **a una persona**, ogni settimana.
⭐ Vale saperlo per due ragioni: è il percorso su cui il difetto del `search_path` si è
manifestato (una lettura `SECURITY DEFINER`, non una diretta), e il costo della scansione
diventa il costo di quel giro — è la ragione per cui quella riga di catalogo è
`cadenza = SETTIMANALE` e non giornaliera.

⚠️ **Il guardrail e la lente danno un verdetto che dipende dal RUOLO** che li lancia, e va
riprodotto col ruolo giusto: `dbops.fn_get_pgagent_job_stato` legge `pgagent.*`, che
`zeroerp_app` non vede (`42501`) e che in CI non esiste (`42P01`), mentre dal proprietario
compila senza difetti — quindi la sua voce di registro risulta «rientrata». Si lancia come
`zeroerp_app`, che è il ruolo che il difetto lo subisce e quello che la CI simula.

---

{% include-markdown "signature-core.md" %}
