{% include-markdown "it/dbzero/script/manual/fn_resolve_emittente_fiscale_id.md" %}
# ⚙️ Funzione `fn_resolve_emittente_fiscale_id`

```sql
CREATE FUNCTION fn_resolve_emittente_fiscale_id(p_modo text, p_valore bigint)
```

**Definizione completa:**

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
                'sono ammessi fiscale, soggetto_ruolo, fattura, listino, ente_incasso, contabile e magazzino',
                p_modo
            )
        );
    END IF;

    RETURN v_emittente_fiscale_id;
END
$function$

COMMENT ON FUNCTION script.fn_resolve_emittente_fiscale_id(p_modo text, p_valore bigint)
IS 'Dice DI CHI E'' una riga: l''id dell''emittente fiscale raggiunto da p_valore secondo p_modo, o NULL se il riferimento non porta a nessun emittente («nessun padrone»: il guard lascia passare). Modi: fiscale (la colonna E'' emittente_fiscale_id), soggetto_ruolo, fattura, listino (dal listino padre della versione), ente_incasso (dal conto su cui atterra il denaro), contabile (la distinta sa di chi e''), magazzino (rev 2026-09-18, Lotto 2 magazzino: magazzini.emittente_fiscale_id — il perimetro del ledger che la primitiva DEFINER scavalca). Un modo sconosciuto SOLLEVA E_PARAMETRO_INVALIDO, non risponde NULL. SECURITY DEFINER del proprietario, perche'' due catene passano da tabelle sotto row security e un guard INVOKER fuori perimetro non troverebbe l''emittente; search_path bloccato. Risponde solo alla domanda di FATTO: il permesso e'' di script.fn_check_user_emittente_scope. Chiamata da script.trgfn_guard_emittente_scope.';
```

---
{% include-markdown "signature-core.md" %}
