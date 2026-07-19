{% include-markdown "it/dbzero/vendite/manual/trgfn_ddt_guard_causale_emissione.md" %}
# ⚙️ Funzione `trgfn_ddt_guard_causale_emissione`

```sql
CREATE FUNCTION trgfn_ddt_guard_causale_emissione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_ddt_guard_causale_emissione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: bloccare l'emissione (EMESSO) di un DDT che non dichiara
--   la causale, o che dichiara VENDITA ma ha righe senza prezzo
--   risolvibile (brief-db-fatturazione-ddt-resi §4a, DL-28).
DECLARE
    v_stato_codice  config.stati_doc_ddt.codice_interno%TYPE;
    v_fatturabile   boolean;
    v_riga_senza    vendite.ddt_righe.id%TYPE;
BEGIN
    SELECT sdd.codice_interno INTO v_stato_codice
      FROM config.stati_doc_ddt sdd
     WHERE sdd.id = NEW.stato_doc_ddt_id;

    IF v_stato_codice IS DISTINCT FROM 'EMESSO' THEN
        RETURN NEW;
    END IF;

    -- R1: la causale dichiara l'intento. Senza, il documento e'
    -- ambiguo per la fatturazione.
    IF NEW.causale_trasporto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_DDT_CAUSALE_OBBLIGATORIA',
            jsonb_build_object(
                'ddt_id', NEW.id,
                'numero', NEW.numero),
            NEW.tx_id,
            COALESCE(NEW.numero, NEW.id::text)
        );
    END IF;

    SELECT ct.fatturabile INTO v_fatturabile
      FROM config.causali_trasporto ct
     WHERE ct.id = NEW.causale_trasporto_id;

    -- Causale non fatturabile: solo trasporto, prezzi irrilevanti.
    IF NOT COALESCE(v_fatturabile, false) THEN
        RETURN NEW;
    END IF;

    -- R2: prezzo risolvibile = proprio OPPURE ereditato dalla riga
    -- d'ordine via fulfillment (stessa COALESCE del lister).
    SELECT dr.id INTO v_riga_senza
      FROM vendite.ddt_righe dr
      LEFT JOIN LATERAL (
          SELECT or_r.prezzo_unitario
            FROM vendite.ordini_righe_fulfillment ful
            JOIN vendite.ordini_righe or_r ON or_r.id = ful.ordine_riga_id
           WHERE ful.ddt_riga_id = dr.id
           ORDER BY ful.id LIMIT 1
      ) src ON TRUE
     WHERE dr.ddt_id = NEW.id
       AND dr.attivo IS TRUE
       AND COALESCE(dr.prezzo_unitario, src.prezzo_unitario) IS NULL
     ORDER BY dr.id
     LIMIT 1;

    IF v_riga_senza IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', TG_NAME, 'E_DDT_PREZZO_NON_RISOLVIBILE',
            jsonb_build_object(
                'ddt_id',   NEW.id,
                'numero',   NEW.numero,
                'riga_id',  v_riga_senza),
            NEW.tx_id,
            COALESCE(NEW.numero, NEW.id::text),
            v_riga_senza::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_ddt_guard_causale_emissione()
IS 'Gate all''emissione DDT (brief-db-fatturazione-ddt-resi §4a, DL-28): (1) causale di trasporto obbligatoria — in DRAFT il NULL resta legittimo, dall''emissione no, cosi'' il lister non deve trattare il NULL in modo speciale; (2) se la causale e'' fatturabile, ogni riga attiva deve avere un prezzo risolvibile (proprio o ereditato dalla riga ordine via fulfillment — le righe da evasione senza prezzo proprio restano legittime). Causale non fatturabile: prezzi irrilevanti. Mirror di trgfn_ddt_guard_indirizzi_obbligatori. NB: vw_ddt_righe_iva_base NON e'' riusabile qui (filtra prezzo_unitario IS NOT NULL). rev 2026-07-18.';
```

---
{% include-markdown "signature-core.md" %}
