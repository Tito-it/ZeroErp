{% include-markdown "it/dbzero/dbops/manual/vw_liste_multi_emittente_non_certificate.md" %}
# 🔍 View `vw_liste_multi_emittente_non_certificate`

> 📝 **Descrizione**
>
> Controllo automatico di P-2b (brief perimetro-emittente, §7 decisione 3): liste che dichiarano multi_emittente = true SENZA esporre l'emittente in nessuna colonna attiva di ui.lista_colonna. ⚠️ DEVE restare a ZERO righe: una riga qui e' una lista con l'adesivo «collaudato» addosso e nessun collaudo dietro — cioe' il flag usato per far sparire un fastidio invece che per dichiarare un lavoro fatto. E' il «prezzo del biglietto» reso verificabile a macchina: una lista si guadagna il flag esponendo l'emittente nella riga (P-4), non prima. Controllo di PURO CATALOGO: non sa nulla delle viste ne' del backend, quindi non prova che la colonna arrivi a video — prova che qualcuno l'abbia dichiarata.

> 🔐 **Sicurezza**: definer (default delle viste) — le tabelle sotto si leggono con i privilegi dell'owner `zeroerp_owner`, e la RLS che vale e' la sua, non quella di chi interroga.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW dbops.vw_liste_multi_emittente_non_certificate AS
SELECT id AS lista_id,
    codice AS lista_codice,
    descrizione,
    schema_dati,
    attivo AS lista_attiva
   FROM ui.lista_definizione ld
  WHERE (multi_emittente AND (NOT (EXISTS ( SELECT 1
           FROM ui.lista_colonna lc
          WHERE ((lc.lista_id = ld.id) AND lc.attivo AND ((lc.campo_sorgente)::text ~ '^emittent'::text))))));
```

</div>


---
{% include-markdown "signature-core.md" %}
