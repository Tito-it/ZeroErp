## 📘 Documentazione Concettuale – Funzione `anagrafiche.fn_ba_ha_storia_emittente`

> **Ultimo aggiornamento**: 26 novembre 2026
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

`anagrafiche.fn_ba_ha_storia_emittente` risponde sì o no: questo billing account ha già almeno un documento,
di qualunque famiglia e in qualunque stato, anche in bozza? È la definizione di «storia» che impedisce di
cambiargli l'azienda.

---

### Si ferma al primo documento

La domanda si fa quando l'azienda sul collegamento di un billing account cambia, tramite
`script.fn_check_ba_cambio_emittente`, e la stessa check la legge la lista dei collegamenti di un'azienda. Per
un sì basta un documento: la funzione guarda le famiglie una dopo l'altra ed esce al primo che trova. Il
conteggio per famiglia, che serve solo a scrivere il messaggio di rifiuto, lo fa la gemella
`anagrafiche.fn_get_storia_emittente_ba`, quando si è già deciso di rifiutare.

---

### Le famiglie vengono dal catalogo

Si guardano le famiglie attive di `vendite.famiglie_documento` che dichiarano la colonna del billing account:
una famiglia senza cliente non può dare storia a nessun cliente, e resta fuori dalla scelta delle famiglie,
prima che si componga la lettura. Di ogni famiglia la tabella è quella della sua sorgente, e conta ogni
documento che porta il billing account: lo stato e il numero non si guardano. Una famiglia attiva la cui
tabella non si trova fa fallire la lettura invece di sparire dal controllo.

Un billing account assente risponde no: la riga senza billing account è l'azienda predefinita, che non è il
cliente di nessuno, e spostarla non cambia l'azienda di nessun billing account.

---

### ⭐ Anche una bozza conta

Una bozza è già un documento di quell'azienda: ogni documento di vendita, fattura compresa, è emesso
dall'azienda del suo billing account (`script.trgfn_doc_guard_emittente_ba`). Spostare il cliente lascerebbe la
bozza a un'azienda che non lo vede più. La finestra di correzione resta finché il billing account non ha nessun
documento: chi ha sbagliato azienda cancella prima i documenti.

---

### ⭐ Coi privilegi del proprietario

Fatture e commesse hanno regole di visibilità per azienda. Coi permessi di chi chiama, la storia presso
un'altra azienda sarebbe invisibile e la risposta sarebbe «nessuna storia» proprio nel caso da fermare.

---

### Test

* `db/pgtap/anagrafiche/test-ba-storia-qualunque-documento-v1.sql` — un DDT in bozza fa già storia e il cambio
  è respinto; emesso, la storia lo conta sotto la sua famiglia e il cambio resta respinto.
* `db/pgtap/anagrafiche/test-billing-account-sempre-collegato-v1.sql` — senza documenti il billing account
  cambia azienda modificando il collegamento; con una fattura in bozza il cambio è respinto.
* `db/pgtap/anagrafiche/test-ba-cambio-emittente-storia-v1.sql` — un billing account appena nato non ha
  storia; dopo una commessa sì.
* `db/pgtap/vendite/test-famiglie-documento-crud-v1.sql` — una famiglia attiva senza billing account non rompe la lettura.

---

### Note di migrazione

* 2026-08-31 — nasce con la storia «documento numerato di qualunque famiglia»; prima si contavano fatture e
  commesse, anche in bozza.
* 2026-09-14 — le famiglie senza billing account restano fuori.
* 2026-10-20 — la tabella di ogni famiglia è quella della sua sorgente.
* 2026-11-26 — la storia diventa «qualunque documento, anche in bozza»: prima contava solo il documento
  numerato, e una bozza lasciava aperto il cambio d'azienda.

---

{% include-markdown "it/dbzero/anagrafiche/_emittente-del-billing-account.md" %}

---

{% include-markdown "signature-core.md" %}
