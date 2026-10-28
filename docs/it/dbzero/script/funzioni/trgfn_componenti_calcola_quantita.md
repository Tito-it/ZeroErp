{% include-markdown "it/dbzero/script/manual/trgfn_componenti_calcola_quantita.md" %}
# ⚙️ Funzione `trgfn_componenti_calcola_quantita`

```sql
CREATE FUNCTION trgfn_componenti_calcola_quantita()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_calcola_quantita()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- TG_ARGV[0]: schema padre (es. 'vendite')
    -- TG_ARGV[1]: tab_padre (es. 'preventivi_righe')
    -- TG_ARGV[2]: col FK figli->padre (es. 'riga_preventivo_id')
    v_riga_padre_id BIGINT;
    v_qta_padre     NUMERIC;
    v_sql           text;
BEGIN
    -- Legge id riga padre da NEW
    EXECUTE format('SELECT ($1).%I', TG_ARGV[2])
      INTO v_riga_padre_id USING NEW;

    -- Legge quantita del padre
    v_sql := format(
        'SELECT quantita FROM %1$I.%2$I WHERE id = $1',
        TG_ARGV[0], TG_ARGV[1]
    );
    EXECUTE v_sql INTO v_qta_padre USING v_riga_padre_id;

    -- Calcola e imposta quantita componente
    NEW.quantita := NEW.coeff_qta_snapshot * COALESCE(v_qta_padre, 1);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_calcola_quantita()
IS 'Trigger function BEFORE INS/UPD su _righe_componenti: imposta NEW.quantita = NEW.coeff_qta_snapshot * quantita_riga_padre. Defense-in-depth contro BE che invia quantita inconsistente. TG_ARGV[0]=schema [1]=tab_padre [2]=col_fk_figli->padre.';
```

</div>

---
{% include-markdown "signature-core.md" %}
