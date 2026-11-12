# Brief BE — Ogni azione di processo ha chi la legge, e ogni azione dichiarata esiste

## ⏭️ Chi riparte — aggiornato al 2026-11-12

**Riparte: team BE**, coi tre presidi di §3. Il lato DB non ha niente da fare: il catalogo e le
matrici esistono già.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Censimento in sola lettura; la guida dei permessi corretta | §2, §4 | — |
| 2 | **team BE** ⏭️ | I presidi P-1, P-2, P-3 | §3 | 1 |
| 3 | Tid | Esito dei test, archiviazione | — | 2 |

**Decisioni aperte di Tid**: nessuna. **Da committare**: questo brief e la guida (§4).

**Brief vicini verificati**: `permessi-e-autorizzazioni-v3.md` (dormiente, tratta i sotto-oggetti: un
altro tema). Il gemello chiuso è
[brief-db-be-fe-catalogo-oggetti-permessi](../work-done/brief-db-be-fe-catalogo-oggetti-permessi.md):
fa per gli **oggetti** quello che qui si chiede per le **azioni**.

## 1. Il problema

Un permesso d'azione si dichiara sulla view (`<metodo>_permission`, oppure l'azione della riga di
una matrice di transizioni tramite `<metodo>_passaggio`) e lo valuta `ZeroERPPermission`. Due
cose possono andare storte senza che nessun test diventi rosso:

* **un'azione dichiarata dove nessuno la valuta.** Su una `AdminAPIView` la permission class è
  `IsAdminZeroERP`, che risponde solo «SUPER_ADMIN o no»: un `post_permission` lì sembra un
  cancello e non lo è;
* **un'azione a catalogo che nessuno legge, o un'azione letta che non è a catalogo.** Nel primo
  caso il pannello la offre e concederla non cambia niente. Nel secondo `check_azione` risponde
  «no» a tutti tranne il SUPER_ADMIN, e nessun amministratore può concederla, perché non esiste la
  riga a cui appenderla. È lo stesso difetto che `core/tests/db/test_aree_dichiarate_a_catalogo.py`
  presidia per le aree.

## 2. Che cosa si sa, come fatto datato (2026-11-12)

Censimento in sola lettura: il dato non decide niente, dice solo che oggi non c'è un controesempio.

* Nessuna delle 91 view che discendono da `AdminAPIView` dichiara un `<metodo>_permission`. Il caso
  da cui nasce la richiesta (`processo_avvia` su «Esegui ora» dei processi) è chiuso in
  `amm_software/api/views.py`: la view resta `AdminAPIView`, non dichiara l'azione, e la docstring
  dice che la riga di catalogo è la sede per il giorno in cui il verbo si aprirà agli operatori. Lo
  presidia solo `test_processi_esegui_ora_api.py`, su quella view.
* Delle 38 azioni attive di `config.azioni_processo`, 31 sono nominate dal backend o dal corpo di
  una funzione del database. Sei sono lette dalle matrici delle transizioni (`emetti_ddt`,
  `emetti_preventivo`, `emetti_ordine`, `emetti_contratto`, `emetti_offerta`, `attiva_listino`).
  Resta senza lettore solo `processo_avvia`, dichiarata come sopra.

## 3. La richiesta: tre presidi

Elenco chiuso. Il posto naturale è accanto a `core/tests/db/test_aree_dichiarate_a_catalogo.py`,
con le view lette **dal percorso reale** (`apps.core.api.rotte`, `anche_condizionali=True`) e gli
attributi letti con `getattr`, come li legge la catena.

* **P-1 — Nessuna azione dichiarata dove non la valuta nessuno.** Una view la cui permission class
  non è `ZeroERPPermission` (per esempio una `AdminAPIView`) non dichiara né `<metodo>_permission`
  né `<metodo>_passaggio`. Generalizza l'asserzione puntuale di `test_processi_esegui_ora_api.py`,
  che a quel punto si ritira (regola del 2).
* **P-2 — Ogni azione dichiarata esiste a catalogo, attiva.** Ogni valore di `<metodo>_permission`
  e ogni letterale passato a `PermissionResolver.check_azione` corrisponde a un `permission_codename`
  attivo di `config.azioni_processo`. Il catalogo si legge dal CSV del seed
  (`80_data/sql/config/azioni_processo.csv`), così il test diventa rosso nella PR che rompe
  l'allineamento e non all'apply, come fa `test_catalogo_oggetti_rotte.py`.
* **P-3 — Ogni azione attiva ha almeno un lettore.** Un lettore è:
  * un `<metodo>_permission` o un `check_azione` del backend (P-2 li ha già raccolti);
  * una riga di una matrice di transizioni: ogni colonna `azione_processo_codename` del database,
    trovata per nome in `information_schema.columns` e non elencata a mano, così una matrice nuova
    entra da sola;
  * il corpo di una funzione del database che la nomina come letterale (`pg_get_functiondef`);
  * una riga di un registro `_SEDE_PER_DOPO`, col motivo, per le azioni seminate prima del loro
    verbo. Oggi ci sta solo `processo_avvia`. Un test del registro pretende che la riga esca il
    giorno in cui l'azione trova un lettore, come `_IN_ATTESA_DI_CATALOGO` nel gemello.

  P-3 ha bisogno del database: va sotto `ZEROERP_TEST_DB_E2E=1`, come il gemello delle aree.

Ognuno dei tre si vede rosso almeno una volta: una view finta con un `post_permission`, un'azione
inventata, una riga del registro senza motivo.

## 4. La guida

`docs/it/guide/architettura-permessi-e-autorizzazioni.md` §6.2 elencava tre permission class
«tutte delegate allo stesso resolver», senza `IsAdminZeroERP`. Corretta in questo giro: la quarta
classe, e la regola che un `<metodo>_permission` su una view di amministrazione non lo valuta
nessuno. Quando i presidi esistono, la guida li nomina.
