### 🧩 Resta sempre almeno un SUPER_ADMIN che non scade

> **Ultimo aggiornamento**: 22 novembre 2026

Il sistema deve avere in ogni momento almeno un amministratore che entra **oggi e domani**: se l'ultimo si
spegnesse, nessuno potrebbe più accendere gli altri. La regola non conta gli amministratori «attivi», ma quelli
**senza scadenza**: una data che passa non scrive niente, e nessun guard può fermare il calendario. Per questo la
garanzia si chiede alla scrittura che **mette** la data di fine, finché resta almeno un amministratore che non ne
ha.

#### Che cosa vuol dire «SUPER_ADMIN senza scadenza»

Lo dice una funzione sola, `script.fn_identita_super_admin_senza_scadenza`, per una veste. Una veste lo è quando
tutte queste cose sono vere insieme:

* ha un legame attivo (`config.profili_accesso_bindings`) verso un profilo attivo di tipo `SUPER_ADMIN`; il profilo
  si riconosce dal tipo, non dal codice, che si può rinominare;
* è una veste `OPERATORE`;
* è **utilizzabile oggi**, secondo `script.fn_veste_utilizzabile`: accesa, dentro la sua finestra di date, col
  soggetto attivo e, per una persona, col rapporto di lavoro acceso e dentro la sua finestra. «Oggi» è il giorno
  operativo (`script.fn_data_operativa`), non la data del server;
* non ha una data di fine, né sulla veste né sul rapporto di lavoro (la riga di `anagrafiche.risorse_umane` dello
  stesso `soggetto_ruolo_id`);
* la sua credenziale non è bloccata dall'amministratore (`config.credenziali`).

Un amministratore che ha già una data di fine non conta: spegnerlo non riduce la garanzia, perché non la dava.
Un legame `SUPER_ADMIN` dato a un'unità organizzativa invece che a una veste non conta.

#### Due domande, un criterio

* `script.fn_check_almeno_un_super_admin_attivo` risponde alla domanda dei guard: dopo questa scrittura, esiste
  ancora almeno una veste senza scadenza? Non solleva errori: risponde `false` quando non ne resta nessuna.
* `script.fn_check_ultimo_super_admin_attivo` risponde per una credenziale: è l'unica che porta un SUPER_ADMIN senza
  scadenza? Serve al backend per sapere, prima di proporla, se un'azione sull'operatore sarebbe rifiutata (spegnerlo,
  togliergli il profilo). Con una credenziale nulla risponde `false`.

Tutte e due leggono la stessa funzione per la veste: una regola cambiata lì cambia per tutti i guard e per il
backend.

#### Quale scrittura, quale guard

Quattro guard presidiano le quattro strade da cui la garanzia si perde. Scattano tutti **dopo** la scrittura,
guardano solo le scritture che la riducono, e chiedono a `script.fn_check_almeno_un_super_admin_attivo` com'è il
sistema dopo; se non resta nessun amministratore senza scadenza, rifiutano con `E_PROFILO_ULTIMO_SUPER_ADMIN`.

| Scrittura | Che cosa la rende a rischio | Guard |
| --- | --- | --- |
| Modifica di una veste (`anagrafiche.identita_digitali`) | spegnerla, darle una data di fine, spostarne l'inizio oltre oggi; e solo se la veste ha un legame `SUPER_ADMIN` attivo | `anagrafiche.trgfn_identita_digitali_guard_ultimo_super_admin` |
| Modifica di un rapporto di lavoro (`anagrafiche.risorse_umane`) | spegnerlo, dargli una data di fine, spostarne l'inizio oltre oggi, spostarlo su un altro `soggetto_ruolo_id`; e solo se sul ruolo di prima c'è una veste `OPERATORE` con un legame `SUPER_ADMIN` attivo | `anagrafiche.trgfn_risorse_umane_guard_ultimo_super_admin` |
| Modifica o cancellazione di un legame (`config.profili_accesso_bindings`) | cancellarlo, spegnerlo, cambiarne il profilo o la veste; e solo se prima era attivo e puntava a un profilo `SUPER_ADMIN` | `config.trgfn_profili_accesso_bindings_guard_ultimo_super_admin` |
| Blocco di una credenziale (`config.credenziali`) | il passaggio da non bloccata a bloccata, anche una riga che nasce già bloccata; e solo se la credenziale porta una veste accesa con un legame `SUPER_ADMIN` attivo | `config.trgfn_credenziali_guard_ultimo_super_admin` |

⭐ Le scritture che **migliorano** la garanzia passano sempre, anche su un sistema già senza amministratori:
togliere una data di fine, riaccendere una veste o un rapporto, sbloccare una credenziale, aggiungere un legame.
È così che si esce da un sistema scoperto.

#### Le strade chiuse da altro

* **Spegnere il soggetto dell'amministratore** non passa: il soggetto non si spegne finché il rapporto è acceso, e
  il rapporto non si spegne finché la veste operatore è accesa («figli prima, padre poi»); la veste è presidiata.
* **Spegnere il profilo `SUPER_ADMIN`** non passa finché ha legami accesi.
* **Cancellare una veste** che ha un legame non passa: la chiave esterna del legame lo impedisce.

#### ⚠️ Che cosa oggi non vede

* **La veste che cambia credenziale, ruolo o tipo.** Il guard sulla veste guarda solo `attivo` e le due date.
  Spostare la veste dell'ultimo amministratore su una credenziale bloccata, su un `soggetto_ruolo_id` il cui
  rapporto ha una data di fine, o farla diventare una veste che non è `OPERATORE`, toglie la garanzia senza che
  nessun guard parli.
* **Il profilo che cambia tipo.** Un profilo `SUPER_ADMIN` portato a un altro tipo non scatta nessun guard: il
  guard sui legami scatta sui legami, non sul profilo.
* **La cancellazione del rapporto.** Il guard sul rapporto scatta sulla modifica. La cancellazione è bloccata, ma
  chi accende la porta di manutenzione che la consente può cancellare il rapporto dell'ultimo amministratore senza
  che la garanzia venga chiesta.
