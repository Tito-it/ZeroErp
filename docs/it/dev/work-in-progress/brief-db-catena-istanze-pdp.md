# Brief DB — La catena delle istanze su un PDP: quando un anello esce o entra

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-05. **A chi:** Tid (analisi, decisioni aperte
> di §6, poi apply e pgTAP).
> **Origine:** censimento `UPDATE OF` di
> [brief-db-esclusioni-implicite.md](../work-done/brief-db-esclusioni-implicite.md) §6.2, verificato il
> 2026-10-05. Tid (stesso giorno): «l'osservazione va risolta, anche il difetto del cliente».
> Voce **D18** di [migliorie-generali-da-test-valutazione.md](migliorie-generali-da-test-valutazione.md).
> ⚠️ **Eredità del 2026-10-14/15:** `trgfn_clienti_set_parent_istanza` è stato riscritto da
> `20261014-17` per la catena delle istanze **fittizie** (C-9 di
> [brief-db-cliente-manuale-uno-per-soggetto-e-utility](../work-done/brief-db-cliente-manuale-uno-per-soggetto-e-utility.md)):
> il corpo di partenza è quello della doc auto-generata, e i difetti di §2 valgono anche per quel ramo.
> **Stato:** 📝 **proposta da analizzare**. Niente scritto in `migrations_v2/`.

## 1. In parole semplici

Su un punto di fornitura (PDP) si succedono nel tempo più clienti: chi entra in un appartamento
subentra a chi c'era prima. Il DB tiene questa successione come una **catena**: l'istanza di
ogni cliente punta a quella del cliente precedente sullo stesso PDP
(`istanze_utilities.parent_istanza_id`). La catena serve al subentro: per esempio il catasto
dell'immobile si copia dall'istanza precedente
(`trg_iu_z50_clone_catasto_from_parent_aft_upd`).

Oggi la catena la calcola un trigger sul cliente, e ha due difetti:

1. **Annullare un cliente non lo toglie dalla catena.** Il trigger non scatta (§2.1).
2. **Anche quando scatta, ricalcola un anello solo:** quello del cliente toccato. Chi lo segue
   sullo stesso PDP continua a puntare all'anello vecchio (§2.2).

C'è poi un terzo difetto, fin qui mai notato: il calcolo **vede solo i clienti dell'azienda di
chi lavora** (§2.3).

## 2. Il difetto

### 2.1 Il trigger non scatta all'annullamento

`trg_clienti_z10_set_parent_istanza_ins_upd` è `BEFORE INSERT OR UPDATE OF pdp_id,
data_attivazione`. Quando si annulla un cliente, nel `SET` c'è `stato_cliente_id`. Poi
`trgfn_clienti_set_periodo`, che è `BEFORE` e per nome viene prima, azzera `data_attivazione`.
Con un `UPDATE OF`, le colonne cambiate da un altro trigger `BEFORE` non contano (linee-guida-trigger
§«Scelta tra `UPDATE` vs `UPDATE OF colonna`»): il trigger non scatta.

`trgfn_clienti_set_parent_istanza` ha **due rami scritti apposta** per il cliente annullato
(`data_attivazione IS NULL` e stato `AN` → `parent_istanza_id = NULL`). Su un UPDATE non ci arriva
mai. Li raggiunge solo un INSERT, e lo stesso vale per il pgTAP
`anagrafiche/test-istanza-cliente-chain`, che prova l'`AN` solo in INSERT.

Lo stesso buco c'è su `pdp_id`. Sul cliente è una **copia** della colonna dell'istanza, che
`trgfn_clienti_sync_pdp` (`BEFORE`) riscrive a ogni INSERT/UPDATE: chi aggiorna un cliente non la
mette mai nel `SET`. Ne soffre anche `trg_clienti_a20_sync_stato_pdp_aft_ins_upd`
(`AFTER … UPDATE OF stato_cliente_id, pdp_id`), vedi §5.

### 2.2 Un anello si ricalcola da solo, la catena no

La funzione scrive **un** `parent_istanza_id`: quello dell'istanza del cliente in `NEW`. Però la
posizione di un cliente nella catena decide anche il padre **del suo successore**. Ogni evento che
sposta un anello lascia sbagliato il vicino:

| Evento sul cliente B, in catena A → B → C | Il padre di C dovrebbe essere | Oggi resta |
| --- | --- | --- |
| B annullato | A | B |
| B inserito dopo C, con `data_attivazione` fra A e C | B | A |
| `data_attivazione` di B spostata oltre C | B | B, e B ora punta a C: due anelli si puntano a vicenda |
| B riattivato da `AN` | B | A |
| B passa a un altro PDP (l'istanza cambia `pdp_id`) | A | B, cioè un'istanza di un altro PDP |
| B cancellato (GUC di manutenzione; l'istanza di B resta) | A | B, un'istanza che non ha più un cliente |

Sono casi del **modello**: gli stati, le date e il PDP sono colonne che si possono scrivere. Che
oggi si presentino o no non cambia la regola.

### 2.3 Il calcolo legge sotto RLS

`trgfn_clienti_set_parent_istanza` è INVOKER e cerca il predecessore in `anagrafiche.clienti`, che
ha la policy `rls_clienti_ef_whitelist` (`fn_scope_ef_whitelist_via_efba`). Un operatore vede solo
i clienti delle sue aziende. Su un PDP però il subentro **attraversa le aziende**: chi subentra può
comprare da un altro emittente. Il predecessore che il trigger non vede non esiste per il calcolo, e
l'istanza viene agganciata all'anello sbagliato, oppure a nessuno.

La catena è un **dato derivato da tutte le righe del PDP**. Va calcolata guardando tutte le righe,
non quelle che chi lavora può leggere.

## 3. La forma proposta

### 3.1 Un ricalcolo della catena intera, per PDP

`anagrafiche.fn_ricalcola_catena_istanze_pdp(p_pdp_id bigint) RETURNS void`:

* **Una sola regola, in una query sola.** Fra i clienti del PDP sono anelli validi quelli con
  `data_attivazione IS NOT NULL` e stato diverso da `AN`. Ordinati per
  `(data_attivazione, id)`, ogni anello ha come padre l'istanza del precedente (`lag()`). Le
  istanze dei clienti non validi del PDP prendono `NULL`.
* **Scrive solo dove cambia** (`IS DISTINCT FROM`): un ricalcolo che non sposta niente non tocca
  righe e non sveglia il clone del catasto.
* **`SECURITY DEFINER`** del proprietario, con `search_path` blindato. Il perimetro è stretto: un
  `pdp_id` in ingresso, una colonna scritta, nessun dato restituito. Non dà a chi chiama niente
  che non potesse già causare aggiornando il proprio cliente. EXECUTE revocato a `PUBLIC` e a
  `zeroerp_app`: la chiama solo il trigger.
* **Serializzata per PDP** con un advisory lock transazionale a due argomenti (namespace +
  `p_pdp_id`), così due transazioni sullo stesso PDP non calcolano due catene diverse sulla
  stessa fotografia.

La regola «anello valido» compare oggi anche in `script.fn_subentro_cliente`, che cerca il
cliente aperto da chiudere. È una domanda diversa: lì serve anche `data_chiusura` e si cerca
**strettamente prima** della nuova data. Non è una copia da ritirare. Va però detto nel commento
delle due funzioni, perché se un giorno cambia il significato di «anello valido» si devono
toccare tutte e due.

### 3.2 Il trigger: `AFTER`, senza `OF`, sui due PDP

Al posto di `trg_clienti_z10_set_parent_istanza_ins_upd` (`BEFORE`, che dava per scritto lo stato
della riga mentre gli altri `BEFORE` lo stavano ancora cambiando):

* `trg_clienti_z10_ricalcola_catena_istanze_aft_ins_upd_dlt`, **`AFTER INSERT OR UPDATE OR
  DELETE … FOR EACH ROW`**;
* sull'UPDATE, `WHEN (OLD.pdp_id IS DISTINCT FROM NEW.pdp_id OR OLD.data_attivazione IS DISTINCT
  FROM NEW.data_attivazione OR OLD.stato_cliente_id IS DISTINCT FROM NEW.stato_cliente_id)`. In un
  `AFTER` il `NEW` è quello finale, compreso ciò che hanno scritto `set_periodo` e `sync_pdp`;
* ricalcola `NEW.pdp_id` e, se diverso, `OLD.pdp_id`: il PDP che l'anello lascia ha un buco da
  chiudere.

Sulla DELETE la FK `fk_istanze_utilities_parent_istanza` non c'entra: sta su `istanze_utilities`,
e cancellare un cliente non cancella la sua istanza. Il ricalcolo parte dai clienti del PDP:
l'istanza rimasta senza cliente esce dal suo perimetro e tiene il padre che aveva. Va deciso se
staccarla (`NULL`) leggendo anche le istanze del PDP senza cliente (D-5).

`trgfn_clienti_set_parent_istanza` si ritira: DROP del trigger e della funzione, e cancellazione
del suo `manual/`, se c'è.

### 3.3 La copia `pdp_id`: istanza → cliente

Se `istanze_utilities.pdp_id` cambia, oggi `clienti.pdp_id` resta vecchio fino al prossimo UPDATE
del cliente, e la catena con lui. Due strade (decisione D-2 in §6):

* **(a)** `istanze_utilities.pdp_id` non si cambia più quando l'istanza ha un cliente: un guard con
  il suo codice errore. Il cambio di PDP diventa un'istanza nuova, come un subentro;
* **(b)** un trigger `AFTER UPDATE` su `istanze_utilities` (senza `OF`, `WHEN (OLD.pdp_id IS DISTINCT
  FROM NEW.pdp_id)`) riallinea `clienti.pdp_id`, e da lì la catena si ricalcola da sola.

Raccomandazione: **(a)**. Un PDP è un luogo fisico, e un'istanza che cambia luogo è un'altra
istanza. (b) tiene viva una copia e fa del cambio di PDP un evento a catena su due tabelle.

## 4. Ricadute da controllare

* **Clone del catasto.** Con il ricalcolo, un'istanza senza catasto che riceve un padre nuovo
  clona il catasto da lì: è proprio il subentro. Un'istanza che il catasto l'ha già (clonato dal
  padre vecchio) lo tiene, per via dell'idempotenza di `fn_clone_catasto_from_parent_by_istanza`.
  Sullo stesso PDP l'immobile è lo stesso, quindi è corretto. Va scritto nel commento del trigger.
  Il clone gira sotto RLS dentro un ricalcolo DEFINER, quindi come proprietario: va verificato
  che `catasto_unita_immobiliari` non abbia guard che leggono l'utente.
* **Le viste** `vw_istanze_utilities_dettaglio` e `vw_istanze_dati_precontrattuali_dettaglio`
  espongono `parent_istanza_id`: il contratto non cambia, cambia solo che il valore è giusto.
* **I pgTAP che leggono la catena** (censiti il 2026-10-05): `anagrafiche/test-istanza-cliente-chain`,
  `anagrafiche/test-simula-subentro`, `anagrafiche/test-billing-account-guard-parent`. Le loro
  asserzioni devono restare verdi senza ritocchi: la regola dell'anello valido non cambia, cambia
  chi la applica e quando.
* **Il registro trigger**: un trigger nuovo scritto a mano su una tabella con automazioni va
  messo nel censo dei CHANGELOG (memoria «trigger a mano»).

## 5. Fuori perimetro, ma vicino

`trgfn_clienti_sync_stato_pdp` (`AFTER INSERT OR UPDATE OF stato_cliente_id, pdp_id`) porta il PDP
ad `ATT` o `DISP` quando il cliente è `AT` o `CH`, e non fa niente su `AN`. Un cliente annullato
lascia il PDP `ATT`. Ha anche lo stesso `OF pdp_id` di §2.1. Non è una questione di catena ma di
stato del PDP, quindi propongo di non metterla qui: Tid decide se aprirle un brief (D-4).

## 6. Decisioni aperte (Tid)

| # | Domanda | Proposta |
| --- | --- | --- |
| D-1 | Ricalcolo DEFINER su tutto il PDP (§3.1) al posto del calcolo INVOKER del singolo anello | sì |
| D-2 | La copia `pdp_id` istanza → cliente (§3.3) | (a) guard: un'istanza con un cliente non cambia PDP |
| D-3 | Le catene sbagliate già presenti nei dati di dev | a mano, con una chiamata al ricalcolo per ogni PDP; niente changeSet di bonifica (AGENTS.md, «bug di dati in sviluppo») |
| D-4 | Lo stato del PDP sull'annullamento (§5) | brief a parte |
| D-5 | L'istanza rimasta senza cliente dopo una DELETE (§3.2) | il ricalcolo legge anche le istanze del PDP senza cliente e le stacca |

## 7. Consegna prevista (dopo le decisioni)

| ChangeSet | Cosa |
| --- | --- |
| `20_code/anagrafiche/2026MMDD-NN-create-fn-ricalcola-catena-istanze-pdp` | la funzione DEFINER, REVOKE e COMMENT |
| `20_code/anagrafiche/2026MMDD-NN-create-trigger-clienti-ricalcola-catena-istanze` | il trigger `AFTER`, DROP di `z10_set_parent_istanza` |
| `20_code/anagrafiche/2026MMDD-NN-drop-trgfn-clienti-set-parent-istanza` | il ritiro della funzione vecchia |
| (D-2 a) `20_code/anagrafiche/…-guard-istanze-pdp-immutabile-con-cliente` + CSV `codici_errore`/`messaggi_errore` | il guard e il suo codice |

pgTAP nuovo, `anagrafiche/test-catena-istanze-pdp-v1`, che i soggetti **se li costruisce**:

1. struttura: il trigger è `AFTER`, senza colonne (`tgattr` vuoto), e la funzione è DEFINER;
2. A → B → C su un PDP; B passa da `AT` ad `AN` cambiando **solo** `stato_cliente_id` → B senza
   padre, C punta ad A;
3. B riattivato → C torna a B;
4. un cliente inserito fra A e C → C punta a lui;
5. `data_attivazione` di B spostata oltre C → A → C → B, senza cicli;
6. **due emittenti**: A dell'emittente X, B dell'emittente Y; l'operatore di Y (veste e utente
   impostati) crea B → B punta ad A, che lui non vede;
7. un UPDATE che non cambia né stato né date né PDP non riscrive nessuna istanza (letto dal
   `ctid`);
8. (D-2 a) cambiare `pdp_id` a un'istanza con un cliente → il codice nuovo.

Poi il censimento dei pgTAP di §4 e i due presidi per una funzione plpgsql nuova
(`dbops/test-riferimenti-morti-v1`, `script/test-catalogo-messaggi-errore-completo`).

## 8. Ricadute su BE/FE

Nessuna attesa: la catena è un dato che calcola il DB, il BE la legge dalle viste. Se D-2 diventa
(a) c'è un codice errore nuovo, che va in `error_policies_generated.py` come tutti.
