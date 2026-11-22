## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_ba_ha_storia_emittente`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento) — le famiglie di documento da guardare
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_storia_emittente_ba](/dbzero/anagrafiche/funzioni/fn_get_storia_emittente_ba) — la gemella che conta, per la frase del rifiuto
> * [script.fn_check_ba_cambio_emittente](/dbzero/script/funzioni/fn_check_ba_cambio_emittente) — la check che la chiama
> * [anagrafiche.fn_guard_ba_cambio_emittente](/dbzero/anagrafiche/funzioni/fn_guard_ba_cambio_emittente) — il guard che solleva

---

### 🎯 Scopo Principale

`anagrafiche.fn_ba_ha_storia_emittente` risponde sì o no: questo billing account ha già almeno un documento
numerato su un registro? È la definizione di «storia» che impedisce di cambiargli l'azienda.

---

### Si ferma al primo documento

La domanda si fa a ogni movimento del collegamento di un billing account e, per ogni riga, dalla lista dei
collegamenti di un'azienda, che spegne il cestino dove lo spostamento non è ammesso. Per un sì basta un
documento: la funzione guarda le famiglie una dopo l'altra ed esce al primo che trova. Il conteggio per
famiglia, che serve solo a scrivere il messaggio di rifiuto, lo fa la gemella
`fn_get_storia_emittente_ba`, quando si è già deciso di rifiutare.

---

### Le famiglie vengono dal catalogo

Si guardano le famiglie attive di `vendite.famiglie_documento` che dichiarano la colonna del billing account:
una famiglia senza cliente non può dare storia a nessun cliente, e resta fuori dalla scelta delle famiglie,
prima che si componga la lettura. Di ogni famiglia la tabella è quella della sua sorgente, e «numerato» vuol
dire la colonna del numero valorizzata e non vuota. Una famiglia attiva la cui tabella non si trova fa fallire
la lettura invece di sparire dal controllo.

Un billing account assente risponde no: la riga senza billing account è la predefinita, e la guarda
`fn_guard_ba_gestore_globale_storia`.

---

### ⭐ Coi privilegi del proprietario

Fatture e commesse hanno regole di visibilità per azienda. Coi permessi di chi chiama, la storia presso
un'altra azienda sarebbe invisibile e la risposta sarebbe «nessuna storia» proprio nel caso da fermare.

---

### ⚠️ Che cosa oggi non copre

* **Una fattura in bozza porta già l'azienda** del suo billing account, e nessun controllo la riallinea quando
  il billing account cambia azienda: la bozza resta all'azienda di prima. È il prezzo scelto della finestra di
  correzione, che una bozza non chiude.

---

### Test

* `db/pgtap/anagrafiche/test-ba-storia-solo-numerati-v1.sql` — un DDT in bozza non fa storia e il cambio
  passa; emesso, prende il numero, la storia lo conta e il cambio è respinto.
* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` — un billing account appena nato non ha
  storia; dopo una commessa sì.
* `db/pgtap/vendite/test-famiglie-documento-crud-v1.sql` — una famiglia attiva senza billing account non rompe la lettura.

---

### Note di migrazione

* 2026-08-31 — nasce con la storia «documento numerato di qualunque famiglia»; prima si contavano fatture e
  commesse, anche in bozza.
* 2026-09-14 — le famiglie senza billing account restano fuori.
* 2026-10-20 — la tabella di ogni famiglia è quella della sua sorgente.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
