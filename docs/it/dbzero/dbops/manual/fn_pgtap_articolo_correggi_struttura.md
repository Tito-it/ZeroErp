## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_articolo_correggi_struttura`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [catalogo.articoli](/dbzero/catalogo/tabelle/articoli) — l'articolo i cui flag strutturali cambiano
>
> Approfondimento funzioni:
>
> * [catalogo.fn_articolo_correggi_struttura](/dbzero/catalogo/funzioni/fn_articolo_correggi_struttura) — il verbo amministratore che la fixture chiama
> * [catalogo.trgfn_articoli_guard_struttura_se_usato](/dbzero/catalogo/funzioni/trgfn_articoli_guard_struttura_se_usato) — il guard che quella porta apre
> * [dbops.fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano) — il super admin costruito che agisce
> * [script.fn_pgtap_set_contesto_operatore](/dbzero/script/funzioni/fn_pgtap_set_contesto_operatore) — la veste del super admin in sessione
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP che cambia i **flag strutturali di un articolo già usato** passando dalla porta
vera: il verbo amministratore, chiamato da un super admin costruito apposta.

Serve ai test che provano che cosa succede **a valle** quando un articolo cambia dopo l'uso: la
natura congelata sulle righe, la riconsegna esente, l'erogazione. Un articolo usato non cambia
quelle colonne (il guard di struttura lo rifiuta), e l'unica strada ammessa è il verbo del
super admin: la fixture prende quella.

---

### ⛔ Non aggira niente

La fixture è `SECURITY INVOKER` e non scrive l'articolo da sé: costruisce un operatore umano
super admin, gli apre la veste in sessione e chiama il verbo. Un helper `SECURITY DEFINER` che
saltasse la porta sarebbe una scorciatoia eseguibile dall'applicazione. Le colonne ammesse e i
rifiuti sono quelli del verbo.

---

### ⚠️ Rimette il contesto di chi chiama

Finito il verbo, la fixture rimette `app.current_user_id` e `app.ruolo_applicativo` ai valori
che avevano prima, anche se erano vuoti: il test riprende con la veste che aveva.

Ogni chiamata costruisce un super admin nuovo.

---

### Test

Non ha un test suo: la presidiano i file che la usano.

* `db/pgtap/vendite/test-righe-natura-vendita-congelata-v1.sql` — la natura resta quella
  congelata sulle righe dopo la correzione dell'articolo;
* `db/pgtap/vendite/test-fn-genera-ddt-riconsegna-eredita-v1.sql`,
  `db/pgtap/vendite/test-righe-erogazione-da-articolo-v1.sql`,
  `db/pgtap/vendite/test-righe-articolo-ammesso-v1.sql` — gli effetti a valle di un articolo
  corretto dopo l'uso.

---

### Note di migrazione

* 2026-10-13 — nasce con il guard di struttura degli articoli usati
  (`brief-db-articoli-ammessi-per-documento`, A-10).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
