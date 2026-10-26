{% include-markdown "it/dbzero/script/manual/fn_check_blocco_login.md" %}
# ⚙️ Funzione `fn_check_blocco_login`

```sql
CREATE FUNCTION fn_check_blocco_login(p_auth_user_id integer, p_nome_digest bytea, p_provenienza inet)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_blocco_login(p_auth_user_id integer, p_nome_digest bytea, p_provenienza inet)
 RETURNS void
 LANGUAGE plpgsql
 SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'public', 'pg_temp'
AS $function$
-- Scopo: prima della verifica della password, dire se questo nome puo'
--   provare da questa provenienza. La chiave e' la credenziale se il
--   nome la trova, il nome tentato se no; poi, uguale per le due: blocco
--   dell'admin (solo credenziale), freno sulla coppia, attesa crescente.
DECLARE
    -- Esplicito: e' config.credenziali.id OPPURE config.nomi_tentati.id,
    -- secondo la chiave (entrambi bigint), non una colonna sola.
    v_chiave_id         bigint;
    v_bloccata_at       config.credenziali.bloccata_at%TYPE;
    v_fallimenti        config.credenziali.fallimenti_consecutivi%TYPE;
    v_ultimo_fallimento config.credenziali.ultimo_fallimento_at%TYPE;
    v_bloccato_fino_a   config.credenziali_provenienze.bloccato_fino_a%TYPE;
    -- Espliciti: parametri da script.fn_login_parametri (testo in
    -- config.parameters) e valori calcolati, senza colonna.
    v_tetto             integer;
    v_attesa_base       integer;
    v_attesa_max        integer;
    v_attesa            integer;
    v_riprova_da        timestamptz;
    v_rimanenti         integer;
BEGIN
    IF p_auth_user_id <= 0 OR p_provenienza IS NULL
       OR p_nome_digest IS NULL OR octet_length(p_nome_digest) <> 32 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_blocco_login', 'E_AUTH_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_auth_user_id',        p_auth_user_id,
                               'p_provenienza',         p_provenienza::text,
                               'nome_digest_lunghezza', octet_length(p_nome_digest)),
            NULL::uuid,
            VARIADIC ARRAY['script.fn_check_blocco_login',
                           'provenienza e digest del nome (32 byte) obbligatori, credenziale positiva se data']);
    END IF;

    -- La chiave, e il suo freno sulla coppia.
    IF p_auth_user_id IS NOT NULL THEN
        SELECT c.id, c.bloccata_at, c.fallimenti_consecutivi, c.ultimo_fallimento_at
          INTO v_chiave_id, v_bloccata_at, v_fallimenti, v_ultimo_fallimento
          FROM config.credenziali c
         WHERE c.auth_user_id = p_auth_user_id;

        SELECT p.bloccato_fino_a
          INTO v_bloccato_fino_a
          FROM config.credenziali_provenienze p
         WHERE p.credenziale_id = v_chiave_id
           AND p.provenienza    = p_provenienza;
    ELSE
        SELECT nt.id, nt.fallimenti_consecutivi, nt.ultimo_fallimento_at
          INTO v_chiave_id, v_fallimenti, v_ultimo_fallimento
          FROM config.nomi_tentati nt
         WHERE nt.nome_digest = p_nome_digest;

        SELECT p.bloccato_fino_a
          INTO v_bloccato_fino_a
          FROM config.nomi_tentati_provenienze p
         WHERE p.nome_tentato_id = v_chiave_id
           AND p.provenienza     = p_provenienza;
    END IF;

    -- Nessuna riga: nessun tentativo, non frenata.
    IF v_chiave_id IS NULL THEN
        RETURN;
    END IF;

    -- 1. Blocco dell'admin: non scade. Esiste solo sulla credenziale.
    IF v_bloccata_at IS NOT NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'script.fn_check_blocco_login', 'E_CREDENZIALE_BLOCCATA',
            jsonb_build_object('auth_user_id', p_auth_user_id,
                               'bloccata_at',  v_bloccata_at),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Freno sulla coppia chiave + provenienza.
    IF v_bloccato_fino_a IS NOT NULL THEN
        IF v_bloccato_fino_a <= now() THEN
            -- Freno scaduto: la coppia riparte da zero.
            IF p_auth_user_id IS NOT NULL THEN
                DELETE FROM config.credenziali_provenienze p
                 WHERE p.credenziale_id = v_chiave_id
                   AND p.provenienza    = p_provenienza;
            ELSE
                DELETE FROM config.nomi_tentati_provenienze p
                 WHERE p.nome_tentato_id = v_chiave_id
                   AND p.provenienza     = p_provenienza;
            END IF;
        ELSE
            -- I minuti vanno nel messaggio (a chi prova) e nel contesto (al log).
            -- Il contesto (auth_user_id NULL per un nome inesistente) va al
            --   log degli errori, non alla risposta: l'envelope porta codice,
            --   messaggio e causa, uguali per le due chiavi.
            v_rimanenti := GREATEST(1,
                CEIL(EXTRACT(EPOCH FROM (v_bloccato_fino_a - now())) / 60)::integer);
            PERFORM script.fn_log_and_raise_error(
                'database', 'script.fn_check_blocco_login', 'E_UTENTE_BLOCCATO',
                jsonb_build_object('auth_user_id',     p_auth_user_id,
                                   'provenienza',      p_provenienza::text,
                                   'bloccato_fino_a',  v_bloccato_fino_a,
                                   'minuti_rimanenti', v_rimanenti),
                NULL::uuid,
                VARIADIC ARRAY[v_rimanenti::text]);
        END IF;
    END IF;

    -- 3. Attesa crescente sulla chiave (da qualunque provenienza).
    IF v_fallimenti > 0 THEN
        SELECT lp.tetto_credenziale, lp.attesa_base_secondi, lp.attesa_max_secondi
          INTO v_tetto, v_attesa_base, v_attesa_max
          FROM script.fn_login_parametri() lp;

        v_attesa := script.fn_login_attesa_secondi(
            v_fallimenti, v_tetto, v_attesa_base, v_attesa_max);

        IF v_attesa > 0 THEN
            v_riprova_da := v_ultimo_fallimento + make_interval(secs => v_attesa);
            IF v_riprova_da > now() THEN
                v_rimanenti := GREATEST(1,
                    CEIL(EXTRACT(EPOCH FROM (v_riprova_da - now())))::integer);
                PERFORM script.fn_log_and_raise_error(
                    'database', 'script.fn_check_blocco_login', 'E_LOGIN_ATTESA',
                    jsonb_build_object('auth_user_id',      p_auth_user_id,
                                       'fallimenti',        v_fallimenti,
                                       'attesa_secondi',    v_attesa,
                                       'secondi_rimanenti', v_rimanenti),
                    NULL::uuid,
                    VARIADIC ARRAY[v_rimanenti::text]);
            END IF;
        END IF;
    END IF;
END;
$function$

COMMENT ON FUNCTION script.fn_check_blocco_login(p_auth_user_id integer, p_nome_digest bytea, p_provenienza inet)
IS 'Check del login, PRIMA della verifica della password, per NOME TENTATO e PROVENIENZA (R-7). La chiave e'' la credenziale quando p_auth_user_id e'' valorizzato, il nome tentato (config.nomi_tentati, per digest) quando e'' NULL: stessa decisione e stessi codici per le due, cosi'' la risposta non dice se il nome esiste. Nell''ordine, il primo che scatta vince: (1) blocco dell''admin -> E_CREDENZIALE_BLOCCATA, non scade, solo sulla credenziale (rivela l''esistenza del nome: accettato, §13.5 (b)); (2) freno sulla coppia chiave + provenienza -> E_UTENTE_BLOCCATO con i minuti rimanenti nel messaggio e nel contesto, e un freno scaduto fa ripartire la coppia (riga cancellata); (3) attesa crescente sulla chiave (fn_login_attesa_secondi) -> E_LOGIN_ATTESA con i secondi rimanenti. Nessuna riga = passa. Provenienza NULL, digest NULL o non di 32 byte, credenziale <= 0 -> E_AUTH_CHIAMATA_NON_VALIDA. Il digest lo calcola il backend (HMAC del nome normalizzato): il nome non entra mai. SECURITY DEFINER del PROPRIETARIO, search_path bloccato; nessun guard di permesso, dichiarato (gira prima del login). Brief: brief-db-blocco-login-per-credenziale §2.4, §3.1, §12.8, §13.';
```

</div>

---
{% include-markdown "signature-core.md" %}
