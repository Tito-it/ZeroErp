{% include-markdown "it/dbzero/script/manual/fn_check_articolo_riga.md" %}
# ⚙️ Funzione `fn_check_articolo_riga`

```sql
CREATE FUNCTION fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint DEFAULT NULL::bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto DEFAULT NULL::vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid DEFAULT NULL::uuid)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
DECLARE
    v_motivi jsonb;
BEGIN
    -- =========================================================
    -- Scopo:
    --   I motivi per cui l'articolo NON puo' stare in una riga del
    --   documento p_documento. '[]' = ammesso. Non solleva: lo fa
    --   il guard di tabella, che la CHIAMA (§12.5.2).
    --   E' la composizione di due meta': il lato documento
    --   (script.fn_articolo_riga_contesto, valida i parametri) e i
    --   motivi (script.fn_check_articolo_riga_su_contesto). Il
    --   picker chiama le due meta' da se', per leggere il
    --   documento una volta sola.
    -- Ritorna: array ORDINATO di
    --   {codice, reason, reason_key, dettaglio, valori}.
    -- =========================================================
    v_motivi := script.fn_check_articolo_riga_su_contesto(
        script.fn_articolo_riga_contesto(
            p_documento, p_documento_id, p_tipo_eccezione, p_articolo_padre_id),
        p_articolo_id,
        p_natura_vendita_id);
    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid)
IS 'Check pura (fn_check_*): i motivi, in ordine DICHIARATO, per cui un articolo non puo'' stare in una riga del documento p_documento (codice di config.tipi_entita: PREVENTIVO | ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO | LISTINO_VERSIONE | ARTICOLO | PROMO_ARTICOLO, altrimenti E_DOC_TIPO_NON_GESTITO). ''[]'' = ammesso; altrimenti {codice, reason, reason_key, dettaglio, valori}. Preventivo, ordine, bolla: 1. SOLO_COMPONENTE (E_ARTICOLO_SOLO_COMPONENTE); 2. KIT_SENZA_COMPONENTI (E_ARTICOLO_KIT_SENZA_COMPONENTI, rev 2026-10-14, 20261014-06, D-7: composito senza nessun componente attivo); 3. la natura secondo la destinazione (preventivo: la ricorrenza va in offerta, E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA; ordine e bolla: solo merce, E_RIGA_NATURA_NON_AMMESSA); la natura e'' quella della riga (p_natura_vendita_id, congelata) se c''e'', altrimenti quella dell''articolo. Offerta e contratto (rev 2026-10-13, 20261013-55, Lotto 3b): p_tipo_eccezione obbligatorio (E_PARAMETRO_INVALIDO). AGGIUNTA e OVERRIDE: 1. SOLO_COMPONENTE; 2. KIT_SENZA_COMPONENTI (D-7); 3. TIPOLOGIA_FUORI_UTILITY (composta da script.fn_check_riga_erogazione senza erogazione); 4. SENZA_EROGAZIONE (vendite.fn_articolo_erogazioni vuota, E_ARTICOLO_SENZA_EROGAZIONE); 5. il listino operativo (le righe di vendite.fn_espandi_listino_versione, standalone e bundle): AGGIUNTA gia'' in listino (E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO), OVERRIDE senza listino (E_RIGA_ECCEZIONE_SENZA_LISTINO) o fuori listino (E_RIGA_ECCEZIONE_FUORI_LISTINO, A-5). ESCLUSIONE: 1. FIGLIO_DI_BUNDLE (composta da script.fn_check_esclusione_articolo_documento); 2. senza listino o fuori listino (A-5). Versione di listino (rev 2026-10-13, 20261013-59, Lotto 3c; p_documento_id = la versione; la riga standalone di vendite.listini_righe): 1. SOLO_COMPONENTE; 2. composito (E_LISTINO_RIGA_COMPOSITO_VIETATO: nella versione sta coi componenti); 3. tipologia mancante (E_ARTICOLO_TIPOLOGIA_MANCANTE) o diversa da quella del listino (E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE). Distinta (ARTICOLO, p_articolo_padre_id obbligatorio, E_PARAMETRO_INVALIDO; la riga di catalogo.articoli_componenti): 1. componente uguale al padre (E_BOM_COMPONENTE_PADRE); 2. componente composito (E_BOM_COMPONENTE_COMPOSITO, D-4); 3. IVA diversa dal padre (E_BOM_IVA_DISCORDANTE); il solo componente qui e'' il caso normale. Promo (PROMO_ARTICOLO, rev 2026-10-14, Lotto 4, D-6; p_documento_id non letto): 1. solo componente (E_PROMO_ARTICOLO_SOLO_COMPONENTE). Rev 2026-10-14 (20261014-03, R-5): il corpo compone script.fn_articolo_riga_contesto (validazione e lato documento) e script.fn_check_articolo_riga_su_contesto (i motivi), che il picker catalogo.fn_articoli_ammessi chiama da se'' per leggere il documento una volta. ⚠️ Ponte A-8: i lettori del listino parlano ancora OFFERTA | CONTRATTO; la traduzione da OFFERTA_COMMERCIALE sta nel contesto e si ritira col giro BE/FE. Una sola check per tipo di riga (A-2): la chiamano i guard di tabella (script.trgfn_righe_guard_articolo_ammesso, catalogo.trgfn_articoli_componenti_guard_componente; sollevano il primo motivo) e, attraverso le due meta'', il picker; l''ordine dell''array e'' il contratto. Brief: brief-db-articoli-ammessi-per-documento (§8.6 A-2, A-5, D-1, D-2, D-3, D-4, D-6).';
```

</div>

---
{% include-markdown "signature-core.md" %}
