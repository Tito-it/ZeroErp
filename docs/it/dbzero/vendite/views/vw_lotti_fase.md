{% include-markdown "it/dbzero/vendite/manual/vw_lotti_fase.md" %}
# 🔍 View `vw_lotti_fase`

> 📝 **Descrizione**
>
> Sede unica della domanda «in che fase e' questo lotto?». Una riga per lotto: i tre assi di config.stati_doc_fiscale (is_abortito, congela_fiscale, chiude_lotto) e il derivato pre_fiscale = COALESCE(NOT congela_fiscale, false): il lotto non ha ancora congelato i suoi documenti, quindi si puo' ancora agire su di loro e li trattiene. Consumatori: script.fn_check_lotto_annullabile, script.fn_check_lotto_riportabile_a_draft, script.fn_check_fattura_eliminabile_da_lotto, script.fn_check_documento_escludibile_da_giro, script.fn_check_attivita_riportabile_da_emettere, vendite.vw_documenti_trattenuti_da_lotto e vendite.vw_dash_competenza_attivita. pre_fiscale e' anche la porta d'uscita: un documento esce dal giro solo da un lotto pre-fiscale, quindi «trattenuto» e «si puo' ancora uscire» coincidono. Non si deriva da chiude_lotto, che marca la transizione che chiude (DEFINITIVA) e non la proprieta' di essere chiuso: DEFINITIVA -&gt; INVIATA -&gt; REGISTRATA non lo portano. Lo stato del lotto e' NOT NULL: la riga del vocabolario c'e' sempre. L'assenza di riga vuol dire lotto inesistente o fuori perimetro RLS, e i fn_check_* la trattano come errore (E_LOTTO_NON_TROVATO).

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

> 🔓 **Sicurezza**: `security_invoker` — le tabelle sotto si leggono con i privilegi e la RLS di chi interroga; owner `zeroerp_owner`.

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
    COALESCE((NOT sdf.congela_fiscale), false) AS pre_fiscale
   FROM (vendite.fatturazione_lotti l
     LEFT JOIN config.stati_doc_fiscale sdf ON ((sdf.id = l.stato_doc_fiscale_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
