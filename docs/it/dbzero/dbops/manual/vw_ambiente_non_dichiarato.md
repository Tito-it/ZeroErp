## 📘 Documentazione Concettuale – Vista `dbops.vw_ambiente_non_dichiarato`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [dbops.installazione](/dbzero/dbops/tabelle/installazione) — la tabella che deve avere la sua riga
> * [dbops.presidi](/dbzero/dbops/tabelle/presidi) — il catalogo in cui la vista è un presidio
>
> Approfondimento funzioni:
>
> * [script.fn_ambiente_dichiarato](/dbzero/script/funzioni/fn_ambiente_dichiarato) — il lettore che la vista usa, e che non solleva
> * [script.fn_ambiente_installazione](/dbzero/script/funzioni/fn_ambiente_installazione) — il lettore che decide, e che senza ambiente fallisce
>
> Guide:
>
> * [Presidi e registri del debito](/guide/presidi-e-registri-del-debito) — come si legge un presidio che deve restare vuoto

---

### 🎯 Scopo Principale

Presidio: una riga, col nome del database, se questa installazione non ha ancora dichiarato se è
di sviluppo o di produzione. Deve restare vuota.

---

### ⭐ Un fatto, un presidio

La tabella [dbops.installazione](/dbzero/dbops/tabelle/installazione) nasce vuota di proposito:
l'ambiente si sceglie alla fase `post` del provisioning. Finché manca, tutto ciò che decide in base
all'ambiente fallisce con `E_CONFIG_MANCANTE`: il provisioning dei dati di sviluppo non parte, e le
sveglie dei processi spegnibili senza una scelta a mano non partono.

Ognuno di quei fallimenti dice il **sintomo**; questa vista dice la **causa**, una volta, a chi la
può sistemare. Per questo il panorama dei processi non ha una causa sua per l'ambiente mancante:
mostra `acceso` vuoto e lascia la diagnosi qui.

La vista legge `script.fn_ambiente_dichiarato`, che non solleva: un presidio che fallisse proprio
nel caso che deve mostrare sarebbe muto.

---

### Chi la guarda

Nel catalogo dei presidi è un presidio che deve restare vuoto, guardato ogni giorno; chi agisce è
chi gestisce il server. La vista gira coi privilegi del proprietario e non ha regole di riga:
l'ambiente non appartiene a nessuna azienda.

---

### Test

* `db/pgtap/dbops/test-installazione-ambiente-v1.sql` — vuota con l'ambiente dichiarato; con
  l'ambiente tolto (costruito) ha una riga col nome del database, e sparisce quando l'ambiente
  torna.
* `db/pgtap/dbops/test-etichette-di-prova-v1.sql` — con l'ambiente non dichiarato è questa vista,
  e non il presidio delle etichette, a dirlo.

---

### Note di migrazione

* 2026-10-16 — nasce con la tabella dell'ambiente (`brief-db-processi-accensione-per-ambiente`).

---

{% include-markdown "signature-core.md" %}
