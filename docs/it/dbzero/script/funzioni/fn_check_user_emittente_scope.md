{% include-markdown "it/dbzero/script/manual/fn_check_user_emittente_scope.md" %}
# ⚙️ Funzione `fn_check_user_emittente_scope`

```sql
CREATE FUNCTION fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION script.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
 RETURNS boolean
 LANGUAGE plpgsql
 STABLE COST 5000
AS $function$
DECLARE
    v_cnt    integer;
    v_attivo bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Verifica se un utente ha accesso a uno specifico
    --   emittente fiscale. Sede unica read+write: la usano gli
    --   adapter RLS e i trigger di guardia.
    --
    -- Regole (refactor §4.6.B.5, + emittente attivo 2026-08-04,
    --         + P-2a 2026-08-18):
    --   1. p_auth_user_id NULL -> FALSE  ⬅ cambiato il 2026-10-04 (Q-1)
    --   2. Emittente attivo diverso da quello richiesto -> false
    --      (restringe CHIUNQUE, anche il super admin)
    --   3. fn_is_super_admin -> true (vede tutto)
    --   4. Assenza identita OPERATORE attiva -> false
    --      (defensive: utente disabilitato non accede)
    --   5. Whitelist vuota -> FALSE  ⬅ cambiato da P-2a
    --   6. Whitelist popolata -> EXISTS match
    -- =========================================================

    -- 1. Nessun utente -> nessun accesso.
    --    ⚠️ Rev 2026-10-04 (Q-1, brief-db-esclusioni-implicite): era
    --    `RETURN true` («job batch»). Le policy restavano chiuse solo
    --    perche' chiedono ANCHE la veste OPERATORE: una sessione con la
    --    veste impostata e l'utente vuoto vedeva TUTTE le aziende. Il
    --    guard di scrittura (trgfn_guard_emittente_scope) aveva gia'
    --    tolto lo stesso ramo il 2026-09-04: senza utente passa solo chi
    --    bypassa comunque la RLS (row_security_active), e quella
    --    decisione la prende lui, prima di chiamare qui. Un processo
    --    legittimo dice chi e' (brief processi automatici).
    IF p_auth_user_id IS NULL THEN
        RETURN false;
    END IF;

    -- 2. Emittente attivo (impersonazione di scope).
    --    Deve precedere il ramo super admin: e' l'unico punto in
    --    cui la selezione puo' restringere chi vede tutto.
    --    IS DISTINCT FROM: con p_emittente_fiscale_id NULL
    --    (riferimento non risolto dagli adapter) resta fail-closed.
    v_attivo := NULLIF(
                    current_setting('app.current_emittente_id', true),
                    ''
                )::bigint;

    IF v_attivo IS NOT NULL
       AND p_emittente_fiscale_id IS DISTINCT FROM v_attivo THEN
        RETURN false;
    END IF;

    -- 3. Super admin? Bypass totale.
    --    ⭐ L'unico attore legittimamente multi-emittente
    --       (decisione Tid 2026-08-17). Non toccato da P-2a.
    IF script.fn_is_super_admin(p_auth_user_id) THEN
        RETURN true;
    END IF;

    -- 4. Identita OPERATORE attiva (helper DRY §4.6.B.0).
    IF NOT script.fn_has_identita_attiva(
               p_auth_user_id,
               'OPERATORE'::config.ruolo_applicativo) THEN
        RETURN false;
    END IF;

    -- 5. Conta righe whitelist
    SELECT count(*)
      INTO v_cnt
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id;

    -- ⚠️ Rev 2026-08-18 (P-2a): era `RETURN true` con il commento
    --   «nessuna restrizione». Un operatore senza riga aveva cosi'
    --   accesso a QUALUNQUE emittente — mentre lo stesso utente,
    --   sul lato scrittura, non poteva nemmeno creare un billing
    --   account (fn_check_user_can_create_ba). Le due letture non
    --   potevano essere entrambe intenzionali: la riga mancante e'
    --   un errore di configurazione, non un permesso.
    --   Brief perimetro-emittente §2.5.
    IF v_cnt = 0 THEN
        RETURN false;  -- nessun accesso: la riga manca
    END IF;

    -- 6. Verifica match specifico
    RETURN EXISTS (
        SELECT 1
          FROM config.user_emittenti_fiscali uef
         WHERE uef.auth_user_id         = p_auth_user_id
           AND uef.emittente_fiscale_id = p_emittente_fiscale_id
    );
END
$function$

COMMENT ON FUNCTION script.fn_check_user_emittente_scope(p_auth_user_id integer, p_emittente_fiscale_id bigint)
IS 'Verifica accesso utente a emittente fiscale. Sede unica read+write: la usano gli adapter RLS (fn_scope_ef_whitelist e famiglia), i verbi DEFINER che ricopiano il filtro e i trigger di guardia. Regole, in ordine: utente NULL -> false (rev 2026-10-04, Q-1: era true, «job batch»; con la veste OPERATORE e l''utente vuoto una sessione vedeva tutte le aziende. Il guard di scrittura aveva tolto lo stesso ramo il 2026-09-04 e decide da se'' il caso senza utente con row_security_active); emittente attivo (GUC app.current_emittente_id) diverso da quello richiesto -> false, PRIMA del bypass super admin (impersonazione di scope: solo restringente, mai allargante, rev 2026-08-04); super admin -> true; identita'' OPERATORE mancante -> false; whitelist vuota -> false (P-2a, 2026-08-18: la riga mancante e'' un errore di configurazione, non un permesso); altrimenti match EXISTS. Brief perimetro-emittente §2.5, brief-db-esclusioni-implicite Q-1.';
```

---
{% include-markdown "signature-core.md" %}
