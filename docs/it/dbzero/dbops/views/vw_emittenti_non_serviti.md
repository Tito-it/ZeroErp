# 🔍 View `vw_emittenti_non_serviti`

> 📝 **Descrizione**
>
> Coppie (processo DOMINIO headless, emittente fiscale attivo) per cui NON esiste un utente tecnico. DEVE restare VUOTA. ⭐ Rev 2026-09-04: riscritta sul modello vero — config.user_emittenti_fiscali e' 1-a-1 sull'utente, quindi la domanda non e' «a questo utente manca la riga per l'emittente X» (che sarebbe vera per costruzione su tutti tranne uno, e la vista non sarebbe mai arrivata a zero) ma «per la coppia processo/emittente esiste un utente?». ⛔ Copre un guasto che non assomiglia a un errore: senza l'utente il lavoro parte, la RLS mostra zero righe e il run chiude con «FATTO, 0 elaborate» — e quell'emittente non viene mai fatturato. ⚠️ Non concede niente: il perimetro lo decide una persona creando l'utente (D-9). Esclusi i processi su canale CODA. Brief: brief-db-processi-automatici-identita-e-perimetro §6.4.

```sql
CREATE OR REPLACE VIEW dbops.vw_emittenti_non_serviti AS
SELECT p.codice AS processo_codice,
    p.canale,
    ef.id AS emittente_fiscale_id,
    ef.codice AS emittente_codice
   FROM (dbops.processi p
     CROSS JOIN anagrafiche.emittenti_fiscali ef)
  WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL) AND (p.canale = ANY (ARRAY['PGAGENT'::text, 'COMMAND'::text])) AND ef.attivo AND (NOT (EXISTS ( SELECT 1
           FROM (dbops.processi_identita pi
             JOIN config.user_emittenti_fiscali uef ON ((uef.auth_user_id = pi.auth_user_id)))
          WHERE ((pi.processo_id = p.id) AND pi.attivo AND (uef.emittente_fiscale_id = ef.id))))));
```


---
{% include-markdown "signature-core.md" %}
