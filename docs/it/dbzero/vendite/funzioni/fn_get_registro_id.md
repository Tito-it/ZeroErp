{% include-markdown "it/dbzero/vendite/manual/fn_get_registro_id.md" %}
# ⚙️ Funzione `fn_get_registro_id`

```sql
CREATE FUNCTION fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint DEFAULT NULL::bigint, p_utility_id integer DEFAULT NULL::integer, p_emittente_soggetto_ruolo_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(registro_id bigint, serie character varying)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_natura_doc_id config.nature_doc_fiscale.id%TYPE;
    v_registro_id   vendite.registri_fatturazione.id%TYPE;
    v_serie         vendite.tipi_doc_fiscale_registri.serie%TYPE;
BEGIN
    -- =========================================================
    -- Scopo: dato un tipo documento E UNA NATURA, il registro di
    --   numerazione e la serie su cui il documento va scritto —
    --   e SOLLEVA se non e' risolvibile.
    --
    -- rev 2026-08-26 (brief-db-registro-e-data-prevista-in-competenza,
    --   L1): la RICERCA se ne va in fn_lookup_registro_id. Qui
    --   resta il punto in cui un NULL diventa un errore di
    --   dominio, perche' questo e' il percorso di chi SCRIVE: un
    --   buco di configurazione deve fermare, non passare.
    --   ⭐ Stessa coppia lettore/involucro gia' in casa
    --   sull'emittente (script.fn_get_ba_emittente_sr_id /
    --   anagrafiche.fn_get_emittente_fiscale_id).
    --
    -- rev 2026-08-18 (brief-design-note-credito-resi N2): la
    --   natura entra nella chiave del mapping e la serie esce
    --   insieme al registro.
    -- =========================================================

    -- Guard di parametro. ⭐ TECNICO dal 2026-08-26 (decisione
    -- di Tid): un tipo documento nullo qui non lo produce un
    -- operatore — l'unico chiamante lo legge da una riga nata
    -- APPROVATA, dove il CHECK lo pretende. E nel contesto non
    -- c'e' nessuna chiave `campo`: un 400 senza campo da
    -- accendere e' un 400 solo di nome.
    -- ⚠️ Qui nominare il parametro nella frase e' AUTORIZZATO
    --    dalla registrazione del codice: il lettore e' chi ha
    --    scritto la chiamata.
    IF p_tipo_doc_fiscale_id IS NULL OR p_tipo_doc_fiscale_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_get_registro_id',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'tipo documento fiscale obbligatorio e maggiore di zero',
                'p_tipo_doc_fiscale_id', p_tipo_doc_fiscale_id),
            NULL::uuid,
            'vendite.fn_get_registro_id',
            'p_tipo_doc_fiscale_id (obbligatorio, maggiore di zero)');
    END IF;

    -- ⭐ La ricerca, il default della natura e la gerarchia a
    --   quattro livelli vivono TUTTI nel lookup: qui non si
    --   cerca piu' niente. La natura risolta torna indietro
    --   apposta, per distinguere i due errori qui sotto.
    SELECT k.natura_doc_id, k.registro_id, k.serie
      INTO v_natura_doc_id, v_registro_id, v_serie
      FROM vendite.fn_lookup_registro_id(
               p_tipo_doc_fiscale_id         => p_tipo_doc_fiscale_id,
               p_natura_doc_id               => p_natura_doc_id,
               p_utility_id                  => p_utility_id,
               p_emittente_soggetto_ruolo_id => p_emittente_soggetto_ruolo_id) k;

    IF v_natura_doc_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_registro_id', 'E_CONFIG_MANCANTE',
            jsonb_build_object('parametro', 'p_natura_doc_id', 'valore', p_natura_doc_id),
            NULL::uuid, 'natura documento non risolta (config.nature_doc_fiscale)');
    END IF;

    IF v_registro_id IS NULL THEN
        PERFORM script.fn_log_and_raise_error('vendite', 'fn_get_registro_id', 'E_CONFIG_MANCANTE',
            jsonb_build_object('tipo_doc_fiscale_id', p_tipo_doc_fiscale_id,
                               'natura_doc_id', v_natura_doc_id,
                               'utility_id', p_utility_id,
                               'emittente', p_emittente_soggetto_ruolo_id),
            NULL::uuid, concat('registro non risolto per tipo_doc ', p_tipo_doc_fiscale_id,
                               ' e natura ', v_natura_doc_id));
    END IF;

    RETURN QUERY SELECT v_registro_id, v_serie;
END;
$function$

COMMENT ON FUNCTION vendite.fn_get_registro_id(p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint, p_utility_id integer, p_emittente_soggetto_ruolo_id bigint)
IS 'Dato un tipo documento fiscale E UNA NATURA (piu'', opzionalmente, utility ed emittente), il registro di numerazione e la SERIE su cui il documento va scritto — e SOLLEVA se non e'' risolvibile. rev 2026-08-26 (brief-db-registro-e-data-prevista-in-competenza, L1): la RICERCA e'' stata estratta in vendite.fn_lookup_registro_id e questa funzione e'' diventata il suo INVOLUCRO. ⭐ E'' la stessa coppia gia'' in casa sull''emittente — script.fn_get_ba_emittente_sr_id legge e torna NULL, anagrafiche.fn_get_emittente_fiscale_id trasforma il NULL in errore — e serve alla stessa cosa: chi LEGGE (le viste della dashboard di competenza, che mostrano una previsione) consuma il lettore, chi SCRIVE consuma questo, dove un buco di configurazione DEVE fermare. ⛔ Firma, RETURNS TABLE e i tre errori sono INVARIATI: i pgTAP che la esercitano chiamano con parametri nominati e asseriscono sui risultati. ⭐ Il lookup restituisce anche la NATURA risolta, ed e'' cosi'' che qui si distingue «natura non risolta» da «registro non trovato» senza rifare il COALESCE del default — cioe'' senza una terza copia della regola che l''estrazione serviva a unificare. ⭐ Il guard su p_tipo_doc_fiscale_id e'' passato da E_PARAMETRO_INVALIDO (DATO_ERRATO, 400) a E_VENDITE_CHIAMATA_NON_VALIDA (TECNICO, 500) — decisione di Tid, 2026-08-26. L''argomento e'' strutturale, non di gusto: l''unico chiamante e'' fn_build_fattura_key, che il tipo documento lo legge da attivita_fatturabili, riga creata dall''emit a partire da un''attivita'' APPROVATA — e chk_commesse_attivita_tipo_doc_emittibile garantisce che li'' il tipo documento ci sia. Un NULL non e'' quindi «l''operatore ha dimenticato un campo» ma un guasto a monte. ⛔ E la spia decisiva: nel contesto NON c''e'' la chiave `campo`, cioe'' finora era un 400 che al frontend non diceva nessun campo da accendere — un 400 solo di nome. ⭐ Nominare il parametro nella frase qui e'' AUTORIZZATO dalla registrazione del codice, il cui lettore e'' chi ha scritto la chiamata. ℹ️ Costo backend zero: il codice e'' gia'' nel catalogo, in error_messages_fallback.py e in error_policies_generated.py. ⚠️ Per chi consuma lo status passa da 400 a 500. ⚠️ I due E_CONFIG_MANCANTE restano invece INTATTI, area e nome compresi: cambiarli sarebbe rumore su punti di log che nessuno ha chiesto di toccare. ℹ️ Volatilita'' invariata: STABLE serve al lookup, che finisce nel target list di una vista; questa la chiama solo chi scrive.';
```

</div>

---
{% include-markdown "signature-core.md" %}
