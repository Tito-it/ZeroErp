# ⚙️ Funzione `fn_pgtap_crea_emittente`

```sql
CREATE FUNCTION fn_pgtap_crea_emittente(p_sigla character varying)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_emittente(p_sigla character varying DEFAULT NULL::character varying)
 RETURNS TABLE(emittente_fiscale_id bigint, emittente_codice character varying, soggetto_ruolo_id bigint, soggetto_id uuid)
 LANGUAGE plpgsql
AS $function$
-- Scopo: creare per una fixture pgTAP un emittente fiscale nuovo,
--   completo del soggetto persona giuridica, del ruolo EF e della
--   valuta.
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_sr_id       anagrafiche.soggetti_ruoli.id%TYPE;
    v_codice      anagrafiche.emittenti_fiscali.codice%TYPE;
    v_ef_id       anagrafiche.emittenti_fiscali.id%TYPE;
    v_try         integer := 0;
    v_libera      boolean := FALSE;
BEGIN
    -- Sigla LIBERA: `uq:codice` e' UNIQUE senza filtro su
    -- `attivo`, quindi una sigla fissa farebbe collidere la
    -- seconda corsa col residuo della prima.
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

    v_soggetto_id := dbops.fn_pgtap_crea_soggetto_pg(
                         'Emittente pgTAP ' || v_codice);
    v_sr_id       := dbops.fn_pgtap_crea_soggetto_ruolo(
                         v_soggetto_id, 'EF'::character varying);

    -- ⚠️ `valuta_id` VALORIZZATA (rev 20260909-32).
    --   `vendite.fn_get_valuta_id` risolve «BA -> EMITTENTE ->
    --   gestore». Su dbdev regge l'ultimo anello; da zero non ne
    --   regge nessuno, e il primo documento muore su
    --   E_CONFIG_MANCANTE.
    --   ⛔ Il primo anello non basta: quando il resolver gira
    --   dentro un trigger sull'INSERT del billing account, la
    --   riga del BA non e' ancora visibile.
    -- ⭐ Rev 2026-10-17: la riga la scrive il verbo di dominio
    --   anagrafiche.fn_crea_emittente_fiscale, come l'applicazione
    --   (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1).
    --   Il ruolo esiste gia' (sopra, con i suoi indirizzi): il verbo lo
    --   ritrova. Nascendo, l'emittente fa nascere anche i propri registri
    --   di numerazione (vendite.fn_provision_registri_emittente).
    SELECT e.emittente_fiscale_id
      INTO v_ef_id
      FROM anagrafiche.fn_crea_emittente_fiscale(
               v_soggetto_id, v_codice,
               jsonb_build_object('valuta_id',
                   (SELECT v.id FROM config.valute v ORDER BY v.id LIMIT 1))) AS e;

    RETURN QUERY SELECT v_ef_id, v_codice, v_sr_id, v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_emittente(p_sigla character varying)
IS 'Helper di fixture pgTAP: crea un emittente fiscale nuovo — soggetto persona giuridica, ruolo EF, riga in anagrafiche.emittenti_fiscali con una sigla PGTRnnnn libera e la VALUTA valorizzata. ⚠️ La valuta non e'' un di piu'': vendite.fn_get_valuta_id risolve «BA -> emittente -> gestore», e su un database ricostruito dai changelog nessuno dei tre e'' valorizzato — il primo documento morirebbe su E_CONFIG_MANCANTE. Da sola NON basta a far vedere l''emittente a un test: per quello serve dbops.fn_pgtap_crea_emittente_operatore. Rev 20260909-32. Rev 2026-10-17: la riga di emittenti_fiscali la scrive il verbo anagrafiche.fn_crea_emittente_fiscale (regola del 2, brief-db-processi-accensione-per-ambiente 2b-1); firma e ritorno invariati.';
```

</div>

---
{% include-markdown "signature-core.md" %}
