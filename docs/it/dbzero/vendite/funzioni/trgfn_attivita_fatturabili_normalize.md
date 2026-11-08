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
  --   Completa tipo_doc_fiscale_id e valuta_id dell'attivita'
  --   fatturabile, che nasce sempre da una riga di commessa
  --   (commessa_attivita_id e' NOT NULL).
  --
  -- Regole:
  --   - le competenze (competenza_mese, competenza_dal/al) arrivano
  --     complete dalla riga di commessa: qui non si toccano. Le
  --     tengono i CHECK della tabella (primo del mese, dal <= al);
  --   - tipo_doc_fiscale_id, se manca: dal tipo del documento da cui
  --     nasce la riga di commessa (commesse_attivita.sorgente_tipo_id);
  --     la riga senza documento (onere, rettifica) prende il tipo
  --     COMMESSA;
  --   - valuta_id, se manca: dal billing account e dall'emittente
  --     della commessa.
  -- =========================================================

  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;

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
END
$function$

COMMENT ON FUNCTION vendite.trgfn_attivita_fatturabili_normalize()
IS 'Completa tipo_doc_fiscale_id e valuta_id di vendite.attivita_fatturabili, BEFORE INSERT OR UPDATE. L''attivita'' nasce sempre da una riga di commessa (commessa_attivita_id NOT NULL) e ne riceve le competenze gia'' complete: qui non si toccano, le tengono i CHECK della tabella. Se manca, tipo_doc_fiscale_id viene dal tipo del documento da cui nasce la riga di commessa (commesse_attivita.sorgente_tipo_id), o dal tipo COMMESSA per la riga senza documento (onere, rettifica), con vendite.fn_get_tipo_doc_fiscale_id; se manca, valuta_id viene dal billing account e dall''emittente della commessa (vendite.fn_get_valuta_id).';
```

</div>

---
{% include-markdown "signature-core.md" %}
