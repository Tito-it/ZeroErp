{% include-markdown "it/dbzero/vendite/manual/trgfn_fondi_source_guard_importo.md" %}
# ⚙️ Funzione `trgfn_fondi_source_guard_importo`

```sql
CREATE FUNCTION trgfn_fondi_source_guard_importo()
```

**Definizione completa:**

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE FUNCTION vendite.trgfn_fondi_source_guard_importo()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
-- Scopo: un fondo AUTOMATICO deve assomigliare alla fattura da cui
--        nasce — stesso segno del totale, non superiore in valore
--        assoluto. Cio' che si vieta non e' il fondo NEGATIVO
--        (legittimo: e' il capo a credito della banda) ma il
--        fondo che racconta un'altra fattura.
-- Uso:   BEFORE INSERT OR UPDATE OF importo, fattura_sorgente_id
--        FOR EACH ROW
DECLARE
    v_totale vendite.fatture.totale_a_pagare%TYPE;
BEGIN
    -- La strada MANUALE ha per definizione il caso opposto:
    -- l'eccedenza di un sovra-incasso e' un credito su una
    -- fattura positiva. Li' il presidio non e' un vincolo di
    -- corrispondenza ma il governo — motivo obbligatorio, azione
    -- di processo, e un processo (in `pagamenti`) che l'eccedenza
    -- la conosce. Il database no: non puo' verificarla finche'
    -- il posting non esiste.
    IF NEW.origine = 'MANUALE' THEN
        RETURN NEW;
    END IF;

    SELECT f.totale_a_pagare INTO v_totale
      FROM vendite.fatture f
     WHERE f.id = NEW.fattura_sorgente_id;

    -- Fail-closed su totale non calcolato: senza una base il
    -- confronto non e' decidibile, e un fondo senza base non e'
    -- un fondo.
    IF v_totale IS NULL
       OR sign(NEW.importo) <> sign(v_totale)
       OR abs(NEW.importo) > abs(v_totale) THEN
        PERFORM script.fn_log_and_raise_error(
            'vendite', 'trgfn_fondi_source_guard_importo',
            'E_FONDO_NON_CORRISPONDE_SORGENTE',
            jsonb_build_object(
                'fondo_source_id',     NEW.id,
                'fattura_sorgente_id', NEW.fattura_sorgente_id,
                'importo',             NEW.importo,
                'totale_a_pagare',     v_totale,
                'origine',             NEW.origine),
            NULL::uuid,
            NEW.importo::TEXT,
            COALESCE(v_totale::TEXT, 'non calcolato'));
    END IF;

    RETURN NEW;
END;
$function$

COMMENT ON FUNCTION vendite.trgfn_fondi_source_guard_importo()
IS 'Guard di corrispondenza fra il fondo e la sua fattura sorgente: importo dello stesso segno del totale_a_pagare e non superiore in valore assoluto; totale non calcolato = rifiuto (fail-closed). ⚠️ Si applica ai soli atti con origine = AUTOMATICA: sulla strada MANUALE il caso principale ha segno opposto per costruzione — l''eccedenza di un sovra-incasso e'' un credito su una fattura dal totale positivo — e un guard applicato a tutti rifiuterebbe proprio l''atto per cui quella strada esiste. Li'' il presidio non e'' un vincolo ma il GOVERNO: motivo obbligatorio, azione di processo, e il processo rimborsi di `pagamenti`, che l''eccedenza la conosce mentre il database no (il posting non esiste ancora). ⚠️ NON vieta il fondo negativo, che e'' legittimo: le due soglie del minimo formano una banda che contiene lo zero e il capo inferiore serve a riportare avanti i CREDITI. Vieta il fondo che racconta un''altra fattura — 8 euro di documento e -32 di fondo, prodotti da una riga contabile piu'' grande della fattura. ⚠️ La regola e'' scritta come segno + valore assoluto e MAI come «compreso fra 0 e il totale»: su una sorgente a credito gli estremi si invertono. ⚠️ E'' un trigger e non un CHECK perche'' deve leggere vendite.fatture — e i trigger BEFORE ROW girano PRIMA dei CHECK, quindi su una sorgente non nulla intercetta lui anche l''importo zero. D-3(a) + coda D-5 di brief-db-fondo-fattura-ricalcolo-e-governo §8.2.';
```

</div>

---
{% include-markdown "signature-core.md" %}
