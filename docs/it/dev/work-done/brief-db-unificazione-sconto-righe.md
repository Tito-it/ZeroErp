# Brief DB — Unificazione nome colonna sconto sulle righe documento

**✅ ESEGUITO (2026-06-05).** DB: rename consegnato dal team DB (commit
`e65cc22e9` + migration `20260605-13/14/15` su `vendite.ordini_righe`,
`vendite.fatture_righe`, `acquisti.ordini_righe` + viste `20260605-16/17`) →
ora `sconto_percentuale` ovunque. BE+FE allineati e verificati (40 test ordini
verdi, `vite build` verde): `ordini_repository`/`ordini_service`/test,
`OrdiniRigaForm`/`OrdiniRigheTable`, doc API. **Residuo segnalato:** i doc
dbzero `manual/ordini_righe.md` e `manual/fatture_righe.md` citano ancora il
vecchio nome nella prosa (dominio team DB).

> **Tipo:** azione DB (DDL rename colonna + CHECK + viste/funzioni che la citano)
> → da eseguire dal **team DB** su `dev/db-tid` (cfr. `feedback_db_actions_passaggio_team`).
> **Origine:** emerso dalla regola del 2 FE (candidato B11, `useRigaArticoloComposito`),
> [regola-del-due-core-fe.md](regola-del-due-core-fe.md). Decisione Tid 2026-06-05:
> "Brief DB unificazione".
> **Priorità:** media (incoerenza di modello, non bug bloccante). Vale
> `feedback_bug_logici_modello` come segnalazione proattiva.

## Problema

Lo stesso concetto — sconto percentuale di riga — ha **due nomi colonna diversi**
fra tabelle gemelle dello stesso dominio `vendite`:

| Tabella | Colonna | Default | CHECK |
| --- | --- | --- | --- |
| `vendite.ordini_righe` | **`sconto_perc`** | _(nessuno)_ | `chk_ordini_v_r_sconto_perc` |
| `vendite.preventivi_righe` | **`sconto_percentuale`** | `0` | `chk_prevrighe_sconto` |

Fonte: [docs/it/dbzero/vendite/tabelle/ordini_righe.md](../../dbzero/vendite/tabelle/ordini_righe.md),
[preventivi_righe.md](../../dbzero/vendite/tabelle/preventivi_righe.md).

Doppia asimmetria: **nome** (`sconto_perc` vs `sconto_percentuale`) **e default**
(assente vs `0`). Si propaga a viste lista/dettaglio, funzioni di ricalcolo IVA,
guard trigger, e a ~15+ riferimenti BE per ciascun nome
(`ordini_repository`/`preventivi_repository`/`*_service`/`types`/`*_views`/test).

> **Da verificare anche:** `vendite.contratti_righe` e le eccezioni offerta
> (`offerta_*`), più `acquisti.ordini_righe` (usa `sconto_perc`): allineare tutto
> al nome scelto in un colpo solo evita di lasciare un terzo outlier.

## Impatto FE (nessun blocco)

Il FE è già stato reso tollerante al drift: la tabella righe è ora il BB
`RigheMasterDetailTable` (B10) con colonne via slot, quindi ogni dominio passa il
proprio `field=` (`sconto_perc` / `sconto_percentuale`) senza duplicazione di
logica. I form (`OrdiniRigaForm`/`PreventiviRigaForm`) mantengono il nome campo
nel proprio `form`/payload. Quindi **il FE non blocca**: si allinea dopo la
consegna DB (rename `field=`, chiave form, mapping payload). Nessun workaround
permanente lato FE.

## Proposta

Unificare su **`sconto_percentuale`** ovunque (più esplicito; già adottato da
preventivi col default `0` sensato):

1. **DDL** `ALTER TABLE vendite.ordini_righe RENAME COLUMN sconto_perc TO
   sconto_percentuale;` + `ALTER ... ALTER COLUMN sconto_percentuale SET DEFAULT 0;`
   (allinea anche il default). Idem per `acquisti.ordini_righe` e ogni altra
   `*_righe` che usi `sconto_perc`.
2. **CHECK** rinominare `chk_ordini_v_r_sconto_perc` → naming coerente con
   `chk_*_sconto` (verificare la condizione: stesso range 0–100 dei preventivi).
3. **Viste / funzioni** aggiornare ogni riferimento `sconto_perc`:
   `vw_ordini_righe_*`, `fn_ricalcola_riepilogo_iva_*`, `fn_offerta_righe_espanse`,
   guard trigger `trgfn_*righe_guard_pending`, ecc.
4. **Niente fase di compatibilità**: ZeroErp non è in produzione
   (`project_no_produzione_solo_sviluppo`) → breaking rename diretto, nessun
   alias temporaneo.

## Follow-up post-consegna DB (BE + FE)

- **BE**: rinominare i ~15 riferimenti `sconto_perc` in `ordini_repository.py`,
  `ordini_service.py`, `types.py`, `*_views.py`, test → `sconto_percentuale`.
  Whitelist payload/update keys incluse.
- **FE**: `OrdiniRigaForm` (`form.sconto_perc` → `sconto_percentuale`, payload),
  `OrdiniRigheTable` (colonna `field="sconto_perc"` → `sconto_percentuale`),
  filtri/export se citano il campo.

## Checklist consegna

- [x] DDL rename colonna + default su tutte le `*_righe` interessate
- [x] CHECK rinominato + condizione verificata
- [x] Viste/funzioni/trigger aggiornati e testati (pgTAP se presente)
- [x] BE+FE allineati dopo la consegna DB
