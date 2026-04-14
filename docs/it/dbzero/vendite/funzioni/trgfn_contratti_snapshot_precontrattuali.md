{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_snapshot_precontrattuali.md" %}
# ⚙️ Funzione `trgfn_contratti_snapshot_precontrattuali`

```sql
CREATE FUNCTION trgfn_contratti_snapshot_precontrattuali()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_snapshot_precontrattuali()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_idp_id           anagrafiche.istanze_dati_precontrattuali.id%TYPE;
    v_classe_utenza_id anagrafiche.istanze_dati_precontrattuali.classe_utenza_id%TYPE;
    v_tipo_utenza_id   config.classi_utenze.tipo_utenza_id%TYPE;
    v_param_1_num      anagrafiche.istanze_dati_precontrattuali.param_1_num%TYPE;
    v_param_2_txt      anagrafiche.istanze_dati_precontrattuali.param_2_txt%TYPE;
    v_meta             anagrafiche.istanze_dati_precontrattuali.meta%TYPE;
BEGIN
    -- Idempotenza: se lo snapshot esiste gia', niente da fare.
    IF EXISTS (
        SELECT 1 FROM vendite.contratti_utilities cu
         WHERE cu.contratto_id = NEW.id
    ) THEN
        RETURN NEW;
    END IF;

    -- Carica il record precontrattuale piu' recente per
    -- (istanza_utility, utility).
    SELECT id,
           classe_utenza_id,
           param_1_num,
           param_2_txt,
           meta
      INTO v_idp_id,
           v_classe_utenza_id,
           v_param_1_num,
           v_param_2_txt,
           v_meta
      FROM anagrafiche.istanze_dati_precontrattuali
     WHERE istanza_utility_id = NEW.istanza_utility_id
       AND utility_id         = NEW.utility_id
     ORDER BY data_update DESC, id DESC
     LIMIT 1;

    IF v_idp_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- Derivazione tipo_utenza_id dalla classe (pricing v5).
    -- Se classe_utenza_id e' NULL (utility senza dimensione),
    -- v_tipo_utenza_id resta NULL: il guard verifica la coerenza.
    IF v_classe_utenza_id IS NOT NULL THEN
        SELECT cu.tipo_utenza_id
          INTO v_tipo_utenza_id
          FROM config.classi_utenze cu
         WHERE cu.id = v_classe_utenza_id;
    END IF;

    INSERT INTO vendite.contratti_utilities (
        contratto_id,
        istanza_utility_id,
        utility_id,
        istanza_dati_precontrattuali_id,
        classe_utenza_id,
        tipo_utenza_id,
        param_1_num,
        param_2_txt,
        meta
    )
    VALUES (
        NEW.id,
        NEW.istanza_utility_id,
        NEW.utility_id,
        v_idp_id,
        v_classe_utenza_id,
        v_tipo_utenza_id,
        v_param_1_num,
        v_param_2_txt,
        COALESCE(v_meta, '{}'::jsonb)
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_snapshot_precontrattuali()
IS 'Snapshot precontrattuali su INSERT di vendite.contratti. Popola anche tipo_utenza_id derivandolo da classi_utenze (pricing v5).';
```

---
{% include-markdown "signature-core.md" %}
