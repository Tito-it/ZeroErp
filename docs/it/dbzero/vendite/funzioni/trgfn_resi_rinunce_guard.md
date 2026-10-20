{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_rinunce_guard.md" %}
# ⚙️ Funzione `trgfn_resi_rinunce_guard`

```sql
CREATE FUNCTION trgfn_resi_rinunce_guard()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_rinunce_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: consistenza ponte RINUNCE. Tipo ri-consegna obbligatorio;
--   Sigma riconsegnate + Sigma rinunciate <= qta_resa;
--   lock anti-concorrenza. Mirror di trgfn_resi_riconsegne_guard.
DECLARE
    v_qta_resa vendite.resi_righe.quantita%TYPE;
    v_riapre   config.tipi_reso.riapre_residuo%TYPE;
    v_gia_ric  numeric;
    v_gia_rin  numeric;
    v_residuo  numeric;
BEGIN
    -- 0) qta > 0 (difesa oltre al CHECK).
    IF NEW.qta IS NULL OR NEW.qta <= 0 THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_rinunce_guard','E_QTA_NON_POSITIVA',
        jsonb_build_object('campo', 'qta', 'qta', NEW.qta), NEW.tx_id, NEW.qta::text);
    END IF;

    -- 1) Lock riga reso + ENTRAMBI i gruppi (serializza rinuncia e
    --    ri-consegna concorrenti: condividono la stessa copertura).
    PERFORM 1 FROM vendite.resi_righe WHERE id = NEW.resi_riga_id FOR UPDATE;
    PERFORM 1 FROM vendite.resi_righe_riconsegne q
      WHERE q.resi_riga_id = NEW.resi_riga_id FOR UPDATE;
    PERFORM 1 FROM vendite.resi_righe_rinunce r
      WHERE r.resi_riga_id = NEW.resi_riga_id FOR UPDATE;

    -- 2) Riga reso: qta_resa + tipo ri-consegna.
    SELECT rr.quantita, tr.riapre_residuo
      INTO v_qta_resa, v_riapre
      FROM vendite.resi_righe rr
      JOIN config.tipi_reso tr ON tr.id = rr.tipo_reso_id
     WHERE rr.id = NEW.resi_riga_id;

    -- Si rinuncia solo a merce rientrata PER essere ri-consegnata:
    -- su una riga A_CREDITO non c'e' nulla da ri-consegnare, quindi
    -- nulla a cui rinunciare. Riuso del codice del gemello (533).
    IF v_riapre IS DISTINCT FROM true THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_rinunce_guard','E_RESO_RICONSEGNA_TIPO_NON_VALIDO',
        jsonb_build_object('resi_riga_id', NEW.resi_riga_id),
        NEW.tx_id, NEW.resi_riga_id::text);
    END IF;

    -- 3) Copertura residua = qta_resa - Sigma ric - Sigma rin
    --    (esclusa la riga corrente in UPDATE).
    SELECT COALESCE(SUM(q.qta), 0)
      INTO v_gia_ric
      FROM vendite.resi_righe_riconsegne q
     WHERE q.resi_riga_id = NEW.resi_riga_id;

    SELECT COALESCE(SUM(r.qta), 0)
      INTO v_gia_rin
      FROM vendite.resi_righe_rinunce r
     WHERE r.resi_riga_id = NEW.resi_riga_id
       AND (TG_OP <> 'UPDATE' OR r.id <> NEW.id);

    v_residuo := v_qta_resa - v_gia_ric - v_gia_rin;

    IF NEW.qta > v_residuo THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_rinunce_guard','E_RESO_RINUNCIA_SUPERA_RESO',
        jsonb_build_object('resi_riga_id', NEW.resi_riga_id,
                           'qta_resa', v_qta_resa,
                           'gia_riconsegnato', v_gia_ric,
                           'gia_rinunciato', v_gia_rin,
                           'qta_nuova', NEW.qta,
                           'residuo', v_residuo),
        NEW.tx_id,
        NEW.resi_riga_id::text, v_qta_resa::text,
        v_gia_ric::text, v_gia_rin::text,
        NEW.qta::text, v_residuo::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_rinunce_guard()
IS 'Guard ponte RINUNCE: tipo riapre_residuo obbligatorio (E_RESO_RICONSEGNA_TIPO_NON_VALIDO, riuso 533) + Sigma riconsegnate + Sigma rinunciate <= qta_resa (E_RESO_RINUNCIA_SUPERA_RESO 560), lock FOR UPDATE su resi_righe e su ENTRAMBI i ponti. Mirror di trgfn_resi_riconsegne_guard: le due uscite (ri-spedire / dichiarare definitiva) condividono la stessa copertura, quindi lo stesso invariante e'' presidiato dai due lati. Il FOR UPDATE sulla riga reso padre serializza rinuncia e ri-consegna concorrenti senza advisory lock. rev 2026-07-26.';
```

</div>

---
{% include-markdown "signature-core.md" %}
