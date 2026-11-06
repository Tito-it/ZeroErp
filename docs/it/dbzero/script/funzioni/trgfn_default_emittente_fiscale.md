{% include-markdown "it/dbzero/script/manual/trgfn_default_emittente_fiscale.md" %}
# ⚙️ Funzione `trgfn_default_emittente_fiscale`

```sql
CREATE FUNCTION trgfn_default_emittente_fiscale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_default_emittente_fiscale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
  v_modo          text := TG_ARGV[0];   -- NULL se non passato (indice fuori da TG_NARGS)
  v_opzione       text := TG_ARGV[1];
  v_row           jsonb;
  v_tx_id         uuid;
  v_auth_user_id  anagrafiche.identita_digitali.auth_user_id%TYPE;
  v_ef_id         anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
  -- Scopo: riempire emittente_fiscale_id quando la riga arriva senza,
  --   con l'emittente di lavoro di chi scrive (attivo di sessione se in
  --   scope, altrimenti quello assegnato). Building block unico: sostituisce
  --   le copie per documento di vendite. Brief: brief-db-emittente-di-default-un-bb-solo.
  -- Regole:
  --   0. argomenti di montaggio non ammessi -> E_TRIGGER_ARGOMENTI_INVALIDI
  --      (difetto di chi installa: muore al primo INSERT, non tace);
  --   1. valore esplicito -> non si sovrascrive mai una scelta dichiarata;
  --   2. SALTA_CON_SORGENTE e riga con sorgente_tipo_id + una chiave
  --      (sorgente_id o sorgente_uid, rev 2026-11-06 giro 0.3) ->
  --      l'emittente e' del documento padre, lo mette il normalize a valle;
  --   3. GUC app.current_user_id vuota -> LASCIA_NULL: RETURN NEW;
  --      SOLLEVA: E_EMITTENTE_NON_RISOLTO;
  --   4. resolver NULL (admin globale senza assegnazione) -> idem;
  --   5. altrimenti NEW.emittente_fiscale_id := emittente di lavoro.

  -- 0) Argomenti di montaggio.
  IF TG_OP <> 'INSERT'
     OR TG_NARGS < 1 OR TG_NARGS > 2
     OR v_modo NOT IN ('SOLLEVA', 'LASCIA_NULL')
     OR (TG_NARGS = 2 AND v_opzione IS DISTINCT FROM 'SALTA_CON_SORGENTE') THEN
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA::text,
      'script.trgfn_default_emittente_fiscale',
      'E_TRIGGER_ARGOMENTI_INVALIDI',
      jsonb_build_object(
        'detail',    'atteso BEFORE INSERT con TG_ARGV[0] in (SOLLEVA, LASCIA_NULL) e TG_ARGV[1] facoltativo = SALTA_CON_SORGENTE',
        'tabella',   TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        'trigger',   TG_NAME,
        'tg_op',     TG_OP,
        'argomenti', to_jsonb(TG_ARGV)
      ),
      NULL::uuid,
      concat_ws(' ', TG_OP, coalesce(NULLIF(array_to_string(TG_ARGV, ', '), ''), '(nessun argomento)'))
    );
  END IF;

  -- 1) Valore esplicito: non si tocca.
  IF NEW.emittente_fiscale_id IS NOT NULL THEN
    RETURN NEW;
  END IF;

  -- Le colonne facoltative (sorgente_*, tx_id) si leggono in sola lettura da
  -- to_jsonb(NEW): esistono su alcune tabelle montate, non su tutte.
  v_row   := to_jsonb(NEW);
  v_tx_id := NULLIF(v_row ->> 'tx_id', '')::uuid;

  -- 2) Riga nata da un documento sorgente: l'emittente e' quello del padre.
  IF v_opzione = 'SALTA_CON_SORGENTE'
     AND (v_row ->> 'sorgente_tipo_id') IS NOT NULL
     AND ((v_row ->> 'sorgente_id') IS NOT NULL OR (v_row ->> 'sorgente_uid') IS NOT NULL) THEN
    RETURN NEW;
  END IF;

  -- 3) Chi scrive. GUC vuota = nessuno da cui dedurre.
  v_auth_user_id := NULLIF(current_setting('app.current_user_id', true), '')::integer;
  IF v_auth_user_id IS NULL THEN
    IF v_modo = 'LASCIA_NULL' THEN
      RETURN NEW;
    END IF;
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA::text,
      'script.trgfn_default_emittente_fiscale',
      'E_EMITTENTE_NON_RISOLTO',
      jsonb_build_object(
        'detail',  'GUC app.current_user_id vuota e riga senza emittente_fiscale_id: fuori da una sessione utente non c'' e'' nulla da cui dedurlo',
        'campo',   'emittente_fiscale_id',
        'tabella', TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME
      ),
      v_tx_id,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  -- 4) Emittente di lavoro: attivo di sessione se in scope, altrimenti quello
  --    assegnato in config.user_emittenti_fiscali; NULL per un admin globale
  --    senza assegnazione (modalita' «tutti gli emittenti», di sola lettura).
  v_ef_id := script.fn_resolve_emittente_for_user(v_auth_user_id);
  IF v_ef_id IS NULL THEN
    IF v_modo = 'LASCIA_NULL' THEN
      RETURN NEW;
    END IF;
    PERFORM script.fn_log_and_raise_error(
      TG_TABLE_SCHEMA::text,
      'script.trgfn_default_emittente_fiscale',
      'E_EMITTENTE_NON_RISOLTO',
      jsonb_build_object(
        'detail',       'operatore senza emittente assegnato (admin globale in modalita'' tutti gli emittenti): la riga deve dichiararlo',
        'campo',        'emittente_fiscale_id',
        'tabella',      TG_TABLE_SCHEMA || '.' || TG_TABLE_NAME,
        'auth_user_id', v_auth_user_id
      ),
      v_tx_id,
      VARIADIC ARRAY[]::text[]
    );
  END IF;

  -- 5) Il default.
  NEW.emittente_fiscale_id := v_ef_id;
  RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_default_emittente_fiscale()
IS 'BEFORE INSERT generico: riempie emittente_fiscale_id, se NULL, con l''emittente di lavoro di chi scrive (script.fn_resolve_emittente_for_user dalla GUC app.current_user_id). TG_ARGV[0] = SOLLEVA (niente da cui dedurre -> E_EMITTENTE_NON_RISOLTO, DATO_ERRATO, campo emittente_fiscale_id) oppure LASCIA_NULL (decide un normalize a valle o il NOT NULL). TG_ARGV[1] facoltativo = SALTA_CON_SORGENTE: una riga con sorgente_tipo_id e una chiave della sorgente (sorgente_id o sorgente_uid) non si tocca, perche'' l''emittente e'' quello del documento padre; una tabella senza sorgente_id la legge NULL dal JSON. Un valore esplicito non si sovrascrive mai. Argomenti non ammessi -> E_TRIGGER_ARGOMENTI_INVALIDI. La colonna e'' sempre emittente_fiscale_id, l''ancora del perimetro.';
```

</div>

---
{% include-markdown "signature-core.md" %}
