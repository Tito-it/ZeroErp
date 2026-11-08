# ⚙️ Funzione `fn_natura_e_merce`

```sql
CREATE FUNCTION fn_natura_e_merce(p_natura_vendita_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_natura_e_merce(p_natura_vendita_id bigint)
 RETURNS boolean
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT ((nv.destinazione_tipo)::text = 'ORDINE_VENDITA'::text)
    FROM config.nature_vendita nv
   WHERE (nv.id = fn_natura_e_merce.p_natura_vendita_id);
END

COMMENT ON FUNCTION script.fn_natura_e_merce(p_natura_vendita_id bigint)
IS 'Building block: la natura di vendita e'' MERCE, cioe'' va all''ordine (config.nature_vendita.destinazione_tipo = ''ORDINE_VENDITA''). Vero/falso; NULL se la natura e'' NULL o non esiste (decide il chiamante). Si chiede sulla natura CONGELATA della riga (A-4), non sull''articolo. Su ordine e bolla «non merce» = onere: l''ammissione (script.fn_check_articolo_riga_su_contesto) lascia entrare solo merce e articoli-onere; se ne entrasse un altro servizio, chi filtra con questo BB va rivisto. Sede unica del predicato (regola del 2): lo usano l''ammissione, catalogo.trgfn_articoli_guard_onere_natura, vendite.vw_preventivi_righe_smistabili_ordine e i lettori di quantita'' di ordine e bolla. BEGIN ATOMIC (linee-guida-sql §5c). brief-db-addebito-trasporto-ordine §8.1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
