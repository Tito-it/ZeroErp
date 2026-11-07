{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_cliente_ba.md" %}
# ⚙️ Funzione `fn_pgtap_crea_cliente_ba`

```sql
CREATE FUNCTION fn_pgtap_crea_cliente_ba(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_cliente_ba(p_etichetta text DEFAULT 'pgTAP'::text, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(billing_account_id bigint, istanza_utility_id bigint, soggetto_ruolo_id bigint, soggetto_id uuid, utility_id integer)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un cliente FATTURABILE, cioe'
--   la catena minima che i documenti pretendono: soggetto ->
--   ruolo CL -> istanza utility -> billing account.
-- Uso:
--   CREATE TEMP TABLE tmp_cli AS
--   SELECT * FROM dbops.fn_pgtap_crea_cliente_ba('RLS preventivi');
-- ⭐ Terzo parametro: l'emittente a cui LEGARE il BA. Serve alle
--   testate con `billing_account_id` NOT NULL (contratti, offerte),
--   il cui guard confronta l'emittente del documento con
--   `anagrafiche.fn_get_emittente_fiscale_pk(ba)`. Senza legame
--   quella funzione ricade sull'emittente di DEFAULT.
-- ⭐ Rev 20261018-37: istanza, BA e legame li scrive il BB
--   anagrafiche.fn_crea_billing_account (regola del 2). Qui restano
--   le scelte della fixture: il codice, la categoria, la valuta e la
--   finestra dei vincoli.
DECLARE
    v_soggetto_id anagrafiche.soggetti.id%TYPE;
    v_sr_id       anagrafiche.soggetti_ruoli.id%TYPE;
    v_ist_id      anagrafiche.billing_account.istanza_utility_id%TYPE;
    v_ba_id       anagrafiche.billing_account.id%TYPE;
    v_utility_id  anagrafiche.billing_account.utility_id%TYPE;
    v_codice      text;
BEGIN
    v_utility_id := COALESCE(
        p_utility_id,
        (SELECT u.id FROM config.utilities u ORDER BY u.id LIMIT 1));

    IF v_utility_id IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_cliente_ba: nessuna utility a catalogo';
    END IF;

    -- Codice libero: `codice` e' UNIQUE, quindi una sigla fissa farebbe
    -- collidere la seconda chiamata con la prima.
    -- ⛔ Il massimo si legge dalle ISTANZE, non dai BA (rev
    --   20260923-07): billing_account e' in RLS, e sotto un operatore
    --   mostra solo i BA della SUA azienda. istanze_utilities in RLS non
    --   e', e il builder le scrive con lo stesso codice del BA.
    SELECT 'PGTAPBA' || lpad((COALESCE(max(substring(iu.codice from 8)::bigint), 0) + 1)::text, 5, '0')
      INTO v_codice
      FROM anagrafiche.istanze_utilities iu
     WHERE iu.codice ~ '^PGTAPBA[0-9]{5}$';
    v_codice := COALESCE(v_codice, 'PGTAPBA00001');

    v_soggetto_id := dbops.fn_pgtap_crea_soggetto_pg(
                         'Cliente ' || p_etichetta || ' ' || v_codice);
    v_sr_id       := dbops.fn_pgtap_crea_soggetto_ruolo(
                         v_soggetto_id, 'CL'::character varying);

    -- ⛔ LA FINESTRA DIFFERITA. `trgfn_istanze_utilities_require_utility_dichiarata`
    --   verifica al COMMIT che l'istanza abbia un satellite (BA / dato
    --   precontrattuale / cliente). Con i vincoli IMMEDIATE, come li
    --   mette il preambolo dei pgTAP, scatterebbe sull'INSERT
    --   dell'istanza, prima che il BA esista.
    SET CONSTRAINTS ALL DEFERRED;

    -- ⚠️ `valuta_id` VALORIZZATA: la risoluzione della valuta di un
    --   documento e' la catena «BA -> emittente -> gestore», e su un
    --   database ricostruito dai changelog nessuno dei tre la porta.
    --   Chiudendo l'anello piu' vicino al documento, la fixture non
    --   dipende da com'e' configurata la macchina.
    SELECT b.billing_account_id, b.istanza_utility_id
      INTO v_ba_id, v_ist_id
      FROM anagrafiche.fn_crea_billing_account(
               p_soggetto_ruolo_id           := v_sr_id,
               p_utility_id                  := v_utility_id,
               p_campi                       := jsonb_build_object(
                   'codice',               v_codice,
                   'categoria_cliente_id', (SELECT cc.id FROM anagrafiche.categorie_clienti cc
                                             ORDER BY cc.id LIMIT 1),
                   'valuta_id',            dbops.fn_pgtap_valuta()),
               p_istanza                     := jsonb_build_object('codice', v_codice),
               p_emittente_soggetto_ruolo_id := p_emittente_soggetto_ruolo_id) b;

    -- Saga completa: i guard differiti scattano QUI, su un mondo
    -- finito. ⚠️ Senza la richiusura il ROLLBACK del test se li
    -- porterebbe via NON verificati.
    SET CONSTRAINTS ALL IMMEDIATE;

    RETURN QUERY
    SELECT v_ba_id, v_ist_id, v_sr_id, v_soggetto_id, v_utility_id;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_cliente_ba(p_etichetta text, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
IS 'Fixture pgTAP: crea la catena minima di un cliente fatturabile (soggetto -> ruolo CL -> istanza utility -> billing account). Istanza, BA e legame li scrive il BB anagrafiche.fn_crea_billing_account; il builder sceglie il codice libero PGTAPBAnnnnn (dalle istanze, fuori dalla RLS) per istanza e BA, la prima categoria cliente e la valuta di dbops.fn_pgtap_valuta (il billing account e'' una radice della catena vendite.fn_get_valuta_id), e apre e richiude la finestra dei vincoli differiti. Il terzo parametro, opzionale, e'' il soggetto_ruolo dell''EMITTENTE a cui legare il billing account: serve alle testate con billing_account_id NOT NULL (contratti, offerte_commerciali), il cui guard confronta l''emittente del documento con anagrafiche.fn_get_emittente_fiscale_pk(ba); senza legame quella funzione ricade sull''emittente di DEFAULT. Usabile anche come zeroerp_app CON un operatore in sessione: il BB rilegge il BA a istruzione finita, e il legame lo scrive il trigger z90 verso l''emittente di chi agisce; un terzo parametro discorde e'' E_SCRIPT_CHIAMATA_NON_VALIDA (costruire il cliente PRIMA di aprire il contesto, o non passarlo). ⚠️ Esce con i vincoli IMMEDIATE, come ogni helper.';
```

</div>

---
{% include-markdown "signature-core.md" %}
