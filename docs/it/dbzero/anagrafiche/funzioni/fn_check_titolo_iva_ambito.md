{% include-markdown "it/dbzero/anagrafiche/manual/fn_check_titolo_iva_ambito.md" %}
# ⚙️ Funzione `fn_check_titolo_iva_ambito`

```sql
CREATE FUNCTION fn_check_titolo_iva_ambito(p_titolo_iva_id bigint)
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION anagrafiche.fn_check_titolo_iva_ambito(p_titolo_iva_id bigint)
 RETURNS jsonb
 LANGUAGE plpgsql
 STABLE
AS $function$
-- Scopo: elencare i motivi per cui l'AMBITO di un titolo IVA non
--   sta in piedi. Funzione PURA (fn_check_*): non solleva e non
--   scrive. La chiamano i due trigger guard — quello sulle righe
--   di ambito e quello sul padre — cosi' la regola non e' scritta
--   in due posti che possono divergere (linee-guida-sql §12.5.2).
--   Brief: brief-db-be-iva-risolutore-e-regime-cliente, I7 / D10 / D13.
-- Ritorna: [] se l'ambito e' coerente; altrimenti array ORDINATO
--   di {codice, reason, dettaglio, valori}.
DECLARE
    v_motivi     jsonb := '[]'::jsonb;
    v_titolo     record;
    v_n_ambiti   bigint;
    v_conflitto  record;
BEGIN
    IF p_titolo_iva_id IS NULL OR p_titolo_iva_id <= 0 THEN
        RETURN v_motivi;   -- una fn_check_* non arbitra l'esistenza
    END IF;

    SELECT t.id, t.soggetto_id, t.emittente_fiscale_id, t.tipo_titolo_iva_id,
           t.ambito, t.attivo, t.validita, tt.descrizione AS tipo_descrizione
      INTO v_titolo
      FROM anagrafiche.soggetti_titoli_iva t
      JOIN config.tipi_titolo_iva tt ON tt.id = t.tipo_titolo_iva_id
     WHERE t.id = p_titolo_iva_id;

    -- ⚠️ SELECT INTO senza righe azzera il record: senza questa
    --   uscita i rami sotto girerebbero su NULL e non
    --   scatterebbero mai — verde per sottrazione.
    IF v_titolo.id IS NULL THEN
        RETURN v_motivi;
    END IF;

    SELECT count(*)
      INTO v_n_ambiti
      FROM anagrafiche.soggetti_titoli_iva_ambiti a
     WHERE a.titolo_iva_id = p_titolo_iva_id;

    -- ── MOTIVO 1 — «vale per tutto» e «vale per queste voci» non
    --    stanno insieme. Un titolo TUTTO con delle righe di ambito
    --    e' una tabella che dice due cose opposte, e il risolutore
    --    ne leggerebbe una sola.
    IF v_titolo.ambito = 'TUTTO' AND v_n_ambiti > 0 THEN
        v_motivi := v_motivi || jsonb_build_object(
            'codice',    'E_TITOLO_IVA_AMBITO_NON_AMMESSO',
            'reason',    'AMBITO_SU_TITOLO_TOTALE',
            'dettaglio', jsonb_build_object('titolo_iva_id', p_titolo_iva_id,
                                            'righe_ambito', v_n_ambiti),
            'valori',    jsonb_build_array(v_titolo.tipo_descrizione));
        RETURN v_motivi;   -- gli altri motivi non hanno senso qui
    END IF;

    -- ── MOTIVO 2 — il PAREGGIO. Due titoli attivi dello stesso
    --    soggetto, verso lo stesso emittente, dello stesso tipo,
    --    con periodi che si toccano, che coprono lo STESSO oggetto
    --    allo STESSO livello: nessuno dei due e' piu' specifico, e
    --    D13 dice che si solleva invece di sceglierne uno.
    --
    -- ⚠️ Livelli DIVERSI non sono un pareggio e non vanno bloccati:
    --    articolo > categoria di merce > tutto e' la regola di D13,
    --    ed e' la stessa della cascata degli indirizzi. Bloccarli
    --    qui vorrebbe dire rifiutare una configurazione legittima.
    --
    -- ⚠️ ORDER BY prima del LIMIT: senza, quale conflitto esca
    --    dipende dal piano del planner e il messaggio nominerebbe
    --    un titolo diverso a ogni corsa.
    IF v_titolo.ambito = 'RISTRETTO' AND v_titolo.attivo IS TRUE THEN
        SELECT altro.id AS titolo_conflitto_id,
               a.livello,
               COALESCE(art.descrizione, gru.descrizione, tip.descrizione) AS oggetto
          INTO v_conflitto
          FROM anagrafiche.soggetti_titoli_iva_ambiti a
          JOIN anagrafiche.soggetti_titoli_iva_ambiti a2
               ON  a2.livello        = a.livello
               AND a2.articolo_id    IS NOT DISTINCT FROM a.articolo_id
               AND a2.gruppo_voce_id IS NOT DISTINCT FROM a.gruppo_voce_id
               AND a2.tipo_voce_id   IS NOT DISTINCT FROM a.tipo_voce_id
          JOIN anagrafiche.soggetti_titoli_iva altro
               ON  altro.id                   = a2.titolo_iva_id
               AND altro.id                  <> v_titolo.id
               AND altro.soggetto_id          = v_titolo.soggetto_id
               AND altro.emittente_fiscale_id = v_titolo.emittente_fiscale_id
               AND altro.tipo_titolo_iva_id   = v_titolo.tipo_titolo_iva_id
               AND altro.ambito               = 'RISTRETTO'
               AND altro.attivo               IS TRUE
               AND altro.validita            && v_titolo.validita
          LEFT JOIN catalogo.articoli        art ON art.id = a.articolo_id
          LEFT JOIN vendite.articoli_gruppi  gru ON gru.id = a.gruppo_voce_id
          LEFT JOIN vendite.articoli_tipologie tip ON tip.id = a.tipo_voce_id
         WHERE a.titolo_iva_id = v_titolo.id
         ORDER BY altro.id, a.id
         LIMIT 1;

        IF v_conflitto.titolo_conflitto_id IS NOT NULL THEN
            v_motivi := v_motivi || jsonb_build_object(
                'codice',    'E_TITOLO_IVA_AMBITO_SOVRAPPOSTO',
                'reason',    'DUE_TITOLI_STESSA_SPECIFICITA',
                'dettaglio', jsonb_build_object(
                                 'titolo_iva_id',       v_titolo.id,
                                 'titolo_conflitto_id', v_conflitto.titolo_conflitto_id,
                                 'livello',             v_conflitto.livello),
                -- ⚠️ Nel VARIADIC va cio' che una persona
                --   riconosce: il tipo di titolo e il NOME della
                --   merce. Mai un id, mai un nome di colonna.
                'valori',    jsonb_build_array(v_titolo.tipo_descrizione,
                                               COALESCE(v_conflitto.oggetto, '')));
        END IF;
    END IF;

    RETURN v_motivi;
END;
$function$

COMMENT ON FUNCTION anagrafiche.fn_check_titolo_iva_ambito(p_titolo_iva_id bigint)
IS 'Single source dei motivi per cui l''AMBITO di un titolo IVA non sta in piedi. Ritorna [] se coerente, altrimenti array ORDINATO di {codice, reason, dettaglio, valori}. PURA: non solleva e non scrive. La chiamano DUE trigger — quello sulle righe di ambito e quello sul padre — e li chiamano invece di riscrivere il predicato: un test che confrontasse due predicati proverebbe che OGGI coincidono, cosi'' invece non possono divergere (linee-guida-sql §12.5.2). ⭐ Il secondo trigger non e'' ridondanza: due titoli diventano sovrapposti anche quando cambia il PADRE — si allarga valido_al, si riattiva un titolo spento, si cambia il tipo — e in nessuno di quei casi la figlia viene toccata. Due motivi: (1) E_TITOLO_IVA_AMBITO_NON_AMMESSO, righe di ambito su un titolo che vale per TUTTO — una tabella che dice due cose opposte, di cui il risolutore ne leggerebbe una sola; (2) E_TITOLO_IVA_AMBITO_SOVRAPPOSTO, il PAREGGIO: due titoli attivi dello stesso soggetto verso lo stesso emittente, dello stesso tipo, con periodi che si toccano, sullo STESSO oggetto allo STESSO livello. ⚠️ Livelli diversi NON sono un pareggio e non si bloccano: D13 li risolve per specificita'' — articolo > categoria di merce > tutto, la stessa cascata degli indirizzi — e bloccarli rifiuterebbe una configurazione legittima. A parita'' di specificita'' invece non c''e'' niente da scegliere: e'' un errore di configurazione, e un''ambiguita'' che si risolve sull''ordine degli id e'' quello che AGENTS.md chiama un''ambiguita'' del modello. ⚠️ SECURITY INVOKER: il confronto e'' fra titoli verso lo STESSO emittente, quindi la policy RLS e'' la stessa per entrambi e non esiste il conflitto invisibile che renderebbe cieco il guard. I7 di brief-db-be-iva-risolutore-e-regime-cliente.';
```

</div>

---
{% include-markdown "signature-core.md" %}
