# Brief DB — GRANT ruolo batch sullo shadow `storico.*` del write-path fatturazione

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Azione GRANT/ruolo. **Follow-up** di
> [brief-db-grant-ruolo-batch-fatturazione-writepath.md](brief-db-grant-ruolo-batch-fatturazione-writepath.md)
> (G1-G3 applicati): chiuso il gap sequenze/log, lo smoke ha scoperto **un'altra dimensione
> del perimetro** non coperta.
>
> **Data**: 2026-06-19 · **Stato**: ✅ **APPLICATO E VERIFICATO (2026-06-19)** — INSERT/UPDATE
> sugli shadow `storico.*` del perimetro (fatturazione + commesse) applicati; lo smoke reale
> supera lo snapshot di storicizzazione. Provisioning ri-eseguito.

---

## 1. Sintomo (smoke reale 2026-06-19, post-G1/G2/G3)

```
run_fatturazione_batch --modalita differita
→ E_PIPELINE — Errore chiusura snapshot: permesso negato per la tabella fatturazione_lotti
  (SQLSTATE: 42501) [E_SNAPSHOT_CLOSE_ERROR]
  trgfn_storico_generic() … UPDATE vendite.fatturazione_lotti … fn_get_or_create_lotto
```

La creazione lotto + codice-seq ora passano. Ma `fn_get_or_create_lotto` fa **UPDATE su
`vendite.fatturazione_lotti`** → scatta il trigger di storicizzazione `trgfn_storico_generic`
(SECURITY INVOKER, gira come ruolo batch) che scrive lo snapshot nello schema **`storico`** →
permesso negato.

## 2. Causa — perimetro non esteso allo shadow `storico`

Il provisioning enumera il perimetro sulle tabelle `vendite.*`, ma **non sulle controparti
`storico.*`** che i trigger di storicizzazione scrivono ad ogni INSERT/UPDATE. Il ruolo
batch ha già `USAGE` sullo schema `storico`, ma **nessun privilegio tabella**.

### Evidenza (audit `zeroerp_app` vs `zeroerp_batch_fatturazione`)

| storico.* (write-path storicizzato) | app (I/U) | batch (I/U) |
| --- | --- | --- |
| `storico.fatturazione_lotti` | ✅/✅ | ❌/❌ |
| `storico.attivita_fatturabili` | ✅/✅ | ❌/❌ |
| `storico.fatture` | ✅/✅ | ❌/❌ |
| `storico.fatture_righe` | ✅/✅ | ❌/❌ |

Schema `storico` USAGE: batch = ✅ (già presente). Mancano solo i privilegi tabella.
Tutte e 4 le tabelle del write-path hanno trigger di storicizzazione (`*all` automation).

## 3. Cosa serve (fix sistematico, non tabella-per-tabella)

Estendere il provisioning del ruolo batch con la regola:

> **per ogni tabella del `_perimeter` che ha un trigger di storicizzazione, concedere al
> ruolo batch `INSERT + UPDATE` sulla controparte `storico.<tabella>`.**

- **INSERT + UPDATE** (entrambi): lo snapshot SCD fa INSERT della nuova versione **e**
  UPDATE del `valid_to`/chiusura della precedente (l'errore è proprio sulla *chiusura*).
- Derivazione automatica dal perimetro esistente (join sui trigger `trgfn_storico_generic`),
  così la regola **non va tenuta in sync a mano** e chiude la classe per sempre.
- Coerente col principio del brief padre: perimetro **enumerato/asserito staticamente**,
  niente whack-a-mole.

> Nota posture/sicurezza: le `storico.*` sono append/versioning interno; INSERT+UPDATE sono
> il minimo per la storicizzazione. **No DELETE.** Restano BYPASSRLS-scoped al solo perimetro
> fatturazione (le storico delle altre aree non vengono toccate).

## 4. Criteri di accettazione

- `run_fatturazione_batch --modalita differita` e `--modalita immediata` (run reale) →
  lotto creato, pipeline avanzata, **fatture generate**, **0 falliti** per permessi
  (incluso lo snapshot di storicizzazione).
- Ruolo batch: `INSERT+UPDATE` sulle 4 `storico.*` del perimetro, **niente DELETE**, niente
  privilegi su `storico.*` fuori perimetro.
- Posture pgTAP esteso: asserisce anche lo shadow storico (I/U presenti, DELETE assente).

## 5. Deliverable (per il team DB)

| # | File | Modifica |
| --- | --- | --- |
| S1 | `scripts/sql/provision_db_role_batch_fatturazione.sql` | per ogni `_perimeter` con trigger storico → `GRANT INSERT, UPDATE ON storico.<t>` |
| S2 | `scripts/sql/check_db_role_batch_fatturazione.sql` | check buchi/over-grant esteso allo shadow storico |
| S3 | `db/pgtap/rls/test-role-batch-fatturazione-postura.sql` | asserzioni I/U presenti + DELETE assente sulle 4 `storico.*` |

### Applicazione (lato Tid), poi smoke
1. Rieseguire il provisioning (idempotente).
2. `./manage-env.sh run_fatturazione_batch --modalita differita` → atteso **0 falliti**.

## 6. Fuori scope
- BE: nessuna modifica (il driver crea già il lotto con la grana corretta).
- Questo è **l'ultimo strato del write-path** noto: chiuso lo storico, lo smoke dovrebbe
  completare end-to-end.
