{% include-markdown "it/dbzero/script/manual/fn_get_emittenti_scope_pk_ids.md" %}
# ⚙️ Funzione `fn_get_emittenti_scope_pk_ids`

```sql
CREATE FUNCTION fn_get_emittenti_scope_pk_ids(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_get_emittenti_scope_pk_ids(p_auth_user_id integer)
 RETURNS bigint[]
 LANGUAGE plpgsql
 STABLE COST 5000
AS $function$
DECLARE
    -- ⚠️ `bigint[]` esplicito: `colonna%TYPE[]` non esiste in PostgreSQL.
    v_ids    bigint[];
    v_attivo anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Scope emittenti per i filtri su colonne PK.
    --   Semantica: NULL = tutto, '{}' = nessuno, array = whitelist.
    --
    -- Struttura (rev 2026-08-04): USCITA UNICA. Prima si calcola
    -- lo scope "di diritto" (super admin / whitelist), poi lo si
    -- interseca con l'emittente attivo in un solo punto. I RETURN
    -- anticipati di prima rendevano impossibile intersecare il
    -- ramo super admin, che e' proprio quello da restringere.
    --
    -- Rev 2026-08-18 (P-2a): l'operatore SENZA riga non vede piu'
    -- tutto. Vedi il ramo OPERATIVO.
    -- =========================================================

    v_attivo := NULLIF(
                    current_setting('app.current_emittente_id', true),
                    ''
                )::bigint;

    -- 1. Scope di diritto: super admin, oppure veste OPERATORE
    --    utilizzabile + whitelist.
    --    ⭐ Rev 2026-10-18 (D-3b-2, 20261018-22): il super admin
    --    si chiede PRIMA della veste. L'esito non cambia — il
    --    super admin richiede gia' una veste OPERATORE
    --    utilizzabile (fn_is_super_admin_account) — ma la veste
    --    si verifica una volta sola invece di due. Ora che la
    --    canonica fn_check_user_emittente_scope chiede qui, e la
    --    chiamano per riga adattatori e guard, la verifica in
    --    piu' raddoppiava il costo di ogni chiamata (misura nel
    --    brief-db-plancache-funzioni-con-query-incorporate).
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        -- Nessuna restrizione: NULL = universo.
        -- ⭐ E' l'UNICO attore legittimamente multi-emittente
        --    (decisione Tid 2026-08-17). Non toccato da P-2a.
        v_ids := NULL;
    ELSIF NOT script.fn_has_identita_attiva(
                  p_auth_user_id,
                  'OPERATORE'::config.ruolo_applicativo) THEN
        -- Nessuna veste OPERATORE utilizzabile (helper DRY
        -- §4.6.B.0). '{}' e' gia' il valore piu' restrittivo:
        -- nessuna intersezione potrebbe cambiarlo, esce subito.
        RETURN '{}'::bigint[];
    ELSE
        -- OPERATIVO: whitelist PK reale. Lettura diretta da
        -- user_emittenti_fiscali (la colonna e' gia' la PK).
        --
        -- ⚠️ Rev 2026-08-18 (P-2a): `coalesce(..., '{}')`.
        --   PRIMA: array_agg su zero righe torna NULL, e NULL in
        --   questa convenzione significa «nessuna restrizione» —
        --   quindi un operatore senza riga vedeva TUTTI gli
        --   emittenti, ed era indistinguibile da un super admin.
        --   Non era uno stato del modello: era un errore di
        --   configurazione che il sistema non rilevava.
        --   ORA: '{}' = nessun accesso. La riga mancante e' un
        --   difetto che si annuncia, invece di aprire in silenzio.
        --   Stessa identica correzione fatta il 2026-08-04 su
        --   fn_get_emittenti_scope_sr_ids, nello stesso punto
        --   logico: qui era rimasta indietro (brief §2.5).
        SELECT coalesce(array_agg(uef.emittente_fiscale_id), '{}'::bigint[])
          INTO v_ids
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id = p_auth_user_id;
    END IF;

    -- 3. Intersezione con l'emittente attivo (uscita unica).
    IF v_attivo IS NULL THEN
        RETURN v_ids;                      -- nessuna impersonazione
    END IF;

    IF v_ids IS NULL THEN
        RETURN ARRAY[v_attivo];            -- universo ∩ {X} = {X}
    END IF;

    IF v_attivo = ANY(v_ids) THEN
        RETURN ARRAY[v_attivo];            -- {A,B} ∩ {X}, X presente
    END IF;

    RETURN '{}'::bigint[];                 -- X fuori scope: nessuno
END
$function$

COMMENT ON FUNCTION script.fn_get_emittenti_scope_pk_ids(p_auth_user_id integer)
IS '⭐ rev 2026-10-18 (20261018-17, D-3b-2): COST 5000. E'' la sede delle regole del perimetro (la canonica fn_check_user_emittente_scope si appoggia a lei) e le policy ef_whitelist dirette la chiamano una volta per istruzione. Scope emittenti per filtri su colonne PK (emittenti_fiscali.id). Semantica: NULL=tutto, ''{}''=nessuno, array=whitelist. Identita OPERATORE mancante -> []; SUPER_ADMIN -> NULL; altrimenti whitelist PK. Post 2026-08-04: uscita unica e intersezione con la GUC app.current_emittente_id (universo ∩ {X} = {X}; whitelist senza X -> []). Post 2026-08-18 (P-2a): operatore non super admin SENZA riga in config.user_emittenti_fiscali -> ''{}'' e non piu'' NULL. Prima vedeva TUTTI gli emittenti ed era indistinguibile da un super admin: non uno stato del modello, un errore di configurazione non rilevato. Allinea la lettura alla scrittura, che gia'' rispondeva false (fn_check_user_can_create_ba). Gemella di fn_get_emittenti_scope_sr_ids (che e'' un wrapper su questa e aveva gia'' ricevuto la correzione). Vedi guida soggetti-e-ruoli §5b e brief perimetro-emittente §2.5.';
```

</div>

---
{% include-markdown "signature-core.md" %}
