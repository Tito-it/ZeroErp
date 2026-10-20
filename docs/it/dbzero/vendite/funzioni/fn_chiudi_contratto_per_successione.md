{% include-markdown "it/dbzero/vendite/manual/fn_chiudi_contratto_per_successione.md" %}
# ⚙️ Funzione `fn_chiudi_contratto_per_successione`

```sql
CREATE FUNCTION fn_chiudi_contratto_per_successione(p_contratto_esistente_id bigint, p_nuovo_valido_dal date)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_chiudi_contratto_per_successione(p_contratto_esistente_id bigint, p_nuovo_valido_dal date)
 RETURNS date
 LANGUAGE plpgsql
AS $function$
-- Scopo:
--   Chiudere (accorciare) un contratto esistente per successione:
--   valido_al := p_nuovo_valido_dal - 1. Restringe la daterange
--   generata e libera la finestra per il nuovo contratto.
--   Cuore del meccanismo generico (brief §3.2.2).
--
-- Parametri:
--   p_contratto_esistente_id : contratto da accorciare.
--   p_nuovo_valido_dal       : data di decorrenza del nuovo contratto.
--
-- Ritorno: il nuovo valido_al impostato sul contratto chiuso.
--
-- Errori:
--   E_PARAMETRO_INVALIDO                  : parametri NULL / contratto inesistente.
--   E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA : la chiusura produrrebbe
--     valido_al < valido_dal (viola chk_contratti_validita) -> guard
--     ESPLICITA prima del CHECK, con numero del contratto nel messaggio.
DECLARE
    v_fn_name         CONSTANT text := 'fn_chiudi_contratto_per_successione';
    v_old             vendite.contratti%ROWTYPE;
    v_nuovo_valido_al vendite.contratti.valido_al%TYPE;
BEGIN
    -- Guard: parametri obbligatori.
    IF p_contratto_esistente_id IS NULL OR p_nuovo_valido_dal IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', v_fn_name,
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'p_contratto_esistente_id', p_contratto_esistente_id,
                'p_nuovo_valido_dal',        p_nuovo_valido_dal
            ),
            NULL::uuid,
            'parametri NULL non ammessi'
        );
    END IF;

    -- Carica e blocca il contratto esistente.
    SELECT * INTO v_old
      FROM vendite.contratti
     WHERE id = p_contratto_esistente_id
     FOR UPDATE;

    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', v_fn_name,
            -- rev 2026-08-07: era E_PARAMETRO_INVALIDO, cioe' 400 su un 404.
            'E_CONTRATTO_NON_TROVATO',
            jsonb_build_object('contratto_id', p_contratto_esistente_id),
            NULL::uuid,
            p_contratto_esistente_id::text
        );
    END IF;

    v_nuovo_valido_al := p_nuovo_valido_dal - 1;

    -- Guard data: la chiusura non deve produrre un intervallo invalido
    -- (valido_al < valido_dal). Si solleva PRIMA del CHECK
    -- chk_contratti_validita per dare un errore parlante con il numero.
    IF v_old.valido_dal > v_nuovo_valido_al THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', v_fn_name,
            'E_CONTRATTO_SUCCESSIONE_DATA_INVALIDA',
            jsonb_build_object(
                'contratto_id',         v_old.id,
                'numero',               v_old.numero,
                'valido_dal_esistente', v_old.valido_dal,
                'nuovo_valido_dal',      p_nuovo_valido_dal,
                'nuovo_valido_al_calcolato', v_nuovo_valido_al
            ),
            NULL::uuid,
            v_old.numero
        );
    END IF;

    -- Accorciamento. NON cambia lo stato (cessazione via job notturno).
    -- L'UPDATE di valido_al non attiva il lock post-attivazione.
    UPDATE vendite.contratti
       SET valido_al = v_nuovo_valido_al
     WHERE id = v_old.id;

    RETURN v_nuovo_valido_al;
END;
$function$

COMMENT ON FUNCTION vendite.fn_chiudi_contratto_per_successione(p_contratto_esistente_id bigint, p_nuovo_valido_dal date)
IS 'Accorcia un contratto esistente per successione: valido_al = p_nuovo_valido_dal - 1. rev 2026-08-07: il contratto inesistente solleva E_CONTRATTO_NON_TROVATO (896) invece di E_PARAMETRO_INVALIDO, che dava 400 su un 404. Trovato dalla lente del quarto lato; brief terzo lato §19.4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
