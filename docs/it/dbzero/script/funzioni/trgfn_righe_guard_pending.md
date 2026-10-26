{% include-markdown "it/dbzero/script/manual/trgfn_righe_guard_pending.md" %}
# ⚙️ Funzione `trgfn_righe_guard_pending`

```sql
CREATE FUNCTION trgfn_righe_guard_pending()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_guard_pending()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Scopo:
    --   Guard L3 generico BEFORE UPDATE per le tabelle RIGA-LEVEL del
    --   sotto-sistema approvazione prezzo (preventivi_righe,
    --   contratti_righe, offerte_commerciali_eccezioni).
    --   Quando la riga era in stato_approvazione_prezzo = 'PENDING'
    --   (richiesta L3 out-of-policy in attesa di esito), blocca le
    --   modifiche ai campi struttura: l'approvatore deve decidere
    --   sulla riga ESATTA proposta.
    --
    --   Strategia ALLOWLIST (non denylist): si confronta to_jsonb(OLD)
    --   vs to_jsonb(NEW) dopo aver rimosso i campi ammessi in PENDING.
    --   Qualsiasi residuo diverso -> raise. Robusto all'aggiunta di
    --   nuove colonne; uniforme tra tabelle con strutture diverse.
    --
    --   Allowlist (modificabili in PENDING):
    --     stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
    --     meta, data_update, user_update (audit framework), tx_id.
    --
    --   TG_ARGV[0]: nome colonna FK padre (es. 'preventivo_id',
    --     'contratto_id', 'offerta_id') — solo per contesto errore.
    v_col_fk_padre  text := TG_ARGV[0];
    v_allow         CONSTANT text[] := ARRAY[
        'stato_approvazione_prezzo',
        'pratica_approvazione_prezzo_id',
        'meta',
        'data_update',
        'user_update',
        'tx_id'
    ];
    v_old_struct    jsonb;
    v_new_struct    jsonb;
    v_campi_mod     text[];
    v_fk_value      text;
BEGIN
    -- Attivo solo se la riga era gia' PENDING prima dell'UPDATE.
    IF OLD.stato_approvazione_prezzo IS DISTINCT FROM
       'PENDING'::config.stato_approvazione_prezzo THEN
        RETURN NEW;
    END IF;

    -- Rimuove i campi workflow/audit e confronta il resto della riga.
    v_old_struct := to_jsonb(OLD) - v_allow;
    v_new_struct := to_jsonb(NEW) - v_allow;

    IF v_old_struct IS DISTINCT FROM v_new_struct THEN
        -- Raccoglie i campi struttura modificati per il contesto errore.
        SELECT array_agg(k ORDER BY k)
          INTO v_campi_mod
          FROM jsonb_object_keys(v_old_struct) AS k
         WHERE (v_old_struct -> k) IS DISTINCT FROM (v_new_struct -> k);

        v_fk_value := to_jsonb(NEW) ->> v_col_fk_padre;

        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_RIGA_PREZZO_PENDENTE',
            jsonb_build_object(
                'riga_id',          OLD.id,
                v_col_fk_padre,     v_fk_value,
                'campi_modificati', v_campi_mod,
                'hint', 'Attendi esito approvazione (APPROVED/REJECTED) '
                     || 'o rifiuta la richiesta prima di modificare la riga.'
            ),
            NULL::uuid,
            OLD.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_guard_pending()
IS 'Guard L3 BEFORE UPDATE generico per tabelle RIGA-LEVEL approvazione prezzo (preventivi_righe, contratti_righe, offerte_commerciali_eccezioni). Blocca modifiche ai campi struttura quando stato_approvazione_prezzo=PENDING, via ALLOWLIST su to_jsonb (workflow/audit ammessi). TG_ARGV[0] = nome colonna FK padre per contesto errore. Raise E_RIGA_PREZZO_PENDENTE (390). Rev 2026-06-01 — estrazione di trgfn_{preventivi,contratti}_righe_guard_pending.';
```

</div>

---
{% include-markdown "signature-core.md" %}
