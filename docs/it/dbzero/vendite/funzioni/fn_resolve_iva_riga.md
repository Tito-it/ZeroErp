{% include-markdown "it/dbzero/vendite/manual/fn_resolve_iva_riga.md" %}
# ⚙️ Funzione `fn_resolve_iva_riga`

```sql
CREATE FUNCTION fn_resolve_iva_riga(p_articolo_id uuid, p_data_riferimento date, p_imponibile numeric, p_billing_account_id bigint, p_utility_id integer, p_soggetto_id uuid, p_emittente_fiscale_id bigint, p_paese_emittente character, p_paese_cliente character, p_e_cessione_beni boolean, p_consumo boolean)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_iva_riga(p_articolo_id uuid, p_data_riferimento date, p_imponibile numeric DEFAULT NULL::numeric, p_billing_account_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_soggetto_id uuid DEFAULT NULL::uuid, p_emittente_fiscale_id bigint DEFAULT NULL::bigint, p_paese_emittente character DEFAULT NULL::bpchar, p_paese_cliente character DEFAULT NULL::bpchar, p_e_cessione_beni boolean DEFAULT NULL::boolean, p_consumo boolean DEFAULT false)
 RETURNS TABLE(quota numeric, iva_id integer, aliquota numeric, natura_codice character varying, is_reverse_charge boolean, esigibilita character, split_payment boolean, riferimento_normativo character varying, origine character varying, titolo_iva_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: essere LA porta del risolutore IVA. Stabilisce il contesto
--   del dispatch — paese di chi emette, paese del cliente, natura
--   dell'operazione — e passa la palla all'implementazione del
--   paese giusto. La regola vera sta li', non qui.
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I2 / D20 / D21.
-- ⚠️ I tre parametri di contesto sono FACOLTATIVI e derivati quando
--   non passati: chi chiama oggi non deve saperne niente, e la
--   firma non cambiera' il giorno che si aggiunge un paese.
-- ⭐ p_consumo (rev 2026-10-04, decisione C di brief-db-bom-flag-quantita-
--   e-kit-in-fattura §13), IN CODA alla firma: la domanda del giro del
--   plafond in fattura. Si inoltra com'e': e' l'implementazione del paese a
--   sapere cosa vuol dire. Default false: tutto come prima.
DECLARE
    v_paese_emitt   config.stati.codice_iso2%TYPE;
    v_paese_cli     config.stati.codice_iso2%TYPE;
    v_cessione_beni config.nature_vendita.e_cessione_beni%TYPE;
BEGIN
    -- ══ IL CONTESTO DEL DISPATCH ═══════════════════════════════
    -- ⚠️ Il paese si legge da config.stati.codice_iso2, che e' una
    --   chiave naturale esterna (standard ISO) e quindi stabile per
    --   costruzione — non un codice di casa che qualcuno rinomina.
    --   E' lo stesso percorso del dispatcher CF/PIVA.
    v_paese_emitt := p_paese_emittente;
    IF v_paese_emitt IS NULL AND p_emittente_fiscale_id IS NOT NULL THEN
        SELECT st.codice_iso2 INTO v_paese_emitt
          FROM anagrafiche.emittenti_fiscali ef
          JOIN anagrafiche.soggetti_ruoli sr ON sr.id = ef.soggetto_ruolo_id
          JOIN anagrafiche.soggetti s        ON s.id  = sr.soggetto_id
          JOIN config.stati st               ON st.id = s.stato_id
         WHERE ef.id = p_emittente_fiscale_id;
    END IF;

    v_paese_cli := p_paese_cliente;
    IF v_paese_cli IS NULL AND p_soggetto_id IS NOT NULL THEN
        SELECT st.codice_iso2 INTO v_paese_cli
          FROM anagrafiche.soggetti s
          JOIN config.stati st ON st.id = s.stato_id
         WHERE s.id = p_soggetto_id;
    END IF;

    -- Cessione di beni o prestazione di servizi: sta sul vocabolario
    -- (D23), agganciato all'articolo via natura_vendita_id.
    v_cessione_beni := p_e_cessione_beni;
    IF v_cessione_beni IS NULL THEN
        SELECT nv.e_cessione_beni INTO v_cessione_beni
          FROM catalogo.articoli a
          JOIN config.nature_vendita nv ON nv.id = a.natura_vendita_id
         WHERE a.id = p_articolo_id;
    END IF;

    -- ══ LO SMISTAMENTO ═════════════════════════════════════════
    -- ⚠️ Decide il paese di CHI EMETTE: e' il suo regime fiscale a
    --   stabilire quale legge si applica. Il paese del cliente entra
    --   nella regola, non nella scelta dell'implementazione.
    -- ⚠️ Emittente assente -> si assume l'Italia, ed e' una scelta:
    --   oggi e' l'unico paese implementato, e rifiutare una chiamata
    --   che non nomina l'emittente spegnerebbe le anteprime di
    --   documento che l'emittente non lo passano.
    IF COALESCE(v_paese_emitt, 'IT') = 'IT' THEN
        RETURN QUERY
        SELECT * FROM vendite.fn_resolve_iva_riga_it(
            p_articolo_id, p_data_riferimento, p_imponibile,
            p_billing_account_id, p_utility_id,
            p_soggetto_id, p_emittente_fiscale_id, p_consumo);
        RETURN;
    END IF;

    -- ⛔ IL RAMO CHE IL DISPATCHER CF/PIVA NON HA. Li' un paese
    --   diverso non valida niente, in silenzio; qui il silenzio
    --   sarebbe un'imposta sbagliata senza errore.
    PERFORM script.fn_log_and_raise_error(
        'vendite', 'fn_resolve_iva_riga', 'E_IVA_PAESE_NON_IMPLEMENTATO',
        jsonb_build_object('paese_emittente', v_paese_emitt,
                           'paese_cliente',   v_paese_cli,
                           'cessione_beni',   v_cessione_beni,
                           'articolo_id',     p_articolo_id),
        NULL::uuid, v_paese_emitt);
END;
$function$

COMMENT ON FUNCTION vendite.fn_resolve_iva_riga(p_articolo_id uuid, p_data_riferimento date, p_imponibile numeric, p_billing_account_id bigint, p_utility_id integer, p_soggetto_id uuid, p_emittente_fiscale_id bigint, p_paese_emittente character, p_paese_cliente character, p_e_cessione_beni boolean, p_consumo boolean)
IS 'LA PORTA del risolutore IVA: e'' questa che i chiamanti chiamano. Stabilisce il contesto del dispatch — paese di chi emette, paese del cliente, natura dell''operazione — e passa la palla all''implementazione del paese giusto; la regola vera sta li'' (oggi vendite.fn_resolve_iva_riga_it). ⭐ GUSCIO e non parametro con rami interni (D21, decisione di Tid): cosi'' aggiungere un paese e'' aggiungere una funzione piu'' una riga qui, mentre con i rami dentro un corpo solo sarebbe riaprire ogni volta la funzione che calcola l''IVA di tutti — la prima e'' additiva, la seconda no. Stampo gia'' in casa: anagrafiche.trgfn_soggetti_valida_cf_piva_dispatch -> script.fn_validate_cf_piva_it. ⛔ MA CON L''ELSE CHE SOLLEVA, e il precedente su questo NON va copiato: il dispatcher del codice fiscale fa IF country = IT e non ha nessun ELSE, quindi per un paese diverso non valida niente IN SILENZIO. Su una validazione e'' un buco; su un risolutore IVA sarebbe un''imposta sbagliata senza errore — qui si solleva E_IVA_PAESE_NON_IMPLEMENTATO. ⚠️ Smista sul paese di CHI EMETTE: e'' il suo regime fiscale a stabilire quale legge si applica; il paese del cliente entra nella regola (per l''intracomunitario decide il luogo di imposizione insieme alla natura dell''operazione) ma non nella scelta dell''implementazione. ⭐ LA FIRMA E'' IL PUNTO, non la logica (D20): prende gia'' il paese di ENTRAMBE le parti e la natura dell''operazione, tutti e tre facoltativi e DERIVATI quando non passati — chi chiama oggi non deve saperne niente, e la firma non cambiera'' il giorno che si aggiunge un paese. ⚠️ Oggi l''implementazione italiana quei tre non li usa: normalmente un parametro accettato e non usato e'' il difetto che questo cantiere combatte, ma la differenza e'' netta — quello e'' un campo che un OPERATORE compila credendo di decidere qualcosa, questo e'' un punto di estensione dichiarato, che costa niente adesso e costerebbe ogni chiamante dopo. ℹ️ I tre si derivano QUI e non nel chiamante perche'' stabilire il contesto del dispatch e'' mestiere del guscio: farli cercare a chi chiama vorrebbe dire ripetere tre lookup in ogni punto che risolve l''IVA. ⚠️ Emittente assente -> si assume l''Italia: oggi e'' l''unico paese implementato, e rifiutare una chiamata che non nomina l''emittente spegnerebbe le anteprime di documento che non lo passano. ⚠️ Il paese si legge da config.stati.codice_iso2, chiave naturale esterna (standard ISO) e quindi stabile per costruzione. ⭐ p_consumo (rev 2026-10-04, decisione C di brief-db-bom-flag-quantita-e-kit-in-fattura §13), in CODA alla firma: la domanda del giro del plafond in fattura — quale titolo vale e quali sono i due trattamenti, senza proiezione sul residuo. Si inoltra com''e'' all''implementazione del paese; default false, tutto come prima.';
```

</div>

---
{% include-markdown "signature-core.md" %}
