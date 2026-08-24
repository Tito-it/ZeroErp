{% include-markdown "it/dbzero/pagamenti/manual/vw_rate_fuori_capienza.md" %}
# 🔍 View `vw_rate_fuori_capienza`

> 📝 **Descrizione**
>
> Le rate il cui residuo e' uscito dalla banda [0, importo]: l'elenco senza il quale la forzatura sarebbe un modo di NASCONDERE denaro invece di registrarlo (brief madre §5). ⭐ DUE motivi e non uno: SOVRA_INCASSATA (residuo negativo — e' entrato piu' del dovuto) e MOVIMENTO_CONTRARIO (residuo oltre l'importo della rata — e' uscito denaro dove non era entrato). Il secondo e' il caso che ha fatto cadere l'asimmetria di D1-bis (pagato 110, rimborso 15 invece di 10), ed e' il motivo per cui la vista NON si chiama «sovra incassate» come diceva il piano: quel nome avrebbe lasciato fuori proprio il caso che ha cambiato la regola. ⚠️ Il criterio guarda i FATTI: contano i movimenti registrati, non le righe ancora in lavorazione — una riga dichiarata e non registrata non ha ancora fatto danno, e chiedere di guardarla vorrebbe dire mostrare qualcosa che potrebbe non succedere mai. `in_lavorazione` resta come colonna, per chi legge la riga e se lo chiede. ⚠️ Le righe forzate sono la TRACCIA della decisione, non il criterio: una rata puo' essere fuori capienza senza che nessuno abbia forzato niente — due incassi legittimi arrivati sullo stesso documento bastano. ⚠️ La formula del saldo NON e' ricopiata: si chiama pagamenti.fn_get_saldo_rata in LATERAL, perche' due copie della regola darebbero prima o poi due risposte diverse e la divergenza si vedrebbe come un elenco che segnala cio' che il guard ha lasciato passare. Il costo si limita prima, con un pre-filtro sulle sole rate che qualcuno ha toccato. ⚠️ security_invoker=on: va RI-SPECIFICATA a ogni CREATE OR REPLACE o PostgreSQL la azzera, e la vista tornerebbe a mostrare le rate di tutti gli emittenti. S2-7 del cantiere incassi.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

```sql
CREATE OR REPLACE VIEW pagamenti.vw_rate_fuori_capienza
WITH (security_invoker=on) AS
WITH candidate AS (
         SELECT s.id AS scadenza_id,
            s.fattura_id,
            s.numero_rata,
            s.data_scadenza,
            s.importo
           FROM vendite.fatture_scadenze s
          WHERE ((EXISTS ( SELECT 1
                   FROM pagamenti.vendite_movimenti m
                  WHERE ((m.scadenza_id = s.id) AND (m.attivo IS TRUE)))) OR (EXISTS ( SELECT 1
                   FROM pagamenti.vendite_contabili_righe cr
                  WHERE ((cr.scadenza_id = s.id) AND (cr.attivo IS TRUE) AND (cr.forzata IS TRUE)))))
        )
 SELECT
        CASE
            WHEN (x.saldo < (0)::numeric) THEN 'SOVRA_INCASSATA'::text
            ELSE 'MOVIMENTO_CONTRARIO'::text
        END AS motivo,
    c.scadenza_id,
    c.fattura_id,
    f.anno,
    f.serie,
    f.numero AS fattura_numero,
    f.billing_account_id,
    f.emittente_soggetto_ruolo_id,
    c.numero_rata,
    c.data_scadenza,
    c.importo AS importo_rata,
    (c.importo - x.saldo) AS registrato,
    x.saldo AS residuo,
    x.incassato,
    x.in_lavorazione,
    fz.righe_forzate,
    fz.motivi_forzatura
   FROM (((candidate c
     JOIN vendite.fatture f ON ((f.id = c.fattura_id)))
     CROSS JOIN LATERAL pagamenti.fn_get_saldo_rata(c.scadenza_id) x(saldo, in_lavorazione, incassato, has_movimenti))
     LEFT JOIN LATERAL ( SELECT (count(*))::integer AS righe_forzate,
            string_agg(NULLIF(btrim(cr.motivo_forzatura), ''::text), ' · '::text ORDER BY cr.id) AS motivi_forzatura
           FROM pagamenti.vendite_contabili_righe cr
          WHERE ((cr.scadenza_id = c.scadenza_id) AND (cr.attivo IS TRUE) AND (cr.forzata IS TRUE))) fz ON (true))
  WHERE ((x.saldo < (0)::numeric) OR (x.saldo > c.importo));
```


---
{% include-markdown "signature-core.md" %}
