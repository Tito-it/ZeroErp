## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_offerta`

> **Ultimo aggiornamento**: 13 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.offerte_commerciali](/dbzero/vendite/tabelle/offerte_commerciali) — la testata che la fixture scrive
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente: il mondo, o quello di un'altra fixture
> * [dbops.fn_pgtap_crea_listino](/dbzero/dbops/funzioni/fn_pgtap_crea_listino) — il listino del mondo, quando il test non ne dà uno
> * [vendite.fn_doc_indirizzo_default](/dbzero/vendite/funzioni/fn_doc_indirizzo_default) — l'indirizzo di default, come alla creazione dal backend
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — la strada per portarla avanti
> * [dbops.fn_pgtap_crea_preventivo](/dbzero/dbops/funzioni/fn_pgtap_crea_preventivo) · [dbops.fn_pgtap_crea_contratto](/dbzero/dbops/funzioni/fn_pgtap_crea_contratto) — i fratelli
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — le fixture e quando usarle

---

### 🎯 Scopo Principale

Un'offerta commerciale del mondo, **senza eccezioni né righe**, in una chiamata sola: l'azienda
con il suo operatore, il cliente fatturabile, il listino e la testata nello stato scelto.
Restituisce le chiavi dell'offerta e del mondo, il listino e lo stato.

---

### ⭐ Perché esiste

I pgTAP che servono un'offerta la scrivevano a mano: la testata, il listino, la versione, lo
stato. Era la stessa regola, «come nasce un'offerta», scritta in molti file: ora ha una sede. I
test che la scrivono ancora a mano passano al builder quando un lavoro li riapre.

---

### Come nasce

* **Il cliente** viene da
  [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder): senza
  billing account costruisce il mondo, con il billing account di un'altra fixture prende
  l'azienda di chi agisce e verifica che quel cliente sia suo. Così più offerte stanno sullo
  stesso cliente.
* **Il listino** è quello del test, se lo dà; altrimenti uno del mondo per l'utility del cliente,
  con una versione attiva.
* **La testata** nasce come la crea il backend: senza stato (lo mette il trigger della nascita),
  senza versione di listino (la congela l'emissione), senza codice (lo genera il dominio), con la
  validità da oggi. Subito dopo, l'indirizzo di default dall'anagrafica del cliente, con la stessa
  chiamata che fa il backend.

---

### ⛔ Eccezioni, righe e scheda di fornitura non le scrive

Sono il caso del test. Un passaggio che le pretende si ferma: il test le scrive e porta avanti
l'offerta da sé.

---

### Nasce in bozza, poi si porta avanti

L'offerta nasce nello stato iniziale e, se il test chiede un altro stato, ci arriva per la
matrice dei passaggi ([dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato)),
dal verbo dell'offerta, sotto i controlli veri: l'emissione congela il listino, il rifiuto passa
con una motivazione della fixture. `SUPERATA` è di processo (nasce creando una revisione) e non si
raggiunge da qui.

Lo stato chiesto si traduce per codice **prima** di costruire, fra i soli stati attivi: uno stato
che non c'è, o che è spento, ferma la fixture subito, senza lasciare un mondo a metà.

Esce con i vincoli **richiusi** (`IMMEDIATE`), come ogni helper di fixture.

---

### Test

* `db/pgtap/vendite/test-offerta-guard-dal-vocabolario-v1.sql` — i test 1-3: l'offerta nasce nello
  stato iniziale; l'emissione congela la versione di listino; il rifiuto scrive la sua data. Le
  offerte del test stanno sul cliente della prima.

---

### Note di migrazione

* 2026-11-13 — nasce (`brief-db-stati-documento-dal-vocabolario`, giro 2).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
