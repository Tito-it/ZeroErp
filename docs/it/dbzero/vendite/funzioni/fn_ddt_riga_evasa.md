# ⚙️ Funzione `fn_ddt_riga_evasa`

```sql
CREATE FUNCTION fn_ddt_riga_evasa(p_ddt_riga_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_riga_evasa(p_ddt_riga_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE
AS $function$
    SELECT EXISTS (SELECT 1
                     FROM vendite.ordini_righe_fulfillment f
                    WHERE f.ddt_riga_id = p_ddt_riga_id)
        OR EXISTS (SELECT 1
                     FROM vendite.resi_righe_riconsegne rr
                    WHERE rr.ddt_riga_id = p_ddt_riga_id);
$function$

COMMENT ON FUNCTION vendite.fn_ddt_riga_evasa(p_ddt_riga_id bigint)
IS 'Predicato (2026-10-11, brief-db-ddt-righe-evase-dall-ordine D-1, D-7): TRUE se la riga di DDT e'' EVASA, cioe'' spedisce merce dovuta da un documento a monte e porta il LEGAME che ne fotografa la quantita'': con una riga d''ordine (vendite.ordini_righe_fulfillment) o con una riga di reso da ri-consegnare (vendite.resi_righe_riconsegne; la ri-consegna legata a un ordine ha tutti e due). FALSE: riga a mano. Sede unica della definizione, letta da: vendite.trgfn_ddt_righe_guard_riga_evasa (articolo, UoM e quantita'' fermi), script.fn_check_ddt_riga_correggi_qta_evasa (e quindi il verbo vendite.fn_ddt_riga_correggi_qta_evasa) e la colonna evasa di vendite.vw_ddt_righe_dettaglio. SECURITY INVOKER: legge sotto la RLS di chi chiede, e i legami hanno il perimetro della riga.';
```

</div>

---
{% include-markdown "signature-core.md" %}
