# ⚙️ Funzione `fn_ordine_proietta_stato_evasione`

```sql
CREATE FUNCTION fn_ordine_proietta_stato_evasione(p_ordine_id bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_ordine_proietta_stato_evasione(p_ordine_id bigint)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- =========================================================
-- Scopo: portare l'ordine nello stato che la sua evasione dice.
--   1. nessun fulfillment su nessuna riga -> CONFERMATO;
--   2. residuo su almeno una riga (fn_ordine_ha_residuo_evasione,
--      reso-aware)                       -> PARZIALMENTE_EVASO;
--   3. altrimenti                         -> EVASO.
--   La transizione passa dalla matrice (trgfn_ordini_guard_transizione):
--   uno stato di partenza che non ammette il passaggio rifiuta li'.
-- Consumatori: fn_genera_ddt_da_ordine, i cinque verbi del reso,
--   fn_ddt_riga_correggi_qta_evasa e il ritiro del legame con la riga
--   di DDT in bozza (trgfn_dlt_block_ordrig_ddtrig).
-- Brief: brief-db-ddt-righe-evase-dall-ordine (§5.2).
-- rev 2026-10-25 (20261025-79, brief-modello-documento-vendita
--   §9): e' il verbo dei passaggi di PROCESSO dell'ordine
--   (manuale = false): scrive con la sola seconda meta' del
--   verbo comune, attraverso la porta. DEFINER, perche' la porta
--   vuole il proprietario; lo stato e' la proiezione
--   dell'evasione, non una scelta di chi chiama.
-- =========================================================
DECLARE
    v_stato_target    config.stati_doc_ordini.codice_interno%TYPE;
    v_stato_target_id config.stati_doc_ordini.id%TYPE;
    v_stato_id        vendite.ordini.stato_doc_ordine_id%TYPE;
BEGIN
    IF p_ordine_id IS NULL OR p_ordine_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_ordine_proietta_stato_evasione',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_ordine_id', p_ordine_id),
            NULL::uuid, 'vendite.fn_ordine_proietta_stato_evasione',
            'p_ordine_id (obbligatorio, maggiore di zero)');
    END IF;

    -- ⭐ Il discrimine del CONFERMATO e' l'esistenza di un legame, non
    --    il residuo pieno: un ordine evaso e poi reso per intero e'
    --    stato evaso, e resta PARZIALMENTE_EVASO.
    IF NOT EXISTS (
        SELECT 1
          FROM vendite.ordini_righe_fulfillment f
          JOIN vendite.ordini_righe orr ON orr.id = f.ordine_riga_id
         WHERE orr.ordine_id = p_ordine_id
    ) THEN
        v_stato_target := 'CONFERMATO';
    ELSIF vendite.fn_ordine_ha_residuo_evasione(p_ordine_id) THEN
        v_stato_target := 'PARZIALMENTE_EVASO';
    ELSE
        v_stato_target := 'EVASO';
    END IF;

    v_stato_target_id := script.fn_doc_stato_id('vendite.ordini'::regclass, v_stato_target);

    IF v_stato_target_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_ordine_proietta_stato_evasione',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('config', 'config.stati_doc_ordini.' || v_stato_target),
            NULL::uuid, 'stato ' || v_stato_target || ' (config.stati_doc_ordini)');
    END IF;

    -- Lo stato di oggi. Ordine assente, o gia' nello stato giusto:
    -- niente (come la WHERE dell'UPDATE di prima).
    SELECT o.stato_doc_ordine_id
      INTO v_stato_id
      FROM vendite.ordini o
     WHERE o.id = p_ordine_id;

    IF NOT FOUND OR v_stato_id = v_stato_target_id THEN
        RETURN;
    END IF;

    -- La matrice la giudica il guard di transizione, all'UPDATE.
    PERFORM script.fn_doc_scrivi_stato('vendite.ordini'::regclass,
                                       p_ordine_id, v_stato_target_id);
END;
$function$

COMMENT ON FUNCTION vendite.fn_ordine_proietta_stato_evasione(p_ordine_id bigint)
IS 'Building block (2026-10-11, brief-db-ddt-righe-evase-dall-ordine §5.2): porta l''ordine nello stato che la sua evasione dice. Nessun fulfillment su nessuna riga -> CONFERMATO; residuo su almeno una riga (vendite.fn_ordine_ha_residuo_evasione, reso-aware) -> PARZIALMENTE_EVASO; altrimenti EVASO. Il discrimine del CONFERMATO e'' l''ESISTENZA di un legame, non il residuo pieno: un ordine evaso e poi reso per intero resta PARZIALMENTE_EVASO. La transizione passa dalla matrice (vendite.trgfn_ordini_guard_transizione), che rifiuta uno stato di partenza che non ammette il passaggio; Scrive solo se lo stato cambia, con la sola seconda meta'' del verbo comune (script.fn_doc_scrivi_stato) attraverso la porta (script.trgfn_doc_stato_solo_dal_verbo): e'' il verbo dei passaggi di PROCESSO dell''ordine (manuale = false nella matrice). SECURITY DEFINER con search_path bloccato (rev 2026-10-25, 20261025-79, brief-modello-documento-vendita §9; era INVOKER): la porta vuole il proprietario, e la proiezione vale per ogni ordine, perche'' lo stato e'' la proiezione dell''evasione e non una scelta di chi chiama; il perimetro di chi agisce lo controllano i consumatori. Destinazione da script.fn_doc_stato_id; assente dal catalogo: E_CONFIG_MANCANTE. Estratta dalle sei madri che la scrivevano a mano (fn_genera_ddt_da_ordine, fn_conferma_reso, fn_annulla_reso, fn_chiudi_riconsegna_reso, fn_riapri_riconsegna_reso, fn_genera_ddt_riconsegna), ritirate lo stesso giorno (20261011-06 … -11); consumatori nuovi: vendite.fn_ddt_riga_correggi_qta_evasa e il ritiro del legame in vendite.trgfn_dlt_block_ordrig_ddtrig. Parametro non valido: E_VENDITE_CHIAMATA_NON_VALIDA (TECNICO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
