# Parametri personalizzati (GUC) in PostgreSQL

> **Ultimo aggiornamento**: 4 novembre 2026
>
> **Destinatari**: chi scrive funzioni, trigger o verbi del database, e chi configura un'installazione
>
> **Vedi anche**:
>
> * [Contratto GUC `app.*`](/guide/contratto-guc-app) — l'identità della richiesta: la sede di tutto ciò che riguarda `app.*`
> * [Configurazione e gestione parametri](/guide/configurazione-e-gestione-parametri) — i parametri che stanno in tabella (`config.parameters`)
> * [dblink](/postgresql/dblink) — il canale dei registri fuori transazione

---

## Che cosa sono

Un **GUC personalizzato** è un parametro con un nome a due parti (`prefisso.nome`) che PostgreSQL
tiene in memoria: per tutto il server, per un database, per un ruolo, per la connessione o per la
sola transazione. Si legge con `current_setting('prefisso.nome', true)` — il secondo argomento
`true` restituisce `NULL` invece di un errore se il parametro non c'è — e si scrive con
`set_config('prefisso.nome', valore, is_local)`:

* `is_local = true`: vale fino alla fine della **transazione**, poi sparisce da solo;
* `is_local = false`: vale per tutta la **connessione**, finché qualcuno non lo cambia.

Un GUC **non è storage**: non si versiona, non ha audit, non sopravvive al riavvio se non sta in un
file di configurazione o in un `ALTER DATABASE/ROLE … SET`. Quello che deve durare, e che una persona
può cambiare, sta in tabella: [Configurazione e gestione parametri](/guide/configurazione-e-gestione-parametri).

---

## Le quattro famiglie

Il prefisso dice a che cosa serve un GUC, chi lo scrive e quanto dura. Sono quattro, e non si
mescolano.

| Prefisso    | A che cosa serve                                                       | Chi lo scrive                                         | Quanto dura                       |
| ----------- | ---------------------------------------------------------------------- | ----------------------------------------------------- | --------------------------------- |
| `myapp.*`   | la **configurazione** dell'installazione: lingua, canale dei registri, ambiente | chi installa: `ALTER DATABASE/ROLE … SET`, opzioni della connessione | persistente                  |
| `dbops.*`   | l'**infrastruttura** della transazione: il `tx_id`                       | le funzioni di `dbops`                                | la transazione                    |
| `app.*`     | l'**identità** della richiesta (e due porte nate con questo prefisso)       | il backend a ogni richiesta; alcune funzioni          | la connessione (identità) · la transazione (contesto) |
| `zeroerp.*` | le **porte**: un verbo che apre, per sé, un passaggio che un guard altrimenti chiude | i verbi del database, le procedure di manutenzione, il provisioning | la transazione            |

### `myapp.*` — la configurazione

Si impostano una volta, a livello di database o di ruolo, e le funzioni le leggono (elenco completo
in [Elenco dei GUC](#elenco-dei-guc)). I più importanti:
la lingua dei messaggi (`myapp.user_language`), la connessione del canale dei registri via dblink
(`myapp.dblink_log_connection`, impostata da `scripts/sql/provision_dblink_log_channel.sql`),
l'ambiente della passata di Liquibase (`myapp.env = 'ci'`, nelle opzioni della connessione di CI).

⚠️ Il canale dei registri si legge dalla **sessione**: sotto pgAgent la sessione è `zeroerp_job`, e il
parametro va impostato anche per lui (o per tutto il database), altrimenti il verbale di un
fallimento non si scrive e resta solo un `WARNING`.

### `dbops.*` — l'infrastruttura

`dbops.tx_id` è l'identificativo della transazione logica: lo crea `dbops.fn_get_or_create_session_tx_id`
e lo legge il trigger del `tx_id` per collegare tutte le righe toccate insieme. Il disegno è nella
guida [Gestione del Transaction ID](/guide/tx_id_implementation_guide).

### `app.*` — l'identità della richiesta

I sei GUC d'identità (`app.current_identita_id`, `app.ruolo_applicativo`, `app.soggetto_ruolo_id`,
`app.current_emittente_id`, `app.current_user_id`, `app.jwt_user`) li scrive il backend a ogni
richiesta, **di connessione** (`is_local = false`), e li **azzera all'inizio** di ogni richiesta: è
quel reset, non il commit, a impedire che una richiesta erediti l'identità della precedente. Le
policy RLS, le funzioni di scope e i trigger di audit li leggono.

Tutto il resto — da dove viene ogni valore, l'invariante «tutto o niente», che cosa succede quando
mancano, come si diagnostica — sta in un posto solo: [Contratto GUC `app.*`](/guide/contratto-guc-app).

Nello stesso prefisso vive anche una **porta** (`app.registrazione_tardiva_riga_id`): funziona come
quelle `zeroerp.*` qui sotto, non è identità e non fa parte del contratto. Una porta nuova si chiama
`zeroerp.*`. (`app.cessazione_automatica`, la seconda, è ritirata dal 2026-10-26: la poteva accendere
chiunque, e la cessazione del contratto passa dai suoi verbi.)

### `zeroerp.*` — le porte

È la famiglia più numerosa, e la meno visibile. Una regola del database — un guard, un lucchetto di
colonna, un «solo in bozza» — chiude una strada a tutti. Il **verbo** che ha il diritto di
percorrerla la apre **per sé**:

1. scrive il GUC della porta con `set_config('zeroerp.<porta>', <valore>, true)`, cioè per la sola
   transazione; il valore, quando serve, nomina **l'oggetto** (`'<documento>:<id>'`), così la porta
   vale per quella riga e non per tutte;
2. fa la scrittura: il guard legge il GUC, riconosce il passaggio e lo lascia passare;
3. richiude la porta (`set_config(…, '', true)`), o la lascia chiudere dalla fine della transazione.

Regole:

* ⛔ **Una porta si apre solo dentro un verbo**, mai dal backend e mai a mano in una sessione di
  lavoro. Un `SET zeroerp.<porta>` in psql scavalca una regola che esiste per una ragione.
* ⛔ **Sempre `is_local = true`**: una porta che resta aperta sulla connessione resta aperta per la
  richiesta successiva, di chiunque sia.
* Il guard legge la porta con `current_setting(…, true)`: una porta assente vale «chiusa».
* Chi scrive un trigger che tocca una colonna protetta da una porta non la «difende» riassegnando
  il valore vecchio: annullerebbe anche le scritture che passano dalla porta
  ([Linee guida Trigger](/linee-guida-trigger)).

Nello stesso prefisso stanno anche gli **override amministrativi** (`zeroerp.allow_*_override`, per
esempio quello del lucchetto di colonna), le porte delle **procedure di manutenzione**
(`zeroerp.maintenance_*`) e i parametri del **provisioning** (`zeroerp.prov_*`), che vivono solo per
la durata dello script.

---

## GUC o tabella?

| Domanda                                                     | GUC                                  | Tabella (`config.parameters` e override) |
| ----------------------------------------------------------- | ------------------------------------ | ---------------------------------------- |
| Lo cambia una persona dall'applicazione?                    | no                                   | sì                                       |
| Serve sapere chi l'ha cambiato e quando?                    | no: non c'è audit                    | sì                                       |
| Vale per un'azienda, un utente, una funzione?               | no: vale per server, database, ruolo, connessione o transazione | sì, per riga |
| È un fatto della connessione o della transazione in corso (chi sei, quale `tx_id`, quale porta è aperta)? | sì | no |

Una regola di dominio (una soglia, un termine, un comportamento che un'azienda sceglie) non sta mai
in un GUC.

---

## Elenco dei GUC

Censiti il 2026-10-24 dalle letture (`current_setting`) e dalle scritture (`set_config`) nei
changeSet, nel backend e negli script. Per vedere chi usa un GUC sul database vivo, la query è nell'area
tecnica, in coda.

### `myapp.*` — configurazione dell'installazione

| GUC                           | Valori                    | Dove si imposta                                                | Chi lo legge                                                        |
| ----------------------------- | ------------------------- | -------------------------------------------------------------- | ------------------------------------------------------------------- |
| `myapp.user_language`         | codice lingua (`it`)      | `ALTER ROLE … IN DATABASE … SET`                               | i messaggi d'errore (`script.fn_get_messaggio`, `fn_log_and_raise_error`) |
| `myapp.dblink_log_connection` | stringa di connessione    | `scripts/sql/provision_dblink_log_channel.sql`, per ruolo      | il canale dei registri fuori transazione (`script.fn_log_error_only`, `maintenance.fn_job_run_log_failure`, `script.fn_ensure_logconn`) |
| `myapp.logconn`               | stringa di connessione    | facoltativo, nella sessione                                    | gli stessi lettori: se c'è, **vince** su `myapp.dblink_log_connection` |
| `myapp.log_with_dblink`       | `on` / `off`              | opzioni della connessione (`off` nelle migrazioni)             | l'audit delle automazioni (`dbops.fn_audit_log_once`) |
| `myapp.bypass_tx_id_check`    | `on` / `off`              | per ruolo o sessione                                           | il trigger del `tx_id` (`dbops.trgfn_tx_id_managed`), secondo livello del bypass |
| `myapp.env`                   | `ci`                      | opzioni della connessione della passata `ci_apply` in CI        | la `preCondition` del changeSet `90_end/ci_apply/20250627-31`       |

### `dbops.*` — infrastruttura della transazione

| GUC           | Chi lo scrive                                   | Chi lo legge                                       |
| ------------- | ----------------------------------------------- | -------------------------------------------------- |
| `dbops.tx_id` | `dbops.fn_get_or_create_session_tx_id`          | il trigger del `tx_id` su ogni tabella tracciata   |

### `app.*` — identità della richiesta e contesto

**Identità** — li scrive il backend a ogni richiesta, di connessione, e li azzera all'inizio della
successiva. Significato, provenienza e regole in [Contratto GUC `app.*`](/guide/contratto-guc-app):

`app.current_identita_id` · `app.ruolo_applicativo` · `app.soggetto_ruolo_id` ·
`app.current_emittente_id` · `app.current_user_id` · `app.jwt_user`

**Porte con il prefisso `app.*`** — non sono identità: sono porte, con lo stesso meccanismo delle
`zeroerp.*` (le apre una funzione per la sola transazione, un guard le legge):

| GUC                                  | Chi la apre                                   | Che cosa lascia passare                                                    |
| ------------------------------------ | --------------------------------------------- | -------------------------------------------------------------------------- |
| `app.registrazione_tardiva_riga_id`  | `pagamenti.fn_posta_riga_tardiva`             | quella sola riga, sul guard della distinta finale                           |

⚠️ **Residuo**: `app.session_key` lo legge `script.fn_get_parameter_di_sessione` (livello «sessione»
degli override dei parametri), ma nessuna funzione lo scrive più: l'unica che lo faceva, insieme ad
`app.user_id` e `app.group_ids`, è stata ritirata il 4 novembre 2026 perché non aveva chiamanti. Oggi
quel livello resta sempre saltato.

### `zeroerp.*` — porte, override, manutenzione, provisioning

Tutti per la sola transazione (`is_local = true`). Il meccanismo è spiegato sopra, in [`zeroerp.*` — le porte](#zeroerp-le-porte).

| Gruppo                    | GUC                                                                                                                                                                  |
| ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| porte dei verbi di documento | `zeroerp.doc_ritira_legami`, `zeroerp.ddt_cambio_stato`, `zeroerp.ddt_annullo`, `zeroerp.ddt_riconsegna`, `zeroerp.ddt_riga_correggi_qta`, `zeroerp.ddt_riga_ritira_legame`, `zeroerp.reso_cambio_stato` |
| porte del magazzino       | `zeroerp.magazzino_posting_inventario`, `zeroerp.magazzino_posting_rettifica`, `zeroerp.magazzino_posting_trasferimento`                                              |
| porta del catalogo        | `zeroerp.articolo_correggi_struttura`                                                                                                                                 |
| override amministrativi   | `zeroerp.allow_lock_columns_override`, `zeroerp.allow_user_emittente_delete_override`, `zeroerp.allow_contabile_riga_delete_override`                                |
| manutenzione              | `zeroerp.maintenance_reset_lotto_draft`, `zeroerp.maintenance_allow_delete_logs`, `zeroerp.maintenance_allow_attivita_bypass`, `zeroerp.maintenance_indirizzi_dettaglio`, `zeroerp.maintenance_toponomastica` |
| provisioning e conversione | `zeroerp.prov_ambiente`, `zeroerp.prov_owner_password`, `zeroerp.prov_app_password`, `zeroerp.prov_job_password`, `zeroerp.prov_log_password`, `zeroerp.migratore`, `zeroerp.conv_utente` |

---

## Area tecnica — esempi

Leggere un GUC senza errore se manca:

```sql
SELECT current_setting('myapp.user_language', true);
```

Impostare la configurazione di un'installazione, una volta:

```sql
ALTER DATABASE zeroerp SET myapp.user_language = 'it';
ALTER ROLE zeroerp_job IN DATABASE zeroerp SET myapp.dblink_log_connection = '<dsn>';
```

Vedere quali GUC `myapp.*` sono impostati per database e ruolo:

```sql
SELECT coalesce(r.rolname, '(tutti)') AS ruolo, d.datname, s.setconfig
  FROM pg_db_role_setting s
  LEFT JOIN pg_roles r ON r.oid = s.setrole
  LEFT JOIN pg_database d ON d.oid = s.setdatabase
 ORDER BY 2, 1;
```

Trovare quali funzioni aprono o leggono una porta:

```sql
SELECT n.nspname, p.proname
  FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace
 WHERE pg_get_functiondef(p.oid) LIKE '%zeroerp.<porta>%'
 ORDER BY 1, 2;
```

---

{% include-markdown "signature-core.md" %}
