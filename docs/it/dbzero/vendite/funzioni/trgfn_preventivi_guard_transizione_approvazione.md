{% include-markdown "it/dbzero/vendite/manual/trgfn_preventivi_guard_transizione_approvazione.md" %}
# ⚙️ Funzione `trgfn_preventivi_guard_transizione_approvazione`

```sql
CREATE FUNCTION trgfn_preventivi_guard_transizione_approvazione()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_preventivi_guard_transizione_approvazione()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- codice_interno dello stato target del preventivo.
    -- Risolto via lookup su config.stati_doc_preventivi per id.
    v_stato_codice config.stati_doc_preventivi.codice_interno%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Bloccare la transizione a stato_interno='ACCETTATO' di un
    --   preventivo che ha righe ancora in workflow approvazione
    --   prezzo (stato_approvazione_prezzo='PENDING'). Garantisce
    --   che le richieste L3 siano esitate prima della
    --   finalizzazione commerciale.
    --
    -- Regole:
    --   1. Risolve codice_interno del nuovo stato (NEW).
    --   2. Se diverso da 'ACCETTATO' -> pass-through (scopo
    --      limitato alla transizione finale).
    --   3. Se ACCETTATO -> EXISTS riga PENDING -> raise.
    --
    -- Naming: uso codice_interno (non codice) per stabilita'
    -- rispetto a relabelling UX del codice business-visible.
    -- =========================================================

    SELECT sdp.codice_interno
      INTO v_stato_codice
      FROM config.stati_doc_preventivi sdp
     WHERE sdp.id = NEW.stato_doc_preventivo_id;

    -- Early return: transizione verso stato diverso da ACCETTATO
    -- non ha preconditions su workflow approvazione.
    IF v_stato_codice IS DISTINCT FROM 'ACCETTATO' THEN
        RETURN NEW;
    END IF;

    -- Transizione ad ACCETTATO: blocca se esistono righe PENDING.
    IF EXISTS (
        SELECT 1
          FROM vendite.preventivi_righe pr
         WHERE pr.preventivo_id = NEW.id
           AND pr.stato_approvazione_prezzo = 'PENDING'::config.stato_approvazione_prezzo
    ) THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_PREVENTIVO_RIGHE_PRICING_PENDENTI',
            jsonb_build_object(
                'preventivo_id', NEW.id,
                'hint', 'Attendi esito dell''approvazione pendente o rifiuta la richiesta prima di accettare il preventivo.'
            ),
            NULL::uuid,
            NEW.id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_preventivi_guard_transizione_approvazione()
IS 'Trigger function: blocca transizione preventivo ad ACCETTATO se esistono righe con stato_approvazione_prezzo=PENDING. Sprint E listini v5 §14.6 (DB-E-4). Raise E_PREVENTIVO_RIGHE_PRICING_PENDENTI.';
```

---
{% include-markdown "signature-core.md" %}
