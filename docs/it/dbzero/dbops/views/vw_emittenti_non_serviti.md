# 🔍 View `vw_emittenti_non_serviti`

> 📝 **Descrizione**
>
> Emittenti fiscali ATTIVI assenti dalla whitelist dell'utente tecnico di un processo DOMINIO headless. DEVE restare VUOTA. ⛔ Copre un guasto che non assomiglia a un errore: senza la riga in config.user_emittenti_fiscali il lavoro parte lo stesso, la RLS mostra zero righe e il run chiude con «FATTO, 0 elaborate» — nessun errore, e quell'emittente non viene mai fatturato. ⭐ E' il contro-esempio alla frase «tolto il bypass, al massimo non fa niente»: «non fa niente» lo nota solo chi si aspettava qualcosa, e questa vista e' chi se lo aspetta. ⚠️ Non concede niente: il perimetro lo aggiunge una PERSONA (decisione D-9), la vista dice solo che cosa manca. Esclusi i processi su canale CODA (girano con lo scope dell'operatore) e quelli ancora senza utente tecnico (affare di vw_processi_dominio_senza_identita). Brief: brief-db-processi-automatici-identita-e-perimetro §6.4.

```sql
CREATE OR REPLACE VIEW dbops.vw_emittenti_non_serviti AS
SELECT p.codice AS processo_codice,
    p.canale,
    pi.auth_user_id,
    ef.id AS emittente_fiscale_id,
    ef.codice AS emittente_codice
   FROM ((dbops.processi p
     JOIN dbops.processi_identita pi ON (((pi.processo_id = p.id) AND pi.attivo)))
     CROSS JOIN anagrafiche.emittenti_fiscali ef)
  WHERE ((p.classe = 'DOMINIO'::text) AND p.attivo AND (p.obsoleto_dal IS NULL) AND (p.canale = ANY (ARRAY['PGAGENT'::text, 'COMMAND'::text])) AND ef.attivo AND (NOT (EXISTS ( SELECT 1
           FROM config.user_emittenti_fiscali uef
          WHERE ((uef.auth_user_id = pi.auth_user_id) AND (uef.emittente_fiscale_id = ef.id))))));
```


---
{% include-markdown "signature-core.md" %}
