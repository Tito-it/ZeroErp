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
  v_is_ruolo_psp boolean := false;  -- l'esito di un EXISTS: nessuna colonna dietro
  v_psp_attivo   anagrafiche.psp.attivo%TYPE;
  v_psp_codice   anagrafiche.psp.codice%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   La coerenza fra un canale d'incasso di tipo PSP e il suo
  --   prestatore.
  --
  -- Regole (tipo = 'PSP'):
  --   - soggetto_ruolo_id e' obbligatorio;
  --   - il ruolo e' un ruolo PSP;
  --   - il PSP e' censito in anagrafiche.psp (acceso o spento);
  --   - solo per un canale ACCESO: il PSP e' acceso. Un canale
  --     spento si modifica anche col PSP spento.
  --   Il verso opposto (un PSP con canali accesi non si spegne)
  --   lo tiene anagrafiche.trgfn_psp_guard_enti_incasso_attivi.
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

    SELECT p.attivo, p.codice
      INTO v_psp_attivo, v_psp_codice
      FROM anagrafiche.psp p
     WHERE p.soggetto_ruolo_id = NEW.soggetto_ruolo_id;

    -- ⚠️ CONFLITTO_STATO e non NON_TROVATO: l'ente e il
    --    soggetto-ruolo esistono, manca un censimento a monte.
    IF NOT FOUND THEN
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

    -- L'acceso del PSP conta solo per un canale che lavora.
    IF NEW.attivo IS TRUE AND v_psp_attivo IS NOT TRUE THEN
      PERFORM script.fn_log_and_raise_error(
        'database', 'pagamenti.trgfn_enti_incasso_guard_psp', 'E_ENTE_INCASSO_PSP_SPENTO',
        jsonb_build_object(
          'campo', 'attivo',
          'codice', NEW.codice,
          'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
          'psp_codice', v_psp_codice
        ),
        NULL::uuid,
        v_psp_codice::text,
        NEW.codice
      );
    END IF;
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_enti_incasso_guard_psp()
IS 'Guard BEFORE INSERT OR UPDATE di pagamenti.enti_incasso per i canali di tipo PSP. Su ogni scrittura il ruolo c''e'' (E_ENTE_INCASSO_PSP_SOGGETTO_RUOLO_OBBLIGATORIO), e'' un ruolo PSP (E_ENTE_INCASSO_PSP_RUOLO_NON_PSP) e il PSP e'' censito in anagrafiche.psp (E_ENTE_INCASSO_PSP_NON_CENSITO). Un canale acceso vuole il PSP acceso (E_ENTE_INCASSO_PSP_SPENTO); uno spento si modifica anche col PSP spento. Il verso opposto lo tiene anagrafiche.trgfn_psp_guard_enti_incasso_attivi.';
```

</div>

---
{% include-markdown "signature-core.md" %}
