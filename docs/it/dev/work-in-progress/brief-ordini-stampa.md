# Brief DB — Stampa documento ordine (PDF)

> **Origine**: richiesta Tid 2026-06-04. Estensione del §12 dell'analisi ordini
> (`analisi-ordini-vendita.md`). Questo brief copre **solo il workstream DB**
> (§12.1): è il prerequisito che BE/FE attendono
> (`feedback_be_fe_attende_prerequisiti_db`).
>
> **Principio**: ordini è il **quarto dominio** cablato sul motore `documenti`
> già usato da preventivi / offerte commerciali / contratti
> (`guide/documenti-e-stampe.md`). **Niente nuovo motore, niente nuove tabelle**:
> il lavoro DB è **un solo seed di lookup** (il tipo documento). I **template**
> HTML/CSS si creano **manualmente** (come per gli altri tre domini), fuori dal
> seed Liquibase.

---

## 1. Decisioni prese (Tid, 2026-06-04)

1. **Template → gestione manuale.** I template `documenti.template_documenti` +
   `template_documenti_versioni` per ordini si creano a mano (come finora per
   preventivo/offerta/contratto). **Non** entrano nel seed Liquibase. → il
   workstream DB si riduce al solo tipo documento (§3).
2. **Codice tipo documento = `ORDINE_VENDITA`** (non `ORDINE_CLIENTE`). Coerente
   con la sorgente `config.sorgenti.codice='ORDINE_VENDITA'` e con il
   `context_builder_code='ORDINE_VENDITA'` previsto lato BE (§12.0.2 analisi).
   Allinea ordini alla famiglia (`PREVENTIVO`/`CONTRATTO`/`OFFERTA_COMMERCIALE`:
   tipo documento = nome sorgente).

---

## 2. Stato verificato (2026-06-04)

Contro il codice attuale (`db/changelog/migrations_v2/`):

| Elemento | Stato | Azione |
| --- | --- | --- |
| `config.sorgenti` `ORDINE_VENDITA` | ✅ presente, `id=6`, attivo (`sorgenti.csv`) | **nessuna** — riuso |
| `documenti.tipi_documento_output` `ORDINE_VENDITA` | ❌ assente (CSV aveva solo PREVENTIVO/CONTRATTO/OFFERTA_COMMERCIALE) | **seed nuova riga** → §3 |
| Tabelle motore `documenti.*` | ✅ esistenti e collaudate | nessuna — riuso |
| Template ordine | gestione manuale | fuori scope DB |

> **Tabelle motore (riuso, già collaudate)**: `tipi_documento_output`,
> `template_documenti`, `template_documenti_versioni`, `documenti_generati`,
> lookup `tipi_asset_documento`/`tipi_file_documento`/`render_engine_documento`.
> Pubblicazione versione template (lato manuale):
> `documenti.fn_pubblica_template_documento_versione`
> (immutabilità post-pubblicazione via trigger protect — ogni modifica = nuova
> versione; senza versione **PUBBLICATA** la generazione fallisce,
> `documenti-e-stampe.md` §2.3).

---

## 3. Workstream DB — unico deliverable: seed tipo documento

### 3.1 Riga seedata

Aggiunta a `80_data/sql/documenti/tipi_documento_output.csv`:

```csv
4,ORDINE_VENDITA,ORDINE_VENDITA,Ordine vendita,true,{},"true",2026-06-04 00:00:00,titodb,2026-06-04 00:00:00,titodb,NULL
```

(`id=4` — prossimo libero; `codice`/`codice_interno=ORDINE_VENDITA`;
`attivo=true`; `meta={}`; `storicizza=true`.)

### 3.2 Meccanismo di applicazione

**Nessun nuovo changeset.** Il CSV è caricato dal changeset seed-base
`80_data/changelog/20260429-58-upsert-documenti-seed-base-mctit.yaml`, che è
`runOnChange: true` + `validCheckSums: ANY` (`loadUpdateData`, upsert per
`primaryKey: id`): è stato progettato apposta per la **crescita del seed**.
Aggiungendo la riga, alla prossima migrazione il changeset si ri-applica e fa
upsert della nuova riga. Una sola fonte di verità per il lookup.

> ⚠️ **Da confermare col team DB** (`feedback_db_actions_passaggio_team`):
> append al CSV canonico (scelta attuale) **oppure** CSV+changeset dedicato.
> La scelta non cambia il dato finale, solo l'organizzazione del seed.

### 3.3 Test pgTAP

`db/pgtap/documenti/test-documenti-tipo-ordine-vendita.sql` (4 test):

1. `ORDINE_VENDITA` presente in `tipi_documento_output`;
2. `ORDINE_VENDITA` attivo;
3. sorgente `ORDINE_VENDITA` presente e attiva in `config.sorgenti` (guardia riuso);
4. nessun `codice` duplicato (idempotenza seed).

Esecuzione: `scripts/testpgtap.sh db/pgtap/documenti/test-documenti-tipo-ordine-vendita.sql`.

---

## 4. Stato implementazione — ✅ EVASO (DB), 2026-06-04

- [x] Riga `ORDINE_VENDITA` aggiunta a `tipi_documento_output.csv`
- [x] Test pgTAP `test-documenti-tipo-ordine-vendita.sql`
- [x] Migrazione locale applicata (`make db-migrate`)
- [x] Test pgTAP eseguito e **verde**
- [ ] Commit / PR — **attende "procedi"** (`feedback_no_commit_autonomo`)

> Il workstream DB di questo brief è **chiuso**: il tipo documento
> `ORDINE_VENDITA` è seedato e risolvibile. Resta solo il commit/PR su conferma.
> Tutto il resto (template manuale, context builder BE, view stampa, azione FE)
> è **fuori scope DB** → §5.

---

## 5. Confini e seguito (fuori da questo brief)

- **Indipendente** dall'estensione modello ordini A+E (§3.0 analisi): parallelo.
- **A valle** (coperti da §12.2/§12.3 analisi, lato BE/FE):
  - context builder BE con `CODE='ORDINE_VENDITA'` nel registry
    (`apps/documenti/services/context_builders/`);
  - view stampa ordini con `_CODICE_SORGENTE_ORDINE = "ORDINE_VENDITA"`;
  - creazione **manuale** del template + versione PUBBLICATA (HTML conferma
    d'ordine: clone layout preventivo/offerta, senza revisioni/listino testata,
    `+fatturazione_trigger`, eventuali chip `documento_origine`/`agente`);
  - azione FE "Stampa" sul dominio ordini.
  - BE/FE **attendono** la delivery di questo seed.
