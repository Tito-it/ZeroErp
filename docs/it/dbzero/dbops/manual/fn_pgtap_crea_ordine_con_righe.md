## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ordine_con_righe`

> 👀 **Vedi anche**
>
> • [dbops.fn_pgtap_crea_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ordine) — la testata su cui si appoggia, che resta senza righe
>
> • [dbops.fn_pgtap_crea_ddt_da_ordine](/dbzero/dbops/funzioni/fn_pgtap_crea_ddt_da_ordine) — la bolla che nasce da questo ordine
>
> • [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarlo avanti
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-pgtap-reso-costruito` (E-1)

---
### 🎯 Scopo Principale

(rev 2026-10-25)

**Un ordine con le sue righe, confermato, in una chiamata sola.**

```sql
CREATE TEMP TABLE tmp_o AS
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('consegne',
           p_quantita => 10, p_prezzo => 20, p_fatturazione_trigger => 'CONSEGNATO');

-- due righe in bozza, la seconda con la data di consegna confermata
SELECT * FROM dbops.fn_pgtap_crea_ordine_con_righe('date', 'DRAFT', p_righe => jsonb_build_array(
           jsonb_build_object('quantita', 10, 'prezzo', 20, 'sconto_percentuale', 5),
           jsonb_build_object('quantita', 5, 'prezzo', 20, 'data_consegna_confermata', '2026-11-20')));
```

---
### 🧭 Perché esiste

Una trentina di test scrivevano a mano la stessa strada in un ordine obbligato: la testata
in bozza con la data scelta alla nascita, il momento di fatturazione riscritto in bozza, le
righe con la loro aliquota, poi la conferma. La stessa strada viveva anche dentro il builder
della bolla da ordine. Ora ha una sede.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **La testata** la fa `dbops.fn_pgtap_crea_ordine`, che **resta senza righe** (è una
  decisione: i test che provano le righe le scrivono da sé). Questo builder la compone: data
  alla nascita (`p_data_ordine`), cliente del test (terzo parametro).
* **Il momento di fatturazione** (`p_fatturazione_trigger`) si scrive in bozza: fuori bozza è
  congelato, e all'inserimento il dominio lo eredita dal cliente.
* **Le righe**: una dai parametri (`p_quantita`, `p_prezzo`, `p_articolo_id`), o più righe da
  `p_righe` con sconto, aliquota, descrizione e date di consegna. Una chiave che il builder
  non conosce solleva: un errore di battitura non passa in silenzio. Articolo costruito e
  prima aliquota attiva quando mancano; lo sconto si scrive solo se chiesto.
* **Lo stato** (default `CONFERMATO`) per la matrice dei passaggi; `DRAFT` lascia l'ordine in
  bozza con le righe.
* **Una testata del test** (`p_ordine_id`, in bozza): quando la testata è il caso del test
  (un emittente di default, un flag, dei termini), il builder ci scrive righe e stato; cliente,
  data e momento di fatturazione allora non si passano.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-ordine-con-righe-v1.sql` (10 casi): firma; ordine di
default confermato con la riga; data e momento di fatturazione; due righe in bozza con sconto
e data di consegna; il builder della testata resta senza righe; la testata del test; quattro
errori del chiamante rifiutati.
