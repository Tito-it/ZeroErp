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
IS 'Building block: la voce di catalogo e'' RITIRATA oggi, cioe'' obsoleto_dal e'' valorizzata e raggiunta alla data operativa (script.fn_data_operativa). Falso se NULL (mai ritirata) o futura (ritiro programmato): mai NULL, quindi NOT script.fn_e_obsoleto(x) e'' il filtro «si sceglie per il nuovo». Sede unica del predicato (regola del 2), anche per il ritiro dei processi (dbops.processi.obsoleto_dal): lo leggono il processo vivo, la sveglia, l''accensione, i presidi, il panorama e il roster. I lettori si trovano con dbops.fn_find_function_usage. BEGIN ATOMIC (linee-guida-sql §5c).';
```

</div>

---
{% include-markdown "signature-core.md" %}
