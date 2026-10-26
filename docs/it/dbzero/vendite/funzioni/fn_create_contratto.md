{% include-markdown "it/dbzero/vendite/manual/fn_create_contratto.md" %}
# ⚙️ Funzione `fn_create_contratto`

```sql
CREATE FUNCTION fn_create_contratto(p_testata jsonb, p_utility jsonb)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_create_contratto(p_testata jsonb, p_utility jsonb DEFAULT NULL::jsonb)
 RETURNS TABLE(contratto_id bigint, numero character varying)
 LANGUAGE plpgsql
AS $function$
-- rev 2026-10-24 (20261024-14, brief-modello-documento-vendita N-1/P-2):
--   lo stato iniziale non si scrive piu' qui: lo mette il trigger della
--   nascita (script.trgfn_doc_stato_iniziale), letto dal vocabolario.
DECLARE
    v_numero       vendite.contratti.numero%TYPE;
    v_contratto_id vendite.contratti.id%TYPE;
    v_testata      jsonb;   -- le sole chiavi ammesse, piu' il numero
    v_util         jsonb;   -- le sole chiavi ammesse della fornitura
    -- rev 2026-07-27: aggiunta 'fatturazione_immediata' (corsia di
    -- instradamento, Fase B brief emissione mirata). Va decisa PRIMA
    -- del push in commessa: in create e' il momento naturale, e senza
    -- questa voce la chiave veniva scartata in silenzio.
    -- rev 2026-08-31: aggiunti i TRE RIFERIMENTI DELL'ATTO — CIG, CUP
    -- e commessa. Stesso difetto della riga sopra, sulla stessa
    -- funzione: in PATCH il backend li scriveva gia', in CREATE la
    -- chiave veniva scartata e il contratto nasceva senza il CIG,
    -- senza nessun errore. ⚠️ A differenza di fatturazione_immediata
    -- le tre sono NULLABLE: un null e' un valore legittimo e vuol
    -- dire «non c'e' un CIG», quindi il BE puo' mandarle sempre.
    v_testata_allowed text[] := ARRAY[
        'billing_account_id', 'emittente_fiscale_id', 'istanza_utility_id',
        'utility_id', 'ambito', 'valido_dal', 'valido_al',
        'parent_contratto_id', 'data', 'listino_id',
        'tipo_variazione_globale', 'valore_variazione_globale',
        'categoria_cliente_id_snapshot', 'valuta_id',
        'fatturazione_immediata',
        'codice_cig', 'codice_cup', 'codice_commessa', 'meta'
    ];
    v_util_allowed text[] := ARRAY[
        'istanza_utility_id', 'utility_id', 'istanza_dati_precontrattuali_id',
        'tipo_utenza_id', 'classe_utenza_id', 'param_1_num',
        'param_2_txt', 'meta'
    ];
BEGIN
    -- ----------------------------------------------------
    -- 1) Numero contratto (consuma il contatore; rolla con
    --    la funzione se un qualsiasi step successivo fallisce).
    -- ----------------------------------------------------
    v_numero := script.fn_generate_codice('contratto');

    -- 2) Lo stato iniziale non si scrive: lo mette il trigger della
    --    nascita (trg_contratti_a05_stato_iniziale_ins), dal vocabolario.

    -- ----------------------------------------------------
    -- 3) INSERT testata: solo chiavi whitelisted presenti
    --    (le assenti ereditano default/trigger DB).
    -- ----------------------------------------------------
    --    La scrittura la fa il BB script.fn_scrivi_riga_da_jsonb (rev
    --    2026-10-17, regola del 2); il FILTRO delle chiavi resta qui, perche'
    --    lo scarto (non il rifiuto) e' una regola di questa madre.
    SELECT COALESCE(jsonb_object_agg(e.key, e.value), '{}'::jsonb)
      INTO v_testata
      FROM jsonb_each(COALESCE(p_testata, '{}'::jsonb)) AS e
     WHERE e.key = ANY(v_testata_allowed);

    v_contratto_id := (script.fn_scrivi_riga_da_jsonb(
                           'vendite.contratti'::regclass,
                           v_testata || jsonb_build_object('numero', v_numero))
                       ->> 'id')::bigint;

    -- ----------------------------------------------------
    -- 4) La scheda di fornitura dell'operatore (opzionale).
    --    rev 2026-10-12 (brief-db-indirizzi-documento-seguono-il-cliente,
    --    D-7 di Tid): il trigger alla nascita (step 3) ha gia' scritto
    --    la scheda dall'anagrafica, se la coppia ha dati
    --    precontrattuali. Prima l'INSERT dell'operatore collideva su
    --    uq_contratti_utilities_contratto_id e il contratto non si
    --    creava. Ora VINCE L'OPERATORE, come nel push dall'offerta:
    --    l'anagrafica fa da base, le sue chiavi la correggono.
    --    ⚠️ UPDATE e non INSERT ... ON CONFLICT: i trigger BEFORE
    --    INSERT giudicano la riga PROPOSTA prima del conflitto, e il
    --    guard tipo/classe la rifiuterebbe se l'operatore manda solo
    --    una parte della scheda. L'UPDATE giudica la riga finale.
    -- ----------------------------------------------------
    IF p_utility IS NOT NULL AND p_utility <> '{}'::jsonb THEN
        SELECT COALESCE(jsonb_object_agg(e.key, e.value), '{}'::jsonb)
          INTO v_util
          FROM jsonb_each(p_utility) AS e
         WHERE e.key = ANY(v_util_allowed);

        IF EXISTS (SELECT 1
                     FROM vendite.contratti_utilities cu
                    WHERE cu.contratto_id = v_contratto_id) THEN
            -- La scheda dall'anagrafica c'e': si correggono le sole chiavi
            -- mandate (nessuna chiave ammessa: nessuna scrittura).
            PERFORM script.fn_scrivi_riga_da_jsonb(
                'vendite.contratti_utilities'::regclass,
                v_util,
                jsonb_build_object('contratto_id', v_contratto_id));
        ELSE
            PERFORM script.fn_scrivi_riga_da_jsonb(
                'vendite.contratti_utilities'::regclass,
                v_util || jsonb_build_object('contratto_id', v_contratto_id));
        END IF;
    END IF;

    -- ----------------------------------------------------
    -- 5) Lo slot di default dall'anagrafica del cliente (rev 2026-10-11,
    --    brief-db-indirizzi-documento-seguono-il-cliente, D-2 e decisione di
    --    Tid sul «quando»: alla creazione lo fa scattare chi crea). La regola
    --    sta in vendite.fn_doc_indirizzo_default; prima la applicava il
    --    backend dopo questa funzione (auto_assegna_indirizzo_default).
    --    Dopo la fornitura: l'istanza del contratto c'e' gia' in testata.
    -- ----------------------------------------------------
    PERFORM vendite.fn_doc_indirizzo_default('CONTRATTO', v_contratto_id);

    RETURN QUERY
    SELECT v_contratto_id, v_numero;
END;
$function$

COMMENT ON FUNCTION vendite.fn_create_contratto(p_testata jsonb, p_utility jsonb)
IS 'Funzione madre atomica: genera il numero, crea la testata contratto (stato DRAFT) e l''eventuale riga utility in un''unica statement (o tutto o rollback, contatore numero incluso). INSERT dinamico delle sole chiavi whitelisted presenti (rispetta i default DB). SECURITY INVOKER. Ritorna (contratto_id, numero). rev 2026-07-27: ''fatturazione_immediata'' aggiunta a v_testata_allowed — la corsia di instradamento si decide PRIMA del push in commessa e la create e'' il momento naturale; senza questa voce la chiave veniva scartata in silenzio. rev 2026-08-31: aggiunti ''codice_cig'', ''codice_cup'' e ''codice_commessa'' — i tre riferimenti dell''atto, colonne dal 20260829-13. ⛔ E'' LO STESSO DIFETTO della rev precedente sulla stessa funzione: in PATCH il backend li scriveva gia'', in CREATE la chiave veniva SCARTATA e il contratto nasceva senza il CIG, con un 200 e nessun errore a video. Un CIG nasce con la gara, cioe'' PRIMA del contratto: la creazione e'' il momento naturale per digitarlo. ⚠️ IL FILTRO E'' SULLA PRESENZA DELLA CHIAVE, e la semantica del null NON e'' la stessa su tutte le voci: ''fatturazione_immediata'' e'' NOT NULL con DEFAULT false, quindi chiave assente = DEFAULT e chiave = null = 23502 (il BE deve omettere o mandare un booleano, mai null); i tre codici dell''atto sono NULLABLE, quindi un null e'' un valore legittimo che significa «non c''e'' un CIG» e il BE puo'' mandarli sempre. ⛔ La whitelist resta NON fail-loud (chiave ignota scartata e non respinta): renderla tale cambierebbe il comportamento di TUTTE le chiavi di una madre gia'' in uso dal backend, e resta la proposta §6 di brief-db-fatturazione-immediata-create-contratto. Piano: analisi-fix-transazioni Classe A #2 + brief-db-fatturazione-immediata-create-contratto + brief-db-fn-create-contratto-codici-atto. rev 2026-10-11 (brief-db-indirizzi-documento-seguono-il-cliente, D-2): in coda, lo slot di default dall''anagrafica del cliente con vendite.fn_doc_indirizzo_default(''CONTRATTO'', id) — prima lo faceva il backend dopo questa funzione. RETURNS TABLE ancorato (vendite.contratti.id%TYPE, vendite.contratti.numero%TYPE: stessi tipi). rev 2026-10-12 (brief-db-indirizzi-documento-seguono-il-cliente, D-7 di Tid): la scheda di fornitura dell''operatore CORREGGE quella che il trigger alla nascita ha appena scritto dall''anagrafica (vendite.fn_doc_fornitura_da_anagrafica), con un UPDATE delle sole chiavi mandate; prima l''INSERT collideva su uq_contratti_utilities_contratto_id e un contratto su una fornitura con dati precontrattuali non si creava. Vince l''operatore, come nel push dall''offerta; perche'' veda i dati dell''anagrafica prima di creare, il drawer li legge da vendite.fn_get_fornitura_da_anagrafica. UPDATE e non ON CONFLICT: i trigger BEFORE INSERT giudicherebbero la riga proposta, parziale. Senza scheda dall''anagrafica resta l''INSERT di prima. rev 2026-10-17 (brief-db-processi-accensione-per-ambiente, 2b-1): le due scritture dinamiche (testata, fornitura) passano dal BB script.fn_scrivi_riga_da_jsonb, regola del 2; il filtro delle chiavi ammesse (scarto, non rifiuto) resta qui. Comportamento invariato.';
```

</div>

---
{% include-markdown "signature-core.md" %}
