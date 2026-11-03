## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_listino`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.listini](/dbzero/vendite/tabelle/listini) — la testata che la fixture scrive
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — la versione, portata ad attiva
> * [config.listini_tipologie_utilities](/dbzero/config/tabelle/listini_tipologie_utilities) — le tipologie ammesse per utility
>
> Approfondimento funzioni:
>
> * [script.fn_pgtap_emittente_sr_operatore](/dbzero/script/funzioni/fn_pgtap_emittente_sr_operatore) — l'emittente di chi agisce
> * [dbops.fn_pgtap_crea_articolo](/dbzero/dbops/funzioni/fn_pgtap_crea_articolo) — l'articolo della riga d'appoggio
> * [dbops.fn_pgtap_listino_aggiungi_articoli](/dbzero/dbops/funzioni/fn_pgtap_listino_aggiungi_articoli) — la riga d'appoggio
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — l'attivazione dal verbo
> * [vendite.fn_attiva_versione_listino](/dbzero/vendite/funzioni/fn_attiva_versione_listino) — il verbo che attiva la versione
> * [script.fn_check_versione_listino_attivabile](/dbzero/script/funzioni/fn_check_versione_listino_attivabile) — quando una versione si attiva
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **un listino con una versione attiva**, dell'azienda di chi agisce, per l'utility
scelta dal test, con il periodo di validità che il test sceglie (di default da oggi, senza
scadenza).

`vendite.listini` è anagrafica: su un database ricostruito è vuota, e «il primo listino attivo»
non esiste. Restituisce il listino, la versione e la tipologia scelta.

---

### Le due cose che non si scelgono

* **L'emittente è quello di chi agisce.** Il listino ha un guard di perimetro che rifiuta un
  emittente fuori dall'azienda dell'operatore: il contesto va aperto **prima**, e senza contesto
  la fixture si ferma con un errore che lo dice.
* **La tipologia è la prima ammessa per l'utility**, nell'ordine del vocabolario. Non tutte le
  tipologie valgono per tutte le utility: una qualunque sbatterebbe sul guard di tipologia. Un'utility
  senza tipologie ammesse ferma la fixture con un errore che la nomina.

Il codice del listino è casuale: l'unicità del codice è globale, e una sigla fissa farebbe
collidere la seconda chiamata con la prima.

---

### ⚠️ La versione ha una riga d'appoggio

Una versione si attiva solo con un prezzo, e si attiva dal verbo. La fixture quindi fa nascere la
versione in bozza, le aggiunge **una riga d'appoggio** su un articolo suo (non gestito a
magazzino, della tipologia del listino, codice che comincia per `PGTAP_LST_ART_`) e la attiva con
`dbops.fn_pgtap_porta_a_stato`. Chi conta le righe della versione ne trova una in più.

La riga d'appoggio non ha periodicità. Se la tipologia scelta è di **quota fissa** e l'articolo
d'appoggio risulta una quota fissa a canone, l'attivazione rifiuta la versione
(`E_LISTINO_VERSIONE_QUOTA_FISSA_SENZA_PERIODICITA`) e la fixture si ferma lì.

---

### Che cosa non scrive

Le righe del listino che servono al test (prezzi, componenti, periodicità) e versioni in stati
diversi da attiva: sono il caso del test. Per mettere articoli nel listino c'è
`dbops.fn_pgtap_listino_aggiungi_articoli`.

---

### Test

Non ha un test suo: la presidiano i file che la usano, fra cui
`db/pgtap/dbops/test-fn-pgtap-crea-contratto-v1.sql`,
`db/pgtap/dbops/test-fn-pgtap-crea-commessa-attivita-v1.sql` e
`db/pgtap/vendite/test-listino-versione-al-modello-v1.sql`.

---

### Note di migrazione

* 2026-09-23 — nasce con il secondo giro delle fixture che costruiscono
  (`brief-db-fixture-che-costruiscono-giro-2`).
* 2026-10-28 — la versione non si scrive più direttamente attiva: nasce in bozza, prende la riga
  d'appoggio e si attiva dal verbo (`brief-modello-documento-vendita`, §16).

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
