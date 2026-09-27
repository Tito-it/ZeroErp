# Brief DB — lo storico che non si chiude: la colonna FK che il trigger cerca e non trova

> **Perimetro:** DB (`dev/db-tid`). Nessuna ricaduta su BE né FE (§6), salvo la
> nota sui codici errore (§10).
> **Aperto:** 2026-09-25.
> **Origine:** trovato strada facendo in
> [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md)
> §11.5: un pgTAP modificava un parametro storicizzato e, sullo scratch, moriva
> con `E_SNAPSHOT_CLOSE_ERROR`.
>
> **Stato:** ✅ **CHIUSO il 2026-09-25 — applicato** su dbdev e su
> `zeroerp_ci` (`20260925-26`, `-27` `EXECUTED`). Verificato dopo l'apply sul
> catalogo vivo di entrambi: **nessun** trigger di storico cerca una colonna che
> la gemella non ha, il codice `E_STORICO_FK_COL_ASSENTE` è a catalogo, il
> rubinetto è nel corpo vivo, il pgTAP owner non ha lasciato residui (§11).
> pgTAP: ✅ **entrambi verdi su `zeroerp_ci`** (il secondo dopo la correzione
> della fixture, §11). Restano fuori, e non
> tengono aperto questo brief: la nota al backend (§10, ✅ chiusa dal backend
> il 2026-09-25) e l'indice sulla colonna FK delle gemelle, da aprire in un
> brief suo (§9).
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
⚠️ *Cambiato in scrittura: un changeSet solo con un `DO` sul catalogo vivo, non
cinque `MARK_RAN` — il perché in §5.1.*

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

✅ **Decisione di Tid del 2026-09-25: strada A.**

## 5. Che cosa è entrato (strada A)

| File | Cosa |
| --- | --- |
| `00_schema/storico/20260925-26-rename-storico-colonna-fk-al-nome-dell-automazione` | le cinque rinomine (§5.1) |
| `20_code/dbops/20260925-27-update-fn-run-automations-storico-verifica-colonna-fk` | il rubinetto (§5.2) |
| `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | `E_STORICO_FK_COL_ASSENTE`, `TECNICO`, id 1127 |
| `db/pgtap/dbops/test-storico-colonna-fk-dei-trigger-v1.sql` | invariante + comportamento, come applicazione (§5.3) |
| `db/pgtap/dbops/test-storico-automazione-colonna-fk-v1.sql` | il rubinetto, `pgtap-runner: owner` (§5.4) |
| `docs/it/dbzero/dbops/manual/fn_run_automations_storico.md`; `storico/manual/parameters.md`, `indirizzi.md`, `comuni.md` | il controllo nuovo; i nomi di colonna; tolta la FK descritta e che non esiste più dal `20250827-02` |

### 5.1 Le cinque rinomine — un changeSet solo, sul catalogo vivo

⚠️ **Cambiato rispetto al disegno** (che diceva «un changeSet per tabella con
`MARK_RAN`»): è **un** changeSet con un `DO` che scorre le cinque gemelle e legge
il catalogo vivo per ciascuna. Il perché:

* dbdev e un DB da zero partono da stati **diversi** (su dbdev `parameters` è già
  a posto): una `preCondition` `MARK_RAN` avrebbe saltato anche la parte che
  vale per tutti (nomi di vincolo e indice, commento);
* il caso «ci sono **entrambe** le colonne» con `MARK_RAN` sarebbe passato in
  silenzio. Qui **solleva**, e nomina tabella e colonne;
* cinque `DO` identici sarebbero cinque copie della stessa logica.

Per ciascuna gemella: se manca → niente (la creerà il provisioning, già col nome
giusto); vecchia sì e nuova no → `RENAME COLUMN`; nuova già presente → niente;
entrambe o nessuna → **solleva**. Poi, sempre:

* il `NOT NULL` (in PostgreSQL 18 ha un nome e la rinomina non lo segue) prende il
  nome `<tab>_<col>_not_null`. Oggi dbdev e CI lo chiamano in due modi diversi su
  `indirizzi_dettaglio`;
* l'indice monocolonna sulla FK, dove c'è, prende il nome `ix_<tab>_<col>_fk`,
  quello di `fn_ensure_storico_table` (`ix_storico_parameters_param_id` sulla CI);
* un `COMMENT ON COLUMN` uguale per le cinque, che dice perché quel nome.

Il nome di arrivo è il default del generatore (`<tabella>_id`), **non** una
chiamata a `fn_get_override_col`: siamo in `00_schema`, e il registro delle
eccezioni è un seed di `80_data` (§11.4).

⛔ Il changeSet del 2025 **non si modifica** (è mergiato: si romperebbe il
checksum).

### 5.2 ⭐ Il rubinetto — `dbops.fn_run_automations_storico`

Prima di montare un trigger, l'automazione verifica che `fk_col` sia una colonna
della gemella. Se non lo è, solleva `E_STORICO_FK_COL_ASSENTE` (classe `TECNICO`).
Il blocco sta **fuori** dal `BEGIN … EXCEPTION` del `CREATE TRIGGER`, che lo
ribattezzerebbe `E_STORICO_UD`, e vale **anche in dry run**: un «verrebbe creato»
su un trigger rotto è una risposta sbagliata.

* ⚠️ Il nome **non** è `…_NOT_FOUND`, come avevo scritto nel disegno: il catalogo
  avverte (su `E_STORICO_PARENT_PK_NOT_FOUND`) che quel suffisso si legge come un
  404, e qui non manca un record.
* ⚠️ `dbops.fn_run_automations` non cattura: se il rubinetto solleva, `ci_apply`
  si ferma. È voluto: è un difetto di struttura, e un `ci_apply` verde con un
  trigger rotto è la forma in cui questo difetto è rimasto nascosto.
* Corpo preso da `pg_proc`, identico alla doc auto-generata il 2026-09-25; unica
  differenza il blocco nuovo, più una riga nella documentazione interna e il
  `COMMENT ON FUNCTION`.

### 5.3 Il presidio sullo stato — `test-storico-colonna-fk-dei-trigger-v1` (plan 16)

* **1-2** — l'invariante: *per ogni trigger su `trgfn_storico_generic`,
  `TG_ARGV[0]` è una colonna della gemella.* Il test 1 pretende almeno un trigger
  (il 2 non è verde a vuoto). Guarda i trigger **che ci sono**, compresi quelli
  nati prima del rubinetto e le gemelle ricreate a mano: è l'altra domanda
  rispetto al 5.2.
* **3-12** — per le cinque gemelle, il nome nuovo c'è e quello vecchio **no**:
  se restassero entrambe, il test 2 sarebbe verde e due colonne direbbero la
  stessa cosa.
* **13-16** — il comportamento su `config.parameters`, con due righe
  **costruite** con `storicizza = true` (due e non una: dopo il primo UPDATE il
  reset può riportare il flag a false). UPDATE e DELETE vivono, e lo snapshot è
  nella gemella legato per `parameters_id`.

Gira come applicazione: `config.parameters` la scrive il pannello di
amministrazione, ed è il percorso che moriva.

### 5.4 Il rubinetto alla prova — `test-storico-automazione-colonna-fk-v1` (plan 7, owner)

Una madre `config.pgtap_sto_fk` e una gemella (copia della forma di
`storico.parameters`) con la colonna FK chiamata `pgtap_sto_fk_rif`:
l'automazione solleva `P0001` con la frase del catalogo, anche in dry run.
Rinominata la colonna a `pgtap_sto_fk_id`, il trigger nasce con quell'argomento,
e l'UPDATE di una riga storicizzata vive e scrive lo snapshot.

Marcato `pgtap-runner: owner`: fa DDL (prima forma ammessa in `scripts/testpgtap.sh`).

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

* **Trovato prima, il 2026-09-23**, da
  [brief-db-fixture-che-costruiscono-giro-2.md](brief-db-fixture-che-costruiscono-giro-2.md)
  §10 punto 2 e da
  [migliorie-generali-da-test-valutazione.md](../work-in-progress/migliorie-generali-da-test-valutazione.md)
  (Lotto 1): solo `parameters`, e le altre quattro scartate come falsi positivi
  perché provate su righe non storicizzate. Entrambi ora rimandano qui.
* **Il registro dei rossi**: `config/test-parameter-fk-surrogate-dispatch-v1.sql`
  era in `baseline-rossi-scratch.tsv` e `baseline-rossi-ci.tsv` come `ASSERZIONE`
  per questo difetto. ✅ Verde su `zeroerp_ci` (Tid, 2026-09-25) → tolto dal
  registro dello **scratch**. ⏳ Dal registro della **CI** (GitHub) no: quello
  lo scrive la CI dal log di una corsa vera (`pgtap-baseline-ci-rientrati.sh`),
  e `zeroerp_ci` è lo scratch, non la CI (intestazione di
  `scripts/pgtap-baseline.sh`). Esce alla prima corsa CI dopo la push.
  Stesso esito per il gemello `config/test-parameter-fk-surrogate-vuoto-v1.sql`
  (giro 2, §10 punto 2): ✅ verde, tolto dallo scratch, in attesa della CI.

## 8. Come è stato provato, e che cosa NON prova

⚠️ **Non ho potuto provare da owner**: la password di `titodb` non è in
`~/.pgpass`, e il servizio `zeroerp_log` viene rifiutato. Tutto quello che segue
gira come `zeroerp_app`, in `BEGIN … ROLLBACK`.

* **Comportamento (test 13-16, SQL estratto)**: su dbdev, dove `parameters` è
  già a posto, **4 ok**. ⭐ **Controprova** su `zeroerp_ci`, ancora rotta: il test
  13 è **rosso** con `la colonna "parameters_id" non esiste … E_SNAPSHOT_CLOSE_ERROR`.
  Il test vede il difetto, non passa a vuoto.
* **Il DO del 20260925-26**: estratto e fatto girare su **copie temporanee**
  delle cinque gemelle (`CREATE TEMP TABLE … (LIKE storico.<tab> INCLUDING ALL)`,
  con `storico.` sostituito da `pg_temp.` **solo** nella prova), su entrambi i DB:
  * `zeroerp_ci`: cinque rinomine; dbdev: quattro, `parameters` saltata;
  * NOT NULL e indice ai nomi attesi, commento su tutte e cinque;
  * **idempotente**: la seconda passata dice «niente da rinominare» per tutte;
  * **mutazione**: aggiunta la colonna vecchia accanto alla nuova su `comuni`,
    il DO solleva nominandole.
  ⚠️ È una prova della **logica**, non del changeSet: le copie non sono le
  tabelle, e l'`ALTER` vero lo può fare solo l'owner.
* **La funzione del 20260925-27**: copia in `pg_temp`, `plpgsql_check_function`
  pulita (un solo avviso, `rel` non usata, che c'era già nel corpo vivo), e un
  dry run su `config` e `anagrafiche` che passa su entrambi i DB. ⚠️ Il ramo
  nuovo **non** è stato esercitato: serve una gemella senza trigger, cioè DDL in
  `storico`. Lo esercita il pgTAP owner del §5.4.
* Guardrail statici verdi: preambolo pgTAP, DDL su trigger generati,
  `runOnChange`. CSV: id 1127 unico, il messaggio si formatta con tre valori.

⛔ **Non prova**: l'SQL estratto da owner sulle tabelle vere, l'apply da zero
(`zeroerp_ci`), i due pgTAP interi. Li lancia Tid.

## 9. Cosa resta

* ✅ **Tid**: apply su dbdev e `zeroerp_ci` (2026-09-25). ⏳ I due pgTAP: prima
  dell'apply il test 2 del primo file era rosso su cinque madri in CI e su
  quattro su dbdev; dopo l'apply il controllo equivalente, letto sul catalogo,
  è vuoto su entrambi (§11).
* ✅ **Backend**: la nota del §10, chiusa il 2026-09-25 (vedi lì).
* 🔵 **L'indice sulla colonna FK delle gemelle: nessuna automazione lo fa
  (verificato il 2026-09-25).** La chiusura dello snapshot
  (`WHERE <fk> = … AND valid_to IS NULL`) gira a ogni UPDATE/DELETE della madre,
  e senza indice legge tutta la gemella.
  * `STORICO_PROVISION` (`fn_ensure_storico_table`) crea `ix_<tab>_<fk>_fk`
    **solo quando crea la gemella**: se la gemella esiste esce subito, e non
    converge mai;
  * la policy degli indici FK (`dbops.apply_fk_index_policy`,
    `vw_fk_senza_indice`) parte da `pg_constraint`, cioè dai vincoli FK veri. Le
    gemelle non ne hanno (li ha tolti `20250827-02`): per lei non esistono.
  * ⇒ Le gemelle nate fuori dal provisioning restano senza. Letto su dbdev,
    fatto datato: `clienti.cliente_id`, `dati_societari.dati_societari_id` e,
    dopo il `20260925-26`, `comuni`, `indirizzi`, `indirizzi_dettaglio`,
    `catasto_unita_immobiliari`.
  * ➜ **Fuori da questo brief, da aprire in un brief suo** (deciso il
    2026-09-25): è un tema di prestazioni, non il difetto chiuso qui.
  * **Proposta**: il provisioning dello storico **converge** anche su una gemella
    che esiste già. Se nessun indice ha in testa la colonna FK (stesso calcolo
    del trigger, override compreso), lo crea con il nome `ix_<tab>_<fk>_fk`. È la
    sede giusta: la struttura della gemella è sua, e la colonna FK la conosce già.
    Un changeSet che crea sei indici a mano sarebbe una seconda sede, e la
    prossima gemella fatta fuori dal provisioning ricadrebbe nello stesso buco.
  * Resta fuori, come altra domanda: `storico.comuni` e `storico.indirizzi`
    non hanno il `NOT NULL` sulla colonna FK, che il provisioning dà a ogni
    gemella nuova.

## 10. Nota per il backend — codici errore da riallineare

> **Per**: team backend (`dev/backend-tid`). **Quando**: dopo l'apply dei
> changeSet del 2026-09-25 (questo brief e
> [brief-db-blocco-login-per-credenziale.md](brief-db-blocco-login-per-credenziale.md)).

Il catalogo dei codici errore ha **8 codici nuovi** che i due file del backend
non portano ancora. Dopo l'apply su dbdev, `test_error_policies_divergenza_db`
diventa **rosso** finché non si rigenera: è il presidio che fa il suo lavoro,
non una regressione.

✅ **Fatto dal backend il 2026-09-25.** Cinque degli otto codici (`E_CREDENZIALE_BLOCCATA`,
`E_LOGIN_ATTESA`, `E_CREDENZIALE_NON_TROVATA`, `E_CREDENZIALE_MOTIVO_OBBLIGATORIO`,
`E_AUTH_CHIAMATA_NON_VALIDA`) erano già registrati da `ea58bec4c`. Registrati
ora gli altri tre, con policy rigenerata e ripiego senza segnaposto:
`E_CREDENZIALE_GIA_OPERATORE`, `E_CREDENZIALE_EMAIL_AMBIGUA`,
`E_STORICO_FK_COL_ASSENTE`. Prima di rigenerare ho verificato che i tre codici
fossero nel CSV in git. Diff del generato: tre voci nuove, **zero classi
cambiate**; `genera_error_policies --check` allineato. I cancelli con
`ZEROERP_TEST_DB_E2E=1` sono verdi, e verde anche la suite intera (5131).
⚠️ Il test `test_error_policies_divergenza_db` citato sopra non esiste con
quel nome: la divergenza col DB la presidia `genera_error_policies --check`.

**Cosa fare:**

1. `manage.py genera_error_policies` → rigenera `error_policies_generated.py`
   dalla vista `config.vw_codici_errore_identita`, e si committa.
2. In `error_messages_fallback.py`, **a mano**, un messaggio di ripiego **senza
   segnaposto** per ciascuno degli 8 codici. Lo pretende
   `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`.

| Codice | Classe | Messaggio a catalogo | Cantiere |
| --- | --- | --- | --- |
| `E_CREDENZIALE_BLOCCATA` | `NON_PERMESSO` | Accesso bloccato dall'amministratore. | login |
| `E_LOGIN_ATTESA` | `NON_PERMESSO` | Troppi tentativi non riusciti: riprovare fra %s secondi. | login |
| `E_CREDENZIALE_NON_TROVATA` | `NON_TROVATO` | Credenziale non trovata. | login |
| `E_CREDENZIALE_MOTIVO_OBBLIGATORIO` | `DATO_ERRATO` | Indicare il motivo del blocco. | login |
| `E_CREDENZIALE_GIA_OPERATORE` | `CONFLITTO_STATO` | L'email %s appartiene gia' a un operatore. | login |
| `E_CREDENZIALE_EMAIL_AMBIGUA` | `TECNICO` | Piu' accessi registrati con la stessa email. | login |
| `E_AUTH_CHIAMATA_NON_VALIDA` | `TECNICO` | Chiamata non valida a %s: %s. | login |
| `E_STORICO_FK_COL_ASSENTE` | `TECNICO` | Automazione di storico: la colonna %s non esiste in %s, … | storico (questo brief) |

⚠️ **Tre punti che contano:**

* **`E_LOGIN_ATTESA` e `E_CREDENZIALE_BLOCCATA` sono 403, non 429**, per scelta
  del DB: il login del frontend intercetta il 429 prima di leggere il codice
  (è il throttle per IP), e perderebbe i secondi d'attesa. La classe
  `NON_PERMESSO` lo dà già: basta non aggiungere un override di status.
* **Il ripiego dei codici con `%s` non contiene il segnaposto.** Per esempio
  `E_LOGIN_ATTESA` → «Troppi tentativi non riusciti: riprovare fra qualche
  secondo.» I secondi veri arrivano nel messaggio del DB e anche nel contesto
  (`secondi_rimanenti`).
* **`E_STORICO_FK_COL_ASSENTE` non arriva mai a una richiesta HTTP**: lo solleva
  solo l'automazione dello storico, durante `ci_apply`. Va nei due file solo
  perché i presidi li vogliono completi. Un ripiego generico da `TECNICO` basta.

## 11. Dopo l'apply (2026-09-25)

Letto come applicazione sul catalogo vivo di dbdev e di `zeroerp_ci`:

| Controllo | dbdev | `zeroerp_ci` |
| --- | --- | --- |
| `20260925-26`, `-27` in `databasechangelog` | `EXECUTED` 09:56 | `EXECUTED` 09:58 |
| trigger di storico con un argomento che non è una colonna della gemella | nessuno (prima 4) | nessuno (prima 5) |
| `E_STORICO_FK_COL_ASSENTE` in `codici_errore` e `messaggi_errore` | sì | sì |
| il rubinetto nel corpo vivo di `fn_run_automations_storico` | sì | sì |
| residui del pgTAP owner (`pgtap_sto_fk`, tabella o trigger) | nessuno | nessuno |

### I pgTAP (corsa di Tid, 2026-09-25, `zeroerp_ci`)

* `test-storico-colonna-fk-dei-trigger-v1`: ✅ **verde**.
* `test-storico-automazione-colonna-fk-v1` (owner): **5/7**, rossi il 6 e il 7.
  Il rubinetto (1-5) funziona. Il rosso era **nella fixture**: lo snapshot
  moriva con `null value in column "id"` sulla gemella di prova.
  * Causa: la gemella di prova è copiata con `LIKE storico.parameters`, e
    **`storico.parameters.id` ha due forme**: su dbdev è un default
    `nextval(...)`, su `zeroerp_ci` una colonna `IDENTITY`. `INCLUDING DEFAULTS`
    copia solo la prima.
  * ✅ Corretto con `INCLUDING IDENTITY`. Provato su entrambi i DB con una
    tabella temporanea: l'INSERT senza `id` riceve un valore. ✅ **Rilanciato
    da Tid su `zeroerp_ci`: 7/7 verde.**
  * ℹ️ **La divergenza di `id` non si sana: non è un difetto.** Nello schema
    `storico` convivono per costruzione due forme di `id`: `IDENTITY` sulle
    gemelle del 2025 (convertite da `20250829-02-migrazione_pk_da_nextval_a_identity`)
    e `BIGSERIAL` su quelle del provisioning, cioè la forma di oggi. Fatto
    datato (2026-09-25): 11/106 su dbdev, 12/105 su `zeroerp_ci`. L'unica
    differenza fra le macchine è `parameters`: ricreata a mano su dbdev (§2), è
    passata dal gruppo del 2025 a quello del provisioning. Entrambe generano
    l'`id` e nessun lettore dipende dalla forma. Ha pesato solo sulla copia con
    `LIKE` della fixture, corretta. ✅ **Decisione di Tid del 2026-09-25: non si sana, si lascia com'è.**

## Registro

| Data | Area | Cosa |
| --- | --- | --- |
| 2026-09-25 | DB | Aperto. Creatore di `storico.parameters` su DB da zero trovato (albero `migrations/`, ancora incluso). dbdev fuori modello (DROP manuale). Censimento: 5 madri con argomento e colonna disallineati, 4 anche su dbdev. Strada A consigliata. |
| 2026-09-25 | DB | Tid sceglie la strada A. Scritti `20260925-26` (rinomine, un DO sul catalogo vivo) e `-27` (rubinetto `E_STORICO_FK_COL_ASSENTE`), codice nel catalogo, due pgTAP, doc. Provato come app (§8); owner, apply e pgTAP a Tid. |
| 2026-09-25 | Tid / DB | Applicato su dbdev e `zeroerp_ci`. Verifica sul catalogo vivo (§11): invariante pulita su entrambi. Brief chiuso lato DB; indice sulle gemelle spostato a un brief suo. |
| 2026-09-25 | Tid | pgTAP verdi su `zeroerp_ci`: `test-storico-colonna-fk-dei-trigger-v1` e, corretta la fixture (`INCLUDING IDENTITY`), `test-storico-automazione-colonna-fk-v1` 7/7. |
| 2026-09-25 | Tid | Brief chiuso. La doppia forma di `storico.*.id` (`IDENTITY` / `BIGSERIAL`) non si sana (§11). Restano fuori il push del backend (§10) e l'indice sulle gemelle (brief suo, §9). |
| 2026-09-25 | backend | §10 chiuso: registrati `E_CREDENZIALE_GIA_OPERATORE`, `E_CREDENZIALE_EMAIL_AMBIGUA`, `E_STORICO_FK_COL_ASSENTE` (policy rigenerata, ripiego); gli altri cinque c'erano già |
