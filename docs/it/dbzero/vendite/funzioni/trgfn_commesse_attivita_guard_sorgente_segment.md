# ⚙️ Funzione `trgfn_commesse_attivita_guard_sorgente_segment`

```sql
CREATE FUNCTION trgfn_commesse_attivita_guard_sorgente_segment()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_commesse_attivita_guard_sorgente_segment()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- =========================================================
-- Scopo: la chiave del push di una riga di commessa nomina il
--   documento della sua provenienza: il codice del tipo e l'uid
--   del documento (<CODICE>:<uid>...), quello che compone
--   script.fn_segment_key. La chiave del gruppo fatturabile ne
--   legge l'uid (D-6): una chiave che nominasse un altro documento
--   metterebbe la riga nel gruppo sbagliato, in silenzio.
-- Le righe senza tipo (ONERE manuale, RETTIFICA) passano: la loro
--   chiave e' MAN:... o quella della riga che rettificano.
-- ⚠️ Scatta dopo il guard unico (ordine alfabetico): il documento,
--   qui, esiste e si vede.
-- =========================================================
DECLARE
    v_codice  config.sorgenti.codice_interno%TYPE;
    v_doc_uid vendite.preventivi.uid%TYPE;   -- l'uid di un documento qualsiasi: uuid
BEGIN
    IF NEW.sorgente_tipo_id IS NULL THEN
        RETURN NEW;
    END IF;

    SELECT s.codice_interno INTO v_codice
      FROM config.sorgenti s
     WHERE s.id = NEW.sorgente_tipo_id;

    SELECT d.documento_uid INTO v_doc_uid
      FROM script.fn_sorgente_documento(NEW.sorgente_tipo_id, NEW.sorgente_id, NEW.sorgente_uid) d;

    IF script.fn_segment_key_sorgente(NEW.segment_key) IS DISTINCT FROM v_codice
       OR v_doc_uid IS NULL
       OR script.fn_segment_key_uid(NEW.segment_key) IS DISTINCT FROM v_doc_uid::text THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.trgfn_commesse_attivita_guard_sorgente_segment',
            'E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO',
            jsonb_build_object('commessa_id',      NEW.commessa_id,
                               'segment_key',      NEW.segment_key,
                               'sorgente_tipo_id', NEW.sorgente_tipo_id,
                               'sorgente_id',      NEW.sorgente_id,
                               'sorgente_uid',     NEW.sorgente_uid,
                               'documento_uid',    v_doc_uid),
            NULL::uuid,
            NEW.segment_key::text, v_codice::text,
            COALESCE(NEW.sorgente_id::text, NEW.sorgente_uid::text));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_commesse_attivita_guard_sorgente_segment()
IS 'Guard di vendite.commesse_attivita: la chiave del push (segment_key) di una riga con provenienza nomina il documento di quella provenienza, cioe'' comincia con il codice_interno del tipo e l''uid del documento, come la compone script.fn_segment_key. Lo legge da script.fn_segment_key_sorgente e script.fn_segment_key_uid, l''uid del documento dal BB che risolve. Serve perche'' la chiave del gruppo fatturabile prende l''uid dalla chiave del push (vendite.fn_gruppo_fatturabile_key_di_attivita): una chiave con l''uid di un altro documento, o senza, metterebbe la riga nel gruppo sbagliato o lo renderebbe impossibile da costruire. Le righe senza tipo (ONERE manuale, RETTIFICA) passano. Solleva E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO. Montato BEFORE INSERT OR UPDATE OF segment_key e le colonne della provenienza, dopo il guard unico (script.trgfn_guard_sorgente).';
```

</div>

---
{% include-markdown "signature-core.md" %}
