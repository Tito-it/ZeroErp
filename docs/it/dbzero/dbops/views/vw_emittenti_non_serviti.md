{% include-markdown "it/dbzero/dbops/manual/vw_emittenti_non_serviti.md" %}
# 🔍 View `vw_emittenti_non_serviti`

> 📝 **Descrizione**
>
> Coppie (processo DOMINIO senza operatore che lo lanci, emittente fiscale attivo) per cui NON esiste un utente tecnico. DEVE restare VUOTA. ⛔ Copre un guasto che non assomiglia a un errore: senza l'utente il lavoro parte, la RLS mostra zero righe e il run chiude con «FATTO, 0 elaborate» — e quell'emittente non viene mai fatturato. ⚠️ Non concede niente: il perimetro lo decide una persona creando l'utente (D-9). ⭐ Rev 2026-09-05 (R-E, strada B): include CODA_AUTOMATICA, cioe' i lavori di coda che nessuna persona accoda. I processi CODA «umani» restano esclusi: girano con l'identita' dell'operatore che li accoda. Brief: brief-db-processi-automatici-residui-be, sezione 1-quater.

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
  WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL) AND (p.canale = ANY (ARRAY['PGAGENT'::text, 'COMMAND'::text, 'CODA_AUTOMATICA'::text])) AND ef.attivo AND (NOT (EXISTS ( SELECT 1
           FROM (dbops.processi_identita pi
             JOIN config.user_emittenti_fiscali uef ON ((uef.auth_user_id = pi.auth_user_id)))
          WHERE ((pi.processo_id = p.id) AND pi.attivo AND (uef.emittente_fiscale_id = ef.id))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
