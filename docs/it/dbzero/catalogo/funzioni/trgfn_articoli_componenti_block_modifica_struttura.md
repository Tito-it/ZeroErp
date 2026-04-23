{% include-markdown "it/dbzero/catalogo/manual/trgfn_articoli_componenti_block_modifica_struttura.md" %}
# ⚙️ Funzione `trgfn_articoli_componenti_block_modifica_struttura`

```sql
CREATE FUNCTION trgfn_articoli_componenti_block_modifica_struttura()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION catalogo.trgfn_articoli_componenti_block_modifica_struttura()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   Garantire che la struttura di una BoM sia immutabile
    --   una volta inserita. Pattern admin "chiudi+inserisci":
    --   per correggere si chiude la riga esistente (UPDATE
    --   valido_al alla data di fine) e si inserisce una
    --   nuova riga con valido_dal successivo. L'EXCLUDE
    --   constraint ex_articoli_componenti_no_overlap
    --   garantisce non-overlap sul triplo (prodotto,
    --   componente, validita).
    --
    -- Regole:
    --   1. DELETE -> bloccato sempre (E_BOM_MODIFICA_VIETATA).
    --   2. UPDATE dei campi di struttura -> bloccato
    --      (coeff_qta, componente_id, obbligatorio,
    --      esposto_in_fattura, partecipa_qta,
    --      determina_qta_padre, valido_dal, validita).
    --      Nota: validita e' incluso per difesa in
    --      profondita' anche se a20_set_validita lo
    --      ricalcola da valido_dal/valido_al.
    --   3. UPDATE di solo valido_al ammesso + check
    --      NEW.valido_al >= OLD.valido_dal -> altrimenti
    --      E_BOM_VALIDO_AL_INVALIDO (chk_articoli_componenti_valid_dates
    --      esistente copre > ma diamo error code custom
    --      UI-friendly per il caso <).
    --   4. UPDATE di campi note/meta/attivo + audit
    --      (user_update/data_update/tx_id) -> ammesso.
    -- =========================================================

    IF TG_OP = 'DELETE' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_BOM_MODIFICA_VIETATA',
            jsonb_build_object(
                'operazione',    'DELETE',
                'hint',          'Chiudi la riga impostando valido_al invece di eliminarla.',
                'prodotto_id',   OLD.prodotto_id,
                'componente_id', OLD.componente_id,
                'riga_id',       OLD.id
            ),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]
        );
    END IF;

    IF TG_OP = 'UPDATE' THEN
        -- Blocca modifiche ai campi di struttura.
        IF NEW.coeff_qta             IS DISTINCT FROM OLD.coeff_qta
           OR NEW.componente_id      IS DISTINCT FROM OLD.componente_id
           OR NEW.obbligatorio       IS DISTINCT FROM OLD.obbligatorio
           OR NEW.esposto_in_fattura IS DISTINCT FROM OLD.esposto_in_fattura
           OR NEW.partecipa_qta      IS DISTINCT FROM OLD.partecipa_qta
           OR NEW.determina_qta_padre IS DISTINCT FROM OLD.determina_qta_padre
           OR NEW.valido_dal         IS DISTINCT FROM OLD.valido_dal
           OR NEW.validita           IS DISTINCT FROM OLD.validita
        THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME,
                'E_BOM_MODIFICA_VIETATA',
                jsonb_build_object(
                    'operazione',    'UPDATE_STRUTTURA',
                    'hint',          'Chiudi questa riga (imposta valido_al) e inserisci una nuova riga con i valori aggiornati.',
                    'prodotto_id',   OLD.prodotto_id,
                    'componente_id', OLD.componente_id,
                    'riga_id',       OLD.id
                ),
                NULL::uuid,
                VARIADIC ARRAY[]::text[]
            );
        END IF;

        -- Check coerenza range su UPDATE valido_al.
        -- chk_articoli_componenti_valid_dates copre
        -- "valido_al > valido_dal"; qui intercettiamo
        -- valido_al < valido_dal con error code custom
        -- UI-friendly. Il caso valido_al = valido_dal
        -- resta a carico del CHECK (errore tecnico).
        IF NEW.valido_al IS DISTINCT FROM OLD.valido_al
           AND NEW.valido_al IS NOT NULL
           AND NEW.valido_al < OLD.valido_dal
        THEN
            PERFORM script.fn_log_and_raise_error(
                'database',
                TG_NAME,
                'E_BOM_VALIDO_AL_INVALIDO',
                jsonb_build_object(
                    'valido_al',   NEW.valido_al,
                    'valido_dal',  OLD.valido_dal,
                    'riga_id',     OLD.id
                ),
                NULL::uuid,
                NEW.valido_al::text,
                OLD.valido_dal::text
            );
        END IF;
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_componenti_block_modifica_struttura()
IS 'Trigger function: blocca DELETE e UPDATE dei campi di struttura di catalogo.articoli_componenti (BoM immutabile, pattern chiudi+inserisci). Ammette UPDATE di valido_al (con check >=valido_dal), attivo, note, meta, audit. Error code: E_BOM_MODIFICA_VIETATA (387), E_BOM_VALIDO_AL_INVALIDO (388).';
```

---
{% include-markdown "signature-core.md" %}
