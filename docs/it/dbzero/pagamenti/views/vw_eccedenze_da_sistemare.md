{% include-markdown "it/dbzero/pagamenti/manual/vw_eccedenze_da_sistemare.md" %}
# 🔍 View `vw_eccedenze_da_sistemare`

> 📝 **Descrizione**
>
> L'ELENCO del processo rimborsi: i documenti il cui residuo ha CAMBIATO SEGNO, cioe' che in valore assoluto hanno incassato piu' del totale (D15-b). Si accoppia con pagamenti.sistemazioni: la vista dice CHE COSA C'E' DA FARE, la tabella CHE COSA E' STATO FATTO. ⭐ La condizione non ha estremi fissi — sign(saldo) = -sign(totale_a_pagare) — quindi vale identica su fatture e note di credito senza nominare ne' l'una ne' l'altra: un intervallo 0..totale su un documento a credito diventa vuoto, ed e' la trappola che questa forma evita per costruzione. Stessa famiglia della regola di capienza del lotto 5. ⭐ Una riga per DOCUMENTO, con le colonne del cliente calcolate in finestra: D15-b chiede di raggruppare per cliente — la compensazione ha senso solo a quel livello — ma l'azione si fa su un documento, e una vista gia' aggregata avrebbe perso cio' che serve per agire. ⭐ chi_e_in_credito esiste perche' un saldo negativo su una fattura e uno positivo su una nota di credito sono situazioni OPPOSTE, e sbagliare il verso significa rimborsare denaro che si deve incassare. ⚠️ I due contatori SEGNALANO e non filtrano: un atto in bozza non ha mosso niente, e nasconderlo sarebbe l'opposto di «la vista presenta, la persona decide». Un atto confermato invece sparisce da solo — i saldi si leggono, non si conservano. ⚠️ security_invoker = on: la vista legge tre tabelle con le policy, e senza girerebbe come proprietario mostrando a ciascuno i documenti dell'altro. ⚠️ Ricreata il 2026-08-25 (S5-1) e di nuovo il 2026-09-18 (P-6) senza cambiare nessuna colonna: la funzione del saldo ha cambiato prima il RETURNS e poi la FIRMA, e per droppare una funzione bisogna prima togliere la vista che la usa. Usa `s.saldo` per nome, senza lista di alias, e chiama la funzione a un argomento, cosi' che una colonna o un parametro in piu' non la riguardino una seconda volta.

> 🔒 **Opzioni di sicurezza**: `security_invoker=on` — reloption non visibile in `pg_get_viewdef`, riportata qui esplicitamente. Va **ri-specificata** in ogni `CREATE OR REPLACE VIEW`, altrimenti PostgreSQL la azzera.

<div data-search-exclude markdown>

```sql
CREATE OR REPLACE VIEW pagamenti.vw_eccedenze_da_sistemare
WITH (security_invoker=on) AS
WITH candidate AS (
         SELECT f.id AS fattura_id,
            f.numero,
            f.data,
            f.totale_a_pagare,
            f.emittente_soggetto_ruolo_id,
            f.billing_account_id,
            ba.soggetto_ruolo_id AS cliente_soggetto_ruolo_id
           FROM (vendite.fatture f
             JOIN anagrafiche.billing_account ba ON ((ba.id = f.billing_account_id)))
          WHERE ((f.totale_a_pagare IS NOT NULL) AND (f.totale_a_pagare <> (0)::numeric) AND (EXISTS ( SELECT 1
                   FROM pagamenti.vendite_movimenti m
                  WHERE ((m.fattura_id = f.id) AND (m.attivo IS TRUE)))))
        ), con_saldo AS (
         SELECT c.fattura_id,
            c.numero,
            c.data,
            c.totale_a_pagare,
            c.emittente_soggetto_ruolo_id,
            c.billing_account_id,
            c.cliente_soggetto_ruolo_id,
            s.saldo
           FROM (candidate c
             CROSS JOIN LATERAL pagamenti.fn_get_saldo_fattura(c.fattura_id) s(saldo, in_lavorazione, incassato, has_movimenti))
        )
 SELECT fattura_id,
    numero AS fattura_numero,
    data AS fattura_data,
    emittente_soggetto_ruolo_id,
    cliente_soggetto_ruolo_id,
    billing_account_id,
    totale_a_pagare,
    saldo AS residuo,
    abs(saldo) AS eccedenza,
        CASE
            WHEN (totale_a_pagare > (0)::numeric) THEN 'CLIENTE'::text
            ELSE 'AZIENDA'::text
        END AS chi_e_in_credito,
    sum(abs(saldo)) OVER (PARTITION BY cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id) AS eccedenza_cliente,
    count(*) OVER (PARTITION BY cliente_soggetto_ruolo_id, emittente_soggetto_ruolo_id) AS documenti_cliente,
    ( SELECT count(*) AS count
           FROM pagamenti.sistemazioni s
          WHERE ((s.fattura_origine_id = cs.fattura_id) AND ((s.stato)::text = 'BOZZA'::text))) AS sistemazioni_in_bozza,
    ( SELECT count(*) AS count
           FROM pagamenti.sistemazioni s
          WHERE ((s.fattura_origine_id = cs.fattura_id) AND ((s.stato)::text = 'CONFERMATA'::text))) AS sistemazioni_confermate
   FROM con_saldo cs
  WHERE (sign(saldo) = (- sign(totale_a_pagare)));
```

</div>


---
{% include-markdown "signature-core.md" %}
