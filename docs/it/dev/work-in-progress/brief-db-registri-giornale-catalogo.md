# Brief DB — I registri del giornale hanno bisogno di un catalogo

> **Chi scrive:** backend (`dev/backend-tid`), 2026-09-19. **A chi:** team DB.
> **Origine:** rilettura critica del pezzo G dell'osservabilità
> (`piano-be-fe-osservabilita-pallino-e-superfici.md`, registro del 19-09) e
> decisione di Tid dello stesso giorno («ok procedi» sulla strada del catalogo).
>
> **In una riga:** il vocabolario dei **registri** che `script.vw_giornale_entita`
> cuce (`EVENT_LOG`, `LOTTO_LOG`, `TASK_RUN`, `FATTURA_LOG`) oggi vive in
> **tre sedi che non si conoscono** — i letterali dei quattro rami `UNION ALL`
> della vista, la costante `GIORNALE_REGISTRI` del backend, l'array `REGISTRI`
> della view Vue — e **nessuna** porta l'etichetta: la tendina «Registro» del
> giornale mostra `EVENT_LOG` grezzo, un testo a video che non passa da `$t()`.
>
> ⇒ **Serve un catalogo** `config.registri_giornale` (§4), nella forma delle
> tabelle di configurazione che il lookup generico sa leggere, più **un pgTAP**
> che tenga la vista e il catalogo allineati nei due versi (§4.3). È lo stesso
> stampo di `config.tipi_entita` e `config.eventi_dominio`, i due vocabolari
> gemelli che la vista già porta in colonna.
>
> ⛔ **Il backend si ferma qui e aspetta**: BE/FE solo con prerequisiti DB
> pronti. Ciò che fa appena il seed è a DB è al §5, ed è poca roba.
>
> ✅ **Lato DB CHIUSO il 19-09 — applicato su dbdev, pgTAP verdi come app
> (13/13 e 15/15), nessuna regressione nella suite.** Da leggere per primo:
> §8 (as-built) e §6 (le tre risposte del team DB, una delle quali cambia il
> §4.1: niente `attivo`). Resta il commit su `dev/db-tid`. **Ora tocca al
> §5 (BE/FE)**, con le quattro note del §8.4 che il DB ha trovato per strada.

---

## 1. Il fatto, letto dalla struttura

`script.vw_giornale_entita` (doc auto-gen `docs/it/dbzero/script/views/`) è
quattro `SELECT` in `UNION ALL`, e ogni ramo scrive il proprio registro come
**letterale**:

```sql
    'EVENT_LOG'::text   AS registro,   -- ramo 1, vendite.event_log
    'LOTTO_LOG'::text   AS registro,   -- ramo 2, fatturazione_lotti_log
    'TASK_RUN'::text    AS registro,   -- ramo 3, fatturazione_lotti_task_runs
    'FATTURA_LOG'::text AS registro,   -- ramo 4, fatture_log
```

Il commento della vista dichiara da sé che i registri **cresceranno** («i
registri di eventi del progetto sono **sei** … la domanda "cosa è successo a
questa pratica" arriverà. Un ramo nuovo entra con un `UNION ALL`»). Quel giorno
il quinto letterale entra nella vista; le altre due sedi **no**, e nessuna
delle due fallisce:

| Sede                                              | Cosa succede col quinto registro                                                                                |
| ------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| `GIORNALE_REGISTRI` (BE, `vendite_repository.py`) | il filtro `?registro=PRATICHE_GIORNALE` risponde **400** — corretto ma cieco: la riga c'è e non si può chiedere |
| `REGISTRI` (FE, `GiornaleListView.vue`)           | la tendina **non lo mostra**. Nessun errore: le righe passano nel «tutti» e basta                               |

⚠️ La misura che segue è un **fatto datato**, non il motivo: al 19-09 le tre
sedi coincidono (quattro valori ovunque). Il motivo è sul modello — un
vocabolario che la vista **emette** e che due consumatori **validano e
mostrano** ha una sede sola, o diverge in silenzio. È già successo alla
tendina gemella «Entità»: sette codici ricopiati a mano contro **nove** a
catalogo (`FLUSSO`, `DEFINIZIONE_WORKFLOW` mancavano), chiuso il 19-09 con un
lookup su `config.tipi_entita`. Lì la sede c'era; qui **va creata**.

### 1.1 Il secondo difetto: l'etichetta

`config.tipi_entita` e `config.eventi_dominio` — gli altri due vocabolari che
la vista porta in colonna — dichiarano entrambi `etichetta_key`, l'indirizzo
i18n che il frontend risolve con `labelOrCode`. Il registro **no**: non ha
dove dichiararlo, quindi la tendina e la colonna «Registro» mostrano il codice
macchina. È l'unico testo del giornale che l'operatore legge in inglese
maiuscolo, e non per scelta.

## 2. Perché un catalogo e non le alternative

| Strada                                                                         | Cosa risolve                                                                                                      | Cosa lascia                                                                                          |
| ------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------- |
| **A. Catalogo `config.registri_giornale`** + pgTAP di allineamento             | una sede, l'etichetta dichiarata dal DB, lookup generico senza codice nuovo, il quinto registro = una riga di CSV | un changeSet e un pgTAP                                                                              |
| B. Il backend espone `registri_ammessi` nell'envelope (da `GIORNALE_REGISTRI`) | la copia FE                                                                                                       | la copia BE resta seconda sede rispetto alla vista; l'etichetta va inventata nel FE                  |
| C. `SELECT DISTINCT registro FROM vw_giornale_entita`                          | tutto, a parole                                                                                                   | una scansione dei quattro registri per popolare una tendina: no                                      |
| D. Una `fn_giornale_registri()` in `script` accanto alla vista                 | la sede unica                                                                                                     | una funzione da tenere allineata a mano alla vista come la costante — sposta il problema in `script` |

**A**, perché è la forma che il progetto ha già scelto due volte per lo stesso
genere di dato (§1.1), e perché il pgTAP del §4.3 è l'unico presidio che
**lega la vista al catalogo nei due versi**: un ramo nuovo senza la sua riga fa
rosso, una riga senza il suo ramo fa rosso.

## 3. Cosa NON cambia

- La vista **non** fa `JOIN` sul catalogo: il registro resta un letterale nel
  ramo (è l'identità del ramo, non un dato da risolvere), e il catalogo lo
  **descrive**. Un `JOIN` per riga su quattro registri comprerebbe niente e
  costerebbe su ogni lettura del giornale.
- Nessuna FK da `vw_giornale_entita` (è una vista) né dalle quattro tabelle
  sorgente: il legame lo tiene il pgTAP, come per i `CHECK` che `valori_check`
  specchia lato Python.
- `GIORNALE_REGISTRI` nel backend **resta** finché il seed non è a DB; dopo, o
  si legge dal catalogo (§5) o si pinna al catalogo con un test — come
  `_CLASSI`/`_CANALI` di `processi_service` sono pinnate ai loro `CHECK`.

## 4. La richiesta

### 4.1 Tabella `config.registri_giornale` (`00_schema`)

> ⚠️ **Tabella richiesta, non as-built.** Tre scostamenti, decisi dal team DB
> e motivati al §6/§8: **niente `attivo`** (D3), `sorgente` **`text`** (D1),
> `id` **`bigint`** come tutte le sorelle di `config` (`smallint` non
> comprava niente su quattro righe e rompeva l'uniformità della forma).

Nella forma che `dbops.fn_get_lookup_codici` pretende — `id` intero,
`codice`, `codice_interno`, `descrizione`, `attivo` — più `etichetta_key` e
`obsoleto_dal` come le due sorelle:

| Colonna          | Tipo                                                                  | Note                                                                                      |
| ---------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `id`             | `smallint` IDENTITY, PK                                               | il lookup generico vuole un id intero                                                     |
| `codice`         | `text` NOT NULL, UNIQUE                                               | mutabile, per la UI                                                                       |
| `codice_interno` | `text` NOT NULL, UNIQUE, **immutabile** (`script.trgfn_lock_columns`) | è il valore che la vista **emette** in `registro` e che il BE valida — la chiave stabile  |
| `descrizione`    | `text` NOT NULL                                                       | italiano, per il lookup e l'export                                                        |
| `etichetta_key`  | `text` NOT NULL                                                       | `config.registri_giornale.<codice_interno minuscolo>` — stesso patto di `tipi_entita`     |
| `sorgente`       | `regclass` o `text` NOT NULL                                          | la tabella che il ramo legge (`vendite.event_log`, …): documenta il ramo e serve al pgTAP |
| `attivo`         | `boolean` NOT NULL DEFAULT true                                       | come ogni tabella config                                                                  |
| `obsoleto_dal`   | `date` NULL                                                           | ritiro senza cancellare (le righe vecchie del diario restano leggibili)                   |
| audit            | `data_insert`/`user_insert`/`data_update`/`user_update`               | standard                                                                                  |

### 4.2 Seed (`80_data/sql/config/registri_giornale.csv`, mirror `loadUpdateData`)

| codice_interno | descrizione                   | sorgente                               |
| -------------- | ----------------------------- | -------------------------------------- |
| `EVENT_LOG`    | Eventi di dominio             | `vendite.event_log`                    |
| `LOTTO_LOG`    | Log del lotto di fatturazione | `vendite.fatturazione_lotti_log`       |
| `TASK_RUN`     | Corse dei task di pipeline    | `vendite.fatturazione_lotti_task_runs` |
| `FATTURA_LOG`  | Log della fattura             | `vendite.fatture_log`                  |

⚠️ `codice` = `codice_interno` alla nascita, come nelle sorelle. Le
`etichetta_key` le porta il frontend nei locales nello stesso giro del §5
~~(`check_i18n_keys.py` le trova nel CSV da sé: scandisce ogni CSV di `80_data`)~~
— ⛔ **falso, verificato il 19-09 leggendo lo script**: `RE_SEED_KEY` legge
solo le chiavi JSON *dentro* le celle (`""label_key"": ""…""`), non una
colonna `etichetta_key`. Le chiavi di `tipi_entita` sono nei locales perché
il cantiere FE le ha scritte a mano. ⇒ Nel §5 le otto chiavi vanno scritte
**e** il guard va insegnato a leggere la colonna (§8.4), o la prossima riga
di catalogo resterà senza testo in silenzio.

### 4.3 Il presidio (pgTAP, `db/pgtap/script/test-giornale-registri-catalogo-v1.sql`)

Dal template `_TEMPLATE.sql.txt`, con il contesto operatore. Due asserzioni,
**entrambe senza dati** — si legge la **definizione** della vista, non le sue
righe (regola zero: una prova che itera sul contenuto passa a vuoto in CI):

1. **ogni registro che la vista emette è a catalogo**: i letterali
   `'X'::text AS registro` estratti da `pg_get_viewdef('script.vw_giornale_entita')`
   sono tutti in `config.registri_giornale.codice_interno` con
   `obsoleto_dal IS NULL`;
2. **ogni registro vivo a catalogo ha il suo ramo**: il verso opposto — una riga
   seminata senza `UNION ALL` è una promessa che il giornale non mantiene.

Più il classico: `attivo`/`obsoleto_dal` coerenti, `codice_interno` bloccato dal
trigger (`throws_ok` su `UPDATE … SET codice_interno`).

⭐ È il pgTAP che rende il catalogo una **sede** e non una quarta copia: senza,
sarebbe la strada D con una tabella al posto della funzione.

### 4.4 Postura

~~Solo `SELECT` all'app, come le sorelle~~ — ⚠️ **le sorelle non sono «solo
SELECT»**: il loop di `90_end/20260205-41` dà all'app `SELECT/INSERT/UPDATE/DELETE`
su ogni tabella di `config` (verificato il 19-09 con `has_table_privilege` su
`tipi_entita`, `eventi_dominio`, `modi_approvvigionamento`), e una postura più
stretta costa tre sedi (AGENTS.md §REVOKE) per un vocabolario di quattro
righe che l'amministrazione potrebbe voler rietichettare. Postura **standard**,
nessun `GRANT` nel changeSet. Niente RLS (vocabolario globale, come
`tipi_entita`). Nessun `GRANT` a ruoli batch (AGENTS.md §privilegi).

## 5. Cosa fa il backend appena il seed è a DB (nello stesso giro)

- `config.registri_giornale` entra in `_REL_CONSENTITE` (`dbops_repository`):
  il frontend monta `<LookupSelect rel="config.registri_giornale" value-field="codice_interno">`
  e l'array `REGISTRI` della view **sparisce**, come `TIPI_ENTITA` il 19-09.
- `GIORNALE_REGISTRI` si **pinna al catalogo** con un test su DB provvisto
  (`richiedi_db_provvisto`: l'insieme Python = `codice_interno` vivi), oppure
  il service la legge dal catalogo — decido alla consegna guardando il costo:
  la validazione del filtro sta su una richiesta di lista, e una `SELECT` da
  quattro righe per chiamata non è un problema, ma la costante pinnata è a
  zero round-trip e fa rosso alla prima divergenza, che è ciò che conta.
- La colonna «Registro» della lista `vendite.giornale` (seed `lista_colonna`
  887) prende un `formato` o uno slot che rende `labelOrCode` sull'etichetta:
  oggi mostra il codice grezzo.
- Locales: nove chiavi (`config.registri_giornale.*`, it/en), e la parola
  «Registro» sulla tendina resta.

## 6. Domande aperte al team DB — ✅ risposte il 19-09

- **D1.** `sorgente` come `regclass` (si rompe se la tabella viene rinominata:
  è un pregio, dice subito che il ramo è da rivedere) o `text` (inerte)? Propongo
  `regclass`.
  ✅ **`text`.** Il pregio attribuito a `regclass` non esiste: `regclass`
  memorizza l'**OID**, quindi **segue** una rinomina in silenzio (stampa il
  nome nuovo) e, se la tabella sparisce, stampa un **numero** senza nessun
  errore — il contrario di «dice subito che il ramo è da rivedere». In più un
  OID in un CSV di seed e nella gemella `storico` è un corpo estraneo. Il
  lavoro che si voleva da `regclass` lo fa il pgTAP, e lo fa meglio (test 6):
  `to_regclass(sorgente) IS NOT NULL` **e** la tabella è fra le dipendenze
  vive della vista (`pg_rewrite` → `pg_depend`). Una sorgente sostituita in
  un ramo o una tabella che non esiste più fanno rosso lì. Provato con due
  mutazioni (§8.3).
- **D2.** Il pgTAP legge `pg_get_viewdef` con una regex sui letterali
  `'…'::text AS registro`: è la forma con cui la vista è scritta oggi. Se il
  team DB preferisce, la vista può esporre i registri in un **commento
  strutturato** o in una `fn_giornale_registri()` `IMMUTABLE` usata dai rami
  stessi (`registro := 'EVENT_LOG'` → la funzione garantisce che sia a
  catalogo). Propongo la regex: non tocca la vista, e la vista è già stata
  riscritta due volte questo mese.
  ✅ **La regex**, con due cinture: un `CHECK` su `codice_interno`
  (`^[A-Z][A-Z0-9_]*$`) che tiene catalogo e regex sullo stesso alfabeto, e
  il **test 3** del pgTAP, che pretende almeno un letterale estratto — senza,
  una riscrittura della vista in una forma che la regex non legge renderebbe
  i due versi verdi su insiemi vuoti (verde per sottrazione). `pg_get_viewdef`
  stampa `'EVENT_LOG'::text AS registro` (verificato su dbdev il 19-09), e
  `riga_key` (`format('EVENT_LOG:%s'…)`) non collide col pattern.
- **D3 (non posta dal brief, decisa dal team DB): niente colonna `attivo`.**
  Il §4.1 la chiedeva «come ogni tabella config» e il §4.3 voleva un test
  «`attivo`/`obsoleto_dal` coerenti» senza dire cosa fosse coerente — segno
  che il flag non aveva una domanda sua. Per un registro non c'è: nessuno
  «assegna» un registro a una riga (lo decide la vista), le righe vecchie del
  diario devono restare leggibili anche a ramo ritirato, e il ritiro ha già il
  suo asse (`obsoleto_dal`, che è quello su cui i due versi del pgTAP
  ragionano). Un secondo flag sarebbe un «flag con due domande» — e le due
  sorelle che il brief chiama *stampo*, `tipi_entita` ed `eventi_dominio`,
  non ce l'hanno per lo stesso motivo. `fn_get_lookup_codici` tratta `attivo`
  come opzionale (`NULL::boolean AS attivo` se manca): il lookup generico
  funziona lo stesso, verificato dal test 7. Il pgTAP **pinna l'assenza**
  (test 2, `hasnt_column`).

## 7. Registro

| Data                    | Cosa                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                    |
| ----------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 2026-09-19              | Brief scritto. Backend in attesa; la tendina «Registro» del giornale resta sulla costante FE, dichiarata come seconda sede nel commento della view.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| 2026-09-19 (ore 18)     | ✅ **Lato DB CHIUSO**: migrazione applicata da Tid, automazioni montate (lock + audit), pgTAP 13/13 come app, suite senza regressioni. Resta il commit; poi il §5.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                       |
| 2026-09-19 (pomeriggio) | ✅ **Lato DB scritto** (Tid: «ok procedi»): `00_schema/config/20260919-08` (tabella), `80_data/changelog/20260919-09` + `sql/config/registri_giornale.csv` (seed, con resync della sequence), pgTAP `script/test-giornale-registri-catalogo-v1.sql` (13 test), i due presidi di `test-vw-giornale-entita.sql` che elencavano i quattro nomi (2, 11) **riscritti sul catalogo** — la quarta copia ritirata nello stesso giro —, descrizione della colonna `registro` in `ui/lista_colonna.csv` (887), manuale `config/manual/registri_giornale.md`, rimando nel manuale della vista. Tre risposte al §6 (D1 `text`, D2 regex + CHECK + test-guard, **D3 niente `attivo`**). Provato con l'SQL estratto (`updateSQL` offline) in `BEGIN…ROLLBACK`: 12/13 (il 13 è il lock di `ci_apply`), 13/13 col lock montato, mirror idempotente alla seconda passata, e **cinque mutazioni** che accendono l'asserzione giusta (§8.3). Per strada: il `check_i18n_keys.py` **non** legge `etichetta_key` (§4.2), le sorelle **non** sono «solo SELECT» (§4.4), e un INSERT senza `id` collideva con la PK del seed — da cui il resync nel `-09` e gli id espliciti nei test negativi. |

## 8. As-built DB (19-09-2026)

### 8.1 Che cosa c'è

| Pezzo                                     | File                                                                                                                                                                               |
| ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tabella                                   | `db/changelog/migrations_v2/00_schema/config/20260919-08-create-config-registri-giornale-mctit.yaml`                                                                               |
| Seed (mirror `loadUpdateData` + `setval`) | `80_data/changelog/20260919-09-seed-registri-giornale-mctit.yaml`, `80_data/sql/config/registri_giornale.csv`                                                                      |
| Presidio vista ⇄ catalogo                 | `db/pgtap/script/test-giornale-registri-catalogo-v1.sql` (plan 13)                                                                                                                 |
| Copie ritirate                            | `db/pgtap/script/test-vw-giornale-entita.sql` test 2 e 11 (ora leggono `config.registri_giornale`); `ui/lista_colonna.csv` riga 887 (la descrizione non elenca più i quattro nomi) |
| Doc                                       | `docs/it/dbzero/config/manual/registri_giornale.md` (nuovo), `docs/it/dbzero/script/manual/vw_giornale_entita.md` (colonna `registro` → catalogo)                                  |

Forma della tabella: `id bigint IDENTITY`, `codice_interno text` UNIQUE +
`CHECK ^[A-Z][A-Z0-9_]*$`, `codice text` UNIQUE non vuoto, `descrizione text
NOT NULL`, `etichetta_key text` `CHECK ^config\.registri_giornale\.[a-z][a-z0-9_]*$`,
`sorgente text` `CHECK schema.tabella`, `obsoleto_dal date NULL`, audit. Niente
`attivo`, niente `tx_id`, niente `meta`/`ordine`. Lock su `codice_interno` e
audit da `ci_apply` (o job pgAgent delle 21:00 su dev).

### 8.2 I tredici test, in una riga ciascuno

1-2 forma (colonne del contratto; **assenza** di `attivo`) · 3 la regex
legge almeno un letterale (guard del metro) · **4** ogni letterale della
vista è a catalogo e vivo · **5** ogni riga viva ha il suo ramo · **6** ogni
`sorgente` si risolve ed è dipendenza della vista · 7 il lookup generico
restituisce esattamente i vivi · 8 `etichetta_key` = namespace + codice
minuscolo · 9-11 i tre `CHECK` · 12 l'UNIQUE · 13 il lock (**`ci_apply`**).

### 8.3 Come è stato provato, e cosa ha trovato

✅ **Esito finale (Tid, 19-09 ore 18): migrazione applicata, automazioni
passate (`trg_registri_giornale_a10_lock_columns_upd` e
`…_audit_data_user_upd` montati), `test-giornale-registri-catalogo-v1`
13/13 come `zeroerp_app`, suite senza regressioni.** La prima corsa, prima
delle automazioni, dava 12/13 col test 13 rosso *per assenza* del lock —
esattamente come scritto nell'intestazione del file.

SQL **estratto** con `updateSQL --url=offline:postgresql` su copie senza
`preConditions`, poi `BEGIN; DDL; seed; corpo del pgTAP; ROLLBACK;` come owner
su dbdev. Base: 12/13, il 13 rosso *per assenza* del lock. Col lock montato a
mano come farebbe `ci_apply` (`trgfn_lock_columns('codice_interno',
'E_CODICE_NON_MODIFICABILE')`) e il mirror eseguito **due volte**: 13/13 — il
lock lascia passare l'`UPDATE` a valore uguale della seconda passata.
Mutazioni, ciascuna accende **solo** ciò che deve:

| Mutazione                                                             | Rosso                                                                                                                                                                                                         |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| riga a catalogo senza ramo (`PRATICHE_GIORNALE`, `pratiche.giornale`) | 5, 6                                                                                                                                                                                                          |
| `obsoleto_dal = oggi` su `EVENT_LOG` (ramo con riga ritirata)         | 4, 7                                                                                                                                                                                                          |
| `sorgente` di una tabella esistente ma non letta dalla vista          | 6                                                                                                                                                                                                             |
| `sorgente` inesistente                                                | 6                                                                                                                                                                                                             |
| `INSERT` senza `id` (prima del resync)                                | ⛔ `23505` sulla **PK**: gli id fissi del seed non avanzano la sequence. Da qui il `setval` nel `-09` e l'`id` esplicito (999999) nei test 9-12, che altrimenti sarebbero stati verdi per il vincolo sbagliato |

`test-vw-giornale-entita.sql` riprovato nella stessa transazione: 15/15.
Guardrail statici (runOnChange, precondition-seed, ddl-trigger, grant-batch,
letterali, preambolo pgTAP): tutti verdi. Il verde **come app** è stato preso
dopo l'apply con `scripts/testpgtap.sh` (vedi in testa a questa sezione).
⚠️ Numerazione: lo stesso giorno esiste anche `90_end/20260919-08-grant-app-select-job-run-log`
(cantiere privilegio job_run_log): due `-08` con id diversi, innocuo per
Liquibase ma fuori dalla convenzione NN globale per data. Non rinominati:
già in `databasechangelog`. Il prossimo numero libero del 19-09 è `-10`.

### 8.4 Cosa eredita il §5 (BE/FE), oltre a quanto già scritto

- **Il guard i18n non vede `etichetta_key`** (§4.2): scrivendo le otto chiavi
  (`config.registri_giornale.{event_log,lotto_log,task_run,fattura_log}`,
  it/en), insegnare a `scripts/check_i18n_keys.py` a leggere la colonna
  `etichetta_key` dei CSV di `80_data` — è la stessa classe di buco delle
  intestazioni di colonna (`etichetta_i18n_key`, 22-08), e `tipi_entita`
  ed `eventi_dominio` oggi passano solo perché qualcuno le ha scritte a mano.
- **Il lookup generico non porta `etichetta_key`** (`id, codice,
  codice_interno, descrizione, attivo, codice_stabile`): o il FE compone la
  chiave dal `codice_interno` con la convenzione (che il test 8 pinna), o
  `config.registri_giornale` entra in `_LOOKUP_SPECIALIZZATE` con
  `etichetta_key` come colonna extra — è esattamente il caso «una colonna in
  più» per cui la variante esiste (api.md §Lookup). La seconda è la forma
  giusta: la chiave la dichiara il DB, il FE non la ricostruisce.
- `attivo` nel payload del lookup arriva **`NULL`** (la colonna non c'è): un
  consumatore che filtrasse `attivo === true` lato FE non vedrebbe niente.
- `GIORNALE_REGISTRI`: la scelta fra «pinnata al catalogo con un test su DB
  provvisto» e «letta dal catalogo» resta al BE (§5); il DB non ha
  preferenze, ma con `obsoleto_dal` il filtro dovrebbe accettare **anche** i
  registri ritirati (le righe vecchie si leggono), cioè `codice_interno` di
  tutte le righe, non dei soli vivi.
