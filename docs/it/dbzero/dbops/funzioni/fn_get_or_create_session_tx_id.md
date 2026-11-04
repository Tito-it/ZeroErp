{% include-markdown "it/dbzero/dbops/manual/fn_get_or_create_session_tx_id.md" %}
# ⚙️ Funzione `fn_get_or_create_session_tx_id`

```sql
CREATE FUNCTION fn_get_or_create_session_tx_id()
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `postgres`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_get_or_create_session_tx_id()
 RETURNS uuid
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
DECLARE
    v_tx_id        dbops.transaction_ids.id%TYPE;
    -- text: il tipo di current_setting, nessuna colonna lo porta
    v_dblink_conn  text;
BEGIN
    ----------------------------------------------------------------------
    -- 0) Se esiste gia' un tx_id in sessione, riusalo e basta
    ----------------------------------------------------------------------
    BEGIN
        v_tx_id := current_setting('dbops.tx_id', true)::uuid;
    EXCEPTION WHEN OTHERS THEN
        v_tx_id := NULL;
    END;

    IF v_tx_id IS NOT NULL THEN
        RETURN v_tx_id;
    END IF;

    ----------------------------------------------------------------------
    -- 1) Il canale e' acceso, e con quale stringa? Lo dice il building
    --    block, PRIMA di aprire qualunque cosa: l'interruttore spento
    --    vale anche per la connessione nuova del passo 3.
    ----------------------------------------------------------------------
    v_dblink_conn := script.fn_canale_log_stringa();

    IF v_dblink_conn IS NULL THEN
        -- Ripiego (a): canale spento o non configurato. Sentinella, e
        -- NIENTE set_config: pubblicare un id non registrato
        -- avvelenerebbe la sessione e farebbe fallire ogni scrittura
        -- tx_id-managed successiva.
        RAISE WARNING
            'dbops.fn_get_or_create_session_tx_id: canale di log spento (myapp.log_with_dblink = off) o non configurato (nessuna stringa di connessione); uso la sentinella uuid_nil e non pubblico la GUC di sessione.';

        RETURN script.uuid_nil();
    END IF;

    ----------------------------------------------------------------------
    -- 2) Assicura la connessione di log persistente. Non solleva mai:
    --    un canale irraggiungibile e' un WARNING, e il passo 3 ripiega.
    ----------------------------------------------------------------------
    PERFORM script.fn_ensure_logconn();

    ----------------------------------------------------------------------
    -- 3) Generazione tx_id tramite dblink verso il DB di log.
    --    E' l'unico percorso che REGISTRA in dbops.transaction_ids, e lo
    --    fa su una connessione separata: la registrazione sopravvive al
    --    rollback della transazione di business (autonomia).
    --    Sulla connessione PERSISTENTE 'logconn', quella che il passo 2
    --    apre o trova gia' aperta: una connessione nuova a ogni
    --    transazione costava ~12 ms, contro 1,3 ms su quella aperta
    --    (misura da superuser, dbdev, 2026-10-18).
    --    La stringa resta il ripiego: se 'logconn' non c'e' (il passo 2
    --    non l'ha potuta aprire) e se e' caduta (server riavviato): la
    --    si chiude e si riprova UNA volta da una connessione nuova.
    ----------------------------------------------------------------------
    BEGIN
        IF 'logconn' = ANY (coalesce(dblink_get_connections(), ARRAY[]::text[])) THEN
            BEGIN
                SELECT tx_id
                INTO v_tx_id
                FROM dblink(
                    'logconn',
                    $gen$
                        SELECT dbops.fn_generate_tx_id(
                            'dbops.fn_get_or_create_session_tx_id',
                            jsonb_build_object('source','fn_get_or_create')
                        )
                    $gen$
                ) AS t(tx_id uuid);
            EXCEPTION WHEN OTHERS THEN
                BEGIN
                    PERFORM dblink_disconnect('logconn');
                EXCEPTION WHEN OTHERS THEN
                    NULL;
                END;
                SELECT tx_id
                INTO v_tx_id
                FROM dblink(
                    v_dblink_conn,
                    $gen$
                        SELECT dbops.fn_generate_tx_id(
                            'dbops.fn_get_or_create_session_tx_id',
                            jsonb_build_object('source','fn_get_or_create')
                        )
                    $gen$
                ) AS t(tx_id uuid);
            END;
        ELSE
            SELECT tx_id
            INTO v_tx_id
            FROM dblink(
                v_dblink_conn,
                $gen$
                    SELECT dbops.fn_generate_tx_id(
                        'dbops.fn_get_or_create_session_tx_id',
                        jsonb_build_object('source','fn_get_or_create')
                    )
                $gen$
            ) AS t(tx_id uuid);
        END IF;

        -- Ripiego (b): dblink ha risposto ma con NULL -> niente id
        -- registrato, quindi sentinella e nessuna pubblicazione.
        IF v_tx_id IS NULL THEN
            RAISE WARNING
                'dbops.fn_get_or_create_session_tx_id: dblink ha restituito NULL; uso la sentinella uuid_nil e non pubblico la GUC di sessione.';
            RETURN script.uuid_nil();
        END IF;

        -- Solo qui l'id e' REGISTRATO: si puo' pubblicare.
        -- Scope LOCALE alla transazione (v1): un identificativo di
        -- transazione non deve sopravvivere alla transazione.
        PERFORM set_config('dbops.tx_id', v_tx_id::text, TRUE);

    EXCEPTION WHEN OTHERS THEN
        -- Ripiego (c): errore dblink -> sentinella, nessuna pubblicazione.
        RAISE WARNING
            'dbops.fn_get_or_create_session_tx_id: errore durante la chiamata dblink a dbops.fn_generate_tx_id: %; uso la sentinella uuid_nil e non pubblico la GUC di sessione.',
            SQLERRM;

        RETURN script.uuid_nil();
    END;

    ----------------------------------------------------------------------
    -- 4) Ritorna il tx_id (mai NULL)
    ----------------------------------------------------------------------
    RETURN v_tx_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_get_or_create_session_tx_id()
IS 'Restituisce il tx_id della transazione (GUC dbops.tx_id) o ne genera uno nuovo via dblink sul canale di log (dbops.fn_generate_tx_id), registrandolo in dbops.transaction_ids fuori dalla transazione di business: la registrazione sopravvive al rollback. Se il canale e'' acceso lo dice script.fn_canale_log_stringa, prima di aprire qualunque connessione. Genera sulla connessione persistente logconn (la apre script.fn_ensure_logconn); la stringa di connessione e'' il ripiego. Pubblica la GUC solo per un id registrato, con scope di transazione. Canale spento, non configurato o irraggiungibile: sentinella uuid_nil con un WARNING, nessuna GUC pubblicata, mai un errore. SECURITY DEFINER di postgres con search_path pg_catalog, public, pg_temp: public serve perche'' dblink vive li''; il pin sta nella definizione, un CREATE OR REPLACE che lo dimentica lo azzera.';
```

</div>

---
{% include-markdown "signature-core.md" %}
