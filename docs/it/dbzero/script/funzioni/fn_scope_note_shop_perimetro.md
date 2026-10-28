# ⚙️ Funzione `fn_scope_note_shop_perimetro`

```sql
CREATE FUNCTION fn_scope_note_shop_perimetro(p_perimetro bigint, p_target_tipo character varying, p_target_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_note_shop_perimetro(p_perimetro bigint, p_target_tipo character varying, p_target_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: la nota e' del cliente shop che guarda? Smista su target_tipo
    --   per il PADRE partizionato vendite.note, veste SHOP_CUSTOMER: solo
    --   gli ordini, e solo quelli nati dallo shop (modo ordine_shop).
    -- Il perimetro lo passa la policy, come in
    --   script.fn_scope_note_cliente_perimetro.
    -- ⛔ L'ELSE false e' la riga che conta: lo shop non vede le note di
    --   fatture, offerte, bolle.
    SELECT CASE p_target_tipo
        WHEN 'ORDINE_VENDITA' THEN script.fn_scope_sr_perimetro(p_perimetro, script.fn_resolve_controparte_sr_id('ordine_shop', p_target_id))
        ELSE false
    END
$function$

COMMENT ON FUNCTION script.fn_scope_note_shop_perimetro(p_perimetro bigint, p_target_tipo character varying, p_target_id bigint)
IS 'Smistatore di scope per il PADRE partizionato vendite.note, veste SHOP_CUSTOMER: la nota e'' del cliente shop che guarda? Solo le note di ORDINE_VENDITA, e solo di ordini nati dallo shop: script.fn_resolve_controparte_sr_id modo ordine_shop, confrontato col perimetro che la policy calcola una volta per istruzione (script.fn_get_identita_sr_perimetro). ⛔ ELSE false. Rev 2026-10-21 (20261021-38, giro 4 di brief-db-perimetro-una-volta-famiglie-residue): prende il posto di fn_scope_note_shop, che calcolava il perimetro per riga. Rev 2026-10-25 (20261025-64, brief-db-grammatica-unica-documenti lotto 3): il ramo parla ORDINE_VENDITA.';
```

</div>

---
{% include-markdown "signature-core.md" %}
