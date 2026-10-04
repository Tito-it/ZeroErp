# Brief DB — Un cambio del catalogo permessi svuota la cache del backend

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** team DB
> (`dev/db-tid`); poi BE (§5), che **attende** la consegna DB.
> **Origine:** [brief-db-permessi-tetto-area.md](brief-db-permessi-tetto-area.md) §6.5 e §10:
> `livello_minimo_area` cambia solo a DB (seed al migrate), e il backend non lo sa.
> **Decisione:** di Tid, 2026-10-04: soluzione LISTEN/NOTIFY, sul meccanismo che già esiste per
> il cambio di reparto.
> **Stato:** 🟡 da fare (DB). Nome del processo deciso (§4).

## 1. Il problema

Il backend tiene in cache, per utente e contesto di sessione, i permessi risolti dalle funzioni DB
(`apps/core/services/permissions_cache.py`, Redis). La cache si svuota quando **l'applicazione**
scrive qualcosa che li cambia: un override (`invalidate_user`), il profilo di un reparto
(`invalidate_department`), un cambio di reparto (trigger DB → `NOTIFY cambio_reparto` → listener →
`invalidate_user`).

Chi scrive il **catalogo** dei permessi **fuori dall'applicazione** non svuota niente:

| Tabella | Chi la scrive | Cosa cambia per gli utenti |
| --- | --- | --- |
| `config.azioni_processo` | seed CSV al migrate | `livello_minimo_area` (tetto d'area), azioni nuove o spente |
| `config.aree_funzionali` | seed CSV al migrate | aree nuove o spente |
| `config.area_model_overrides` | seed CSV al migrate | a quale area appartiene un oggetto ⇒ quale tetto lo limita |
| `config.profili_accesso`, `config.profili_accesso_aree`, `config.profili_accesso_azioni`, `config.profili_accesso_bindings` | app (solo il PUT del profilo di **reparto**, che invalida il reparto), seed, interventi a mano | tutto l'ereditato di chi ha quel profilo, anche `AD_HOC` e `PORTALE`, che l'app non invalida |

Fino alla scadenza della voce (`PERMISSIONS_CACHE_TTL`, 300 s) gli utenti lavorano coi permessi
vecchi: un'azione appena chiusa dal tetto resta eseguibile. ⚠️ Il team DB applica i migrate per
conto suo, indipendentemente dal deploy del backend: svuotare la cache dallo script di deploy
**non** chiuderebbe il buco, e nemmeno una correzione fatta in `psql`.

## 2. La regola

**Ogni scrittura che cambia il catalogo o i profili dei permessi, da qualunque scrittore, avvisa il
backend al commit.** Il backend svuota la cache di tutti (`invalidate_all`, invalidazione per
generazione: costa un ricalcolo per utente alla richiesta successiva).

È lo stesso schema del cambio di reparto (`anagrafiche.trgfn_risorse_umane_notify_cambio_reparto`
→ `anagrafiche.fn_notify_cambio_reparto` → canale `cambio_reparto`), con una differenza: qui la
notifica non riguarda un utente, ma tutti.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| R1 | Una funzione `script.fn_notify_permessi_catalogo(p_tabella text)` che emette `pg_notify('permessi_catalogo', json_build_object('tabella', p_tabella)::text)`. Sede unica del nome del canale lato DB. Forma e guard come `fn_notify_cambio_reparto`. |
| R2 | Una trigger function generica (`script.trgfn_notify_permessi_catalogo()`, argomento: il nome della tabella, oppure `TG_TABLE_SCHEMA.TG_TABLE_NAME`) che chiama R1 e restituisce `NULL`. |
| R3 | Un trigger **`AFTER INSERT OR UPDATE OR DELETE … FOR EACH STATEMENT`** (non per riga: un mirror CSV tocca decine di righe e basta un avviso) su ognuna delle **sette** tabelle di §1, prefisso `z90_` come quello del cambio di reparto. ⭐ `NOTIFY` è transazionale: parte al commit, non parte su rollback, e PostgreSQL scarta i payload identici nella stessa transazione. Valutare anche `TRUNCATE`. |
| R4 | Verificare che il mirror dei CSV (`80_data`, `loadUpdateData`) faccia `INSERT`/`UPDATE` normali e quindi **accenda** i trigger: è il caso per cui il brief esiste. Se un passo li disattiva (`session_replication_role`, `ALTER TABLE … DISABLE TRIGGER`), dirlo nella consegna. |
| R5 | pgTAP: per ogni tabella, una scrittura in transazione produce **una** notifica sul canale col nome della tabella (`LISTEN` + `pg_notification_queue_usage` non basta: usare il metodo dei test del cambio di reparto, se esiste, o dichiarare come si prova). Una scrittura annullata non ne produce. |
| R6 | Doc `manual/` delle due funzioni e una riga nella guida di architettura dei permessi (§ cache), che oggi non dice chi svuota la cache al cambio di catalogo. |

ℹ️ **Fuori:** `config.user_override_*`. Le scrive il pannello, che invalida già l'utente
(`invalidate_user`). Un avviso per utente su scritture fuori dall'app è un'altra cosa (payload per
utente, come il cambio di reparto) e non serve per chiudere questo buco.

## 4. Il processo che ascolta si rinomina `listen_permessi` (✅ Tid, 2026-10-04)

Il listener oggi si chiama `listen_cambio_reparto` (`dbops.processi.codice`, `sveglie.json`,
unità systemd `zeroerp-listen-cambio-reparto`, `application_name` della sessione, che
`dbops.vw_processi_programmazione` legge per dire se il processo è vivo). Col canale nuovo fa due
cose, e il nome non lo direbbe più. Decisione: **un solo processo**, che ascolta entrambi i canali,
rinominato **`listen_permessi`**. Due processi separati non servono: stessa connessione, stesso
destinatario.

| # | Cosa (DB) |
| --- | --- |
| R7 | `dbops.processi`: il codice `listen_cambio_reparto` diventa `listen_permessi` (dal seed CSV, mai con `UPDATE`, linee-guida-sql §11.2), con descrizione aggiornata: «invalida la cache permessi al cambio di reparto di un utente e al cambio del catalogo o dei profili dei permessi». Verificare chi altro legge quel codice (viste di presidio, `job_run_log`, pgTAP) e allinearlo nello stesso giro. ⚠️ Le righe storiche di `maintenance.job_run_log` col codice vecchio: dire nella consegna se restano (storia) o se una FK le lega al catalogo. |

⛔ **Ordine**: il codice cambia a DB e nel BE **insieme**. Col DB avanti, il listener si presenterebbe
con un `application_name` che il catalogo non conosce più, e il presidio lo darebbe «muto» pur vivo;
col BE avanti, il contrario. Il BE si allinea appena il DB consegna (§5), prima del riavvio del
servizio.

## 5. Lato BE, a consegna DB fatta

* `apps/anagrafiche/services/notify_listener.py`: `LISTEN` anche su `permessi_catalogo`;
  `_handle_notification` smista per canale: `cambio_reparto` → `invalidate_user` (come oggi),
  `permessi_catalogo` → `invalidate_all` (che oggi esiste e non chiama nessuno).
* ⭐ **All'avvio e a ogni riconnessione** del listener, un `invalidate_all`: una notifica emessa
  mentre il processo era giù è persa (LISTEN/NOTIFY non accoda), e il migrate fatto con il
  listener spento è esattamente il caso da coprire.
* Il nome del canale in **una** costante, accanto a `CHANNEL`.
* Test in `anagrafiche/tests/services/test_notify_listener.py`: smistamento per canale, payload
  non valido ignorato, `invalidate_all` all'avvio.
* Il rinomino di §4: costante `PROCESSO_LISTEN_CAMBIO_REPARTO` → `PROCESSO_LISTEN_PERMESSI` in
  `core/services/processi.py`, command `listen_permessi` (ritirato `listen_cambio_reparto`), unità
  systemd `zeroerp-listen-permessi` (`backend/deploy/systemd/`, poi `install-timers.sh` sugli host:
  la vecchia unità va disabilitata), `sveglie.json`, il test `core/tests/services/test_sveglie.py`
  e i commenti che citano il nome vecchio, nello stesso giro.
