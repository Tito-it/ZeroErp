{% include-markdown "it/dbzero/dbops/manual/fn_pgtap_crea_listino.md" %}
# ⚙️ Funzione `fn_pgtap_crea_listino`

```sql
CREATE FUNCTION fn_pgtap_crea_listino(p_utility_id integer, p_etichetta text, p_valido_dal date, p_valido_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION dbops.fn_pgtap_crea_listino(p_utility_id integer, p_etichetta text DEFAULT 'pgTAP'::text, p_valido_dal date DEFAULT script.fn_data_operativa(), p_valido_al date DEFAULT NULL::date)
 RETURNS TABLE(listino_id bigint, listino_versione_id bigint, tipologia_id smallint)
 LANGUAGE plpgsql
AS $function$
-- Scopo: dare a una fixture pgTAP un LISTINO con una versione ATTIVA,
--   dell'azienda di chi agisce, per l'utility scelta dal test.
--   vendite.listini e' anagrafica: su un database ricostruito e' vuota.
-- Uso:
--   CREATE TEMP TABLE tmp_listino AS
--   SELECT * FROM dbops.fn_pgtap_crea_listino(<utility_id>, 'offerta');
--   -- versione scaduta, per chi collauda la chiusura:
--   SELECT * FROM dbops.fn_pgtap_crea_listino(<utility_id>, 'chiusura',
--                                             DATE '2022-01-01', DATE '2022-12-31');
-- ⚠️ L'emittente non si sceglie: e' quello di CHI AGISCE
--   (script.fn_pgtap_emittente_sr_operatore), perche' il guard
--   emittente_scope di vendite.listini non ne accetta un altro. Quindi
--   il contesto va aperto PRIMA.
-- ⚠️ La tipologia e' la prima AMMESSA per l'utility
--   (config.listini_tipologie_utilities, guard
--   trgfn_listini_guard_tipologia_utility): una qualunque sbatterebbe
--   sul guard per le utility che non la prevedono. E non e' una quota
--   fissa (config.listini_tipologie.e_quota_fissa): l'articolo d'appoggio
--   sarebbe una quota fissa a canone, che senza periodicita' non lascia
--   attivare la versione. Chi vuole un listino di quota fissa lo
--   costruisce e da' la periodicita' alle righe.
-- ⛔ Le RIGHE del listino del test non le scrive: prezzi e componenti
--   sono il caso del test. Ne scrive UNA d'appoggio, su un articolo suo
--   (rev 2026-10-28, 20261028-25): una versione si attiva solo con un
--   prezzo (script.fn_check_versione_listino_attivabile), e si attiva dal
--   verbo (vendite.fn_attiva_versione_listino, via
--   dbops.fn_pgtap_porta_a_stato). Chi conta le righe della versione ne
--   trova una in piu': quella d'appoggio, il suo articolo ha il codice
--   PGTAP_LST_ART_<casuale>.
DECLARE
    v_emittente_sr vendite.listini.emittente_soggetto_ruolo_id%TYPE;
    v_tipologia    vendite.listini.tipologia_id%TYPE;
    v_listino      vendite.listini.id%TYPE;
    v_versione     vendite.listini_versioni.id%TYPE;
    v_articolo     catalogo.articoli.id%TYPE;
BEGIN
    v_emittente_sr := script.fn_pgtap_emittente_sr_operatore();

    IF v_emittente_sr IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_listino: nessun emittente per chi agisce — aprire il contesto prima (script.fn_pgtap_set_contesto_operatore)';
    END IF;

    SELECT ltu.tipologia_id INTO v_tipologia
      FROM config.listini_tipologie_utilities ltu
      JOIN config.listini_tipologie lt
        ON lt.id = ltu.tipologia_id
       AND lt.attivo
     WHERE ltu.utility_id = p_utility_id
       AND ltu.attivo
       AND lt.e_quota_fissa IS NOT TRUE
     ORDER BY lt.ordinamento, lt.id
     LIMIT 1;

    IF v_tipologia IS NULL THEN
        RAISE EXCEPTION
            'fn_pgtap_crea_listino: nessuna tipologia di listino ammessa per l''utility %, esclusa la quota fissa (config.listini_tipologie_utilities)',
            p_utility_id;
    END IF;

    -- Codice libero: uq_listini_codice e' globale, una sigla fissa
    -- farebbe collidere la seconda chiamata con la prima.
    INSERT INTO vendite.listini (
        codice, descrizione, utility_id, tipologia_id, emittente_soggetto_ruolo_id
    )
    VALUES (
        'PGTAP_LST_' || substr(md5(clock_timestamp()::text || random()::text), 1, 16),
        'Fixture pgTAP: listino ' || p_etichetta,
        p_utility_id, v_tipologia, v_emittente_sr
    )
    RETURNING id INTO v_listino;

    -- Nasce in bozza (trigger della nascita).
    INSERT INTO vendite.listini_versioni (
        listino_id, codice_versione, valido_dal, valido_al
    )
    VALUES (v_listino, 'PGTAP_V1', p_valido_dal, p_valido_al)
    RETURNING id INTO v_versione;

    -- La riga d'appoggio: un articolo suo, della tipologia del listino.
    v_articolo := dbops.fn_pgtap_crea_articolo(
        'PGTAP_LST_ART_' || substr(md5(clock_timestamp()::text || random()::text), 1, 12),
        false,
        p_listino_tipologia_id => v_tipologia);
    PERFORM dbops.fn_pgtap_listino_aggiungi_articoli(v_versione, ARRAY[v_articolo]);

    -- Attiva dal verbo.
    PERFORM dbops.fn_pgtap_porta_a_stato('vendite.listini_versioni'::regclass, v_versione, 'ATTIVA');

    RETURN QUERY SELECT v_listino, v_versione, v_tipologia;
END;
$function$

COMMENT ON FUNCTION dbops.fn_pgtap_crea_listino(p_utility_id integer, p_etichetta text, p_valido_dal date, p_valido_al date)
IS 'Fixture pgTAP: un listino con una versione ATTIVA, dell''emittente di chi agisce (contesto aperto prima), per l''utility scelta. Tipologia: la prima ammessa per l''utility (config.listini_tipologie_utilities) che non e'' una quota fissa (config.listini_tipologie.e_quota_fissa): la quota fissa a canone vuole la periodicita'' sulle righe, e chi vuole quel listino lo costruisce e la da'' (dbops.fn_pgtap_listino_aggiungi_articoli, p_periodicita). Date della versione a scelta (default: dalla data operativa, aperta). La versione nasce in bozza, prende una riga d''appoggio (un articolo suo, codice PGTAP_LST_ART_<casuale>: chi conta le righe ne trova una in piu'') e si attiva dal verbo (dbops.fn_pgtap_porta_a_stato, che chiama vendite.fn_attiva_versione_listino). Le altre righe restano al test. Senza contesto, o senza una tipologia ammessa che non sia di quota fissa: RAISE EXCEPTION.';
```

</div>

---
{% include-markdown "signature-core.md" %}
