# ⚙️ Funzione `fn_documento_riga_erogazioni`

```sql
CREATE FUNCTION fn_documento_riga_erogazioni(p_documento character varying, p_documento_id bigint, p_articolo_id uuid)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_documento_riga_erogazioni(p_documento character varying, p_documento_id bigint, p_articolo_id uuid)
 RETURNS TABLE(tipo_erogazione character varying, fonte_quantita_attesa character varying, e_default boolean, generazione_canone character varying, origine text)
 LANGUAGE plpgsql
 STABLE
AS $function$

-- ⚠️ p_documento ancorato a config.sorgenti.codice_interno (CONTRATTO |
--   OFFERTA_COMMERCIALE, grammatica unica, lotto 1); p_documento_id nudo
--   DICHIARATO (id polimorfo).
-- Scopo: per il form delle righe (B-R4), le combinazioni (erogazione, fonte)
--   che una riga con questo articolo puo' avere su questo documento, con
--   quella che la riga erediterebbe (e_default). Le stesse righe di
--   vendite.fn_articolo_erogazioni, che l'eredita' e il guard leggono: il form
--   preseleziona cio' che il DB scriverebbe e propone solo cio' che il DB
--   accetterebbe.
-- Zero righe se l'articolo ha una tipologia che la utility del documento
--   non prevede: per quell'articolo nessuna combinazione e' ammessa (il guard
--   lo dice col campo articolo_id). Zero righe anche se documento o articolo
--   non ci sono o non si vedono.
-- Ordine: `ordine` di vendite.fn_articolo_erogazioni (20261007-66), lo stesso
--   che usa l'eredita'. Il default in testa, poi per erogazione e per
--   fonte. Il form propone la prima fonte di un'erogazione e coincide col DB
--   per costruzione. (Rev 2026-10-21, §I.1: il criterio «DERIVATA_COMPONENTI
--   per ultima» e' uscito con la fonte, ritirata.)
DECLARE
    v_motivi jsonb;
BEGIN
    -- Lo stesso predicato del guard, sulla sola parte che non dipende dalla
    -- combinazione (erogazione e fonte NULL: il motivo 2 tace).
    v_motivi := script.fn_check_riga_erogazione(
        p_documento, p_documento_id, p_articolo_id,
        'AGGIUNTA'::vendite.tipo_eccezione_contratto, NULL, NULL);

    IF jsonb_array_length(v_motivi) > 0 THEN
        RETURN;
    END IF;

    RETURN QUERY
    SELECT ae.tipo_erogazione, ae.fonte_quantita_attesa, ae.e_default,
           ae.generazione_canone, ae.origine
      FROM vendite.fn_articolo_erogazioni(p_articolo_id) ae
     -- L'ordine del BB (§D.4 punto 1): la prima fonte di un'erogazione e'
     -- quella che l'eredita' scriverebbe.
     ORDER BY ae.ordine;
END;
$function$

COMMENT ON FUNCTION vendite.fn_documento_riga_erogazioni(p_documento character varying, p_documento_id bigint, p_articolo_id uuid)
IS 'Lettura per il form delle righe di contratto (p_documento = CONTRATTO) e di offerta (OFFERTA), richiesta B-R4: le combinazioni (tipo_erogazione, fonte_quantita_attesa) che una riga con questo articolo può avere su questo documento, con e_default su quella che la riga erediterebbe, la generazione_canone da proporre sulle CANONE e l''origine. Sono le righe di vendite.fn_articolo_erogazioni, la stessa sede che leggono l''eredità e il guard: il form preseleziona ciò che il DB scriverebbe e propone solo ciò che accetterebbe. Prende il posto di fontiQuantitaErogazione.js nel frontend e della copia Python della matrice. Zero righe se l''articolo ha una tipologia che la utility del documento non prevede (script.fn_check_riga_erogazione, motivo TIPOLOGIA_FUORI_UTILITY) o se documento o articolo non si vedono. Ordinate come le ordina vendite.fn_articolo_erogazioni (colonna ordine), lo stesso ordine dell''eredità: il default in testa, poi per erogazione e per fonte, quindi la prima fonte di un''erogazione è quella che il DB scriverebbe. Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §C.7 (B4); ordine dal 20261007-68 (§D.4 punto 1). ⭐ rev 2026-10-19 (20261019-24, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato). Rev 2026-10-21 (20261021-49, brief-db-offerta-emissione-ed-erogazione §I.1): commenti senza DERIVATA_COMPONENTI, ritirata.';
```

</div>

---
{% include-markdown "signature-core.md" %}
