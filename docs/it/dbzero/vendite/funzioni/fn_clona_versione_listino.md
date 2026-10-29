{% include-markdown "it/dbzero/vendite/manual/fn_clona_versione_listino.md" %}
# ⚙️ Funzione `fn_clona_versione_listino`

```sql
CREATE FUNCTION fn_clona_versione_listino(p_sorgente_id bigint, p_codice_versione character varying, p_valido_dal date, p_valido_al date)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_clona_versione_listino(p_sorgente_id bigint, p_codice_versione character varying, p_valido_dal date, p_valido_al date DEFAULT NULL::date)
 RETURNS TABLE(versione_id bigint, righe_copiate integer, componenti_copiati integer, componenti_saltati integer)
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_listino_id vendite.listini_versioni.listino_id%TYPE;
    v_tx_id      vendite.listini_versioni.tx_id%TYPE;
    v_nuova_id   vendite.listini_versioni.id%TYPE;
    -- CONTEGGI delle righe copiate e dei componenti della sorgente.
    v_righe      integer;
    v_componenti integer;
    v_comp_sorg  integer;
BEGIN
    -- ==========================================================
    -- Scopo: copiare una versione di listino, con le sue righe
    --   e i suoi componenti attivi, in una versione nuova in
    --   BOZZA dello stesso listino, in una transazione.
    --   Vedi l'intestazione del changeSet 20261029-04.
    -- ==========================================================

    -- 1. Parametri e sorgente, nel perimetro (RLS).
    IF p_sorgente_id IS NULL OR p_sorgente_id <= 0 THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_clona_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_sorgente_id', p_sorgente_id),
            NULL::uuid, 'vendite.fn_clona_versione_listino',
            'p_sorgente_id (obbligatorio, maggiore di zero)');
    END IF;
    IF NULLIF(btrim(p_codice_versione), '') IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_clona_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_codice_versione', p_codice_versione),
            NULL::uuid, 'vendite.fn_clona_versione_listino',
            'p_codice_versione (obbligatorio, non vuoto)');
    END IF;
    IF p_valido_dal IS NULL THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_clona_versione_listino',
            'E_VENDITE_CHIAMATA_NON_VALIDA',
            jsonb_build_object('p_valido_dal', p_valido_dal),
            NULL::uuid, 'vendite.fn_clona_versione_listino',
            'p_valido_dal (obbligatorio)');
    END IF;

    SELECT lv.listino_id, lv.tx_id
      INTO v_listino_id, v_tx_id
      FROM vendite.listini_versioni lv
     WHERE lv.id = p_sorgente_id
       FOR KEY SHARE OF lv;
    IF NOT FOUND THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'vendite.fn_clona_versione_listino',
            'E_VENDITE_LISTINO_VERSIONE_NOT_FOUND',
            -- Frase chiusa: nessun segnaposto, il variadico vuoto e' esplicito.
            jsonb_build_object('id', p_sorgente_id), NULL::uuid,
            VARIADIC ARRAY[]::text[]);
    END IF;

    -- 2. Prima cio' che vieta, prima di scrivere.
    PERFORM script.fn_raise_primo_motivo_se_presente(
        'vendite', 'vendite.fn_clona_versione_listino',
        script.fn_check_versione_listino_clonabile(p_sorgente_id, p_valido_dal),
        'valido_dal',
        v_tx_id,
        jsonb_build_object('sorgente_id', p_sorgente_id,
                           'listino_id', v_listino_id,
                           'valido_dal', p_valido_dal));

    -- 3. La versione nuova: lo stato dal guard della nascita.
    INSERT INTO vendite.listini_versioni (listino_id, codice_versione, valido_dal, valido_al)
    VALUES (v_listino_id, p_codice_versione, p_valido_dal, p_valido_al)
    RETURNING id INTO v_nuova_id;

    -- 4. Le righe attive.
    INSERT INTO vendite.listini_righe (listino_versione_id, articolo_id, uom_id,
                                       prezzo, meta, attivo)
    SELECT v_nuova_id, r.articolo_id, r.uom_id, r.prezzo, r.meta, TRUE
      FROM vendite.listini_righe r
     WHERE r.listino_versione_id = p_sorgente_id
       AND r.attivo IS TRUE;
    GET DIAGNOSTICS v_righe = ROW_COUNT;

    -- 5. I componenti attivi, nel periodo comune alla riga di
    --    distinta e alla versione nuova; gli altri si saltano.
    SELECT count(*) INTO v_comp_sorg
      FROM vendite.listini_righe_componenti c
     WHERE c.listino_versione_id = p_sorgente_id
       AND c.attivo IS TRUE;

    INSERT INTO vendite.listini_righe_componenti (
           listino_versione_id, articolo_componente_id, articolo_padre_id,
           articolo_figlio_id, prezzo, iva_id, valido_dal, valido_al, attivo)
    SELECT v_nuova_id, c.articolo_componente_id, c.articolo_padre_id,
           c.articolo_figlio_id, c.prezzo, c.iva_id,
           GREATEST(ac.valido_dal, p_valido_dal),
           -- LEAST ignora i NULL: NULL solo se aperte entrambe.
           LEAST(ac.valido_al, p_valido_al),
           TRUE
      FROM vendite.listini_righe_componenti c
      JOIN catalogo.articoli_componenti ac ON ac.id = c.articolo_componente_id
     WHERE c.listino_versione_id = p_sorgente_id
       AND c.attivo IS TRUE
       AND GREATEST(ac.valido_dal, p_valido_dal)
           <= LEAST(COALESCE(ac.valido_al, 'infinity'::date),
                    COALESCE(p_valido_al,  'infinity'::date));
    GET DIAGNOSTICS v_componenti = ROW_COUNT;

    RETURN QUERY SELECT v_nuova_id, v_righe, v_componenti, v_comp_sorg - v_componenti;
END;
$function$

COMMENT ON FUNCTION vendite.fn_clona_versione_listino(p_sorgente_id bigint, p_codice_versione character varying, p_valido_dal date, p_valido_al date)
IS 'VERBO «Clona» di una versione di listino, in una transazione: la sorgente nel perimetro, da qualunque stato (SECURITY INVOKER, la RLS delle tabelle del listino; FOR KEY SHARE; non trovata E_VENDITE_LISTINO_VERSIONE_NOT_FOUND); prima cio'' che vieta, sul campo valido_dal (il primo motivo di script.fn_check_versione_listino_clonabile: E_LISTINO_VERSIONE_CLONE_PRIMA_DELLA_SORGENTE, decisione D2); poi la versione nuova dello stesso listino (codice, decorrenza e fine dai parametri; nasce BOZZA, attivo e meta dai default), le righe attive della sorgente (articolo, uom, prezzo, meta) e i componenti attivi con la validita'' ricalcolata come intersezione fra la riga di distinta e la versione nuova. Si saltano i componenti senza intersezione. Ritorna la versione nuova, righe e componenti copiati, componenti saltati. Prende il posto di listini_repository.clone_versione e della regola D2 del service. Il permesso d''area resta al backend. EXECUTE solo all''applicazione. Brief: brief-modello-documento-vendita §16.14 (C-1 = a, Tid 2026-10-29).';
```

</div>

---
{% include-markdown "signature-core.md" %}
