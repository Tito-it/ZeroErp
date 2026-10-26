{% include-markdown "it/dbzero/vendite/manual/trgfn_resi_riconsegne_guard.md" %}
# ⚙️ Funzione `trgfn_resi_riconsegne_guard`

```sql
CREATE FUNCTION trgfn_resi_riconsegne_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_resi_riconsegne_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: consistenza ponte ri-consegna. Tipo ri-consegna
--   obbligatorio; Sigma qta <= qta_resa; lock anti-concorrenza.
-- rev 2026-07-26: il residuo sottrae ANCHE le rinunce
--   (resi_righe_rinunce). Senza, su una riga da 10 con 7 rinunciati
--   il guard vedrebbe residuo=10 e lascerebbe ri-spedire 10:
--   Sigma ric + Sigma rin = 17 > 10. Le due uscite condividono la
--   stessa copertura, quindi lo stesso invariante.
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
        'database','trgfn_resi_riconsegne_guard','E_QTA_NON_POSITIVA',
        jsonb_build_object('campo', 'qta', 'qta', NEW.qta), NEW.tx_id, NEW.qta::text);
    END IF;

    -- 1) Lock riga reso + gruppo riconsegne + gruppo rinunce
    --    (rev 2026-07-26: anche le rinunce, stessa copertura).
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

    IF v_riapre IS DISTINCT FROM true THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_riconsegne_guard','E_RESO_RICONSEGNA_TIPO_NON_VALIDO',
        jsonb_build_object('resi_riga_id', NEW.resi_riga_id),
        NEW.tx_id, NEW.resi_riga_id::text);
    END IF;

    -- 3) Copertura residua = qta_resa - Sigma ric - Sigma rin
    --    (escl. riga corrente in UPDATE sul proprio ponte).
    SELECT COALESCE(SUM(q.qta), 0)
      INTO v_gia_ric
      FROM vendite.resi_righe_riconsegne q
     WHERE q.resi_riga_id = NEW.resi_riga_id
       AND (TG_OP <> 'UPDATE' OR q.id <> NEW.id);

    SELECT COALESCE(SUM(r.qta), 0)
      INTO v_gia_rin
      FROM vendite.resi_righe_rinunce r
     WHERE r.resi_riga_id = NEW.resi_riga_id;

    v_residuo := v_qta_resa - v_gia_ric - v_gia_rin;

    IF NEW.qta > v_residuo THEN
      PERFORM script.fn_log_and_raise_error(
        'database','trgfn_resi_riconsegne_guard','E_RESO_RICONSEGNA_SUPERA_RESO',
        jsonb_build_object('resi_riga_id', NEW.resi_riga_id,
                           'qta_resa', v_qta_resa,
                           'gia_riconsegnato', v_gia_ric,
                           'gia_rinunciato', v_gia_rin,
                           'qta_nuova', NEW.qta,
                           'residuo', v_residuo),
        NEW.tx_id,
        NEW.resi_riga_id::text, v_qta_resa::text,
        v_gia_ric::text, NEW.qta::text, v_residuo::text);
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_resi_riconsegne_guard()
IS 'Guard ponte ri-consegna: tipo riapre_residuo obbligatorio (E_RESO_RICONSEGNA_TIPO_NON_VALIDO) + Sigma qta <= qta_resa (E_RESO_RICONSEGNA_SUPERA_RESO), lock FOR UPDATE. Mirror trgfn_ordini_ful_guard_consistenza. rev 2026-07-13. rev 2026-07-26 (brief-db-chiusura-riconsegna-reso-definitivo S4.6): il residuo sottrae ANCHE le rinunce (vendite.resi_righe_rinunce) e il lock copre entrambi i ponti - le due uscite (ri-spedire / dichiarare definitiva) condividono la stessa copertura, quindi lo stesso invariante quantita >= Sigma ric + Sigma rin, presidiato dai due lati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
