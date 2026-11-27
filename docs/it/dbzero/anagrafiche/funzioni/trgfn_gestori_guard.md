{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_gestori_guard.md" %}
# ⚙️ Funzione `trgfn_gestori_guard`

```sql
CREATE FUNCTION trgfn_gestori_guard()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_gestori_guard()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_soggetto_id   anagrafiche.soggetti.id%TYPE;
    v_partita_iva   anagrafiche.soggetti.partita_iva%TYPE;
    v_existing_id   anagrafiche.gestori.id%TYPE;
BEGIN
-- =========================================================
-- Scopo: guard di dominio di anagrafiche.gestori, BEFORE
--   INSERT OR UPDATE.
--
-- Regole:
--  0) il ruolo esiste           -> E_GESTORE_SOGGETTO_RUOLO_MANCANTE
--  1) il soggetto del gestore ha la partita IVA
--                               -> E_RUOLO_RICHIEDE_PIVA
--  2) il gestore e' uno solo    -> E_GESTORE_SINGLETON_VIOLATO
--
-- ⭐ Il singleton ha due sedi, e ognuna ha il suo mestiere: qui
--   il caso normale, con la frase per l'operatore; l'indice
--   anagrafiche.uq_gestori_singleton le scritture concorrenti,
--   che questa lettura non vede (due transazioni aperte insieme
--   non vedono l'una la riga dell'altra). Nessuna delle due si
--   toglie.
--
-- ⚠️ La partita IVA si giudica quando si scrive il gestore. Se
--   dopo la si toglie al soggetto, la ferma
--   anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori solo
--   quando il dettaglio del soggetto la vuole
--   (config.tipi_soggetto_dettaglio.piva_obbligatoria); con un
--   dettaglio che non la vuole il gestore resta senza. E' un
--   limite dichiarato, non un guard sul soggetto.
-- =========================================================

    ----------------------------------------------------------------
    -- 0) Il soggetto_ruolo esiste: si risale al soggetto
    ----------------------------------------------------------------
    SELECT s.id, s.partita_iva
      INTO v_soggetto_id, v_partita_iva
      FROM anagrafiche.soggetti_ruoli sr
      JOIN anagrafiche.soggetti s
        ON s.id = sr.soggetto_id
     WHERE sr.id = NEW.soggetto_ruolo_id;

    IF v_soggetto_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_GESTORE_SOGGETTO_RUOLO_MANCANTE',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'soggetto_ruolo_id', NEW.soggetto_ruolo_id
            ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 1) Il soggetto del gestore ha la partita IVA
    ----------------------------------------------------------------
    IF v_partita_iva IS NULL OR btrim(v_partita_iva) = '' THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_RUOLO_RICHIEDE_PIVA',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'soggetto_id', v_soggetto_id,
                'soggetto_ruolo_id', NEW.soggetto_ruolo_id
            ),
            NULL::uuid,
            'gestore',
            v_soggetto_id::text,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    ----------------------------------------------------------------
    -- 2) Il gestore e' uno solo. id <> NEW.id: l'UPDATE della
    --    stessa riga passa.
    ----------------------------------------------------------------
    SELECT g.id
      INTO v_existing_id
      FROM anagrafiche.gestori g
     WHERE g.id <> COALESCE(NEW.id, -1)
     ORDER BY g.id
     LIMIT 1;

    IF FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            TG_NAME,
            'E_GESTORE_SINGLETON_VIOLATO',
            jsonb_build_object(
                'table', TG_TABLE_NAME,
                'existing_gestore_id', v_existing_id,
                'new_soggetto_ruolo_id', NEW.soggetto_ruolo_id
            ),
            NULL::uuid,
            NEW.soggetto_ruolo_id::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_gestori_guard()
IS 'Guard BEFORE INSERT OR UPDATE di anagrafiche.gestori. Il ruolo esiste (E_GESTORE_SOGGETTO_RUOLO_MANCANTE), il soggetto ha la partita IVA (E_RUOLO_RICHIEDE_PIVA), il gestore e'' uno solo (E_GESTORE_SINGLETON_VIOLATO). Il singleton lo tiene anche l''indice anagrafiche.uq_gestori_singleton, per le scritture concorrenti che questo guard non vede. La partita IVA si giudica quando si scrive il gestore: toglierla dopo al soggetto la ferma anagrafiche.trgfn_soggetti_guard_cf_piva_obbligatori solo se il dettaglio del soggetto la vuole.';
```

</div>

---
{% include-markdown "signature-core.md" %}
