## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_ddt_riconsegna`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento funzioni:
>
> * [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna) — la madre da cui nasce la bolla
> * [dbops.fn_pgtap_crea_reso](/dbzero/dbops/funzioni/fn_pgtap_crea_reso) — il reso per ri-consegna da cui parte
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla avanti
> * [vendite.fn_annulla_ddt](/dbzero/vendite/funzioni/fn_annulla_ddt) — il verbo dell'annullo, che resta del test
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

La bolla che rimanda al cliente la merce di un reso per ri-consegna confermato, nello stato
chiesto (di norma **consegnata**), in una chiamata sola, per la strada vera del dominio.

---

### ⭐ Perché esiste, e perché è separata dal reso

Dopo un reso per ri-consegna i test generavano la bolla di ritorno e le riscrivevano a mano
indirizzo e causale, poi i passaggi fino a consegnata: la stessa trappola d'ordine della
bolla nata da un ordine. È una fixture a sé, e non un passo del builder del reso, perché i
test fanno più ri-consegne dallo stesso reso, a quantità e date diverse.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **La bolla** la fa la madre
  [vendite.fn_genera_ddt_riconsegna](/dbzero/vendite/funzioni/fn_genera_ddt_riconsegna):
  tutto ciò che il reso lascia da ri-consegnare, oppure una quantità di **una** riga del reso
  (riga e quantità vanno insieme, o nessuna delle due), alla data chiesta o alla data
  operativa. La madre copia causale e indirizzi dalla bolla d'origine e scrive il legame con
  la riga del reso.
* **Ciò che l'emissione pretende** e la madre non ha portato lo completa la fixture: la
  causale per codice (di norma `VENDITA`) **solo se manca**, e gli indirizzi obbligatori
  mancanti.
* **Lo stato** si raggiunge per la matrice dei passaggi, sotto i controlli veri.
* **Le regole** — reso confermato, tipo per ri-consegna, quantità ancora da ri-spedire — le
  giudica la madre, non la fixture: un reso a credito, che non ha niente da ri-consegnare, lo
  rifiuta la madre.

Restituisce la bolla, la sua **prima** riga con la quantità base e lo stato; con più righe il
test le legge da sé.

---

### ⛔ Non annulla

Uno stato abortito si rifiuta prima di costruire: la bolla di ri-consegna ha i legami, e il
suo annullo è del verbo [vendite.fn_annulla_ddt](/dbzero/vendite/funzioni/fn_annulla_ddt). Si
chiede la bolla emessa e si annulla dal test.

Uno stato o una causale che non esistono, e la quantità senza la riga (o il contrario),
fermano la fixture prima di costruire. Esce con i vincoli **richiusi** (`IMMEDIATE`), come
ogni helper di fixture.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-ddt-riconsegna-v1.sql` — la ri-consegna dell'intero
  reso, consegnata e legata alla riga del reso; causale e indirizzi completi; una parte di
  una riga a una data; il reso a credito rifiutato dalla madre; lo stato abortito e la
  quantità senza riga rifiutati.

---

### Note di migrazione

* 2026-10-25 — nasce per raccogliere la strada che i test ricopiavano
  (`brief-db-pgtap-reso-costruito`, D-3).
* 2026-10-27 — lo stato iniziale si legge dalla testata e non dal vocabolario
  (`brief-modello-documento-vendita` §15.13).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
