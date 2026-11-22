## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_get_storia_emittente_ba`

> **Ultimo aggiornamento**: 22 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.famiglie_documento](/dbzero/vendite/tabelle/famiglie_documento) — le famiglie contate, e le parole della frase
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_ba_ha_storia_emittente](/dbzero/anagrafiche/funzioni/fn_ba_ha_storia_emittente) — la gemella del sì o no
> * [script.fn_check_ba_cambio_emittente](/dbzero/script/funzioni/fn_check_ba_cambio_emittente) — compone il motivo del rifiuto con queste righe

---

### 🎯 Scopo Principale

`anagrafiche.fn_get_storia_emittente_ba` dice quanta storia ha un billing account e di che specie: una riga per
ogni famiglia di documento che ne ha almeno uno numerato, col conteggio. Nessuna riga vuol dire nessuna storia.

---

### Serve solo alla frase del rifiuto

La chiama `script.fn_check_ba_cambio_emittente` quando ha già deciso di rifiutare, dopo che
`fn_ba_ha_storia_emittente` ha risposto sì. Con più famiglie in gioco, il messaggio deve dire **quale**
documento blocca: una frase che nominasse solo le fatture manderebbe a cercarle a un cliente fermato da un DDT.
Le parole sono le descrizioni del catalogo (`famiglia_descrizione`), e il codice della famiglia
(`famiglia_documento`) è quello della sua sorgente: una famiglia nuova cambia la frase da sé.

Le famiglie a zero non escono, così chi compone la frase non filtra niente. Le righe vengono nell'ordine del
catalogo, e la check le tiene in quell'ordine.

---

### La stessa definizione della gemella

Conta ciò che la gemella trova: i documenti numerati delle famiglie attive che dichiarano il billing account,
nella tabella della loro sorgente. Le due funzioni leggono la stessa scelta delle famiglie, e una dice sì
quando l'altra restituisce almeno una riga. Un billing account assente non restituisce righe. Gira coi
privilegi del proprietario per la stessa ragione: la storia presso un'altra azienda non deve sparire sotto le
regole di visibilità.

---

### Test

* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` — nessuna riga per un billing account appena
  nato; una commessa conta sotto la sua famiglia, e la frase nomina la specie.
* `db/pgtap/anagrafiche/test-ba-storia-solo-numerati-v1.sql` — il DDT in bozza non conta, emesso conta sotto la
  sua famiglia.

---

### Note di migrazione

* 2026-08-31 — prende il posto della forma con due conteggi fissi, fatture e commesse; da allora le famiglie
  vengono dal catalogo, e la fattura in bozza non conta più.
* 2026-09-14 — le famiglie senza billing account restano fuori.
* 2026-10-20 — la tabella di ogni famiglia è quella della sua sorgente, e il codice della famiglia è quello
  della sorgente.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
