{% include-markdown "it/dbzero/script/manual/fn_resolve_emittente_sr_id.md" %}
# ⚙️ Funzione `fn_resolve_emittente_sr_id`

```sql
CREATE FUNCTION fn_resolve_emittente_sr_id(p_modo text, p_valore bigint)
```

> 🔐 **Sicurezza**: `SECURITY DEFINER` — gira con i privilegi dell'owner `zeroerp_owner`: GRANT e RLS sono i suoi, non quelli di chi la chiama.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.fn_resolve_emittente_sr_id(p_modo text, p_valore bigint)
 RETURNS bigint
 LANGUAGE plpgsql
 STABLE SECURITY DEFINER
 SET search_path TO 'pg_catalog', 'pg_temp'
AS $function$
DECLARE
    v_risultato anagrafiche.soggetti_ruoli.id%TYPE;
BEGIN
    -- =========================================================
    -- GENERATO da dbops.fn_genera_risolutori_emittente dal registro
    -- dbops.emittente_modi: non si modifica a mano, il migrate
    -- successivo lo riscriverebbe. Un modo nuovo e' una riga del
    -- seed 80_data/sql/dbops/emittente_modi.csv.
    --
    -- Scopo: il soggetto-ruolo dell'emittente di una riga, o NULL
    --   se il riferimento non porta a nessun emittente.
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
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM magazzino.assets t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'attivita_fatturabile' THEN
        SELECT t1.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.attivita_fatturabili t0
          JOIN vendite.commesse t1 ON t1.id = t0.commessa_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'commessa' THEN
        SELECT t0.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.commesse t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'commessa_attivita' THEN
        SELECT t1.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.commesse_attivita t0
          JOIN vendite.commesse t1 ON t1.id = t0.commessa_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'contabile' THEN
        SELECT t0.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM pagamenti.vendite_contabili t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'conto_bancario' THEN
        SELECT t0.soggetto_ruolo_id
          INTO v_risultato
          FROM anagrafiche.soggetti_ruoli_conti_bancari t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'contratto' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.contratti t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'contratto_riga' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.contratti_righe t0
          JOIN vendite.contratti t1 ON t1.id = t0.contratto_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ddt' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.ddt t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ddt_riga' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.ddt_righe t0
          JOIN vendite.ddt t1 ON t1.id = t0.ddt_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'documento_generato' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM documenti.documenti_generati t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ente_incasso' THEN
        SELECT t1.soggetto_ruolo_id
          INTO v_risultato
          FROM pagamenti.enti_incasso t0
          JOIN anagrafiche.soggetti_ruoli_conti_bancari t1 ON t1.id = t0.soggetto_ruolo_conto_bancario_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'evento_asset' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM magazzino.eventi_assets t0
          JOIN magazzino.assets t1 ON t1.id = t0.asset_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'fattura' THEN
        SELECT t0.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.fatture t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'fattura_sdi' THEN
        SELECT t1.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.fatture_sdi t0
          JOIN vendite.fatture t1 ON t1.id = t0.fattura_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'fiscale' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM anagrafiche.emittenti_fiscali t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'flusso' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM pratiche.flussi t0
          JOIN pratiche.pratiche t1 ON t1.id = t0.pratica_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'inventario' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM magazzino.inventari t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'listino' THEN
        SELECT t0.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.listini t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'listino_versione' THEN
        SELECT t1.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.listini_versioni t0
          JOIN vendite.listini t1 ON t1.id = t0.listino_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'lotto' THEN
        SELECT t0.emittente_soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.fatturazione_lotti t0
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'magazzino' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM magazzino.magazzini t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'movimento' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM magazzino.movimenti t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'offerta' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.offerte_commerciali t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'offerta_eccezione' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.offerte_commerciali_eccezioni t0
          JOIN vendite.offerte_commerciali t1 ON t1.id = t0.offerta_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ordine' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.ordini t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'ordine_riga' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.ordini_righe t0
          JOIN vendite.ordini t1 ON t1.id = t0.ordine_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'pratica' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM pratiche.pratiche t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'preventivo' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.preventivi t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'preventivo_riga' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.preventivi_righe t0
          JOIN vendite.preventivi t1 ON t1.id = t0.preventivo_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'reso' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.resi t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'reso_riga' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM vendite.resi_righe t0
          JOIN vendite.resi t1 ON t1.id = t0.reso_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'rettifica' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM magazzino.rettifiche t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSIF p_modo = 'soggetto_ruolo' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM anagrafiche.emittenti_fiscali t0
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t0.id
         WHERE t0.soggetto_ruolo_id = p_valore;
    ELSIF p_modo = 'trasferimento' THEN
        SELECT ef.soggetto_ruolo_id
          INTO v_risultato
          FROM magazzino.trasferimenti t0
          JOIN magazzino.magazzini t1 ON t1.id = t0.magazzino_id_from
          JOIN anagrafiche.emittenti_fiscali ef ON ef.id = t1.emittente_fiscale_id
         WHERE t0.id = p_valore;
    ELSE
        -- Un modo sconosciuto solleva: NULL vorrebbe dire «nessun
        -- padrone», e un refuso in un montaggio spegnerebbe il guard.
        PERFORM script.fn_log_and_raise_error(
            'database',
            'script.fn_resolve_emittente_sr_id',
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

COMMENT ON FUNCTION script.fn_resolve_emittente_sr_id(p_modo text, p_valore bigint)
IS 'Il gemello in convenzione soggetto-ruolo di script.fn_resolve_emittente_fiscale_id: il soggetto_ruolo_id dell''emittente raggiunto da p_valore secondo p_modo, o NULL. Stessi modi e stesse strade (le righe di dbops.emittente_modi), con un''altra risposta in fondo: la colonna del soggetto-ruolo, o quella dell''emittente fiscale della radice. Il corpo lo genera dbops.fn_genera_risolutori_emittente: non si modifica a mano. Il doppio binario PK/SR e'' una scelta dichiarata del progetto. Un modo sconosciuto solleva E_PARAMETRO_INVALIDO. SECURITY DEFINER per la stessa ragione del gemello; search_path bloccato. La chiama il giornale degli eventi (vendite.trgfn_event_log_deriva_scope).';
```

</div>

---
{% include-markdown "signature-core.md" %}
