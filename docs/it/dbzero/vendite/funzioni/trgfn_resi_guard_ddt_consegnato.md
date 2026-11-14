{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_guard_ddt_consegnato.md" %}
# ⚙️ Funzione `trgfn_resi_guard_ddt_consegnato`

```sql
CREATE FUNCTION trgfn_resi_guard_ddt_consegnato()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_guard_ddt_consegnato()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6e): la regola sta in
--   script.fn_check_ddt_rendibile, letta anche dalla capability della bolla
--   (can_genera_reso). Qui si solleva il primo motivo.
-- Scopo: il reso e' ammesso solo se il DDT sorgente lo genera: non da una
--   bolla di trasferimento, non da una bolla non consegnata (i motivi di
--   script.fn_check_ddt_rendibile). Solo per sorgente DDT_VENDITA
--   (data-driven). La bolla ha chiave id: si cerca per sorgente_id.
DECLARE
    v_is_ddt boolean;
BEGIN
    -- Applica solo alla sorgente DDT_VENDITA.
    SELECT EXISTS (
        SELECT 1 FROM config.sorgenti
         WHERE id = NEW.sorgente_tipo_id
           AND codice_interno = 'DDT_VENDITA'
    ) INTO v_is_ddt;

    IF NOT v_is_ddt THEN
        RETURN NEW;
    END IF;

    -- La forma della sorgente (sorgente_id obbligatorio) la fa valere il
    -- vincolo chk_resi_sorgente_forma: qui non si risponde al suo posto.
    IF NEW.sorgente_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- I motivi (bolla di trasferimento, bolla non consegnata) e il loro
    -- ordine stanno nella check, la stessa della capability della bolla.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'trgfn_resi_guard_ddt_consegnato',
        script.fn_check_ddt_rendibile(NEW.sorgente_id),
        NULL, NULL::uuid,
        jsonb_build_object('sorgente_id', NEW.sorgente_id));

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_guard_ddt_consegnato()
IS 'Guard del reso, BEFORE INSERT: un reso da una bolla (sorgente DDT_VENDITA, cercata per sorgente_id: la bolla ha chiave id) nasce solo se script.fn_check_ddt_rendibile non da'' motivi, e qui si solleva il primo: E_RESO_DA_DDT_TRASFERIMENTO per una bolla di trasferimento fra depositi (la merce e'' rimasta nostra, un reso la farebbe rientrare due volte), E_RESO_DDT_NON_CONSEGNATO per una bolla non consegnata o assente. La stessa check da'' can_genera_reso nella capability della bolla (script.fn_available_actions_ddt). Il contesto porta la chiave della bolla (sorgente_id) e il dettaglio del motivo (ddt_id, stato_ddt). Altre sorgenti, e sorgente_id nullo (lo rifiuta il vincolo chk_resi_sorgente_forma), passano.';
```

</div>

---
{% include-markdown "signature-core.md" %}
