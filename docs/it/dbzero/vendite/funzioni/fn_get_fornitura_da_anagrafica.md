# ⚙️ Funzione `fn_get_fornitura_da_anagrafica`

```sql
CREATE FUNCTION fn_get_fornitura_da_anagrafica(p_istanza_utility_id bigint, p_utility_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_fornitura_da_anagrafica(p_istanza_utility_id bigint, p_utility_id integer)
 RETURNS TABLE(istanza_dati_precontrattuali_id bigint, classe_utenza_id integer, tipo_utenza_id integer, param_1_num numeric, param_2_txt character varying, meta jsonb)
 LANGUAGE plpgsql
 STABLE
AS $function$
BEGIN
    -- =========================================================
    -- Scopo:
    --   La scheda di fornitura che l'anagrafica da' alla coppia:
    --   il record precontrattuale, con il tipo d'uso derivato dalla
    --   classe. Zero righe = la coppia non ha dati precontrattuali.
    -- =========================================================
    IF p_istanza_utility_id IS NULL OR p_utility_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'fn_get_fornitura_da_anagrafica', 'E_DOC_FORNITURA_PARAMETRO_MANCANTE',
            jsonb_build_object('istanza_utility_id', p_istanza_utility_id,
                               'utility_id',         p_utility_id),
            NULL::uuid,
            'vendite.fn_get_fornitura_da_anagrafica',
            'la coppia istanza/utility');
    END IF;

    -- Un record per coppia (uq_istanze_dati_precontrattuali_id_utility_id):
    -- nessun ORDER BY, nessun LIMIT. Senza classe (utility senza
    -- dimensione) il tipo d'uso resta NULL: lo giudica il guard
    -- della scheda del contratto.
    RETURN QUERY
    SELECT idp.id,
           idp.classe_utenza_id,
           cu.tipo_utenza_id,
           idp.param_1_num,
           idp.param_2_txt,
           COALESCE(idp.meta, '{}'::jsonb)
      FROM anagrafiche.istanze_dati_precontrattuali idp
      LEFT JOIN config.classi_utenze cu ON cu.id = idp.classe_utenza_id
     WHERE idp.istanza_utility_id = p_istanza_utility_id
       AND idp.utility_id         = p_utility_id;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_fornitura_da_anagrafica(p_istanza_utility_id bigint, p_utility_id integer)
IS 'La scheda di fornitura che i dati precontrattuali danno a una coppia (istanza, utility): il record di anagrafiche.istanze_dati_precontrattuali con il tipo d''uso derivato dalla classe (config.classi_utenze), meta mai NULL. Zero righe = la coppia non ha dati precontrattuali; al piu'' una riga (uq_istanze_dati_precontrattuali_id_utility_id: il vecchio ORDER BY data_update ... LIMIT 1 del trigger di nascita nascondeva il vincolo). La sede unica della scheda «dall''anagrafica»: la scrive vendite.fn_doc_fornitura_da_anagrafica (nascita del contratto, cambio di cliente in bozza di contratto e offerta, D-5), e il drawer la mostra all''operatore prima della creazione perche'' la veda e la corregga (D-7). Coppia NULL: E_DOC_FORNITURA_PARAMETRO_MANCANTE (TECNICO). STABLE, INVOKER: legge sotto la RLS di chi chiama. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§8.4).';
```

</div>

---
{% include-markdown "signature-core.md" %}
