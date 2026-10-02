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
    --   nuova riga con valido_dal successivo. Il temporal UNIQUE
    --   constraint uq_articoli_componenti_no_overlap (PG 18)
    --   garantisce non-overlap sul triplo (prodotto, componente,
    --   validita WITHOUT OVERLAPS).
    --
    -- Regole:
    --   1. DELETE -> bloccato sempre (E_BOM_MODIFICA_VIETATA).
    --   2. UPDATE dei campi di struttura -> bloccato
    --      (coeff_qta, componente_id, obbligatorio,
    --      esposizione_in_fattura, partecipa_qta,
    --      determina_qta_padre, valido_dal).
    --      Nota: validita rimossa dalla lista perche' e' ora
    --      STORED generated: PostgreSQL rifiuta scritture dirette
    --      prima che il trigger venga eseguito; in BEFORE trigger
    --      NEW.validita e' NULL e non puo' essere usata per check.
    --   3. UPDATE di valido_al ammesso (chiusura della riga).
    --      L'ordine delle date NON si giudica qui: lo giudica il
    --      guard comune script.trgfn_guard_date_validita, montato
    --      dall'automazione DATE_VALIDITA su ogni tabella con la
    --      coppia valido_dal/valido_al (rev 20260924-01: ritirato
    --      il ramo E_BOM_VALIDO_AL_INVALIDO, che ne era una copia).
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
        -- validita non inclusa: e' STORED generated, scritture dirette
        -- sono gia' rifiutate da PostgreSQL prima che il trigger esegua.
        IF NEW.coeff_qta              IS DISTINCT FROM OLD.coeff_qta
           OR NEW.componente_id       IS DISTINCT FROM OLD.componente_id
           OR NEW.obbligatorio        IS DISTINCT FROM OLD.obbligatorio
           OR NEW.esposizione_in_fattura IS DISTINCT FROM OLD.esposizione_in_fattura
           OR NEW.partecipa_qta       IS DISTINCT FROM OLD.partecipa_qta
           OR NEW.determina_qta_padre IS DISTINCT FROM OLD.determina_qta_padre
           OR NEW.valido_dal          IS DISTINCT FROM OLD.valido_dal
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
    END IF;

    RETURN CASE WHEN TG_OP = 'DELETE' THEN OLD ELSE NEW END;
END;
$function$

COMMENT ON FUNCTION catalogo.trgfn_articoli_componenti_block_modifica_struttura()
IS 'Trigger function: blocca DELETE e UPDATE dei campi di struttura di catalogo.articoli_componenti (BoM immutabile, pattern chiudi+inserisci). Ammette UPDATE di valido_al (chiusura), attivo, note, meta, audit. validita e'' STORED generated: scritture dirette rifiutate da PG. Error code: E_BOM_MODIFICA_VIETATA (387). Rev 20260924-01: l''ordine delle date (valido_al non precede valido_dal) non e'' piu'' qui: ha una sede sola, script.trgfn_guard_date_validita (automazione DATE_VALIDITA); E_BOM_VALIDO_AL_INVALIDO ritirato. Rev 20261001-43: il campo di struttura esposto_in_fattura e'' ora esposizione_in_fattura (tre modi, brief-db-esposizione-componenti-kit-in-fattura).';
```

---
{% include-markdown "signature-core.md" %}
