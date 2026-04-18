{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_auth_user_guard_persona_fisica.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_auth_user_guard_persona_fisica`

```sql
CREATE FUNCTION trgfn_risorse_umane_auth_user_guard_persona_fisica()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    -- %TYPE per restare allineati alla colonna sorgente.
    v_soggetto_id anagrafiche.risorse_umane.soggetto_id%TYPE;
BEGIN
    -- ------------------------------------------------------------
    -- Trigger function: guard "persona fisica pura" su
    -- risorse_umane_auth_user (BEFORE INSERT/UPDATE).
    --
    -- Regole (delegate a script.fn_guard_soggetto_pf_pura):
    --   - Il soggetto collegato deve avere codice_fiscale
    --   - Il soggetto collegato NON deve avere partita_iva
    --
    -- Nota: l'appartenenza del soggetto a un emittente fiscale
    --   viene verificata al login lato Django (auth view), non qui.
    -- ------------------------------------------------------------

    -- 1) Risolvi il soggetto a partire dalla risorsa umana collegata
    --    dal bridge (NEW.risorsa_umana_id e' FK verso risorse_umane).
    SELECT ru.soggetto_id
      INTO v_soggetto_id
      FROM anagrafiche.risorse_umane ru
     WHERE ru.id = NEW.risorsa_umana_id;

    -- 2) Delega alla funzione riusabile (solleva eccezione se
    --    il soggetto non e' PF pura; altrimenti restituisce l'id).
    PERFORM script.fn_guard_soggetto_pf_pura(v_soggetto_id);

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_auth_user_guard_persona_fisica()
IS 'Guard su risorse_umane_auth_user: delega a script.fn_guard_soggetto_pf_pura la verifica che il soggetto collegato sia persona fisica pura (CF obbligatorio, P.IVA vietata). Il trigger associato resta invariato (a10_guard_persona_fisica_ins_upd).';
```

---
{% include-markdown "signature-core.md" %}
