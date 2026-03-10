{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_auth_user_guard_persona_fisica.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_auth_user_guard_persona_fisica`

```sql
CREATE FUNCTION trgfn_risorse_umane_auth_user_guard_persona_fisica()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: guard su risorse_umane_auth_user — consente il collegamento
--   auth_user solo per soggetti persona fisica pura.
-- Regole:
--   1. Il soggetto non deve avere partita_iva (no professionisti/ditte individuali)
--   2. Il soggetto deve avere codice_fiscale (persona fisica identificata)
-- Nota: il vincolo emittente fiscale (user deve essere associato ad almeno
--   un emittente) e' verificato al login lato Django (auth view), non qui,
--   perche' user_emittenti_fiscali richiede auth_user_id che esiste solo
--   dopo la creazione del bridge.
DECLARE
  v_soggetto_id    anagrafiche.risorse_umane.soggetto_id%TYPE;
  v_partita_iva    anagrafiche.soggetti.partita_iva%TYPE;
  v_codice_fiscale anagrafiche.soggetti.codice_fiscale%TYPE;
BEGIN
  -- Recupera il soggetto collegato alla risorsa umana
  SELECT ru.soggetto_id
    INTO v_soggetto_id
    FROM anagrafiche.risorse_umane ru
   WHERE ru.id = NEW.risorsa_umana_id;

  -- Recupera i dati fiscali del soggetto
  SELECT s.partita_iva, s.codice_fiscale
    INTO v_partita_iva, v_codice_fiscale
    FROM anagrafiche.soggetti s
   WHERE s.id = v_soggetto_id;

  -- 1. Guard no P.IVA: un soggetto con partita_iva (anche se ha CF)
  --    e' un professionista o ditta individuale, non un dipendente.
  IF v_partita_iva IS NOT NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_AUTH_USER_SOGGETTO_CON_PIVA',
      jsonb_build_object(
        'table', TG_TABLE_NAME,
        'risorsa_umana_id', NEW.risorsa_umana_id,
        'soggetto_id', v_soggetto_id,
        'nota', 'Solo persone fisiche pure (senza partita IVA) possono avere un account di login'
      ),
      NULL::uuid,
      NEW.risorsa_umana_id::text
    );
  END IF;

  -- 2. Guard CF obbligatorio: il soggetto deve avere codice fiscale
  --    per poter essere identificato come persona fisica.
  IF v_codice_fiscale IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'database',
      TG_NAME,
      'E_AUTH_USER_SOGGETTO_SENZA_CF',
      jsonb_build_object(
        'table', TG_TABLE_NAME,
        'risorsa_umana_id', NEW.risorsa_umana_id,
        'soggetto_id', v_soggetto_id,
        'nota', 'Il soggetto deve avere un codice fiscale per poter accedere al sistema'
      ),
      NULL::uuid,
      NEW.risorsa_umana_id::text
    );
  END IF;

  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica()
IS 'Guard su risorse_umane_auth_user: consente il collegamento auth_user solo per soggetti persona fisica pura (CF obbligatorio, P.IVA vietata). Il vincolo emittente fiscale e'' verificato al login lato Django.';
```

---
{% include-markdown "signature-core.md" %}
