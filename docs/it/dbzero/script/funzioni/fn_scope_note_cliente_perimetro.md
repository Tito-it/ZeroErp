# ⚙️ Funzione `fn_scope_note_cliente_perimetro`

```sql
CREATE FUNCTION fn_scope_note_cliente_perimetro(p_perimetro bigint, p_target_tipo character varying, p_target_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_cliente_perimetro(p_perimetro bigint, p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: la nota e' del cliente che guarda? Smista su target_tipo per
    --   il PADRE partizionato vendite.note, veste CLIENTE_PORTALE.
    -- Il perimetro (il soggetto dell'identita') NON lo calcola lei: glielo
    --   passa la policy in UNA sottoquery su
    --   script.fn_get_identita_sr_perimetro, valutata una volta per
    --   istruzione. Per riga resta il cliente della testata, dal
    --   risolutore DEFINER con lo stesso modo della partizione.
    -- ⛔ L'ELSE false e' la riga che conta: un target_tipo senza ramo
    --   rende quelle note INVISIBILI al cliente, non visibili.
    SELECT CASE p_target_tipo
        WHEN 'FATTURA'        THEN script.fn_scope_sr_perimetro(p_perimetro, script.fn_resolve_controparte_sr_id('fattura', p_target_id))
        WHEN 'ORDINE_VENDITA' THEN script.fn_scope_sr_perimetro(p_perimetro, script.fn_resolve_controparte_sr_id('ordine', p_target_id))
        ELSE false
    END
$function$

COMMENT ON FUNCTION script.fn_scope_note_cliente_perimetro(p_perimetro bigint, p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore di scope per il PADRE partizionato vendite.note, veste CLIENTE_PORTALE: la nota e'' del cliente che guarda? Il perimetro (il soggetto dell''identita'') lo passa la policy, calcolato UNA volta per istruzione da script.fn_get_identita_sr_perimetro; per riga resta il cliente della testata, da script.fn_resolve_controparte_sr_id (FATTURA: modo fattura; ORDINE_VENDITA: modo ordine, gli stessi delle partizioni), confrontato da script.fn_scope_sr_perimetro (linee-guida-sql §10.3). ⛔ ELSE false: un target_tipo senza ramo rende quelle note invisibili al cliente. Rev 2026-10-21 (20261021-38, giro 4 di brief-db-perimetro-una-volta-famiglie-residue): prende il posto di fn_scope_note_cliente, che calcolava il perimetro per riga. Rev 2026-10-25 (20261025-63, brief-db-grammatica-unica-documenti lotto 3): il ramo dell''ordine parla ORDINE_VENDITA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
