## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_commessa`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — la testata che la fixture fa nascere
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — dove sta la sorgente principale
>
> Approfondimento funzioni:
>
> * [vendite.fn_get_or_create_commessa](/dbzero/vendite/funzioni/fn_get_or_create_commessa) — la madre che apre la commessa
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente su cui la commessa nasce
> * [dbops.fn_pgtap_crea_commessa_attivita](/dbzero/dbops/funzioni/fn_pgtap_crea_commessa_attivita) — l'attività che l'uscita dalla bozza pretende
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — il passaggio di stato per la matrice
> * [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — la porta del legame documento → commessa, che qui non si usa
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **una commessa del mondo in una chiamata** — l'azienda con il suo operatore, il
cliente fatturabile e la commessa aperta dalla madre del dominio, nello stato che il test chiede,
con competenza nel mese corrente. Restituisce tutte le chiavi, codice compreso, l'attività
scritta (se c'è) e lo stato raggiunto.

La commessa si scriveva a mano in molti pgTAP, con un codice inventato ed emittente e cliente
pescati dal database; altri chiamavano la madre ricopiando dieci argomenti. Era la stessa regola
scritta più volte: ora ha una sede.

---

### Che cosa decide la fixture e che cosa decide il dominio

* **Il cliente**: senza conto di fatturazione la fixture costruisce il mondo (e, senza contesto,
  apre il contesto sull'operatore che costruisce); con il conto di un'altra fixture prende
  l'azienda di chi agisce e verifica quel conto — uno di un'altra azienda la ferma subito.
* **La commessa** la apre `vendite.fn_get_or_create_commessa`, sempre nuova: **codice, emittente
  e stato iniziale li decide la madre**, come in produzione.
* **La competenza** è il mese corrente, così le attività della fixture gemella ci cadono dentro.

---

### Lo stato, l'attività e la sorgente principale

* **Lo stato chiesto** si giudica prima di costruire: un codice che non esiste ferma la fixture
  con un errore che la nomina. Vuoto, o lo stato iniziale: la commessa resta lì. Un altro: ci
  arriva per la **matrice dei passaggi**, con `dbops.fn_pgtap_porta_a_stato`, sotto i controlli
  veri.
* **L'attività**: una commessa esce dalla bozza solo con almeno una riga approvata. Se il test non
  dice niente, la fixture scrive **un'attività** approvata e non emessa prima del passaggio, ma
  solo quando lo stato chiesto non è l'iniziale; il test può chiederla sempre o mai. Senza
  attività l'uscita dalla bozza la ferma il controllo vero, non la fixture: è il caso del test
  che vuole provarlo.
* **La sorgente principale** (`ROOT`): il giro di fatturazione la pretende, e la madre non la
  scrive. A richiesta la fixture la scrive subito dopo la nascita: la commessa è la radice di se
  stessa, sorgente `COMMESSA`, chiave il suo id. La riga si scrive direttamente, non dalla porta
  `vendite.fn_link_commessa_sorgente`. Di default non la scrive.

---

### Che cosa non scrive

* le attività oltre la prima, e quelle con forme particolari (già emesse, da approvare, con altre
  quantità): sono il caso del test, o della fixture gemella;
* le altre sorgenti della commessa, cioè i documenti da cui nasce.

Esce con i vincoli richiusi (`IMMEDIATE`), come ogni fixture che apre una finestra differita.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-commessa-v1.sql` — la commessa esiste ed è quella
  tornata; l'emittente è quello del conto di fatturazione; la competenza è il mese corrente; il
  codice viene dal dominio; la seconda chiamata riusa l'azienda con un cliente nuovo; senza stato
  resta nell'iniziale senza attività; lo stato pronto per la fatturazione si raggiunge sul cliente
  chiesto con un'attività approvata; senza attività lo ferma il controllo vero; uno stato che non
  c'è parla; la sorgente principale c'è solo a richiesta, una sola e di tipo commessa.

---

### Note di migrazione

* 2026-10-07 — nasce con il terzo giro delle fixture che costruiscono documenti
  (`brief-db-fixture-rls-documenti-costruiti`).
* 2026-10-24 — lo stato chiesto, il conto del test e l'attività; a richiesta la sorgente
  principale, che tre pgTAP scrivevano a mano con la stessa riga; col conto del test non
  costruisce più un cliente in più (`brief-modello-documento-vendita`, Q-2, R-3, §4-octies).
* 2026-10-27 — lo stato iniziale si legge dalla testata, non dal vocabolario.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
