## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_fattura_attivita`

> 👀 **Vedi anche**
>
> • [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — la madre che emette le attività
>
> • [dbops.fn_pgtap_crea_commessa_attivita](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa_attivita) — le attività da fatturare
>
> • [dbops.fn_pgtap_crea_fattura](/dbzero/dbops/funzioni/fn_pgtap_crea_fattura) · [vendite.fn_get_or_create_fattura_header](/dbzero/vendite/funzioni/fn_get_or_create_fattura_header) — la testata, senza o con lotto
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-pgtap-reso-costruito` (E-2)

---
### 🎯 Scopo Principale

(rev 2026-10-25)

**Una o più attività di commessa fatturate**: emesse dal dominio e agganciate a una fattura
vera, in bozza, una riga per attività.

```sql
CREATE TEMP TABLE tmp_att AS
SELECT * FROM dbops.fn_pgtap_crea_commessa_attivita(v_commessa, 25,
           p_sorgente_codice => 'DDT_VENDITA', p_sorgente_uid => v_ddt_uid::text,
           p_sorgente_riga_id => v_ddt_riga, p_quantita => 10);

CREATE TEMP TABLE tmp_fatt AS
SELECT * FROM dbops.fn_pgtap_fattura_attivita('accrediti', ARRAY[(SELECT attivita_id FROM tmp_att)]);

-- dentro un lotto
SELECT * FROM dbops.fn_pgtap_fattura_attivita('lotto', ARRAY[v_att], (SELECT lotto_id FROM tmp_lotto));
```

---
### 🧭 Perché esiste

Accrediti, rinunce, annulli, chiusure delle partite e lotti partono tutti da «un'attività già
fatturata». I test la costruivano a mano, ognuno a modo suo: l'emissione, la lettura
dell'attività fatturabile (spesso per segmento, che con le rettifiche prende quella
sbagliata), la testata, la riga, l'aggancio. Del dominio nessuna funzione scrive le righe di
fattura — le scrive l'applicazione — quindi ogni file le riscriveva. Ora la strada ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **Le attività** le costruisce il test (commessa con la sorgente iniziale, attività sul
  segmento della bolla, quantità e prezzo): qui si fattura ciò che c'è. Tutte dello stesso
  cliente: una fattura è di un cliente solo.
* **L'emissione** la fa la madre, una volta per commessa (emette tutte le attività approvate e
  non ancora emesse di quella commessa), col marchio del lotto se c'è.
* **L'attività fatturabile** si prende **per attività**, ancora libera: non per segmento.
* **La testata**: senza lotto dal builder della fattura, in bozza sul cliente; con un lotto
  dalla funzione del dominio che crea la testata del lotto.
* **Le righe**: quantità, prezzo, articolo, unità e competenza dall'attività fatturabile, la
  prima aliquota attiva. Poi l'aggancio della riga all'attività; col lotto anche il lucchetto.

---
### 🚫 Cosa NON fa

**Non porta avanti la fattura**: resta in bozza. Emetterla, portarla avanti o toglierla (col
verbo `vendite.fn_cleanup_fatture_by_ids`) è il caso del test.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-fattura-attivita-v1.sql` (8 casi): firma; una attività con la
sua fattura in bozza e la riga agganciata; l'attività fatturabile scelta per attività; due
attività in una fattura, nell'ordine dato; il lotto con marchio, lucchetto e testata del lotto;
tre errori del chiamante rifiutati.
