{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_guard_annullamento.md" %}
# ⚙️ Funzione `trgfn_preventivi_guard_annullamento`

```sql
CREATE FUNCTION trgfn_preventivi_guard_annullamento()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_guard_annullamento()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: impedire l'annullamento di un preventivo che ha gia'
--   prodotto qualcosa a valle (un ordine generato, o l'ingresso
--   in una commessa). La regola vive in
--   script.fn_check_preventivo_annullabile, la stessa letta da
--   fn_available_actions_preventivo per accendere il bottone:
--   qui si solleva soltanto, col codice del PRIMO motivo.
--   Brief: brief-db-vie-uscita-operatore §3.1.
--
-- rev 2026-11-14 (brief-db-stati-documento-dal-vocabolario, giro 6a):
--   l'annullo e' la destinazione che il vocabolario marca is_abortito,
--   non un codice. Il codice resta per il contesto dell'errore.
--
-- rev 2026-08-04 (bonifica riferimenti morti, F5): `NEW.codice` non e' una
--   colonna di vendite.preventivi. L'identificativo leggibile e' `numero`
--   (varchar); ci sono anche `uid` (uuid, la chiave usata dalle catene
--   documentali) e `rev`. Il refuso e' nato con la funzione, tre changeSet
--   fa, ed e' arrivato al controllo lo stesso giorno.
DECLARE
    v_codice_a config.stati_doc_preventivi.codice_interno%TYPE;
    -- La destinazione e' lo stato di annullo? Dal vocabolario.
    v_abortito config.stati_doc_preventivi.is_abortito%TYPE;
    v_motivi   jsonb;
BEGIN
    -- No-op se lo stato non cambia davvero.
    IF NEW.stato_doc_preventivo_id IS NOT DISTINCT FROM OLD.stato_doc_preventivo_id THEN
        RETURN NEW;
    END IF;

    SELECT sdp.codice_interno, sdp.is_abortito
      INTO v_codice_a, v_abortito
      FROM config.stati_doc_preventivi sdp
     WHERE sdp.id = NEW.stato_doc_preventivo_id;

    -- Stato non trovato: v_abortito NULL, niente da giudicare (la FK lo
    -- esclude, come prima).
    IF v_abortito IS NOT TRUE THEN
        RETURN NEW;
    END IF;

    v_motivi := script.fn_check_preventivo_annullabile(NEW.id);

    IF jsonb_array_length(v_motivi) > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME::text,
            v_motivi -> 0 ->> 'codice',
            jsonb_build_object(
                'preventivo_id', NEW.id,
                'numero',        NEW.numero,
                'stato_a',       v_codice_a,
                'motivi',        v_motivi
            ),
            NEW.tx_id,
            coalesce(NEW.numero, NEW.id::text),
            coalesce(v_motivi -> 0 ->> 'dettaglio', '0')
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_guard_annullamento()
IS 'Guard dell''annullo del preventivo (BEFORE UPDATE OF stato_doc_preventivo_id). Quando lo stato cambia verso lo stato di annullo, quello che il vocabolario config.stati_doc_preventivi marca is_abortito, solleva il primo motivo di script.fn_check_preventivo_annullabile: E_PREV_ORDINE_GIA_GENERATO (un ordine non annullato nato dal preventivo) o E_PREV_ANNULLA_COMMESSA_EMESSA (righe del preventivo gia'' emesse dalla commessa). E'' la stessa funzione con cui script.fn_available_actions_preventivo spegne l''annullo, col motivo. Il codice dello stato serve solo al contesto dell''errore. Che il passaggio sia nella matrice lo giudica vendite.trgfn_preventivi_guard_transizione, che scatta dopo.';
```

</div>

---
{% include-markdown "signature-core.md" %}
