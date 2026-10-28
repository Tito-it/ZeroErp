{% include-markdown "it/dbzero/pagamenti/manual/trgfn_enti_incasso_guard_psp.md" %}
# ⚙️ Funzione `trgfn_enti_incasso_guard_psp`

```sql
CREATE FUNCTION trgfn_enti_incasso_guard_psp()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_enti_incasso_guard_psp()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_is_ruolo_psp boolean := false;
  v_exists_psp boolean := false;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Validare la coerenza tra tipo ente incasso e ruolo PSP.
  --
  -- Regole:
  --   - se tipo = 'PSP', soggetto_ruolo_id e' obbligatorio
  --   - il soggetto_ruolo_id deve appartenere al tipo ruolo PSP
  --   - deve esistere una riga attiva in anagrafiche.psp
  --
  -- Rev 2026-08-21 (passo P-7): i tre E_GENERICO passano a tre
  -- codici distinti — i tre gradini hanno tre rimedi diversi — e il
  -- terzo punto smette di loggare TG_NAME al posto del nome della
  -- funzione. Nessun predicato e' cambiato.
  -- =========================================================

  IF NEW.tipo = 'PSP' THEN
    IF NEW.soggetto_ruolo_id IS NULL THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_enti_incasso_guard_psp', 'E_ENTE_INCASSO_PSP_SOGGETTO_RUOLO_OBBLIGATORIO',
        jsonb_build_object(
          'detail', 'soggetto_ruolo_id obbligatorio per tipo PSP',
          'campo', 'soggetto_ruolo_id',
          'tipo', NEW.tipo,
          'codice', NEW.codice
        ),
        NULL::uuid,
        NEW.codice
      );
    END IF;

    -- Il confronto e' su codice_interno, che e' immutabile, non
    -- sull'etichetta modificabile.
    SELECT EXISTS (
      SELECT 1
      FROM anagrafiche.soggetti_ruoli sr
      JOIN config.tipi_ruoli tr
        ON tr.id = sr.tipo_ruolo_id
      WHERE sr.id = NEW.soggetto_ruolo_id
        AND tr.codice_interno = 'PSP'
    )
    INTO v_is_ruolo_psp;

    IF NOT v_is_ruolo_psp THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_enti_incasso_guard_psp', 'E_ENTE_INCASSO_PSP_RUOLO_NON_PSP',
        jsonb_build_object(
          'detail', 'soggetto_ruolo_id non coerente con ruolo PSP',
          'campo', 'soggetto_ruolo_id',
          'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
          'tipo', NEW.tipo
        ),
        NULL::uuid,
        NEW.soggetto_ruolo_id::text
      );
    END IF;

    SELECT EXISTS (
      SELECT 1
      FROM anagrafiche.psp p
      WHERE p.soggetto_ruolo_id = NEW.soggetto_ruolo_id
        AND p.attivo IS TRUE
    )
    INTO v_exists_psp;

    -- ⚠️ CONFLITTO_STATO e non NON_TROVATO: l'ente e il
    --    soggetto-ruolo esistono, manca un censimento a monte.
    IF NOT v_exists_psp THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_enti_incasso_guard_psp', 'E_ENTE_INCASSO_PSP_NON_CENSITO',
        jsonb_build_object(
          'detail', 'soggetto_ruolo_id PSP non censito in anagrafiche.psp',
          'soggetto_ruolo_id', NEW.soggetto_ruolo_id
        ),
        NULL::uuid,
        NEW.soggetto_ruolo_id::text
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$
```

</div>

---
{% include-markdown "signature-core.md" %}
