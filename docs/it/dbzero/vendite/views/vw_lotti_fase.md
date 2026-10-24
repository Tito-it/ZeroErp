{% include-markdown "it/dbzero/vendite/manual/vw_lotti_fase.md" %}
# 🔍 View `vw_lotti_fase`

> 📝 **Descrizione**
>
> SEDE UNICA della domanda «in che fase e' questo lotto?». Una riga per lotto: i tre assi grezzi di config.stati_doc_fiscale (is_abortito, congela_fiscale, chiude_lotto) piu' i DUE derivati che li interpretano. Consumatori: script.fn_check_lotto_annullabile, script.fn_check_lotto_riportabile_a_draft, script.fn_check_fattura_eliminabile_da_lotto, script.fn_check_documento_escludibile_da_giro (pre_fiscale) e vendite.vw_documenti_trattenuti_da_lotto (in_gioco).
> ⭐ I DUE DERIVATI SONO LO STESSO ASSE CON IL FAIL-CLOSED IN DIREZIONE OPPOSTA, e differiscono in UN SOLO caso — lo stato non risolvibile. `pre_fiscale` = COALESCE(NOT congela_fiscale, false) risponde a «si puo' ancora agire sul documento?» e sull'ignoto dice NO (non si tocca). `in_gioco` = COALESCE(NOT congela_fiscale, true) risponde a «il lotto trattiene ancora i suoi documenti?» e sull'ignoto dice SI' (non ci si mette le mani). ⛔ Non sono un doppione: le due domande vogliono la risposta prudente OPPOSTA, e con un flag solo un lotto senza stato risolvibile risulterebbe libero per il secondo giro E non estraibile dal primo — il peggio dei due, in silenzio.
> ⚠️ SUI SEI STATI A CATALOGO COINCIDONO: DRAFT ed EMESSA veri, DEFINITIVA, INVIATA, REGISTRATA e ANNULLATA falsi. La differenza vive sul settimo caso, che il modello ammette perche' la colonna e' nullable.
> ⭐ E `pre_fiscale` E' ANCHE LA PORTA D'USCITA: fn_check_documento_escludibile_da_giro ammette di togliere un documento dal giro solo da un lotto pre-fiscale. Sui sei stati veri vale quindi «trattenuto ⇔ si puo' ancora uscire»; sull'ignoto le due prudenze divergono, ed e' voluto.
> ⛔ NESSUNO DEI DUE si deriva da `chiude_lotto`: quel flag marca la TRANSIZIONE che chiude (solo DEFINITIVA), non la proprieta' di essere chiuso — il catalogo ammette DEFINITIVA -&gt; INVIATA -&gt; REGISTRATA, e quei due stati non lo portano, quindi un lotto chiuso risulterebbe di nuovo aperto.
> ⚠️ I TRE ASSI GREZZI SONO NULLABILI e i derivati no: il grezzo e' il fatto (che puo' essere ignoto), il derivato e' la decisione (che non puo' esserlo). COALESCE-are anche i grezzi metterebbe nella stessa colonna il fatto e la difesa.
> ⚠️ L'ASSENZA DI RIGA e' un'altra cosa ancora: significa lotto inesistente o fuori perimetro RLS. I quattro fn_check_* la trattano come errore (E_LOTTO_NON_TROVATO) e continuano a farlo.
> Brief: brief-db-il-trattenuto-passa-lo-stesso.md (L1, L2).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW vendite.vw_lotti_fase
WITH (security_invoker=true) AS
SELECT l.id AS lotto_id,
    l.codice AS lotto_codice,
    l.competenza_mese AS lotto_competenza_mese,
    sdf.codice_interno AS stato_codice_interno,
    sdf.is_abortito,
    sdf.congela_fiscale,
    sdf.chiude_lotto,
    COALESCE((NOT sdf.congela_fiscale), false) AS pre_fiscale,
    COALESCE((NOT sdf.congela_fiscale), true) AS in_gioco
   FROM (vendite.fatturazione_lotti l
     LEFT JOIN config.stati_doc_fiscale sdf ON ((sdf.id = l.stato_doc_fiscale_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
