{% include-markdown "it/dbzero/ui/manual/trgfn_lista_definizione_guard_multi_emittente.md" %}
# ⚙️ Funzione `trgfn_lista_definizione_guard_multi_emittente`

```sql
CREATE FUNCTION trgfn_lista_definizione_guard_multi_emittente()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION ui.trgfn_lista_definizione_guard_multi_emittente()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_owner text;
    v_tocca boolean;
BEGIN
    -- Cosa conta come «tocca il flag»:
    --   INSERT -> solo se nasce gia' acceso (un false esplicito e'
    --             il default e non dichiara niente);
    --   UPDATE -> qualunque cambio di valore.
    IF TG_OP = 'INSERT' THEN
        v_tocca := COALESCE(NEW.multi_emittente, false);
    ELSE
        v_tocca := NEW.multi_emittente IS DISTINCT FROM OLD.multi_emittente;
    END IF;

    IF NOT v_tocca THEN
        RETURN NEW;
    END IF;

    -- ⚠️ Il proprietario si LEGGE, non si scrive a mano: un nome di
    --   ruolo hardcoded sarebbe giusto su questa istanza e falso
    --   sulla prossima.
    SELECT pg_get_userbyid(c.relowner)
      INTO v_owner
      FROM pg_class c
      JOIN pg_namespace n ON n.oid = c.relnamespace
     WHERE n.nspname = 'ui' AND c.relname = 'lista_definizione';

    -- pg_has_role(..., 'USAGE') e' vero per il proprietario e per
    -- chi ne e' membro: il migrate passa, l'applicazione no.
    IF pg_has_role(current_user, v_owner, 'USAGE') THEN
        RETURN NEW;
    END IF;

    PERFORM script.fn_log_and_raise_error(
        'ui',
        'trgfn_lista_definizione_guard_multi_emittente',
        'E_UI_MULTI_EMITTENTE_NON_SCRIVIBILE',
        jsonb_build_object(
            'lista_codice', NEW.codice,
            'lista_id', NEW.id,
            'column', 'multi_emittente',
            'valore_richiesto', NEW.multi_emittente,
            'current_user', current_user,
            'owner_atteso', v_owner,
            'detail', 'Il flag si dichiara nel seed lista_definizione.csv, mai da interfaccia'
        ),
        NULL::uuid,
        NEW.codice::text
    );

    RETURN NEW;  -- irraggiungibile: la riga sopra solleva
END
$function$

COMMENT ON FUNCTION ui.trgfn_lista_definizione_guard_multi_emittente()
IS 'Strato 1 di P-2b (decisione Q1): il flag multi_emittente si scrive solo dal PROPRIETARIO della tabella — cioe'' dal migrate/seed — e mai dall''applicazione. E'' un trigger e non un permesso di colonna perche'' il giro dei grant runtime (90_end/ci_apply/20260205-41, runOnChange) ri-concede UPDATE a livello di TABELLA su tutto lo schema ui a ogni passata: una REVOKE sopravvivrebbe fino al successivo db-ci-apply su dev, e in CI nemmeno un istante. Nessuna GUC di override: la condizione e'' su chi sei, non c''e'' niente da accendere. Il ruolo proprietario si legge da pg_class, non e'' scritto a mano. ⚠️ Copre UNA colonna: il baratto accettato in Q1. Brief perimetro-emittente §11.5.';
```

---
{% include-markdown "signature-core.md" %}
