# ⚙️ Funzione `trgfn_fatture_righe_guard_riga_capofila`

```sql
CREATE FUNCTION trgfn_fatture_righe_guard_riga_capofila()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fatture_righe_guard_riga_capofila()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: «niente catene» sulla relazione capofila/parti di
--        vendite.fatture_righe. Una parte deve puntare a una riga
--        che ha riga_capofila_id NULL, e una riga che ha gia'
--        delle parti non puo' diventare a sua volta una parte.
-- Uso:   BEFORE INSERT OR UPDATE FOR EACH ROW
-- ⚠️ Il DELETE non serve: cancellare una capofila con delle parti
--    e' gia' impedito dalla FK (NO ACTION), e cancellare una parte
--    non crea nessuna catena.
DECLARE
    -- ⚠️ %TYPE anche qui: la colonna e' bigint oggi, e una
    --    variabile ancorata non va riletta il giorno che cambia.
    v_capofila_di_capofila vendite.fatture_righe.riga_capofila_id%TYPE;
    v_trovata              boolean;
    v_ha_parti             boolean;
    v_motivo               text;
BEGIN
    -- Riga ordinaria: non e' una parte, non c'e' niente da dire.
    -- ⭐ E' il caso della quasi totalita' delle righe: si esce
    --    prima di leggere qualunque cosa.
    IF NEW.riga_capofila_id IS NULL THEN
        RETURN NEW;
    END IF;

    -- ── RAMO 1: in avanti — la capofila indicata e' gia' una parte?
    SELECT true, r.riga_capofila_id
      INTO v_trovata, v_capofila_di_capofila
      FROM vendite.fatture_righe r
     WHERE r.id = NEW.riga_capofila_id;

    -- ⚠️ NON trovata: NON e' compito di questa funzione. O la riga
    --    non esiste, o sta su un'altra fattura e la RLS non la
    --    mostra — in entrambi i casi a parlare e' la FK composita
    --    fk_fatture_righe_riga_capofila, con un 23503 che dice la
    --    cosa giusta («documento sbagliato», non «catena»).
    -- ⛔ Sollevare qui darebbe all'operatore il messaggio sbagliato
    --    per il problema che ha davvero.
    IF NOT COALESCE(v_trovata, false) THEN
        RETURN NEW;
    END IF;

    IF v_capofila_di_capofila IS NOT NULL THEN
        v_motivo := format(
            'la riga %s indicata come capofila e'' a sua volta una parte della riga %s',
            NEW.riga_capofila_id, v_capofila_di_capofila);
    ELSE
        -- ── RAMO 2: all'indietro — questa riga ha gia' delle parti?
        -- ⭐ E' il ramo che si dimentica. La riga puntata e' una
        --    capofila legittima, quindi il ramo 1 tace: la catena
        --    nasce dall'altro capo, perche' e' QUESTA riga ad avere
        --    gia' dei figli che diventerebbero nipoti.
        -- ⚠️ Su INSERT non puo' essere vero (la riga non esiste
        --    ancora e nessuno la punta), ma il controllo NON si
        --    restringe a TG_OP = 'UPDATE': un ramo che si spegne da
        --    solo su INSERT non costa niente, e la condizione
        --    esplicita sarebbe una cosa in piu' da rileggere.
        SELECT EXISTS (SELECT 1 FROM vendite.fatture_righe f
                        WHERE f.riga_capofila_id = NEW.id)
          INTO v_ha_parti;

        IF v_ha_parti THEN
            v_motivo := format(
                'la riga %s ha gia'' delle parti proprie e non puo'' diventare a sua volta una parte',
                NEW.id);
        END IF;
    END IF;

    IF v_motivo IS NOT NULL THEN
        -- ⚠️ TECNICO: niente chiave `campo` (non c'e' nessun campo
        --    da accendere su un 500) e niente `bersaglio` (si mette
        --    solo sugli errori rimediabili dall'operatore).
        PERFORM script.fn_log_and_raise_error(
            'vendite',
            'trgfn_fatture_righe_guard_riga_capofila',
            'E_FATTURA_RIGA_CAPOFILA_INCOERENTE',
            jsonb_build_object(
                'operazione',       TG_OP,
                'fattura_id',       NEW.fattura_id,
                'riga_id',          NEW.id,
                'riga_capofila_id', NEW.riga_capofila_id),
            NEW.tx_id,
            NEW.id::text, v_motivo
        );
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fatture_righe_guard_riga_capofila()
IS 'Guard (BEFORE INSERT OR UPDATE su vendite.fatture_righe): la relazione capofila/parti resta a UN SOLO SALTO. ⭐ Presidia DUE rami, e il secondo e'' quello che si dimentica: (1) IN AVANTI, la riga si aggancia a una riga che e'' gia'' una parte; (2) ALL''INDIETRO, una riga che HA GIA'' delle parti viene agganciata a una terza — li'' il primo controllo tace, perche'' la riga puntata e'' una capofila legittima e la catena nasce dall''altro capo. ⛔ Serve perche'' il difetto e'' MUTO: se «capofila -> parti» smette di essere una lettura a un salto, chi somma gli importi di un''attivita'' attraversando attivita_fatturabili.fattura_riga_id prende meta'' valore e non fallisce. E'' un trigger e non un vincolo perche'' bisogna guardare la riga PUNTATA, e nessun CHECK sa farlo — l''altra invariante della stessa colonna, «stessa fattura», e'' invece la FK composita fk_fatture_righe_riga_capofila e non ha bisogno di codice. ⚠️ SECURITY INVOKER E'' UNA DECISIONE, non una dimenticanza: vendite.fatture_righe ha la RLS, ma la FK composita garantisce che capofila e parte stiano sulla STESSA fattura, quindi hanno lo stesso perimetro e chi scrive la parte vede per forza la capofila. Se la riga indicata non si trova questa funzione ESCE IN SILENZIO di proposito: significa che sta su un altro documento, e a parlare dev''essere la FK con un 23503 — l''errore giusto per quel problema. ⚠️ Nessun UPDATE OF riga_capofila_id: la catena si crea anche modificando la riga puntata. Errore: E_FATTURA_RIGA_CAPOFILA_INCOERENTE (TECNICO, un codice solo per i due rami col motivo come valore). brief-db-richieste-aperte-dal-backend voce 5 (N3, decisione D).';
```

</div>

---
{% include-markdown "signature-core.md" %}
