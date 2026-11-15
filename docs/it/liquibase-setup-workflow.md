# Liquibase — struttura e workflow (v2)

> **Ultimo aggiornamento**: 12 novembre 2026
>
> **Destinatari**: chi scrive changeSet per il database di ZeroERP
>
> **Vedi anche**:
>
> * [Linee guida SQL](linee-guida-sql.md) — le convenzioni di ogni oggetto, e al §11 i divieti dei changeSet che si rompono solo in CI
> * [Provisioning ruoli DB](/dev/backend/provisioning-db-roles) e [Installazione](/installazione) — i ruoli di sistema e l'ordine dei passi su un database nuovo
> * [Configurazione GitHub](/dev/github/configurazione) — come la CI ricostruisce il database da zero
> * Versione iniziale, solo consultazione: [liquibase-setup-workflow_v1](./liquibase-setup-workflow_v1.md)

---

## In una frase

Ogni modifica al database è un **changeSet** in un file YAML sotto `db/changelog/migrations_v2/`;
l'ordine di esecuzione lo dà il **nome del file** (data e numero) per schema e codice, e la
**fase** (la cartella) per dati, job e passi finali. Liquibase si lancia sempre dal wrapper, mai dal
binario nudo.

---

## 1. Prerequisiti

* Java 17 e Liquibase 5 Community. Il binario sta in `tools/liquibase/current/` e il driver JDBC
  in `tools/liquibase/jdbc/`, versionati nel repository: nel `PATH` non c'è nessun `liquibase`.
* Il wrapper **`scripts/liquibase5.sh`**: aggancia il driver e, prima di `update`/`validate`,
  rigenera la timeline `changelog-autogen.yaml`. Lo usa il `makefile`.
* Un aggiornamento di Liquibase tocca quattro punti nello stesso giro: la cartella
  `tools/liquibase/<versione>/`, il collegamento `tools/liquibase/current`, la chiave `version:` del
  passo `setup-liquibase` in `ci.yaml` e in `ci-validate.yaml`, e l'intestazione di
  `scripts/ci-local.sh`.
* Un database con i **ruoli di sistema** già creati da `scripts/sql/provision_zeroerp.sql`: il
  migratore è `zeroerp_owner`, proprietario di tutti gli oggetti.

### Due diritti che si notano solo quando mancano

**Il migratore scrive nello schema `pgagent`.** La fase `85_pgagent` crea i lavori a orario. Lo
schema `pgagent` lo crea l'estensione e appartiene a `postgres`; i diritti a `zeroerp_owner` e a
`zeroerp_job` li dà la fase `pre` del provisioning. ⚠️ I changeSet di `85_pgagent` girano solo dove
l'estensione c'è (`onFail: MARK_RAN`): in CI vengono saltati, e il primo ambiente in cui girano
davvero è un'installazione vera. Lì **devono** girare.

Gli ambienti differiscono quindi anche per ciò che gira di notte: dove pgAgent non c'è i job non
esistono, dove c'è ma il suo demone punta a un altro database esistono e non girano. Davanti a una
differenza fra il database di sviluppo e uno ricostruito si leggono i job
(`20_code/maintenance/*proc_*_job*`) e il giornale `maintenance.job_run_log`, prima di attribuirla a
un difetto.

**Il lavoro delle statistiche deve poter analizzare ogni tabella.**
[fn_analyze_statistiche](/dbzero/maintenance/funzioni/fn_analyze_statistiche) lancia `ANALYZE` e
poi verifica di esserci riuscito (`E_STATISTICHE_MANCANTI`). Per analizzare una tabella bisogna
esserne proprietari: la procedura gira come `zeroerp_owner`, che possiede tutto, comprese le tabelle
che il primo passo di Liquibase crea da superuser (`databasechangelog`, `databasechangeloglock`,
`internal.project_metadata`), perché gliele passa la fase `pre`.

---

## 2. Le cartelle

```text
db/changelog/
├─ changelog-master-v2.yaml        # il master in uso
├─ changelog-master.yaml           # master della prima generazione (v1), incluso dal v2
├─ changelog-provision-pre.yaml    # passi da superuser, PRIMA del migrate (context provision)
├─ changelog-provision-post.yaml   # passi da superuser, DOPO il migrate (context provision)
│
├─ migrations_v2/
│  ├─ changelog-autogen.yaml       # generato: la timeline di 00_schema + 20_code (non committato)
│  ├─ 00_schema/<schema>/          # struttura: tabelle, colonne, vincoli, indici
│  ├─ 20_code/<schema>/            # codice: funzioni, trigger, procedure, viste
│  ├─ 70_dati_sistema/             # i dati senza cui il codice non gira
│  ├─ 80_data/                     # seed e configurazioni (CSV + loadUpdateData)
│  ├─ 85_pgagent/                  # i job di pgAgent
│  └─ 90_end/                      # passi finali; ci_apply/ = la passata ci_apply
│
├─ migrations/  baseline/          # prima generazione (v1): congelata
└─ legacy/                         # archivio di file dismessi
```

### Regole

* Tutto il lavoro nuovo va in `migrations_v2/`, in file **`.yaml`** (non `.yml`), **un changeSet
  per file**, `logicalFilePath` sempre valorizzato.
* ⛔ **Un changeSet già mergiato o pushato non si modifica**: si rompe la catena dei checksum. Per
  cambiare una funzione o un trigger si scrive un file nuovo, con il numero successivo.
* ⛔ **Il confine è l'apply, non il commit.** Un changeSet applicato su un database non si modifica
  nemmeno se il file non è ancora committato: Liquibase non lo riesegue, e il file racconta una cosa
  diversa da ciò che ha girato. Nel checksum entra tutto ciò che sta in `changes` (anche un
  `COMMENT ON`); restano liberi i commenti `#` dell'intestazione. La correzione è un changeSet nuovo.
* ⛔ **Il DDL e il corpo di un oggetto esistente si prendono dalla doc auto-generata**
  (`docs/it/dbzero/<schema>/…`), mai da uno YAML: per lo stesso oggetto ce ne sono spesso cinque o
  sei, e ripartire da uno vecchio fa regredire in silenzio le revisioni intermedie.
  ⚠️ La doc auto-generata mostra l'oggetto come PostgreSQL lo ha normalizzato: i `%TYPE` sono sciolti
  e `SECURITY INVOKER` non compare. Dal vivo si prende il **corpo**; la **dichiarazione** (firma,
  `RETURNS`, sicurezza) si prende dall'ultimo changeSet che la porta ancora ancorata. Nel
  `COMMENT ON FUNCTION` la firma ha i tipi risolti. E il blocco non è incollabile così com'è: la
  definizione si chiude con `$function$` senza `;`, che nel changeSet va aggiunto, altrimenti
  l'istruzione che segue è un errore di sintassi all'apply. Presidio: `scripts/guardrail_forme_changeset.py`, regola `punto-e-virgola`.
* Nella testata di un changeSet e nell'intestazione di un pgTAP un documento di lavoro si cita **per
  nome**, mai col percorso: a lavoro chiuso il documento cambia cartella e il percorso muore, mentre
  il nome è unico nel repository. Quando più changeSet nascono da un modello, il rimando si controlla
  nel modello prima di generare.
* ⛔ La prima generazione (`baseline/`, `migrations/`) non si tocca: lo presidia
  `scripts/guardrail_v1_congelato.py` ([linee-guida-sql §11.11](linee-guida-sql.md)).
* `00_schema` e `20_code` non sono inclusi dal master direttamente: il loro ordine è la timeline
  `changelog-autogen.yaml`, che `scripts/gen_master_autogen.py` costruisce dal **nome** dei file.
  Una sottocartella non cambia l'ordine: conta solo `YYYYMMDD-NN`.
* ⭐ **`70_dati_sistema`: i dati che il codice legge.** Un dato letto da una funzione, da un
  trigger o da un `DEFAULT` (per esempio il fuso dell'azienda, `SYSTEM_FUSO_ORARIO`) non può nascere
  in `80_data`: da zero tutto il codice gira prima di tutti i seed, e il primo seed che passa da quel
  codice si fermerebbe. Ci vanno pochi changeSet, uno per dato, con le regole di `80_data`; il
  valore resta nel CSV di `80_data/sql/`, sede unica.
* `90_end/` è per i passi finali e le reti di convergenza. Ciò che deve girare **dopo** i trigger
  delle automazioni va dentro `90_end/ci_apply/`: l'`includeAll` ordina per percorso, e
  `90_end/2026…` viene prima di `90_end/ci_apply/…`.

---

## 3. Il nome di un file

```text
migrations_v2/<fase>/<schema>/YYYYMMDD-NN-<tipo>-<descrizione>-<autore>.yaml
es.  20_code/dbops/20261024-26-update-fn-pgtap-crea-commessa-stato-e-ba-mctit.yaml
```

* `YYYYMMDD-NN` è una numerazione **globale per data**, su tutte le cartelle: il numero libero è il
  massimo già usato quel giorno, in **qualunque** fase (anche `80_data` e `90_end`), più uno.
* Oltre `-99` non si va: si passa al giorno dopo, da `-01`.
* Si parte dall'**ultima data usata**, anche se il giorno di calendario è un altro, e si prende il
  numero successivo: niente buchi riempiti, niente salti per lasciare spazio a un altro lavoro.
* Il numero lo dice `scripts/prossimo_changeset.py` (`… 5` per cinque numeri consecutivi), che legge
  i file, i rami git e il `databasechangelog` dei due database. La risposta vale per il minuto in cui
  gira: si rilancia subito prima di salvare ogni file. Con due lavori aperti insieme l'intervallo si
  concorda, e si occupa per intero appena deciso, con un file per numero.
* Un changeSet **non ancora applicato** si può rinumerare: cambiano insieme il nome del file, l'`id`,
  il `logicalFilePath` e ogni citazione del numero in altri changeSet, pgTAP, pagine `manual/` e brief.
  Dopo l'apply il numero non si tocca più.
* `<tipo>` dice che cosa fa il changeSet (`create`, `update`, `alter`, `add`, `drop`, `comment`, …).
* `<autore>` è lo stesso dell'attributo `author` del changeSet.

---

## 4. Il master e l'ordine di esecuzione

Il master `changelog-master-v2.yaml` include, in quest'ordine:

1. la prima generazione (`changelog-master.yaml`);
2. la timeline di `00_schema` + `20_code` (`migrations_v2/changelog-autogen.yaml`);
3. `70_dati_sistema`, `80_data`, `85_pgagent`, `90_end`, ognuna con `includeAll`.

---

## 5. Le passate: chi lancia che cosa

Un database ricostruito da zero (CI, scratch, installazione nuova) si costruisce con quattro
invocazioni di Liquibase, ognuna con il suo utente e i suoi **contesti**:

| Passata                | Changelog                        | Utente          | Contesti                         | Che cosa fa                                                       |
| ---------------------- | -------------------------------- | --------------- | -------------------------------- | ----------------------------------------------------------------- |
| provisioning, pre      | `changelog-provision-pre.yaml`   | superuser       | `provision`                      | i metadati di progetto e le estensioni, che solo un superuser può creare |
| migrazione             | `changelog-master-v2.yaml`       | `zeroerp_owner` | `!provision and !dati_macchina`  | schema, codice, dati, job, passi finali                           |
| provisioning, post     | `changelog-provision-post.yaml`  | superuser       | `provision`                      | la nascita e l'hardening delle funzioni che appartengono al superuser (registro `dbops.sec_functions_owner`). ⛔ Le loro **revisioni** no: stanno nel migrate, con la proprietà in prestito (qui sotto) |
| convergenza            | `changelog-master-v2.yaml`       | `zeroerp_owner` | `ci_apply`                       | i trigger delle automazioni e i lavori strutturali, in ordine     |

Fra le passate, `scripts/sql/provision_zeroerp.sql` (fasi `ruoli`, `pre`, `post`) crea i ruoli e
sistema proprietà e diritti. L'ordine completo per un'installazione è in
[Installazione](/installazione); quello della CI in `.github/workflows/ci-validate.yaml`.

I contesti in uso:

| Contesto        | Che cosa marca                                                                                             |
| --------------- | ---------------------------------------------------------------------------------------------------------- |
| `provision`     | i changeSet da superuser, raccolti nei due changelog di provisioning                                        |
| `ci_apply`      | la convergenza dopo il migrate: automazioni e lavori strutturali ([guida automazioni, §9](/guide/automazione-db)) |
| `dati_macchina` | i seed che valgono per una sola macchina ([linee-guida-sql §11.7](linee-guida-sql.md))                       |

⚠️ Una passata **senza** `--contexts` esegue i changeSet di **tutti** i contesti. È quello che
succede sul database di sviluppo (sotto), ed è voluto lì; altrove il filtro va scritto per intero.

### Modificare una funzione del superuser: la proprietà in prestito

Una funzione del registro `dbops.sec_functions_owner` appartiene a `postgres`. Il migratore non la
può modificare, e nemmeno commentare: `CREATE OR REPLACE`, `ALTER` e `COMMENT ON FUNCTION` li può
eseguire solo il proprietario. ⛔ La revisione **non** si mette in `context: provision`: sul database
di sviluppo il migrate gira senza contesti, quindi la esegue `zeroerp_owner`, che viene rifiutato. Da
zero, poi, girerebbe **dopo** il migrate e riporterebbe il corpo vecchio sopra le revisioni
successive. È il caso di `maintenance.fn_job_run_log_failure`, documentato in
`changelog-provision-post.yaml`.

La revisione sta nel migrate normale, in un solo changeSet:

1. presta la proprietà: `UPDATE dbops.sec_functions_owner SET required_owner = current_user …`, poi
   `SELECT dbops.fn_sync_functions_owner();`;
2. verifica il prestito con un `DO` che solleva se `pg_get_userbyid(proowner) <> current_user`. La
   sync, quando fallisce, degrada a `WARNING`;
3. applica la modifica;
4. restituisce la proprietà: `required_owner = 'postgres'`, poi di nuovo `fn_sync_functions_owner()`.

Modello: `20_code/script/20260807-19-rename-messaggio-non-definito`. Prima di scrivere si riprende la
forma dalle revisioni precedenti della **stessa** funzione. ⛔ Nessuna `preCondition` sulla riga del
registro: la riga arriva dal CSV di `80_data`, e in `20_code`, da zero, non c'è ancora. In quel
momento la funzione è ancora del migratore. `fn_sync_functions_owner` non sta nel registro e non
presta la proprietà a sé stessa: per lei serve una copia di servizio (`20260929-09`).

---

## 6. Come si lancia, in pratica

⛔ **Sono tutte migrazioni**: le blocca l'hook `scripts/guardrail_no_db_migrate.py` e si lanciano
solo con la conferma esplicita per quel comando. Restano liberi `status`, `validate` e `updateSQL`,
che non applicano niente. Che cosa è già applicato si legge dalla tabella `databasechangelog`.

Per vedere l'SQL che Liquibase genererebbe da un change che non è SQL (`loadData`, `createTable`) si
usa `updateSQL` con `--url=offline:postgresql`, che non apre connessioni. In questa modalità le
`preConditions` non sono valutabili, e il file `databasechangelog.csv` che resta nella cartella va
tolto prima di ogni resa, o la successiva salta i changeSet già registrati. Un changeSet intero si
prova con `scripts/prova_changeset.py`.

### 6.1 Il database di sviluppo (dbdev)

Dalla cartella `db/`:

```bash
cd db
../scripts/liquibase5.sh update
```

Il wrapper legge `db/liquibase.properties` (connessione, utente della propria macchina, master v2) e
rigenera la timeline. Non c'è `--contexts`, quindi l'`update` esegue **tutto**:

* la migrazione **e** la convergenza `ci_apply`: a ogni update i trigger delle automazioni e i
  lavori strutturali si riallineano, senza una seconda passata;
* i seed `dati_macchina`: dbdev è la macchina a cui appartengono;
* i changeSet `context: provision`. ⚠️ Per questo, quando un lotto ne porta, il **provisioning
  post** da superuser va lanciato **prima** dell'update: altrimenti l'update li troverebbe senza
  esserne proprietario e si fermerebbe.

`db/liquibase.properties` e `db/internal.env` sono della propria macchina e non sono committati.

### 6.2 Il database scratch, come lo costruisce la CI

```bash
PGPASSWORD_POSTGRES='…' scripts/ci-local.sh --ci-apply
```

`scripts/ci-local.sh` riproduce in locale le quattro passate del §5, nello stesso ordine della CI,
sul database scratch `zeroerp_ruoli` (o quello indicato da `CI_DB`). La password serve per il
superuser, che crea il database e lancia le due passate di provisioning.

* `--ci-apply` aggiunge la convergenza: senza, lo scratch non ha le automazioni e non è
  confrontabile con la CI;
* senza `--fresh` è **incrementale**: riprende da dove era arrivato, e il ciclo «correggo → provo» si
  misura in secondi. Se si è corretto un changeSet **già applicato**, serve `--fresh`, che ricostruisce
  da zero;
* in fondo prepara lo scratch anche per i pgTAP (estensione `pgtap`, schema `django` copiato senza
  privilegi, diritti di `zeroerp_app`);
* rifiuta di lavorare sul database nominato in `db/internal.env`, cioè quello di sviluppo.

È la prova da fare prima di mandare un lotto in CI: trova il changeSet che rompe un database
ricostruito da zero senza aspettare GitHub.

### 6.3 Con `make`

Il `makefile` ha le due passate di un database già costruito, con il wrapper:

```bash
make db-migrate DB_USER=<utente> DB_PASS='…'     # contesti: !test AND !provision
make db-ci-apply DB_USER=<utente> DB_PASS='…'    # contesto ci_apply
```

L'utente di default è il migratore `zeroerp_owner`; la password non sta nel file (`DB_PASS` o
`DB_PASSWORD`), e senza i target si fermano prima di chiamare Liquibase. Connessione da `DB_HOST`,
`DB_PORT`, `DB_NAME`.

---

## 7. Cambiare una struttura senza rompere: Expand → Align → Contract

1. **Expand** (`00_schema`): si aggiunge l'oggetto nuovo senza togliere il vecchio.
2. **Align** (`20_code`): funzioni e trigger lavorano con entrambe le forme.
3. **Contract** (`00_schema`): si toglie il vecchio, in un lotto successivo.

Le regole che valgono lungo i tre passi:

* ⛔ **Chi toglie aspetta il lettore.** Un changeSet che toglie o rinomina un oggetto letto dal
  backend non entra nel ramo finché il lettore non è cambiato: l'`update` applica tutti i file
  presenti, e un ordine scritto in prosa non lo ferma. Se deve andare nello stesso giro, si lascia un
  passo che non rompe il lettore (una vista col nome vecchio, da togliere dopo).
* **Fra `00_schema` e `20_code` decide il numero, non la cartella.** Quando un changeSet di
  `00_schema` toglie una dipendenza che un changeSet di `20_code` deve ricreare (una vista, un trigger
  che nomina la colonna in `UPDATE OF`, una funzione `BEGIN ATOMIC`), il ricreatore ha un numero più
  alto di chi toglie, in un file suo: aggiunta a un changeSet con numero più basso «perché il codice
  viene dopo», la ricreazione gira prima del `DROP` e l'oggetto resta a terra con il migrate verde.
  Le dipendenze si tolgono per nome, mai con `CASCADE`, che le porta via senza dirlo.
* **Un dato si sposta con tutto ciò che lo compone.** Prima di portare un valore in un'altra sede si
  cerca dove è usato: se entra in una concatenazione o in un `format()`, gli altri operandi fanno
  parte del dato. Il test copre il caso in cui il pezzo accessorio **non** è vuoto. La correzione è
  doppia: una bonifica idempotente (che confronta col valore non ancora trasformato) e la funzione
  che crea le righe nuove.
* **Convertire una colonna su una tabella con guard di riga.** Un backfill per `UPDATE` attraversa i
  trigger e si ferma sui guard. `ALTER COLUMN … TYPE … USING <espressione sulla riga>` è DDL: nessun
  trigger di riga, nessun momento con due colonne. Anche una colonna nuova si riempie così
  (`ADD COLUMN`, poi `ALTER … TYPE <stesso tipo> USING`); un valore costante con `DEFAULT` seguito da
  `DROP DEFAULT`. ⛔ Un trigger `UPDATE OF <colonna>` è una dipendenza che `ALTER TYPE` rifiuta: si
  toglie prima e si ricrea dopo, nello stesso changeSet. Per l'allineamento di una colonna derivata
  che resta un `UPDATE`, vedi [linee guida trigger](linee-guida-trigger.md).
* **Cambiare la chiave di una tabella partizionata.** Il tipo non si cambia sul padre: si crea un
  padre nuovo e, per ogni partizione, `DETACH`, `ALTER COLUMN … TYPE … USING`, `ATTACH`. ⛔ `ATTACH`
  confronta la **struttura** dei `CHECK`, non il loro testo: su ogni partizione staccata si tolgono e
  si rimettono con lo stesso testo del padre nuovo, altrimenti il changeSet passa su un database e si
  ferma su un altro. La colonna identity appartiene al padre: la sequenza nuova riparte dal valore
  della vecchia. FK entranti, policy, grant e commenti del padre si rimettono.
* **Ritirare una tabella** vuol dire togliere anche: le funzioni trigger dei suoi trigger (il `DROP`
  toglie il trigger, la funzione resta orfana); la tabella stessa dal provisioning, se è nata lì; la
  pagina `manual/`, e alla rigenerazione la pagina generata e la riga d'indice in
  `docs/it/dbzero/<schema>/`.

I divieti che decidono se un changeSet regge su un database ricostruito da zero — `runOnChange` in
`00_schema`/`20_code`, `preCondition` sul contenuto di `80_data`, DDL sui trigger generati da
`ci_apply`, `GRANT` ai ruoli batch, `UPDATE` sui seed invece del CSV — stanno, con i loro presidi, in
[linee-guida-sql §11](linee-guida-sql.md).

---

{% include-markdown "signature-core.md" %}
