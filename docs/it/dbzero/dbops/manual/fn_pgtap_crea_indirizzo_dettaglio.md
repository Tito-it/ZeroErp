## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_indirizzo_dettaglio`

> **Ultimo aggiornamento**: 7 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [anagrafiche.indirizzi_dettaglio](/dbzero/anagrafiche/tabelle/indirizzi_dettaglio) — l'indirizzo che la fixture fabbrica
> * [config.stradario](/dbzero/config/tabelle/stradario) — il seed su cui l'indirizzo si appoggia
>
> Approfondimento funzioni:
>
> * [anagrafiche.fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio) — il «trova o crea» di dominio, che la fixture non usa
> * [anagrafiche.trgfn_indirizzi_dettaglio_normalize](/dbzero/anagrafiche/funzioni/trgfn_indirizzi_dettaglio_normalize) — calcola le colonne normalizzate su cui sta l'unicità
> * [dbops.fn_pgtap_crea_pdp](/dbzero/dbops/funzioni/fn_pgtap_crea_pdp) — il punto di prelievo, su un indirizzo di questa fixture
> * [dbops.fn_pgtap_crea_magazzino](/dbzero/dbops/funzioni/fn_pgtap_crea_magazzino) — il magazzino, idem
> * [dbops.fn_pgtap_crea_operatore_umano](/dbzero/dbops/funzioni/fn_pgtap_crea_operatore_umano) — l'operatore umano, idem
>
> Guide:
>
> * [Come si scrive un test pgTAP](/guide/pgtap-come-si-scrive-un-test) — i dati di macchina si costruiscono, non si pescano

---

### 🎯 Scopo Principale

Un indirizzo di dettaglio per un test, fabbricato e non cercato: civico 99999 sulla prima
via viva di seed, con l'etichetta del test come interno. Ne torna l'id. Una via soppressa non si
usa: il guard del ritiro rifiuterebbe l'indirizzo.

---

### ⭐ L'indirizzo è dato di macchina: si fabbrica

`anagrafiche.indirizzi_dettaglio` è dato di macchina: su un database ricostruito non ce n'è
nessuno, e una fixture che ne cerca uno «attivo» muore prima di eseguire un'asserzione. Lo
stradario invece è seed, e c'è sempre: la fixture prende il primo per id, che serve solo come
ancora. Se lo stradario è vuoto solleva, perché è un seed che manca e non un dato di
macchina.

---

### ⚠️ La stessa etichetta dà lo stesso indirizzo

L'interno è l'etichetta troncata a **10 caratteri**, e l'unicità dell'indirizzo sta sulle
colonne normalizzate dal trigger (stradario, civico, estensione, palazzina, scala, piano,
interno, con i vuoti che contano come uguali). Una seconda chiamata con la stessa etichetta
trova la riga esistente e ne torna l'id, toccando solo la data di aggiornamento. Ne segue:

* due etichette che coincidono nei primi 10 caratteri, una volta normalizzate, danno lo
  **stesso** indirizzo;
* chi vuole indirizzi diversi deve dare etichette diverse entro quei 10 caratteri, come fa
  [fn_pgtap_crea_pdp](/dbzero/dbops/funzioni/fn_pgtap_crea_pdp), che ne usa una numerata.

⚠️ Il «trova o crea» è scritto qui, non preso da
[fn_get_or_create_indirizzo_dettaglio](/dbzero/anagrafiche/funzioni/fn_get_or_create_indirizzo_dettaglio):
una riga trovata ma disattivata la fixture la torna com'è, dove il building block di dominio
la riattiverebbe.

---

### 🚫 Non è un indirizzo vero

Serve a soddisfare un obbligo di indirizzo, non a provare gli indirizzi: un test che verifica
la normalizzazione o la geolocalizzazione si costruisce il suo.

---

### Codici errore

Uno stradario vuoto è un'eccezione senza codice, sollevata dalla fixture. Valgono i guard
dell'indirizzo di dettaglio.

---

### Test

* `db/pgtap/anagrafiche/test-indirizzi-dettaglio-unicita-v1.sql` — la stessa etichetta dà lo
  stesso id, etichette diverse danno id diversi, sull'indice di unicità di oggi.
* La usano come fixture i test di magazzino, del perimetro di magazzino sotto RLS e dei punti
  di prelievo.

---

### Note di migrazione

* 2026-09-15 — nasce, per i test di magazzino che cercavano un indirizzo esistente e su un
  database ricostruito non lo trovavano.
* 2026-10-25 — il «trova» segue il nuovo indice di unicità sulle colonne normalizzate.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
