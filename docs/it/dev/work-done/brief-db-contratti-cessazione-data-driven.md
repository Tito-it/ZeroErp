# Brief DB — Cessazione contratti data-driven (`valido_al` ⇔ `stato_doc_contratto_id` CESSATO) [LANDED 2026-04-26]

> **Status**: ✅ **LANDED** — Team DB ha applicato trigger guard + job
> notturno il 2026-04-26. Vedi:
> - `db/changelog/migrations_v2/20_code/vendite/20260426-05-create-trgfn-contratti-guard-transizione-stato-mctit.yaml`
> - `db/changelog/migrations_v2/85_pgagent/20260426-06-replace-pgagent-job-chiusura-scadenze-daily-mctit.yaml`
> - Codici errore seedati: `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` (id 392), `E_AUTOMAZIONE_CHIUSURA_CONFIG_INVALIDA` (id 393)
>
> Variazione rispetto al brief originale: **stato SOSPESO rimosso completamente** dal modello (era previsto come stato intermedio non operativo). Workflow attuale: DRAFT → ATTIVO → CESSATO.
>
> ---
>
> **Target team**: DB (`dev/db-tid`)
> **Origine**: bug logico individuato 2026-04-25 dopo applicazione del Profilo A FE/BE su contratti vendite.
> **Impatto**: `vendite.contratti` (transizione stato CESSATO ⇔ valido_al)
> **Autore memo**: backend agent (`dev/backend-tid`)
> **Pattern di riferimento**: identico al brief `brief-db-listini-stato-chiusa-sync.md` (chiuso ✓ sui listini-versioni). Stesso identico problema, stessa identica soluzione applicata a un'altra entità.

## 1. Contesto

Dopo Profilo A su contratti, il FE espone un dialog "Cessa contratto" che chiede la data e fa POST `cambia-stato` con `valido_al`. Il service applicativo già implementa la regola fail-safe data-driven:

- `valido_al < CURRENT_DATE` → cessazione immediata (PATCH valido_al + UPDATE stato CESSATO in transazione)
- `valido_al >= CURRENT_DATE` → **cessazione programmata** (solo PATCH valido_al, lo stato resta ATTIVO/SOSPESO)
- `valido_al` NULL su CESSATO → rifiutato dal service (data obbligatoria)

**Manca lato DB** quanto già fatto sui listini-versioni:

- **Trigger guard** sulla tabella `vendite.contratti` che rifiuta la transizione manuale ATTIVO/SOSPESO → CESSATO se `valido_al >= CURRENT_DATE` o `IS NULL` (defense-in-depth: oggi un client che bypassa il service e fa UPDATE diretto può portare a stato CESSATO + validita' aperta = incoerenza)
- **Job notturno pgAgent** che allinea automaticamente `stato → CESSATO` quando `valido_al < CURRENT_DATE`. Senza job, le cessazioni programmate non vengono mai applicate

## 2. Decisione di design

Identica a listini-versioni:

> **Fonte di verità operativa = `validita` / `valido_al`. Lo `stato` è flag informativo eventualmente stantio.**

Il resolver / le query operative (es. `list_righe_preview` contratti) filtrano già per `validita @> CURRENT_DATE` data-driven. Il guard DB blocca lo stato incoerente, il job notturno fa il sync.

## 3. Richieste al team DB

### 3.1 Trigger guard transizione stato

Nome proposto: `trgfn_contratti_a10_guard_transizione_stato`

Logica (BEFORE UPDATE OF `stato_doc_contratto_id`):

| Vecchio stato | Nuovo stato | Ammesso? |
|---|---|---|
| DRAFT | ATTIVO | sì (attivazione) |
| ATTIVO | SOSPESO | sì (sospensione) |
| ATTIVO | CESSATO | **solo se** `valido_al IS NOT NULL AND valido_al < CURRENT_DATE` |
| SOSPESO | ATTIVO | sì (riattivazione) |
| SOSPESO | CESSATO | **solo se** `valido_al IS NOT NULL AND valido_al < CURRENT_DATE` |
| CESSATO | qualsiasi | **vietato** (terminale) |

Codice errore: `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA` (id da seedare in `config.messaggi_errore`).

L'UPDATE eseguito dal job notturno (3.2) passa il guard per costruzione (cambia stato solo quando `valido_al < CURRENT_DATE`).

### 3.2 Job notturno pgAgent

Nome proposto: `vendite.job_contratti_close_scadute` (eseguire a 00:05).

Funzione SQL incapsulante (parallelo a `vendite.fn_listini_versioni_close_scadute`):

```sql
CREATE OR REPLACE FUNCTION vendite.fn_contratti_close_scadute()
RETURNS integer
LANGUAGE plpgsql
AS $$
DECLARE
    v_count integer;
    v_id_cessato bigint;
BEGIN
    SELECT id INTO v_id_cessato
      FROM config.stati_doc_contratti
     WHERE codice_interno = 'CESSATO';

    UPDATE vendite.contratti
       SET stato_doc_contratto_id = v_id_cessato
     WHERE stato_doc_contratto_id IN (
              SELECT id FROM config.stati_doc_contratti
               WHERE codice_interno IN ('ATTIVO', 'SOSPESO')
           )
       AND valido_al IS NOT NULL
       AND valido_al < CURRENT_DATE;

    GET DIAGNOSTICS v_count = ROW_COUNT;
    RETURN v_count;
END;
$$;
```

Alternativa più snella: subquery direttamente nell'UPDATE del job (no funzione).

### 3.3 Back-fill eventuale

Verificare se esistono contratti già in stato CESSATO con `valido_al IS NULL` (incoerenza pre-fix):

```sql
SELECT count(*)
  FROM vendite.contratti c
  JOIN config.stati_doc_contratti sd ON sd.id = c.stato_doc_contratto_id
 WHERE sd.codice_interno = 'CESSATO'
   AND c.valido_al IS NULL;
```

Se > 0 (probabile zero in dev), back-fill con `data_update::date` prima di landare il guard 3.1.

## 4. Impatto BE (già pianificato su `dev/backend-tid`)

Già fatto:

- `apps/vendite/services/contratti_service.py::cambia_stato`: regola data-driven (immediata vs programmata) + validazioni (data >= valido_dal, data obbligatoria per CESSATO)
- 4 nuovi test service che coprono i 3 scenari + scenario "senza valido_al"
- Helper `_assert_contratto_draft` / `_assert_contratto_draft_from_riga` (Profilo A)

## 5. Impatto FE (già pianificato su `dev/backend-tid`)

Già fatto:

- Dialog "Cessa contratto" con DatePicker default oggi
- Titoli/messaggi/conferma differenziati per cessazione **immediata** (severity danger) vs **programmata** (severity warn) in base alla scelta utente
- Toast success differenziato (`Cessazione programmata al {data}` vs `Contratto cessato`)
- Campo `valido_al` mostrato readonly come "Cessazione programmata al" in stato ATTIVO/SOSPESO se valido_al è valorizzato
- i18n IT/EN aggiornate

## 6. Ordine di landing consigliato

1. 3.3 back-fill (se necessario)
2. 3.1 trigger guard (in `20_code/vendite/`)
3. 3.2 funzione + job pgAgent (funzione in `20_code/vendite/`, job in `85_pgagent/`)
4. Smoke test:
   - Programmare cessazione contratto al 2026-12-31 → verificare stato resta ATTIVO + valido_al impostato
   - Programmare cessazione al CURRENT_DATE - 1 → verificare stato passa a CESSATO subito (immediata)
   - Tentare UPDATE diretto stato → CESSATO con valido_al futuro via SQL → verificare guard rifiuta `E_CONTRATTO_STATO_TRANSIZIONE_INVALIDA`
   - Eseguire `SELECT vendite.fn_contratti_close_scadute()` manualmente → verificare conta righe chiuse coerente

## 7. Riferimenti

- Pattern listini-versioni speculare: [`brief-db-listini-stato-chiusa-sync.md`](brief-db-listini-stato-chiusa-sync.md) (chiuso, già in produzione)
- Standard FE pattern: [`docs/it/dev/frontend/frontend-standards.md`](../frontend/frontend-standards.md) sezione "Transizione a stato terminale con data"
- Service BE: [`backend/apps/vendite/services/contratti_service.py:cambia_stato`](../../../backend/apps/vendite/services/contratti_service.py)
- Dialog FE: [`frontend/src/vendite/components/ContrattoDrawer.vue`](../../../frontend/src/vendite/components/ContrattoDrawer.vue)

---

*Brief redatto 2026-04-25. Aggiornare in coda con esito landing.*
