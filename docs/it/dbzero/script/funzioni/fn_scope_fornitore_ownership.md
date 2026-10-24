{% include-markdown "it/dbzero/script/manual/fn_scope_fornitore_ownership.md" %}
# ⚙️ Funzione `fn_scope_fornitore_ownership`

```sql
CREATE FUNCTION fn_scope_fornitore_ownership(p_identita_id bigint, p_fornitore_sr_id bigint)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_scope_fornitore_ownership(p_identita_id bigint, p_fornitore_sr_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE COST 5000
AS $function$
    -- Scopo: l'identita' (veste FORNITORE_PORTALE, utilizzabile oggi) e' il
    --   soggetto p_fornitore_sr_id? Fail-closed: identita' NULL, inesistente,
    --   in altra veste o non utilizzabile -> false.
    -- ⭐ Rev 2026-10-21 (20261021-42, giro 5 di brief-db-perimetro-una-volta-
    --   famiglie-residue): la composizione dei building block delle policy di
    --   controparte (script.fn_get_identita_sr_perimetro nella veste
    --   FORNITORE_PORTALE, confrontato da script.fn_scope_sr_perimetro). Resta
    --   la funzione della regola FORNITORE_OWNERSHIP nel catalogo
    --   config.scope_policy; le policy di acquisti non passano piu' di qui
    --   (20261021-43).
    SELECT script.fn_scope_sr_perimetro(
        script.fn_get_identita_sr_perimetro(
            p_identita_id,
            ARRAY['FORNITORE_PORTALE']::config.ruolo_applicativo[]),
        p_fornitore_sr_id)
$function$

COMMENT ON FUNCTION script.fn_scope_fornitore_ownership(p_identita_id bigint, p_fornitore_sr_id bigint)
IS 'Scope policy FORNITORE_OWNERSHIP: ritorna true se il soggetto_ruolo del fornitore target coincide con il soggetto_ruolo dell''identita e l''identita e'' in veste FORNITORE_PORTALE attiva. STABLE, inlineable. Rev 2026-10-07 (brief-db-veste-utilizzabile): l''identita'' deve essere utilizzabile oggi (script.fn_veste_utilizzabile), non solo accesa: una veste scaduta non vede piu'' i suoi dati. Rev 2026-10-21 (20261021-42, giro 5 di brief-db-perimetro-una-volta-famiglie-residue): composizione dei building block delle policy di controparte (script.fn_get_identita_sr_perimetro nella veste FORNITORE_PORTALE, script.fn_scope_sr_perimetro); le policy di acquisti non passano piu'' di qui.';
```

</div>

---
{% include-markdown "signature-core.md" %}
