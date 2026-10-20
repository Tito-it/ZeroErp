{% include-markdown "it/dbzero/script/manual/vw_lotto_documento_righe.md" %}
# 🔍 View `vw_lotto_documento_righe`

> 📝 **Descrizione**
>
> Quale BOZZA di un lotto contiene righe di quale DOCUMENTO: la terna (lotto, fattura, gruppo_key), distinta. ⭐ Esiste perche' la stessa relazione si legge nei DUE versi — la madre chiede «quali bozze tocca questo documento» per cancellarle, il conteggio chiede «quali documenti contiene questa bozza» per dire chi viene trascinato — e scritti separatamente sarebbero due catene da tenere allineate a mano. 🔴 La chiave si calcola su vendite.commesse_attivita, raggiunta da attivita_fatturabili.commessa_attivita_id: su attivita_fatturabili darebbe COMMESSA:&lt;hash del segment_key&gt;, che non combacia con nessuna riga di perimetro (misurato il 2026-09-08: zero corrispondenze). ⚠️ security_invoker: commesse_attivita ha la RLS e attivita_fatturabili no — il JOIN alla commessa E' il perimetro. Brief: brief-db-uscita-documento-dal-giro §5.4-bis.

> 🔒 **Opzioni di sicurezza**: `security_invoker=true` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW script.vw_lotto_documento_righe
WITH (security_invoker=true) AS
SELECT DISTINCT lf.lotto_id,
    fr.fattura_id,
    vendite.fn_build_gruppo_fatturabile_key(ca.sorgente_tipo_id, ca.sorgente_uid, ca.commessa_id) AS gruppo_key
   FROM (((vendite.fatturazione_lotti_fatture lf
     JOIN vendite.fatture_righe fr ON ((fr.fattura_id = lf.fattura_id)))
     JOIN vendite.attivita_fatturabili af ON ((af.fattura_riga_id = fr.id)))
     JOIN vendite.commesse_attivita ca ON ((ca.id = af.commessa_attivita_id)));
```

</div>


---
{% include-markdown "signature-core.md" %}
