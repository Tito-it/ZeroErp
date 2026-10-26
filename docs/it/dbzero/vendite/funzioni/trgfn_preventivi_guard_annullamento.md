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
-- rev 2026-08-04 (bonifica riferimenti morti, F5): `NEW.codice` non e' una
--   colonna di vendite.preventivi. L'identificativo leggibile e' `numero`
--   (varchar); ci sono anche `uid` (uuid, la chiave usata dalle catene
--   documentali) e `rev`. Il refuso e' nato con la funzione, tre changeSet
--   fa, ed e' arrivato al controllo lo stesso giorno.
DECLARE
    v_codice_a config.stati_doc_preventivi.codice_interno%TYPE;
    v_motivi   jsonb;
BEGIN
    -- No-op se lo stato non cambia davvero.
    IF NEW.stato_doc_preventivo_id IS NOT DISTINCT FROM OLD.stato_doc_preventivo_id THEN
        RETURN NEW;
    END IF;

    SELECT sdp.codice_interno
      INTO v_codice_a
      FROM config.stati_doc_preventivi sdp
     WHERE sdp.id = NEW.stato_doc_preventivo_id;

    IF v_codice_a IS DISTINCT FROM 'ANNULLATO' THEN
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
IS 'Trigger function: blocca l''annullamento di un preventivo che ha gia'' un figlio a valle (ordine generato o riga in commesse_sorgenti), delegando il verdetto a script.fn_check_preventivo_annullabile — la stessa funzione letta da fn_available_actions_preventivo. Creata 2026-08-04 con la riattivazione delle transizioni verso ANNULLATO (brief-db-vie-uscita-operatore).';
```

</div>

---
{% include-markdown "signature-core.md" %}
