{% include-markdown "it/dbzero/config/manual/fn_profilo_super_admin_id.md" %}
# ⚙️ Funzione `fn_profilo_super_admin_id`

```sql
CREATE FUNCTION fn_profilo_super_admin_id()
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION config.fn_profilo_super_admin_id()
 RETURNS integer
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_profilo_id config.profili_accesso.id%TYPE;
    v_n          integer;  -- un conteggio: nessuna colonna di cui sia il riflesso
BEGIN
    -- =========================================================
    -- Scopo:
    --   L'id dell'UNICO profilo di accesso attivo di tipo
    --   SUPER_ADMIN: quello che si lega a un operatore super
    --   admin.
    --
    -- Regole:
    --   - la chiave e' il TIPO (enum), non il codice ne' l'id
    --     del seed;
    --   - solo i profili attivi: uno spento non si lega;
    --   - esattamente uno, altrimenti E_CONFIG_MANCANTE: due
    --     profili non si scelgono per id.
    -- =========================================================
    SELECT count(*), min(pa.id)
      INTO v_n, v_profilo_id
      FROM config.profili_accesso pa
     WHERE pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
       AND pa.attivo;

    IF v_n <> 1 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'config.fn_profilo_super_admin_id',
            'E_CONFIG_MANCANTE',
            jsonb_build_object('tipo_profilo_accesso', 'SUPER_ADMIN',
                               'profili_attivi', v_n),
            NULL::uuid,
            'un solo profilo di accesso SUPER_ADMIN attivo (trovati '
                || v_n::text || ')');
    END IF;

    RETURN v_profilo_id;
END;
$function$

COMMENT ON FUNCTION config.fn_profilo_super_admin_id()
IS 'LETTORE (2026-10-18): l''id dell''UNICO profilo di accesso attivo di tipo SUPER_ADMIN, quello che si lega a un operatore super admin; E_CONFIG_MANCANTE (con il numero dei profili attivi trovati) se non ce n''e'' esattamente uno. La chiave e'' il TIPO (enum config.tipo_profilo_accesso, la stessa dei guard anti-lockout e di script.fn_is_super_admin), non il codice (modificabile, senza lock) ne'' l''id del seed. Il modello non vieta due profili di quel tipo: sceglierne uno per id sarebbe un''ambiguita''; un profilo spento non si lega. ⭐ Sede unica (regola del 2): la regola era scritta in anagrafiche.fn_crea_risorsa_umana_v2 e nel backend (AmmSoftwareRepository._set_super_admin_binding). Lettori: anagrafiche.fn_crea_risorsa_umana_v2 (20261019-17), il backend. R-BE-11 (ok Tid 2026-10-18), brief-db-processi-accensione-per-ambiente §6.15.';
```

---
{% include-markdown "signature-core.md" %}
