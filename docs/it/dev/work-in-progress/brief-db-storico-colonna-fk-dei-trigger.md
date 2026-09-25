# Brief DB — lo storico che non si chiude: la colonna FK che il trigger cerca e non trova

> **Perimetro:** DB (`dev/db-tid`). Nessuna ricaduta su BE né FE (§6).
> **Aperto:** 2026-09-25.
> **Origine:** trovato strada facendo in
> [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md)
> §11.5: un pgTAP modificava un parametro storicizzato e, sullo scratch, moriva
> con `E_SNAPSHOT_CLOSE_ERROR`.
>
> **Stato:** 🟡 **analisi chiusa, niente scritto.** Una decisione per Tid in §4.
>
> **In una riga.** Il trigger di storico riceve il nome della colonna che lega la
> riga storica alla madre; su **cinque** tabelle quel nome non esiste nella
> gemella in `storico`, e ogni UPDATE o DELETE di una riga con `storicizza = true`
> muore. Su dbdev ne sono rotte quattro, sul database ricostruito da zero cinque.

---

## 1. Il difetto, sul modello

`script.trgfn_storico_generic` è una funzione di trigger **generica**: il nome
della colonna FK nella tabella storica non lo conosce, lo riceve in `TG_ARGV[0]`.
Nel ramo di chiusura (sezione 3 del corpo) lo usa così:

```text
UPDATE storico.<tab> SET valid_to = … WHERE <TG_ARGV[0]> = <id> AND valid_to IS NULL
```

Se quella colonna non c'è, l'`EXECUTE` fallisce e il trigger solleva
`E_SNAPSHOT_CLOSE_ERROR`: la scrittura sulla madre viene respinta.

L'argomento lo calcola `dbops.fn_run_automations_storico`:

```text
fk_col := fn_get_override_col(schema, tabella, 'STORICO_FK', tabella || '_id')
```

cioè **«nome tabella + `_id`»**, salvo eccezione dichiarata in
`80_data/sql/dbops/automation_overrides_cols.csv`. È lo stesso nome con cui
`dbops.fn_ensure_storico_table` crea una gemella **quando manca**.

⇒ Il contratto è: *la gemella ha la colonna `<tabella>_id`, oppure l'eccezione è
scritta nel registro.* Le tabelle storiche nate a mano nel 2025 (`migrations/`,
non `migrations_v2/`) usano il **singolare** (`parameter_id`, `indirizzo_id`, …).
Tre sono state dichiarate (`clienti`, `soggetti`, `parameter_overrides`); cinque no.

⚠️ **Due proprietà rendono il difetto invisibile:**

1. **Nessun controllo fra argomento e colonna.** L'automazione monta il trigger
   senza verificare che la colonna esista nella gemella; il trigger lo scopre solo
   alla prima chiusura di uno snapshot.
2. **Il cancello `storicizza`.** Il trigger esce subito sulle righe con
   `storicizza = false`. Il difetto scatta solo su una riga storicizzata, cioè
   proprio sulle righe per cui lo storico esiste.

## 2. Chi crea che cosa, su un database da zero

La catena si legge dai changelog, non da dbdev:

* `changelog-master-v2.yaml` → `include: changelog-master.yaml` →
  `includeAll: migrations`: **il vecchio albero gira ancora** su ogni
  installazione nuova.
* `migrations/00_bootstrap/20250729-11-create-seq-and-table-storico_parameters-mctit.yml`
  crea `storico.parameters` con `parameter_id` (e una FK che
  `20250827-02-storico-drop-legacy-fk` toglie poco dopo, insieme a tutte le FK
  dello schema `storico`).
* Le automazioni trovano la gemella già fatta, `fn_ensure_storico_table` esce
  senza toccarla, e `fn_run_automations_storico` monta il trigger con il nome di
  default.

Stessa storia per le altre quattro. Per `catasto_unita_immobiliari` la colonna
è stata **rinominata** dal `20251212-02` (`dato_catastale_id` →
`catasto_unita_immobiliare_id`, al singolare), ma senza dichiarare l'eccezione.

### Perché dbdev ha `parameters_id` (fuori modello)

Su dbdev il changeSet del 2025 risulta `EXECUTED` il 2025-09-14, eppure la colonna
è `parameters_id`. Tre indizi dicono che la tabella è stata **cancellata a mano e
ricreata** dal provisioning:

* l'oid di `storico.parameters` è molto più alto di quello delle gemelle del 2025;
* l'ordine delle colonne è quello di `fn_ensure_storico_table`;
* nessun changeSet, né attivo né nella storia git, fa un `DROP` di quella tabella,
  e `fn_ensure_storico_table` crea soltanto.

⇒ Per `parameters` è **dbdev** a essere fuori modello, non la CI. Stessa forma del
§7 di [brief-db-codici-ritirati-negli-argomenti-dei-trigger.md](brief-db-codici-ritirati-negli-argomenti-dei-trigger.md).

## 3. La fotografia (2026-09-25 — fatto datato, non un motivo)

Controllo generale: per ogni trigger montato su `trgfn_storico_generic`,
l'argomento è una colonna della gemella?

| Madre | Argomento del trigger | Colonna reale | dbdev | `zeroerp_ci` |
| --- | --- | --- | --- | --- |
| `config.parameters` | `parameters_id` | `parameter_id` | ✅ (ricreata a mano) | ❌ |
| `anagrafiche.catasto_unita_immobiliari` | `catasto_unita_immobiliari_id` | `catasto_unita_immobiliare_id` | ❌ | ❌ |
| `anagrafiche.indirizzi` | `indirizzi_id` | `indirizzo_id` | ❌ | ❌ |
| `anagrafiche.indirizzi_dettaglio` | `indirizzi_dettaglio_id` | `indirizzo_dettaglio_id` | ❌ | ❌ |
| `config.comuni` | `comuni_id` | `comune_id` | ❌ | ❌ |

Tutte e cinque hanno la colonna `storicizza`. Prova su dbdev, `UPDATE … SET
storicizza = storicizza` su un'unità catastale storicizzata, in transazione
annullata:

```text
ERRORE: Errore chiusura snapshot: la colonna "catasto_unita_immobiliari_id" non esiste (SQLSTATE: 42703)
```

⚠️ Quante righe siano storicizzate oggi non conta: una riga storicizzata su una
di queste tabelle basta a rompere la scrittura, e il modello la ammette su tutte e
cinque.

⚠️ **Nessun pgTAP lo vede**: nessuno modifica una riga storicizzata di queste
tabelle. `anagrafiche/test-catasto-unita-immobiliare.sql` legge la gemella
«se c'è» dentro un `lives_ok`, e dichiara nel commento di non conoscere la colonna.

## 4. Le due strade, e quella consigliata

### A. ⭐ Consigliata: la gemella prende il nome di default

Un changeSet per tabella in `00_schema/storico/` rinomina la colonna al nome che il
generatore si aspetta (`parameters_id`, `catasto_unita_immobiliari_id`,
`indirizzi_id`, `indirizzi_dettaglio_id`, `comuni_id`).

Perché è la strada giusta, sul modello:

* **Il trigger resta com'è.** È già montato con il nome giusto su entrambi i
  database: basta che la colonna esista. Nessun DDL su un trigger generato da
  `ci_apply` (linee-guida-sql §11.5).
* **Nessun buco di ordine.** La rinomina gira in `00_schema`, **prima** di
  `80_data`: gli upsert di `80_data` su `config.parameters` trovano già uno
  storico che funziona.
* **Un'eccezione in meno.** Una gemella con il nome di default non ha bisogno di
  una riga nel registro: si allinea al contratto del generatore invece di
  aggiungere un caso speciale.

Forma di ciascun changeSet: fa **una cosa sola**, con precondizione `MARK_RAN`
«la colonna vecchia c'è e la nuova no». Su dbdev `parameters` viene saltato
(ha già il nome nuovo); sugli altri quattro e su `zeroerp_ci` rinomina.

### B. L'eccezione nel registro (`STORICO_FK` in `automation_overrides_cols.csv`)

È il meccanismo già usato per `clienti`, `soggetti`, `parameter_overrides`. Qui
però ha tre problemi:

1. **Il CSV da solo non muove nessun trigger**: l'automazione crea solo se il
   trigger manca. Servirebbe un `DROP` e una rigenerazione in `90_end`, come il
   `20260923-02` per i lock.
2. **Ordine**: il CSV si carica in `80_data`, la rigenerazione gira in `90_end`.
   In mezzo, ogni upsert di `80_data` su una riga storicizzata di queste tabelle
   muore ancora.
3. **Per `parameters`** dbdev andrebbe comunque riallineato, con una rinomina
   inversa, visto che la sua colonna è `parameters_id`.

⇒ **Decisione per Tid: A o B.** Il resto del brief è scritto per A.

## 5. Che cosa entra (strada A)

### 5.1 Le cinque rinomine — `00_schema/storico/`

Un file e un changeSet per tabella (linee-guida-sql §11.5: *uno per oggetto*).

* **Precondizione**: `onFail: MARK_RAN`; `sqlCheck` = 1 se la colonna vecchia
  esiste **e** la nuova no.
  ⚠️ Se esistessero entrambe, il changeSet salterebbe in silenzio: quel caso lo
  prende il presidio di §5.3, non il migrate.
* **Corpo**: `ALTER TABLE storico.<tab> RENAME COLUMN <vecchia> TO <nuova>`.
  ⚠️ In PostgreSQL 18 il `NOT NULL` è un vincolo con un nome
  (`parameters_parameter_id_not_null`), che la rinomina della colonna **non
  segue**. Lo stesso vale per gli indici (`ix_storico_parameters_param_id`).
  Da decidere nel giro di scrittura se rinominarli nello stesso `DO`, con
  `IF EXISTS`, così che dbdev e un DB da zero abbiano gli stessi nomi.
* Aggiornare il `COMMENT ON COLUMN` dove nomina la colonna vecchia (il
  `20251212-02` ne scrive uno su `catasto_unita_immobiliare_id`).

⛔ Il changeSet del 2025 **non si modifica** (è mergiato: si romperebbe il
checksum).

### 5.2 ⭐ Il rubinetto — `dbops.fn_run_automations_storico`

Prima di montare un trigger, l'automazione verifica che `fk_col` sia una colonna
della gemella. Se non lo è, **solleva** con un codice nuovo
(`E_STORICO_FK_COL_NOT_FOUND`, classe `TECNICO`), invece di montare un trigger
destinato a morire alla prima chiusura.

È il punto in cui il difetto si sarebbe fermato **alla nascita**, per tutte e
cinque le tabelle. Corpo dalla doc auto-generata, non da uno YAML.

### 5.3 Il presidio sullo stato — pgTAP in `db/pgtap/dbops/`

Invariante strutturale: *per ogni trigger su `trgfn_storico_generic`,
`TG_ARGV[0]` è una colonna della gemella in `storico`.*

Non ripete il 5.2, risponde a un'altra domanda: il 5.2 guarda un trigger **mentre
nasce**, questo guarda i trigger **che ci sono**, compresi quelli nati prima del
rubinetto e le gemelle ricreate a mano, come è successo su dbdev.

⚠️ Gira dopo `ci_apply`, quando i trigger esistono. Su un DB senza trigger di
storico non avrebbe niente da verificare: va scritto con un `ok()` che pretende
**almeno un** trigger di storico, per non essere verde a vuoto.

### 5.4 Una prova che il difetto non torni — pgTAP

Per ognuna delle cinque madri: una riga con `storicizza = true`, un `UPDATE`,
e `lives_ok` più la presenza di uno snapshot chiuso (`valid_to` valorizzata) nella
gemella. La riga si **fabbrica**, non si pesca fra quelle esistenti (AGENTS.md,
corollario sui test).

## 6. Chi legge quelle colonne (censito il 2026-09-25)

* **Funzioni**: nessuna nomina `storico.<tab>` di queste cinque in chiaro.
  I lettori dinamici risolvono la colonna dallo stesso calcolo del generatore:
  `fn_storico_risolvi_scope` usa `fn_get_override_col(… 'STORICO_FK', tabella||'_id')`
  e `script.fn_get_snapshot_as_of` riceve la colonna dal chiamante.
  ⇒ Con la strada A si **allineano**, non si rompono.
* **Viste**: nessuna dipende da queste cinque gemelle.
* **`dbops.audit_sources`**: non le registra.
* **Backend / frontend**: nessun riferimento.
* **pgTAP**: `anagrafiche/test-catasto-unita-immobiliare.sql` legge la gemella
  senza nominare la colonna. `dbops/test-nessun-timestamp-senza-fuso-v1.sql` la
  cita solo in un commento.

## 7. Ricadute su altri brief

* [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md)
  §11.5 rimanda qui.
* `80_data/changelog/20260925-20-upsert-parameters-login` fa nascere i parametri
  di login con `storicizza = false`, e nell'intestazione cita questo difetto come
  seconda ragione. La prima ragione (coerenza con i due parametri fratelli) resta
  valida; la seconda cade quando questo brief è applicato. Da riallineare in quel
  brief, non qui.

## 8. Come si prova, e che cosa non prova

* SQL **estratto** dai changeSet, in `BEGIN … ROLLBACK`, da owner: su
  `zeroerp_ci` le cinque rinomine e poi un `UPDATE` di una riga storicizzata per
  tabella, che deve passare; su dbdev lo stesso, con `parameters` saltato.
* Prova per mutazione del 5.2: con l'eccezione `STORICO_FK` di `clienti` tolta
  nella transazione, il rubinetto deve sollevare nominando `anagrafiche.clienti`.
* ⛔ Non prova il comportamento come applicazione: l'harness gira da owner. I pgTAP
  li lancia Tid dopo l'apply.

## Registro

| Data | Area | Cosa |
| --- | --- | --- |
| 2026-09-25 | DB | Aperto. Creatore di `storico.parameters` su DB da zero trovato (albero `migrations/`, ancora incluso). dbdev fuori modello (DROP manuale). Censimento: 5 madri con argomento e colonna disallineati, 4 anche su dbdev. Strada A consigliata. |
