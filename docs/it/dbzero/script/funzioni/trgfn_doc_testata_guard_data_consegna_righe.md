{% include-markdown "it/dbzero/script/manual/trgfn_doc_testata_guard_data_consegna_righe.md" %}
# ⚙️ Funzione `trgfn_doc_testata_guard_data_consegna_righe`

```sql
CREATE FUNCTION trgfn_doc_testata_guard_data_consegna_righe()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_doc_testata_guard_data_consegna_righe()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ v_documento nudo: e' il selettore del montaggio (TG_ARGV);
    --   lo valida il lettore.
    v_documento text := TG_ARGV[0];
    -- La data piu' bassa fuori regola (righe di
    -- script.fn_doc_date_consegna_anteriori): composta.
    v_fuori     record;
    -- La frase (script.fn_get_stato_testata_documento): composta.
    v_etichetta text;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Rifiutare una data del documento successiva a una data
    --   di consegna gia' scritta su una riga attiva. BEFORE
    --   UPDATE FOR EACH ROW WHEN la data cambia.
    -- =========================================================
    SELECT a.colonna, a.data_consegna
      INTO v_fuori
      FROM script.fn_doc_date_consegna_anteriori(v_documento, NEW.id, NEW.data) AS a
     ORDER BY a.data_consegna, a.posizione
     LIMIT 1;

    IF FOUND THEN
        SELECT t.etichetta
          INTO v_etichetta
          FROM script.fn_get_stato_testata_documento(v_documento, NEW.id) AS t;

        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text,
            'E_DOC_DATA_OLTRE_CONSEGNA_RIGHE',
            jsonb_build_object('campo',              'data',
                               'testata_id',         NEW.id,
                               'colonna_righe',      v_fuori.colonna,
                               'prima_data_consegna', v_fuori.data_consegna),
            NEW.tx_id,
            COALESCE(v_etichetta, initcap(v_documento) || ' #' || NEW.id::text),
            to_char(NEW.data,              'DD/MM/YYYY'),
            to_char(v_fuori.data_consegna, 'DD/MM/YYYY'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_doc_testata_guard_data_consegna_righe()
IS 'Guard di testata (2026-10-13, collaudo date di consegna): la data del documento non si sposta oltre una data di consegna gia'' scritta su una sua riga attiva — il lato opposto di script.trgfn_doc_righe_guard_data_consegna, senza il quale la regola si aggirerebbe dalla testata. Rifiuto E_DOC_DATA_OLTRE_CONSEGNA_RIGHE (DATO_ERRATO), campo data; valori: etichetta del documento, data nuova, la data di consegna piu'' bassa fra quelle che resterebbero prima (il limite oltre cui la testata non va). Righe e colonne le dice script.fn_doc_date_consegna_anteriori (DEFINER, sede unica dell''elenco). Montaggio: TG_ARGV[0] = documento (ORDINE, PREVENTIVO). BEFORE UPDATE FOR EACH ROW WHEN (OLD.data IS DISTINCT FROM NEW.data), fascia _a10_: fuori bozza parla prima il lock della testata (_a05_).';
```

</div>

---
{% include-markdown "signature-core.md" %}
