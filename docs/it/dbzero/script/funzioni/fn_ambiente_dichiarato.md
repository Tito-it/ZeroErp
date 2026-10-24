# ⚙️ Funzione `fn_ambiente_dichiarato`

```sql
CREATE FUNCTION fn_ambiente_dichiarato()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_ambiente_dichiarato()
 RETURNS text
 LANGUAGE sql
 STABLE
AS $function$
    -- Scopo: l'ambiente di questa installazione, NULL se non e'
    --   ancora dichiarato. Per chi DESCRIVE (panorami,
    --   presidi); chi DECIDE usa script.fn_ambiente_installazione().
    SELECT i.ambiente
      FROM dbops.installazione i
     WHERE i.id = 1;
$function$

COMMENT ON FUNCTION script.fn_ambiente_dichiarato()
IS 'L''ambiente di questa installazione (SVILUPPO o PRODUZIONE) letto da dbops.installazione, oppure NULL se la fase post del provisioning non l''ha ancora dichiarato. Per chi DESCRIVE senza decidere (il panorama dei processi, il presidio dbops.vw_ambiente_non_dichiarato): un''installazione non dichiarata e'' proprio la cosa da mostrare, non un motivo per morire. NULL non e'' un valore di ripiego: chi DECIDE in base all''ambiente usa script.fn_ambiente_installazione(), che fallisce con E_CONFIG_MANCANTE. Brief: brief-db-processi-accensione-per-ambiente (R-1).';
```

</div>

---
{% include-markdown "signature-core.md" %}
