{% include-markdown "it/dbzero/vendite/manual/fn_lookup_registro_documento.md" %}
# ⚙️ Funzione `fn_lookup_registro_documento`

```sql
CREATE FUNCTION fn_lookup_registro_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_lookup_registro_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer DEFAULT NULL::integer)
 RETURNS TABLE(registro_id bigint, serie character varying)
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_registro vendite.registri_fatturazione.id%TYPE;
    v_serie    vendite.registri_fatturazione.serie_default%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   CERCARE il registro su cui si numera un documento di
    --   questa famiglia, e basta. Chi non trova risponde NULL:
    --   qui non si solleva mai.
    --
    -- ⛔ Il guard di parametro e il raise NON stanno qui: sono
    --   in vendite.fn_get_registro_documento, l'involucro per
    --   chi SCRIVE.
    -- =========================================================

    -- ⚠️ Fallback a DUE livelli, e solo sull'UTILITY:
    --     1) il registro della mia utility
    --     2) il registro «per tutte le utility»
    --   ⛔ Sull'emittente NON c'e' fallback: il registro «di
    --     nessuno» e' stato chiuso dal C1-2, e riaprirlo qui
    --     rimetterebbe due partite IVA sulla stessa serie.
    -- ⚠️ Solo registri ATTIVI: un registro spento e' una
    --   configurazione ritirata, non una da ripescare.
    -- ℹ️ Con un parametro a NULL il predicato non corrisponde a
    --   niente e la risposta e' NULL: e' voluto, non un caso da
    --   intercettare.
    SELECT r.id, r.serie_default
      INTO v_registro, v_serie
      FROM vendite.registri_fatturazione r
     WHERE r.famiglia_documento           = p_famiglia_documento
       AND r.emittente_soggetto_ruolo_id  = p_emittente_soggetto_ruolo_id
       AND r.attivo IS TRUE
       AND (r.utility_id IS NULL OR r.utility_id = p_utility_id)
     ORDER BY
         CASE
             WHEN r.utility_id = p_utility_id THEN 1
             WHEN r.utility_id IS NULL        THEN 2
             ELSE 9
         END, r.id
     LIMIT 1;

    -- ⭐ UNA riga sempre, anche tutta a NULL: e' il contratto
    --   del lettore, e permette al chiamante di distinguere
    --   «non trovato» da «non chiamato».
    RETURN QUERY SELECT v_registro, v_serie;
END;
$function$

COMMENT ON FUNCTION vendite.fn_lookup_registro_documento(p_famiglia_documento character varying, p_emittente_soggetto_ruolo_id bigint, p_utility_id integer)
IS 'CERCA il registro su cui si numera un documento di una data FAMIGLIA (DDT, ORDINE, COMMESSA, RESO) per un dato emittente, con l''utility a raffinare — e NON solleva mai. E'' il lettore puro di cui vendite.fn_get_registro_documento e'' l''involucro: stessa coppia, e stessa ragione, di vendite.fn_lookup_registro_id / vendite.fn_get_registro_id. ⛔ NON passa da vendite.tipi_doc_fiscale_registri, e non e'' una scorciatoia: quella mappa parte dal TIPO DOCUMENTO FISCALE e dalla NATURA, che DDT, ordine, commessa e reso non hanno — vendite.ddt non ha proprio la colonna del tipo. Per queste famiglie la chiave e'' «famiglia + emittente (+ utility)», e una riga di registro per emittente basta: non c''e'' niente da mappare. Le due risoluzioni restano quindi DUE, e partono da chiavi diverse verso la stessa tabella; unificarle vorrebbe dire inventare un tipo documento fiscale per il DDT, cioe'' allargare un vocabolario che 83 file di 20_code leggono come chiuso. ⚠️ Il fallback e'' a DUE livelli e SOLO sull''utility (la mia → quella per tutte): sull''EMITTENTE non c''e'', ed e'' la differenza che conta — il registro «di nessuno» e'' stato chiuso dal NOT NULL del 2026-08-30 (C1-2), e ricrearne uno per questa strada riaprirebbe dalla finestra il difetto chiuso dalla porta, rimettendo due partite IVA sulla stessa serie. ⚠️ Solo registri ATTIVI: uno spento e'' una configurazione ritirata, non una da ripescare. ⚠️ La SERIE e'' il serie_default del registro ed esce grezza: senza mappa non esiste nessun override di serie, e NULL significa «nessuna serie» — la stessa convenzione che vendite.fn_assign_numero_fattura risolve con il suo COALESCE. ℹ️ La famiglia FATTURA non e'' rifiutata qui: il guard sta nell''involucro, dove stanno tutti i guard di questa coppia — un lettore che giudicasse i parametri smetterebbe di essere un lettore, e la vista che lo consuma vuole una risposta, non un verdetto. ℹ️ Ritorna SEMPRE una riga, anche tutta a NULL. STABLE: legge una sola tabella. Piano: brief-db-registri-di-numerazione-emittente-e-trasloco, C2-4.';
```

</div>

---
{% include-markdown "signature-core.md" %}
