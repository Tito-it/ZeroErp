# ⚙️ Funzione `trgfn_righe_default_erogazione_da_articolo`

```sql
CREATE FUNCTION trgfn_righe_default_erogazione_da_articolo()
```

> 🔓 **Sicurezza**: `SECURITY INVOKER` (default) — gira con i privilegi di chi la chiama; owner `zeroerp_owner`.

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION script.trgfn_righe_default_erogazione_da_articolo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: la riga eredita dall'articolo come si eroga (B-R2, decisione di
--   Tid del 2026-10-07): riempie SOLO i campi vuoti, la scelta
--   dell'operatore vince (dentro il perimetro, che giudica il guard).
--   · erogazione vuota: la combinazione di default dell'articolo
--     (erogazione, fonte se vuota); se la fonte
--     e' gia' indicata, un'erogazione che l'articolo ammette con QUELLA fonte
--     (il default per primo), altrimenti il default — e il guard rifiuta la
--     fonte, col suo campo;
--   · erogazione indicata e fonte vuota: la fonte che l'articolo ammette per
--     quell'erogazione (il default, se e' quella; altrimenti la prima).
--     Se l'articolo non la ammette
--     la fonte resta vuota: la riempie la matrice generica
--     (trgfn_righe_default_fonte_qta) e il guard del perimetro rifiuta la riga;
--   ⛔ rev 2026-10-29 (F-7 di Tid, brief-db-contratto-righe-periodiche-in-
--     commessa §6.6): la generazione_canone NON si eredita piu'
--     dall'articolo. Anticipati o normali li dice la testata
--     (vendite.contratti.generazione_canone, vendite.offerte_commerciali.
--     generazione_canone): la riga vuota la segue, valorizzata la forza.
--     Riempirla qui la staccherebbe dalla testata.
-- Fonte: vendite.fn_articolo_erogazioni (tipologia, altrimenti natura).
-- Generica sulle due tabelle gemelle (vendite.contratti_righe,
--   vendite.offerte_commerciali_eccezioni): legge NEW.articolo_id e le tre
--   colonne. Trigger BEFORE INSERT WHEN tipo_eccezione <> 'ESCLUSIONE', fascia
--   _a10_, nome che precede default_fonte_qta e guard_erogazione_*: prima si
--   eredita, poi la matrice generica riempie cio' che resta, poi si giudica.
-- ⚠️ Su UPDATE (OF tipo_erogazione) non si eredita niente di vuoto: un UPDATE che
--   svuota l'erogazione e' una scelta, e la rifiuta il guard d'obbligo. Si
--   riallinea solo la FONTE quando cambia la sola erogazione (prima lo faceva la
--   matrice generica di trgfn_righe_default_fonte_qta, col default del
--   vocabolario e non con quello dell'articolo: un servizio CANONE -> CONSUMO
--   prendeva LETTURE, fuori dal suo perimetro).
-- Ordine: ogni scelta prende la PRIMA combinazione utile secondo
--   ae.ordine, il rango che il BB dichiara (default, poi erogazione, poi
--   fonte). Lo stesso ordine della lista del form
--   (vendite.fn_documento_riga_erogazioni): §D.4 punto 1, 20261007-66.
--   Rev 2026-10-21 (§I.1): DERIVATA_COMPONENTI ritirata, solo commenti.
DECLARE
    v_scelta record;
BEGIN
    -- UPDATE (solo OF tipo_erogazione, vedi -64): l'erogazione cambia e la
    -- fonte NO. Se la coppia esce dal perimetro dell'articolo, la fonte diventa
    -- quella che l'articolo ammette per la nuova erogazione (il default per
    -- primo). Se l'operatore ha cambiato anche la fonte, la scelta e' sua: non
    -- si tocca, e il guard la giudica.
    IF TG_OP = 'UPDATE' THEN
        IF NEW.tipo_erogazione IS NOT NULL
           AND NEW.tipo_erogazione IS DISTINCT FROM OLD.tipo_erogazione
           AND NEW.fonte_quantita_attesa IS NOT DISTINCT FROM OLD.fonte_quantita_attesa
           AND NOT EXISTS (
               SELECT 1 FROM vendite.fn_articolo_erogazioni(NEW.articolo_id) ae
                WHERE ae.tipo_erogazione = NEW.tipo_erogazione
                  AND ae.fonte_quantita_attesa = NEW.fonte_quantita_attesa) THEN
            SELECT ae.fonte_quantita_attesa INTO v_scelta
              FROM vendite.fn_articolo_erogazioni(NEW.articolo_id) ae
             WHERE ae.tipo_erogazione = NEW.tipo_erogazione
             ORDER BY ae.ordine
             LIMIT 1;
            IF FOUND THEN
                NEW.fonte_quantita_attesa := v_scelta.fonte_quantita_attesa;
            END IF;
        END IF;
        RETURN NEW;
    END IF;

    IF NEW.tipo_erogazione IS NULL THEN
        -- Con la fonte gia' indicata, un'erogazione che l'articolo ammette CON
        -- quella fonte (il default per primo); se nessuna, il default, e il
        -- guard rifiutera' la fonte col suo campo.
        SELECT ae.tipo_erogazione, ae.fonte_quantita_attesa
          INTO v_scelta
          FROM vendite.fn_articolo_erogazioni(NEW.articolo_id) ae
         WHERE ae.e_default
            OR ae.fonte_quantita_attesa = NEW.fonte_quantita_attesa
         ORDER BY (ae.fonte_quantita_attesa IS NOT DISTINCT FROM NEW.fonte_quantita_attesa) DESC,
                  ae.ordine
         LIMIT 1;
        IF FOUND THEN
            NEW.tipo_erogazione := v_scelta.tipo_erogazione;
            IF NEW.fonte_quantita_attesa IS NULL THEN
                NEW.fonte_quantita_attesa := v_scelta.fonte_quantita_attesa;
            END IF;
        END IF;
    ELSIF NEW.fonte_quantita_attesa IS NULL THEN
        SELECT ae.fonte_quantita_attesa
          INTO v_scelta
          FROM vendite.fn_articolo_erogazioni(NEW.articolo_id) ae
         WHERE ae.tipo_erogazione = NEW.tipo_erogazione
         ORDER BY ae.ordine
         LIMIT 1;
        IF FOUND THEN
            NEW.fonte_quantita_attesa := v_scelta.fonte_quantita_attesa;
        END IF;
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION script.trgfn_righe_default_erogazione_da_articolo()
IS 'Trigger generico (vendite.contratti_righe, vendite.offerte_commerciali_eccezioni), BEFORE INSERT OR UPDATE OF tipo_erogazione WHEN tipo_eccezione <> ESCLUSIONE. Su UPDATE: se cambia la sola erogazione e la coppia esce dal perimetro dell''articolo, la fonte diventa quella che l''articolo ammette per la nuova erogazione (se l''operatore ha cambiato anche la fonte non si tocca). Su INSERT la riga eredita dall''articolo come si eroga, riempiendo solo i campi vuoti (la scelta dell''operatore vince, il perimetro lo giudica script.trgfn_righe_guard_erogazione_perimetro). Erogazione vuota: la combinazione di default dell''articolo (erogazione; fonte se vuota); con la fonte già indicata, un''erogazione che l''articolo ammette con quella fonte, default per primo (altrimenti il default, e il guard rifiuta la fonte). Erogazione indicata e fonte vuota: la fonte che l''articolo ammette per quell''erogazione (il default se lo è, altrimenti la prima); se non la ammette resta vuota, la riempie trgfn_righe_default_fonte_qta e il guard rifiuta la riga. Fonte: vendite.fn_articolo_erogazioni (tipologia, altrimenti natura). Ogni scelta prende la prima combinazione utile nell''ordine che il BB dichiara (colonna ordine: default, poi erogazione, poi fonte), lo stesso della lista del form vendite.fn_documento_riga_erogazioni. Decisione B-R2 di Tid del 2026-10-07. Nasce il 2026-10-07, brief-db-offerta-emissione-ed-erogazione §C.7 (B3); ordine dal 20261007-67 (§D.4 punto 1). Rev 2026-10-21 (20261021-50, §I.1): commenti senza DERIVATA_COMPONENTI, ritirata. ⛔ Rev 2026-10-29 (20261029-19, F-7 di Tid, brief-db-contratto-righe-periodiche-in-commessa): la generazione_canone non si eredita più dall''articolo — la dice la testata del documento, e la riga vuota la segue.';
```

</div>

---
{% include-markdown "signature-core.md" %}
