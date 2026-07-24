# Brief DB — `trgfn_tx_id_managed`: uscita anticipata quando il tx_id è già fornito

> **Tipo**: brief operativo per il **team DB** · **Target**: `dev/db-tid` · **Data**:
> 2026-07-24 · **Owner**: Tid · **Stato**: ✅ **APPLICATO e TESTATO** (2026-07-24)
> · **Priorità**: 🟡 MEDIA (nessun dato a rischio: era lavoro inutile su ogni
> scrittura tracciata del database, più un accoppiamento che teneva fermo il
> canale di log).
>
> **Esito**: changeset `20260724-06` applicato, `test-tx-id-coerenza-non-registrato.sql`
> **verde 11/11**, canale di log **sbloccato e verificato** (§6.3: zero rumore
> dblink, errore effettivamente persistito in `dbops.error_log`). Vedi §10.
>
> **Perimetro**: SOLO DB — `dbops.trgfn_tx_id_managed`. Nessun impatto BE/FE:
> il comportamento osservabile dalle applicazioni non cambia (§5).
>
> **Origine**: diagnosi del rumore `dblink` emerso durante i pgTAP della slice
> [brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md)
> (2026-07-24). Il trigger è quello ridisegnato da
> [brief-db-coerenza-tx-id-non-registrato.md](../work-done/brief-db-coerenza-tx-id-non-registrato.md).

---

## 1. Il sintomo

Ogni volta che un guard solleva un errore, i test sputano tre righe di rumore:

```text
ATTENZIONE:  script.fn_log_error_only: dblink_exec DSN fallita
             (code=E_...): permesso negato per lo schema script
ATTENZIONE:  script.fn_log_error_only: dblink_exec logconn fallita ...
ATTENZIONE:  script.fn_log_error_only: nessuna connessione dblink valida,
             log non persistito (code=E_...).
```

Sono `WARNING`, non fallimenti: l'errore arriva regolarmente al chiamante e i
`throws_ok` funzionano. Ma **l'errore non viene registrato in
`dbops.error_log`** — il canale di log, in dev, non ha mai funzionato.

## 2. La catena reale (verificata sul vivo)

Il primo sospetto — che lo statement spedito via dblink toccasse lo schema
`script` — **è sbagliato**. `script.fn_log_error_only` costruisce un `v_sql`
pulito:

```sql
INSERT INTO dbops.error_log(occurred_at, area, function_name,
                            messaggio_errore_id, context, tx_id)
VALUES (now(), ..., ...);
```

Nessun riferimento a `script`. Il problema è **cosa scatta dentro quell'INSERT**:

```text
dblink_exec → sessione remota (service=zeroerp_log, ruolo ristretto)
  └─ INSERT INTO dbops.error_log
       └─ trg_error_log_gen_tx_id_ins_upd  BEFORE INSERT
            └─ dbops.trgfn_tx_id_managed()      ← NON è SECURITY DEFINER
                 ├─ SELECT … FROM config.parameters   (primo statement)
                 ├─ script.uuid_nil()
                 ├─ script.fn_log_error_only(…)
                 └─ script.fn_log_and_raise_error(…)  → permesso negato
```

Il ruolo remoto ha `USAGE ON SCHEMA dbops`, `INSERT` su `error_log` e la
sequence: nient'altro. Il trigger gira **come invoker** e tocca `config` e
`script`. Percorso più probabile: la lettura di `config.parameters` fallisce, e
il gestore d'eccezione che dovrebbe segnalarlo chiama
`script.fn_log_and_raise_error` — è quel secondo errore che affiora.

**Non è una regressione recente.** Confrontate la revisione di novembre 2025
(`20251114-04`) e quella attuale (`20260722-11`): entrambe leggono
`config.parameters` come primo statement e chiamano le stesse tre funzioni
`script.*`. L'accoppiamento c'è dall'origine; è emerso ora solo perché i guard
nuovi esercitano il percorso di log.

## 3. Il difetto vero non è il canale di log

Il canale è il sintomo. Il difetto è nella struttura del trigger:

```text
riga   1   SELECT … FROM config.parameters      ← lettura su OGNI riga
riga  ~30  rami che toccano script.*
riga ~205  IF NEW.tx_id IS NOT NULL AND NEW.tx_id::text = '' THEN … END IF;
riga ~208  IF NEW.tx_id IS NOT NULL THEN RETURN NEW; END IF;   ← esce QUI
riga ~212  NEW.tx_id := COALESCE(GUC, v_new_tx_id, uuidv7());
```

Quando il chiamante **fornisce già** il `tx_id`, tutto ciò che sta sopra
**non ha alcun effetto sul risultato**: `v_new_tx_id` viene consumato solo dalla
`COALESCE` finale, che si raggiunge unicamente se `NEW.tx_id IS NULL`.

Il trigger è installato su **280 tabelle** (verificato sulla doc auto-gen).
Ogni INSERT/UPDATE che porta già il proprio tx_id paga una lettura di
`config.parameters` e un giro di rami inutili.

## 4. Decisione

**Spostare in testa alla funzione, in quest'ordine:**

1. la normalizzazione `IF NEW.tx_id IS NOT NULL AND NEW.tx_id::text = '' THEN
   NEW.tx_id := NULL; END IF;`
2. l'uscita `IF NEW.tx_id IS NOT NULL THEN RETURN NEW; END IF;`

L'ordine è vincolante: invertirlo lascerebbe passare un tx_id "stringa vuota"
senza normalizzarlo. Per una colonna `UUID` quel ramo è di fatto irraggiungibile
— un uuid convertito a testo non è mai `''` — ma **non lo si elimina di
nascosto**: si sposta com'è, e la sua eventuale rimozione è una decisione
separata.

Il resto del corpo resta identico, riga per riga.

### Due risultati con una modifica

- **Il canale di log si sblocca senza toccare i grant.** L'INSERT del log
  fornisce sempre il proprio `tx_id` (`fn_log_error_only` lo risolve prima di
  costruire `v_sql`), quindi con l'uscita in testa il trigger ritorna subito:
  niente `config.parameters`, niente `script.*`, permesso mai richiesto.
  `trg_error_log_gen_tx_id_ins_upd` è **l'unico** trigger su `dbops.error_log`
  (verificato), quindi non restano altri ostacoli sul percorso.
- **280 tabelle smettono di pagare lavoro inutile** su ogni scrittura che porta
  già il tx_id.

## 5. Cosa si perde: l'analisi onesta

Il warning `W_TXID_NOT_REGISTERED` scatta **solo** se valgono entrambe:

1. la GUC di sessione `dbops.tx_id` **è impostata**, e
2. quell'id **non** è in `dbops.transaction_ids`.

È una diagnosi sulla **sessione** («questa connessione gira con un'etichetta
fasulla»), non sulla riga.

| Caso | Effetto dell'uscita anticipata |
| --- | --- |
| **Canale di log** (la sessione dblink) | **Nessuna perdita.** La sessione remota è nuova a ogni chiamata e la GUC non le viene mai impostata (è scritta con scope locale alla transazione, non attraversa la connessione). Condizione 1 falsa → il warning non poteva scattare né prima né dopo |
| **Scritture applicative ordinarie** | **Nessuna perdita.** Non forniscono il tx_id: è il trigger a riempirlo, quindi percorrono la strada lunga esattamente come oggi |
| **Sessione con GUC avvelenata + scritture che portano il proprio tx_id** | Il warning non viene emesso su quelle righe. Ma basta **una sola** scrittura della stessa sessione che lasci il tx_id vuoto perché l'allarme suoni lo stesso |

Resta scoperto solo il caso in cui **tutte quante** le scritture di una sessione
avvelenata portino il proprio tx_id — combinazione stretta, e una sessione così
non ha comunque bisogno del trigger.

**In pratica non si perde la capacità di accorgersi dell'anomalia: si perdono
occasioni ridondanti di segnalarla.**

## 6. Piano

Numerazione: `20260724-01..05` sono occupati dalla slice guard-uscita-commessa
→ si parte da **`-06`**.

### 6.1 — `20260724-06-update-trgfn-tx-id-managed-early-exit-mctit.yaml`

`20_code/dbops/`, `runOnChange: false`. Corpo **dalla doc auto-gen**
(`docs/it/dbzero/dbops/funzioni/trgfn_tx_id_managed.md`), non dagli YAML
([[feedback_db_doc_first]]): tre revisioni si sono sovrapposte, un singolo YAML
è stale. Unica modifica: i due blocchi di §4 spostati in testa, subito dopo
`BEGIN`. Commento in-linea che spiega **perché** sono lì e che l'ordine fra i due
è vincolante. Bump del `COMMENT ON FUNCTION`.

⚠️ Apostrofi: raddoppiati nei letterali `IS '...'`, assenti nei commenti `--`
fuori dai dollar-quote (vedi §3 di
[brief-db-guard-uscita-commessa-e-capabilities.md](brief-db-guard-uscita-commessa-e-capabilities.md)).

### 6.2 — pgTAP: `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql`

**Dato che cambia la valutazione del rischio**: ho verificato tutti gli INSERT
della suite esistente (`plan(7)`) — **nessuno fornisce un tx_id esplicito**,
inseriscono solo colonne di business e lasciano riempire al trigger. La suite
vive quindi **interamente sul percorso `NEW.tx_id IS NULL`**, che questa modifica
non tocca: deve restare verde senza alcun adattamento. Se qualcosa diventasse
rosso lì, sarebbe una regressione vera, non un test da allineare.

Il rovescio: **il comportamento nuovo oggi non ha copertura**. Si estende a
`plan(10)`:

| # | Test |
| --- | --- |
| 8 | Riga con `tx_id` esplicito: il valore fornito viene conservato tale e quale |
| 9 | Riga con `tx_id` esplicito **e GUC avvelenata**: l'INSERT riesce e il tx_id resta quello fornito (la GUC non lo contamina) |
| 10 | Strutturale: nel corpo vivo l'uscita anticipata precede la lettura di `config.parameters` — `strpos(def,'IF NEW.tx_id IS NOT NULL THEN') < strpos(def,'config.parameters')` |

Il test 10 è la sola verifica possibile del *perché* della modifica: che il
lavoro venga saltato non è osservabile dall'esterno.

### 6.3 — Verifica di sblocco del canale (manuale)

Dopo l'applicazione, rieseguire un pgTAP che solleva un errore (es.
`test-guard-uscita-commessa-v1.sql`): i tre `ATTENZIONE` devono **sparire** e la
riga comparire in `dbops.error_log`. È la prova che la catena è chiusa.

### 6.4 — Documentazione

`docs/it/guide/tx_id_implementation_guide.md`: aggiungere che il trigger esce
subito quando il tx_id è già valorizzato, e che in quel caso il controllo di
registrazione della GUC non viene eseguito.

## 7. Rischi

| Rischio | Valutazione |
| --- | --- |
| **280 tabelle** interessate | Il raggio è ampio, ma la modifica è un **anticipo di un `RETURN` già esistente** su un percorso in cui tutto ciò che precede è privo di effetti. Nessuna riga cambia valore |
| Suite tx_id esistente | Verificata: sta tutta sul percorso `tx_id IS NULL`, non toccato (§6.2) |
| Perdita del warning | Analizzata in §5: nulla nei casi reali |
| Il ramo "stringa vuota" | Spostato **com'è**, non rimosso |

## 8. Alternativa scartata, e cosa resta aperto

**Estendere i grant del ruolo di log** (`USAGE ON SCHEMA script` e `config`,
`EXECUTE` sulle tre funzioni, `SELECT` su `config.parameters`) chiuderebbe il
sintomo senza toccare il trigger. Scartata: è fragile — ogni futura modifica alla
catena del trigger può richiudere il canale, **e in silenzio**, perché sono solo
`WARNING`. Inoltre non toglie il lavoro inutile dalle altre 279 tabelle.

Nel repo non esiste alcun `GRANT USAGE ON SCHEMA script`: quei grant vivono nello
script di provisioning fuori da Liquibase
([[reference_batch_role_grants_provision_script]]). Se dopo questa modifica
emergesse un altro percorso remoto che tocca `script`, quello sarà il posto in
cui intervenire — ma prima serve un caso reale, non una supposizione.

**Aperto, fuori perimetro**: se il canale di log resti da provisionare in dev
(password `zeroerp_log_password` non valorizzata, changeset
`20260205-42` in `context: disabled`) è una verifica infrastrutturale a sé. Con
§6.3 lo si scopre subito.

## 9. Esito (2026-07-24)

**Applicato e verificato sul DB vivo.**

| Consegna | Esito |
| --- | --- |
| `20260724-06-update-trgfn-tx-id-managed-early-exit-mctit.yaml` | ✅ applicato (`pg_get_functiondef`: uscita in testa, `exit@1499 < config@1650`) |
| `test-tx-id-coerenza-non-registrato.sql` `plan(7)` → `plan(11)` | ✅ **11/11** (test 1-7 preesistenti verdi senza adattamento — vivono sul percorso `tx_id IS NULL`, non toccato) |
| Canale di log sbloccato (§6.3) | ✅ **zero** righe `ATTENZIONE dblink` rieseguendo `test-guard-uscita-commessa-v1.sql` (prima: 3 per ogni errore) |
| Persistenza reale in `dbops.error_log` | ✅ probe con `fn_log_and_raise_error`: la riga compare in `error_log` (prima l'errore non veniva persistito) |

**Nuova copertura** (test 8-11): tx_id esplicito conservato (8-9), non contaminato
da GUC avvelenata (10), uscita anticipata in testa nel corpo vivo (11, strutturale
— l'unico che discrimina, gli altri passano in entrambe le versioni).

### Resta aperto

- **Doc auto-gen** `trgfn_tx_id_managed.md`: la rigenera Tid al prossimo giro
  ([[feedback_no_hand_edit_autogen_docs]]); al momento mostra ancora i blocchi in
  fondo. Il DB vivo è già corretto.
- **Guida** `tx_id_implementation_guide.md` (§6.4): da aggiornare con l'uscita
  anticipata. Non bloccante.
- **Ramo "stringa vuota"**: spostato com'era, **non rimosso**. Per una colonna
  UUID è codice morto; la sua eliminazione è una decisione separata, non presa
  qui.

## 10. Riferimenti

- Trigger vivo: `docs/it/dbzero/dbops/funzioni/trgfn_tx_id_managed.md`
- Funzione di log: `docs/it/dbzero/script/funzioni/fn_log_error_only.md`
- Disegno del tx_id: [brief-db-coerenza-tx-id-non-registrato.md](../work-done/brief-db-coerenza-tx-id-non-registrato.md) §3, §4.2
- Suite esistente: `db/pgtap/dbops/test-tx-id-coerenza-non-registrato.sql`
- Guida: `docs/it/guide/tx_id_implementation_guide.md`
