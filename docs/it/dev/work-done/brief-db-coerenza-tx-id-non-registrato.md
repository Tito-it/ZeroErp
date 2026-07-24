# Brief DB — Coerenza tx_id: mai pubblicare un id non registrato, e `W_` che avverte davvero

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-22 · **Owner**: Tid · **Stato**: ✅ **CHIUSO (2026-07-22)** — tutti e 9 gli
> step fatti, pgTAP 7/7, **CI verde senza bypass**.
>
> **Esito.** Il difetto bloccava ogni ambiente **senza** canale di log (CI
> `no provision`, macchine di sviluppo); in produzione, dove il canale è
> configurato, non si manifestava. Ora la validazione del tx_id è attiva anche
> nella CI senza provisioning, invece di essere disattivata: quello step esercita
> il caso peggiore anziché aggirarlo.
>
> ⚠️ **Se un domani quello step tornasse a fallire con `W_TXID_NOT_REGISTERED`, la
> risposta NON è rimettere `myapp.bypass_tx_id_check`**: significa che qualcosa ha
> ricominciato a pubblicare nella GUC un tx_id non registrato. Vedi §3.
>
> **Perimetro**: SOLO DB + guida + un ritocco CI in coda. Due funzioni `dbops`, una
> nota nel registro, la guida `tx_id_implementation_guide.md`, un pgTAP nuovo.
> Nessuna modifica BE/FE.
> **Contesto**: non siamo in produzione → si corregge il comportamento, non si
> costruiscono compatibilità.
> **Origine**: fallimento CI dello step `Liquibase update (standard, no provision)`
> su `80_data/20260720-10-seed-dbops-coda-lavori-tipi-fatturazione-giro`, con
> `W_TXID_NOT_REGISTERED` sollevato dal trigger di audit.

---

## 1. Il problema, in due frasi

Ogni scrittura tracciata porta un **numero di transazione** (`tx_id`) e c'è un
**registro** dei numeri validi (`dbops.transaction_ids`). Un controllo in
`dbops.trgfn_tx_id_managed` verifica che il numero sia nel registro.

Quando il canale verso il registro non è disponibile,
`dbops.fn_get_or_create_session_tx_id` **inventa un numero e non lo scrive da
nessuna parte**, ma lo pubblica nella GUC di sessione `dbops.tx_id`. Il controllo
poi lo cerca nel registro, non lo trova, e **blocca**. Poiché la GUC è di
sessione e Liquibase usa una sola connessione, da quel momento **ogni** scrittura
tracciata della run fallisce.

## 2. Non è un disaccordo di disegno: sono due bug contro un'intenzione chiara

La guida `tx_id_implementation_guide.md` descrive un sistema coerente. È il codice
che se ne discosta, in due punti indipendenti.

**Bug 1 — si pubblica un id che non si è registrato.**
`fn_get_or_create_session_tx_id` ha tre rami di ripiego (canale non configurato,
dblink che risponde `NULL`, dblink che solleva). Tutti e tre fanno
`v_tx_id := uuidv7()` seguito da `set_config('dbops.tx_id', …, false)`: generano un
id **non registrato** e lo pubblicano **a livello di sessione** (terzo parametro
`false` = non-local, sopravvive alla transazione). Il ramo dblink invece chiama
`dbops.fn_generate_tx_id`, che **registra**: quel percorso è coerente, i ripieghi no.

**Bug 2 — il controllo blocca dove doveva avvertire.**
La guida (§202) dice: *«Se non trovato: **logga WARNING** `W_TXID_NOT_REGISTERED` e
**assegna `uuid_nil()`**»*. Il codice però usa `script.fn_log_and_raise_error`, che
**solleva**. La prova è nel codice stesso: subito dopo la `PERFORM` c'è
`v_new_tx_id := script.uuid_nil();` — **una riga irraggiungibile**, che non ha altra
spiegazione se non che l'autore intendeva proseguire. È stato usato l'helper
sbagliato: serviva `script.fn_log_error_only`.

Da qui anche l'incoerenza di nome: il codice si chiama `W_` (warning) ma si comporta
da errore fatale. Non va rinominato — **va fatto comportare come si chiama**.

### Perché si vede solo ora, e solo in CI

`ci.yaml` esegue `ALTER ROLE zeroerp SET myapp.dblink_log_connection = …`, quindi il
percorso nominale funziona e i tx_id sono registrati davvero. `ci-validate.yaml`
non lo fa, per scelta: è il profilo che verifica l'applicabilità su un DB **non
provisionato**. Lì scatta il ripiego, e con esso la catena sopra. Lo step stava
facendo il suo mestiere: ha trovato che una migrazione dipende dal provisioning.

## 3. La regola che scioglie la tensione — ed è quella che il progetto aveva già

> **Non pubblicare mai un `tx_id` che non hai registrato.**

Non è una regola nuova: **era la disciplina della v1** (`migrations/50_dbops/20250707-15`),
persa nella riscrittura del 22-11-2025. Vedi §3.bis per l'archeologia.

| Situazione | Comportamento |
| --- | --- |
| Canale di log disponibile | Registra via dblink (transazione **autonoma**: sopravvive al rollback di quella di business) e pubblica, **con scope locale alla transazione** |
| Canale assente, spento, o dblink fallito | Ritorna la sentinella `script.uuid_nil()` e **non pubblica nulla** |

La finezza che rende il disegno chiuso: **la validazione del trigger scatta solo
sull'id pubblicato nella GUC**. Se si pubblicano solo id venuti dal registro, e nel
degrado non si pubblica affatto, l'invariante è vero **per costruzione** e il ramo
«non registrato» diventa irraggiungibile in condizioni normali.

Così `myapp.bypass_tx_id_check` torna a essere ciò che il nome promette — una deroga
per casi particolari — invece della stampella senza la quale non parte niente.

**Perché la sentinella e NON una registrazione locale.** Una prima stesura di questo
brief proponeva di registrare in locale il tx_id di ripiego. È la scelta sbagliata:
la guida stabilisce l'**immutabilità del registro** (`transaction_ids` non si
modifica né si cancella, c'è un trigger di protezione). Riempirlo di id generati in
CI e sulle macchine di sviluppo lo inquinerebbe in modo permanente. La v1 evitava il
problema semplicemente non registrando e non pubblicando nulla.

**Cosa si perde nel degrado.** Con la sentinella, in assenza di canale tutte le righe
condividono `uuid_nil`: si perde la correlazione per-transazione. È il prezzo
accettato dal disegno originale, ed è comunque meglio dell'alternativa: la proprietà
di autonomia — la ragione per cui esiste il dblink, che punta **allo stesso database**
(`log_db` di default è `current_database()`: non serve la remotezza, serve una
connessione separata che committa per conto suo) — **non è ottenibile da nessun
disegno** senza un secondo canale.

## 3.bis Archeologia (verificata 2026-07-22) — il controllo non è mai stato tolto

Sospetto legittimo da fugare prima di procedere: «forse il controllo era stato
allentato per un motivo». **No.** In tutte e quattro le versioni di
`trgfn_tx_id_managed` (`20250707-21`, `20250814-01`, `20251031-11`, `20251114-04`) il
ramo «Caso C» è identico, commento compreso: *«ID non registrato: log warning e
assegna nil»* seguito da `fn_log_and_raise_error` e dalla riga morta
`v_new_tx_id := script.uuid_nil();`. La discrepanza è nata con la prima versione ed è
stata ricopiata fedelmente quattro volte.

Ciò che invece **è** cambiato è `fn_get_or_create_session_tx_id`, riscritta il
22-11-2025. Tre regressioni rispetto alla v1:

| | v1 (`20250707-15`) | attuale (`20251122-11`) |
| --- | --- | --- |
| `PERFORM script.fn_ensure_logconn()` (rispetta `myapp.log_with_dblink`) | **sì** | **no**: legge la connstring a mano |
| Ripiego senza dblink | `script.uuid_nil()`, **senza `set_config`** | `uuidv7()` non registrato, **pubblicato** |
| Scope della GUC | `set_config(..., TRUE)` = **locale alla transazione** | `set_config(..., false)` = **di sessione** |

Il passaggio a `false` è discutibile di per sé: un identificativo *di transazione*
che sopravvive fra transazioni della stessa connessione contraddice il proprio nome.
Ed è l'ingrediente che trasforma una singola generazione fallita nel fallimento di
**tutta** la run Liquibase, che usa una connessione sola.

## 4. Gli interventi

### 4.1 `dbops.fn_get_or_create_session_tx_id` — ripristinare la disciplina v1

Tre modifiche, tutte con un precedente nella v1:

1. **Eliminare i tre `uuidv7()` nudi.** Ogni ramo di ripiego (canale non
   configurato, dblink `NULL`, dblink in errore) ritorna `script.uuid_nil()` **senza**
   `set_config`. Nessun id non registrato viene mai pubblicato.
2. **Ripristinare lo scope locale**: `set_config('dbops.tx_id', …, TRUE)`. Un
   identificativo di transazione non deve sopravvivere alla transazione. Da sola,
   questa riga impedisce l'avvelenamento della sessione.
3. **Ripristinare `PERFORM script.fn_ensure_logconn()`** in testa, così l'interruttore
   `myapp.log_with_dblink` torna a essere rispettato con la semantica canonica
   (spento o connstring assente → non si tenta il dblink; oggi lo si tenta e
   fallisce, inutilmente).

Non cambiano: firma, `SECURITY DEFINER`, il ramo dblink, il riuso del tx_id già in
sessione.

⚠️ **Conseguenza da mettere in conto**: con lo scope locale, ogni transazione genera
un tx_id nuovo (una riga in più in `transaction_ids` per transazione, dove il canale
è attivo). È il comportamento corretto e quello originale, ma è un cambio di volume
sul registro rispetto a oggi: va detto a chi lo monitora.

### 4.2 `dbops.trgfn_tx_id_managed` — avvertire, non bloccare

Nel ramo «id non registrato», sostituire `script.fn_log_and_raise_error` con
`script.fn_log_error_only`. La riga `v_new_tx_id := script.uuid_nil();` che segue
diventa finalmente raggiungibile ed è il comportamento che la guida descrive.

⚠️ **Verificare i test.** La modifica è nel verso permissivo (da «solleva» a
«prosegue»), quindi non può rompere test che oggi passano; poteva però invalidare
test scritti per attendersi il raise. **Verificato 2026-07-22: nessuno.** Zero
occorrenze di `W_TXID_NOT_REGISTERED` in `db/pgtap/` e in `backend/`. Lo step 3
dell'avanzamento è quindi già assolto.

### 4.3 Convenzione `E_` / `W_` — scritta e verificata

Decisione presa: **`E_` = errore bloccante** (`fn_log_and_raise_error`),
**`W_` = avvertimento non bloccante** (`fn_log_error_only`).

L'audit del CSV mostra che il costo di adottarla è nullo: **`W_TXID_NOT_REGISTERED`
(id 19) è l'unico codice `W_` dell'intero `messaggi_errore.csv`**, su 354 codici.
Dopo §4.2 rispetta la convenzione, quindi **non va rinominato**: il nome resta e
finalmente corrisponde al comportamento. Nessun altro codice da toccare.

La convenzione va scritta in `docs/it/linee-guida-sql.md` (o nella guida errori),
perché è la regola che ha ingannato chi ha diagnosticato questo problema.

### 4.4 ~~Distinguere gli id in modalità ridotta~~ — **ritirato**

Una prima stesura prevedeva di marcare in `session_info` gli id registrati
localmente. **Cade insieme alla registrazione locale** (§3): con la sentinella non
si scrive nulla nel registro, quindi non c'è nulla da marcare — ed è meglio così,
visto il vincolo di immutabilità di `transaction_ids`.

La modalità ridotta resta comunque riconoscibile: le righe scritte in quella
modalità portano `tx_id = uuid_nil`, che è un valore distinguibile a colpo d'occhio.

### 4.5 Aggiornare la guida

`docs/it/guide/tx_id_implementation_guide.md` descrive come funzionante un percorso
che non lo è: la «Catena di fallback» (§153-161) e il punto 5 di §357 dicono
*«uuidv7() locale (WARNING, non registrato)»* e *«il tx_id resta valido ma non è
registrato»*. Dopo §4.1 il ripiego **è** registrato: vanno riscritti entrambi, più
la tabella delle GUC se cambia la semantica di `myapp.log_with_dblink`.

### 4.6 CI — togliere il bypass (in coda, non prima)

`.github/workflows/ci-validate.yaml` ha oggi `-c myapp.bypass_tx_id_check=true` sui
due step Liquibase che girano come `zeroerp` (già committato). Con §4.1+§4.2 non
serve più: **va rimosso**, così quello step torna a esercitare davvero il controllo
invece di spegnerlo — oggi lo stiamo disattivando proprio nel profilo che dovrebbe
verificare il caso peggiore.

**Ordine obbligato**: il bypass si toglie **dopo** che §4.1 e §4.2 sono applicate e
verdi. Toglierlo prima rimette la CI rossa.

## 5. Verifiche attese

### 5.1 Funzionali (pgTAP nuovo, `db/pgtap/dbops/`)

1. Con `myapp.log_with_dblink=off`: `fn_get_or_create_session_tx_id()` ritorna
   `uuid_nil` e **non** imposta la GUC `dbops.tx_id` (§4.1 punto 1).
2. Stesso caso: un `INSERT` su tabella tracciata **riesce** e scrive
   `tx_id = uuid_nil`. È il test che riproduce il fallimento CI d'origine.
3. Con canale attivo: la GUC impostata **sparisce a fine transazione** (scope
   locale, §4.1 punto 2) e l'id ritornato **esiste** in `dbops.transaction_ids`.
4. Con la GUC forzata a mano a un id **non** registrato (simulazione della sessione
   avvelenata): un `INSERT` su tabella tracciata **non solleva** e assegna
   `uuid_nil()` (§4.2).
5. Non-regressione: con bypass attivo il comportamento resta quello di oggi.

### 5.2 Di integrazione

- ✅ La CI `ci-validate` passa **senza** `bypass_tx_id_check` (§4.6) — verificato 2026-07-22.
- ✅ `ci.yaml` (con canale configurato) resta verde: il percorso dblink non è toccato.

## 6. Avanzamento

| # | Step | Stato |
| --- | --- | --- |
| 1 | `fn_get_or_create_session_tx_id`: ripristino disciplina v1 — niente `uuidv7` nudo, scope `TRUE`, `fn_ensure_logconn` (§4.1) | ✅ `20260722-10` |
| 2 | `trgfn_tx_id_managed`: `fn_log_error_only` nel ramo non-registrato (§4.2) | ✅ `20260722-11` |
| 3 | Grep pgTAP: nessun test si attende il raise (§4.2) | ✅ 2026-07-22 (zero occorrenze) |
| 4 | ~~`session_info` in modalità ridotta~~ — ritirato (§4.4) | — |
| 5 | pgTAP nuovo (§5.1) | ✅ **7/7 verdi** su dev — `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql` |
| 6 | Convenzione `E_`/`W_` scritta nelle linee guida (§4.3) | ✅ `Messaggi-di-Errore-e-Generazione-Log.md` §Best practice |
| 7 | Guida `tx_id_implementation_guide.md` riallineata (§4.5) | ✅ flusso, catena, principi 2 e 5, tabella GUC |
| 8 | Apply dev + rigen doc auto-gen + note nei manual | ✅ apply, rigen, e note di manutenzione sui manual delle due funzioni |
| 9 | Rimosso il bypass dalla CI (§4.6) | ✅ `ci-validate.yaml`, entrambi gli step |

## 7. Fuori perimetro

- **`config.parameters.tx_id_bypass_enabled`**: resta `false`. Con la regola §3 il
  controllo non ha più motivo di essere spento globalmente.
- **Rinomina di `W_TXID_NOT_REGISTERED`**: non serve (§4.3).
- **Il caso limite `fn_numera_fattura_opz_emessa`** e altri difetti di audit non
  legati al tx_id: non toccati qui.

## 8. Riferimenti

- Guida da riallineare: `docs/it/guide/tx_id_implementation_guide.md`
  (§«Catena di fallback», §202, §357, tabella GUC)
- Funzioni vive: `docs/it/dbzero/dbops/funzioni/fn_get_or_create_session_tx_id.md`,
  `trgfn_tx_id_managed.md`, `fn_generate_tx_id.md`
- Precedente canonico dell'interruttore: `docs/it/dbzero/script/funzioni/fn_ensure_logconn.md`
- Provisioning del canale: `scripts/sql/provision_dblink_log_channel.sql`
  (`log_db` = `current_database()`: il dblink è un loopback, serve l'autonomia non la remotezza)
- Sintomo d'origine: `db/changelog/migrations_v2/80_data/changelog/20260720-10-seed-dbops-coda-lavori-tipi-fatturazione-giro-mctit.yaml`
- CI: `.github/workflows/ci-validate.yaml` (step `standard, no provision` e `CI apply`),
  `.github/workflows/ci.yaml` riga 83 (canale configurato → verde)
