{% include-markdown "it/dbzero/script/manual/fn_check_user_emittente_scope.md" %}
# ⚙️ Funzione `fn_check_user_emittente_scope`

```sql
CREATE FUNCTION fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE COST 5000
AS $function$
DECLARE
    -- ⚠️ `bigint[]` esplicito: `colonna%TYPE[]` non esiste in PostgreSQL.
    v_perimetro bigint[];
    v_attivo    anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica se un utente ha accesso a uno specifico
    --   emittente fiscale. Sede unica read+write: la usano gli
    --   adapter RLS, i verbi DEFINER e i trigger di guardia.
    --
    -- ⭐ Rev 2026-10-18 (D-3b-2, brief-db-plancache-funzioni-
    --   con-query-incorporate §5quinquies): le regole stanno in
    --   script.fn_get_emittenti_scope_pk_ids, che le scrive come
    --   INSIEME (gli emittenti visibili) ed e' gia' la sede del
    --   perimetro per il backend. Fino a oggi la stessa regola era
    --   scritta DUE volte, qui e li': ora una. Qui resta la domanda
    --   su UN emittente, fatta con la stessa funzione di scope delle
    --   policy (script.fn_scope_ef_perimetro), e le policy dirette
    --   calcolano il perimetro una volta per istruzione invece che
    --   una volta per riga.
    --
    -- Regole (ora in fn_get_emittenti_scope_pk_ids):
    --   1. p_auth_user_id NULL -> FALSE  (2026-10-04, Q-1)
    --   2. Emittente attivo diverso da quello richiesto -> false
    --      (restringe CHIUNQUE, anche il super admin)
    --   3. fn_is_super_admin -> true (vede tutto)
    --   4. Assenza identita OPERATORE utilizzabile -> false
    --   5. Whitelist vuota -> FALSE  (P-2a, 2026-08-18)
    --   6. Whitelist popolata -> l'emittente ci sta dentro
    --   ⚠️ La 4 la _pk_ids la guarda PRIMA della 3: l'esito non
    --   cambia, perche' il super admin richiede gia' una veste
    --   OPERATORE utilizzabile (fn_is_super_admin_account).
    --   Il perche' di 1 (Q-1) e di 5 (P-2a) e' nel COMMENT di
    --   questa funzione.
    -- =========================================================
    -- ⭐ Rev 2026-10-18 (20261018-23): con un emittente attivo di
    --    sessione il perimetro di fn_get_emittenti_scope_pk_ids e'
    --    al piu' {attivo}. Per un emittente diverso la risposta e'
    --    gia' false, e la si da' SENZA calcolare il perimetro: non
    --    e' una seconda regola, e' la conseguenza della prima, e
    --    script/test-fn-get-emittenti-scope-pk-ids-and-parity tiene
    --    allineate le due. Senza, ogni chiamata per riga (adattatori
    --    via_*, guard) pagava il perimetro intero anche per le righe
    --    che l'emittente attivo esclude: misura nel brief.
    --    IS DISTINCT FROM: emittente NULL -> false (fail-closed).
    v_attivo := NULLIF(current_setting('app.current_emittente_id', true), '')::bigint;
    IF v_attivo IS NOT NULL AND p_emittente_fiscale_id IS DISTINCT FROM v_attivo THEN
        RETURN false;
    END IF;

    v_perimetro := script.fn_get_emittenti_scope_pk_ids(p_auth_user_id);

    -- NULL = tutti. Emittente NULL (riferimento non risolto dagli
    -- adapter) -> false se il perimetro non e' «tutti».
    -- Rev 2026-10-18 (20261018-25, D-3b-2c): la firma a un argomento perimetro.
    RETURN script.fn_scope_ef_perimetro(v_perimetro, p_emittente_fiscale_id);
END
$function$

COMMENT ON FUNCTION script.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS '⭐ rev 2026-10-18 (20261018-18, D-3b-2): le regole stanno in una sede sola, script.fn_get_emittenti_scope_pk_ids (il perimetro come insieme); qui la domanda su un emittente la fa script.fn_scope_ef_perimetro, la stessa funzione delle policy. Stesse risposte. Verifica accesso utente a emittente fiscale. Sede unica read+write: la usano gli adapter RLS (fn_scope_ef_whitelist e famiglia), i verbi DEFINER che ricopiano il filtro e i trigger di guardia. Regole, in ordine: utente NULL -> false (rev 2026-10-04, Q-1: era true, «job batch»; con la veste OPERATORE e l''utente vuoto una sessione vedeva tutte le aziende. Il guard di scrittura aveva tolto lo stesso ramo il 2026-09-04 e decide da se'' il caso senza utente con row_security_active); emittente attivo (GUC app.current_emittente_id) diverso da quello richiesto -> false, PRIMA del bypass super admin (impersonazione di scope: solo restringente, mai allargante, rev 2026-08-04); super admin -> true; identita'' OPERATORE mancante -> false; whitelist vuota -> false (P-2a, 2026-08-18: la riga mancante e'' un errore di configurazione, non un permesso); altrimenti match EXISTS. Brief perimetro-emittente §2.5, brief-db-esclusioni-implicite Q-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
