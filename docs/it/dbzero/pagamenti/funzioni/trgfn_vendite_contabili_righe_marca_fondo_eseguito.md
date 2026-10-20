{% include-markdown "it/dbzero/pagamenti/manual/trgfn_vendite_contabili_righe_marca_fondo_eseguito.md" %}
# ⚙️ Funzione `trgfn_vendite_contabili_righe_marca_fondo_eseguito`

```sql
CREATE FUNCTION trgfn_vendite_contabili_righe_marca_fondo_eseguito()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    v_codice pagamenti.vendite_contabili_righe_stati.codice_interno%TYPE;
BEGIN
    -- =========================================================
    -- Scopo:
    --   Quando la riga contabile nata da un fondo fattura entra
    --   in uno stato REGISTRATO, l'atto che l'ha generata passa
    --   a ESEGUITO.
    --
    -- ⭐ Perche' qui e non nella madre del posting: la madre non
    --    e' l'unica strada per cui una riga finisce registrata
    --    (correzione a mano, import da flusso, ri-posting). Un
    --    trigger sulla tabella protegge il DATO, una riga dentro
    --    una funzione protegge QUELLA funzione.
    --
    -- ⚠️ Scrive da `pagamenti` verso `vendite`: quella tabella
    --    non ha RLS e `stato` non e' fra le colonne bloccate da
    --    trgfn_lock_columns. Ma fa scattare il guard delle
    --    transizioni del fondo: e' il motivo dell'ordine
    --    obbligato -49 -> -50 -> -51.
    --
    -- Uso: AFTER INSERT OR UPDATE OF stato_id FOR EACH ROW
    -- =========================================================

    -- La riga non viene da un fondo: e' il caso della
    -- stragrande maggioranza, e non c'e' niente da marcare.
    IF NEW.fondo_source_id IS NULL THEN
        RETURN NULL;
    END IF;

    -- Una riga disattivata non e' in nessun conto: dire che il
    -- denaro si e' mosso sarebbe falso.
    IF NEW.attivo IS NOT TRUE THEN
        RETURN NULL;
    END IF;

    -- Nessun movimento di stato: niente da marcare.
    IF TG_OP = 'UPDATE' AND NEW.stato_id IS NOT DISTINCT FROM OLD.stato_id THEN
        RETURN NULL;
    END IF;

    SELECT s.codice_interno
      INTO v_codice
      FROM pagamenti.vendite_contabili_righe_stati s
     WHERE s.id = NEW.stato_id;

    -- ⚠️ Confronto contro codice_interno, la chiave immutabile:
    --    `codice` e' l'etichetta e l'utente puo' rinominarla.
    IF v_codice IS DISTINCT FROM 'POSTATA' THEN
        RETURN NULL;
    END IF;

    -- ⭐ Idempotente e non forzante: si tocca solo un atto
    --    ancora ASSEGNATO. Un atto gia' ESEGUITO (ri-posting)
    --    non cambia; uno ANNULLATO o DISPONIBILE non si
    --    resuscita — quella transizione la matrice la
    --    rifiuterebbe, e l'errore accuserebbe questo trigger
    --    invece di chi ha portato l'atto dov'e'.
    UPDATE vendite.fatture_fondi_fattura_source s
       SET stato = 'ESEGUITO'
     WHERE s.id = NEW.fondo_source_id
       AND s.stato = 'ASSEGNATO';

    RETURN NULL;
END;
$function$

COMMENT ON FUNCTION pagamenti.trgfn_vendite_contabili_righe_marca_fondo_eseguito()
IS 'Porta l''atto di fondo fattura (vendite.fatture_fondi_fattura_source) a ESEGUITO quando la riga contabile che ne nasce entra in POSTATA. Nasce il 2026-08-21 col lotto 3 del cantiere incassi (S1-16, decisione D11). ⭐ E'' un trigger e non una riga dentro la madre del posting perche'' scatta sul FATTO: la madre non e'' l''unica strada per cui una riga puo'' finire registrata (correzione a mano, import da flusso, ri-posting), e un trigger sulla tabella protegge il dato invece di proteggere una funzione. ⭐ Effetto strutturale: i tre lettori dei fondi (fn_sync_contabili_fondo_fattura, fn_applica_fondi_fattura, vw_fondi_fattura_da_decidere) filtrano su ASSEGNATO o DISPONIBILE, quindi un atto che passa a ESEGUITO esce da tutti e tre senza che nessuno di loro cambi: e'' cosi'' che i difetti C-2 (il sync che riscriveva una riga gia'' registrata) e C-3 (il fondo interamente postato che si auto-annullava) smettono di essere raggiungibili. ⚠️ Scrive da pagamenti verso vendite: quella tabella non ha RLS e `stato` non e'' fra le colonne bloccate dal lock, ma l''UPDATE fa scattare vendite.trgfn_fondi_source_guard_transizione — da cui l''ordine obbligato CHECK (20260821-49) -> matrice (-50) -> trigger (questo). ⚠️ Idempotente: l''UPDATE filtra stato = ASSEGNATO, quindi un ri-posting non cambia nulla e un atto ANNULLATO non viene resuscitato. ⚠️ «Stato registrato» e'' oggi POSTATA e basta, confrontato per codice_interno; se un giorno gli stati registrati diventassero due, la mossa giusta e'' una bandiera di catalogo accanto a is_postabile/is_final/richiede_abbinamento.';
```

</div>

---
{% include-markdown "signature-core.md" %}
