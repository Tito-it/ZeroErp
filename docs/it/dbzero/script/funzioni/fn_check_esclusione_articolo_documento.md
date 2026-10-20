{% include-markdown "it/dbzero/script/manual/fn_check_esclusione_articolo_documento.md" %}
# ⚙️ Funzione `fn_check_esclusione_articolo_documento`

```sql
CREATE FUNCTION fn_check_esclusione_articolo_documento(p_documento character varying, p_documento_id bigint, p_articolo_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_esclusione_articolo_documento(p_documento character varying, p_documento_id bigint, p_articolo_id uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$

-- Scopo: elencare i motivi per cui un articolo NON si puo' escludere
--   da un contratto o da un'offerta (p_documento = CONTRATTO |
--   OFFERTA_COMMERCIALE). Funzione PURA (fn_check_*): nessun raise di dominio,
--   nessuna scrittura.
-- Consumatori: il guard script.trgfn_righe_guard_esclusione_figlio_bundle
--   (solleva il PRIMO motivo) e vendite.fn_documento_righe_preview
--   (spegne «Escludi» sulla riga e dice perche').
-- Ritorna: [] se ammesso; altrimenti array ORDINATO di
--   {codice, reason, reason_key, dettaglio, valori}.
-- ⚠️ p_documento e' il codice della sorgente (CONTRATTO |
--   OFFERTA_COMMERCIALE), ancorato a config.sorgenti.codice_interno
--   (grammatica unica dei tipi di documento, lotto 1). p_documento_id
--   nudo DICHIARATO: un id polimorfo (due testate).
DECLARE
    v_motivi              jsonb := '[]'::jsonb;
    v_listino_id          vendite.listini.id%TYPE;
    v_listino_versione_id vendite.listini_versioni.id%TYPE;
    v_e_figlio_bundle     boolean := false;
BEGIN
    SELECT lo.listino_id, lo.listino_versione_id
      INTO v_listino_id, v_listino_versione_id
      FROM vendite.fn_documento_listino_operativo(p_documento, p_documento_id) lo;

    -- Nessuna versione operativa (nessun listino, documento che non
    -- c'e' o non si vede): nessun bundle da cui escludere. Chi
    -- scrive passa comunque dalla policy e dalle FK.
    IF v_listino_versione_id IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT EXISTS (
        SELECT 1
          FROM vendite.listini_righe_componenti lrc
         WHERE lrc.listino_versione_id = v_listino_versione_id
           AND lrc.articolo_figlio_id  = p_articolo_id
           AND lrc.attivo              = TRUE
           AND lrc.validita           @> (SELECT script.fn_data_operativa())
    ) INTO v_e_figlio_bundle;

    -- ---- MOTIVO 1 — e' un componente di un bundle ------------------
    -- Il bundle si vende come unita': si esclude il padre, mai il
    -- singolo figlio. `valori` = l'articolo, il VARIADIC del messaggio.
    IF v_e_figlio_bundle THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',     'E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA',
            'reason',     'FIGLIO_DI_BUNDLE',
            'reason_key', 'vendite.contratti.escludi_blocco.figlio_di_bundle',
            'dettaglio',  jsonb_build_object(
                              'documento',           p_documento,
                              'documento_id',        p_documento_id,
                              'articolo_id',         p_articolo_id,
                              'listino_id',          v_listino_id,
                              'listino_versione_id', v_listino_versione_id),
            'valori',     jsonb_build_array(p_articolo_id::text));
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_esclusione_articolo_documento(p_documento character varying, p_documento_id bigint, p_articolo_id uuid)
IS 'Check pura (fn_check_*): i motivi per cui un articolo NON si puo'' escludere da un contratto o da un''offerta (p_documento = CONTRATTO | OFFERTA). Oggi un motivo: l''articolo e'' componente (articolo_figlio_id) di un bundle della versione operativa del listino del documento (vendite.fn_documento_listino_operativo) — il bundle si vende come unita'', si esclude il padre (E_CONTRATTO_ESCLUSIONE_FIGLIO_BUNDLE_VIETATA, reason FIGLIO_DI_BUNDLE). [] = ammesso; nessuna versione operativa = []. Consumatori: il guard script.trgfn_righe_guard_esclusione_figlio_bundle (solleva il primo motivo) e vendite.fn_documento_righe_preview (escludi_blocco_codice): pulsante ed errore non divergono. Prende il posto di script.fn_check_esclusione_articolo_contratto (ritirata nello stesso giro), che valeva per il solo contratto: fn_push_offerta_a_contratto copia le righe 1:1 e la regola deve valere ai due capi. Nasce il 2026-10-04, brief-db-righe-esclusione-solo-non-si-vende (R4, R5c). ⭐ rev 2026-10-19 (20261019-20, brief-db-grammatica-unica-documenti lotto 1, G-1 di Tid): il documento si nomina col codice della sorgente, CONTRATTO | OFFERTA_COMMERCIALE (era OFFERTA); dove sopra si legge OFFERTA come selettore, oggi e'' OFFERTA_COMMERCIALE. p_documento ancorato a config.sorgenti.codice_interno%TYPE: la firma passa da text a character varying (DROP + CREATE, nessun dipendente registrato).';
```

</div>

---
{% include-markdown "signature-core.md" %}
