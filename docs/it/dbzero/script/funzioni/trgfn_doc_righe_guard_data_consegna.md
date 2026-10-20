{% include-markdown "it/dbzero/script/manual/trgfn_doc_righe_guard_data_consegna.md" %}
# ⚙️ Funzione `trgfn_doc_righe_guard_data_consegna`

```sql
CREATE FUNCTION trgfn_doc_righe_guard_data_consegna()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_righe_guard_data_consegna()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ v_documento nudo: e' il selettore del montaggio (TG_ARGV);
    --   lo valida il lettore. v_testata_id e' l'id del padre (due
    --   testate diverse).
    v_documento  text   := TG_ARGV[0];
    v_col_padre  text   := TG_ARGV[1];
    v_testata_id bigint := (to_jsonb(NEW) ->> TG_ARGV[1])::bigint;
    -- La prima data fuori regola (righe di
    -- script.fn_doc_date_consegna_anteriori): composta, nessuna
    -- colonna di cui sia il riflesso.
    v_fuori      record;
    -- La frase (script.fn_get_stato_testata_documento, RETURNS
    -- TABLE di text): composta.
    v_etichetta  text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare una data di consegna anteriore alla data del
    --   documento. BEFORE INSERT OR UPDATE FOR EACH ROW: in UPDATE
    --   il lettore giudica solo le date cambiate (o tutte, se la
    --   riga torna attiva o cambia testata).
    -- =========================================================
    SELECT a.colonna, a.data_consegna, a.data_documento
      INTO v_fuori
      FROM script.fn_doc_date_consegna_anteriori(
               v_documento, v_testata_id, NULL,
               to_jsonb(NEW),
               CASE WHEN TG_OP = 'UPDATE' THEN to_jsonb(OLD) END) AS a
     ORDER BY a.posizione
     LIMIT 1;

    IF FOUND THEN
        SELECT t.etichetta
          INTO v_etichetta
          FROM script.fn_get_stato_testata_documento(v_documento, v_testata_id) AS t;

        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text,
            'E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE',
            jsonb_build_object('campo',      v_fuori.colonna,
                               'riga_id',    NEW.id,
                               v_col_padre,  v_testata_id),
            NEW.tx_id,
            COALESCE(v_etichetta, initcap(v_documento) || ' #' || v_testata_id::text),
            to_char(v_fuori.data_consegna,  'DD/MM/YYYY'),
            to_char(v_fuori.data_documento, 'DD/MM/YYYY'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_righe_guard_data_consegna()
IS 'Guard di riga (2026-10-13, collaudo date di consegna): una data di consegna di una riga non viene prima della data del documento. Rifiuto E_DOC_RIGA_DATA_CONSEGNA_ANTERIORE (DATO_ERRATO), campo = la colonna fuori regola; valori: etichetta del documento, data di consegna, data del documento. La data NULL resta ammessa («nessuna data»), la stessa data del documento pure. Il predicato non sta qui: lo dice script.fn_doc_date_consegna_anteriori (DEFINER, sede unica dell''elenco delle colonne di consegna), che in UPDATE giudica solo le date cambiate — tutte se la riga torna attiva o cambia testata — e non giudica una riga spenta. Montaggio: TG_ARGV[0] = documento (ORDINE, PREVENTIVO), TG_ARGV[1] = colonna della testata. BEFORE INSERT OR UPDATE FOR EACH ROW, fascia _a10_. Il lato opposto (la testata che si sposta oltre le righe) e'' script.trgfn_doc_testata_guard_data_consegna_righe.';
```

</div>

---
{% include-markdown "signature-core.md" %}
