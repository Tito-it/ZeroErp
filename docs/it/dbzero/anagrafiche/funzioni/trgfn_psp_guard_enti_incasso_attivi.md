{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_psp_guard_enti_incasso_attivi.md" %}
# ⚙️ Funzione `trgfn_psp_guard_enti_incasso_attivi`

```sql
CREATE FUNCTION trgfn_psp_guard_enti_incasso_attivi()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_psp_guard_enti_incasso_attivi()
 RETURNS trigger
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_quanti  bigint;  -- un conteggio (count(*)): nessuna colonna dietro
BEGIN
    -- =========================================================
    -- Scopo: un PSP con canali d'incasso attivi non si spegne.
    --   Montata BEFORE UPDATE OF attivo, WHEN acceso -> spento.
    --
    -- Il legame e' il ruolo: pagamenti.enti_incasso.soggetto_ruolo_id
    --   e' il ruolo del PSP (anagrafiche.psp.soggetto_ruolo_id, che
    --   non si cambia). Ogni canale che nomina un ruolo PSP e' un
    --   canale di quel PSP: non si filtra il tipo.
    --
    -- ⚠️ SECURITY DEFINER: i canali hanno la row level security, e
    --   da invocante quelli di un'altra azienda non si vedrebbero.
    -- =========================================================
    SELECT count(*)
      INTO v_quanti
      FROM pagamenti.enti_incasso e
     WHERE e.soggetto_ruolo_id = NEW.soggetto_ruolo_id
       AND e.attivo IS TRUE;

    IF v_quanti > 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database',
            'anagrafiche.trgfn_psp_guard_enti_incasso_attivi',
            'E_PSP_ENTI_INCASSO_ATTIVI',
            jsonb_build_object(
                'campo', 'attivo',
                'psp_id', NEW.id,
                'soggetto_ruolo_id', NEW.soggetto_ruolo_id,
                'enti_attivi', v_quanti
            ),
            NULL::uuid,
            NEW.codice::text
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_psp_guard_enti_incasso_attivi()
IS 'Guard BEFORE UPDATE OF attivo di anagrafiche.psp: un PSP con canali d''incasso attivi (pagamenti.enti_incasso che nominano il suo ruolo) non si spegne, E_PSP_ENTI_INCASSO_ATTIVI. Si spengono prima i canali. SECURITY DEFINER: i canali sono sotto row level security, e il guard li conta tutti, di ogni azienda. Il verso opposto, il canale acceso che vuole il PSP acceso, lo tiene pagamenti.trgfn_enti_incasso_guard_psp.';
```

</div>

---
{% include-markdown "signature-core.md" %}
