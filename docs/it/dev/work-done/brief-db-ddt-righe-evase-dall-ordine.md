# Brief DB — Le righe di un DDT nato da un ordine

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-10, dal collaudo a video di Tid. **A chi:**
> team DB; poi BE/FE (§6).
> **Stato (2026-10-11):** ✅ **lato DB applicato e verde** (§7): changeSet `20261011-05 … -20`, `-34`,
> `-35`, applicati da Tid su dbdev e `zeroerp_ci`; corsa pgTAP senza regressioni. Dentro anche la
> ri-consegna di un reso (D-7), il divieto di legami nuovi su bolle emesse (D-6) e l'annullo con
> conferma (D-8, lavorato in [brief-db-annullo-documento-con-legami](brief-db-annullo-documento-con-legami.md)
> §3). ✅ **Lato BE/FE fatto il 2026-10-11** (§10), compreso l'annullo (§3.4 del brief D29).
> ✅ **Collaudo a video di Tid superato il 2026-10-11. Chiuso e archiviato lo stesso giorno** (§11).
> **Nel registro dei difetti DB:** voce **D28** di `migliorie-generali-da-test-valutazione.md`, che
> rimanda qui.

## 1. La domanda

Su un DDT generato da un ordine, che cosa si cambia in bozza? Le righe evase, cioe' quelle che
portano il legame con una riga d'ordine, si modificano? Se ne aggiungono altre a mano?

## 2. Che cosa c'e' oggi (contratto, letto dalla doc auto-generata)

* **L'evasione** (`vendite.fn_genera_ddt_da_ordine(p_ordine_id, p_righe, p_data)`) crea **sempre una
  bolla nuova** in `DRAFT`: righe, componenti e una riga di `vendite.ordini_righe_fulfillment`
  `(ordine_riga_id, ddt_riga_id, qta_evasa)` per riga. Poi proietta lo stato dell'ordine
  (`CONFERMATO`/`PARZIALMENTE_EVASO`/`EVASO`). Oltre il residuo rifiuta con `E_QTA_SUPERA_RESIDUO`.
* **Il guard del legame** `vendite.trgfn_ordini_ful_guard_consistenza` (articolo, UoM, residuo,
  cliente) e' montato **solo su `ordini_righe_fulfillment`**. Scatta quando il legame si scrive, non
  quando cambia la riga di DDT.
* **Su `vendite.ddt_righe`, in bozza:**

  | Operazione su una riga evasa | Oggi |
  | --- | --- |
  | cancellarla | ⛔ `E_DELETE_BLOCKED_FUL` (`trgfn_dlt_block_ordrig_ddtrig`) |
  | cambiarne quantita', articolo, UoM | ✅ passa, nessuno ricontrolla il fulfillment |
  | aggiungere una riga a mano | ✅ passa |

  Fuori bozza tutto e' fermo (`trgfn_doc_righe_lock_fuori_bozza`).
* **L'invariante del brief dell'evasione**
  ([brief-db-ddt-vendita-evasione-e-stati](brief-db-ddt-vendita-evasione-e-stati.md)
  §4 e invariante 1): «`qta_evasa` e' immutabile, append-only». E' la fotografia di cio' che e' stato
  spedito con quel DDT; il reso non la scala, e' un movimento a parte. ⚠️ Nessun lock a DB la presidia:
  `ordini_righe_fulfillment` ha guard, storico e `require_attivo`, non un lock di colonna.
* **Il magazzino** (Lotto 3) **non e' toccato da questo brief e regge gia' le modifiche in bozza**:
  la riga e' l'unita' commerciale, i prelievi (`ddt_righe_prelievi`) quella fisica, e la coerenza
  fra i due la controlla l'emissione (`fn_check_ddt_merce`: somma dei prelievi = quantita' della riga,
  disponibilita'). Il legame con l'**ordine** invece non lo controlla nessuno.

## 3. Perche' e' un difetto, sul modello

* **La quantita' della riga evasa e la `qta_evasa` divergono in silenzio.** Ordine pippo 10, evasi
  10, poi in bozza la riga passa a 6: il magazzino scarica 6, l'ordine resta evaso per 10, e i 4
  mancanti non tornano nel residuo. Nessun errore.
* **L'articolo della riga evasa puo' cambiare.** La riga d'ordine dell'articolo A risulta evasa da
  una riga di DDT che consegna B: e' il caso che il guard del legame rifiuta alla generazione.
* **Per consegnare meno del generato non c'e' una strada.** La riga evasa non si cancella, e il
  verbo d'evasione non aggiunge righe a una bolla esistente: resta solo eliminare la bozza e
  rigenerarla, perdendo trasporto, indirizzi e prelievi gia' compilati.
* **L'invariante e' scritta in un brief, non nel DB.**

⚠️ Nessuna di queste ragioni dipende da quante righe ci sono oggi in quello stato.

## 4. Decisioni di Tid (2026-10-10; D-6 e D-7 il 2026-10-11)

| # | Domanda | Decisione |
| --- | --- | --- |
| **D-1** | La riga evasa si modifica liberamente? | ⛔ **No.** Articolo, UoM e quantita' di una riga legata a un fulfillment sono **fermi**: sono la fotografia di cio' che si evade |
| **D-2** | Come si consegna meno del generato (ordine 10, bolla 6)? | Con un **verbo DB «correggi la quantita' evasa»**, ammesso **solo in bozza** e **solo sui DDT nati da un ordine**: cambia nella stessa operazione la quantita' della riga e la sua `qta_evasa`, entro il residuo, e riproietta lo stato dell'ordine. L'invariante non si rompe nel suo significato: `qta_evasa` fotografa cio' che e' **spedito**, e una bozza non e' partita |
| **D-3** | La riga evasa si toglie? | ✅ **Si', in bozza**, col ritiro del suo fulfillment: il residuo torna all'ordine e lo stato si riproietta. Fuori bozza resta fermo |
| **D-4** | `qta_evasa` fuori bozza? | ⛔ **Ferma**, con un lock dichiarato a DB (l'invariante del brief dell'evasione, finalmente scritta) |
| **D-5** | Righe aggiunte a mano su un DDT da ordine? | ✅ **Ammesse** (es. ordine pippo 10, bolla 15: riga evasa 10 + riga a mano pippo 5). Non sono legate all'ordine; vanno al cliente della bolla, che e' quello dell'ordine (D-6 di `brief-db-esecutivi-ba-coppia`) |
| **D-6** (2026-10-11) | Un legame **nuovo** su una bolla gia' emessa (INSERT fuori bozza)? | ⛔ **No**: un legame nato dopo la spedizione cambia cio' che l'ordine (o il reso) risulta spedito senza che niente sia partito. Il lock fuori bozza copre anche l'INSERT |
| **D-7** (2026-10-11) | Le righe di **ri-consegna** di un reso hanno lo stesso difetto: brief nuovo o qui? | ✅ **Qui, con la stessa regola**: la riga di ri-consegna e' una riga evasa (legame con la riga di reso, e col fulfillment se il reso viene da un ordine). Ferma, corretta dal verbo, cancellabile in bozza col ritiro dei suoi legami |
| **D-8** (2026-10-11) | Annullare una bolla che porta legami (§7.6): che cosa succede ai legami? | ✅ **Si ritirano con l'annullo** (strada A), come in D-3: l'ordine si riproietta, il reso torna da ri-consegnare. ⚠️ Ma **non in silenzio**: l'annullo avvisa dei legami e chiede **conferma** (§8). Dentro questo brief, non uno nuovo. ⭐ Lavorato in [brief-db-annullo-documento-con-legami](brief-db-annullo-documento-con-legami.md) §3 |

## 5. Forma proposta (la sceglie il team DB)

1. **Guard su `vendite.ddt_righe` (UPDATE):** se la riga ha un fulfillment, `articolo_id`,
   `uom_operativa_id`, `quantita` e `qta_operativa` non cambiano, con un codice registrato. Il guard
   deve lasciar passare il verbo del punto 2 (porta del verbo, come le altre GUC-porta dei verbi DDT).
2. **Il verbo** `vendite.fn_ddt_riga_correggi_qta_evasa(p_ddt_riga_id, p_qta_operativa)` (nome di
   lavoro):
   * solo DDT in `DRAFT` con sorgente `ORDINE_VENDITA`; solo righe con fulfillment;
   * nuova quantita' `> 0` ed entro il residuo dell'ordine (stessa formula di
     `fn_ordine_ha_residuo_evasione`, reso-aware), lock come nel guard del legame;
   * aggiorna riga (quantita', e i componenti tramite la propagazione gia' esistente) e `qta_evasa`
     nella stessa transazione; riproietta lo stato dell'ordine.
   * ⭐ **Regola del 2**: la proiezione dello stato dell'ordine oggi sta dentro
     `fn_genera_ddt_da_ordine`. Con il verbo (e col ritiro del punto 3) i consumatori diventano piu'
     d'uno: si estrae in un BB, adottato anche da `fn_genera_ddt_da_ordine`, nello stesso giro.
3. **Cancellazione in bozza:** `trgfn_dlt_block_ordrig_ddtrig`, ramo 2a (`E_DELETE_BLOCKED_FUL`),
   diventa: in bozza la riga si cancella e il suo fulfillment si ritira con lei (poi la proiezione
   del punto 2); fuori bozza resta com'e' (e comunque parla prima il lock delle righe).
   ⚠️ Il ramo 2b (riga usata da resi o riconsegne) resta: in bozza non ci sono resi.
4. **Lock su `ordini_righe_fulfillment.qta_evasa`** fuori bozza del DDT (D-4), con lo stesso porta
   del verbo in bozza. Forma: un BB di lock o una riga di `dbops.automation_lock_columns`, secondo
   cosa serve per l'eccezione «in bozza, solo dal verbo».
5. **Capability:** la riga deve dire al form che cosa e' fermo e se la quantita' passa dal verbo
   (per esempio `evasa`, o i campi fermi per riga nella vista del dettaglio righe). Il FE la legge,
   non ricopia la regola.
6. **Codici** nuovi registrati, con policy e frase di ripiego: guard della riga evasa; verbo fuori
   perimetro (stato, sorgente, riga senza fulfillment); quantita' oltre il residuo riusa
   `E_QTA_SUPERA_RESIDUO`.

### 5.1 Fuori da qui

* ~~**I DDT di riconsegna** (da reso, `fn_genera_ddt_riconsegna`, legame in `resi_righe_riconsegne`):
  Tid ha deciso il verbo **solo per i DDT da ordine**. Le righe di riconsegna restano come oggi; se
  servira' la stessa domanda, sara' un brief suo.~~ ⚠️ **Superato il 2026-10-11 da D-7**: la
  ri-consegna entra in questo brief con la stessa regola (§7).
* Il magazzino (Lotto 3): invariato, l'emissione ricontrolla i prelievi sulla quantita' nuova.

### 5.2 pgTAP (fixture fabbricati)

* Ordine pippo 10, DDT generato con 10: `UPDATE` diretto della quantita' della riga evasa →
  rifiutato col codice; `UPDATE` dell'articolo → rifiutato.
* Lo stesso col verbo a 6: riga 6, `qta_evasa` 6, ordine `PARZIALMENTE_EVASO`, residuo 4.
* Verbo oltre il residuo (con un secondo DDT gia' evaso sulla stessa riga) → `E_QTA_SUPERA_RESIDUO`.
* Verbo su un DDT emesso, su un DDT standalone, su una riga a mano → rifiutato.
* Cancellazione della riga evasa in bozza: fulfillment ritirato, residuo 10, stato `CONFERMATO`.
* `UPDATE` di `qta_evasa` su un DDT emesso → rifiutato.
* Ordine pippo 10, bolla con riga evasa 10 + riga a mano pippo 5: si emette; l'ordine resta
  `EVASO` per 10.
* Emissione dopo il verbo: i prelievi devono sommare 6 (Lotto 3, invariato).

## 6. Ricaduta BE/FE (dopo la consegna DB)

* Form riga del DDT: sulla riga evasa articolo e UoM spenti, la quantita' chiama il verbo invece del
  salvataggio della riga; il pulsante di cancellazione segue la capability. Righe a mano invariate.
* Service: un metodo per il verbo, codici nuovi con policy e ripiego.
* Guida [gestione-ddt](../../guide/gestione-ddt.md): una sezione «Le righe di un DDT da ordine»
  (righe evase ferme, correzione della quantita', righe a mano, i due esempi pippo 10→15 e 10→6).

### 6.1 Il contratto consegnato dal DB (2026-10-11, da leggere per primo)

| Cosa | Dove | Note per BE/FE |
| --- | --- | --- |
| La riga e' evasa | `vendite.vw_ddt_righe_dettaglio.evasa` (boolean) | `true`: la riga viene da un ordine o da un reso da ri-consegnare (D-7). Articolo, UoM e quantita' **spenti** nel form; la quantita' si cambia dal verbo. `false`: riga a mano, form com'e' oggi |
| Il pulsante «Correggi quantita' evasa» | `vendite.vw_ddt_righe_dettaglio.correggi_qta_evasa_blocco` (text) | `NULL` = acceso. Altrimenti il `reason` del motivo: `DDT_NON_IN_BOZZA`, `RIGA_NON_EVASA`, `DDT_SENZA_ORIGINE`, `LEGAMI_MULTIPLI`. Il pulsante esiste solo dove `evasa = true` (gli altri motivi sono stato o forma, e restano grigi col tooltip) |
| Le chiavi dei tooltip | `vendite.ddt.correggi_qta_evasa_reason.<reason minuscolo>` | ⚠️ **quattro chiavi nuove nei locales** (`ddt_non_in_bozza`, `riga_non_evasa`, `ddt_senza_origine`, `legami_multipli`): finche' mancano, `scripts/check_i18n_keys.py` (controllo 4) e' rosso |
| Il verbo | `SELECT vendite.fn_ddt_riga_correggi_qta_evasa(ddt_riga_id, qta_operativa)` → nuova quantita' evasa (unita' base) | una `SELECT`, atomica. Riga, componenti, legami (ordine e/o reso) e stato dell'ordine cambiano insieme |
| Annullare una bolla con legami (D-8) | ⚠️ **superato il 2026-10-11 da brief-db-annullo-documento-con-legami §8** (forma comune, D-4): l'annullo diretto risponde **E_DOC_ANNULLO_CON_LEGAMI** (409); la finestra elenca i legami da `vendite.fn_documento_legami('DDT', ddt_id)`; alla conferma `SELECT * FROM vendite.fn_annulla_ddt(ddt_id, <legami visti>)`. ~~E_DDT_ANNULLO_CON_LEGAMI~~, ~~`vendite.fn_ddt_legami`~~ ritirati | la conferma che non corrisponde (righe cambiate nel frattempo) risponde lo stesso codice: la finestra si ripresenta. Il nome del documento d'origine per il gesto «vai a» viene dal lineage. Una bolla senza legami si annulla come oggi |
| Cancellare la riga evasa | `DELETE FROM vendite.ddt_righe` come oggi | in bozza ora **riesce**, anche sulla riga di ri-consegna: i legami si ritirano, l'ordine si riproietta, il reso torna da ri-consegnare. Il pulsante segue `can_edit_righe` come le altre righe |
| Codici nuovi | `E_DDT_RIGA_EVASA_FERMA` (409), `E_DDT_RIGA_NON_EVASA` (409), `E_DDT_RIGA_EVASA_LEGAMI_MULTIPLI` (500), `E_DDT_LEGAME_EVASIONE_SOLO_DA_VERBO` (500); ~~`E_DDT_ANNULLO_CON_LEGAMI`~~ → `E_DOC_ANNULLO_CON_LEGAMI` (409, conferma; brief-db-annullo-documento-con-legami §8) | policy e ripiego nel BE. Riusati: `E_RIGA_DOC_NON_BOZZA`, `E_QTA_NON_POSITIVA` (campo `qta_operativa`), `E_QTA_SUPERA_RESIDUO`, `E_RESO_RICONSEGNA_SUPERA_RESO`, `E_DDT_RIGA_NON_TROVATA`, `E_VENDITE_CHIAMATA_NON_VALIDA` |
| `E_DELETE_BLOCKED_FUL`, `E_DELETE_RIGA_DOC_REFERENZIATA` | — | il primo non arriva piu' dalla riga di DDT (solo dalla riga d'ordine); il secondo, sulla riga di DDT, solo se e' l'origine di un reso. Il commento in `ddt_repository.delete_riga` («blocca la delete se la riga e' collegata a un ordine») e' da aggiornare |

## 7. Consegna DB (2026-10-11)

### 7.1 I changeSet

| NN | Oggetto | Cosa |
| --- | --- | --- |
| `-05` | `vendite.fn_ordine_proietta_stato_evasione` | ⭐ BB: lo stato dell'ordine dalla sua evasione. Nessun legame → `CONFERMATO` (terzo esito, nuovo: serve a D-3); residuo → `PARZIALMENTE_EVASO`; altrimenti `EVASO` |
| `-06 … -11` | `fn_genera_ddt_da_ordine`, `fn_conferma_reso`, `fn_annulla_reso`, `fn_chiudi_riconsegna_reso`, `fn_riapri_riconsegna_reso`, `fn_genera_ddt_riconsegna` | ⭐ regola del 2: la proiezione era copiata a mano in **sei** madri, non in una come diceva §5.2. Ritirate tutte nello stesso giro; comportamento invariato (girano solo su ordini con un legame, quindi il terzo esito li' non si raggiunge). Firma, `RETURNS` e `COMMENT` con `%TYPE`; `SECURITY INVOKER` esplicito sulle quattro non DEFINER |
| `-12` | `vendite.fn_ddt_riga_evasa` | il predicato «riga evasa» (fulfillment **o** ponte di ri-consegna), sede unica di guard, check e vista |
| `-13` | `vendite.trgfn_ddt_righe_guard_riga_evasa` + trigger `_a10_` | D-1, D-7 |
| `-14` | ⭐ BB `vendite.trgfn_ddt_riga_legame_guard(colonna quantita', colonna del capo a monte)`, montato su `ordini_righe_fulfillment` e su `resi_righe_riconsegne` (`_a05_`) | il legame non si scrive a mano (D-2, D-3, D-4, D-7). Un BB e non due funzioni: i due legami sono la stessa cosa vista da due documenti a monte, e la ri-consegna da ordine li ha tutti e due |
| `-15` | lock delle righe montato sui due legami, **INSERT e UPDATE**, livello RIGA | D-4, D-6, D-7; il DELETE e' del guard del legame (D-8) |
| `-16` | ⭐ BB `vendite.fn_ddt_riga_ritira_legami` + `vendite.trgfn_dlt_block_ordrig_ddtrig` | D-3, D-7, D-8: il ritiro dei legami di una riga in un posto solo (cancellazione in bozza e annullo); i resi che hanno la riga come origine parlano prima |
| `-17` | `script.fn_check_ddt_riga_correggi_qta_evasa` | la check dell'azione di riga (§12.5 delle linee guida) |
| `-18` | `vendite.fn_ddt_riga_correggi_qta_evasa` | il verbo, SECURITY DEFINER: riga, fulfillment e ponte |
| `-19` | `vendite.vw_ddt_righe_dettaglio` | `+ evasa`, `+ correggi_qta_evasa_blocco` |
| `-20`, `-34`, `-35` | D-8 | brief-db-annullo-documento-con-legami §3.5 |
| CSV | `codici_errore.csv`, `messaggi_errore.csv` | cinque codici (id 1283-1287); note di `E_DELETE_BLOCKED_FUL` e `E_DELETE_RIGA_DOC_REFERENZIATA` aggiornate |

### 7.2 Scelte del team DB, dove il §5 lasciava strada

* ⭐ **La FK del legame resta `ON DELETE RESTRICT`.** Una `CASCADE` era la strada piu' corta per D-3, ma
  il test 9 di `test-delete-righe-documento-bozza-v1` la dichiara il muro voluto. Il ritiro lo fa la
  madre (`trgfn_dlt_block_ordrig_ddtrig`) aprendo una porta per QUELLA riga (GUC
  `zeroerp.ddt_riga_ritira_legame`, stile «la madre dichiara: sono io»). Un DELETE che arriva al
  legame per un'altra strada resta un 23503.
* **Le due porte non sono uguali.** Quella del verbo (`zeroerp.ddt_riga_correggi_qta`) vuole anche il
  proprietario della tabella, come la porta del registro. Quella del ritiro no: parte da un trigger
  che gira come chi cancella. Chi la accende a mano toglie un legame lasciando la riga: e' la famiglia
  Q-2 di D17, non un difetto nuovo.
* **I due capi del legame non si spostano mai.** Non era chiesto: e' la stessa invariante (un legame
  spostato su un'altra riga diverge come una quantita' cambiata).
* **Il verbo non ricontrolla le quantita'.** Il residuo dell'ordine lo giudica
  `trgfn_ordini_ful_guard_consistenza` (`E_QTA_SUPERA_RESIDUO`, reso-aware), la copertura del reso
  `trgfn_resi_riconsegne_guard` (`E_RESO_RICONSEGNA_SUPERA_RESO`): scattano sull'UPDATE dei legami.
* **Ritiro della ri-consegna (D-7).** Il reso non ha uno stato da riproiettare: la sua copertura da
  ri-consegnare si ricalcola (`fn_resi_riga_residuo_riconsegna`) e la riga torna in coda. L'ordine, se
  c'e', si riproietta: il residuo riaperto dal reso torna aperto.
* **`DDT_SENZA_ORIGINE` e `LEGAMI_MULTIPLI`** sono motivi della check, non casi ignorati. Una bolla
  standalone con un legame scritto a mano ha la riga ferma, e il verbo la rifiuta. Una riga con due
  legami dello stesso tipo il modello la ammette (l'unicita' e' sulla coppia) ma nessuna madre la
  produce: il verbo non sa dividere una quantita' e rifiuta, con un codice TECNICO.

### 7.3 Ordine dei BEFORE

* `ddt_righe` (UPDATE): `_a05_doc_righe_lock_fuori_bozza` → `_a10_guard_riga_evasa` → … →
  `_a10_qta_from_operativa`. Il guard confronta l'input (`qta_operativa`) prima del ricalcolo.
* `ordini_righe_fulfillment`, `resi_righe_riconsegne`: `_a05_doc_bozza` (INSERT/UPDATE fuori bozza:
  `E_RIGA_DOC_NON_BOZZA`) → `_a05_guard_legame` (la porta; da solo sul DELETE) → `_a10_guard_*`
  (residuo dell'ordine, copertura del reso).

### 7.4 La prova (2026-10-11, su `zeroerp_ci`, transazione ritirata, da owner)

* SQL **estratto** dai quindici YAML (`yaml.safe_load`) con i codici nuovi, eseguito con
  `ON_ERROR_STOP`: passa. I sette corpi riscritti coincidono col vivo dello scratch prima della prova.
* pgTAP nuovo, **36/37** a questo punto del giro (**42/43** con D-8, brief-db-annullo-documento-con-legami §3.5). L'ultimo (la GUC accesa a mano non apre la porta del verbo) e' **rosso da owner
  per costruzione**: il proprietario apre la porta. Come app e' verde, ed e' dichiarato nel file.
* ⭐ Il pgTAP ha morso alla prima corsa: il guard del legame lasciava passare tutto quando la GUC non
  era mai stata impostata. Il NULL di `current_setting(…, true)` faceva diventare NULL anche il
  confronto, e `IF NOT NULL` non scatta. Corretto con `COALESCE` in tutti e due i guard prima di
  consegnare.
* Prima/dopo su 59 pgTAP (tutti i file che nominano le sei madri, i due legami, la vista, il trigger
  di cancellazione o il BB del lock, piu' i presidi trasversali): **nessuna regressione**. Cambiano
  solo i file che il giro sposta per contratto, aggiornati nello stesso giro:
  * `vendite/test-trgfn-doc-righe-lock-fuori-bozza-v1` test 2 e `vendite/test-righe-gemelle-secondo-giro-v1`
    test 9: i due censimenti degli adottanti del BB (quindici; nove a livello RIGA);
  * `vendite/test-vw-righe-dettaglio-sorgente-lista-v1` test 7: le due colonne nuove;
  * `script/test-rubinetto-primo-motivo-v1` test 5: il verbo e' un sito nuovo dell'helper. ⚠️ L'altra
    sessione DB di oggi (R-DB della testata, `20261011-21 … -33`) ha gia' portato l'atteso a **37**,
    contando anche il suo sito: con i soli miei changeSet la prova da' 36, con tutti e due i giri 37.
  `dbops/test-riferimenti-morti-v1` (plpgsql_check su tutte le funzioni), `test-stati-check-scrittori`,
  `test-catalogo-messaggi-errore-completo` e `test-vw-codici-errore-motivo-nominato`: verdi dopo.
* **D-6, fixture rifatte** (costruivano un legame su una bolla gia' consegnata, che ora il lock rifiuta):
  * la «riga multipla» di `test-fn-resi-da-accreditare-chiusura`, `test-fn-partite-merce-chiusura` e
    `test-fn-situazione-merce-ordine-chiusura`: l'helper che fabbrica la bolla lega la seconda riga
    d'ordine mentre e' in bozza (`p_lega_anche`). Nel terzo la coppia e' **dedicata** (ordine A3 e B):
    sul DDT del caso 1 avrebbe reso A non misurabile gia' al test 4; l'atteso del test 9 passa da 3
    partite a 1 (una bolla sola), il significato resta. Rossi identici a prima (i test di scope, rossi da
    owner);
  * `test-resi-rinunce-fondamenta`: il ponte puntava alla riga del DDT d'ORIGINE (consegnato), forma che
    nessuna madre produce. Ora punta a una bolla in bozza dello stesso cliente. ⚠️ Il file pesca dai dati
    di dev: sullo scratch si ferma dove si fermava prima, la prova vera e' la corsa su dbdev.
* ⚠️ Lo scratch non ha anagrafiche: i file che pescano dai dati falliscono **uguale** prima e dopo, e li'
  la prova non dice niente. Conta la corsa di Tid su dbdev.
* ⚠️ **Un'altra sessione DB lavora oggi** sulle R-DB di `brief-db-testata-dopo-emissione`. Numeri
  disgiunti, ma due file condivisi: il test 2 di `test-trgfn-doc-righe-lock-fuori-bozza-v1` (anche quel
  giro monta il BB, sui satelliti) e il conteggio del rubinetto. Chi committa per secondo riallinea.

### 7.5 Decisioni prese il 2026-10-11

D-6 e D-7 (§4). Nessuna domanda aperta su questo giro.

### 7.6 Trovato nel giro: l'annullo non riapriva il residuo → D-8

La matrice ammette `DRAFT → ANNULLATO` e `EMESSO → ANNULLATO`. Nessuno toccava i legami di una bolla
annullata, e il residuo dell'ordine li somma senza guardare lo stato del DDT: l'ordine restava evaso per
merce mai partita (o stornata dal magazzino), e non si poteva piu' rispedire. Deciso da Tid il
2026-10-11 (D-8), lavorato e spostato in [brief-db-annullo-documento-con-legami](brief-db-annullo-documento-con-legami.md) §3.


## 8. D-8 — Spostato

L'annullo di una bolla con legami (ritiro con conferma: disegno, consegna DB, prova, ricaduta BE/FE) sta
dal 2026-10-11 nel brief
[brief-db-annullo-documento-con-legami](brief-db-annullo-documento-con-legami.md), §3: e' il primo caso
di un principio che vale per tutti i documenti con legami (decisione di Tid). I changeSet restano quelli
di questo giro (`20261011-14`, `-15`, `-16`, `-20`, `-34`, `-35`), la decisione resta D-8 (§4).

## 9. Apply e corsa pgTAP (2026-10-11)

Tid ha applicato `20261011-05 … -20`, `-34`, `-35` su dbdev e su `zeroerp_ci`: **nessuna regressione**.
Una fixture era sfuggita al censimento di D-8 perche' pesca la bolla dai dati invece di fabbricarla:
`script/test-capability-motivi-e-nessuna-azione-v1` test 13 annullava con un UPDATE diretto un DDT figlio
di un ordine, e il guard di transizione l'ha rifiutato (giustamente). Ora passa da `vendite.fn_annulla_ddt`,
dichiarando le righe lette da `vendite.fn_ddt_legami`. Il censimento rifatto su ogni scrittura di stato
ANNULLATO di una bolla nei pgTAP non ha trovato altri casi. Le righe dei codici nei due CSV e i due test
condivisi (rubinetto, lock delle righe) sono entrati col commit del giro della testata (`43d03c390`).

**Resta:** niente: BE/FE fatto (§10), collaudo superato e archivio (§11). Nessun debito DB da portare in archivio: il solo
trovato nel giro (l'annullo, §7.6) vive in brief-db-annullo-documento-con-legami (D29).

## 10. Consegna BE/FE (2026-10-11)

### 10.1 Backend

| Cosa | Dove |
| --- | --- |
| `evasa`, `correggi_qta_evasa_blocco` nelle righe | nessuna modifica: il repository legge `v.*` di `vw_ddt_righe_dettaglio` (lista e lettura completa) |
| Il verbo | `POST …/ddt/<id>/righe/<riga_id>/qta-evasa/` (`qta_operativa`) → `ddt_service.correggi_qta_evasa` → `DdtRepository.correggi_qta_evasa`. Il BE controlla solo che il valore sia un numero: bozza, riga evasa, residuo e quantita' positiva li giudica il DB |
| I legami per la finestra | `GET …/ddt/<id>/legami/` → `ddt_service.get_legami`: le righe di `fn_ddt_legami`, `righe_legate` (righe **distinte**, lo stesso conteggio del verbo) e le `origini` (archi di livello 1 del lineage, a livello di testata) |
| L'annullo | `cambia-stato` verso ANNULLATO passa **sempre** da `fn_annulla_ddt`, col campo nuovo `righe_legate_confermate` (assente al primo tentativo). `E_DDT_ANNULLO_CON_LEGAMI` ha l'override `confirm_and_retry` in `error_ui_overrides.py` |
| Commenti | `ddt_repository.delete_riga` e `ddt_service.elimina_riga`: la riga evasa in bozza si cancella |
| Test | 9 in `test_ddt_service.py` (29-37), 3 in `test_ddt_api.py` (15-17). Suite `core` + `vendite` verde (3939), ruff e mypy (cricchetto) puliti |
| Prova sul DB vero | smoke in transazione annullata su dbdev, ruolo `zeroerp_app`: bolla generata da un ordine, legami e origini letti, riga `evasa = true` col verbo acceso, PATCH diretto della quantita' → `E_DDT_RIGA_EVASA_FERMA`, verbo → nuova `qta_evasa`, verbo oltre il residuo → `E_QTA_SUPERA_RESIDUO`, annullo senza conferma e con conferma sbagliata → `E_DDT_ANNULLO_CON_LEGAMI`, con conferma giusta → ANNULLATO e legami ritirati |

### 10.2 Frontend

| Cosa | Dove |
| --- | --- |
| Form riga | `DdtRigaForm`: sulla riga `evasa` quantita' spenta (articolo e UoM lo erano gia' in modifica), la quantita' non viaggia nel PATCH, pulsante «Correggi quantita' evasa» col tooltip dal motivo (`vendite.ddt.correggi_qta_evasa_reason.<motivo>`, via `componiBloccoMotivo`) e una riga di spiegazione |
| Il verbo | `DdtCorreggiQtaEvasaDialog` (AppDialog sm, fotografia D-14); lo store avvisa i tab DDT, ORDINE, RESO |
| L'annullo | `DdtDrawer`: il cambio di stato passa da `useForzaturaConfermata`; la domanda apre `DdtAnnulloLegamiDialog` (righe legate, origini apribili con `DocumentoDrawerHost`, conferma che dichiara `righe_legate`). Dopo l'annullo si rileggono dettaglio, merce e collegamenti; lo store avvisa ORDINE e RESO |
| Cancellazione | invariata: segue `can_edit_righe` come le altre righe |
| i18n | le quattro chiavi dei motivi c'erano gia'; nuove `correggi_qta_evasa*`, `riga_evasa_hint`, `annullo_legami.*` (it + en). Titolo e pulsante della finestra d'annullo: `azione_annulla`, il nome dell'azione |
| Presidi | `check_i18n_keys` pulito, `npm run guards` verde, oxlint/eslint puliti, vitest `vendite` + `core` verde (596), build ok |
| Guida | `gestione-ddt.md`: §4.3 «Annullare una bolla da ordine o da reso», §6.3 «Le righe di un DDT da ordine» (pippo 10→15 e 10→6), errori, §15.3 |

### 10.3 Trovato nel giro, fuori da questo brief

* ⚠️ **Gli altri cambi di stato del DDT non passano dal verbo.** ➡️ Alla chiusura: e' gia' la richiesta
  R-1 del Lotto 3 (`brief-db-magazzino-lotto-3-scarico-da-ddt` §6), voce di PROJECT_CONTEXT «Magazzino,
  Lotto 3»: non si eredita a parte. `ddt_service.cambia_stato` (e quindi
  `emetti`) fa ancora l'UPDATE diretto di `stato_doc_ddt_id`, mentre `vendite.fn_cambia_stato_ddt` si
  dichiara «VERBO di ogni cambio di stato di una bolla»: su una bolla che muove merce il guard risponde
  `E_DDT_STATO_SOLO_DA_VERBO`. Qui e' stato portato al verbo il solo ANNULLATO (via `fn_annulla_ddt`,
  che lo chiama). Il resto e' il lato BE del Lotto 3 del magazzino, gia' aperto in PROJECT_CONTEXT.
* Da verificare, non un difetto dichiarato: lo smoke ha trovato un ordine `EVASO` per cui
  `fn_ordine_ha_residuo_evasione` risponde `true` (reso-aware), e `fn_genera_ddt_da_ordine` lo rifiuta per
  stato. Se il residuo riaperto da un reso si rispedisce solo dalla ri-consegna, i due sono coerenti;
  se qualche superficie usa quel predicato per accendere «Genera DDT» sull'ordine, il pulsante sarebbe
  acceso su un gesto rifiutato. ➡️ **Verificato alla chiusura: e' un dato, non un difetto del modello.**
  Nessuna capability e nessun codice del backend leggono il predicato (lo usano solo le madri e la
  proiezione). L'ordine trovato (62688, dbdev) e' `EVASO` con **zero** legami di evasione e l'ultima
  scrittura il 2026-09-30: nessuna strada del modello lo produce (la proiezione da' `CONFERMATO` senza
  legami, e prima di questo giro un legame non si poteva togliere). Si corregge a mano se serve.

### 10.4 Richiesta al team DB — il messaggio di `E_QTA_SUPERA_RESIDUO` (rilievo in-app di Tid, 2026-10-11)

Correggendo la quantità evasa oltre il residuo (verbo D-2), l'operatore legge:

> «Quantità supera residuo. Tabella ordine_riga id 69422.  Quantità ordine qta_ordine , quantità evasa22.000000 , qtà nuovaevasa_pre, residuo 0.000000»

**Il difetto sta nel guard, non nel testo.** `vendite.trgfn_ordini_ful_guard_consistenza`
(changeSet `20261009-80`, stessa chiamata in `20260921-49`) passa a `script.fn_log_and_raise_error`
dieci argomenti VARIADIC a coppie nome/valore (`'ordine_riga', id, 'qta_ordine', v, 'evasa_pre', v, …`),
mentre il template in `config.messaggi_errore` ha sei `%s` posizionali. I segnaposto quindi si prendono
nomi e valori alla rinfusa: «Quantità ordine **qta_ordine**», «qtà nuova**evasa_pre**». Il pgTAP
(`test-ddt-righe-evase-dall-ordine` 17, `test-fn-genera-ddt-da-ordine` 21) verifica il codice e non il
testo, quindi è verde.

**Cosa chiede Tid:**

1. Un **numero leggibile** al posto dell'id tecnico: il numero dell'ordine e il numero della riga, non
   «Tabella ordine_riga id 69422».
2. **Togliere dal messaggio tutta la parte delle quantità** (ordine, evasa, nuova, residuo): per
   l'operatore è superflua. I valori restano nel `jsonb` di contesto del log, dove servono a chi indaga.

Forma indicativa (le parole le sceglie il team DB): *«La quantità supera il residuo della riga {riga_nr}
dell'ordine {numero}.»* Il template e la chiamata vanno **allineati insieme**: un `%s` per ogni valore
passato, senza coppie nome/valore. Va aggiunto un test pgTAP **sul testo** del messaggio, così uno
sfasamento come questo non resta verde. Il ripiego BE (`error_messages_fallback.py`) è già senza `%s`
e non cambia; dopo l'apply si rigenera la policy (`error_policies_generated.py`) col DB allineato a git.

## 11. Chiusura (2026-10-11)

* Collaudo a video di Tid superato: riga evasa ferma, «Correggi quantita' evasa» (10 → 6 con l'ordine
  `PARZIALMENTE_EVASO`, oltre il residuo rifiutato), riga a mano su bolla da ordine (10 → 15), cancellazione
  della riga evasa in bozza, annullo con la finestra dei legami (da bozza e da emessa), bolla senza legami,
  ri-consegna da reso.
* Nessun residuo ereditato: i due punti del §10.3 sono uno gia' del Lotto 3, l'altro un dato.
* Il principio dell'annullo con legami continua, per gli altri documenti, in
  [brief-db-annullo-documento-con-legami](brief-db-annullo-documento-con-legami.md) (D29).
* Registro dei difetti: **D28** chiusa (§7 di `migliorie-generali-da-test-valutazione.md`).
