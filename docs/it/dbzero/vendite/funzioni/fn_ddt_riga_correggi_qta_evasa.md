# ⚙️ Funzione `fn_ddt_riga_correggi_qta_evasa`

```sql
CREATE FUNCTION fn_ddt_riga_correggi_qta_evasa(p_ddt_riga_id bigint, p_qta_operativa numeric)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ddt_riga_correggi_qta_evasa(p_ddt_riga_id bigint, p_qta_operativa numeric)
 RETURNS numeric
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: correggere la quantita' evasa di una riga di DDT in
--   bozza (D-2 di brief-db-ddt-righe-evase-dall-ordine): riga e
--   legame nella stessa operazione, entro il residuo, poi lo stato
--   dell'ordine. Vedi l'intestazione del changeSet.
-- Ritorna: la nuova qta_evasa (unita' base).
-- =========================================================
DECLARE
    v_utente    config.user_override_azioni.auth_user_id%TYPE;
    v_ddt_id    vendite.ddt_righe.ddt_id%TYPE;
    v_qta_base  vendite.ddt_righe.quantita%TYPE;
    v_ordine_id vendite.ordini.id%TYPE;
BEGIN
    v_utente := NULLIF(current_setting('app.current_user_id', true), '')::integer;

    -- 1. Parametri.
    IF p_ddt_riga_id IS NULL OR p_ddt_riga_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_ddt_riga_correggi_qta_evasa',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_ddt_riga_id', p_ddt_riga_id),
            NULL::uuid, 'vendite.fn_ddt_riga_correggi_qta_evasa',
            'p_ddt_riga_id (obbligatorio, maggiore di zero)');
    END IF;

    IF p_qta_operativa IS NULL OR p_qta_operativa <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_ddt_riga_correggi_qta_evasa',
            'E_QTA_NON_POSITIVA',
            jsonb_build_object('campo', 'qta_operativa',
                               'ddt_riga_id', p_ddt_riga_id,
                               'qta_operativa', p_qta_operativa),
            NULL::uuid, COALESCE(p_qta_operativa::text, 'vuota'));
    END IF;

    -- 2. La riga e il suo DDT, FOR UPDATE, nel perimetro (predicato
    --    della policy: DEFINER). Fuori perimetro come inesistente.
    SELECT dr.ddt_id
      INTO v_ddt_id
      FROM vendite.ddt_righe dr
      JOIN vendite.ddt d ON d.id = dr.ddt_id
     WHERE dr.id = p_ddt_riga_id
       AND script.fn_scope_ef_whitelist_via_ddt(v_utente, d.id)
       FOR UPDATE OF d, dr;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_ddt_riga_correggi_qta_evasa',
            'E_DDT_RIGA_NON_TROVATA',
            jsonb_build_object('ddt_riga_id', p_ddt_riga_id),
            NULL::uuid, p_ddt_riga_id::text);
    END IF;

    -- 3. La regola sta nella check: qui si solleva il primo motivo.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_ddt_riga_correggi_qta_evasa',
        script.fn_check_ddt_riga_correggi_qta_evasa(p_ddt_riga_id),
        NULL, NULL::uuid,
        jsonb_build_object('ddt_riga_id', p_ddt_riga_id, 'ddt_id', v_ddt_id));

    -- 4. Riga e legame, con la porta aperta per QUESTA riga. La
    --    quantita' base la ricalcola trgfn_qta_from_operativa; il
    --    residuo lo giudica il guard di consistenza del legame.
    PERFORM set_config('zeroerp.ddt_riga_correggi_qta', p_ddt_riga_id::text, true);

    UPDATE vendite.ddt_righe dr
       SET qta_operativa = p_qta_operativa
     WHERE dr.id = p_ddt_riga_id
    RETURNING dr.quantita INTO v_qta_base;

    -- Il legame con l'ordine (se c'e')...
    UPDATE vendite.ordini_righe_fulfillment f
       SET qta_evasa = v_qta_base
     WHERE f.ddt_riga_id = p_ddt_riga_id;

    -- ...e quello con il reso da ri-consegnare (se c'e', D-7).
    UPDATE vendite.resi_righe_riconsegne rr
       SET qta = v_qta_base
     WHERE rr.ddt_riga_id = p_ddt_riga_id;

    PERFORM set_config('zeroerp.ddt_riga_correggi_qta', '', true);

    -- 5. Lo stato dell'ordine, se la riga ne evade uno (al piu' un
    --    legame: lo garantisce la check).
    SELECT orr.ordine_id
      INTO v_ordine_id
      FROM vendite.ordini_righe_fulfillment f
      JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
     WHERE f.ddt_riga_id = p_ddt_riga_id;

    IF v_ordine_id IS NOT NULL THEN
        PERFORM vendite.fn_ordine_proietta_stato_evasione(v_ordine_id);
    END IF;

    RETURN v_qta_base;
END;
$function$

COMMENT ON FUNCTION vendite.fn_ddt_riga_correggi_qta_evasa(p_ddt_riga_id bigint, p_qta_operativa numeric)
IS 'VERBO (2026-10-11, brief-db-ddt-righe-evase-dall-ordine D-2, D-7): corregge la quantita'' evasa di una riga di DDT in bozza. Nella stessa operazione la riga prende la quantita'' operativa (componenti per la propagazione esistente) e i suoi legami la quantita'' base ricalcolata: il fulfillment (riga d''ordine) e il ponte di ri-consegna (riga di reso), quello che c''e''; poi, se la riga evade un ordine, il suo stato si riproietta (vendite.fn_ordine_proietta_stato_evasione). Ritorna la nuova qta_evasa. Ordine: guard di parametro (E_VENDITE_CHIAMATA_NON_VALIDA; quantita'' <= 0 o vuota E_QTA_NON_POSITIVA, campo qta_operativa), riga e DDT FOR UPDATE nel perimetro (script.fn_scope_ef_whitelist_via_ddt nella WHERE; fuori perimetro E_DDT_RIGA_NON_TROVATA), primo motivo di script.fn_check_ddt_riga_correggi_qta_evasa (DDT non in bozza, riga a mano, DDT senza origine, piu'' legami), scritture con la porta aperta (GUC transazionale zeroerp.ddt_riga_correggi_qta = id della riga: la onorano vendite.trgfn_ddt_righe_guard_riga_evasa e vendite.trgfn_ddt_riga_legame_guard, insieme al proprietario della tabella). Oltre il residuo dell''ordine: E_QTA_SUPERA_RESIDUO (trgfn_ordini_ful_guard_consistenza, reso-aware); oltre la copertura del reso: E_RESO_RICONSEGNA_SUPERA_RESO (trgfn_resi_riconsegne_guard). Nessuna seconda copia qui. SECURITY DEFINER con search_path bloccato; EXECUTE solo all''app. Nessun guard di permesso a DB: il permesso di modifica del DDT resta al backend.';
```

</div>

---
{% include-markdown "signature-core.md" %}
