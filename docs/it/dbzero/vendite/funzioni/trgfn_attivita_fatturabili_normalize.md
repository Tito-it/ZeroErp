{% include-markdown "it/dbzero/vendite/manual/trgfn_attivita_fatturabili_normalize.md" %}
# ⚙️ Funzione `trgfn_attivita_fatturabili_normalize`

```sql
CREATE FUNCTION trgfn_attivita_fatturabili_normalize()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_attivita_fatturabili_normalize()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_emittente_id anagrafiche.emittenti_fiscali.soggetto_ruolo_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Normalizza campi base e risolve tipo_doc_fiscale/valuta.
  --
  -- Regole:
  --   - competenza_mese sempre valorizzata e al primo del mese
  --   - se NULL -> mese di posticipa_al (se presente)
  --   - competenza_dal/al: se NULL, default su data_attivita
  --   - sorgente_riga default 0 se sorgente valorizzata
  --   - tipo_doc_fiscale_id: da sorgente_origine_tipo_id
  --     (business originale), fallback su sorgente_tipo_id
  --   - valuta_id: BA -> emittente fiscale -> gestore
  --   - Commessa-aware: quando commessa_attivita_id IS NOT NULL
  --     lo snapshot CA e` gia` completo per competenze,
  --     si preserva risoluzione tipo_doc/valuta se NULL.
  -- =========================================================

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

  -- -------------------------------------------------------
  -- Righe da commessa: lo snapshot competenze e` gia` completo.
  -- Si preserva risoluzione tipo_doc_fiscale_id e valuta_id
  -- perche` CA potrebbe non averli.
  -- -------------------------------------------------------
  IF NEW.commessa_attivita_id IS NOT NULL THEN
    -- sorgente_riga default
    IF NEW.sorgente_tipo_id IS NOT NULL AND NEW.sorgente_riga IS NULL THEN
      NEW.sorgente_riga := 0;
    END IF;

    -- tipo_doc_fiscale_id: CA potrebbe non averlo
    IF NEW.tipo_doc_fiscale_id IS NULL THEN
      IF NEW.sorgente_origine_tipo_id IS NOT NULL THEN
        NEW.tipo_doc_fiscale_id := vendite.fn_get_tipo_doc_fiscale_id(
          NEW.sorgente_origine_tipo_id
        );
      ELSIF NEW.sorgente_tipo_id IS NOT NULL THEN
        NEW.tipo_doc_fiscale_id := vendite.fn_get_tipo_doc_fiscale_id(
          NEW.sorgente_tipo_id
        );
      END IF;
    END IF;

    -- valuta_id: emittente dalla commessa (gia` risolto da fn_get_or_create_commessa)
    IF NEW.valuta_id IS NULL AND NEW.billing_account_id IS NOT NULL THEN
      SELECT c.emittente_soggetto_ruolo_id
        INTO v_emittente_id
        FROM vendite.commesse c
       WHERE c.id = NEW.commessa_id;
      NEW.valuta_id := vendite.fn_get_valuta_id(
        NEW.billing_account_id, v_emittente_id
      );
    END IF;

    RETURN NEW;
  END IF;

  -- -------------------------------------------------------
  -- Flusso standard (righe non da commessa)
  -- -------------------------------------------------------
  IF NEW.competenza_mese IS NULL AND NEW.posticipa_al IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.posticipa_al)::date;
  ELSIF NEW.competenza_mese IS NOT NULL THEN
    NEW.competenza_mese := date_trunc('month', NEW.competenza_mese)::date;
  END IF;

  IF NEW.competenza_dal IS NULL THEN
    NEW.competenza_dal := NEW.data_attivita;
  END IF;

  IF NEW.competenza_al IS NULL THEN
    NEW.competenza_al := NEW.competenza_dal;
  END IF;

  IF NEW.sorgente_tipo_id IS NOT NULL THEN
    IF NEW.sorgente_riga IS NULL THEN
      NEW.sorgente_riga := 0;
    END IF;
  END IF;

  -- Risolvi emittente da BA per risoluzione valuta
  IF NEW.billing_account_id IS NOT NULL THEN
    v_emittente_id := anagrafiche.fn_get_emittente_fiscale_id(
      NEW.billing_account_id
    );
  END IF;

  -- §26 B+D: risolve tipo_doc_fiscale_id dalla sorgente business
  -- originale (non da COMMESSA). Fallback legacy per righe senza
  -- sorgente_origine_tipo_id.
  IF NEW.tipo_doc_fiscale_id IS NULL THEN
    IF NEW.sorgente_origine_tipo_id IS NOT NULL THEN
      NEW.tipo_doc_fiscale_id := vendite.fn_get_tipo_doc_fiscale_id(
        NEW.sorgente_origine_tipo_id
      );
    ELSIF NEW.sorgente_tipo_id IS NOT NULL THEN
      NEW.tipo_doc_fiscale_id := vendite.fn_get_tipo_doc_fiscale_id(
        NEW.sorgente_tipo_id
      );
    END IF;
  END IF;

  IF NEW.valuta_id IS NULL THEN
    NEW.valuta_id := vendite.fn_get_valuta_id(
      NEW.billing_account_id,
      v_emittente_id
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_normalize()
IS 'Normalizza competenze/sorgente; risolve tipo_doc_fiscale_id e valuta_id (catena BA -> emittente -> gestore). Commessa-aware: skip normalizzazione competenze quando commessa_attivita_id IS NOT NULL.';
```

</div>

---
{% include-markdown "signature-core.md" %}
