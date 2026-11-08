# ⚙️ Funzione `fn_check_commessa_sorgente_emittente_omogeneo`

```sql
CREATE FUNCTION fn_check_commessa_sorgente_emittente_omogeneo(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_commessa_sorgente_emittente_omogeneo(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_ef_commessa vendite.commesse.emittente_soggetto_ruolo_id%TYPE;
    v_ef_sorgente anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   «Una commessa non puo' aggregare diversi emittenti
    --   insieme» (Tid). Qui si risponde SI/NO per una singola
    --   sorgente che si sta per collegare.
    --
    -- ⭐ Il confronto e' fra DUE COLONNE, senza intermediari: la
    --   commessa l'emittente ce l'ha addosso (NOT NULL dal
    --   20260826-41) e il documento lo dice da se'
    --   (script.fn_get_sorgente_emittente_sr_id).
    --   La versione precedente passava dal billing account su
    --   entrambi i lati, e su quattro tabelle sorgente su sei
    --   quella colonna e' NULLABLE: si fermava su documenti
    --   validi.
    --
    -- Convenzione fn_check_*: boolean, nessun raise proprio.
    -- ⚠️ Puo' pero' PROPAGARE i fail-closed del risolutore
    --   (E_SORG_*): non sono verdetti di dominio, sono difetti
    --   di configurazione o riferimenti rotti, e mascherarli qui
    --   li renderebbe invisibili.
    -- =========================================================
    IF p_commessa_id IS NULL OR p_sorgente_tipo_id IS NULL
       OR (p_sorgente_id IS NULL AND p_sorgente_uid IS NULL) THEN
        -- ⛔ Fail-closed: «non so dirlo» non e' «va bene».
        RETURN false;
    END IF;

    -- ⚠️ SECURITY DEFINER: senza, una commessa fuori perimetro
    --   sarebbe invisibile e questo NOT FOUND direbbe il falso.
    SELECT c.emittente_soggetto_ruolo_id
      INTO v_ef_commessa
      FROM vendite.commesse c
     WHERE c.id = p_commessa_id;

    IF NOT FOUND OR v_ef_commessa IS NULL THEN
        RETURN false;
    END IF;

    v_ef_sorgente := script.fn_get_sorgente_emittente_sr_id(
                         p_sorgente_tipo_id, p_sorgente_id, p_sorgente_uid);

    -- ⛔ NULL = fail-closed, e NON `IS NOT DISTINCT FROM`: con
    --   quello due emittenti irrisolti direbbero «omogeneo»,
    --   cioe' la trappola del NULL nella chiave riaperta qui.
    IF v_ef_sorgente IS NULL THEN
        RETURN false;
    END IF;

    RETURN v_ef_commessa = v_ef_sorgente;
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_commessa_sorgente_emittente_omogeneo(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_id bigint, p_sorgente_uid uuid)
IS 'Pure check (boolean, nessun raise proprio): il documento che si sta collegando appartiene allo STESSO emittente fiscale della commessa? E'' l''invariante «una commessa non puo'' aggregare diversi emittenti insieme», sull''asse dei documenti. Il documento si passa con le colonne del modello (tipo, sorgente_id, sorgente_uid). Il confronto e'' fra DUE COLONNE, senza intermediari: la commessa porta l''emittente addosso (NOT NULL) e il documento lo dice da se'' via script.fn_get_sorgente_emittente_sr_id, sulle stesse colonne. Non passa dal billing account: su piu'' tabelle sorgente quella colonna e'' NULLABLE, e il criterio e'' l''EMITTENTE e non l''identita'' del billing account (un documento di un BA figlio contribuisce alla commessa del padre). ⚠️ SECURITY DEFINER: legge vendite.commesse, che ha la RLS. ⛔ NULL -> false (fail-closed) e NON IS NOT DISTINCT FROM. ⚠️ Puo'' PROPAGARE i fail-closed del risolutore (E_SORG_*): difetti di configurazione o riferimenti rotti, non verdetti di dominio.';
```

</div>

---
{% include-markdown "signature-core.md" %}
