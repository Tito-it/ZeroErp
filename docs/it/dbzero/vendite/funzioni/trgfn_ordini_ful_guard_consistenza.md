{% include-markdown "it/dbzero/vendite/manual/trgfn_ordini_ful_guard_consistenza.md" %}
# ⚙️ Funzione `trgfn_ordini_ful_guard_consistenza`

```sql
CREATE FUNCTION trgfn_ordini_ful_guard_consistenza()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ordini_ful_guard_consistenza()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
  DECLARE
    v_art_ordine  vendite.ordini_righe.articolo_id%TYPE;
    v_uom_ordine  vendite.ordini_righe.uom_operativa_id%TYPE;
    v_art_ddt     vendite.ddt_righe.articolo_id%TYPE;
    v_uom_ddt     vendite.ddt_righe.uom_operativa_id%TYPE;
    v_qta_ordine  vendite.ordini_righe.quantita%TYPE;
    v_qta_evasa   vendite.ordini_righe_fulfillment.qta_evasa%TYPE;
    v_residuo     numeric;
    v_ba_ordine   vendite.ordini.billing_account_id%TYPE;
    v_ordine_lbl  text;
    v_ba_ddt      vendite.ddt.billing_account_id%TYPE;
    v_ddt_lbl     text;
  BEGIN
    -- =========================================================
    -- Scopo:
    --   Guardia di consistenza su INSERT/UPDATE di
    --   ordini_righe_fulfillment: verifica articolo, UOM
    --   operativa, quantita residua e over-fulfillment.
    --   RESO-AWARE (rev 2026-07-13): il residuo include l'addendo
    --   ri-consegna (helper unico fn_ordine_riga_qta_riconsegna),
    --   coerente con fn_ordine_ha_residuo_evasione.
    -- =========================================================

    -- 0) Guardia quantita > 0
    IF NEW.qta_evasa IS NULL OR NEW.qta_evasa <= 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_ordini_ful_guard_consistenza','E_QTA_NON_POSITIVA',
        jsonb_build_object('campo', 'qta_evasa', 'qta_evasa', NEW.qta_evasa),
        NULL::uuid,
        NEW.qta_evasa::text
      );
    END IF;

    -- 1) Lock concorrente per evitare over-fulfillment:
    --    blocco riga ordine
    PERFORM 1
      FROM vendite.ordini_righe orr
    WHERE orr.id = NEW.ordine_riga_id
    FOR UPDATE;

    --    blocco gruppo fulfillment della stessa ordine_riga
    --    (serializza modifiche parallele sulle stesse righe)
    PERFORM 1
      FROM vendite.ordini_righe_fulfillment q
    WHERE q.ordine_riga_id = NEW.ordine_riga_id
    FOR UPDATE;

    -- 2) Leggo riga ordine (valori coerenti dopo lock)
    SELECT articolo_id, COALESCE(uom_operativa_id, 0), quantita
      INTO v_art_ordine, v_uom_ordine, v_qta_ordine
      FROM vendite.ordini_righe
    WHERE id = NEW.ordine_riga_id;

    -- 3) Leggo riga ddt
    SELECT articolo_id, COALESCE(uom_operativa_id, 0)
      INTO v_art_ddt, v_uom_ddt
      FROM vendite.ddt_righe
    WHERE id = NEW.ddt_riga_id;

    IF v_art_ordine IS NULL OR v_art_ddt IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_ordini_ful_guard_consistenza','E_FULFILL_NOT_FOUND',
        jsonb_build_object('ordine_riga_id', NEW.ordine_riga_id,
                          'ddt_riga_id', NEW.ddt_riga_id),
        NULL::uuid,
        'ordine_riga', NEW.ordine_riga_id::text,
        'ddt_riga', NEW.ddt_riga_id::text
      );
    END IF;

    -- 4) Match articolo
    IF v_art_ordine <> v_art_ddt THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_ordini_ful_guard_consistenza','E_ARTICOLO_MISMATCH',
        jsonb_build_object('ordine_riga_id', NEW.ordine_riga_id,
                          'ddt_riga_id', NEW.ddt_riga_id),
        NULL::uuid,
        'ordine_riga', NEW.ordine_riga_id::text,
        'ddt_riga', NEW.ddt_riga_id::text
      );
    END IF;

    -- 5) Match UOM operativa (solo se presenti su entrambe: 0 = non impostata)
    IF v_uom_ordine <> 0 AND v_uom_ddt <> 0 AND v_uom_ordine <> v_uom_ddt THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_ordini_ful_guard_consistenza','E_UOM_MISMATCH',
        jsonb_build_object('ordine_riga_id', NEW.ordine_riga_id,
                          'ddt_riga_id', NEW.ddt_riga_id,
                          'uom_ordine', v_uom_ordine,
                          'uom_ddt', v_uom_ddt),
        NULL::uuid,
        -- rev 2026-08-04 (bonifica F3): v_uom_ordine e v_uom_ddt sono
        --   bigint e il parametro e' VARIADIC text[]. Senza ::text la
        --   chiamata non si risolve e il mismatch di UoM non viene
        --   mai riportato con il suo codice.
        'ordine_riga', NEW.ordine_riga_id::text, v_uom_ordine::text,
        'ddt_riga', NEW.ddt_riga_id::text, v_uom_ddt::text
      );
    END IF;

    -- 5-bis) Il cliente — rev 2026-10-09 (brief-db-esecutivi-ba-coppia,
    --    D-6): la riga di DDT evade una riga d'ordine DELLO STESSO
    --    billing account. «Un esecutivo derivato ha il BA della sua
    --    sorgente»: prima una riga di DDT del cliente A poteva evadere
    --    l'ordine del cliente B, e la diagnosi del push spingeva le righe
    --    su BA diversi. Le altre due porte della regola sono la testata
    --    del DDT (vendite.trgfn_ddt_guard_cliente_sorgente) e il reso.
    SELECT o.billing_account_id, 'ordine ' || COALESCE(o.numero, '#' || o.id::text)
      INTO v_ba_ordine, v_ordine_lbl
      FROM vendite.ordini_righe orr
      JOIN vendite.ordini o ON o.id = orr.ordine_id
     WHERE orr.id = NEW.ordine_riga_id;

    SELECT d.billing_account_id, 'DDT ' || COALESCE(d.numero, '#' || d.id::text)
      INTO v_ba_ddt, v_ddt_lbl
      FROM vendite.ddt_righe dr
      JOIN vendite.ddt d ON d.id = dr.ddt_id
     WHERE dr.id = NEW.ddt_riga_id;

    IF v_ba_ordine IS DISTINCT FROM v_ba_ddt THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_ordini_ful_guard_consistenza','E_DOC_CLIENTE_DIVERSO_DA_SORGENTE',
        jsonb_build_object('ordine_riga_id', NEW.ordine_riga_id,
                          'ddt_riga_id', NEW.ddt_riga_id,
                          'billing_account_ordine', v_ba_ordine,
                          'billing_account_ddt', v_ba_ddt),
        NULL::uuid,
        v_ddt_lbl,
        v_ordine_lbl
      );
    END IF;

    -- 6) Residuo = quantita ordine - sum(evasa esistente, esclusa
    --    riga corrente in UPDATE) + addendo reso (ri-consegna).
    SELECT COALESCE(SUM(q.qta_evasa), 0)
      INTO v_qta_evasa
      FROM vendite.ordini_righe_fulfillment q
    WHERE q.ordine_riga_id = NEW.ordine_riga_id
      AND (TG_OP <> 'UPDATE' OR q.id <> NEW.id);

    v_residuo := v_qta_ordine - v_qta_evasa
               + vendite.fn_ordine_riga_qta_riconsegna(NEW.ordine_riga_id);

    IF NEW.qta_evasa > v_residuo THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_ordini_ful_guard_consistenza','E_QTA_SUPERA_RESIDUO',
        jsonb_build_object('ordine_riga_id', NEW.ordine_riga_id,
                          'qta_ordine', v_qta_ordine,
                          'evasa_pre', v_qta_evasa,
                          'qta_nuova', NEW.qta_evasa,
                          'residuo', v_residuo),
        NULL::uuid,
        'ordine_riga', NEW.ordine_riga_id::text,
        'qta_ordine', v_qta_ordine::text,
        'evasa_pre', v_qta_evasa::text,
        'qta_nuova', NEW.qta_evasa::text,
        'residuo', v_residuo::text
      );
    END IF;

    RETURN NEW;
  END;
  $function$

COMMENT ON FUNCTION vendite.trgfn_ordini_ful_guard_consistenza()
IS 'Guard consistenza fulfillment: articolo/uom/residuo + over-fulfillment (E_QTA_SUPERA_RESIDUO). RESO-AWARE: residuo include addendo ri-consegna (fn_ordine_riga_qta_riconsegna), coerente con fn_ordine_ha_residuo_evasione. rev 2026-07-13. rev 2026-10-09 (brief-db-esecutivi-ba-coppia, D-6): + il cliente, E_DOC_CLIENTE_DIVERSO_DA_SORGENTE — la riga di DDT evade solo righe d''ordine dello stesso billing account.';
```

</div>

---
{% include-markdown "signature-core.md" %}
