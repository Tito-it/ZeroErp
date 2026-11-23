# Brief DB — magazzino: il lotto è dell'azienda

## ✅ Chiuso — 2026-11-22

> **Ultimo aggiornamento**: 22 novembre 2026

**Nessuno riparte.** Il lato DB (P-0 … P-5, `20261122-14` … `-19`) è applicato da Tid coi pgTAP
verdi; R-1 … R-5 e F-1 sono fatti dalla sessione BE/FE lo stesso giorno (§6, esiti in riga) ed
entrati in `Tito-dev` con la PR #209. Nessun debito residuo. Archiviato in `work-done/`.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | D-L1 = a, D-L2 = a, D-L3 = b, D-L4 = a; il via al P-0 | §4 | — |
| 1-bis | ✅ Tid | D-L5 = a, D-L6 = a; il via al P-1 | §5.1 | — |
| 2 | ✅ team DB | P-0 (§5.1); P-1 (§5.2); P-2 … P-4 (§5.3) | §5 | — |
| 3 | ✅ Tid | apply di P-1 … P-4 e di `-19`, pgTAP verdi col runner | §5.2, §5.3 | — |
| 4 | ✅ sessione BE / FE | R-1 … R-5; F-1 | §6, §6-bis | — |
| 5 | ✅ team DB | P-5; archiviazione | §5 | — |

Decisioni aperte di Tid: nessuna.

> **Brief vicini verificati (2026-11-22):**
> * [brief-db-magazzino-tutte-le-scritture-dal-verbo](brief-db-magazzino-tutte-le-scritture-dal-verbo.md) ha i verbi del lotto
>   (`fn_aggiungi_lotto`, `fn_modifica_lotto`) e la R-1 al BE che li adotta. Da lì nasce questo
>   brief (§5.3);
> * `work-in-progress/analisi-db-magazzino-carico-e-scarico` cita i lotti fra le tabelle «uguali
>   per tutti».
>
> Nessuno copre il tema.

---

**Chi scrive:** team DB (`dev/db-tid`), 2026-11-22. **A chi:** Tid (decisioni, §4), poi team DB;
🔵 richieste a BE in §6.

## 0. In due parole

Un **lotto** è una partita di merce, con un codice e una scadenza. Oggi un lotto appartiene solo
all'articolo, e gli articoli sono comuni a tutte le aziende del gestionale. Il lotto «L-123» di un
articolo è quindi uno solo per tutte le aziende. Da qui tre effetti:
* un'azienda può cambiare la scadenza di un lotto che usa un'altra;
* un'azienda non può disattivare un lotto che un'altra sta usando;
* due aziende non possono avere ciascuna il proprio «L-123» dello stesso articolo.

Tid ha deciso che ogni azienda gestisce i suoi lotti (2026-11-22). Il lotto prende l'azienda, come
i magazzini e i seriali.

## 1. La storia della decisione che si cambia

* **2026-09-14, Lotto 1 del magazzino**
  ([brief-db-magazzino-lotto-1-terreno-vuoto](brief-db-magazzino-lotto-1-terreno-vuoto.md),
  §4.3 e M-6). `magazzino.lotti` nasce **fuori dal perimetro RLS**, perché è «una definizione, non ha
  `magazzino_id`, e non ha FK verso tabelle protette». Unicità `(articolo_id, codice)`.
* **2026-09-21, backend.** `test_perimetro_emittente_copertura.py`: *«un lotto è dell'ARTICOLO, […] il
  perimetro emittente qui non esiste come dimensione»*. La lista si legge per articolo.
* **Guida del dominio** (`dbzero/magazzino/_dominio-magazzino.md`, §«Il perimetro»): i lotti restano
  fuori *«per costruzione»*, coi vocabolari.
* **2026-11-22**: chiudendo le scritture sui verbi (brief vicino, §5.3), il verbo di modifica vede i
  figli di tutte le aziende. Il lotto in comune diventa visibile come un fatto di dominio, e **Tid
  sceglie il lotto dell'azienda**.

Il ragionamento del 14-09 resta vero sulla forma: senza `magazzino_id` né emittente, il lotto non
aveva una riga da proteggere. Cambia la premessa di dominio: il lotto non è una definizione
dell'articolo, è un fatto dell'azienda che riceve o produce la merce.

## 2. Il punto di partenza — letto il 2026-11-22

Fatti datati, letti su dbdev. Si rifanno al P-0.

* **La tabella.** `magazzino.lotti(id, articolo_id NN, codice NN, data_arrivo NN, data_scadenza,
  attivo, meta, …)`, `UNIQUE (articolo_id, codice)`, FK verso `catalogo.articoli`. Nessuna RLS,
  nessun emittente.
* **Chi la cita**, cioè chi ha `lotto_id`: `movimenti`, `movimenti_attesi`, `inventari_righe`,
  `rettifiche_righe`, `trasferimenti_righe` e `vendite.ddt_righe_prelievi`. Ognuna di queste ha già
  un'azienda, attraverso il suo magazzino o il suo documento.
* **Chi la scrive**: i verbi `magazzino.fn_aggiungi_lotto` e `fn_modifica_lotto` (DEFINER, il livello
  sull'oggetto); l'app ha solo `SELECT` dal 2026-11-22. Il backend li adotta con la R-1 del brief
  vicino.
* **Righe**: 0 su dbdev.
* ⚠️ **Il nome `lotto` è già preso** nel risolutore dell'emittente:
  `script.fn_resolve_emittente_fiscale_id('lotto', …)` e `script.fn_scope_ef_whitelist_via_lotto`
  parlano del **lotto di fatturazione** (`vendite.fatturazione_lotti`). Il lotto di magazzino avrà un
  nome suo.

## 3. Il problema, sul modello

Un lotto senza azienda è una riga che due aziende condividono senza saperlo:
* la scadenza di un lotto di A la può cambiare B;
* la tracciabilità («chi ha spostato la scadenza di questo lotto») attraversa due aziende;
* il codice del lotto, che in realtà è scritto sul cartone del fornitore di **una** azienda, non può
  ripetersi su un'altra.

Con l'azienda sul lotto valgono le regole che il magazzino ha già: la RLS di lettura, il guard di
perimetro in scrittura (D-M6 del brief vicino) e il no-leak dei verbi.

## 4. Decisioni aperte — a Tid

Da prendere una alla volta. Ognuna ha una proposta.

| | Domanda | Opzioni | Proposta |
| --- | --- | --- | --- |
| **D-L1** ✅ **DECISA da Tid il 2026-11-22: a** | Come si lega il lotto all'azienda? | **a** una colonna `emittente_fiscale_id NOT NULL`, come `magazzini` e `assets` · **b** un `magazzino_id`: il lotto sta in un magazzino | ⭐ **a.** Un lotto si sposta fra i magazzini della stessa azienda (trasferimenti): legarlo a un magazzino lo inchioderebbe al primo. L'azienda è quella che riceve la merce, e il default di sessione (`trgfn_default_emittente_fiscale`) la mette da solo, come sul seriale |
| **D-L2** ✅ **DECISA da Tid il 2026-11-22: a** | Il codice è unico per…? | **a** `(emittente, articolo, codice)` · **b** resta `(articolo, codice)` | ⭐ **a.** Due aziende possono ricevere dallo stesso fornitore partite con lo stesso codice. Con **b** la seconda azienda non potrebbe registrarla |
| **D-L3** ✅ **DECISA da Tid il 2026-11-22: b** (il gestionale non è in produzione: i lotti che ci sono sono dati di test, si sceglie la strada pratica). ⚠️ **Al P-1**: un'«azienda di default dell'installazione» non esiste come concetto; la strada pratica è quella di `assets` (`20260915-09`): colonna `NOT NULL` con la precondizione «zero righe», e il migrate si ferma se un database ha lotti | I lotti che esistono già | **a** l'azienda dai movimenti del lotto; un lotto mosso da due aziende ferma la migrazione e si guarda a mano · **b** l'azienda di default di ogni installazione · **c** si cancellano | ⭐ **a.** La regola è del modello: un lotto è dell'azienda che lo ha movimentato. Un lotto di due aziende è un dato da capire, non da indovinare. ⚠️ Fatto datato: oggi su dbdev le righe sono zero. La regola vale comunque, per le installazioni che ne avranno |
| **D-L4** ✅ **DECISA da Tid il 2026-11-22: a** | I figli: un movimento, una riga di inventario, un prelievo di bolla col lotto di un'altra azienda | **a** un guard sui sei figli: il lotto è dell'azienda della riga · **b** nessun controllo, basta la RLS | ⭐ **a.** La RLS filtra la lettura, non il riferimento: una FK verso un lotto altrui passa anche se non lo si vede. È la stessa forma di `trgfn_trasferimenti_guard_stesso_emittente`; un BB solo, montato sui sei figli |

## 5. I passi

| Passo | Cosa | Note |
| --- | --- | --- |
| **P-0** | Censimento, al momento di scrivere | ✅ **fatto il 2026-11-22** (§5.1); ne escono D-L5 e D-L6 |
| P-1 ✅ **applicato il 2026-11-22** (§5.2), pgTAP verdi | La colonna, il default di sessione, il guard di perimetro (`trgfn_guard_emittente_scope`, modo `fiscale`), la RLS, l'unicità (D-L1, D-L2); il pregresso (D-L3) | `00_schema` + `20_code`; il nuovo modo del risolutore col nome suo (§2) |
| P-2 ✅ **applicato il 2026-11-22** (§5.3), pgTAP verdi | I verbi: `fn_aggiungi_lotto` e `fn_modifica_lotto` leggono la riga nel perimetro (`E_MAG_LOTTO_NON_TROVATO`, no-leak), come ubicazione e magazzino | CREATE OR REPLACE coi `%TYPE` |
| P-3 ✅ **applicato il 2026-11-22** (§5.3), pgTAP verdi | Il guard dei figli (D-L4); con D-L5 anche sul seriale; il motivo in `fn_check_riga_magazzino` (D-L6) | un BB, sei montaggi (dodici con D-L5) |
| P-4 ✅ **applicato il 2026-11-22** (§5.3), pgTAP verdi | pgTAP: perimetro in lettura e scrittura, no-leak dei verbi, unicità per azienda, il guard dei figli, il pregresso | come app; i casi si costruiscono |
| P-5 ✅ **scritto il 2026-11-22** (§5.3) | Guida del dominio: i lotti escono dall'elenco «uguali per tutti»; le pagine `manual/` | un registro dei BB lato DB non esiste: il BB nuovo sta in `script`, col suo `COMMENT` |

### 5.1 Il P-0 — 2026-11-22

Letto su dbdev dalla struttura (catalogo, corpi delle funzioni, seed) e dai file del repository.
Sono fatti datati: dicono **dove** si mette mano, non **che cosa** si fa.

**Lo stampo è il seriale.** `magazzino.assets` ha già la forma che il lotto prende con D-L1:
`emittente_fiscale_id` col default di sessione (`trg_assets_a10_default_emittente_ins`,
`trgfn_default_emittente_fiscale('SOLLEVA')`), il guard di perimetro
(`trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')`), la policy
`rls_assets_ef_whitelist` e lo storico in modo `EF`. Il seriale non ammette l'emittente fra le
colonne della nascita (`fn_assets_colonne_ammesse('crea')`), e il lotto fa lo stesso: lo mette la
sessione (R-2).

**Le sedi lato DB che il P-1 … P-4 toccano:**

| Sede | Oggi | Con D-L1 … D-L4 |
| --- | --- | --- |
| `magazzino.lotti` (`00_schema`) | nessun emittente; `uq_mag_lotti_articolo_codice (articolo_id, codice)`; nessuna RLS | colonna `NOT NULL` con FK verso `anagrafiche.emittenti_fiscali`; unicità `(emittente_fiscale_id, articolo_id, codice)`; RLS accesa |
| `80_data/sql/dbops/fk_index_policy.csv` | — | la riga della FK nuova |
| `80_data/sql/dbops/emittente_modi.csv` | il modo `lotto` è di `vendite.fatturazione_lotti` | un modo nuovo, `lotto_magazzino` (`PK`, `emittente_fiscale_id`); il risolutore è **generato** dal registro, non si scrive a mano |
| `80_data/sql/dbops/storico_scope_policy.csv`, riga 122 | `NESSUNO`, «fuori dal perimetro RLS per costruzione» | `EF`, `emittente_fiscale_id` |
| `80_data/sql/ui/lista_definizione.csv`, riga 82 | `perimetro_emittente = f` | `t` (e la certificazione di `dbops.vw_liste_multi_emittente_non_certificate`, se la lista diventa multi-emittente) |
| `80_data/sql/ui/lista_colonna.csv`, riga 922 | «Il codice della partita, univoco per articolo» | «… univoco per azienda e articolo» |
| `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql:178` | `magazzino.lotti` fra le liste globali, col commento «il lotto appartiene all'articolo» | esce dall'elenco |
| `magazzino.fn_aggiungi_lotto`, `fn_modifica_lotto`, `fn_crea_lotto` | — | P-2: lettura nel perimetro, no-leak |
| i sei figli: `movimenti`, `movimenti_attesi`, `inventari_righe`, `rettifiche_righe`, `trasferimenti_righe`, `vendite.ddt_righe_prelievi` | sul lotto, solo `trgfn_child_requires_active_parent` | P-3: il guard di D-L4. L'emittente della riga si risolve coi modi che il registro ha già: `magazzino`, `inventario`, `rettifica`, `trasferimento`, `ddt_riga` |

Viste che dipendono da `magazzino.lotti`: **nessuna** (`pg_depend`). Le viste `dbops.vw_lotti_*` sono
dei lotti di fatturazione.

**I pgTAP che fabbricano lotti: 15 file.**
* 9 passano dal builder `dbops.fn_pgtap_crea_lotto_di_magazzino` o dal verbo: con il default di
  sessione prendono l'azienda da soli, se il test ha un operatore in sessione. Il builder è INVOKER:
  senza `app.current_user_id` il default `SOLLEVA` risponde `E_EMITTENTE_NON_RISOLTO`.
* 6 fanno `INSERT INTO magazzino.lotti` a mano: `dbops/test-presidi-magazzino-grana-v1`,
  `dbops/test-sorgenti-orfane-v1`, `magazzino/test-fn-scrivi-movimento-controlli-v1`,
  `magazzino/test-fn-scrivi-movimento-disponibilita-v1`, `magazzino/test-movimenti-vincoli-v2`,
  `magazzino/test-sorgente-registro-v1`. Dal 2026-11-22 l'app non ha `INSERT` sui lotti, quindi
  girano da owner; dopo il P-1 devono dare l'emittente, o passare dal builder.

**Due fatti che toccano le decisioni (per Tid):**

1. **Il seriale ha lo stesso buco che D-L4 chiude per il lotto.** Sui sei figli, per `asset_id`
   c'è solo `trgfn_child_requires_active_parent`. «Il seriale è dell'emittente del magazzino» lo
   controlla soltanto `script.fn_check_riga_magazzino` (passo 7, `E_MAG_ASSET_DI_ALTRO_EMITTENTE`),
   quando la riga **diventa un movimento**. Una riga di inventario in bozza, o un prelievo di bolla,
   può puntare oggi a un seriale di un'altra azienda. Il guard di D-L4 è la stessa regola sulla
   stessa forma («il riferimento è dell'azienda della riga») ⇒ D-L5.
2. **`fn_check_riga_magazzino` ha il passo 7 per il seriale e non il gemello per il lotto.** Gira
   INVOKER, ma i chiamanti che scrivono (`fn_scrivi_movimento`, `fn_posta_inventario`, `fn_apri_blocco`)
   sono DEFINER, quindi da proprietario la RLS non filtra e il lotto altrui si vede. Con il guard
   di D-L4 il movimento lo ferma comunque la tabella; il passo 6 serve al **messaggio**:
   `fn_inventario_piano` risponde `NON_POSTABILE` con un motivo, e oggi per il lotto altrui
   direbbe «non è dell'articolo, oppure non è più attivo» ⇒ D-L6.

| | Domanda | Opzioni | Proposta |
| --- | --- | --- | --- |
| **D-L5** ✅ **DECISA da Tid il 2026-11-22: a** | Il guard di D-L4 vale anche per il seriale? | **a** un BB solo, «il riferimento è dell'azienda della riga», montato su `lotto_id` e su `asset_id` dei sei figli · **b** solo il lotto; il seriale in un brief suo | ⭐ **a.** È la seconda occorrenza della stessa regola, nello stesso giro (regola del 2). Il BB prende il modo della riga e il modo del riferimento, e risolve tutti e due dal registro |
| **D-L6** ✅ **DECISA da Tid il 2026-11-22: a** | Il motivo «lotto di un'altra azienda» in `fn_check_riga_magazzino` | **a** il passo 6 prende il gemello del passo 7 (`E_MAG_LOTTO_DI_ALTRO_EMITTENTE`, un codice nuovo a catalogo) · **b** nessun motivo nuovo, basta il guard | ⭐ **a.** La funzione è la sede dei motivi di una riga (C8): un motivo che c'è per il seriale e manca per il lotto è un buco nella sede, non una scelta |

**Garanzie ritirate** (regola trasversale, `.codex/AGENTS.md`):

| Garanzia | Chi ci contava, lato DB | Esito |
| --- | --- | --- |
| «un lotto lo vede chiunque» (nessuna RLS) | `script.fn_check_riga_magazzino`, INVOKER. Chiamato da DEFINER (`fn_scrivi_movimento`, quindi tutti i `fn_posta_*`; `fn_posta_inventario` e `fn_apri_blocco` anche direttamente): da proprietario vede tutto, non cambia. Chiamato da INVOKER (`fn_inventario_piano`, `fn_check_ddt_merce`, `fn_check_reso_merce`, `fn_check_documento_interno_registrabile`): il lotto altrui non si vede e il motivo è `LOTTO_DI_ALTRO_ARTICOLO` | va adeguato in questo giro (D-L6). Con il guard dei figli la riga col lotto altrui non si salva più, ma la funzione la sa giudicare anche da sola |
| | `dbops.trgfn_prevent_deactivate_if_children` sui sei figli (sei trigger su `lotti`) | non ne dipende: con D-L4 i figli di un lotto sono tutti della sua azienda |
| «`(articolo, codice)` individua un lotto» | nessuna funzione DB cerca un lotto per codice (letto il 2026-11-22: tutte lo leggono per `id`) | non ne dipende |

Lato BE la sessione DB non legge: la richiesta è la R-3 (§6).

### 5.2 Il P-1 — applicato il 2026-11-22, pgTAP verdi

| File | Che cosa |
| --- | --- |
| `00_schema/magazzino/20261122-14-alter-lotti-emittente-e-perimetro` | `emittente_fiscale_id NOT NULL` + `fk_mag_lotti_emittente_fiscale`; `uq_mag_lotti_articolo_codice` → `uq_mag_lotti_emittente_articolo_codice (emittente_fiscale_id, articolo_id, codice)`, che copre la FK per prefisso (nessuna riga in `fk_index_policy`); `rls_lotti_ef_whitelist` con l'espressione di `rls_assets_ef_whitelist`, RLS accesa senza `FORCE`; i `COMMENT`. Precondizione «zero righe» (D-L3) |
| `20_code/magazzino/20261122-15-create-trigger-default-e-guard-emittente-lotti` | `trg_lotti_a10_default_emittente_ins` (`SOLLEVA`) prima di `trg_lotti_a10_guard_emittente_scope_ins_upd` (`fiscale`) |
| `80_data/sql/dbops/emittente_modi.csv` | il modo `lotto_magazzino` (`PK`, `emittente_fiscale_id`): il risolutore lo rigenera il `90_end` |
| `80_data/sql/dbops/storico_scope_policy.csv`, riga 122 | `NESSUNO` → `EF` |
| `80_data/sql/ui/lista_definizione.csv`, riga 82 | `perimetro_emittente` → `t` (`multi_emittente` resta `f`, come `magazzino.magazzini`) |
| `80_data/sql/ui/lista_colonna.csv`, riga 922 | «univoco per azienda e articolo» |
| `db/pgtap/ui/test-lista-definizione-perimetro-emittente-v1.sql` | `magazzino.lotti` esce dalle liste globali |

Provati in `ROLLBACK` sullo scratch con `scripts/prova_changeset.py`: estratto eseguito per intero,
catalogo identico prima e dopo.

⚠️ **Che cosa si temeva che rompesse** (scritto prima dell'apply; all'apply di Tid i pgTAP sono verdi). Sono 15 i pgTAP che creano lotti (§5.1).
Da proprietario e senza `app.current_user_id`, il default `SOLLEVA` risponde
`E_EMITTENTE_NON_RISOLTO`. Si rompono i 6 file con l'`INSERT` a mano, e quelli col builder che non
hanno un operatore in sessione. I pgTAP che verificano i figli contro il lotto vedono cambiare
l'unicità. Il P-4 li adegua, dando l'emittente esplicito o passando dal builder con un operatore.

### 5.3 P-2 … P-5 — applicati il 2026-11-22, pgTAP verdi

| Passo | File | Che cosa |
| --- | --- | --- |
| P-2 | `20_code/magazzino/20261122-16-update-verbi-lotto-nel-perimetro` | `fn_modifica_lotto` legge il lotto con `script.fn_check_user_emittente_scope` sul suo emittente, il predicato della policy (`E_MAG_LOTTO_NON_TROVATO`, no-leak), come `fn_modifica_magazzino`. `fn_aggiungi_lotto`: cambia il commento, e il `RETURNS` è ancorato con `%TYPE`. `fn_crea_lotto`: solo il `COMMENT`. Le firme non cambiano |
| P-3 | `20_code/script/20261122-17-create-trgfn-guard-riferimento-stesso-emittente` | il BB `script.trgfn_guard_riferimento_stesso_emittente(modo_riga, colonna_riga, modo_rif, colonna_rif)`: i due emittenti dal registro `dbops.emittente_modi`, col risolutore DEFINER. Dodici montaggi `trg_<t>_a10_guard_rif_{lotto,asset}_emittente_ins_upd` (D-L4, D-L5). Riferimento inesistente e riferimento altrui rispondono uguale, `E_RIFERIMENTO_DI_ALTRO_EMITTENTE` |
| P-3 | `20_code/script/20261122-19-update-trgfn-guard-riferimento-stesso-emittente-variadic` | correzione in avanti del `-17`: il ramo `E_RIFERIMENTO_DI_ALTRO_EMITTENTE` chiamava `fn_log_and_raise_error` senza l'ultimo argomento (`VARIADIC text[]`, senza default) e rispondeva `42883`. L'hanno visto i casi 11-14 del pgTAP |
| P-3 | `20_code/script/20261122-18-update-fn-check-riga-magazzino-lotto-di-altro-emittente` | passo 6: `E_MAG_LOTTO_DI_ALTRO_EMITTENTE`, gemello del passo 7 (D-L6); la firma passa ai `%TYPE` |
| P-3 | `80_data/sql/config/codici_errore.csv`, `messaggi_errore.csv` | i due codici nuovi, `DATO_ERRATO` (messaggi `1529`, `1530`) |
| P-4 | `db/pgtap/magazzino/test-lotto-dell-azienda-v1.sql` (nuovo, plan 17, come app) | struttura, nascita con l'emittente della sessione, lo stesso codice in due aziende, RLS di lettura, unicità nell'azienda, no-leak del verbo e della check, il guard dei figli (`INSERT` e `UPDATE` in un'istruzione sola, lotto e seriale, id inesistente), i dodici montaggi per funzione e argomenti, l'ordine fra gli a10 |
| P-4 | `db/pgtap/magazzino/test-fn-scrivi-movimento-controlli-v1.sql` (plan 25 → 26) | 12-bis: il lotto di B con lo stesso codice di quello di A → `E_MAG_LOTTO_DI_ALTRO_EMITTENTE` |
| P-5 | `dbzero/magazzino/_dominio-magazzino.md`, `manual/lotti.md`, `script/manual/fn_check_riga_magazzino.md` | il lotto è dell'azienda; il passo 6 |

Provati in `ROLLBACK` sullo scratch con `scripts/prova_changeset.py`: gli estratti girano per
intero, e dopo il rollback il catalogo è identico. Applicati da Tid, con `-19`: pgTAP verdi col
runner (2026-11-22).

**`%TYPE`.** Nelle funzioni scritte qui i parametri, i `RETURNS` e le variabili sono ancorati
dove esiste una colonna di cui sono il riflesso. Restano col tipo esplicito, e il motivo è scritto
nel file, `p_dati`/`jsonb` (il delta), i nomi di colonna degli argomenti di montaggio (`text`) e le
`text[]` delle colonne ammesse.

**Chi passa ancora dai guard nuovi.** I sei pgTAP che inseriscono lotti a mano girano col contesto
di un operatore: il default di sessione dà l'emittente, e al P-1 i test erano verdi. Il caso 12 di
`test-fn-scrivi-movimento-controlli` resta com'era: la check parla prima del guard. Nessun seed di
`80_data` scrive lotti o figli con un lotto o un seriale.

⚠️ **La `reason_key` nuova** `magazzino.riga.blocco.lotto_di_altro_emittente` è un debito verso il
frontend (linee-guida-sql §12.3), richiesta F-1. `scripts/check_i18n_keys.py` la segnala appena la
doc auto-generata è rigenerata.

## 6. Richieste a BE — nello stesso giro di PR

* **R-1** `test_perimetro_emittente_copertura.py`: `magazzino.lotti` passa fra le tabelle col
  perimetro (oggi è «figli dell'articolo, perimetro_emittente = false»).
* **R-2** La lista dei lotti per articolo resta, ed è filtrata dalla RLS. Il BE censisce i suoi
  lettori e la vista del form del lotto. L'azienda non si sceglie: la mette la sessione.
* **R-3** Garanzie ritirate (§5.1): censisci i lettori di `magazzino.lotti` che contano su «un lotto
  lo vede chiunque» o su «`(articolo, codice)` individua un lotto» (per esempio una ricerca del lotto
  per codice, senza l'azienda). Ognuno si adegua o dice perché non ne dipende.
* **R-4** Il vincolo di unicità cambia nome: `uq_mag_lotti_articolo_codice` →
  `uq_mag_lotti_emittente_articolo_codice` (`20261122-14`). La mappa vincolo → errore in
  `backend/apps/magazzino/services/anagrafiche_magazzino_service.py:84` traduce il nome vecchio in
  `E_ANAG_DUPLICATO` sul campo `codice`; va portata sul nome nuovo, e con lei la tabella degli errori
  di `docs/it/backend/magazzino/manual/api_anagrafiche_magazzino.md:178`. Cambia prima il DB: fino
  all'adeguamento, un codice duplicato arriva al BE come violazione non tradotta.
* **R-5** Due codici nuovi, tutti e due `DATO_ERRATO` con `campo` nel contesto: il BE li traduce
  sul campo, e non ricontrolla la regola.
  * `E_RIFERIMENTO_DI_ALTRO_EMITTENTE`: da `script.trgfn_guard_riferimento_stesso_emittente`, sulle
    scritture che oggi il backend fa diretto (righe di inventario e di rettifica, prelievi della
    bolla), con `campo` = `lotto_id` o `asset_id`;
  * `E_MAG_LOTTO_DI_ALTRO_EMITTENTE`: dalla primitiva, ai posting; e come motivo `NON_POSTABILE`
    nel piano dell'inventario.

  Censisci anche i form che propongono lotti e seriali: dalla RLS ricevono solo quelli
  dell'azienda, quindi il codice lo vede solo chi manda un id a mano.

**Esiti, sessione BE del 2026-11-22**

* **R-1** ✅ `magazzino.lotti` esce da `_ESENZIONI`; `ApiLottiList` e `ApiLottiExport` dichiarano `lista_codice`.
* **R-2** ✅ la lista per articolo somma lo scope sull'emittente del lotto (`add_emittente_scope_condition`),
  come i magazzini; la riga porta `emittente_fiscale_id`; l'azienda non viaggia nel payload (400 se mandata).
* **R-3** ✅ censiti i lettori: `anagrafiche_magazzino_repository` (lista, dettaglio), `magazzino_repository`
  (`lookup_lotti`, proiezione delle righe), `ddt_repository` e `resi_repository` (`LEFT JOIN` per il codice,
  per `id`: non ne dipendono). Nessuno cerca un lotto per `(articolo, codice)`. **Un lettore dipendeva** da «un
  lotto lo vede chiunque»: `lookup_lotti` proponeva i lotti di tutte le aziende del perimetro, e a chi ne ha
  più di una avrebbe offerto lotti che il guard dei figli poi rifiuta. Ora prende `magazzino_id` e filtra
  sull'emittente del magazzino, come `lookup_assets` (rotta `lotti/lookup/?magazzino_id=`, tre form FE adeguati).
* **R-4** ✅ la mappa vincolo → errore usa `uq_mag_lotti_emittente_articolo_codice`; doc API allineata.
* **R-5** ✅ i due codici hanno la policy (rigenerata, zero classi spostate) e il ripiego senza segnaposto;
  passano col campo dal canale `COLUMN`, senza ricontrollo nel BE. I form propongono solo lotti e seriali
  dell'azienda del magazzino (vedi R-3).
* **F-1** ✅ `magazzino.riga.blocco.lotto_di_altro_emittente` in `it.json` ed `en.json`. ⚠️ Senza `%s`:
  la chiave gemella del seriale non ha segnaposto, e la chiave i18n non riceve i `valori` per posizione.
  Testo: «Il lotto non appartiene all'emittente del magazzino.»

## 6-bis. Richieste a FE — nello stesso giro di PR

* **F-1** La chiave i18n `magazzino.riga.blocco.lotto_di_altro_emittente` in `it.json` e `en.json`,
  accanto a `magazzino.riga.blocco.seriale_di_altro_emittente`. Testo: «Il lotto %s non appartiene
  all'emittente del magazzino %s.» (i valori arrivano in `valori`, come per il seriale).

## 7. Che cosa NON entra

| Cosa | Dove |
| --- | --- |
| il lotto di **fatturazione** (`vendite.fatturazione_lotti`) | è un'altra cosa, col suo nome |
| l'articolo: resta comune a tutte le aziende | — |
| l'apply, i pgTAP col runner, il commit | Tid |

---

## Registro

| Data | Chi | Cosa |
| --- | --- | --- |
| 2026-11-22 | Tid | Dal §5.3 di `brief-db-magazzino-tutte-le-scritture-dal-verbo`: «lotto b» (il lotto è dell'azienda), in un brief apposito |
| 2026-11-22 | DB | Prima stesura: la storia della decisione del 14-09 (§1), i fatti datati (§2), quattro decisioni a Tid con una proposta (§4) |
| 2026-11-22 | Tid | D-L1 = a: l'azienda sul lotto (`emittente_fiscale_id NOT NULL`), non il magazzino |
| 2026-11-22 | Tid | D-L2 = a: il codice è unico per `(emittente, articolo, codice)` |
| 2026-11-22 | Tid | D-L3 = b: i lotti che esistono prendono l'azienda di default dell'installazione; niente migrazione ragionata, il gestionale non è in produzione |
| 2026-11-22 | Tid | D-L4 = a: un guard sui sei figli; il via al P-0 |
| 2026-11-22 | DB | P-0 (§5.1): lo stampo è il seriale; le sedi lato DB; 15 pgTAP che fabbricano lotti; le garanzie ritirate; due decisioni nuove a Tid (D-L5, D-L6); R-3 al BE |
| 2026-11-22 | Tid | D-L5 = a (un BB su lotto e seriale), D-L6 = a (il motivo gemello); il via al P-1 |
| 2026-11-22 | DB | P-1 scritto e provato in `ROLLBACK` (§5.2), non applicato; D-L3 realizzata con la precondizione «zero righe» (stampo `assets`); R-4 al BE (nome del vincolo) |
| 2026-11-22 | Tid | P-1 applicato, pgTAP verdi |
| 2026-11-22 | DB | P-2 … P-5 scritti e provati in `ROLLBACK` (§5.3); due codici d'errore; R-5 al BE, F-1 al FE |
| 2026-11-22 | DB | Dopo l'apply di P-2 … P-4 (Tid): casi 11-14 rossi (`42883`, la chiamata a `fn_log_and_raise_error` senza `VARIADIC`) → `20261122-19`; caso 16 rosso per l'ordine dell'array nel test (`ORDER BY 1` dentro l'aggregato) → test corretto |
| 2026-11-22 | Tid | P-2 … P-4 e `20261122-19` applicati, pgTAP verdi. Lavoro DB chiuso; restano R-1 … R-5 (BE) e F-1 (FE) |
| 2026-11-22 | BE/FE | R-1 … R-5 e F-1 fatti (§6, esiti); `lookup_lotti` per l'emittente del magazzino (R-3) |
| 2026-11-22 | DB | Chiuso e archiviato in `work-done/2026/`: lavoro DB applicato, R-1 … R-5 e F-1 in `Tito-dev` (PR #209); nessun debito residuo |
