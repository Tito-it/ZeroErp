# Brief DB → BE — Piano rate della fattura (scadenze)

> ## ✅ CHIUSO — 2026-08-02
>
> **Contratto onorato su entrambi i lati.** DB: generatore, wrapper, seed,
> armamento delle due corsie e guard D-K alla numerazione, tutti applicati e
> coperti da pgTAP. BE: cablaggio, sei contatori, guard d'ordine e **smoke verde**
> (`smoke-fattura-scadenze.py`, 10 casi, più il PDF nel caso 9 di
> `smoke-fatturazione-render-stampa.py`), entrambi con prova di mutazione.
>
> **Non restano voci aperte.** Il §6 («se si produce una lista») è condizionale e
> nessuna lista serve; il §7 elenca ciò che è **fuori scope per decisione**:
> riconciliazione rata↔incasso, blocco `2.4 DatiPagamento` e portale clienti —
> in quest'ordine, quando si riaprirà il tema incassi.
>
> **Da qui in avanti si legge come riferimento**, non come lavoro: formula,
> codici errore, contatori e trappole restano validi. Lo stato del cantiere sta
> in [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md) §9.

---

> **Riscritto il 2026-08-02.** La stesura precedente era del 2026-07-29 e portava
> in testa un blocco di revisione: era «superata in parte sostanziale», perché
> descriveva un lavoro da fare e buona parte di quel lavoro è stata poi decisa
> diversamente — **D-I** ha eliminato il «percorso legacy» che ne occupava metà.
> Tenerla in piedi accanto al piano significava avere due fonti che divergono,
> che è il difetto che questo cantiere ha già pagato altrove. **La storia sta in
> git**: qui resta solo ciò che serve adesso.
>
> **Fonte di verità sullo stato**: [piano-db-satelliti-fattura.md](piano-db-satelliti-fattura.md) §9.
> Questo documento è il **contratto verso il BE** — cosa il DB espone, cosa il BE
> deve cablare, e dove i due si incontrano.
>
> **Fratello**: [brief-db-snapshot-indirizzi-fattura.md](brief-db-snapshot-indirizzi-fattura.md) (step DRAFT).
> **Lavoro applicativo a valle**: [piano-be-fe-satelliti-fattura.md](piano-be-fe-satelliti-fattura.md).

---

## 1. Perché serve

Far generare alla pipeline il **piano rate** di ogni fattura in
`vendite.fatture_scadenze`. Fino a oggi quella tabella è vuota per costruzione:
non è un bug, è un produttore che non è mai stato scritto — tutto il resto della
catena esiste già (audit, storico, RLS, grant al ruolo batch, lettore, contesto
PDF, endpoint di dettaglio, BB frontend).

Quattro conseguenze, di cui una fiscale:

1. il **PDF** non stampa il piano rate, benché la sezione esista nel template;
2. il blocco **`2.4 DatiPagamento` della FatturaPA non è generato** — è
   completezza fiscale, non un abbellimento;
3. il **portale clienti** ha in piano `GET /api/portale/scadenze/`, oggi vuoto;
4. nel drawer fattura «Modalità di pagamento» e «Termine» sono sempre vuoti.

---

## 2. Dove siamo

**Aggiornato il 2026-08-02: il cantiere è CHIUSO su entrambi i lati.** Task
armato, guard D-K applicato, smoke verde. Il **§5-bis** resta come nota di
manutenzione: dice perché lo smoke gira su fatture nuove e cosa non asserire.

| Pezzo | Stato |
|---|---|
| `vendite.fn_genera_scadenze_fattura(fattura_id)` — il generatore | ✅ applicata, pgTAP 14/14 |
| `vendite.fn_genera_scadenze_lotto(lotto_id, batch_size)` — il wrapper | ✅ applicata, pgTAP 11/11 |
| Codici errore **570-573** | ✅ registrati in `config.messaggi_errore` |
| Registro del task: `pipeline_task_registry` **20**, `impl` **20**, `task_policy` **19-23** | ✅ seminati |
| Cablaggio BE (handler, wrapper, `ALLOWED_TASK_FUNCTIONS`, sei contatori, test) | ✅ **fatto** (`14970e898`) |
| Il task nei `processi` dello step EMESSA | ✅ **ARMATO** su pipeline **3** (MASSIVO) e **2** (GIORNALIERO) |
| Corsia GIORNALIERO/EMESSA (pipeline 2), prima vuota | ✅ **riempita**: fondi → fondi → IVA → scadenze |
| Invariante pgTAP sui `processi`, esteso a tutte le tappe | ✅ `test-pipeline-processi-invariante-v1.sql`, 7/7 |
| **Guard D-K alla numerazione** (Fase 4b) — `numera_fatture` ora rifiuta i documenti incoerenti | ✅ **applicato** (`20260802-24`), pgTAP 9/9 — **§5-bis punto 3** |
| **Smoke di accettazione end-to-end** | ✅ **VERDE** (`7a041d2e7`): `smoke-fattura-scadenze.py` **10 casi** + il PDF in `smoke-fatturazione-render-stampa.py` caso 9, entrambi con **prova di mutazione** |

> ✅ **CONTRATTO ONORATO SU ENTRAMBI I LATI (2026-08-02).** Non restano voci
> aperte. Il brief si legge ora come riferimento — formula, errori, contatori —
> non come lavoro da fare.

---

## 3. Il contratto

### 3.1 Il generatore, per fattura

```sql
SELECT * FROM vendite.fn_genera_scadenze_fattura(:fattura_id);
-- deleted_rows integer, inserted_rows integer
```

**Legge e non risolve.** Prende `termine_pagamento_id` dalla testata, dove arriva
passando dalla chiave di aggregazione. Non risale a nessuna anagrafica: se lo
facesse esisterebbero due risolutori delle condizioni di pagamento, e due
risolutori divergono in silenzio — è ciò che la Fase 3b è servita a togliere.

**È idempotente**: `DELETE` + `INSERT`, quindi rieseguire ricostruisce lo stesso
piano invece di sommarcisi. La `DELETE` avviene **prima** dei casi a base non
positiva: una fattura diventata interamente coperta da acconti **perde** le rate
che aveva, invece di conservarle senza che nessuno lo dica.

**Scrive anche** `fatture.termine_pagamento_snapshot` con i **valori** del
termine e non il solo id, così una fattura emessa continua a spiegare le proprie
rate anche se il catalogo cambia.

### 3.2 Il wrapper, per lotto

```sql
SELECT * FROM vendite.fn_genera_scadenze_lotto(:lotto_id, :batch_size);
-- fatture_count, deleted_rows, inserted_rows,
-- skipped_rows, skipped_errore_rows, failed_rows
```

**I due `skipped` sono due cose diverse e vanno mostrati diversi.**
`skipped_rows` = fatture **oltre la soglia** DRAFT/EMESSA: documenti chiusi, non
hanno lavoro da fare. `skipped_errore_rows` = fatture marcate critiche **da un
altro task**: documenti rotti, che uno step a valle non deve riprovare. Un
contatore unico direbbe «cinque saltate» senza distinguere cinque documenti a
posto da cinque da guardare, che per chi legge il cockpit sono l'opposto.

**Il fallimento di una non uccide il giro**: la fattura difettosa viene marcata
`'C'` su `fatture_log` e le altre proseguono, così i problemi si vedono tutti in
una volta invece di uno per esecuzione.

**Il rilancio dello stesso step ripara**: al successo il task ritira le
**proprie** segnalazioni. Quelle di un altro task restano — chi le ha alzate sa
quando abbassarle.

---

## 4. Gli errori, e cosa farne

| Codice | Quando | Cosa dice davvero |
|---|---|---|
| **570** `E_SCADENZE_TERMINE_MANCANTE` | testata senza `termine_pagamento_id` | difetto a monte: la catena ha un default (`TP_1RATA`), non dovrebbe accadere |
| **571** `E_SCADENZE_BASE_NON_PRONTA` | `totale_a_pagare` è NULL | passi eseguiti fuori ordine: i totali si calcolano prima |
| **572** `E_SCADENZE_TERMINE_INVALIDO` | il termine di catalogo è inconciliabile con quella base | è il **termine** a essere sbagliato, non la fattura |
| **573** `E_SCADENZE_FATTURA_BLOCCATA` | fattura oltre DRAFT/EMESSA | è uno snapshot fiscale: il suo piano rate è quello |

⚠️ **Tre casi che NON sono errori**, e su cui non va costruito nessun allarme:

- `totale_a_pagare = 0` → **zero rate, nessun log**: fattura interamente coperta
  da acconti, documento normale;
- `totale_a_pagare < 0` → **zero rate + log non critico**: saldo a favore del
  cliente. A volte è corretto, a volte è un fondo configurato male, e la
  differenza la vede una persona. Il modello aveva già deciso prima di noi che un
  documento a credito non si rateizza (`CHECK (importo >= 0)`);
- una fattura **senza rate non è una fattura difettosa**.

> ℹ️ **Un quinto codice, che non è del generatore ma vi arriverà addosso lo
> stesso**: **574 `E_FATTURA_NON_NUMERABILE_INCOERENTE`**, sollevato da
> `fn_assign_numero_fattura` nello step **DEFINITIVA**. Non nasce qui, ma è il
> valle naturale di questo lavoro: è il presidio che impedisce di dare un numero
> fiscale a un documento a cui le rate mancano. Le sei condizioni e le
> conseguenze pratiche sono nel **§5-bis punto 3**.
>
> Attenzione a non confonderlo con il **571** `E_SCADENZE_BASE_NON_PRONTA`: il
> 571 dice «i totali non ci sono ancora, il piano rate non si può calcolare» ed è
> dello step EMESSA; il 574 dice «il documento è incoerente, non merita un numero
> fiscale» ed è dello step DEFINITIVA. Stesso sintomo a monte, momenti e rimedi
> diversi.

---

## 5. Cosa deve fare il BE

Nessuna logica di calcolo in Python: solo cablaggio, sul modello esatto di
`ricalcola_iva_lotto`.

1. ✅ handler `_handle_genera_scadenze_lotto_task` in `pipeline_step_executor.py`
   (+ entry nel `handler_registry`);
2. ✅ wrapper `run_genera_scadenze_lotto_task(*, lotto_id, batch_size)` in
   `pipeline_repository.py`;
3. ✅ voce in `ALLOWED_TASK_FUNCTIONS` → `vendite.fn_genera_scadenze_lotto`;
4. ✅ i **sei contatori** nel risultato del task, con i due `skipped` separati;
5. ✅ test unitari dell'handler (run + dry-run) e del wrapper;
6. ✅ smoke sul percorso reale: `smoke-fattura-scadenze.py` **10 casi** verdi con
   prova di mutazione, e il PDF coperto dal **caso 9** di
   `smoke-fatturazione-render-stampa.py` (9/9) — messo lì e non duplicato, perché
   la macchina per verificare un rendering (template, contesto, Jinja, PDF reale)
   esiste già in quel file.

### L'armamento: fatto, in entrambi i tempi ✅

Il seed era in **due tempi**, come per lo snapshot indirizzi e per la stessa
ragione: il dispatch dei task non è dinamico.

Entrambi i tempi sono stati eseguiti il 2026-08-02, nell'ordine giusto: prima la
registrazione del task lato BE, poi il nodo `genera_scadenze_lotto` nei `processi`
dello step EMESSA. La **corsia giornaliera** (`fatturazione_pipeline` id 2), che
era vuota, è stata riempita nello stesso giro con fondi + IVA + scadenze: finché
restava così emetteva documenti senza riepilogo IVA né totali.

📌 **Due presidi sull'ordine, complementari — non toglierne uno.** Il task deve
stare **dopo** `ricalcola_iva_lotto`, perché prima la base `totale_a_pagare` non
esiste. Oggi l'invariante è sorvegliato da due parti, che guardano oggetti
diversi:

| Presidio | Dove | Cosa vede |
|---|---|---|
| `_TASK_ORDER_DEPENDENCIES` | `pipeline_step_executor.py` (BE) | la **configurazione letta** a runtime, prima che il primo task scriva |
| `test-pipeline-processi-invariante-v1.sql` | `db/pgtap/vendite/` (DB) | il **seed** che quella configurazione la produce |

Non sono la stessa difesa scritta due volte: il primo protegge un giro già
avviato da una config girata, il secondo impedisce che la config sbagliata nasca.
Chi in futuro li trovasse entrambi non ne rimuova uno pensando a un doppione.

---

## 5-bis. Prima di scrivere lo smoke: tre cose che lo farebbero fallire su comportamenti corretti

**1. Va girato su fatture NUOVE, prodotte da un giro post-3b.** Le fatture
esistenti al 2026-08-02 (**632, 834-836**) sono state create il 31/07; la catena
che scrive `termine_pagamento_id` in testata è entrata il 01/08 con la Fase 3b.
Sono **anteriori di ~13 ore** al meccanismo, quindi su di loro
`E_SCADENZE_TERMINE_MANCANTE` (570) è **il comportamento corretto**, non un
difetto. Uno smoke puntato sul parco esistente sarà rosso per sempre, e sarà un
rosso che non insegna niente.

**2. La quadratura si asserisce solo sulle fatture con base positiva.** Il punto 6
chiede che le rate quadrino al centesimo con `totale_a_pagare`; il **§4** dice che
con `totale_a_pagare <= 0` le rate sono **zero** ed è un documento legittimo. Le
due frasi convivono solo se lo smoke **esclude** dalla quadratura le fatture a
base non positiva. Altrimenti fallisce sulla prima fattura interamente coperta da
acconti — e fallirebbe *correttamente*, che è il modo peggiore di scoprirlo.

**3. D-K è ARRIVATO (2026-08-02, `20260802-24` applicato): la numerazione ora
verifica sei condizioni.** Non è più un avviso su qualcosa che verrà — è il
comportamento di adesso, e tocca direttamente lo smoke.

`vendite.fn_assign_numero_fattura` rifiuta con
**`E_FATTURA_NON_NUMERABILE_INCOERENTE` (574)** un documento che violi anche una
sola di queste:

| # | Condizione |
|---|---|
| 1 | `totale_a_pagare` è NULL — i totali non sono mai stati calcolati |
| 2 | ci sono righe ma **nessun riepilogo IVA** |
| 3 | `totale_a_pagare > 0` e **nessuna rata**, oppure **Σ rate ≠ totale_a_pagare** |
| 4 | `totale_a_pagare <= 0` ma **esistono rate** (D-D allo specchio) |
| 5 | i **riepiloghi IVA non quadrano** con i totali di testata |
| 6 | `totale_a_pagare` **non è la somma dei suoi addendi** (`totale_doc` + fondi + arrotondamenti) |

Insieme verificano una catena continua, senza anelli scoperti:
`riepiloghi IVA →(5) totale_doc →(6) totale_a_pagare →(3/4) rate`.

**Cosa cambia per voi, in concreto:**

- **Lo step `numera_fatture` ora può dire di no**, e prima non l'aveva mai fatto.
  L'errore arriva con **tutti** i motivi insieme (array `motivi` nel payload, e
  concatenati nel messaggio), non uno per giro: un solo rilancio vi dice tutto
  ciò che manca al documento.
- Il codice **574 è già registrato** in `config.messaggi_errore` dalla Fase 1.3 —
  se non è ancora in `error_policies.py`, va aggiunto lì.
- **Le fixture che numerano fatture prive di satelliti si rompono.** Lato DB era
  **una** su tre: `test-numera-fattura-opz-emessa`, sanata facendole costruire un
  documento completo con le funzioni vere (`fn_ricalcola_riepilogo_iva_fattura` →
  `fn_ricalcola_totali_fattura` → `fn_genera_scadenze_fattura`) invece di
  scrivere i satelliti a mano. Se avete fixture Python che numerano, è lo stesso
  lavoro.
- Le fatture **632, 834-836** ora **non sono numerabili** — condizione 3, non
  hanno rate perché non hanno il termine in testata. È la seconda ragione, dopo
  il punto 1, per cui lo smoke va su documenti nuovi.

> ℹ️ **Una precisazione che smonta una motivazione che girava.** Il guard sta
> *prima* del consumo del progressivo, ma **non** per evitare un buco di
> numerazione: verificato il 2026-08-02, `fn_get_next_progressivo` non usa alcuna
> sequence — è `pg_advisory_xact_lock` + `UPDATE last_numero` — quindi è
> transazionale e il numero fa rollback insieme al documento. Il danno che il
> guard evita è l'**opposto e irreversibile**: un numero fiscale valido su un
> documento invalido. Una volta numerato, il documento è DEFINITIVA, i satelliti
> sono congelati e **le rate mancanti non si possono più aggiungere**: si ripara
> solo con una nota di variazione. Se trovate la frase «nextval non fa rollback»
> nei changeSet precedenti, è superata.

---

## 6. Se si produce una LISTA

Oggi **non esiste nessuna lista di scadenze**: verificato, in
`ui.lista_definizione` non c'è. Il frontend mostra la sintesi del piano rate nel
drawer fattura tramite il BB `ScadenzeSintesi` / `useScadenzeSintesi`, e mostra
`—` finché le rate non arrivano — quindi **si accende da sé** quando il task gira.
Per far vedere le rate non serve nessuna lista.

Se invece si decide di farla, valgono le regole di
[piano-migrazione-primevue-5.md](../work-in-progress/piano-migrazione-primevue-5.md), e non sono
formalità: `<ListaConfigurabile>` è parametrizzato dalla configurazione risolta
dal BE, quindi **senza configurazione non si monta**.

**I cinque prerequisiti tecnici:**

| # | Prerequisito | Nota per le scadenze |
|---|---|---|
| 1 | **Endpoint paginato server-side** | 🔴 **non esiste**: nessuna rotta scadenze. È lavoro BE vero, non «di passaggio» |
| 2 | **Codici colonna == campi dell'API** | il BB rende `data[codice]`: il nome è un contratto, non un'etichetta |
| 3 | **Display field risolti dal BE** | numero fattura, cliente, termine: in JOIN, mai lookup client-side |
| 4 | **Il caller resta padrone dei dati** | fornisce `rows`/`total`/`loading` e gestisce `@page`/`@sort`; il BB non fa fetch |
| 5 | **Rendering custom via slot** | `cell-{codice}` per la cella, `actions` + `RowActionsMenu` per le azioni |

**La configurazione**: una riga in `ui.lista_definizione` + N in `ui.lista_colonna`
(facoltative `lista_colonna_permesso` e `lista_preset`). Si può creare
dall'amministrazione in-app — è **dato, non DDL** — ma **va anche seedata**,
altrimenti sparisce su un'installazione pulita. Il seed è leggero: i quattro
loader sono `runOnChange` + `ANY`, cioè mirror vivi dei CSV, quindi **basta
appendere le righe**, nessun changeset nuovo. I file stanno sotto `db/`, quindi
passano da noi. Per la parte meccanica c'è `scripts/gen_seed_lista.py`.

### 🔴 Due limiti di dominio che la lista deve rispettare

**Non esiste uno stato di pagamento della rata.** `fatture_scadenze` non ha uno
stato, e gli incassi (`pagamenti.vendite_movimenti`) sono legati alla **fattura**
e non alla singola rata: nessuna FK incasso → scadenza, e lo schema
`contabilita` è vuoto. Quindi **nessuna colonna «scaduta / insoluta», nessuna
colorazione di sollecito, nessun filtro «da incassare»**: su una fattura già
incassata sarebbero tutti falsi. Si può fare l'elenco del **piano rate**; uno
**scadenzario** è un'altra cosa, e il modello oggi non può sostenerlo.

**La «prossima rata» è temporale, non di pagamento.** La regola vive già in
`useScadenzeSintesi` ed è una per tutto il prodotto: la prossima per data, e se
sono tutte passate l'ultima. Se la lista la ricalcola per conto suo, drawer e
lista daranno risposte diverse sullo stesso documento.

> Quando la riconciliazione rata ↔ incasso esisterà, lo scadenzario diventa
> possibile e questi due limiti cadono. Prima no.

---

## 7. Fuori scope

- **Riconciliazione rata ↔ incasso**: è il prerequisito di solleciti e
  scadenzario, e non c'è.
- Blocco `2.4 DatiPagamento` del payload SDI: abilitato da questo lavoro, ma è
  del cantiere SDI.
- `GET /api/portale/scadenze/` del portale clienti.

---

## 8. Cosa non fare — trappole già pagate

- **Non risolvere le condizioni di pagamento nel task**: si leggono dalla
  testata. Un secondo risolutore diverge, e diverge in silenzio.
- **Non trattare `totale_a_pagare <= 0` come errore**: bloccherebbe il lotto al
  primo cliente con acconto capiente.
- **Non filtrare le fatture su `stato_esecuzione = 'ERRORE'`**, se un domani
  scriverete un filtro vostro: quella colonna dice «c'è un log critico» di
  **qualunque** task, e chi la usa per saltare si chiude fuori dal proprio stesso
  rilancio. Il criterio giusto è **di chi è** la segnalazione (`meta->>'task'`).
- **Non derivare stati di pagamento dalle date** — §6.
