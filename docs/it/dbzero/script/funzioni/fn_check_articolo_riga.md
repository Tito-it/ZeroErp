{% include-markdown "it/dbzero/script/manual/fn_check_articolo_riga.md" %}
# ⚙️ Funzione `fn_check_articolo_riga`

```sql
CREATE FUNCTION fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid, p_scelta_nuova boolean)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint DEFAULT NULL::bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto DEFAULT NULL::vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid DEFAULT NULL::uuid, p_scelta_nuova boolean DEFAULT false)
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
    --   p_scelta_nuova: la riga e' una scelta nuova (la calcola il
    --   guard dalla riga); solo allora conta il motivo OBSOLETO.
    -- Ritorna: array ORDINATO di
    --   {codice, reason, reason_key, dettaglio, valori}.
    -- =========================================================
    v_motivi := script.fn_check_articolo_riga_su_contesto(
        script.fn_articolo_riga_contesto(
            p_documento, p_documento_id, p_tipo_eccezione, p_articolo_padre_id),
        p_articolo_id,
        p_natura_vendita_id,
        p_scelta_nuova);
    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION script.fn_check_articolo_riga(p_documento text, p_documento_id bigint, p_articolo_id uuid, p_natura_vendita_id bigint, p_tipo_eccezione vendite.tipo_eccezione_contratto, p_articolo_padre_id uuid, p_scelta_nuova boolean)
IS 'Check pura (fn_check_*): i motivi, in ordine dichiarato, per cui un articolo non puo'' stare in una riga del documento p_documento (codice di config.tipi_entita: PREVENTIVO | ORDINE_VENDITA | DDT_VENDITA | OFFERTA_COMMERCIALE | CONTRATTO | LISTINO_VERSIONE | ARTICOLO | PROMO_ARTICOLO, altrimenti E_DOC_TIPO_NON_GESTITO). ''[]'' = ammesso; altrimenti {codice, reason, reason_key, dettaglio, valori}, e l''ordine dell''array e'' il contratto. Compone script.fn_articolo_riga_contesto (validazione e lato documento) e script.fn_check_articolo_riga_su_contesto (i motivi); il picker catalogo.fn_articoli_ammessi chiama le due meta'' da se'', per leggere il documento una volta. Con p_scelta_nuova = true il primo motivo, per ogni documento, e'' OBSOLETO (E_ARTICOLO_OBSOLETO: l''articolo e'' ritirato secondo script.fn_e_obsoleto); lo passano i guard di riga, che lo calcolano dalla riga (INSERT senza sorgente, o articolo cambiato). Preventivo, ordine, bolla: 1. SOLO_COMPONENTE (E_ARTICOLO_SOLO_COMPONENTE); 2. KIT_SENZA_COMPONENTI (E_ARTICOLO_KIT_SENZA_COMPONENTI: composito senza una distinta da oggi in poi, catalogo.fn_articolo_padre_di_distinta_da_oggi; la distinta alla data del documento la giudica l''init dei componenti, E_DOC_COMPOSITO_BOM_VUOTA); 3. la natura secondo la destinazione (preventivo: la ricorrenza va in offerta, E_VENDITA_RIGA_RICORRENTE_USA_OFFERTA; ordine e bolla: merce o articolo-onere secondo script.fn_natura_e_merce e catalogo.articoli.causale_onere_id, altrimenti E_RIGA_NATURA_NON_AMMESSA); la natura e'' quella della riga (p_natura_vendita_id, congelata) se c''e'', altrimenti quella dell''articolo. Offerta e contratto: p_tipo_eccezione obbligatorio (E_PARAMETRO_INVALIDO). AGGIUNTA e OVERRIDE: 1. SOLO_COMPONENTE; 2. KIT_SENZA_COMPONENTI; 3. TIPOLOGIA_FUORI_UTILITY (script.fn_check_riga_erogazione senza erogazione); 4. SENZA_EROGAZIONE (vendite.fn_articolo_erogazioni vuota, E_ARTICOLO_SENZA_EROGAZIONE); 5. il listino operativo (le righe di vendite.fn_espandi_listino_versione, standalone e bundle): AGGIUNTA gia'' in listino (E_CONTRATTO_AGGIUNTA_GIA_IN_LISTINO), OVERRIDE senza listino (E_RIGA_ECCEZIONE_SENZA_LISTINO) o fuori listino (E_RIGA_ECCEZIONE_FUORI_LISTINO). ESCLUSIONE: 1. FIGLIO_DI_BUNDLE (script.fn_check_esclusione_articolo_documento); 2. senza listino o fuori listino. Versione di listino (p_documento_id = la versione; la riga standalone di vendite.listini_righe): 1. SOLO_COMPONENTE; 2. composito (E_LISTINO_RIGA_COMPOSITO_VIETATO: nella versione sta coi componenti); 3. tipologia mancante (E_ARTICOLO_TIPOLOGIA_MANCANTE) o diversa da quella del listino (E_ARTICOLO_TIPOLOGIA_INCOMPATIBILE). Distinta (ARTICOLO, la riga di catalogo.articoli_componenti; p_articolo_padre_id obbligatorio, E_PARAMETRO_INVALIDO, e composito, E_ARTICOLO_NON_COMPOSITO): 1. componente uguale al padre (E_BOM_COMPONENTE_PADRE); 2. componente composito (E_BOM_COMPONENTE_COMPOSITO); 3. IVA diversa dal padre (E_BOM_IVA_DISCORDANTE); il solo componente qui e'' il caso normale. Promo (PROMO_ARTICOLO; p_documento_id non letto): 1. solo componente (E_PROMO_ARTICOLO_SOLO_COMPONENTE). Una sola check per tipo di riga: la chiamano i guard di tabella (script.trgfn_righe_guard_articolo_ammesso, catalogo.trgfn_articoli_componenti_guard_componente; sollevano il primo motivo) e, attraverso le due meta'', il picker.';
```

</div>

---
{% include-markdown "signature-core.md" %}
