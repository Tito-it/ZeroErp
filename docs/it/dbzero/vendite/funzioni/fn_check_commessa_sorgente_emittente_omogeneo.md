# ⚙️ Funzione `fn_check_commessa_sorgente_emittente_omogeneo`

```sql
CREATE FUNCTION fn_check_commessa_sorgente_emittente_omogeneo(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_check_commessa_sorgente_emittente_omogeneo(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public'
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
    IF p_commessa_id IS NULL OR p_sorgente_tipo_id IS NULL OR p_sorgente_uid IS NULL THEN
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
                         p_sorgente_tipo_id, p_sorgente_uid);

    -- ⛔ NULL = fail-closed, e NON `IS NOT DISTINCT FROM`: con
    --   quello due emittenti irrisolti direbbero «omogeneo»,
    --   cioe' la trappola del NULL nella chiave riaperta qui.
    IF v_ef_sorgente IS NULL THEN
        RETURN false;
    END IF;

    RETURN v_ef_commessa = v_ef_sorgente;
END;
$function$

COMMENT ON FUNCTION vendite.fn_check_commessa_sorgente_emittente_omogeneo(p_commessa_id bigint, p_sorgente_tipo_id bigint, p_sorgente_uid text)
IS 'Pure check (boolean, nessun raise proprio): la sorgente che si sta collegando appartiene allo STESSO emittente fiscale della commessa? E'' l''invariante detto da Tid — «una commessa non puo'' aggregare diversi emittenti insieme» — sull''asse dei documenti (H4). ⭐ rev 2026-08-26: il confronto e'' fra DUE COLONNE, senza intermediari — la commessa porta l''emittente addosso (NOT NULL dal 20260826-41) e il documento lo dice da se'' via script.fn_get_sorgente_emittente_sr_id. La versione precedente passava dal BILLING ACCOUNT su entrambi i lati, e su quattro tabelle sorgente su sei (ordini, preventivi, ddt, resi) quella colonna e'' NULLABLE: si fermava fail-closed su documenti perfettamente validi. ⛔ E'' caduta anche la scorciatoia «stesso billing account -> true»: serviva a evitare due risoluzioni, e con la lettura diretta non c''e'' piu'' niente da evitare — una scorciatoia che non fa risparmiare nulla e'' solo un ramo in piu'' da mantenere. ⭐ Il criterio resta l''EMITTENTE e non l''identita'' del billing account (decisione D-4): bloccare sul BA vieterebbe per sempre che un documento di un BA figlio contribuisca alla commessa del padre, e l''albero dei billing account esiste apposta perche'' piu'' BA stiano sotto lo stesso emittente — una decisione di dominio che nessuno ha preso. ⚠️ SECURITY DEFINER: legge vendite.commesse, che ha la RLS. ⛔ NULL -> false (fail-closed) e NON IS NOT DISTINCT FROM. ⚠️ Puo'' PROPAGARE i fail-closed del risolutore (E_SORG_*): difetti di configurazione o riferimenti rotti, non verdetti di dominio. Piano: brief-db-emittente-commessa-invariante, L6.';
```

</div>

---
{% include-markdown "signature-core.md" %}
