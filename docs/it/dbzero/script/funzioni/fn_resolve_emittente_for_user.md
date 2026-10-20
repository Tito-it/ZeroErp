{% include-markdown "it/dbzero/script/manual/fn_resolve_emittente_for_user.md" %}
# ⚙️ Funzione `fn_resolve_emittente_for_user`

```sql
CREATE FUNCTION fn_resolve_emittente_for_user(p_auth_user_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_emittente_for_user(p_auth_user_id integer)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE;
    v_attivo               anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- Guard input: p_auth_user_id obbligatorio e > 0
    IF p_auth_user_id IS NULL OR p_auth_user_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script',
            'fn_resolve_emittente_for_user',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'p_auth_user_id obbligatorio e > 0',
                'auth_user_id', p_auth_user_id
            ),
            NULL::uuid,
            'p_auth_user_id obbligatorio e > 0'
        );
    END IF;

    -- =========================================================
    -- Regola unica (rev 2026-08-04):
    --   emittente attivo se valido per l'utente,
    --   altrimenti la riga di configurazione.
    -- Il super admin passa dal primo ramo, l'operatore dal
    -- secondo. Il controllo di validita' passa dalla canonica:
    -- cosi' l'invariante "solo restringente, mai allargante" e'
    -- vera per costruzione e non per convenzione sul fatto che
    -- il BE non setti la GUC agli operatori.
    -- =========================================================
    v_attivo := NULLIF(
                    current_setting('app.current_emittente_id', true),
                    ''
                )::bigint;

    IF v_attivo IS NOT NULL
       AND script.fn_check_user_emittente_scope(p_auth_user_id, v_attivo) THEN
        RETURN v_attivo;
    END IF;

    -- Modello 1-a-1: dopo la migration UNIQUE(auth_user_id)
    -- esiste al massimo una riga per utente. LIMIT 1 difensivo.
    -- NB: nessun filtro su ef.attivo perche' per costruzione
    -- l'EF associato a un utente e' sempre attivo:
    --   - dbops.trgfn_child_requires_active_parent su
    --     user_emittenti_fiscali blocca INSERT/UPDATE su EF non attivo
    --   - dbops.trgfn_prevent_deactivate_if_children su
    --     emittenti_fiscali blocca la disattivazione di un EF
    --     con righe figlie in user_emittenti_fiscali
    -- Aggiungere il filtro qui creerebbe incoerenza con
    -- script.fn_check_user_can_create_ba (che non filtra).
    SELECT uef.emittente_fiscale_id
      INTO v_emittente_fiscale_id
      FROM config.user_emittenti_fiscali uef
     WHERE uef.auth_user_id = p_auth_user_id
     LIMIT 1;

    RETURN v_emittente_fiscale_id;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_emittente_for_user(p_auth_user_id integer)
IS 'Resolver utente->emittente di lavoro. Regola (rev 2026-08-04): emittente attivo (GUC app.current_emittente_id) se valido per l''utente secondo fn_check_user_emittente_scope, altrimenti la riga 1-a-1 di config.user_emittenti_fiscali. Ritorna anagrafiche.emittenti_fiscali.id (PK reale) o NULL se l''utente non ha ne'' emittente attivo ne'' riga (admin globale in modalita'' "tutti gli emittenti"). Nessun filtro su ef.attivo: per costruzione l''EF associato a un utente e'' sempre attivo (trigger di guardia su entrambi i lati). NON solleva errore in caso di NULL: il chiamante decide la semantica (i trigger di default emittente sollevano *_EMITTENTE_NON_RISOLTO).';
```

</div>

---
{% include-markdown "signature-core.md" %}
