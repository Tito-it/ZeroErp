{% include-markdown "it/dbzero/vendite/manual/trgfn_contratti_default_emittente.md" %}
# ⚙️ Funzione `trgfn_contratti_default_emittente`

```sql
CREATE FUNCTION trgfn_contratti_default_emittente()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_contratti_default_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_user_id_text text;
  v_user_id      integer;
BEGIN
  -- 1) Skip se gia' valorizzato esplicitamente nel payload
  --    (admin globale, batch job, migration data, push da offerta).
  IF NEW.emittente_fiscale_id IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- 2) Lettura GUC app.current_user_id (missing_ok=true).
  --    JwtAuditAuthentication la setta SEMPRE su request auth ok.
  v_user_id_text := current_setting('app.current_user_id', true);

  IF v_user_id_text IS NULL OR btrim(v_user_id_text) = '' THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'trgfn_contratti_default_emittente',
      'E_CONTRATTO_EMITTENTE_NON_RISOLTO',
      jsonb_build_object(
        'detail', 'GUC app.current_user_id vuota e payload senza emittente_fiscale_id',
        'numero_contratto', NEW.numero
      ),
      NULL::uuid,
      concat('GUC vuota, numero=', NEW.numero)
    );
  END IF;

  -- Cast safe: la GUC e' sempre numerica se valorizzata.
  v_user_id := v_user_id_text::integer;

  -- 3) Resolver operatore -> emittente (modello 1-a-1).
  --    Ritorna NULL per admin globale (no riga in user_emittenti_fiscali).
  NEW.emittente_fiscale_id := script.fn_resolve_emittente_for_user(v_user_id);

  IF NEW.emittente_fiscale_id IS NULL THEN
    PERFORM script.fn_log_and_raise_error(
      'vendite',
      'trgfn_contratti_default_emittente',
      'E_CONTRATTO_EMITTENTE_NON_RISOLTO',
      jsonb_build_object(
        'detail', 'Operatore senza EF assegnato (admin globale): payload deve specificare emittente_fiscale_id',
        'auth_user_id', v_user_id,
        'numero_contratto', NEW.numero
      ),
      NULL::uuid,
      concat('auth_user_id=', v_user_id::text, ', numero=', NEW.numero)
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION vendite.trgfn_contratti_default_emittente()
IS 'BEFORE INSERT trigger fn: setta contratti.emittente_fiscale_id da GUC app.current_user_id via script.fn_resolve_emittente_for_user. Skip se valorizzato esplicitamente (admin globale, push da offerta). Solleva E_CONTRATTO_EMITTENTE_NON_RISOLTO se GUC vuota o operatore admin globale senza payload esplicito. Pattern simmetrico a trgfn_preventivi_default_emittente.';
```

---
{% include-markdown "signature-core.md" %}
