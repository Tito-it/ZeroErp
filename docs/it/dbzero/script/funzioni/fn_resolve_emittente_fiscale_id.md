{% include-markdown "it/dbzero/script/manual/fn_resolve_emittente_fiscale_id.md" %}
# ⚙️ Funzione `fn_resolve_emittente_fiscale_id`

```sql
CREATE FUNCTION fn_resolve_emittente_fiscale_id(p_modo text, p_valore bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_emittente_fiscale_id(p_modo text, p_valore bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_risultato anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- =========================================================
    -- GENERATO da dbops.fn_genera_risolutori_emittente dal registro
    -- dbops.emittente_modi: non si modifica a mano, il migrate
    -- successivo lo riscriverebbe. Un modo nuovo e' una riga del
    -- seed 80_data/sql/dbops/emittente_modi.csv.
    --
    -- Scopo: l'id dell'emittente fiscale di una riga, o NULL se il
    --   riferimento non porta a nessun emittente.
    --
    -- SECURITY DEFINER: le strade passano da tabelle con la ROW
    --   SECURITY accesa, e per chi e' fuori perimetro la riga non
    --   c'e': «non la vedo» non e' «non esiste». Dipende dalla RLS
    --   abilitata e non forzata (il proprietario la salta).
    -- =========================================================
    IF p_valore IS NULL THEN
        RETURN NULL;
    END IF;

    IF p_modo = 'asset' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM magazzino.assets t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'attivita_fatturabile' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.attivita_fatturabili t0
          JOIN vendite.commesse t1 ON t1.id = t0.commessa_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t1.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'commessa' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.commesse t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t0.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'commessa_attivita' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.commesse_attivita t0
          JOIN vendite.commesse t1 ON t1.id = t0.commessa_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t1.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'contabile' THEN
        SELECT ef.id
          INTO v_risultato
          FROM pagamenti.vendite_contabili t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t0.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'conto_bancario' THEN
        SELECT ef.id
          INTO v_risultato
          FROM anagrafiche.soggetti_ruoli_conti_bancari t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t0.soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'contratto' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.contratti t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'contratto_riga' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.contratti_righe t0
          JOIN vendite.contratti t1 ON t1.id = t0.contratto_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ddt' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.ddt t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ddt_riga' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.ddt_righe t0
          JOIN vendite.ddt t1 ON t1.id = t0.ddt_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'documento_generato' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM documenti.documenti_generati t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ente_incasso' THEN
        SELECT ef.id
          INTO v_risultato
          FROM pagamenti.enti_incasso t0
          JOIN anagrafiche.soggetti_ruoli_conti_bancari t1 ON t1.id = t0.soggetto_ruolo_conto_bancario_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t1.soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'evento_asset' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM magazzino.eventi_assets t0
          JOIN magazzino.assets t1 ON t1.id = t0.asset_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'fattura' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.fatture t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t0.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'fattura_sdi' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.fatture_sdi t0
          JOIN vendite.fatture t1 ON t1.id = t0.fattura_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t1.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'fiscale' THEN
        SELECT t0.id
          INTO v_risultato
          FROM anagrafiche.emittenti_fiscali t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'flusso' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM pratiche.flussi t0
          JOIN pratiche.pratiche t1 ON t1.id = t0.pratica_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'inventario' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM magazzino.inventari t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'listino' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.listini t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t0.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'listino_versione' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.listini_versioni t0
          JOIN vendite.listini t1 ON t1.id = t0.listino_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t1.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'lotto' THEN
        SELECT ef.id
          INTO v_risultato
          FROM vendite.fatturazione_lotti t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.soggetto_ruolo_id = t0.emittente_soggetto_ruolo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'magazzino' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM magazzino.magazzini t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'movimento' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM magazzino.movimenti t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'offerta' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.offerte_commerciali t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'offerta_eccezione' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.offerte_commerciali_eccezioni t0
          JOIN vendite.offerte_commerciali t1 ON t1.id = t0.offerta_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ordine' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.ordini t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ordine_riga' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.ordini_righe t0
          JOIN vendite.ordini t1 ON t1.id = t0.ordine_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'pratica' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM pratiche.pratiche t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'preventivo' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.preventivi t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'preventivo_riga' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.preventivi_righe t0
          JOIN vendite.preventivi t1 ON t1.id = t0.preventivo_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'reso' THEN
        SELECT t0.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.resi t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'reso_riga' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM vendite.resi_righe t0
          JOIN vendite.resi t1 ON t1.id = t0.reso_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'rettifica' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM magazzino.rettifiche t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'soggetto_ruolo' THEN
        SELECT t0.id
          INTO v_risultato
          FROM anagrafiche.emittenti_fiscali t0
         WHERE t0.soggetto_ruolo_id = p_valore;
    ELSIF p_modo = 'trasferimento' THEN
        SELECT t1.emittente_fiscale_id
          INTO v_risultato
          FROM magazzino.trasferimenti t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id_from
         WHERE t0.id = p_valore;
    ELSE
        -- Un modo sconosciuto solleva: NULL vorrebbe dire «nessun
        -- padrone», e un refuso in un montaggio spegnerebbe il guard.
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_resolve_emittente_fiscale_id',
            'E_PARAMETRO_INVALIDO',
            jsonb_build_object(
                'detail', 'Modo di risoluzione sconosciuto',
                'modo',   p_modo,
                'valore', p_valore
            ),
            NULL::uuid,
            format(
                'il modo di risoluzione dell''emittente «%s» non esiste: sono ammessi %s',
                p_modo,
                'asset, attivita_fatturabile, commessa, commessa_attivita, contabile, conto_bancario, contratto, contratto_riga, ddt, ddt_riga, documento_generato, ente_incasso, evento_asset, fattura, fattura_sdi, fiscale, flusso, inventario, listino, listino_versione, lotto, magazzino, movimento, offerta, offerta_eccezione, ordine, ordine_riga, pratica, preventivo, preventivo_riga, reso, reso_riga, rettifica, soggetto_ruolo, trasferimento'
            )
        );
    END IF;

    RETURN v_risultato;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_emittente_fiscale_id(p_modo text, p_valore bigint)
IS 'Dice DI CHI E'' una riga: l''id dell''emittente fiscale raggiunto da p_valore secondo p_modo, o NULL se il riferimento non porta a nessun emittente («nessun padrone»: il guard lascia passare). I modi e le loro strade sono le righe di dbops.emittente_modi, e il corpo lo genera dbops.fn_genera_risolutori_emittente: non si modifica a mano. Un modo sconosciuto solleva E_PARAMETRO_INVALIDO, non risponde NULL. SECURITY DEFINER del proprietario, perche'' le strade passano da tabelle sotto row security e un chiamante fuori perimetro non troverebbe l''emittente; search_path bloccato. Risponde solo alla domanda di fatto: il permesso e'' di script.fn_check_user_emittente_scope. La chiamano le policy ef_whitelist, gli adattatori script.fn_scope_ef_whitelist_via_* e il guard di scrittura script.trgfn_guard_emittente_scope.';
```

</div>

---
{% include-markdown "signature-core.md" %}
