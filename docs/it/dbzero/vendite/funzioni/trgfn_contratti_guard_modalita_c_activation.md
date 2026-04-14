# ⚙️ Funzione `trgfn_contratti_guard_modalita_c_activation`

```sql
CREATE FUNCTION trgfn_contratti_guard_modalita_c_activation()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_guard_modalita_c_activation()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_new_codice_interno config.stati_doc_contratti.codice_interno%TYPE;
    v_righe_totali       integer;
    v_righe_senza_prezzo integer;
BEGIN
    -- Short-circuit 1: se la NUOVA versione non e' (non sta diventando)
    -- modalita' C, il guard non si applica.
    IF NEW.listino_id IS NOT NULL THEN
        RETURN NEW;
    END IF;

    -- Risolvi il codice_interno dello stato NUOVO.
    SELECT s.codice_interno INTO v_new_codice_interno
      FROM config.stati_doc_contratti s
     WHERE s.id = NEW.stato_doc_contratto_id;

    -- Short-circuit 2: se il contratto non e' ATTIVO (ne' lo diventa),
    -- modalita' C senza righe complete e' ammissibile (DRAFT).
    IF v_new_codice_interno IS DISTINCT FROM 'ATTIVO' THEN
        RETURN NEW;
    END IF;

    -- Short-circuit 3: su UPDATE, se ne' stato ne' listino cambiano,
    -- nulla di rilevante e' mutato (ricontrollare sarebbe spreco).
    IF TG_OP = 'UPDATE'
       AND OLD.listino_id IS NULL
       AND OLD.stato_doc_contratto_id = NEW.stato_doc_contratto_id THEN
        RETURN NEW;
    END IF;

    -- Conteggio righe e righe con prezzo_unitario NULL.
    SELECT COUNT(*),
           COUNT(*) FILTER (WHERE cr.prezzo_unitario IS NULL)
      INTO v_righe_totali, v_righe_senza_prezzo
      FROM vendite.contratti_righe cr
     WHERE cr.contratto_id = NEW.id
       AND COALESCE(cr.attivo, true) = true;

    IF v_righe_totali = 0 THEN
        -- %s: contratto_id.
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME,
            'E_CONTRATTO_MODALITA_C_SENZA_RIGHE',
            jsonb_build_object('contratto_id', NEW.id),
            NULL::uuid,
            NEW.id::text
        );
    END IF;

    IF v_righe_senza_prezzo > 0 THEN
        -- %s: contratto_id, righe_senza_prezzo, righe_totali.
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            TG_NAME,
            'E_CONTRATTO_MODALITA_C_RIGHE_INCOMPLETE',
            jsonb_build_object(
                'contratto_id', NEW.id,
                'righe_totali', v_righe_totali,
                'righe_senza_prezzo', v_righe_senza_prezzo
            ),
            NULL::uuid,
            NEW.id::text,
            v_righe_senza_prezzo::text,
            v_righe_totali::text
        );
    END IF;

    RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_guard_modalita_c_activation()
IS 'Guard BEFORE INS/UPD (stato) su vendite.contratti: in transizione ad ATTIVO, se listino_id NULL (modalita'' C) tutte le righe attive devono avere prezzo_unitario NOT NULL. Pricing v5.';
```

---
{% include-markdown "signature-core.md" %}
