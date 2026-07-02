# Brief DB — Disinnesco binding `vendita.push_preventivo` (unbind + deprecate, **zero DELETE**)

> **Tipo**: brief DB (solo UPDATE idempotenti, nessuna cancellazione) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟢 bassa (chiude l'ultimo residuo di uniformità pratica preventivi)
> **Data**: 2026-07-02 · **Stato**: ✅ **FATTO** (2026-07-02) — applicato e testato (pgTAP verdi).
>
> **Esito consegna DB**: unbind `template_flussi.handler_id` sui CONFERMA di
> IMMEDIATA/DIFFERITA (niente più `E_HANDLER_NON_REGISTRATO`); `handler_flussi
> 'vendita.push_preventivo'` → `attivo=false` (riga conservata, senza binding);
> `tipi_prestazione.obsoleto_dal=2026-06-30` su IMMEDIATA/DIFFERITA (istanze esistenti vive,
> guard blocca solo le nuove); B8 `regole_generazione` 9001 → `attivo=false`;
> `fn_push_preventivo_a_ordine` intatta. Implementazione: seed `runOnChange`
> (template_flussi/tipi_prestazione/regole_generazione csv) + changeset `20260702-01` per la
> sola disattivazione handler (ordine 07→08); pgTAP `test-seed-pratica-preventivi.sql`
> aggiornato. **Tutti i criteri §4 soddisfatti.**
>
> **Origine**: residuo di [analisi-uniformita-pratica-preventivi.md](analisi-uniformita-pratica-preventivi.md)
> §7.3 / tracker [piano-be-fe-uniformita-pratica-preventivi.md](../work-in-progress/piano-be-fe-uniformita-pratica-preventivi.md) (Fase 3).

## 1. Il problema reale (landmine, non "ritiro")

`obsoleto_dal` **chiude già** i tipi 9002/9003 (`PREVENTIVI_IMMEDIATA`/`DIFFERITA`): blocca le
**nuove** pratiche via guard `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`, e le istanze esistenti
continuano a vivere. **Nessun tipo/istanza va cancellato o ritirato.**

Il residuo è **solo un riferimento pendente**: il BE (branch `dev/backend-tid`, 2026-07-02) ha
già rimosso l'handler Python `vendita.push_preventivo` (classe + registrazione + test; `check`
verde, 63 test verdi), **ma a DB i template `CONFERMA` di 9002/9003 hanno ancora
`handler_id = 9001`**. Se una di quelle istanze stale completasse la CONFERMA, il dispatch
cercherebbe `vendita.push_preventivo` → `E_HANDLER_NON_REGISTRATO`. Dev-only, basso rischio, ma
è un binding verso un handler che non esiste più: **va disinnescato**.

## 2. Vincoli — cosa NON si tocca

- **Nessun DELETE**: niente cancellazione di istanze (`pratiche`/`flussi`), tipi
  (`tipi_prestazione`), template, o righe seed. Solo `UPDATE`.
- **`vendite.fn_push_preventivo_a_ordine` resta**: è la primitiva di copia righe
  preventivo→ordine, **tuttora usata** dal nuovo SMISTAMENTO. Il disinnesco riguarda
  l'*handler orchestratore*, non questa funzione.
- **Seed mergiati non toccati**: il changeset li **supera** e gira per ultimo (nessuna
  riscrittura dei seed storici).

## 3. Piano — un solo changeset idempotente, tutto UPDATE

`20260702-NN` (ordine vincolante: unbind **prima** del deactivate):

1. **Unbind dei template CONFERMA** (rimuove il landmine):
   ```sql
   UPDATE pratiche.template_flussi
      SET handler_id = NULL
    WHERE handler_id = (SELECT id FROM pratiche.handler_flussi
                         WHERE handler_key = 'vendita.push_preventivo');
   ```
   Tocca i CONFERMA di 9002/9003 (il catalogo attivo 9004 non è bound a questo handler). Le
   istanze esistenti di quei flussi, completando, non dispatchano più nulla.

2. **Deprecare l'handler** (dopo l'unbind: `prevent_deactivate_if_children` blocca finché i
   template lo referenziano):
   ```sql
   UPDATE pratiche.handler_flussi
      SET attivo = false
    WHERE handler_key = 'vendita.push_preventivo';
   ```
   Riga **conservata** (audit), morta e senza binding. *(Decisione confermata: `attivo=false`,
   non DELETE.)*

3. **Assicurare l'obsolescenza dei tipi** (no-op se già valorizzata):
   ```sql
   UPDATE pratiche.tipi_prestazione
      SET obsoleto_dal = DATE '2026-06-30'
    WHERE codice_interno IN ('PREVENTIVI_IMMEDIATA','PREVENTIVI_DIFFERITA')
      AND obsoleto_dal IS NULL;
   ```

4. **B8 — disabilitare la regola smoke** (ora necessaria: con 9003 obsoleto, la regola che
   genera una pratica 9003 sbatterebbe nel guard obsoleto):
   ```sql
   UPDATE pratiche.regole_generazione SET attivo = false WHERE id = 9001;
   ```

## 4. Criterio di accettazione

- Nessun `pratiche.template_flussi.handler_id` punta più all'handler `vendita.push_preventivo`.
- `pratiche.handler_flussi` `vendita.push_preventivo` → `attivo=false` (riga presente, senza binding).
- `tipi_prestazione` 9002/9003 con `obsoleto_dal` valorizzato.
- `regole_generazione` id 9001 → `attivo=false`.
- **`fn_push_preventivo_a_ordine` intatta** e usata dal giro SMISTAMENTO.
- Smoke `smoke-test-pratica-preventivi-bivio.sh` resta verde (usa 9004).
- Eventuali pgTAP che asseriscono il vecchio stato (handler attivo / binding presente) →
  aggiornati alla nuova asserzione (unbound + `attivo=false`).

## 5. Nota di coordinamento

Il BE è già rimosso su `dev/backend-tid`. Finché questo changeset non gira, in dev resta il
binding pendente (dispatch di una CONFERMA 9002/9003 → `E_HANDLER_NON_REGISTRATO`, fail-fast).
Nessuna istanza attiva attesa; a merge/apply del changeset il residuo è chiuso.

---

*✅ Consegnato e chiuso (2026-07-02). Questo brief e l'analisi
`analisi-uniformita-pratica-preventivi.md` sono in `work-done/`; il tracker
`piano-be-fe-uniformita-pratica-preventivi.md` resta in `work-in-progress/` marcato COMPLETO.*
