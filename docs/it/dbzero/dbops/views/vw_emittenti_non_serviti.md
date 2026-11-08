{% include-markdown "it/dbzero/dbops/manual/vw_emittenti_non_serviti.md" %}
# 🔍 View `vw_emittenti_non_serviti`

> 📝 **Descrizione**
>
> Coppie (processo DOMINIO vivo senza operatore che lo lanci, emittente fiscale attivo) per cui NON esiste un utente tecnico. DEVE restare VUOTA. Copre un guasto che non assomiglia a un errore: senza l'utente il lavoro parte, la RLS mostra zero righe e il run chiude con «FATTO, 0 elaborate», e quell'emittente non viene mai lavorato. Non concede niente: il perimetro lo decide una persona creando l'utente. Canali: PGAGENT, COMMAND e CODA_AUTOMATICA (i lavori di coda che nessuna persona accoda); i processi CODA girano con l'identita' dell'operatore che li accoda. Processo vivo = ritiro non raggiunto (script.fn_e_obsoleto).

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_emittenti_non_serviti AS
SELECT p.codice AS processo_codice,
    p.canale,
    ef.id AS emittente_fiscale_id,
    ef.codice AS emittente_codice
   FROM (dbops.processi p
     CROSS JOIN anagrafiche.emittenti_fiscali ef)
  WHERE ((p.classe = 'DOMINIO'::text) AND (NOT script.fn_e_obsoleto(p.obsoleto_dal)) AND (p.canale = ANY (ARRAY['PGAGENT'::text, 'COMMAND'::text, 'CODA_AUTOMATICA'::text])) AND ef.attivo AND (NOT (EXISTS ( SELECT 1
           FROM (dbops.processi_identita pi
             JOIN config.user_emittenti_fiscali uef ON ((uef.auth_user_id = pi.auth_user_id)))
          WHERE ((pi.processo_id = p.id) AND pi.attivo AND (uef.emittente_fiscale_id = ef.id))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
