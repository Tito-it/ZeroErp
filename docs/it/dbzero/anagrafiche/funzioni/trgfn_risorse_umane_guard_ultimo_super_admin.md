{% include-markdown "it/dbzero/anagrafiche/manual/trgfn_risorse_umane_guard_ultimo_super_admin.md" %}
# ⚙️ Funzione `trgfn_risorse_umane_guard_ultimo_super_admin`

```sql
CREATE FUNCTION trgfn_risorse_umane_guard_ultimo_super_admin()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_identita_id anagrafiche.identita_digitali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire le scritture sul rapporto di un SUPER_ADMIN
    --   che lascerebbero il sistema senza un SUPER_ADMIN SENZA
    --   SCADENZA (script.fn_check_almeno_un_super_admin_attivo).
    --
    -- Regole:
    --   1. Short-circuit: solo le scritture che RIDUCONO la
    --      garanzia (spegnere, data di fine, inizio nel futuro,
    --      spostamento su un altro soggetto_ruolo). Togliere una
    --      data di fine o riaprire il rapporto passa sempre.
    --   2. Short-circuit 2: solo se sul soggetto_ruolo di PRIMA
    --      c'e' una veste OPERATORE con un binding SUPER_ADMIN
    --      attivo.
    --   3. Verifica post-stato via fn_check; se false, raise.
    -- =========================================================

    IF NOT (   (OLD.attivo AND NOT NEW.attivo)
            OR (OLD.valido_al IS NULL AND NEW.valido_al IS NOT NULL)
            OR (OLD.valido_dal <= (SELECT script.fn_data_operativa()) AND NEW.valido_dal > (SELECT script.fn_data_operativa()))
            OR (OLD.soggetto_ruolo_id IS DISTINCT FROM NEW.soggetto_ruolo_id))
    THEN
        RETURN NULL;
    END IF;

    -- La veste SUPER_ADMIN appesa a questo rapporto (al piu' una
    -- accesa per soggetto_ruolo e tipo: uq_identita_digitali_sr_ruolo_attivo;
    -- ORDER BY per non dipendere dal piano quando ce ne sono di spente).
    SELECT idg.id
      INTO v_identita_id
      FROM anagrafiche.identita_digitali   idg
      JOIN config.profili_accesso_bindings pab
        ON pab.identita_digitale_id = idg.id
       AND pab.attivo
      JOIN config.profili_accesso          pa
        ON pa.id = pab.profilo_accesso_id
       AND pa.attivo
       AND pa.tipo = 'SUPER_ADMIN'::config.tipo_profilo_accesso
     WHERE idg.soggetto_ruolo_id = OLD.soggetto_ruolo_id
       AND idg.ruolo_applicativo = 'OPERATORE'::config.ruolo_applicativo
     ORDER BY idg.attivo DESC, idg.id
     LIMIT 1;

    IF v_identita_id IS NULL THEN
        RETURN NULL;
    END IF;

    IF NOT script.fn_check_almeno_un_super_admin_attivo() THEN
        PERFORM script.fn_log_and_raise_error(
            'anagrafiche',
            TG_NAME,
            'E_PROFILO_ULTIMO_SUPER_ADMIN',
            jsonb_build_object(
                'op', TG_OP,
                'risorsa_umana_id', OLD.id,
                'identita_digitale_id', v_identita_id,
                'attivo', NEW.attivo,
                'valido_dal', NEW.valido_dal,
                'valido_al', NEW.valido_al
            ),
            NULL::uuid,
            VARIADIC ARRAY[]::text[]
        );
    END IF;

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin()
IS 'Guard anti-lockout sul rapporto (AFTER UPDATE di attivo, valido_dal, valido_al, soggetto_ruolo_id su risorse_umane): rifiuta una scrittura che riduce la garanzia del rapporto di un SUPER_ADMIN (spegnerlo, dargli una data di fine, spostarne l''inizio nel futuro, spostarlo su un altro soggetto_ruolo) se dopo non resta nessun SUPER_ADMIN senza scadenza (script.fn_check_almeno_un_super_admin_attivo). Le scritture che migliorano non si fermano mai. Codice E_PROFILO_ULTIMO_SUPER_ADMIN. Gemello di trgfn_identita_digitali_guard_ultimo_super_admin. Nasce il 2026-10-07 (brief-db-veste-utilizzabile, decisione di Tid): con D-2 la fine del rapporto chiude l''accesso dell''operatore, e il calendario non scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
