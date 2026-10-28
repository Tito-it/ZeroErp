{% include-markdown "it/dbzero/script/manual/trgfn_guard_emittente_scope.md" %}
# ⚙️ Funzione `trgfn_guard_emittente_scope`

```sql
CREATE FUNCTION trgfn_guard_emittente_scope()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_guard_emittente_scope()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_auth_user_id         anagrafiche.identita_digitali.auth_user_id%TYPE;
  v_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE;
  v_col_value            bigint;
  v_mode                 text := TG_ARGV[0];
  v_col_name             text := TG_ARGV[1];
BEGIN
  -- =========================================================
  -- Difesa in profondita': verifica che l'utente corrente abbia
  -- scope sull'emittente fiscale della riga.
  --
  -- Modalita' (TG_ARGV[0]) — la risoluzione vive tutta in
  -- script.fn_resolve_emittente_fiscale_id:
  --   'soggetto_ruolo' = la colonna contiene soggetto_ruolo_id
  --   'fattura'        = la colonna contiene fattura_id
  --   'fiscale'        = la colonna E' gia' emittente_fiscale_id
  --   'contabile'      = la colonna contiene contabile_id, e il
  --                      perimetro si deriva dal CONTO DI INCASSO
  --                      della distinta (D5)
  --   'listino'        = la colonna contiene listino_id
  --   'magazzino'      = la colonna contiene magazzino_id (Lotto 2)
  --
  -- Se emittente non risolvibile -> skip (nessun padrone).
  --
  -- ⭐ Rev 2026-08-22 (lotto 6, S3-4). La risoluzione era QUI, e
  --   il guard e' SECURITY INVOKER: nel modo 'fattura' leggeva
  --   vendite.fatture sotto row security, e per un utente fuori
  --   perimetro quella lettura dava ZERO RIGHE. Emittente NULL ->
  --   ramo «non risolvibile» -> RETURN NEW. Il guard si spegneva
  --   esattamente nel caso che esiste per coprire, e il controllo
  --   di integrita' referenziale — che gira fuori dalla row
  --   security — non si opponeva: la riga entrava.
  --   Adesso la risoluzione la fa una SECURITY DEFINER, che legge
  --   tutto; qui resta solo l'applicazione della decisione.
  --
  -- ⛔ Rev 2026-09-04 (fase 6, brief processi automatici). Il
  --   ramo «utente NULL -> RETURN NEW» diceva «batch job, nessun
  --   filtro»: era l'ultima porta da cui un processo applicativo
  --   scriveva senza dire chi fosse, e bastava NON impostare una
  --   GUC per aprirla. Adesso passa solo chi bypasserebbe
  --   comunque la RLS.
  --
  -- ⛔ Rev 2026-09-18 (magazzino Lotto 2, sezione 6-ter C1).
  --   row_security_active risponde per il CURRENT_USER, che
  --   dentro una SECURITY DEFINER e' il proprietario: FALSE
  --   sempre. Dentro una DEFINER (current_user <> session_user)
  --   quella risposta non dice niente su chi sta scrivendo: si
  --   risolve comunque l'emittente e, se la riga ha un padrone,
  --   ci si ferma. Una riga senza padrone (le email di sistema)
  --   passa come prima. Provato con fn_accoda_email_sistema.
  -- =========================================================

  -- 1. Leggi user_id dalla sessione PG
  v_auth_user_id := NULLIF(
    current_setting('app.current_user_id', true), ''
  )::integer;

  IF v_auth_user_id IS NULL THEN
    -- ⭐ UN CRITERIO SOLO, E NON E' NOSTRO.
    --   row_security_active() risponde per la tabella in gioco e
    --   per QUESTA sessione: false per il proprietario (senza
    --   FORCE ROW LEVEL SECURITY), per un superuser e per un
    --   ruolo BYPASSRLS. Sono esattamente le sessioni che le
    --   policy non filtrano: se la RLS le lascia passare, questo
    --   guard non ha titolo per fermarle — e viceversa.
    --   ⛔ Non si elenca a mano «proprietario o superuser o
    --   bypassrls»: sarebbe una SECONDA scrittura della stessa
    --   regola, e due scritture prima o poi dissentono.
    IF NOT row_security_active(TG_RELID::regclass) THEN
      -- ⚠️ Ma «per QUESTA sessione» vuol dire per il current_user:
      --   dentro una SECURITY DEFINER e' il proprietario della
      --   funzione, non chi ha chiamato. Fuori da una DEFINER
      --   (current_user = session_user) la risposta vale e si passa.
      -- ⭐ Rev 2026-10-15: si confronta col ruolo di SESSIONE, non col
      --   login. Un utente personale che lavora come proprietario
      --   (`SET role`) ha session_user <> current_user anche fuori
      --   da una DEFINER; una DEFINER cambia current_user ma non il
      --   parametro `role`. Brief: brief-db-ruoli-di-sistema §19.
      IF current_user = coalesce(nullif(current_setting('role'), 'none'), session_user) THEN
        RETURN NEW;
      END IF;

      -- Dentro una DEFINER, senza identita': si guarda la RIGA.
      -- Nessun padrone -> niente da proteggere, passa (email di
      -- sistema). Un padrone -> nessuno risponde di questa
      -- scrittura: si ferma qui sotto.
      v_col_value := (to_jsonb(NEW) ->> v_col_name)::bigint;
      IF v_col_value IS NULL THEN
        RETURN NEW;
      END IF;
      v_emittente_fiscale_id :=
          script.fn_resolve_emittente_fiscale_id(v_mode, v_col_value);
      IF v_emittente_fiscale_id IS NULL THEN
        RETURN NEW;
      END IF;
    END IF;

    -- Sessione applicativa senza identita': si ferma. Non e'
    -- «permesso negato a qualcuno» — non c'e' nessuno a cui
    -- negarlo: e' un processo configurato senza identita'.
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA::text,
      'trgfn_guard_emittente_scope',
      'E_SCOPE_SENZA_UTENTE',
      jsonb_build_object(
        'detail', 'Scrittura senza utente in sessione su tabella con perimetro emittente',
        'modo', v_mode,
        'colonna', v_col_name,
        'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        'db_user', current_user,
        'session_user', session_user,
        'dentro_definer', current_user <> coalesce(nullif(current_setting('role'), 'none'), session_user),
        'emittente_fiscale_id', v_emittente_fiscale_id,
        'operazione', TG_OP
      ),
      NULL::uuid,
      TG_TABLE_SCHEMA::text,
      TG_TABLE_NAME::text
    );
  END IF;

  -- 2. Leggi valore colonna da NEW
  v_col_value := (to_jsonb(NEW) ->> v_col_name)::bigint;

  IF v_col_value IS NULL THEN
    RETURN NEW;
  END IF;

  -- Su UPDATE, skip se la colonna non e' cambiata
  IF TG_OP = 'UPDATE' AND
     v_col_value = (to_jsonb(OLD) ->> v_col_name)::bigint THEN
    RETURN NEW;
  END IF;

  -- 3. Risolvi l'emittente FUORI dalla row security.
  v_emittente_fiscale_id :=
      script.fn_resolve_emittente_fiscale_id(v_mode, v_col_value);

  IF v_emittente_fiscale_id IS NULL THEN
    -- ⭐ Nessun padrone: dati non ancora collegati, oppure una
    --   distinta INTERNA (fondo fattura, compensazione) che non e'
    --   il canale di nessuno. Prima questo ramo raccoglieva anche
    --   i documenti altrui; adesso no.
    RETURN NEW;
  END IF;

  -- 4. Verifica scope (canonica auth_user_id, bypass SUPER_ADMIN)
  IF NOT script.fn_check_user_emittente_scope(
           v_auth_user_id, v_emittente_fiscale_id) THEN
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA::text,
      'trgfn_guard_emittente_scope',
      'E_SCOPE_EMITTENTE',
      jsonb_build_object(
        'detail', 'Utente non autorizzato per emittente fiscale',
        'auth_user_id', v_auth_user_id,
        'emittente_fiscale_id', v_emittente_fiscale_id,
        'modo', v_mode,
        'table', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
      ),
      NULL::uuid,
      format(
        'Utente %s non autorizzato per emittente fiscale %s su %s.%s',
        v_auth_user_id, v_emittente_fiscale_id,
        TG_TABLE_SCHEMA, TG_TABLE_NAME
      )
    );
  END IF;

  RETURN NEW;
END
$function$

COMMENT ON FUNCTION script.trgfn_guard_emittente_scope()
IS 'Guard di scrittura del perimetro emittente (BB, montato BEFORE INSERT OR UPDATE su 24+ tabelle con TG_ARGV = modo, colonna): risolve l''emittente della riga con script.fn_resolve_emittente_fiscale_id (DEFINER: legge fuori dalla row security) e chiede a script.fn_check_user_emittente_scope se l''utente in sessione (app.current_user_id) puo'' scriverci — E_SCOPE_EMITTENTE altrimenti. Nessun padrone: passa. Senza utente in sessione passa solo chi la RLS non filtrerebbe comunque (row_security_active: proprietario, superuser, BYPASSRLS), altrimenti E_SCOPE_SENZA_UTENTE (rev 04-09). ⛔ Rev 2026-09-18 (magazzino Lotto 2, C1): dentro una SECURITY DEFINER row_security_active risponde per il proprietario, non per chi chiama — se current_user e'' diverso dal ruolo di sessione (parametro role, o session_user se none: rev 2026-10-15, un utente personale che lavora come proprietario non e'' una DEFINER) e la riga HA un padrone, senza identita'' si ferma comunque; senza padrone (email di sistema) passa. Provato con fn_accoda_email_sistema. E'' il perimetro della primitiva DEFINER di magazzino, rimesso da una sede sola.';
```

</div>

---
{% include-markdown "signature-core.md" %}
