# ⚙️ Funzione `fn_provenienza_prezzo_esplosa`

```sql
CREATE FUNCTION fn_provenienza_prezzo_esplosa(p_origine character varying, p_listino_versione_id bigint, p_listino_riga_id bigint, p_contesto jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_provenienza_prezzo_esplosa(p_origine character varying, p_listino_versione_id bigint, p_listino_riga_id bigint, p_contesto jsonb)
 RETURNS TABLE(origine_prezzo character varying, listino_versione_id bigint, listino_riga_id bigint, prezzo_base_snapshot numeric, tipo_variazione_applicata character varying, valore_variazione_applicata numeric, promo_id bigint, prezzo_contratto_id bigint, categoria_cliente_id_snapshot smallint, classe_utenza_id_snapshot integer)
 LANGUAGE sql
 IMMUTABLE PARALLEL SAFE
AS $function$
    SELECT p_origine,
           p_listino_versione_id,
           p_listino_riga_id,
           (s.c ->> 'prezzo_base_snapshot')::numeric,
           (s.c ->> 'tipo_variazione_applicata')::varchar,
           (s.c ->> 'valore_variazione_applicata')::numeric,
           (s.c ->> 'promo_id')::bigint,
           (s.c ->> 'contratto_id')::bigint,
           (s.c ->> 'categoria_cliente_id_snapshot')::smallint,
           (s.c ->> 'classe_utenza_id_snapshot')::integer
      FROM (SELECT CASE WHEN p_origine IS NULL
                          OR p_origine IN ('MANUALE', 'COMPONENTI')
                        THEN NULL
                        ELSE p_contesto END AS c) s;
$function$

COMMENT ON FUNCTION vendite.fn_provenienza_prezzo_esplosa(p_origine character varying, p_listino_versione_id bigint, p_listino_riga_id bigint, p_contesto jsonb)
IS 'Dalla provenienza del prezzo di una riga di documento (origine, versione e riga di listino, contesto del resolver) le dieci colonne della provenienza di una riga di commessa, in una riga sola. Le chiavi del contesto sono i nomi delle colonne del risultato del resolver (vendite.fn_resolve_prezzo_listino_v2_esito): prezzo_base_snapshot, tipo_variazione_applicata, valore_variazione_applicata, promo_id, contratto_id (esce come prezzo_contratto_id), categoria_cliente_id_snapshot, classe_utenza_id_snapshot; le altre si ignorano, e to_jsonb di una riga del resolver e'' un contesto valido. Il contesto conta solo per un''origine da listino: con MANUALE, COMPONENTI o senza origine quei campi sono NULL. Origine, versione e riga passano come sono. La leggono i lister del push (vendite.fn_list_*_da_pushare) e vendite.fn_contratti_addebiti_maturati_con_provenienza.';
```

</div>

---
{% include-markdown "signature-core.md" %}
