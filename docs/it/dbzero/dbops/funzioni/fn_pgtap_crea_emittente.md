{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_emittente.md" %}
# ⚙️ Funzione `fn_pgtap_crea_emittente`

```sql
CREATE FUNCTION fn_pgtap_crea_emittente(p_sigla character varying)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

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
                   dbops.fn_pgtap_valuta())) AS e;

    -- ⭐ Rev 2026-11-27 (brief-db-utility-gestite-dall-emittente
    --   D-U-2, D-U-12): un'azienda tratta solo le utility che
    --   gestisce, e i billing account e i documenti lo verificano
    --   con una FK. L'azienda di prova gestisce ogni utility che la
    --   matrice ammette oggi per l'emittente fiscale, senza
    --   parametri: e' un'azienda completa, come quella che il
    --   SUPER_ADMIN configura. Il test che vuole un'azienda senza
    --   un'utility cancella la riga (senza BA ne' documenti).
    INSERT INTO anagrafiche.emittenti_fiscali_utilities
           (emittente_soggetto_ruolo_id, utility_id)
    SELECT v_sr_id, m.utility_id
      FROM config.utilities_tipi_ruolo m
      JOIN config.tipi_ruoli t ON t.id = m.tipo_ruolo_id
     WHERE t.codice_interno = 'EF'
       AND m.attivo IS TRUE
       AND (m.valido_dal IS NULL OR m.valido_dal <= script.fn_data_operativa())
       AND m.valido_al IS NULL
    ON CONFLICT (emittente_soggetto_ruolo_id, utility_id) DO NOTHING;

    RETURN QUERY SELECT v_ef_id, v_codice, v_sr_id, v_soggetto_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_emittente(p_sigla character varying)
IS 'Helper di fixture pgTAP: crea un emittente fiscale nuovo — soggetto persona giuridica, ruolo EF, riga in anagrafiche.emittenti_fiscali con una sigla PGTRnnnn libera e la VALUTA valorizzata. ⚠️ La valuta non e'' un di piu'': vendite.fn_get_valuta_id risolve «BA -> emittente -> gestore», e su un database ricostruito dai changelog nessuno dei tre e'' valorizzato — il primo documento morirebbe su E_CONFIG_MANCANTE. L''azienda gestisce ogni utility che la matrice config.utilities_tipi_ruolo ammette oggi per l''emittente fiscale (una riga senza parametri in anagrafiche.emittenti_fiscali_utilities). Da sola NON basta a far vedere l''emittente a un test: per quello serve dbops.fn_pgtap_crea_emittente_operatore. La riga di emittenti_fiscali la scrive il verbo anagrafiche.fn_crea_emittente_fiscale; la valuta e'' quella di dbops.fn_pgtap_valuta.';
```

</div>

---
{% include-markdown "signature-core.md" %}
