# ⚙️ Funzione `fn_e_obsoleto`

```sql
CREATE FUNCTION fn_e_obsoleto(p_obsoleto_dal date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_e_obsoleto(p_obsoleto_dal date)
 RETURNS boolean
 LANGUAGE sql
 STABLE PARALLEL SAFE
BEGIN ATOMIC
 SELECT ((p_obsoleto_dal IS NOT NULL) AND (p_obsoleto_dal <= script.fn_data_operativa()));
END

COMMENT ON FUNCTION script.fn_e_obsoleto(p_obsoleto_dal date)
IS 'Building block: la voce di catalogo e'' RITIRATA oggi, cioe'' obsoleto_dal e'' valorizzata e raggiunta alla data operativa (script.fn_data_operativa). Falso se NULL (mai ritirata) o futura (ritiro programmato): mai NULL, quindi NOT script.fn_e_obsoleto(x) e'' il filtro «si sceglie per il nuovo». Sede unica del predicato (regola del 2): lo usano dbops.fn_get_lookup_codici, dbops.trgfn_child_requires_non_obsolete_parent, dbops.vw_bersagli_non_dichiarati, vendite.trgfn_event_log_deriva_scope e il motivo E_ARTICOLO_OBSOLETO di script.fn_check_articolo_riga_su_contesto. ⛔ Non e'' la regola dei processi (dbops.processi.obsoleto_dal: qualunque data spegne subito). BEGIN ATOMIC (linee-guida-sql §5c). brief-db-articoli-obsoleto-dal §4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
