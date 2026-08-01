# Brief DB → BE — Piano rate della fattura (scadenze)

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

Il DB è **pronto e applicato**: non c'è niente da aspettare per cominciare.

| Pezzo | Stato |
|---|---|
| `vendite.fn_genera_scadenze_fattura(fattura_id)` — il generatore | ✅ applicata, pgTAP 14/14 |
| `vendite.fn_genera_scadenze_lotto(lotto_id, batch_size)` — il wrapper | ✅ applicata, pgTAP 11/11 |
| Codici errore **570-573** | ✅ registrati in `config.messaggi_errore` |
| Registro del task: `pipeline_task_registry` **20**, `impl` **20**, `task_policy` **19-23** | ✅ seminati, **inerti** |
| Il task nei `processi` dello step EMESSA | ⛔ **non armato** — §5 |

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

---

## 5. Cosa deve fare il BE

Nessuna logica di calcolo in Python: solo cablaggio, sul modello esatto di
`ricalcola_iva_lotto`.

1. handler `_handle_genera_scadenze_lotto_task` in `pipeline_step_executor.py`
   (+ entry nel `handler_registry`);
2. wrapper `run_genera_scadenze_lotto_task(*, lotto_id, batch_size)` in
   `pipeline_repository.py`;
3. voce in `ALLOWED_TASK_FUNCTIONS` → `vendite.fn_genera_scadenze_lotto`;
4. i **sei contatori** nel risultato del task, con i due `skipped` separati;
5. test unitari dell'handler (run + dry-run) e del wrapper;
6. smoke sul percorso reale: le rate esistono, quadrano **al centesimo** con
   `totale_a_pagare`, e il PDF le stampa.

### L'armamento: chi muove per primo

Il seed è in **due tempi**, come per lo snapshot indirizzi e per la stessa
ragione: il dispatch dei task non è dinamico.

**Fatto**: registro, implementazione e policy sono seminati e **inerti** — non
fanno partire niente.

**Da fare, in quest'ordine**: prima voi registrate il task in
`ALLOWED_TASK_FUNCTIONS`, poi noi aggiungiamo il nodo `genera_scadenze_lotto` ai
`processi` dello step EMESSA. Invertire l'ordine fa morire il lotto su un task
sconosciuto.

⚠️ Nello stesso giro va riempita la **corsia giornaliera** (`fatturazione_pipeline`
id 2), oggi vuota: fondi + IVA + scadenze. Finché resta così quella corsia emette
documenti senza riepilogo IVA né totali.

---

## 6. Se si produce una LISTA

Oggi **non esiste nessuna lista di scadenze**: verificato, in
`ui.lista_definizione` non c'è. Il frontend mostra la sintesi del piano rate nel
drawer fattura tramite il BB `ScadenzeSintesi` / `useScadenzeSintesi`, e mostra
`—` finché le rate non arrivano — quindi **si accende da sé** quando il task gira.
Per far vedere le rate non serve nessuna lista.

Se invece si decide di farla, valgono le regole di
[piano-migrazione-primevue-5.md](piano-migrazione-primevue-5.md), e non sono
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
