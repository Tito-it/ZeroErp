# Brief DB — `zeroerp_log` nasce con gli altri ruoli di sistema

## ✅ Chiuso il 2026-10-15

| # | Chi | Che cosa | Dove |
| --- | --- | --- | --- |
| 1 | ✅ **team DB** | `zeroerp_log` creato dalla fase `ruoli` di `provision_zeroerp.sql`; via il `CREATE ROLE` a mano dai due workflow, dalla guida d'installazione e da `provision_dblink_log_channel.sql` | §2, §5 |
| 2 | ✅ **Tid** | Via i vecchi privilegi di default di `titodb` su `zeroerp` (da pgAdmin; 117 revoche, una per diritto) | §3 |
| 3 | ✅ **Tid** | `scripts/ci-local.sh --ci-apply` su `zeroerp_ruoli` dopo la fase 4 | §4 |

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-15. **A chi:** il team DB e Tid.
> **Origine:** il debito residuo della chiusura di
> [brief-db-ruoli-di-sistema](brief-db-ruoli-di-sistema.md) (§18, §19 e la tabella in testa).
> Voce-rimando: D35 in [migliorie-generali-da-test-valutazione](../work-in-progress/migliorie-generali-da-test-valutazione.md).
> **Ricadute BE/FE:** nessuna.
> **Stato:** ✅ chiuso il 2026-10-15 (proposta della parte 1 approvata da Tid lo stesso giorno).

## 1. Il problema

`zeroerp_log` è un ruolo di sistema come `zeroerp_owner`, `zeroerp_job` e `zeroerp_app`: nome fisso,
password senza default. Ma non lo crea la fase `ruoli` di `scripts/sql/provision_zeroerp.sql`: lo
creano a mano i due workflow di GitHub (`CREATE ROLE zeroerp_log …` nel passo di bootstrap) e la guida
d'installazione (passo 1-bis), oppure `provision_dblink_log_channel.sql`, che però gira **dopo** le
migrazioni perché concede su `dbops.error_log`.

E deve esistere **prima** del migrate: il changeSet `90_end/20260905-38` gli dà `INSERT` sul giornale
dei job (`maintenance.job_run_log`) solo se il ruolo c'è, altrimenti salta con un avviso e quel diritto
non arriva più. Senza, il verbale di un lavoro fallito non viene scritto.

⇒ Tre sedi per la stessa cosa, e un ordine che si ricorda solo leggendo la guida.

## 2. Parte 1 — la proposta

* la fase `ruoli` crea anche `zeroerp_log` (`-v log_password=…`, servita **solo** se il ruolo manca,
  come le altre: D-3), con la stessa postura (login, non superuser, `NOBYPASSRLS`) e il suo
  `COMMENT ON ROLE`;
* via il `CREATE ROLE zeroerp_log` da `ci.yaml` e `ci-validate.yaml` (resta il parametro del canale, che
  in CI è una stringa di connessione con password: ambiente, non ruolo);
* `provision_dblink_log_channel.sql`: la creazione del ruolo diventa un controllo («manca: lancia la fase
  `ruoli`»), restano i diritti su `dbops.error_log` e i parametri del canale;
* la guida d'installazione perde il passo 1-bis, e il passo 1 passa anche `log_password`;
* prova sul cluster usa-e-getta, database come in CI, e la verifica che dopo il migrate `zeroerp_log`
  abbia `INSERT` su `maintenance.job_run_log`.

⚠️ La memoria del server non regge un build da zero mentre gira il resto (2026-10-15: swap pieno): la
prova si fa a server scarico.

## 3. Parte 2 — i vecchi privilegi di default di `titodb` (Tid, facoltativo)

Dopo la conversione di dbdev `titodb` lavora come `zeroerp_owner` e non crea più niente a nome suo:
i suoi 48 privilegi di default su `zeroerp` non scattano più. Toglierli è pulizia, da superuser:

```
psql -h localhost -U postgres -d zeroerp -At -c "SELECT format('ALTER DEFAULT PRIVILEGES FOR ROLE titodb%s REVOKE ALL ON %s FROM %I',
    CASE WHEN d.defaclnamespace = 0 THEN '' ELSE ' IN SCHEMA ' || quote_ident(d.defaclnamespace::regnamespace::text) END,
    CASE d.defaclobjtype WHEN 'r' THEN 'TABLES' WHEN 'S' THEN 'SEQUENCES' WHEN 'f' THEN 'FUNCTIONS' WHEN 'T' THEN 'TYPES' WHEN 'n' THEN 'SCHEMAS' END,
    pg_get_userbyid(a.grantee))
  FROM pg_default_acl d CROSS JOIN LATERAL aclexplode(d.defaclacl) a
 WHERE d.defaclrole = 'titodb'::regrole AND a.grantee <> 0" | psql -h localhost -U postgres -d zeroerp
```

Chiuso quando `SELECT count(*) FROM pg_default_acl WHERE defaclrole = 'titodb'::regrole` dà 0.

## 4. Parte 3 — `ci-local.sh` dopo la fase 4 (Tid)

`scripts/ci-local.sh` è cambiato con la fase 4 (via `--classico`, il ponte del ruolo batch e il passo dei
privilegi dell'app, assorbito dalla fase `post`) e non si è potuto lanciare dalla sessione DB (vuole
`sudo`). La CI di GitHub con gli stessi passi è verde; manca la corsa locale:

```
PGPASSWORD_POSTGRES='…' scripts/ci-local.sh --ci-apply
```

Chiuso quando finisce con «passata completata» e il testimone su dbdev invariato.

## 5. Che cosa è stato fatto, e la prova

* `scripts/sql/provision_zeroerp.sql`, fase `ruoli`: `zeroerp_log` entra nell'elenco dei ruoli di
  sistema (password con `-v log_password`, servita solo se il ruolo manca; postura verificata; commento
  del ruolo), e riceve `CONNECT` sul database insieme a job e app;
* `scripts/sql/provision_dblink_log_channel.sql`: non crea più il ruolo. Se manca si ferma e dice dove
  nasce; restano i diritti su `dbops.error_log` e i parametri del canale;
* `.github/workflows/ci.yaml` e `ci-validate.yaml`: `-v log_password=secret-log` alla fase `ruoli`, via il
  `CREATE ROLE zeroerp_log` a mano (resta il parametro del canale, che in CI è una stringa di connessione);
* `installazione.md`: via il passo 1-bis, il passo 1 passa anche `log_password`; pagina del provisioning
  e play-book allineati.

**Prova** (cluster usa-e-getta, struttura di dbdev, 2026-10-15): fase `ruoli` su un cluster vuoto senza
`log_password` → si ferma su `zeroerp_log` (nessun ruolo creato: il blocco è uno solo); con le quattro
password → quattro ruoli, login, non superuser, senza `BYPASSRLS`, col commento; `CONNECT` a
`zeroerp_log`; `zeroerp_owner` membro di `pg_read_all_stats` (D-6). Rilancio senza password: passa. Il
`20260905-38` (SQL estratto) su un database dove `zeroerp_log` esiste già: `INSERT` sul giornale dei job
concesso. Lo script del canale: col ruolo passa senza password; senza il ruolo si ferma col messaggio
che rimanda alla fase `ruoli`. La CI di GitHub prova il resto alla prossima PR.

---
{% include-markdown "signature-core.md" %}
