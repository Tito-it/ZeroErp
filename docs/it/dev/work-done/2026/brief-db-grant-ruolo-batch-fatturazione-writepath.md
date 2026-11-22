# Brief DB — Completare i GRANT del ruolo batch sul write-path fatturazione

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Azione GRANT/ruolo: spiega *cosa* manca e *perché*; il *come* (script grant,
> changeset/idempotenza) è del team DB.
>
> **Data**: 2026-06-19 · **Stato**: ✅ **APPLICATO E VERIFICATO (2026-06-19)** — grant
> sequenze (code-seq standalone) + INSERT/UPDATE su log/task_runs/event_log applicati;
> lo smoke reale supera la creazione lotto e il write-path. Provisioning ri-eseguito.
>
> **Origine**: smoke live a RLS enforced del driver `run_fatturazione_batch` (2026-06-19).
> Chiusi i gap tipo_doc e utility, il run reale raggiunge l'INSERT in `fatturazione_lotti`
> e fallisce con `permesso negato per la sequenza fatturazione_lotti_codice_seq`.
> Contesto RLS Path A: [brief-db-emittibili-lane-utility-id.md](brief-db-emittibili-lane-utility-id.md)
> e il brief RLS originale (canale sistema batch).

---

## 1. Contesto e problema

Il batch headless gira nel canale di sistema con il ruolo **`zeroerp_batch_fatturazione`**
(BYPASSRLS, RLS Path A). **Tutte** le funzioni del write-path fatturazione sono
**SECURITY INVOKER** (verificato: `script.fn_generate_codice`, `vendite.fn_log_event`,
`vendite.fn_log_pipeline_fase`, `vendite.fn_start/complete_lotto_task_run`,
`vendite.fn_select_attivita_fatturabili`, `vendite.fn_emit_attivita_fatturabili_da_commessa`):
girano quindi **coi privilegi del ruolo chiamante**, cioè il ruolo batch.

Il ruolo batch ha ricevuto i grant sulle **tabelle principali** (lotti / AF / fatture /
righe: S/I/U OK), ma **NON** su sequenze e tabelle ancillari del percorso. È un
**sottoinsieme parziale** dei privilegi che `zeroerp_app` (operatore) ha già — ed è per
questo che l'API on-demand (scope operatore) funziona e il batch no.

### Evidenza (audit grant: `zeroerp_app` vs `zeroerp_batch_fatturazione`)

| Oggetto | Priv | zeroerp_app | batch |
| --- | --- | --- | --- |
| `vendite.fatturazione_lotti_codice_seq` | USAGE | ✅ | ❌ |
| `vendite.fatture_numero_seq` | USAGE | ✅ | ❌ |
| `vendite.event_log` | INSERT | ✅ | ❌ |
| `vendite.fatturazione_lotti_task_runs` | INSERT/UPDATE | ✅ | ❌ |
| `vendite.attivita_fatturabili_log` | INSERT | ✅ | ❌ |
| `vendite.fatture_log` | INSERT | ✅ | ✅ (già ok) |

> Inoltre il ruolo batch ha USAGE su **nessuna** sequenza dello schema `vendite`
> (`fatturazione_lotti_codice_seq`, `fatture_numero_seq`, ecc.): la generazione codice
> (`fn_generate_codice` → `nextval`) fallisce subito.

---

## 2. Cosa serve (risultato atteso)

**Allineare i privilegi del ruolo `zeroerp_batch_fatturazione` a quelli di `zeroerp_app`
per l'intero write-path fatturazione** — non oggetto-per-oggetto (si itererebbe sul
prossimo mancante), ma in modo sistematico:

- **Sequenze**: `USAGE` su tutte le sequenze usate dai trigger genera-codice/numerazione
  del percorso (almeno `fatturazione_lotti_codice_seq`, `fatture_numero_seq`; verificare
  l'intero set fatturazione).
- **Tabelle ancillari**: `INSERT`/`UPDATE` dove il pipeline scrive: `event_log` (INSERT),
  `fatturazione_lotti_task_runs` (INSERT+UPDATE), `attivita_fatturabili_log` (INSERT), più
  eventuali tabelle log/riepiloghi IVA/fondi del percorso non ancora esercitate.

> Criterio robusto suggerito: **diff dei privilegi** `zeroerp_app` → `zeroerp_batch_fatturazione`
> sugli oggetti del perimetro fatturazione, e replicare i mancanti. Così il set è completo
> in un colpo, senza scoprire il prossimo a runtime.

---

## 3. Decisione / nota di sicurezza

- Il ruolo è **BYPASSRLS**: i suoi grant **definiscono il blast radius**. L'allineamento va
  fatto **solo sul perimetro fatturazione** (gli stessi oggetti che tocca `zeroerp_app` nel
  write-path), **non** schema-wide. Non concedere privilegi oltre quelli dell'operatore.
- **Scartare** l'alternativa "rendere SECURITY DEFINER le funzioni infrastrutturali"
  (`fn_generate_codice`, `fn_log_event`, …): sono generiche e usate da tutta l'app →
  cambierebbe la postura di sicurezza per ogni chiamante. Coerente con RLS Path A è
  **completare i grant del ruolo**, non spostare i privilegi nelle funzioni.

---

## 4. Criteri di accettazione

- `run_fatturazione_batch --modalita differita` e `--modalita immediata` (run reale, canale
  di sistema) completano: lotto creato, pipeline avanzata, fatture generate, **0 falliti**
  per permessi.
- Nessun grant al ruolo batch oltre il perimetro fatturazione (no privilegi extra rispetto
  a `zeroerp_app`).
- (Se applicabile) changeset grant idempotente, ripetibile in ogni ambiente.

---

## 5. Fuori scope

- BE: nessuna modifica. Il driver crea già il lotto con la grana corretta
  (emittente, tipo_doc, utility, competenza); il blocco residuo è **solo** di privilegi DB.
- Pull / discovery / guard tipo_doc: invariati.
