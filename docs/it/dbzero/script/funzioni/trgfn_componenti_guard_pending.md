{% include-markdown "it/dbzero/script/manual/trgfn_componenti_guard_pending.md" %}
# ⚙️ Funzione `trgfn_componenti_guard_pending`

```sql
CREATE FUNCTION trgfn_componenti_guard_pending()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_guard_pending()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- Scopo:
    --   Guard L3 generico BEFORE UPDATE per tabelle *_componenti BoM CASO A.
    --   Quando stato_approvazione_prezzo = PENDING (richiesta di approvazione
    --   prezzo out-of-policy in attesa di esito), blocca le modifiche ai
    --   campi struttura del componente.
    --
    --   Allowlist modificabile in PENDING:
    --     stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
    --     meta, data_update, user_update (audit automatico), tx_id.
    --
    --   Denylist (campi struttura comuni a tutte le tabelle *_componenti):
    --     <col_fk_padre> (dinamico, da TG_ARGV[0]),
    --     articolo_componente_id, componente_id, coeff_qta_snapshot,
    --     quantita, uom_operativa_id, factor_to_base, qta_operativa,
    --     prezzo_unitario, iva_id, origine_prezzo, ordine, attivo.
    --
    --   TG_ARGV[0]: nome colonna FK padre (es. 'riga_contratto_id',
    --               'eccezione_offerta_id').
    --
    --   Se la tabella viene estesa con nuove colonne struttura,
    --   aggiornare la denylist (pattern difensivo).
    v_col_fk_padre  text    := TG_ARGV[0];
    v_fk_changed    boolean := FALSE;
    v_fk_value      bigint;
BEGIN
    -- Attivo solo se il componente era gia' in PENDING prima dell'UPDATE
    IF OLD.stato_approvazione_prezzo IS DISTINCT FROM
       'PENDING'::config.stato_approvazione_prezzo
    THEN
        RETURN NEW;
    END IF;

    -- Confronto colonna FK padre (dinamico)
    EXECUTE format(
        'SELECT ($1).%I IS DISTINCT FROM ($2).%I',
        v_col_fk_padre, v_col_fk_padre
    ) USING NEW, OLD INTO v_fk_changed;

    -- Controlla campi struttura (statici, comuni a tutte le tabelle)
    IF v_fk_changed
    OR NEW.articolo_componente_id  IS DISTINCT FROM OLD.articolo_componente_id
    OR NEW.componente_id           IS DISTINCT FROM OLD.componente_id
    OR NEW.coeff_qta_snapshot      IS DISTINCT FROM OLD.coeff_qta_snapshot
    OR NEW.quantita                IS DISTINCT FROM OLD.quantita
    OR NEW.uom_operativa_id        IS DISTINCT FROM OLD.uom_operativa_id
    OR NEW.factor_to_base          IS DISTINCT FROM OLD.factor_to_base
    OR NEW.qta_operativa           IS DISTINCT FROM OLD.qta_operativa
    OR NEW.prezzo_unitario         IS DISTINCT FROM OLD.prezzo_unitario
    OR NEW.iva_id                  IS DISTINCT FROM OLD.iva_id
    OR NEW.origine_prezzo          IS DISTINCT FROM OLD.origine_prezzo
    OR NEW.ordine                  IS DISTINCT FROM OLD.ordine
    OR NEW.attivo                  IS DISTINCT FROM OLD.attivo
    THEN
        -- Recupera valore FK padre per contesto errore
        EXECUTE format('SELECT ($1).%I', v_col_fk_padre)
            USING OLD INTO v_fk_value;

        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_COMPONENTE_PREZZO_PENDENTE',
            jsonb_build_object(
                'componente_id',  OLD.id,
                v_col_fk_padre,   v_fk_value,
                'hint', 'Attendi esito approvazione (APPROVED/REJECTED) '
                     || 'prima di modificare il componente.'
            ),
            NULL::uuid,
            OLD.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_guard_pending()
IS 'Guard L3 BEFORE UPDATE generico per tabelle *_componenti BoM CASO A. Blocca modifiche ai campi struttura quando stato_approvazione_prezzo=PENDING. TG_ARGV[0] = nome colonna FK padre (es. ''riga_contratto_id'', ''eccezione_offerta_id''). Raise E_COMPONENTE_PREZZO_PENDENTE. Rev 2026-05-26 — generalizzazione di trgfn_*_componenti_guard_pending.';
```

</div>

---
{% include-markdown "signature-core.md" %}
