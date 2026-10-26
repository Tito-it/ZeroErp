{% include-markdown "it/dbzero/script/manual/fn_check_famiglia_documento_struttura_modificabile.md" %}
# ⚙️ Funzione `fn_check_famiglia_documento_struttura_modificabile`

```sql
CREATE FUNCTION fn_check_famiglia_documento_struttura_modificabile(p_famiglia_id integer)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_famiglia_documento_struttura_modificabile(p_famiglia_id integer)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
 SET search_path TO 'pg_catalog', 'public'
AS $function$
DECLARE
    v_motivi   jsonb := '[]'::jsonb;
    v_codice   vendite.famiglie_documento.codice_interno%TYPE;
    v_registri bigint;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Elencare i motivi che impediscono di cambiare le colonne
    --   che dicono DOVE VIVE IL DOCUMENTO di una famiglia:
    --   schema_tabella, nome_tabella, colonna_numero,
    --   colonna_billing_account, colonna_serie.
    --   Funzione PURA (fn_check_*): nessuna scrittura, nessun
    --   raise di dominio.
    --   Consumatori: il guard che rifiuta l'UPDATE, e la
    --   maschera del CRUD, che tiene il gruppo di campi in sola
    --   lettura e dice PERCHE'.
    --
    -- Ritorna: [] se si puo'; altrimenti array ORDINATO di
    --   {codice, reason, reason_key, dettaglio, valori}.
    --   Oggi il motivo e' UNO SOLO.
    --
    -- ⭐ IL PREDICATO E' «ESISTE UN REGISTRO», e non «esiste un
    --   documento numerato»: un registro appena nato ha gia'
    --   copiato dentro di se' i default della famiglia, quindi
    --   la divergenza comincia prima del primo numero.
    --   ⚠️ E i registri SPENTI contano: uno spento si riaccende,
    --   e si riaccende con la forma che aveva.
    --
    -- ⛔ codice_interno non e' fra le colonne protette da qui:
    --   lo presidia il lock automatico con il suo messaggio.
    -- =========================================================

    -- Guard di parametro: un id assente o non positivo non esce
    -- da nessuna interfaccia, lo produce un chiamante rotto.
    IF p_famiglia_id IS NULL OR p_famiglia_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_famiglia_documento_struttura_modificabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('parametro', 'p_famiglia_id',
                               'valore', p_famiglia_id),
            NULL::uuid,
            'script.fn_check_famiglia_documento_struttura_modificabile',
            'identificativo della famiglia non valido');
    END IF;

    SELECT f.codice_interno
      INTO v_codice
      FROM vendite.famiglie_documento f
     WHERE f.id = p_famiglia_id;

    -- ⭐ E non si risponde []: sarebbe «si puo' cambiare», che su
    --   una riga inesistente e' una frase senza senso.
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'script', 'fn_check_famiglia_documento_struttura_modificabile',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('famiglia_id', p_famiglia_id),
            NULL::uuid,
            'script.fn_check_famiglia_documento_struttura_modificabile',
            concat('famiglia di documento ', p_famiglia_id, ' inesistente'));
    END IF;

    -- ---- MOTIVO 1 — la famiglia ha gia' dei registri --------
    SELECT count(*)
      INTO v_registri
      FROM vendite.registri_fatturazione r
     WHERE r.famiglia_documento = v_codice;

    IF v_registri > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_FAMIGLIA_DOCUMENTO_CHIAVE_IMMUTABILE',
            'reason',     'HA_REGISTRI',
            'reason_key', 'amministrazione.famiglie_documento.struttura_blocco.ha_registri',
            'dettaglio',  jsonb_build_object('famiglia_id',    p_famiglia_id,
                                             'codice_interno', v_codice,
                                             'registri',       v_registri),
            -- ⭐ I due valori riempiono i due %s del messaggio a
            --   catalogo: la famiglia e quanti registri la
            --   portano. ⛔ Nessun nome di colonna qui dentro:
            --   quello viaggia nel `campo` del contesto, che e'
            --   il canale del frontend.
            'valori',     jsonb_build_array(v_codice, v_registri::text));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_famiglia_documento_struttura_modificabile(p_famiglia_id integer)
IS 'Pure check (§12.5.1): i motivi che impediscono di cambiare le colonne che dicono DOVE VIVE IL DOCUMENTO di una famiglia (schema_tabella, nome_tabella, colonna_numero, colonna_billing_account, colonna_serie). Torna [] se si puo'', altrimenti il motivo HA_REGISTRI con E_FAMIGLIA_DOCUMENTO_CHIAVE_IMMUTABILE. ⛔ PERCHE'': quelle colonne non descrivono la famiglia, la fanno funzionare — le legge in SQL dinamico il presidio sul cambio emittente del billing account, e le legge script.fn_check_registro_serie_ammessa a ogni scrittura su un registro. Il caso peggiore e'' colonna_serie portata a NULL: da quel momento la serie risulta non ammessa e i registri che ce l''hanno restano con un secchio del contatore che il documento non sa piu'' distinguere, senza che nessun vincolo se ne accorga. ⭐ IL PREDICATO E'' «ESISTE UN REGISTRO» e non «esiste un numero», deliberatamente piu'' largo di quello sulla forma del numero: un registro appena nato ha gia'' copiato dentro di se'' i default della famiglia, quindi la divergenza comincia prima del primo documento; e i registri SPENTI contano, perche'' uno spento si riaccende con la forma che aveva. ⛔ codice_interno NON e'' fra le colonne protette da qui: lo presidia il lock automatico (script.trgfn_lock_columns, E_CODICE_NON_MODIFICABILE), e due presidi sulla stessa colonna con due messaggi diversi sono la cosa da non fare. ⚠️ SECURITY INVOKER motivato: legge solo famiglie_documento e registri_fatturazione, nessuna delle due con RLS — a differenza della gemella sulla disattivazione, che conta documenti sotto RLS ed e'' per questo DEFINER. Un privilegio si chiede quando serve, non per simmetria. ⚠️ Il nome della colonna toccata NON e'' nella frase: viaggia nel context ->> campo, il canale con cui il frontend accende l''input giusto. Piano: brief-be-fe-crud-registri-di-numerazione, sezione 11.5 (DB-3).';
```

</div>

---
{% include-markdown "signature-core.md" %}
