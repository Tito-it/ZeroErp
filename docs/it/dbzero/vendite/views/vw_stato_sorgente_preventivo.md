{% include-markdown "it/dbzero/vendite/manual/vw_stato_sorgente_preventivo.md" %}
# 🔍 View `vw_stato_sorgente_preventivo`

> 📝 **Descrizione**
>
> Resolver di dominio D2 (brief-db-proiezione-stato-dominio): descrittore normalizzato dello stato vivo di ogni preventivo — stato nativo (alias fedeli) + fase/esito/terminale dichiarati su config.stati_doc_preventivi. Chiave (sorgente_tipo_id, sorgente_uid) coerente con pratiche.pratiche_sorgenti (key_selector=uid); al piu' una riga per chiave. Read-time (nessun mirror); fotografa lo stato MEMORIZZATO: la transizione EMESSO-&gt;SCADUTO e' asincrona (job notturno). Consumata dal motore solo via script.vw_stato_sorgente.

```sql
CREATE OR REPLACE VIEW vendite.vw_stato_sorgente_preventivo AS
SELECT s.id AS sorgente_tipo_id,
    (p.uid)::text AS sorgente_uid,
    sdp.codice_interno AS stato_codice_interno,
    sdp.codice AS stato_codice,
    sdp.descrizione AS stato_descrizione,
    sdp.fase,
    sdp.esito,
    sdp.terminale
   FROM ((vendite.preventivi p
     JOIN config.sorgenti s ON ((((s.codice_interno)::text = 'PREVENTIVO'::text) AND (s.attivo IS TRUE))))
     JOIN config.stati_doc_preventivi sdp ON ((sdp.id = p.stato_doc_preventivo_id)));
```


---
{% include-markdown "signature-core.md" %}
