{% include-markdown "it/dbzero/script/manual/fn_resolve_emittente_fiscale_id.md" %}
# ⚙️ Funzione `fn_resolve_emittente_fiscale_id`

```sql
CREATE FUNCTION fn_resolve_emittente_fiscale_id(p_modo text, p_valore bigint)
```

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
    v_emittente_fiscale_id anagrafiche.emittenti_fiscali.id%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Dire DI CHI E' una riga, e nient'altro. Risponde un id di
    --   emittente fiscale, o NULL se il riferimento non porta a
    --   nessun emittente.
    --
    -- ⭐ Perche' SECURITY DEFINER (ed e' il punto):
    --   il chiamante e' un guard di scrittura, che gira con i
    --   permessi di chi scrive. Due delle catene passano da
    --   tabelle con la ROW SECURITY ACCESA (vendite.fatture,
    --   pagamenti.vendite_contabili): letta da un utente fuori
    --   perimetro, la riga NON C'E' — e un guard che non trova
    --   l'emittente lascia passare. Il guard si spegnerebbe
    --   esattamente nel caso che esiste per coprire.
    --   La domanda di FATTO («di chi e'») e la domanda di
    --   PERMESSO («posso scriverci») sono due domande diverse:
    --   qui si risponde solo alla prima, la seconda resta a
    --   script.fn_check_user_emittente_scope.
    --
    -- ⚠️ Dipende dal fatto che le tabelle abbiano la RLS
    --   ABILITATA ma NON FORZATA: il proprietario la salta. Con
    --   un FORCE ROW LEVEL SECURITY questa funzione tornerebbe a
    --   leggere filtrata e andrebbe rivista. Stessa nota su
    --   script.fn_check_scadenza_di_fattura.
    --
    -- ⚠️ search_path bloccato: una SECURITY DEFINER senza
    --   search_path fisso e' un'iniezione che aspetta.
    -- =========================================================

    IF p_valore IS NULL THEN
        RETURN NULL;
    END IF;

    IF p_modo = 'fiscale' THEN
        -- Convenzione PK: la colonna E' gia' emittente_fiscale_id.
        -- Si verifica comunque che esista: un id che non c'e' non
        -- deve valere come «emittente noto».
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.id = p_valore;

    ELSIF p_modo = 'soggetto_ruolo' THEN
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM anagrafiche.emittenti_fiscali ef
         WHERE ef.soggetto_ruolo_id = p_valore;

    ELSIF p_modo = 'fattura' THEN
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.fatture f
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
         WHERE f.id = p_valore;

    ELSIF p_modo = 'ente_incasso' THEN
        -- ⭐ D5: il canale conosce il CONTO su cui atterra il suo
        --   denaro, e quel conto ha un solo padrone (lo garantisce
        --   ex_src_bancari_conto_incasso_un_solo_soggetto).
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM pagamenti.enti_incasso e
          JOIN anagrafiche.soggetti_ruoli_conti_bancari src
            ON src.id = e.soggetto_ruolo_conto_bancario_id
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = src.soggetto_ruolo_id
         WHERE e.id = p_valore;

    ELSIF p_modo = 'contabile' THEN
        -- ⭐ Rev 2026-09-15 (brief distinta-numerata-sul-registro, D3):
        --   la distinta SA di chi e'. Una lettura, non tre JOIN per
        --   canale — e una distinta INTERNA (fondo fattura,
        --   compensazione) non risolve piu' NULL: e' del suo
        --   emittente, come il lotto o l'atto da cui nasce.
        --   Fino a oggi rispondeva NULL apposta («non e' il canale di
        --   nessuno»), e la testata era visibile a tutti: quel ramo
        --   non descrive piu' il modello.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM pagamenti.vendite_contabili c
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
         WHERE c.id = p_valore;

    ELSIF p_modo = 'listino' THEN
        -- ⭐ DB-4: una VERSIONE di listino non porta l'emittente — lo porta il
        --   listino padre, con `emittente_soggetto_ruolo_id` NOT NULL. Un salto
        --   solo, come il modo 'fattura'.
        -- ⚠️ Rev 2026-10-18: p_valore qui e' l'id del LISTINO (il chiamante
        --   risolve gia' la versione). Dalla VERSIONE c'e' il modo
        --   'listino_versione'.
        -- ⚠️ JOIN interna: un listino il cui soggetto_ruolo non e' (piu') un
        --   emittente risolve a NULL, cioe' «nessun padrone». Oggi non ne
        --   esistono (misurato: zero orfani il 2026-09-05), ed e' il
        --   comportamento giusto se ne nascesse uno — non si inventa un
        --   padrone.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.listini l
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = l.emittente_soggetto_ruolo_id
         WHERE l.id = p_valore;

    ELSIF p_modo = 'magazzino' THEN
        -- ⭐ Rev 2026-09-18 (brief magazzino Lotto 2, D-L2-b / M-6): un
        --   MAGAZZINO e' di un emittente (magazzini.emittente_fiscale_id
        --   NOT NULL, Lotto 1 D-L1-e): un salto solo, come 'fattura'.
        --   Serve al guard di scope montato su movimenti,
        --   movimenti_attesi e valore_giacenza, cioe' dove la primitiva
        --   DEFINER scavalca la RLS: il perimetro si rimette QUI, non con
        --   un controllo scritto a mano nella primitiva. Si verifica che
        --   esista: un id che non c'e' vale «nessun padrone», e a fermarlo
        --   provvede la primitiva (E_MAG_MAGAZZINO_NON_VALIDO) o la FK.
        SELECT m.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM magazzino.magazzini m
         WHERE m.id = p_valore;

    -- ⭐ Rev 2026-10-18 (20261018-31, D-3b-2 giro 1b): i modi dei
    --   documenti di vendita e delle loro righe. Le policy ef_whitelist
    --   delle tabelle senza colonna emittente lo chiedono QUI, per riga,
    --   e confrontano col perimetro calcolato una volta per istruzione
    --   (script.fn_scope_ef_perimetro). DEFINER e' il punto anche per
    --   loro: letta sotto la RLS del padre, ogni riga rieseguiva la
    --   policy del padre. Gli adattatori fn_scope_ef_whitelist_via_*
    --   chiedono qui la stessa cosa (20261018-32): la strada documento ->
    --   emittente e' scritta UNA volta.
    --   Le catene sono una lettura per chiave; le colonne di collegamento
    --   sono tutte NOT NULL.
    ELSIF p_modo = 'ddt' THEN
        -- Il DDT porta l'emittente.
        SELECT d.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.ddt d
         WHERE d.id = p_valore;
    ELSIF p_modo = 'ddt_riga' THEN
        -- La riga di DDT: dal DDT.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.ddt_righe r
          JOIN vendite.ddt p ON p.id = r.ddt_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'ordine' THEN
        -- L'ordine porta l'emittente.
        SELECT o.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.ordini o
         WHERE o.id = p_valore;
    ELSIF p_modo = 'ordine_riga' THEN
        -- La riga d'ordine: dall'ordine.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.ordini_righe r
          JOIN vendite.ordini p ON p.id = r.ordine_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'preventivo' THEN
        -- Il preventivo porta l'emittente.
        SELECT pv.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.preventivi pv
         WHERE pv.id = p_valore;
    ELSIF p_modo = 'preventivo_riga' THEN
        -- La riga di preventivo: dal preventivo.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.preventivi_righe r
          JOIN vendite.preventivi p ON p.id = r.preventivo_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'offerta' THEN
        -- L'offerta porta l'emittente.
        SELECT oc.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.offerte_commerciali oc
         WHERE oc.id = p_valore;
    ELSIF p_modo = 'offerta_eccezione' THEN
        -- L'eccezione d'offerta: dall'offerta.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.offerte_commerciali_eccezioni r
          JOIN vendite.offerte_commerciali p ON p.id = r.offerta_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'contratto' THEN
        -- Il contratto porta l'emittente.
        SELECT k.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.contratti k
         WHERE k.id = p_valore;
    ELSIF p_modo = 'contratto_riga' THEN
        -- La riga di contratto: dal contratto.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.contratti_righe r
          JOIN vendite.contratti p ON p.id = r.contratto_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'reso' THEN
        -- Il reso porta l'emittente.
        SELECT rs.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.resi rs
         WHERE rs.id = p_valore;
    ELSIF p_modo = 'reso_riga' THEN
        -- La riga di reso: dal reso.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM vendite.resi_righe r
          JOIN vendite.resi p ON p.id = r.reso_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'commessa' THEN
        -- La commessa porta il ruolo emittente: un salto, come 'fattura'.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.commesse c
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
         WHERE c.id = p_valore;
    ELSIF p_modo = 'commessa_attivita' THEN
        -- L'attivita' di commessa: dalla commessa.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.commesse_attivita ca
          JOIN vendite.commesse c ON c.id = ca.commessa_id
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
         WHERE ca.id = p_valore;
    ELSIF p_modo = 'attivita_fatturabile' THEN
        -- L'attivita' fatturabile: dalla sua commessa.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.attivita_fatturabili af
          JOIN vendite.commesse c ON c.id = af.commessa_id
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = c.emittente_soggetto_ruolo_id
         WHERE af.id = p_valore;
    ELSIF p_modo = 'lotto' THEN
        -- Il lotto di fatturazione porta il ruolo emittente.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.fatturazione_lotti l
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = l.emittente_soggetto_ruolo_id
         WHERE l.id = p_valore;
    ELSIF p_modo = 'fattura_sdi' THEN
        -- La pratica SDI: dalla sua fattura.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.fatture_sdi s
          JOIN vendite.fatture f ON f.id = s.fattura_id
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = f.emittente_soggetto_ruolo_id
         WHERE s.id = p_valore;
    ELSIF p_modo = 'listino_versione' THEN
        -- La versione di listino: dal listino padre.
        SELECT ef.id
          INTO v_emittente_fiscale_id
          FROM vendite.listini_versioni lv
          JOIN vendite.listini l ON l.id = lv.listino_id
          JOIN anagrafiche.emittenti_fiscali ef
            ON ef.soggetto_ruolo_id = l.emittente_soggetto_ruolo_id
         WHERE lv.id = p_valore;
    -- ⭐ Rev 2026-10-18 (20261018-48, D-3b-2 ondata 2): i modi di
    --   magazzino, pratiche e documenti generati, per le stesse ragioni
    --   dei documenti di vendita (20261018-31): le policy ef_whitelist
    --   delle tabelle senza colonna emittente lo chiedono qui per riga, e
    --   gli adattatori via_* chiedono qui (20261018-49).
    ELSIF p_modo = 'asset' THEN
        -- L'asset porta l'emittente.
        SELECT a.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM magazzino.assets a
         WHERE a.id = p_valore;
    ELSIF p_modo = 'evento_asset' THEN
        -- L'evento di un asset: dall'asset.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM magazzino.eventi_assets r
          JOIN magazzino.assets p ON p.id = r.asset_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'inventario' THEN
        -- L'inventario: dal suo magazzino.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM magazzino.inventari r
          JOIN magazzino.magazzini p ON p.id = r.magazzino_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'movimento' THEN
        -- Il movimento: dal suo magazzino.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM magazzino.movimenti r
          JOIN magazzino.magazzini p ON p.id = r.magazzino_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'rettifica' THEN
        -- La rettifica: dal suo magazzino.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM magazzino.rettifiche r
          JOIN magazzino.magazzini p ON p.id = r.magazzino_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'trasferimento' THEN
        -- Il trasferimento: dal magazzino di PARTENZA, come l'adattatore di prima.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM magazzino.trasferimenti r
          JOIN magazzino.magazzini p ON p.id = r.magazzino_id_from
         WHERE r.id = p_valore;
    ELSIF p_modo = 'pratica' THEN
        -- La pratica porta l'emittente.
        SELECT pr.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM pratiche.pratiche pr
         WHERE pr.id = p_valore;
    ELSIF p_modo = 'flusso' THEN
        -- Il flusso: dalla sua pratica.
        SELECT p.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM pratiche.flussi r
          JOIN pratiche.pratiche p ON p.id = r.pratica_id
         WHERE r.id = p_valore;
    ELSIF p_modo = 'documento_generato' THEN
        -- Il documento generato porta l'emittente.
        SELECT dg.emittente_fiscale_id
          INTO v_emittente_fiscale_id
          FROM documenti.documenti_generati dg
         WHERE dg.id = p_valore;
    ELSE
        -- ⛔ Non si restituisce NULL: NULL vuol dire «lascia
        --    passare», e un errore di battitura in un CREATE
        --    TRIGGER spegnerebbe il guard in silenzio.
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
                'il modo di risoluzione dell''emittente «%s» non esiste: '
                'sono ammessi fiscale, soggetto_ruolo, fattura, fattura_sdi, listino, listino_versione, '
                'ente_incasso, contabile, magazzino, ddt, ddt_riga, ordine, ordine_riga, preventivo, '
                'preventivo_riga, offerta, offerta_eccezione, contratto, contratto_riga, reso, '
                'reso_riga, commessa, commessa_attivita, attivita_fatturabile, lotto, asset, '
                'evento_asset, inventario, movimento, rettifica, trasferimento, pratica, flusso '
                'e documento_generato',
                p_modo
            )
        );
    END IF;

    RETURN v_emittente_fiscale_id;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_emittente_fiscale_id(p_modo text, p_valore bigint)
IS '⭐ rev 2026-10-18 (20261018-48, D-3b-2 ondata 2): 9 modi di magazzino, pratiche e documenti generati (asset, evento_asset, inventario, movimento, rettifica, trasferimento, pratica, flusso, documento_generato), per le policy ef_whitelist e gli adattatori via_*. ⭐ rev 2026-10-18 (20261018-31, D-3b-2 giro 1b): 18 modi dei documenti di vendita e delle loro righe (ddt, ddt_riga, ordine, ordine_riga, preventivo, preventivo_riga, offerta, offerta_eccezione, contratto, contratto_riga, reso, reso_riga, commessa, commessa_attivita, attivita_fatturabile, lotto, fattura_sdi, listino_versione): li chiedono le policy ef_whitelist per riga e gli adattatori fn_scope_ef_whitelist_via_*, una strada sola. Dice DI CHI E'' una riga: l''id dell''emittente fiscale raggiunto da p_valore secondo p_modo, o NULL se il riferimento non porta a nessun emittente («nessun padrone»: il guard lascia passare). Modi: fiscale (la colonna E'' emittente_fiscale_id), soggetto_ruolo, fattura, listino (dal listino padre della versione), ente_incasso (dal conto su cui atterra il denaro), contabile (la distinta sa di chi e''), magazzino (rev 2026-09-18, Lotto 2 magazzino: magazzini.emittente_fiscale_id — il perimetro del ledger che la primitiva DEFINER scavalca). Un modo sconosciuto SOLLEVA E_PARAMETRO_INVALIDO, non risponde NULL. SECURITY DEFINER del proprietario, perche'' due catene passano da tabelle sotto row security e un guard INVOKER fuori perimetro non troverebbe l''emittente; search_path bloccato. Risponde solo alla domanda di FATTO: il permesso e'' di script.fn_check_user_emittente_scope. Chiamata da script.trgfn_guard_emittente_scope.';
```

</div>

---
{% include-markdown "signature-core.md" %}
