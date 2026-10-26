{% include-markdown "it/dbzero/script/manual/trgfn_componenti_propaga_qta.md" %}
# ⚙️ Funzione `trgfn_componenti_propaga_qta`

```sql
CREATE FUNCTION trgfn_componenti_propaga_qta()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_componenti_propaga_qta()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- TG_ARGV[0]: schema (es. 'vendite')
    -- TG_ARGV[1]: tab_figli (es. 'preventivi_righe_componenti')
    -- TG_ARGV[2]: col FK figli->padre (es. 'riga_preventivo_id')
    v_sql text;
BEGIN
    -- Quantita' non cambiata: niente da propagare.
    -- ⚠️ Rev 2026-10-04 (brief-db-esclusioni-implicite): qui c'era
    --    scritto «UPDATE OF quantita garantisce gia' il cambio». E'
    --    falso due volte: UPDATE OF scatta se la colonna e' nel SET,
    --    anche a valore uguale, e NON scatta se la cambia un altro
    --    trigger BEFORE. Su queste righe quantita la calcola
    --    trgfn_qta_from_operativa da qta_operativa: cambiare solo
    --    qta_operativa (come fa il backend sui preventivi) lasciava i
    --    componenti con la quantita' vecchia. I trigger ora sono AFTER
    --    UPDATE con WHEN (OLD.quantita IS DISTINCT FROM NEW.quantita),
    --    che guarda la riga finale; questo controllo resta per le
    --    chiamate dirette.
    IF NEW.quantita IS NOT DISTINCT FROM OLD.quantita THEN
        RETURN NULL;
    END IF;

    -- Aggiorna quantita su tutti i figli attivi:
    -- quantita = coeff_qta_snapshot * NEW.quantita (padre)
    v_sql := format(
        $q$UPDATE %1$I.%2$I
              SET quantita = coeff_qta_snapshot * $1
            WHERE %3$I = $2
              AND attivo = TRUE$q$,
        TG_ARGV[0],
        TG_ARGV[1],
        TG_ARGV[2]
    );
    EXECUTE v_sql USING NEW.quantita, NEW.id;

    RETURN NULL;  -- AFTER trigger
END;
$function$

COMMENT ON FUNCTION script.trgfn_componenti_propaga_qta()
IS 'Trigger function AFTER UPDATE su riga padre, WHEN (OLD.quantita IS DISTINCT FROM NEW.quantita): propaga quantita ai figli attivi come coeff_qta_snapshot * NEW.quantita. TG_ARGV[0]=schema [1]=tab_figli [2]=col_fk_figli->padre. Usata su 5 tabelle sorgente CASO A (preventivi, ordini, DDT, contratti, eccezioni d''offerta). Rev 2026-10-04 (brief-db-esclusioni-implicite): i trigger erano AFTER UPDATE OF quantita, che non scatta quando quantita la riscrive un trigger BEFORE (trgfn_qta_from_operativa da qta_operativa): cambiare solo qta_operativa lasciava i componenti con la quantita'' vecchia.';
```

</div>

---
{% include-markdown "signature-core.md" %}
