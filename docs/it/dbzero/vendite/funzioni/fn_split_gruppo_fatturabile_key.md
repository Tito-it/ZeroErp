{% include-markdown "it/dbzero/vendite/manual/fn_split_gruppo_fatturabile_key.md" %}
# ⚙️ Funzione `fn_split_gruppo_fatturabile_key`

```sql
CREATE FUNCTION fn_split_gruppo_fatturabile_key(p_gruppo_key text)
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.fn_split_gruppo_fatturabile_key(p_gruppo_key text)
 RETURNS TABLE(sorgente_tipo_id bigint, sorgente_uid text, commessa_id bigint)
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: il verso INVERSO di vendite.fn_build_gruppo_fatturabile_key.
--        Da '<codice_interno>:<uid>' torna la coppia sorgente; da
--        'MAN:<commessa_id>' torna la commessa.
-- ⛔ Le due funzioni sono GEMELLE e si leggono insieme: il prefisso
--        'MAN' e la forma della chiave sono decisi la'. Il presidio
--        e' un pgTAP di andata e ritorno, non l'occhio.
-- ⚠️ NON SOLLEVA MAI: la chiama una lista, e una chiave storta deve
--        produrre un ripiego, non una lista rotta. Una riga sempre,
--        con tre NULL quando non riconosce niente.
DECLARE
    v_key    text := btrim(COALESCE(p_gruppo_key, ''));
    v_sep    integer;
    v_prefix text;
    v_resto  text;
BEGIN
    -- Una riga SEMPRE: i tre OUT partono a NULL e si valorizzano
    -- solo se c'e' qualcosa da dire. Stessa forma della sorella
    -- vendite.fn_get_sorgente_documento_ref.
    sorgente_tipo_id := NULL;
    sorgente_uid     := NULL;
    commessa_id      := NULL;

    v_sep := strpos(v_key, ':');
    IF v_key = '' OR v_sep < 2 THEN
        RETURN NEXT;
        RETURN;
    END IF;

    v_prefix := left(v_key, v_sep - 1);
    -- ⚠️ `substr` e non `split_part`: l'uid e' un uuid e i due punti
    --    non ce li ha, ma una chiave malformata con un secondo ':'
    --    verrebbe TRONCATA in silenzio, e un troncamento silenzioso
    --    e' peggio di un ripiego dichiarato.
    v_resto  := substr(v_key, v_sep + 1);

    IF v_resto = '' THEN
        RETURN NEXT;
        RETURN;
    END IF;

    -- ── FORMA 1: riga sourceless -> 'MAN:<commessa_id>' ──
    -- ⛔ Il prefisso e' un letterale deciso da
    --    fn_build_gruppo_fatturabile_key: qui si RILEGGE, non si
    --    inventa. Se cambia la', questa smette di riconoscere la
    --    forma e il pgTAP di andata e ritorno diventa rosso.
    IF v_prefix = 'MAN' THEN
        -- Solo cifre: un cast su altro solleverebbe, e questa
        -- funzione ha promesso di non farlo.
        IF v_resto ~ '^[0-9]+$' THEN
            commessa_id := v_resto::bigint;
        END IF;
        RETURN NEXT;
        RETURN;
    END IF;

    -- ── FORMA 2: riga con documento -> '<codice_interno>:<uid>' ──
    -- ⛔ L'aggancio e' su `codice_interno` (immutabile), mai su
    --    `codice` — linee-guida-sql §6c/§6d: al primo rename fatto
    --    dall'utente la risoluzione smetterebbe in silenzio.
    -- Nessun filtro su `attivo`: un documento nato da una sorgente
    -- poi disattivata resta quel documento, e la segnalazione che
    -- lo nomina va letta comunque.
    SELECT s.id
      INTO sorgente_tipo_id
      FROM config.sorgenti s
     WHERE s.codice_interno = v_prefix
     LIMIT 1;

    IF sorgente_tipo_id IS NOT NULL THEN
        sorgente_uid := v_resto;
    END IF;

    RETURN NEXT;
    RETURN;
END;
$function$

COMMENT ON FUNCTION vendite.fn_split_gruppo_fatturabile_key(p_gruppo_key text)
IS 'Verso INVERSO di vendite.fn_build_gruppo_fatturabile_key: da una chiave di gruppo fatturabile torna la coppia sorgente (''<codice_interno>:<uid>'') oppure la commessa (''MAN:<commessa_id>''). ⭐ Esiste perche'' chi legge una SEGNALAZIONE ha in mano solo la chiave, e per mostrare il numero del documento deve tornare alla sorgente. ⛔ Le due funzioni sono GEMELLE e si leggono insieme: il prefisso ''MAN'' e la forma della chiave sono decisi nella funzione che costruisce, qui si rileggono. Il presidio non e'' l''occhio ma un pgTAP di ANDATA E RITORNO — split(build(x)) = x sulle due forme. ⚠️ NON SOLLEVA MAI, e non e'' pigrizia: la chiama una lista, e una chiave storta deve produrre un ripiego e non una lista rotta. Torna sempre UNA riga, con tre NULL quando non riconosce la forma. ⚠️ `substr` e non `split_part` sul resto: una chiave malformata con un secondo '':'' verrebbe troncata in silenzio. ⛔ L''aggancio della sorgente e'' su codice_interno, mai su codice (linee-guida-sql §6c/§6d). ⚠️ Non risale a commesse_attivita di proposito: la chiave su una segnalazione e'' un fatto STORICO, e quel lavoro puo'' essere gia'' fatturato o uscito dal giro — la risoluzione si svuoterebbe proprio dopo. STABLE, SECURITY INVOKER. Brief: brief-db-uscita-documento-dal-giro §6.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
