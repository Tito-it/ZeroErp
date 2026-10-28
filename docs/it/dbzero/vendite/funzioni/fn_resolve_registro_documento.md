{% include-markdown "it/dbzero/vendite/manual/fn_resolve_registro_documento.md" %}
# ⚙️ Funzione `fn_resolve_registro_documento`

```sql
CREATE FUNCTION fn_resolve_registro_documento(p_billing_account_id_riga bigint, p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_resolve_registro_documento(p_billing_account_id_riga bigint, p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint DEFAULT NULL::bigint)
 RETURNS TABLE(ba_fatturazione_id bigint, utility_id integer, emittente_soggetto_ruolo_id bigint, registro_id bigint, serie character varying, politica_data_documento character varying)
 LANGUAGE plpgsql
 STABLE ROWS 1
AS $function$
DECLARE
    v_ba_fattura_id anagrafiche.billing_account.id%TYPE;
    v_utility_id    anagrafiche.billing_account.utility_id%TYPE;
    v_emittente_id  anagrafiche.soggetti_ruoli.id%TYPE;
    v_registro_id   vendite.registri_fatturazione.id%TYPE;
    v_serie         vendite.tipi_doc_fiscale_registri.serie%TYPE;
    v_politica      vendite.registri_fatturazione.politica_data_documento%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   «Su quale sezionale nascera' un documento di questo tipo
    --   e di questa natura, per questo billing account» — e con
    --   quale politica di data. Una sede sola, per chi legge e
    --   per chi scrive.
    --
    -- ⛔ NON SOLLEVA SUI DATI: tipo documento assente, natura non
    --   risolvibile, registro non mappato, billing account non
    --   visibile — tutto esce NULL. Il solo raise e' il guard di
    --   parametro qui sotto.
    -- =========================================================

    -- Guard di parametro: TECNICO, perche' nessuna interfaccia
    -- produce questo valore. vendite.commesse.billing_account_id
    -- e' NOT NULL, e fn_build_fattura_key ha gia' il suo
    -- E_VALORE_MANCANTE a monte.
    IF p_billing_account_id_riga IS NULL OR p_billing_account_id_riga <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'database', 'vendite.fn_resolve_registro_documento',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object(
                'detail', 'billing account della riga obbligatorio e maggiore di zero',
                'p_billing_account_id_riga', p_billing_account_id_riga),
            NULL::uuid,
            'vendite.fn_resolve_registro_documento',
            'p_billing_account_id_riga (obbligatorio, maggiore di zero)');
    END IF;

    -- ⛔ I DUE ANCORAGGI, in una lettura sola e da due colonne
    --    DIVERSE della stessa riga:
    --      * il BA di FATTURAZIONE e' il PADRE quando c'e';
    --      * la UTILITY e' quella della RIGA.
    --    Scambiarli non da' nessun errore: da' un sezionale
    --    sbagliato, in silenzio.
    SELECT COALESCE(ba.parent_account_id, ba.id), ba.utility_id
      INTO v_ba_fattura_id, v_utility_id
      FROM anagrafiche.billing_account ba
     WHERE ba.id = p_billing_account_id_riga;

    -- ⛔ Riga non trovata — che sotto RLS vuol dire anche «non
    --    visibile a chi sta leggendo» — e ci si FERMA.
    --    Tirare dritto lascerebbe utility ed emittente entrambi
    --    NULL, e la gerarchia a quattro livelli ripiegherebbe sul
    --    registro «di nessuno»: un sezionale plausibile e
    --    sbagliato. «Non lo so» e' una risposta; «il registro
    --    generico» e' una bugia.
    IF FOUND THEN

        -- Emittente dal BA DI FATTURAZIONE, col lettore PURO.
        -- ⚠️ Non anagrafiche.fn_get_emittente_fiscale_id, che
        --    solleva: le due divergono solo sul BA nullo, che il
        --    guard qui sopra ha gia' rifiutato.
        v_emittente_id := script.fn_get_ba_emittente_sr_id(v_ba_fattura_id);

        -- Sezionale, serie e politica: la ricerca vive tutta nel
        -- lookup, gerarchia a quattro livelli compresa.
        SELECT k.registro_id, k.serie, k.politica_data_documento
          INTO v_registro_id, v_serie, v_politica
          FROM vendite.fn_lookup_registro_id(
                   p_tipo_doc_fiscale_id         => p_tipo_doc_fiscale_id,
                   p_natura_doc_id               => p_natura_doc_id,
                   p_utility_id                  => v_utility_id,
                   p_emittente_soggetto_ruolo_id => v_emittente_id) k;
    END IF;

    -- ⭐ UNA riga sempre, anche tutta a NULL.
    RETURN QUERY SELECT v_ba_fattura_id, v_utility_id, v_emittente_id,
                        v_registro_id, v_serie, v_politica;
END;
$function$

COMMENT ON FUNCTION vendite.fn_resolve_registro_documento(p_billing_account_id_riga bigint, p_tipo_doc_fiscale_id bigint, p_natura_doc_id bigint)
IS 'La catena che sceglie il SEZIONALE di un documento, incapsulata per intero e in un punto solo: dal billing account della riga fino a registro, serie e politica della data. La usano sia chi SCRIVE (vendite.fn_build_fattura_key) sia chi LEGGE (le viste della dashboard di competenza, per la colonna «data prevista»), ed e'' questo che impedisce alla previsione di mentire: e'' la stessa funzione, non una copia della stessa logica. ⛔ I DUE ANCORAGGI, ed e'' il motivo per cui esiste: il BA di FATTURAZIONE e'' il PADRE quando c''e'' (COALESCE su parent_account_id), la UTILITY e'' quella della RIGA. Chi ricopia la catena a occhio li scambia, e il difetto e'' silenzioso — la lista mostra un sezionale e la fattura ne prende un altro. ⚠️ Sull''EMITTENTE l''ancoraggio e'' innocuo, e va detto per non far cercare il rischio dove non e'': anagrafiche.fn_guard_albero_ba_emittente impone che padre e figlio abbiano lo stesso emittente (due trigger z95, in entrambi i versi, SECURITY DEFINER contro la RLS, nessuna GUC di override). ⛔ Sulla UTILITY no: billing_account.utility_id e'' NOT NULL e nessun guard la vincola fra padre e figlio, ed e'' l''altro dei due assi con cui si sceglie il sezionale — la differenza fra i due ancoraggi e'' viva proprio li''. ⛔ Il parametro si chiama p_billing_account_id_riga APPOSTA: dev''essere il BA della riga, perche'' e'' da li'' che esce la utility; passargli il ba_fatturazione_id — che la vista gruppi gia'' espone — da'' una previsione plausibile e sbagliata proprio sui BA con padre. ⭐ Restituisce anche gli anelli intermedi (BA di fatturazione, utility, emittente) perche'' a fn_build_fattura_key servono per la chiave e per il reseller: senza, dovrebbe ricalcolarseli e i due ancoraggi resterebbero scritti in due posti. ⛔ NON SOLLEVA SUI DATI — tipo documento assente, natura non risolvibile, registro non mappato: tutto NULL. L''unico raise e'' il guard di parametro sul billing account, TECNICO perche'' nessuna interfaccia lo produce. ⛔ E con la riga del billing account NON VISIBILE sotto RLS si FERMA invece di tirare dritto: utility ed emittente sarebbero entrambi NULL e la gerarchia ripiegherebbe sul registro «di nessuno», restituendo un sezionale plausibile e sbagliato. «Non lo so» e'' una risposta; «il registro generico» e'' una bugia. ℹ️ L''emittente si legge con script.fn_get_ba_emittente_sr_id (lettore puro, STABLE) e non con l''involucro che solleva: le due divergono solo sul BA nullo, gia'' rifiutato dal guard. STABLE, e onestamente: tutte le funzioni che chiama lo sono. Piano: brief-db-registro-e-data-prevista-in-competenza, DB-1.';
```

</div>

---
{% include-markdown "signature-core.md" %}
