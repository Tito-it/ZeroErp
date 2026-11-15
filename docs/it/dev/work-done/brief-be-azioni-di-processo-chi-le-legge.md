# Brief BE — Ogni azione di processo ha chi la legge, e ogni azione dichiarata esiste

## ⏭️ Chi riparte — aggiornato al 2026-11-14

✅ **Chiuso il 2026-11-14** e archiviato (via di Tid). I tre presidi di §3 sono scritti e verdi (§5); nello
stesso giro, `AZIONE_OVERRIDE_PREZZO` ha una sede sola (§5). Il lato DB non ha avuto niente da fare.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Censimento in sola lettura; la guida dei permessi corretta | §2, §4 | — |
| 2 | ✅ team BE | I presidi P-1, P-2, P-3 (2026-11-14) | §3, §5 | 1 |
| 3 | ✅ Tid | Esito dei test, archiviazione (2026-11-14) | §5 | 2 |

**Decisioni aperte di Tid**: nessuna. **Da committare**: questo brief, la guida (§4), i presidi e la costante (§5).

**Brief vicini verificati**: `permessi-e-autorizzazioni-v3.md` (dormiente, tratta i sotto-oggetti: un
altro tema). Il gemello chiuso è
[brief-db-be-fe-catalogo-oggetti-permessi](brief-db-be-fe-catalogo-oggetti-permessi.md):
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

## 5. Consegnato (team BE, 2026-11-14)

Un file, accanto al gemello delle aree:
`backend/apps/core/tests/db/test_azioni_processo_dichiarate_e_lette.py`.

* **P-1 e P-2 senza DB** (`AzioniDichiarateTests`): le view dal percorso reale
  (`classi_view(anche_condizionali=True)`), le dichiarazioni lette con `getattr` come la catena
  (`<chiave>_permission`, escluso `model_permission`, e `<chiave>_passaggio`); il catalogo dal seed
  col BB `seed_csv`.
* **Le chiamate a `check_azione` dal sorgente (AST)**: l'argomento si risolve come lo risolve Python,
  un letterale o una costante di modulo (le `AZIONE_*`). Un argomento che non si risolve così è un
  rosso, salvo che la funzione che lo contiene stia nel registro `_INOLTRI`, che dice da dove
  arrivano i valori: la catena dei permessi (`ZeroERPPermission.valuta`, valori presi dalle view) e
  `_require_any_action` di `ui/api/views_admin.py` (valori dalle liste dei suoi chiamanti). Un
  registro senza righe morte ha il suo test.
* **P-3 sul DB vero** (`AzioniLetteTests`, opt-in `ZEROERP_TEST_DB_E2E=1`): le matrici per nome di
  colonna in `information_schema.columns`; i corpi con `pg_get_functiondef`, cercando il codename
  come letterale (`quote_literal`). Fuori dalla ricerca: le funzioni delle estensioni e gli helper
  `fn_pgtap_*`, che costruiscono fixture. Il registro `_SEDE_PER_DOPO` porta solo `processo_avvia`,
  col motivo; un test pretende che la riga esca quando l'azione trova un lettore.
* **Ognuno visto rosso**: una view finta (`AdminAPIView` con `post_permission`, e con
  `post_passaggio`), un'azione inventata e una spenta, una riga del registro senza motivo. Sul DB:
  tolto `processo_avvia` dal registro, P-3 la segnala.
* **Ritirato** (regola del 2): l'asserzione puntuale di `test_processi_esegui_ora_api.py`, test 3.
* **Una costante, una sede** (regola del 2, ok Tid 2026-11-14): `AZIONE_OVERRIDE_PREZZO` era definita
  due volte, in `_pricing_gate_helpers.py` (la copia, «per evitare cicli di import») e in
  `_approvazioni_prezzo_constants.py`. Il modulo delle costanti non importa niente, quindi il ciclo non
  c'era: resta lì, accanto a `AZIONE_APPROVA_PREZZO`, e il gate L1 la importa. L'ha trovata la scansione
  di P-2, che leggeva tutte e due le copie.

Fatto datato, 2026-11-14, su dbdev: 38 azioni attive; 29 nominate dal backend, 8 solo dalle matrici,
`blocca_merce` e `registra_magazzino` anche dai corpi delle funzioni; senza lettore solo
`processo_avvia`.

## 6. Revisione (2026-11-14)

* 🔴 **Trovato e corretto un cancello decorativo sulla catena**, che P-1 come era scritto non vedeva:
  `ApiFondoFatturaDelete` (`vendite/api/views_fondi_fattura.py`) serve solo `DELETE` e dichiarava
  `post_permission = "governa_fondo_fattura"`. La catena legge `<chiave>_permission` con la chiave della
  richiesta (`delete`): l'azione `pericolosa` non la chiedeva nessuno, e cancellare un fondo passava col
  solo livello sull'area vendite. Ora `delete_permission`. Il test della view pinnava il **nome**
  dell'attributo, ed era per questo verde: sostituito con uno sul comportamento di
  `ZeroERPPermission.valuta` per un `DELETE` (livello d'area pieno, azione negata → 403), visto rosso col
  codice di prima.
* **P-1 allargato**: su una view della catena una dichiarazione sta solo su una chiave che la view serve
  (il metodo HTTP che implementa, o l'action del viewset). Test 2b sul percorso reale e 2c su due view
  finte; il 2b era rosso su `ApiFondoFatturaDelete` prima della correzione.
* **P-3**: le matrici sono le sole **tabelle** con la colonna `azione_processo_codename`. Una vista che
  la proiettasse dal catalogo avrebbe dato un lettore a ogni azione.
* Allineati `api.md` (§ fondi fattura), `backend/vendite/manual/api_fondi_fattura.md`, il commento di
  `FondiFatturaDaDecidereTab.vue` e la guida dei permessi (§ presidi).
