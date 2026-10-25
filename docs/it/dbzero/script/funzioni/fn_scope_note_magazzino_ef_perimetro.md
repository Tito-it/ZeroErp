{% include-markdown "it/dbzero/script/manual/fn_scope_note_magazzino_ef_perimetro.md" %}
# ⚙️ Funzione `fn_scope_note_magazzino_ef_perimetro`

```sql
CREATE FUNCTION fn_scope_note_magazzino_ef_perimetro(p_perimetro bigint[], p_target_tipo character varying, p_target_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_magazzino_ef_perimetro(p_perimetro bigint[], p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: la nota sta nel perimetro dell'operatore? Smista su
    --   target_tipo per il PADRE partizionato magazzino.note, che non
    --   eredita le policy delle partizioni. Nelle partizioni _riga
    --   target_id e' la TESTATA: il modo e' quello della testata.
    -- Il perimetro NON lo calcola lei: glielo passa la policy in UNA
    --   sottoquery non correlata su script.fn_get_emittenti_scope_pk_ids
    --   (InitPlan, una volta per istruzione). Per riga resta l'emittente,
    --   dal risolutore DEFINER con lo stesso modo della partizione.
    -- ⛔ L'ELSE false e' la riga che conta: un target_tipo nuovo e non
    --   gestito rende quelle note INVISIBILI dal padre, non visibili a
    --   tutti (neanche al super admin). Presidio: P-12 di
    --   rls/test-rls-magazzino-perimetro-v1, contro i confini delle partizioni.
    SELECT CASE p_target_tipo
        WHEN 'ASSET'              THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('asset', p_target_id))
        WHEN 'EVENTO_ASSET'       THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('evento_asset', p_target_id))
        WHEN 'INVENTARIO'         THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('inventario', p_target_id))
        WHEN 'INVENTARIO_RIGA'    THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('inventario', p_target_id))
        WHEN 'MOVIMENTO'          THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('movimento', p_target_id))
        WHEN 'RETTIFICA'          THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('rettifica', p_target_id))
        WHEN 'RETTIFICA_RIGA'     THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('rettifica', p_target_id))
        WHEN 'TRASFERIMENTO'      THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('trasferimento', p_target_id))
        WHEN 'TRASFERIMENTO_RIGA' THEN script.fn_scope_ef_perimetro(p_perimetro, script.fn_resolve_emittente_fiscale_id('trasferimento', p_target_id))
        ELSE false
    END
$function$

COMMENT ON FUNCTION script.fn_scope_note_magazzino_ef_perimetro(p_perimetro bigint[], p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore di scope per il PADRE partizionato magazzino.note, veste OPERATORE: la nota sta nel perimetro? Il perimetro lo passa la policy, calcolato UNA volta per istruzione da script.fn_get_emittenti_scope_pk_ids in una sottoquery non correlata (InitPlan); per riga resta l''emittente, da script.fn_resolve_emittente_fiscale_id con lo stesso modo della partizione (nelle _riga target_id e'' la testata), confrontato da script.fn_scope_ef_perimetro (linee-guida-sql §10.3). ⛔ ELSE false: un target_tipo non gestito rende quelle note invisibili, non pubbliche, anche al super admin; che ogni confine di partizione abbia il suo ramo lo presidia P-12 di rls/test-rls-magazzino-perimetro-v1. Stampo: script.fn_scope_note_ef_perimetro (vendite). Rev 2026-10-21 (20261021-25, P-1 di brief-db-perimetro-una-volta-famiglie-residue): prende il posto di fn_scope_note_magazzino_ef_whitelist, che calcolava il perimetro per riga. Rev 2026-10-25 (20261025-65, brief-db-grammatica-unica-documenti lotto 3): stessi rami; il presidio si confronta coi confini delle partizioni, perche'' il CHECK chk_note_target_tipo e'' ritirato (20261025-56).';
```

</div>

---
{% include-markdown "signature-core.md" %}
