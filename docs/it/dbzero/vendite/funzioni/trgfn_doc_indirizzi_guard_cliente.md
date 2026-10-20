# ⚙️ Funzione `trgfn_doc_indirizzi_guard_cliente`

```sql
CREATE FUNCTION trgfn_doc_indirizzi_guard_cliente()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- ⚠️ v_documento nudo: e' il selettore del montaggio (TG_ARGV), senza
    --   colonna di vocabolario. v_documento_id e' POLIMORFO: l'id di sei
    --   testate diverse.
    v_documento    text := TG_ARGV[0];
    v_fk_col       pg_catalog.pg_attribute.attname%TYPE;
    v_documento_id bigint;
    v_ruolo        anagrafiche.soggetti_ruoli.id%TYPE;
    v_istanza      anagrafiche.indirizzi.istanza_utility_id%TYPE;
    v_trovato      boolean := false;
    v_motivo       text;   -- motivo macchina del predicato, senza vocabolario
    v_tipo_descr   config.tipi_indirizzi.descrizione%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Un indirizzo d'anagrafica scritto su un documento deve essere
    --   del cliente del documento (ruolo e, se legato a una
    --   fornitura, istanza). Gli una-tantum passano sempre.
    -- =========================================================
    SELECT s.colonna_fk INTO v_fk_col
      FROM script.fn_doc_indirizzi_sede(v_documento) AS s;

    -- Montaggio errato: errore di chiamante, non di dato.
    IF v_fk_col IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_DOC_TIPO_NON_GESTITO',
            jsonb_build_object('trigger',   TG_NAME,
                               'table',     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                               'documento', v_documento),
            NULL::uuid,
            COALESCE(v_documento, '<null>'));
    END IF;

    v_documento_id := (to_jsonb(NEW) ->> v_fk_col)::bigint;

    -- Un UPDATE che non tocca il legame (origini, documento) non si
    -- rigiudica: il guard giudica la provenienza, non lo snapshot.
    IF TG_OP = 'UPDATE'
       AND NEW.origine_indirizzo_id      IS NOT DISTINCT FROM OLD.origine_indirizzo_id
       AND NEW.origine_soggetto_ruolo_id IS NOT DISTINCT FROM OLD.origine_soggetto_ruolo_id
       AND v_documento_id IS NOT DISTINCT FROM (to_jsonb(OLD) ->> v_fk_col)::bigint THEN
        RETURN NEW;
    END IF;

    -- Una-tantum: nessun cliente da confrontare.
    IF NEW.origine_indirizzo_id IS NULL AND NEW.origine_soggetto_ruolo_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT c.soggetto_ruolo_id, c.istanza_utility_id, true
      INTO v_ruolo, v_istanza, v_trovato
      FROM script.fn_get_cliente_testata_documento(v_documento, v_documento_id) AS c;

    -- Testata assente: la FK parlera'.
    IF NOT v_trovato THEN
        RETURN NEW;
    END IF;

    v_motivo := script.fn_indirizzo_documento_fuori_cliente(
                    NEW.origine_indirizzo_id, NEW.origine_soggetto_ruolo_id,
                    v_ruolo, v_istanza);

    IF v_motivo IS NOT NULL THEN
        SELECT t.descrizione INTO v_tipo_descr
          FROM config.tipi_indirizzi t
         WHERE t.id = NEW.tipo_indirizzo_id;

        PERFORM script.fn_log_and_raise_error(
            'vendite', TG_NAME::text, 'E_INDIRIZZO_DOC_NON_DEL_CLIENTE',
            jsonb_build_object(
                'campo',                     'tipo_indirizzo_id',
                'table',                     TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
                'documento',                 v_documento,
                'testata_id',                v_documento_id,
                'motivo',                    v_motivo,
                'tipo_indirizzo_id',         NEW.tipo_indirizzo_id,
                'origine_indirizzo_id',      NEW.origine_indirizzo_id,
                'origine_soggetto_ruolo_id', NEW.origine_soggetto_ruolo_id,
                'soggetto_ruolo_id',         v_ruolo,
                'istanza_utility_id',        v_istanza),
            NEW.tx_id,
            COALESCE(v_tipo_descr, NEW.tipo_indirizzo_id::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_doc_indirizzi_guard_cliente()
IS 'Building block BEFORE INSERT OR UPDATE OF origine_indirizzo_id, origine_soggetto_ruolo_id, <colonna verso la testata> FOR EACH ROW sulle sei vendite.*_indirizzi, TG_ARGV[0] = documento (DDT | ORDINE | PREVENTIVO | OFFERTA | CONTRATTO | FATTURA, script.fn_doc_indirizzi_sede). Un indirizzo d''anagrafica (origine valorizzata) deve essere del cliente del documento: il predicato e'' script.fn_indirizzo_documento_fuori_cliente, il cliente lo legge script.fn_get_cliente_testata_documento (DEFINER). Rifiuta con E_INDIRIZZO_DOC_NON_DEL_CLIENTE (DATO_ERRATO, campo tipo_indirizzo_id, valore: il tipo leggibile; nel contesto il motivo ALTRO_CLIENTE | ALTRA_FORNITURA). Una-tantum, testata assente, UPDATE che non cambia origini ne'' documento: passa. Montaggio con un documento ignoto: E_DOC_TIPO_NON_GESTITO (TECNICO). Sostituisce il guard d''origine del backend (upsert_indirizzo_documento), che lo diceva solo per chi passava dal service. Brief: brief-db-indirizzi-documento-seguono-il-cliente (§5.4, §7.2 c).';
```

</div>

---
{% include-markdown "signature-core.md" %}
