# Brief DB — GRANT ruolo batch per il worker coda stampa (C-2b)

> ## ✅ RISOLTO 2026-07-21 — archiviato in work-done
>
> Il team DB ha aggiunto il perimetro di scrittura al provisioning **versionato**
> `scripts/sql/provision_db_role_batch_fatturazione.sql` (eseguito dalla CI, step
> «Provision ruolo batch»):
> * `vendite.fatture_stampa_coda` → grade **`u`** (il drainer fa solo claim/marca/reaper);
> * `documenti.documenti_generati` / `_file` / `_eventi` → grade **`i`** (render = solo
>   INSERT append, verificato: nessun UPDATE/DELETE su quelle 3 tabelle nel path);
> * le SEQUENCE identity si auto-concedono via il join `pg_depend` dello script; il read
>   del path (fatture/righe/riepiloghi/emittenti/template/config) è coperto dal SELECT
>   schema-wide.
>
> **Riproducibile in CI** (non applicato a mano): il ruolo batch è `NOSUPERUSER BYPASSRLS`
> anche in CI, ma la CI non *esegue* `draina_coda_stampa` → il gap era invisibile finché il
> worker non ha girato davvero sul DB dev (per questo lo smoke reale è indispensabile,
> [[feedback_audit_db_preventivo_smoke]]).
>
> **Verifica (DoD) superata**: `draina_coda_stampa` post-grant → `job_run_log ok=True`
> (coda vuota; il render end-to-end si esercita con una stampa reale ora che P-3 è a posto).
>
> Documento archiviato come record del problema trovato + fix. Resta valido il **§4**
> (residuo `run_as=SISTEMA` su `dbops.coda_lavori`) per quando nascerà un job di sistema.

---

> **Tipo**: brief DB al team (azione GRANT) · **Target**: `dev/db-tid` · **Data**:
> 2026-07-21 · **Owner richiesta**: BE (cockpit fatturazione, Fase C) · **Priorità**:
> **bloccante** per il deploy del worker `draina_coda_stampa`.
>
> Regola: le azioni DB non partono dall'agent — questo è il brief scritto
> ([[feedback_db_actions_passaggio_team]]). Nessuna migration proposta qui: il team
> DB sceglie meccanismo e file (aggiungo solo il fabbisogno e l'evidenza).

## 1. Problema (trovato con smoke reale)

Il worker `python manage.py draina_coda_stampa` (Fase C C-2b) gira nel **canale di
sistema** sul ruolo **`zeroerp_batch_fatturazione`** (BYPASSRLS, alias
`system_fatturazione`) e fa **SQL diretto** sulla coda stampa. Lo smoke run sul DB dev
fallisce al primo tocco di tabella:

```
django.db.utils.ProgrammingError: permesso negato per la tabella fatture_stampa_coda
# job_run_log: jobname=draina_coda_stampa origine=CRON ok=False
```

**Causa.** `BYPASSRLS` salta la Row Level Security, **non** i privilegi di tabella
(`GRANT`). Il ruolo `zeroerp_batch_fatturazione`:

* **NON è membro** di `zeroerp_app` (`pg_auth_members` vuota per questi ruoli) → **non
  eredita** i grant dell'app;
* ha i propri grant sulle tabelle che il batch `run_fatturazione_batch` già usava, ma
  la tabella **`vendite.fatture_stampa_coda`** (nuova, G1) — e verosimilmente il resto
  del path di render documentale — **non gli sono stati concessi**.

Gap **latente da quando C-2b è stato committato** (#1032): il worker stampa non ha mai
potuto girare. Emerso solo ora con lo smoke (i test mock non vedono i GRANT —
[[feedback_audit_db_preventivo_smoke]]).

> Per contrasto: `draina_coda_lavori` (coda generica) gira **ok=True**. I suoi job odierni
> sono `run_as=OPERATORE` → girano sul ruolo **app** (`zeroerp_app`, RLS attiva) che ha i
> grant. Il ruolo batch gli servirebbe solo per eventuali job `run_as=SISTEMA` (nessuno
> seedato oggi — vedi §4).

## 2. Fabbisogno — privilegi del ruolo batch sul path di render stampa

Il drainer + `DocumentGenerationService.genera_documento` (contesto sistema, `user=None`,
`emittente_scope=None`) toccano in SQL diretto queste tabelle. Il ruolo
`zeroerp_batch_fatturazione` deve poterle usare con la stessa DML del ruolo `zeroerp_app`
(che sul path web renderizza già correttamente):

| Tabella | DML del path | Note |
| --- | --- | --- |
| `vendite.fatture_stampa_coda` | **SELECT, UPDATE** | claim (`FOR UPDATE SKIP LOCKED`), marca fatto/errore, reaper, count — **blocco confermato** |
| `vendite.fatture` | SELECT | testata + risoluzione PK emittente (JOIN) |
| `vendite.fatture_righe` | SELECT | righe per il context builder FATTURA |
| `vendite.fatture_riepiloghi_iva` | SELECT | riepilogo IVA (tabella reale) |
| `anagrafiche.emittenti_fiscali` | SELECT | JOIN PK emittente da SR |
| `documenti.documenti_generati` | SELECT, INSERT | esito documento |
| `documenti.documenti_generati_eventi` | INSERT | audit evento |
| `documenti.documenti_generati_file` | INSERT | file prodotto |
| `documenti.template_documenti` (+ `_versioni`, `template_asset`, `tipi_asset_documento`, `tipi_documento_output`, `render_engine_documento`) | SELECT | risoluzione template/asset/output |
| `config.parameters`, `config.sorgenti` | SELECT | parametri + risoluzione sorgente FATTURA |
| eventuali **SEQUENCE** delle tabelle in INSERT (`documenti.*`) | USAGE | per i `nextval` |

> `vendite.fn_numera_fattura_opz_emessa` (backstop C-2d) è chiamata come funzione: se è
> `SECURITY DEFINER` (owner `titodb`) al ruolo batch basta `EXECUTE`; verificare.

**La lista sopra è il path noto**; per non fare whack-a-mole conviene che il team DB
allinei i privilegi del ruolo batch **all'intero path di render** (mirror di ciò che ha
`zeroerp_app` su quelle tabelle/sequence), oppure valuti un meccanismo di gruppo. **Scelta
del meccanismo al team DB** (grant espliciti per tabella vs. ruolo-gruppo condiviso vs.
membership selettiva): il ruolo batch è stato volutamente ristretto nel brief
`work-done/brief-db-contesto-sistema-batch-fatturazione-rls.md`, quindi la membership piena
in `zeroerp_app` potrebbe over-grant — decidere lì.

## 3. Verifica (definition of done)

Con un lotto DEFINITIVO che ha accodato righe in `fatture_stampa_coda` (o una riga PENDING
di prova), sul DB dev:

```bash
cd backend && set -a && source ./env.sh && source ./.env.systemd && set +a
bin/run-command.sh draina_coda_stampa --limit 5
# atteso: nessun 'permesso negato'; job_run_log ok=True; righe coda → FATTO/ERRORE
#         (ERRORE di dominio ok: è il template/dato, non più un grant)
```

`SELECT jobname, ok, error_code FROM maintenance.job_run_log WHERE jobname='draina_coda_stampa' ORDER BY id DESC LIMIT 1;`

## 4. Fuori perimetro (ma da tenere presente)

* **Job `run_as=SISTEMA` sulla coda generica**: nessuno seedato oggi (`FATTURAZIONE_GIRO`
  è OPERATORE). Quando ne nascerà uno, il drainer `draina_coda_lavori` per quel job userà
  il ruolo batch → servirà GRANT del ruolo batch anche su `dbops.coda_lavori`
  (SELECT/UPDATE) + le tabelle di quel job. Non urgente adesso.
* Nessuna modifica a RLS: qui è **solo** privilegio di tabella (GRANT/USAGE).
