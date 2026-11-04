## 📘 Documentazione Concettuale – Funzione `dbops.fn_pgtap_crea_fattura`

> **Ultimo aggiornamento**: 4 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.fatture](/dbzero/vendite/tabelle/fatture) — la testata che la fixture scrive
> * [vendite.fatture_indirizzi](/dbzero/vendite/tabelle/fatture_indirizzi) — gli indirizzi congelati, che si possono togliere
> * [config.stati_doc_fiscale](/dbzero/config/tabelle/stati_doc_fiscale) — gli stati e il confine del congelamento
>
> Approfondimento funzioni:
>
> * [dbops.fn_pgtap_cliente_del_builder](/dbzero/dbops/funzioni/fn_pgtap_cliente_del_builder) — il cliente su cui la fattura nasce
> * [script.fn_pgtap_registro_fattura](/dbzero/script/funzioni/fn_pgtap_registro_fattura) — il registro coerente con l'emittente di chi agisce
> * [vendite.trgfn_fatture_guard_registro_emittente](/dbzero/vendite/funzioni/trgfn_fatture_guard_registro_emittente) — il guard che rifiuta un registro di un'altra azienda
> * [vendite.fn_snapshot_indirizzi_fattura](/dbzero/vendite/funzioni/fn_snapshot_indirizzi_fattura) — gli indirizzi che l'uscita dalla bozza pretende
> * [vendite.fn_snapshot_intestazione_fattura](/dbzero/vendite/funzioni/fn_snapshot_intestazione_fattura) — l'intestazione che l'uscita dalla bozza pretende
> * [dbops.fn_pgtap_porta_a_stato](/dbzero/dbops/funzioni/fn_pgtap_porta_a_stato) — il passaggio di stato per la matrice
> * [anagrafiche.fn_parametri_importo_utility](/dbzero/anagrafiche/funzioni/fn_parametri_importo_utility) — i parametri che valgono senza la coppia (emittente, utility)
>
> Guide:
>
> * [pgTAP — come si scrive un test](/guide/pgtap-come-si-scrive-un-test) — dove si sceglie una fixture

---

### 🎯 Scopo Principale

Fixture pgTAP: **una fattura del mondo in una chiamata** — l'azienda con il suo operatore, il
cliente fatturabile, il registro coerente e la testata nello stato scelto. Restituisce tutte le
chiavi.

---

### ⭐ Una fattura è una catena, non un `INSERT`

Ogni anello è una cosa che chi scrive il test non può indovinare:

1. il cliente va legato all'azienda di **chi agisce** — lo fa un trigger, guardando la sessione —
   quindi il contesto va aperto prima (senza un conto del test la fixture lo apre da sé);
2. il registro dipende dall'emittente di chi agisce: uno di un'altra azienda lo rifiuta un guard;
3. la valuta si risolve lungo la catena «cliente → azienda → gestore»: su un database ricostruito
   nessuno dei tre anelli regge da solo.

La coppia (emittente, utility) **non si scrive**: senza la sua riga valgono i parametri di sistema
dell'utility, e una testata fiscale non la pretende. Scriverla nasconderebbe ai test proprio il
caso dell'emittente nuovo.

Tipo documento e valuta si scelgono dal catalogo con un ordine stabile: il primo attivo, la prima
per id.

---

### La seconda fattura dello stesso cliente

Senza conto di fatturazione ogni chiamata costruisce un cliente nuovo, nella stessa azienda. Un
test che vuole due fatture dello stesso cliente passa il conto della prima, e la fixture non
costruisce un cliente in più. Il conto viene verificato: uno di un'altra azienda la ferma subito,
invece di produrre una testata che un guard rifiuterebbe più avanti.

---

### Lo stato: nasce in bozza, poi si porta avanti

La fattura nasce nello stato iniziale. Lo stato chiesto si giudica prima di costruire (un codice
che non esiste ferma la fixture); se non è l'iniziale, la fixture scrive indirizzi e intestazione
coi building block, come fa la fatturazione prima di emettere, e porta la fattura avanti per la
matrice dei passaggi, sotto i controlli veri. Un passaggio che pretende ciò che la fixture non
scrive (righe con IVA, scadenze, numero) fallisce: il test lo scrive e porta avanti da sé.

---

### Fuori bozza, senza indirizzi o senza intestazione

Alcuni test vogliono proprio una fattura **già fuori bozza ma senza indirizzi**, o **senza
intestazione**: è il caso che provano (il controllo d'uscita dalla bozza, il blocco dei dati
collegati, l'intestazione mancante). La fattura esce dalla bozza completa, si ferma nell'ultimo
stato non ancora congelato del percorso (lo dice il vocabolario degli stati con `congela_fiscale`),
lì perde indirizzi e/o intestazione e poi arriva allo stato chiesto.

Chiedere di spogliare una fattura che resta in bozza ferma la fixture: la bozza nasce già senza.

---

### Minimo, totale a pagare, termine e utility

* Il flag `minimo`, il totale da pagare e il termine di pagamento si scrivono **alla nascita**: i
  test dei fondi li fissano lì, e un ritocco dopo la nascita sarebbe una strada che il dominio non
  fa. Vuoti: `minimo` falso, totale e termine vuoti.
* A richiesta la fattura nasce **senza utility**: la colonna lo ammette, ed è un caso dei test dei
  fondi. Una fattura con un'utility diversa da quella del cliente la scrive il test.

---

### Che cosa non scrive

Entra ciò che ha una trappola d'ordine, non ciò che serve spesso: righe, scadenze, contabili e
movimenti sono il caso del test, che li scrive coi propri importi. Esce con i vincoli richiusi
(`IMMEDIATE`); chi ha bisogno della finestra differita la riapre subito dopo.

---

### Test

* `db/pgtap/dbops/test-fn-pgtap-crea-fattura-v1.sql` — la testata esiste e porta registro e conto
  tornati; il registro è dell'azienda di chi agisce; la coppia (emittente, utility) non è scritta;
  lo stato è quello chiesto; il terzo parametro riusa il cliente; uno stato inesistente parla; fuori
  bozza indirizzi e intestazione ci sono, e con la spoliazione mancano (tutti e due, o i soli
  indirizzi); spogliare una bozza parla; minimo, totale e termine scritti alla nascita; la fattura
  senza utility.

---

### Note di migrazione

* 2026-09-23 — nasce con il secondo giro delle fixture che costruiscono
  (`brief-db-fixture-che-costruiscono-giro-2`): nove file di `db/pgtap/pagamenti/` pescavano la
  catena e morivano su un database ricostruito.
* 2026-10-21 — la coppia (emittente, utility) non si scrive più (`brief-db-modelli-documento-standard`, R-4).
* 2026-10-22 — la verifica del conto passa al building block comune delle fixture.
* 2026-10-24 — nascita in bozza e passaggio per la matrice; spoliazione; minimo, totale e termine;
  fattura senza utility; col conto del test non costruisce più un cliente in più
  (`brief-modello-documento-vendita`, N-1, Q-2, R-5, §4-octies).
* 2026-10-27 — lo stato iniziale si legge dalla testata, non dal vocabolario.

---

{% include-markdown "it/dbzero/dbops/_fixture-pgtap.md" %}

---

{% include-markdown "signature-core.md" %}
