{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_guard_distinta_finale.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_righe_guard_distinta_finale`

```sql
CREATE FUNCTION trgfn_vendite_contabili_righe_guard_distinta_finale()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_is_final         pagamenti.vendite_contabili_stati.is_final%TYPE;
    v_stato            pagamenti.vendite_contabili_stati.codice_interno%TYPE;
    v_codice           pagamenti.vendite_contabili.codice%TYPE;
    v_diventa_pronta   pagamenti.vendite_contabili_righe_stati.is_postabile%TYPE;
    v_righe_lavorabili pagamenti.vendite_contabili_stati.righe_lavorabili%TYPE;
    -- NUDO di proposito: l'esito di una decisione, non il riflesso di una colonna.
    v_da_guardare      boolean;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Impedire che una riga contabile finisca — o torni utile —
    --   sotto una distinta in stato finale (CHIUSA o ANNULLATA):
    --   la' non entra in nessun conto e non verra' mai registrata.
    --   E, dal 2026-09-30, CONGELARE le righe che stanno gia' sotto
    --   una distinta le cui righe non si lavorano piu' (ANNULLATA).
    --
    -- ⚠️ CINQUE mosse. Le quattro d'INGRESSO: nascere li', esserci
    --    RIATTIVATA, esserci SPOSTATA da un'altra distinta, e — dal
    --    2026-08-22 — diventarci PRONTA DA REGISTRARE restando
    --    dov'e'. Poi la quinta, che si valuta per PRIMA: TOCCARE una
    --    riga che sta gia' sotto una distinta con
    --    righe_lavorabili = false.
    --
    -- ⚠️ Cio' che NON si rifiuta — SOLO dove le righe sono ancora
    --    lavorabili, cioe' sotto una CHIUSA: sospendere, scartare,
    --    riprendere, correggere il motivo_sospeso di una riga gia'
    --    li'. E' dire che cosa ne e' stato di quel denaro, e sotto
    --    una CHIUSA ha un futuro (la registrazione tardiva, D20-b).
    --    Sotto una ANNULLATA non c'e' niente da dire: quel denaro,
    --    per il registro, non e' mai arrivato, e le righe si leggono
    --    soltanto (D-3, Tid 2026-09-30).
    --
    -- ⭐ La quarta mossa ha UNA porta, e la apre solo il verbo
    --    pagamenti.fn_posta_riga_tardiva. Una SOSPESA sotto una
    --    distinta REGISTRATA si abbina e si registra nello stesso
    --    gesto: il verbo si presenta con la GUC transazionale
    --    app.registrazione_tardiva_riga_id = <id>, e questo guard
    --    lascia passare SOLO quella riga, SOLO in quella
    --    transazione, SOLO nel ramo del cambio di stato, e SOLO se
    --    chi scrive e' il proprietario della tabella: dentro il
    --    verbo (SECURITY DEFINER) si', per l'applicazione mai.
    --    Le altre mosse non la leggono: la tardiva non fa
    --    nascere, non riattiva, non sposta — e non lavora sotto
    --    un'annullata. Precedente: app.cessazione_automatica in
    --    vendite.
    -- =========================================================

    -- ⭐ QUINTA MOSSA (2026-09-30, D-2/D-3). La riga STA gia' sotto
    --    una distinta le cui righe non si lavorano piu': ogni UPDATE
    --    e' rifiutato — cambio di stato (anche verso SOSPESA o
    --    SCARTATA), correzione di un dato, riattivazione, spostamento
    --    FUORI. Annullata vuol dire sola lettura.
    -- ⭐ Si guarda la distinta di PARTENZA (OLD.contabile_id): e'
    --    quella dove la riga sta. Le quattro mosse guardano l'arrivo,
    --    e tirare una riga fuori da un'annullata non lo vedevano.
    -- ⭐ Si valuta PRIMA delle altre: lo specifico batte il generico,
    --    e una riattivazione sotto un'annullata deve sentirsi dire
    --    «si legge soltanto», non «non accetta altre righe».
    -- ⚠️ La domanda si fa al CATALOGO (righe_lavorabili), non a
    --    is_final: CHIUSA e ANNULLATA sono entrambe finali e opposte
    --    per le righe.
    -- ⚠️ IS FALSE e non IS NOT TRUE: la colonna e' NOT NULL, quindi
    --    NULL vuol dire solo «testata non letta» — e dire «annullata»
    --    di una testata che non si legge sarebbe un messaggio falso.
    -- 🔴 Stato e origine si leggono FUORI dalla row security
    --    (script.fn_get_contabile_stato_origine, 2026-11-03): la riga
    --    si vede anche dalla FATTURA, e chi la vede cosi' non vede la
    --    sua distinta. Letta sotto RLS, la testata non c'era e il
    --    guard taceva. Il CODICE resta sotto RLS: chi non vede la
    --    distinta ne legge l'id, non il numero.
    -- ⚠️ La porta della tardiva NON vale qui: la tardiva lavora solo
    --    sotto una CHIUSA registrata, e rifiuta l'annullata prima di
    --    scrivere.
    -- ℹ️ Il DELETE e la disattivazione hanno la loro sede in
    --    guard_contenuto, che chiama script.fn_check_riga_contabile_eliminabile
    --    (motivo DISTINTA_ANNULLATA, stesso codice): la disattivazione
    --    arriva qui solo se quella check l'ha gia' lasciata passare.
    IF TG_OP = 'UPDATE' THEN
        SELECT s.righe_lavorabili, s.codice_interno
          INTO v_righe_lavorabili, v_stato
          FROM script.fn_get_contabile_stato_origine(OLD.contabile_id) d
          JOIN pagamenti.vendite_contabili_stati s ON s.id = d.stato_id;

        IF v_righe_lavorabili IS FALSE THEN
            SELECT c.codice
              INTO v_codice
              FROM pagamenti.vendite_contabili c
             WHERE c.id = OLD.contabile_id;

            PERFORM script.fn_log_and_raise_error(
                'database',
                'pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale',
                'E_RIGA_CONTABILE_DISTINTA_ANNULLATA',
                jsonb_build_object(
                    'contabile_riga_id', OLD.id,
                    'contabile_id',      OLD.contabile_id,
                    'contabile_codice',  v_codice,
                    'stato_distinta',    v_stato,
                    'operazione',        TG_OP,
                    'reason',            'DISTINTA_ANNULLATA'
                ),
                NEW.tx_id,
                COALESCE(v_codice, OLD.contabile_id::text)
            );
        END IF;
    END IF;

    v_da_guardare := CASE
        WHEN TG_OP = 'INSERT' THEN NEW.attivo IS TRUE
        -- riattivazione, oppure spostamento sotto un'altra distinta
        ELSE (NEW.attivo IS TRUE AND OLD.attivo IS NOT TRUE)
          OR (NEW.contabile_id IS DISTINCT FROM OLD.contabile_id)
    END;

    -- ⭐ QUARTA MOSSA. La riga non si sposta e non si riattiva:
    --    cambia stato, e il nuovo stato la rende PRONTA DA
    --    REGISTRARE. Sotto una distinta finale quel denaro non
    --    verrebbe mai registrato — il posting parte dalla testata,
    --    e una CHIUSA la rifiuta.
    -- ⚠️ La domanda si fa al CATALOGO (`is_postabile`), non a un
    --    elenco di stati scritto qui: e' la stessa scelta di
    --    `richiede_abbinamento` sul guard gemello.
    -- ℹ️ La lettura si paga solo se le altre tre mosse non hanno
    --    gia' deciso, e solo su un cambio di stato vero.
    IF NOT v_da_guardare
       AND TG_OP = 'UPDATE'
       AND NEW.attivo IS TRUE
       AND NEW.stato_id IS DISTINCT FROM OLD.stato_id
    THEN
        SELECT s.is_postabile
          INTO v_diventa_pronta
          FROM pagamenti.vendite_contabili_righe_stati s
         WHERE s.id = NEW.stato_id;

        v_da_guardare := COALESCE(v_diventa_pronta, false);

        -- ⭐ LA PORTA DELLA TARDIVA (D20-b). Si apre per UNA riga —
        --    quella nominata dalla GUC — e si richiude col ROLLBACK
        --    o il COMMIT, perche' set_config(..., true) e'
        --    transazionale. ⚠️ current_setting(name, true) risponde
        --    NULL se la GUC non e' mai stata impostata nella sessione
        --    e '' se lo e' stata in una transazione gia' chiusa:
        --    NULLIF le tratta uguali, e nessuna delle due apre.
        -- ⛔ La GUC settata su un ALTRO id non apre: e' la
        --    condizione che il pgTAP prova per prima.
        -- ⛔ E la sola GUC non apre: l'applicazione la puo' accendere
        --    da se'. Chi scrive dev'essere il proprietario della
        --    tabella, cioe' il verbo SECURITY DEFINER
        --    (script.fn_is_proprietario_tabella).
        IF v_da_guardare
           AND NULLIF(current_setting('app.registrazione_tardiva_riga_id', true), '')
               = NEW.id::text
           AND script.fn_is_proprietario_tabella(TG_RELID)
        THEN
            v_da_guardare := false;
        END IF;
    END IF;

    IF NOT v_da_guardare THEN
        RETURN NEW;
    END IF;

    -- 🔴 Fuori dalla row security, come la quinta mossa: un guard
    --    che legge sotto RLS non distingue «non lo vedo» da «non
    --    c'e'», e la riga vista dalla fattura sta proprio li'.
    SELECT s.is_final, s.codice_interno
      INTO v_is_final, v_stato
      FROM script.fn_get_contabile_stato_origine(NEW.contabile_id) d
      JOIN pagamenti.vendite_contabili_stati s ON s.id = d.stato_id;

    IF COALESCE(v_is_final, false) IS FALSE THEN
        RETURN NEW;
    END IF;

    SELECT c.codice
      INTO v_codice
      FROM pagamenti.vendite_contabili c
     WHERE c.id = NEW.contabile_id;

    PERFORM script.fn_log_and_raise_error(
        'database',
        'pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale',
        'E_RIGA_CONTABILE_DISTINTA_FINALE',
        jsonb_build_object(
            'contabile_riga_id', NEW.id,
            'contabile_id',      NEW.contabile_id,
            'contabile_codice',  v_codice,
            'stato_distinta',    v_stato,
            'stato_riga_id',     NEW.stato_id,
            'diventa_pronta',    COALESCE(v_diventa_pronta, false),
            'operazione',        TG_OP
        ),
        NEW.tx_id,
        COALESCE(v_codice, NEW.contabile_id::text),
        CASE WHEN v_stato = 'ANNULLATA' THEN 'annullata' ELSE 'chiusa' END
    );

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_righe_guard_distinta_finale()
IS 'Guard delle righe contabili sotto una distinta in stato finale. Cinque mosse. La prima si valuta per prima: ogni UPDATE di una riga la cui distinta di partenza (OLD.contabile_id) ha righe_lavorabili = false, cioè l''ANNULLATA, è rifiutato con E_RIGA_CONTABILE_DISTINTA_ANNULLATA: cambio di stato, correzione di un dato, riattivazione, spostamento fuori. Annullata vuol dire sola lettura: il documento non è mai successo. Le altre quattro sono d''ingresso, e rifiutano con E_RIGA_CONTABILE_DISTINTA_FINALE una riga utile sotto una distinta finale (CHIUSA o ANNULLATA), dove non entrerebbe in nessun conto: nascerci, esserci riattivata, esserci spostata, diventarci pronta da registrare restando dov''è. Sotto una CHIUSA si vieta solo l''ingresso in uno stato is_postabile: sospendere, scartare, riprendere o correggere il motivo di una riga che sta lì resta possibile. La quarta mossa ha una porta, la registrazione tardiva: la GUC transazionale app.registrazione_tardiva_riga_id uguale all''id della riga, e chi scrive è il proprietario della tabella (script.fn_is_proprietario_tabella). Le due cose insieme si hanno solo dentro il verbo pagamenti.fn_posta_riga_tardiva, SECURITY DEFINER, che abbina e registra la riga nello stesso gesto; l''applicazione non apre la porta, nemmeno accendendo la GUC. Le altre mosse non leggono la GUC. Lo stato della distinta si legge fuori dalla row security (script.fn_get_contabile_stato_origine): una riga si vede anche dalla fattura, e chi la vede così può non vedere la sua distinta. Le domande si fanno al catalogo (righe_lavorabili, is_postabile, is_final), non a un elenco nel guard. Il DELETE e la disattivazione hanno la loro sede in pagamenti.trgfn_vendite_contabili_righe_guard_contenuto; il gemello d''uscita è pagamenti.trgfn_vendite_contabili_guard_chiusura.';
```

</div>

---
{% include-markdown "signature-core.md" %}
