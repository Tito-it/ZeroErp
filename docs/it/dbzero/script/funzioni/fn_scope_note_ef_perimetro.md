# ⚙️ Funzione `fn_scope_note_ef_perimetro`

```sql
CREATE FUNCTION fn_scope_note_ef_perimetro(p_perimetro bigint[], p_target_tipo character varying, p_target_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_ef_perimetro(p_perimetro bigint[], p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: la nota sta nel perimetro dell'operatore? Smista su
    --   target_tipo per il PADRE partizionato vendite.note, che non
    --   eredita le policy delle partizioni.
    -- Il perimetro NON lo calcola lei: glielo passa la policy in UNA
    --   sottoquery non correlata su script.fn_get_emittenti_scope_pk_ids
    --   (InitPlan, una volta per istruzione). Per riga resta l'emittente,
    --   dal risolutore DEFINER con lo stesso modo della partizione.
    -- ⛔ L'ELSE false e' la riga che conta: un target_tipo nuovo e non
    --   gestito rende quelle note INVISIBILI dal padre, non visibili a
    --   tutti (neanche al super admin). Presidio: rls/test-rls-note-padre.
    SELECT CASE p_target_tipo
        WHEN 'PREVENTIVO' THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('preventivo', p_target_id))
        WHEN 'ORDINE'     THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('ordine', p_target_id))
        WHEN 'DDT'        THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('ddt', p_target_id))
        WHEN 'CONTRATTO'  THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('contratto', p_target_id))
        WHEN 'FATTURA'    THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('fattura', p_target_id))
        WHEN 'OFFERTA'    THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('offerta', p_target_id))
        WHEN 'ATTIVITAFT' THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('attivita_fatturabile', p_target_id))
        ELSE false
    END
$function$

COMMENT ON FUNCTION script.fn_scope_note_ef_perimetro(p_perimetro bigint[], p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore di scope per il PADRE partizionato vendite.note, veste OPERATORE: la nota sta nel perimetro? Il perimetro lo passa la policy, calcolato UNA volta per istruzione da script.fn_get_emittenti_scope_pk_ids in una sottoquery non correlata (InitPlan); per riga resta l''emittente, da script.fn_resolve_emittente_fiscale_id con lo stesso modo della partizione, confrontato da script.fn_scope_ef_perimetro (linee-guida-sql §10.3). Esiste perche'' le policy delle PARTIZIONI non risalgono al padre. ⛔ ELSE false: un target_tipo non gestito rende quelle note invisibili dal padre, anche al super admin; i rami contro chk_note_target_tipo li presidia rls/test-rls-note-padre. Rev 2026-10-21 (20261021-25, P-1 di brief-db-perimetro-una-volta-famiglie-residue): prende il posto di fn_scope_note_ef_whitelist, che calcolava il perimetro per riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
