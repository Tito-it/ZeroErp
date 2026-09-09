# ⚙️ Funzione `fn_pgtap_crea_emittente`

```sql
CREATE FUNCTION fn_pgtap_crea_emittente(p_sigla character varying)
```

**Definizione completa:**

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_emittente(p_sigla character varying DEFAULT NULL::character varying)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, soggetto_ruolo_id bigint, soggetto_id uuid)
 LANGUAGE plpgsql
AS $function$
-- Scopo: creare per una fixture pgTAP un emittente fiscale nuovo,
--   completo del soggetto persona giuridica e del ruolo EF.
-- Uso:
--   CREATE TEMP TABLE tmp_ef AS
--   SELECT * FROM dbops.fn_pgtap_crea_emittente();
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_sr_id       anagrafiche.soggetti_ruoli.id%TYPE;
    v_codice      anagrafiche.emittenti_fiscali.codice%TYPE;
    v_ef_id       anagrafiche.emittenti_fiscali.id%TYPE;
    v_try         integer := 0;
    v_libera      boolean := FALSE;
BEGIN
    -- La sigla: se non la impone il chiamante se ne cerca una
    -- LIBERA. ⚠️ `uq:codice` e' UNIQUE senza filtro su `attivo`,
    -- quindi una sigla fissa farebbe collidere la seconda corsa
    -- con il residuo della prima — lo stesso difetto per cui
    -- esiste dbops.fn_pgtap_piva_libera.
    -- ⚠️ La forma la impone chk_emittenti_fiscali_codice_forma:
    -- solo maiuscole e cifre, da 2 a 10 caratteri.
    IF p_sigla IS NOT NULL THEN
        v_codice := p_sigla;
    ELSE
        LOOP
            v_try := v_try + 1;
            EXIT WHEN v_try > 9999;
            v_codice := 'PGTR' || lpad(v_try::text, 4, '0');
            IF NOT EXISTS (SELECT 1
                             FROM anagrafiche.emittenti_fiscali e
                            WHERE e.codice = v_codice) THEN
                v_libera := TRUE;
                EXIT;
            END IF;
        END LOOP;

        IF NOT v_libera THEN
            RAISE EXCEPTION
                'fn_pgtap_crea_emittente: nessuna sigla PGTRnnnn libera';
        END IF;
    END IF;

    -- I due helper aprono e richiudono da soli la finestra dei
    -- guard differiti, quindi qui non serve toccarla.
    v_soggetto_id := dbops.fn_pgtap_crea_soggetto_pg(
                         'Emittente pgTAP ' || v_codice);
    v_sr_id       := dbops.fn_pgtap_crea_soggetto_ruolo(
                         v_soggetto_id, 'EF'::character varying);

    -- ⭐ Nascendo, l'emittente fa nascere anche i suoi registri di
    --   numerazione (vendite.fn_provision_registri_emittente): e'
    --   il percorso reale, e un test che ne avesse bisogno li
    --   trova gia' pronti.
    INSERT INTO anagrafiche.emittenti_fiscali (soggetto_ruolo_id, codice)
    VALUES (v_sr_id, v_codice)
    RETURNING id INTO v_ef_id;

    RETURN QUERY SELECT v_ef_id, v_codice, v_sr_id, v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_emittente(p_sigla character varying)
IS 'Helper di fixture pgTAP: crea un emittente fiscale nuovo — soggetto persona giuridica, ruolo EF, riga in anagrafiche.emittenti_fiscali con una sigla PGTRnnnn libera. Ritorna emittente_fiscale_id, emittente_codice, soggetto_ruolo_id, soggetto_id. ⚠️ Da sola NON basta a far vedere l''emittente a un test: il contesto operatore sceglie un utente che abbia gia'' un emittente in config.user_emittenti_fiscali, e su un database ricostruito non ce n''e'' nessuno — per quello serve dbops.fn_pgtap_crea_emittente_operatore. ⭐ Nascendo, l''emittente fa nascere i propri registri di numerazione (vendite.fn_provision_registri_emittente).';
```

---
{% include-markdown "signature-core.md" %}
