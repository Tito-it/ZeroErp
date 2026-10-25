## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ddt_riconsegna`

> 👀 **Vedi anche**
>
> • [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) — la madre da cui nasce la bolla
>
> • [dbops.fn_pgtap_crea_reso](/dbzero/dbops/funzioni/fn_pgtap_crea_reso) — il reso per ri-consegna da cui parte
>
> • [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla avanti
>
Guide: [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) · brief `brief-db-pgtap-reso-costruito` (D-3)

---
### 🎯 Scopo Principale

(rev 2026-10-25)

**La bolla che rimanda al cliente la merce di un reso per ri-consegna, già consegnata, in
una chiamata sola.**

```sql
-- tutto il reso
CREATE TEMP TABLE tmp_ric AS
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna((SELECT reso_id FROM tmp_r));

-- una parte di una riga, a una data
SELECT * FROM dbops.fn_pgtap_crea_ddt_riconsegna(
           (SELECT reso_id FROM tmp_r), p_resi_riga_id => (SELECT resi_riga_id FROM tmp_r),
           p_quantita => 2, p_data => DATE '2026-09-01');
```

---
### 🧭 Perché esiste

Dopo un reso per ri-consegna i test generavano la bolla di ritorno e le riscrivevano a mano
indirizzo e causale, poi i passaggi fino a consegnata: la stessa trappola d'ordine della
bolla nata da un ordine. È separata dal builder del reso perché i test fanno più
ri-consegne dallo stesso reso, a quantità e date diverse.

---
### 🔗 Cosa decide la funzione e cosa decide il dominio

* **La bolla** la fa la madre `vendite.fn_genera_ddt_riconsegna`: tutto ciò che il reso
  lascia da ri-consegnare, oppure `p_quantita` della riga `p_resi_riga_id` (i due insieme),
  alla data `p_data`. La madre copia causale e indirizzi dalla bolla d'origine e scrive il
  legame con la riga del reso.
* **Ciò che l'emissione pretende** e la madre non ha portato lo completa il builder: la
  causale per codice (`p_causale_codice`, default `VENDITA`) solo se manca, gli indirizzi
  obbligatori mancanti.
* **Lo stato** (default `CONSEGNATO`) si raggiunge per la matrice dei passaggi, sotto i
  controlli veri.
* **Le regole** — reso confermato, tipo per ri-consegna, quantità ancora da ri-spedire — le
  giudica la madre.

---
### 🚫 Cosa NON fa

**Non annulla**: uno stato abortito si rifiuta prima di costruire. La bolla di ri-consegna
ha i legami, e il suo annullo è del verbo `vendite.fn_annulla_ddt`.

---
### ⚠️ Il contratto sui vincoli differiti

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---
### 🧪 Il presidio

`db/pgtap/dbops/test-fn-pgtap-crea-ddt-riconsegna-v1.sql` (7 casi): firma; ri-consegna
dell'intero reso, consegnata e legata; causale e indirizzi; una parte di una riga a una
data; il reso a credito rifiutato dalla madre; due errori del chiamante rifiutati.
