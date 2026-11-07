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
  v_tipo_origine vendite.commesse_attivita.sorgente_tipo_id%TYPE;
BEGIN
  -- =========================================================
  -- Scopo:
  --   Normalizza campi base e risolve tipo_doc_fiscale/valuta.
  --
  -- Regole:
  --   - competenza_mese sempre valorizzata e al primo del mese
  --   - se NULL -> mese di posticipa_al (se presente)
  --   - competenza_dal/al: se NULL, default su data_attivita
  --   - tipo_doc_fiscale_id: dal tipo del documento da cui nasce la
  --     riga di commessa (commesse_attivita.sorgente_tipo_id, per la FK
  --     commessa_attivita_id); la riga senza documento (onere, rettifica)
  --     nasce dalla commessa, e prende il tipo COMMESSA
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
    -- tipo_doc_fiscale_id: CA potrebbe non averlo. Il tipo si legge dalla
    -- riga di commessa: la provenienza dell'attivita' e' la FK
    -- commessa_attivita_id, e la riga di commessa dice da quale documento nasce.
    IF NEW.tipo_doc_fiscale_id IS NULL THEN
      SELECT COALESCE(ca.sorgente_tipo_id, s.id)
        INTO v_tipo_origine
        FROM vendite.commesse_attivita ca
        LEFT JOIN config.sorgenti s ON s.codice_interno = 'COMMESSA'
       WHERE ca.id = NEW.commessa_attivita_id;
      IF v_tipo_origine IS NOT NULL THEN
        NEW.tipo_doc_fiscale_id := vendite.fn_get_tipo_doc_fiscale_id(v_tipo_origine);
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

  -- Risolvi emittente da BA per risoluzione valuta
  IF NEW.billing_account_id IS NOT NULL THEN
    v_emittente_id := anagrafiche.fn_get_emittente_fiscale_id(
      NEW.billing_account_id
    );
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
IS 'Normalizza le competenze e risolve tipo_doc_fiscale_id e valuta_id di vendite.attivita_fatturabili. Sulla riga nata da una riga di commessa (commessa_attivita_id) le competenze arrivano gia'' complete; se manca, tipo_doc_fiscale_id viene dal tipo del documento da cui nasce la riga di commessa (commesse_attivita.sorgente_tipo_id), o dal tipo COMMESSA per la riga senza documento (onere, rettifica), con vendite.fn_get_tipo_doc_fiscale_id; la valuta dall''emittente della commessa. Altrimenti competenza_mese al primo del mese, competenza_dal/al dalla data dell''attivita'', valuta dalla catena BA -> emittente -> gestore.';
```

</div>

---
{% include-markdown "signature-core.md" %}
