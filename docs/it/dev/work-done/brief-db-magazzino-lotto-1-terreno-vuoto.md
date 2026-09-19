# Brief DB — magazzino, Lotto 1: il terreno vuoto

> **Destinatario:** team DB (`dev/db-tid`). ⛔ **Niente per BE/FE in questo
> lotto**: `backend/apps/magazzino` è uno scheletro e resta tale finché non
> esiste la primitiva (Lotto 2). Nessuna vista di lista, nessuna chiave i18n,
> nessun endpoint nasce qui.
>
> **Origine.** Decisione di Tid, 2026-09-14: *«la prima cosa da fare è
> l'analisi carico e scarico, utile sia per vendite che acquisti»*, e lo stesso
> giorno le cinque decisioni che quel documento **presupponeva** senza
> possederle — D-1, D-4, D-6, D-7, D-8 dell'[analisi aggancio
> §8-quater](../work-in-progress/analisi-db-magazzino-aggancio-documento-e-produzione.md). Con
> quelle prese, il primo pezzo eseguibile è **tutto il DDL già deciso**, sul
> terreno vuoto.
>
> **Stato:** ✅ **CHIUSO lato DB** (Tid, 2026-09-15 sera): migrazione applicata
> su dbdev — 26 changeSet `EXECUTED`, nessun `MARK_RAN` dove non atteso —,
> automazioni passate, **baseline pgTAP verde su dbdev e su `zeroerp_ci`**
> (il DB ricostruito da zero). Ventitré file di changeSet, cinque pgTAP del
> lotto più due fuori lotto riscritti, la doc. ✅ **Commit `61b4cb5d3` su
> `dev/db-tid` (15-09, 15:18), pushato, pagine auto-gen rigenerate e dentro.**
> ✅ **Mergiato su `Tito-dev`** (PR #1593, 15-09 14:43 UTC, commit `937acd83a`
> = il `61b4cb5d3` riallineato dopo #1592). Corsa del merge (`34984791746`):
> pgTAP **nessuna regressione**, RIENTRATO di `config/test-sorgenti-scope-pulizia-v1`
> confermato; Django era rosso per i soli `E_MAG_*` — **chiuso dal BE con
> `6f786ed9f` (PR #1595), CI su `Tito-dev` verde dalle 16:45 UTC del 15-09**
> (§12 p.6-7). ✅ **CHIUSO e archiviato in `work-done/` il 2026-09-17 (sera)**:
> i tre «aperti» del 17-09 sono rientrati lo stesso giorno, ciascuno letto
> dalla sua sorgente e non supposto — (1) il brief gemello
> `brief-db-emittente-di-default-un-bb-solo` è **applicato** su dbdev
> (`20260915-36 → -46` `EXECUTED` alle 12:06, dal `databasechangelog`;
> `trg_magazzini_a10_default_emittente_ins` e `trg_assets_a10_default_emittente_ins`
> montati: il punto §4.7 è chiuso) e il BE lo ha già assorbito
> (`E_EMITTENTE_NON_RISOLTO` a policy, i tre codici marcati RITIRATI); (2) la
> riga 58 di `baseline-rossi-ci.tsv` è **tolta** con
> `scripts/pgtap-baseline-ci-rientrati.sh 35241276981` (la corsa verde del merge
> #1601, 15:35 UTC: `config/test-sorgenti-scope-pulizia-v1` RIENTRATO, 372 → 365
> righe insieme a sei rientrati di `pagamenti`/`vendite` che la stessa corsa ha
> dichiarato); (3) `requires_lotto` in UI è del **Lotto 2** per definizione
> (§4.3), non un residuo di questo. Verificato sui file di HEAD (`86deea82f`),
> non sul commit: 2 `E_MAG_*` in ciascun modulo BE, 0 `ambito_causale` in
> `backend/apps` e `frontend/src`; «Django tests» della corsa `35241276981`:
> `Ran 4872 tests … OK (skipped=32)`. ⛔ Il cantiere `dbops` sull'ordine
> dei job **non si apre** (§12 p.2: le automazioni su dev si lanciano a mano).
> ⚠️ La sera del 15-09 ha insegnato più della scrittura: **sette** cose erano
> verdi in sessione per ragioni sbagliate e le ha trovate solo il DB da zero
> o il runner — sono le ultime sei righe di §5, e il Lotto 2 parte da lì.
> Le §3 porta **sette decisioni piccole** che il
> DDL richiede e che l'analisi non aveva chiuso: **tutte confermate da Tid il
> 15-09** (§3). ⭐ Le ultime due (D-L1-f, D-L1-g) sono **uscite dal
> censimento P-0**, non dalle colonne: il riquadro di §6-bis dice da dove.
>
> **Perimetro:** il **DDL** di `magazzino` (più tre tocchi fuori schema:
> `catalogo.articoli.requires_lotto`, `config.sorgenti`, `dbops`), il **guard
> del verso** (M-1), il **perimetro RLS** (M-6) con la sua variante di scope, e
> i **pgTAP strutturali**. ⛔ Fuori: la primitiva, le operazioni, la vista di
> disponibilità, la vista degli orfani — sono il Lotto 2, e la §9 dice perché
> non stanno qui.
>
> ⚠️ **Le decisioni non si ridiscutono qui.** Ogni riga di DDL sotto cita la
> decisione da cui discende (M-* di carico/scarico, D-* dell'aggancio). Se una
> riga non ha una decisione dietro, è in §3 con una raccomandazione — oppure
> è un difetto di questo brief.

---

## 0. In due parole, senza tecnicismi

Il magazzino di ZeroErp è **disegnato e mai partito**: le tabelle ci sono, le
regole sono state decise in tre analisi fra il 1° e il 14 settembre, e **non c'è
una sola riga dentro**. Questo lotto **mette le tabelle nella forma decisa** —
cambia nomi, toglie colonne che non servono più, aggiunge quelle che mancano,
mette i vincoli — e **chiude il recinto** (chi vede che cosa) prima che
qualcuno cominci a scrivere.

Non fa entrare né uscire merce: quello è il lotto dopo. Ma è il lotto in cui
ogni cambiamento **costa zero** — fra sei mesi le stesse modifiche vorrebbero
dire migrare dati, riscrivere funzioni, e ri-provare tutto.

---

## 1. Il filtro: che cosa entra qui, e perché adesso

Entra ciò che soddisfa **tutte e tre** le condizioni:

1. è **deciso** (M-1 → M-9, oppure D-1/D-2/D-3/D-4/D-6/D-7/D-8/D-9);
2. è **DDL, seed di catalogo, o codice che il DDL richiede** (il guard del
   verso, la variante di scope, le policy) — non un'operazione;
3. **nessuna funzione applicativa lo legge** oggi, quindi cambiarlo non rompe
   un comportamento in esercizio.

⭐ **La terza condizione è la ragione del «adesso»**, ed è una lettura di
struttura, non una misura: `magazzino` ha **due** funzioni in tutto
(`fn_get_magazzino_note`, `trgfn_magazzini_normalize`), nessuna delle due
tocca ciò che questo lotto rinomina o toglie, e `backend/apps/magazzino` è
uno scheletro. Il giorno in cui la primitiva esiste, ogni rinomina diventa una
riscrittura di funzione.

⚠️ **E il perimetro RLS entra qui, non nel Lotto 2** — ed è un vincolo
scoperto scrivendo, non una preferenza. `dbops.vw_rls_perimetro_scoperto` (in
servizio dall'11-09) marca `NON_DICHIARATO` **ogni tabella con una FK verso una
tabella protetta** senza policy + `ENABLE`, e il suo pgTAP fa rosso. Armare
`magazzini` e non le sue figlie (`movimenti`, `ubicazioni`, `inventari`, le
note…) lo farebbe rosso sulle figlie. *Il perimetro si chiude quando nasce
l'ancora.*
🔴 **Corretto in P-0 (14-09)**: la prima stesura diceva anche *«dare a
`magazzini` la FK verso `anagrafiche.emittenti_fiscali` e non armarla farebbe
rosso il presidio»*. **Falso**: `emittenti_fiscali` ha `relrowsecurity = false`
(è un'anagrafica di sistema, non un documento), e l'unico criterio della vista
è `FIGLIA_DI_TABELLA_PROTETTA` — una FK verso una tabella **non** protetta non
la fa scattare. Il vincolo è **transitivo e parte da `magazzini` armata**, non
dalla FK: la ragione del «tutto in un giro» resta, la sua metà sbagliata esce.

---

## 2. Le decisioni da cui discende ogni riga

| Decisione | Dove | Che cosa impone qui |
| --- | --- | --- |
| **M-1** verso nella quantità | carico/scarico §4 | `causali.segno ∈ {−1, +1}`; guard `sign(qta) = segno` su `movimenti` e `movimenti_attesi`; cade `qta > 0` sugli attesi; `COMMENT` su `vw_giacenza` |
| **M-2** primitiva + operazioni | §5-bis | ⏸️ **Lotto 2** — qui solo ciò che la primitiva leggerà: le colonne di catalogo |
| **M-3** disponibile | §7-bis | ⏸️ Lotto 2 — qui la **forma** di `movimenti_attesi` |
| **M-4** valorizzazione | §7-ter | `costo_medio` → `valore_giacenza`, senza `qta`, con FK articolo; `impatto_valorizzazione` via; `COMMENT` su `costo_unitario`; le tre viste rifatte |
| **M-5** lotti, seriali, ubicazioni | §7-quater | tabella `lotti`; `articoli.requires_lotto`; `movimenti.lotto_id`/`asset_id`; `\|qta\| = 1` con seriale; `richiede_lotto`/`richiede_seriale` via; vista per ubicazione; via `magazzino_id_dest`, `ubicazione_id_from/_to`, `richiede_magazzino_dest` e i due CHECK; `assets.ubicazione` via. ⭐ *Propagata alle righe delle testate* (aggancio §8-quater, D-6) |
| **M-6** perimetro | §7-sexies | `magazzini.emittente_fiscale_id`, `assets.emittente_fiscale_id`, `movimenti_attesi.magazzino_id NOT NULL`, policy su tutto ciò che porta merce o valore, `ENABLE` (non `FORCE`: postura del progetto), viste `security_invoker` |
| **M-8** storno | §7-quinquies | `movimenti.attivo` via; legame allo stornato; ⭐ causali dello storno (§3, D-L1-d) |
| **D-1** catalogo | aggancio §8-quater | `sorgente_tipo_id` + `sorgente_riga`/`sorgente_uid` su ledger e attesi; `doc_*` via |
| **D-2/D-3** testate | idem | `sorgente_riga` sulle quattro; guard tipizzato su **sei** tabelle; FK mancante su `rettifiche`; doppione su `trasferimenti` |
| **D-4** identità | idem | `UNIQUE … NULLS NOT DISTINCT` sull'identità; `uq_mag_movimenti_docref` e `uq_mag_reservations_docref` via; niente progressivo |
| **D-6** sorgente obbligatoria | idem | `NOT NULL` sul ledger; nullable sugli attesi; `lotto_id`/`asset_id` sulle righe delle testate |
| **D-7** operazioni a catalogo | idem | `scope` nuovo; cinque righe di magazzino + le cinque `*_RIGA` fantasma nel CSV |
| **D-8** ambito via | idem | `ambito_causale_id`, `ambito_causale`, `richiede_odl`, `contabilizza_cdc`, `abilita_billing` via; quattro causali nuove |
| **D-9** presidi | idem | FK + guard sul ledger (qui); la vista degli orfani nel Lotto 2 |
| **D-5** ODL | ⏸️ aperta | niente: nessun passo la presuppone |

---

## 3. ⚠️ Le cinque decisioni piccole che il DDL richiede

> Sono uscite scrivendo le colonne, non le analisi. Ognuna ha una
> raccomandazione; **si confermano prima di scrivere il passo che le tocca**.
> Nessuna cambia la forma del lotto: cambiano una colonna o un vincolo.
> ✅ **Confermate da Tid il 2026-09-15**: D-L1-a, b, c, d, e, f come
> raccomandate; **D-L1-g contro la raccomandazione** (si droppa ora, la
> richiesta a BE/FE sta nella decisione). I due scostamenti di P-1 (§4.3)
> confermati lo stesso giorno.

### D-L1-a — In che unità è scritto il ledger? → **nella UoM base dell'articolo; `movimenti.uom_id` si toglie**

`movimenti.uom_id` è nullable e nessuna decisione lo nomina. Ma `vw_giacenza`
**somma `qta`** per articolo e magazzino: se due movimenti dello stesso articolo
portassero unità diverse, quella somma non significherebbe niente, e nessun
vincolo lo impedirebbe — è la stessa forma del verso lasciato libero (M-1).
⇒ Il ledger è in **UoM base** (`catalogo.articoli.uom_id`, NOT NULL), e la
colonna sul movimento è ridondante. *Come l'operatore l'ha digitata* (10 scatole
da 12) sta sulla riga di documento, che ha `uom_operativa_id` +
`factor_to_base` — e il movimento la raggiunge attraverso la sorgente. La
conversione la fa l'**operazione** prima di chiamare la primitiva (Lotto 2);
qui si toglie la colonna e si scrive la regola nel `COMMENT` di `qta`.

### D-L1-b — Il ciclo degli attesi → **`stato ∈ {APERTA, CHIUSA}` + `data_chiusura`; `attivo` si toglie**

§7-bis dice che `planned → picked → fulfilled → cancelled` va rifatto
(*«`picked` è di sola uscita»*) e non dice come. Con la tabella ridotta a ciò
che non si deriva — il **blocco manuale** e la **merce prelevata non ancora
uscita** — la natura dell'attesa la dice già la **causale** (verso) più la
**sorgente** (c'è un documento o no); allo stato resta una domanda sola: *conta
ancora?* ⇒ `stato` `APERTA`/`CHIUSA` (CHECK, non tabella: due valori senza
attributi), `data_chiusura` obbligatoria se e solo se `CHIUSA`. ⛔ `attivo` si
toglie per la stessa ragione di M-8: sarebbe il secondo modo di dire «non
conta». Il blocco si **libera a mano** (§7-bis): liberare = `CHIUSA`, con la
data e l'autore dell'audit.

### D-L1-c — Il «verbo» dell'identità → **è la causale; niente `operazione_verbo`**

§6 mette nell'identità un verbo (`SCARICO`, `OUT`, `IN`, `STORNO`…) e propone
una colonna nuova. Ma nel modello a due cataloghi **la causale è già il verbo
dell'operazione**: `TRASF_OUT` e `TRASF_IN` distinguono le due righe del
trasferimento, `ODL_USCITA_MAT` un prelievo, e lo storno (D-L1-d) ha causali
sue. Una colonna `operazione_verbo` sarebbe un **vocabolario parallelo** alle
causali — precisamente il «quinto asse» che §6 vieta per i prefissi. ⇒
L'identità è `(sorgente_tipo_id, sorgente_riga, sorgente_uid, causale_id,
asset_id, lotto_id, ubicazione_id)`. ⚠️ Vale perché `causale_id` sul movimento
è **immutabile** (è un ledger): se un giorno una causale si ritira, le righe
storiche la tengono. Se la proposta è respinta, P-4 aggiunge la colonna col
suo CHECK e la mette nell'indice al posto di `causale_id`: cambia una riga.

### D-L1-d — Lo storno ha bisogno di causali sue → **`STORNO_POS` (+1) e `STORNO_NEG` (−1)**

Sotto il guard di M-1 il movimento contrario **non può** portare la causale
dell'originale: `SCARICO_VEN` è −1 e lo specchio è +1. Due causali generiche,
sullo stampo di `RETT_POS`/`RETT_NEG`; *che cosa* è stornato lo dice il legame
`storno_di_movimento_id`, non la causale. ⛔ Non una causale-specchio per
ciascuna delle sedici: sarebbero sedici righe che dicono la stessa cosa.

### D-L1-e — Le note sull'accumulatore → **`note_costo_medio` si ritira**

`valore_giacenza` diventa (M-4) una **copia ricostruibile** dal registro. Una
nota su una copia non ha un autore naturale: se qualcuno deve dire qualcosa di
un valore di giacenza, lo dice dell'articolo o del magazzino. Rinominarla in
`note_valore_giacenza` conserverebbe una partizione che nessuno scriverà.
⇒ Si toglie la partizione e il valore `COSTO_MEDIO` esce dal CHECK
`chk_note_target_tipo` del padre. *(Se preferisci tenerla: rinomina + bound
`VALORE_GIACENZA`, in P-6.)* ✅ P-0 conferma che è sicuro: zero lettori di
`COSTO_MEDIO` in `pg_proc`, backend, frontend, pgTAP e seed.

### D-L1-f — Le cinque `*_RIGA` fantasma sono **`attivo = false`** → **entrano nel CSV `attivo = true`, `meta = '{}'`**

🔴 Trovato in P-0 (d): le righe 3/5/7/9/11 di `config.sorgenti` sul DB di
sviluppo non sono solo *fuori dal CSV* — sono **archiviate**: `attivo = f`,
`meta = {"archived": true, "archived_at": "2026-02-25 …", "archived_reason":
"Sorgenti RIGA legacy fuori scope commessa-v2"}`, per un `UPDATE` a mano che
**nessun changeSet registra**. Il brief le copiava «per identità», e per
identità le avrebbe seminate **spente**. Ma `script.trgfn_guard_sorgente_polimorfa_tipizzata`
pretende `s.attivo = true` (altrimenti `E_SORG_CONF`), e il `require_attivo`
generato su `movimenti.sorgente_tipo_id` le rifiuterebbe comunque: uno scarico
`DDT_VENDITA_RIGA:{riga}` — *«la sorgente esiste già a catalogo»*, dice
l'analisi c/s §6 — sarebbe **rifiutato** su dev e su CI, per due guard.
⇒ Raccomandazione: le cinque entrano **attive e senza il marchio**. Ragione
sul modello: `config.sorgenti` descrive **che cosa può essere nominato come
sorgente** — cinque tabelle di riga che esistono — non chi lo nomina oggi; il
motivo dell'archiviazione parla di *un* consumatore (commesse-v2) e vale per
lui, non per il catalogo. Alternativa più stretta: attive solo `ORDINE_VENDITA_RIGA`
(7, l'atteso) e `DDT_VENDITA_RIGA` (9, lo scarico), le altre tre come stanno —
ma sarebbe seminare tre righe archiviate su un DB nuovo, cioè spedire un
ricordo di dbdev come progetto. ⚠️ Su dev il loader fa un `UPDATE` f→t: nessun
guard lo ferma (i `block_deact` guardano solo t→f).

### D-L1-g — `ambito_causale` ha **due lettori vivi fuori dal DB** → **si droppa ora, con la richiesta a BE/FE** (Tid, 15-09)

🔴 Trovato in P-0 (b): `magazzino.ambito_causale` è nominata da
`backend/apps/core/db/dbops_repository.py:107` (whitelist `_REL_CONSENTITE`
del CRUD generico delle tabelle di configurazione) e da
`frontend/src/core/config-tables.js:63` (registro `CONFIG_TABLES` del pannello
admin, voce «Ambito Causale»). Sono due righe morte — ma un `DROP TABLE` nello
stesso giro le trasforma in un **500** sulla voce del pannello, e la regola è
scritta (memoria `reference_cancellare_una_fonte_censire_i_lettori`, caso
`storico.risorse_umane_auth_user` del 12-09): *un lettore vivo fuori dal
database decide l'ordine di apply, e una frase nel brief non è un cancello*.
Raccomandavo di differire il `DROP TABLE` a un changeSet a parte, dopo BE/FE.
✅ **Decisione di Tid (2026-09-15): si droppa ORA** e si accetta il 500 sulla
voce «Ambito Causale» del pannello finché i due lati non tolgono le righe —
è una voce di amministrazione senza dati dietro, non un percorso di esercizio.
⇒ P-3 come nella prima stesura (tabella, `storico.ambito_causale`, loader
`20251001-05`, CSV, riga 69 di `storico_scope_policy` con `DELETE`,
`manual/`). 🔵 **Richiesta a BE e FE** (da fare nello stesso giro di PR, o
subito dopo): togliere `"magazzino.ambito_causale"` da `_REL_CONSENTITE` in
`backend/apps/core/db/dbops_repository.py` (riga 107 al 14-09) e la riga
`{ schema: 'magazzino', rel: 'magazzino.ambito_causale', … }` da
`CONFIG_TABLES` in `frontend/src/core/config-tables.js` (riga 63). Finché
restano, la voce risponde `42P01` → 500; nessun'altra conseguenza.

---

## 4. Il DDL, tabella per tabella

> Letto dalla **doc auto-generata** (`docs/it/dbzero/magazzino/tabelle/*.md`)
> il 2026-09-14, non dagli YAML. Dove dico «generato» intendo un trigger che
> nasce da `ci_apply` (audit, `tx_id`, storico, `require_attivo`,
> `block_deact`): su quelli **niente DDL incondizionata** — §5.

### 4.1 `magazzino.causali` (D-8, M-1, M-4, M-5, D-L1-d)

| Cosa | Come | Decisione |
| --- | --- | --- |
| `segno` | CHECK `chk_magazzino_causali_segno` riscritto: `segno IN (-1, 1)`; **`DROP DEFAULT`** (era `0`, che il CHECK ora vieta: un default vietato è una contraddizione scritta) | M-1 |
| `impatto_valorizzazione` + `chk_magazzino_causali_imp_val` | **DROP** | M-4 |
| `richiede_lotto`, `richiede_seriale`, `richiede_magazzino_dest` | **DROP** | M-5 |
| `abilita_billing`, `richiede_odl`, `contabilizza_cdc` | **DROP** | D-8 |
| `ambito_causale_id` + `fk_mag_causali_ambito` + `ix_magazzino_causali_ambito_causale_id` | **DROP**; il generato `trg_causali_a10_ambito_causale_require_attivo_ins_upd` → `DROP TRIGGER IF EXISTS` (non si rigenera: la FK non c'è più) | D-8 |
| `is_installazione_asset`, `is_rettifica`, `consente_stock_negativo`, `ordine`, `codice`, `codice_interno`, `descrizione`, `attivo` | **restano**. ⚠️ `is_installazione_asset` non è censita da nessuna analisi: nessuna funzione la legge (verificato 14-09 su `20_code/` e `backend/`). Resta perché è la sola marca che lega la causale al ciclo di vita dell'asset (`ASSET_INSTALL`), e il consumatore nasce col Lotto 2 — se allora non lo trova, esce | — |
| **tabella `ambito_causale`** | **DROP TABLE** (+ `storico.ambito_causale` `IF EXISTS`, zero righe al 14-09) — ha due lettori vivi in BE e FE, e Tid ha scelto di droppare ora con la richiesta ai due lati (D-L1-g). Il suo `block_deact` cade con lei. `DELETE` della riga 69 di `storico_scope_policy` (loadUpdateData non cancella; stampo `20260912-09`). ⚠️ Il suo loader `80_data/changelog/20251001-05-upsert-magazzino-ambito-causale-table.yaml` ha `onFail: HALT` + `tableExists`: su un DB da zero girerebbe **dopo** il DROP e fermerebbe il migrate ⇒ **si cancella il file del loader e il CSV** (`ambito_causale.csv`). Un loader di una tabella ritirata è codice morto; l'id resta orfano in `databasechangelog` su dev, e Liquibase non se ne lamenta. ⭐ Verificare con `liquibase validate` prima dell'apply | D-8, D-L1-g |
| **seed** `causali.csv` + loader `20251001-51` | il CSV perde le otto colonne tolte; il loader (`runOnChange` + `validCheckSums: ANY`, quindi **modificabile in place** — precedente `20260614-08`) perde le stesse righe nella lista `columns:`. **Sei righe nuove** (id **23-28** — la prima stesura diceva 11-16, ma le dieci esistenti sono 13-22): | §3 c/s, D-L1-d |

| id | `codice` = `codice_interno` | `segno` | `ordine` | `is_rettifica` | `consente_stock_negativo` | Descrizione |
| --- | --- | --- | --- | --- | --- | --- |
| 23 | `CARICO_RESO_VEN` | +1 | 21 | f | f | Carico da reso cliente (`vendite.resi`) |
| 24 | `SCARICO_RESO_ACQ` | −1 | 22 | f | f | Scarico per reso a fornitore |
| 25 | `ODL_VERSAMENTO_PF` | +1 | 52 | f | f | Versamento prodotto finito da ODL |
| 26 | `INV_INIZIALE` | +1 | 42 | f | f | Inventario iniziale (primo carico) — ⛔ **non** `is_rettifica`: dice un'altra cosa (§3 c/s) |
| 27 | `STORNO_POS` | +1 | 90 | f | f | Storno in entrata (specchio di una uscita) |
| 28 | `STORNO_NEG` | −1 | 91 | f | f | Storno in uscita (specchio di una entrata) |

⚠️ **Trovato provando P-3**: un id esplicito da CSV **non avanza la sequence** —
`causali_id_seq` era a 24 e la tabella arriva a 28; `magazzino.causali` è nel
CRUD generico del pannello admin, quindi la prima causale creata a mano
avrebbe preso 23 → duplicato. ⇒ `80_data/20260915-04` riallinea
`causali_id_seq` **e** `sorgenti_id_seq` (stessa cosa per le righe 16-20; lì la
sequence era già a 32, `GREATEST` non la fa arretrare). Stampo `20260802-27`.

⚠️ Le dieci righe esistenti: `TRASF_OUT`/`TRASF_IN` perdono `none` con la
colonna (M-4: il trasferimento valorizza). Nessun altro valore cambia.

### 4.2 `config.sorgenti` (D-7)

| Cosa | Come |
| --- | --- |
| `chk_sorgenti_scope` | si estende con **`MAGAZZINO`** — *«record di operazione che genera movimenti di magazzino»* — nella forma di `20260714-07` (`REVERSE_FLOW`); il `COMMENT` della colonna si aggiorna |
| CSV `sorgenti.csv`, **le cinque fantasma** | `PREVENTIVO_RIGA` (3), `CONTRATTO_RIGA` (5), `ORDINE_VENDITA_RIGA` (7), `DDT_VENDITA_RIGA` (9), `FATTURA_RIGA` (11): 🔴 esistono **solo sul DB di sviluppo** (intestazione di `20260820-03`; CSV a 10 righe, DB a 15) **e sono archiviate** (`attivo = f`, `meta.archived` — D-L1-f). Entrano nel CSV con `target_table`, `key_selector = id`, `tipo_doc_fiscale_id` e `data_insert` letti dalle righe vive, ma **`attivo = t` e `meta = {}`** — il loader è `loadUpdateData` su `id`: su dev fa un `UPDATE` f→t (nessun guard lo ferma), su CI un `INSERT`. `scope = ROW_VALIDATOR`, `categoria = RIGA`, `area` NULL, `label_selector` NULL |
| CSV, **le righe di magazzino** (id 16-20) | `RESO_VENDITA_RIGA` → `vendite.resi_righe` (`ROW_VALIDATOR`, come le sorelle); `INVENTARIO_RIGA` → `magazzino.inventari_righe`, `RETTIFICA_RIGA` → `magazzino.rettifiche_righe`, `TRASFERIMENTO_RIGA` → `magazzino.trasferimenti_righe`, `EVENTO_ASSET` → `magazzino.eventi_assets` (`MAGAZZINO`). Tutte `key_selector = 'id'`, `categoria = RIGA`, `area` NULL, `tipo_doc_fiscale_id` NULL, `label_selector` NULL |

⚠️ `target_table` è `regclass`: il CSV si carica in `80_data`, dopo tutto
`00_schema` — le tabelle esistono. ⛔ E nessun changeSet di `00_schema`/`20_code`
di questo lotto precondiziona sull'esistenza di queste righe (`guardrail_precondition_seed.py`).

### 4.3 `magazzino.lotti` — nuova — e `catalogo.articoli.requires_lotto` (M-5)

```
lotti: id bigint identity PK · articolo_id uuid NOT NULL FK catalogo.articoli
       · codice varchar(64) NOT NULL · data_arrivo date NOT NULL
       · data_scadenza date · attivo bool NOT NULL DEFAULT true
       · meta jsonb NOT NULL DEFAULT '{}' · tx_id uuid · storicizza bool NOT NULL DEFAULT true
       · data_insert/user_insert/data_update/user_update
UNIQUE (articolo_id, codice) — lo stesso codice su articoli diversi è legittimo (§7-quater)
CHECK btrim(codice) <> ''  ·  CHECK data_scadenza IS NULL OR data_scadenza >= data_arrivo
COMMENT su data_arrivo: «data di arrivo o di produzione: quella da cui si conta la rotazione (FIFO fisico)»
```

✅ **Scritta il 14-09** (`00_schema/catalogo/20260914-15`, `00_schema/magazzino/20260914-16`,
`80_data/changelog/20260914-17` + `sql/magazzino/fk_index_policy_magazzino_lotto1.csv`,
riga 122 di `storico_scope_policy.csv`), provata con l'SQL estratto in
transazione annullata: UNIQUE per articolo, i due CHECK, la FK **coperta**
secondo `vw_fk_senza_indice`. **Due scostamenti** dalla riga qui sopra come era
stata scritta, entrambi motivati nell'intestazione dei changeSet:

- `storicizza DEFAULT **true**` (era `false`): la tabella esiste per la
  tracciabilità, e *«chi ha spostato la scadenza di questo lotto»* è una
  domanda che si fa — storicizzazione permanente, la forma delle anagrafiche
  (`magazzini`, `causali`), non quella one-shot di `reservations`;
- `fk_index_policy` → **f**, non `t`: l'UNIQUE `(articolo_id, codice)` ha
  `articolo_id` come prefisso, `vw_fk_senza_indice` non la elenca, e con `t`
  `apply_fk_index_policy` la salterebbe comunque (guardia 1). Un indice a
  mano sarebbe la ridondanza bonificata il 27-07 su `costo_medio`. Stessa
  forma della riga di `valore_giacenza` (§4.6).

- `catalogo.articoli.requires_lotto boolean NOT NULL DEFAULT false`, accanto a
  `requires_serial`: **due booleani distinti** (§7-quater, punto 3).
- ⛔ **Fuori dal perimetro RLS** (§7-sexies, correzione del 04-09): è una
  definizione, non ha `magazzino_id`, e non ha FK verso tabelle protette —
  quindi il presidio non la vede.
- ⚠️ Tabella nuova: audit, `tx_id` e storico **arrivano da `ci_apply`** (su dev,
  il pgagent alle 21:00). Nessun trigger si scrive a mano.
- `fk_index_policy`: `fk_mag_lotti_articolo` → **f** — la domanda «i lotti di
  questo articolo» è il primo accesso, e la serve già l'UNIQUE (vedi sopra).
- ⚠️ `requires_lotto` **non** entra nel guard BoM
  (`trgfn_articoli_guard_flags_struttura_bom_attiva`, che congela
  `is_composito`/`requires_serial` su un padre di distinta attiva): il lotto
  è una partita, non struttura di composizione. Se un giorno lo sarà, è una
  riga in quel guard.
- 🔵 **Per BE/FE, Lotto 2**: `requires_serial` è esposto da
  `vw_articoli_dettaglio`, da `catalogo_repository`/`catalogo_service`/`views`
  e dal drawer articolo (`ArticoloDrawer.vue`); `requires_lotto` dovrà
  seguirlo quando la primitiva lo leggerà — la vista la tocca il DB in quel
  lotto. ⚠️ **Corretto il 15-09 (sera)**: la prima stesura (e l'intestazione di
  `20260914-15`) diceva *«un `CREATE OR REPLACE` oggi azzererebbe
  `security_invoker`»* — **falso**: quella vista **non** ha `security_invoker`
  e non deve prenderlo (`catalogo.articoli` non è in RLS; è scritto nel suo
  `COMMENT`, presidio `rls/test-rls-viste-security-invoker`). La ragione vera
  del rinvio è una sola: **nessun consumatore** finché la primitiva non legge
  la colonna. ⛔ **E «per simmetria» vale solo per il POSTO nel drawer, non per
  il comportamento**: `requires_serial` è un **flag di struttura BoM** —
  congelato da `trgfn_articoli_guard_flags_struttura_bom_attiva` insieme a
  `is_composito`/`is_solo_componente`, registrato in
  `dbops.lock_columns_conditional`, e il drawer lo **disabilita** via
  `non_editable_fields` quando l'articolo è padre di una distinta attiva.
  `requires_lotto` è **fuori** da quel guard e da quel registro **per
  decisione** (§7-quater p.3: una partita non è struttura di composizione):
  il toggle nel drawer **non** passa da `isFieldLocked`, e il BE non lo mette
  nel lock. Chi copia `requires_serial` a occhi chiusi eredita il lucchetto.

### 4.4 `magazzino.movimenti` (D-1, D-6, D-4, M-1, M-5, M-8, D-L1-a, D-L1-c)

| Cosa | Come | Decisione |
| --- | --- | --- |
| `doc_schema`, `doc_table`, `doc_id`, `doc_riga_id`, `uq_mag_movimenti_docref` | **DROP** | D-1, D-4 |
| `sorgente_tipo_id bigint NOT NULL` FK `config.sorgenti`; `sorgente_riga bigint`; `sorgente_uid uuid` | **ADD**; CHECK `chk_mag_movimenti_sorgente_chiave`: `(sorgente_riga IS NOT NULL) <> (sorgente_uid IS NOT NULL)` — esattamente una chiave | D-1, D-6 |
| guard tipizzato | `trg_movimenti_a10_guard_sorgente_ins_upd` `BEFORE INSERT OR UPDATE OF sorgente_tipo_id, sorgente_riga, sorgente_uid` → `script.trgfn_guard_sorgente_polimorfa_tipizzata()` (nome sullo stampo di `commesse_sorgenti`) | D-3, D-9 |
| `lotto varchar` → `lotto_id bigint` FK `lotti`; `seriale varchar` → `asset_id bigint` FK `assets` | **DROP** + **ADD**; CHECK `chk_mag_movimenti_asset_qta_unitaria`: `asset_id IS NULL OR abs(qta) = 1` | M-5 |
| `magazzino_id_dest` (+ FK, indice), `ubicazione_id_from`, `ubicazione_id_to` (+ FK, indici), `chk_mag_movimenti_da_destinazione_distinti`, `chk_mag_movimenti_ubi_from_to_diff` | **DROP** | M-5 (coppie) |
| `ubicazione_id bigint` FK `ubicazioni` | **ADD** (una sola posizione per riga). ⚠️ «l'ubicazione appartiene a `magazzino_id`» è cross-tabella: lo controlla la primitiva (Lotto 2), non un CHECK | M-5 |
| `attivo` | **DROP**. 🔴 **Riscritta in P-0**: il `DROP COLUMN` è bloccato da **cinque** trigger di `movimenti` che portano `attivo` nella lista `UPDATE OF` (provato in transazione annullata): i quattro `require_attivo` generati (`trg_movimenti_a10_{articoli,causali,magazzini,unita_misura}_require_attivo_ins_upd`, tutti `AFTER INSERT OR UPDATE OF attivo, <fk>`) e `trg_movimenti_a10_note_movimento_block_deact_upd` → `DROP TRIGGER IF EXISTS` **prima** del DROP; `ci_apply` rigenera i tre `require_attivo` superstiti senza `attivo` (la forma è quella di `costo_medio`: `UPDATE OF magazzino_id`), non il `block_deact` (una tabella senza `attivo` non ha niente da bloccare). ⚠️ In più `trg_note_movimento_a10_movimenti_require_attivo_ins_upd` **su `note_movimento`** legge `SELECT attivo FROM magazzino.movimenti` a ogni INSERT di una nota: senza `DROP TRIGGER IF EXISTS` ogni nota su un movimento morirebbe con `42703`; non si rigenera (il padre non ha più `attivo`). ✅ I `*_a10_movimenti_block_deact_upd` sui **padri** (`causali`, `magazzini`, `catalogo.articoli`) **non si toccano**: `trgfn_prevent_deactivate_if_children` cerca l'`attivo` della figlia a runtime con `fn_col_exists` e, se manca, conta tutte le righe — è già il comportamento giusto per un ledger (una causale con movimenti non si spegne). La prima stesura li dava da droppare «perché il framework li rigenera senza colonna di stato»: la definizione del trigger è identica prima e dopo, è la funzione che si adatta | M-8 |
| `storno_di_movimento_id bigint` FK `movimenti(id)` | **ADD** + `UNIQUE` semplice (i NULL non collidono; un movimento si storna una volta) | M-8 |
| `uom_id` (+ FK `fk_mag_movimenti_uom`, generato `trg_movimenti_a10_unita_misura_require_attivo_ins_upd` — è lo stesso della riga `attivo` — e, sul padre `catalogo.unita_misura`, `trg_unita_misura_a10_movimenti_block_deact_upd`, che porta `'uom_id'` come argomento e senza la colonna solleverebbe `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` a ogni disattivazione di una UoM) | **DROP**; `COMMENT` su `qta`: «in UoM base dell'articolo; la conversione la fa l'operazione» | D-L1-a |
| **identità** | `CREATE UNIQUE INDEX uq_mag_movimenti_identita ON magazzino.movimenti (sorgente_tipo_id, sorgente_riga, sorgente_uid, causale_id, asset_id, lotto_id, ubicazione_id) NULLS NOT DISTINCT` — **SQL esplicito**, non `addUniqueConstraint` (§5). `COMMENT`: la regola dell'operazione-per-tranche (D-4) e perché è **globale** (la terna contiene la sorgente: §6 c/s) | D-4, D-L1-c |
| `costo_unitario` | `COMMENT` con i **tre** significati (M-4: input in entrata da documento, output in uscita = media corrente, ereditato dall'uscita gemella nel trasferimento) | M-4 |
| `transfer_uid` + `ix_mag_mov_transfer_uid` | **restano**: raggruppano la coppia, non identificano (§6 c/s) | — |
| verso | guard di §4.9 | M-1 |
| `fk_index_policy` | **DELETE** `fk_mag_movimenti_magazzino_dest`, `_ubicazione_from`, `_ubicazione_to`, `_uom`; **ADD** `fk_mag_movimenti_sorgente_tipo` f, `_lotto` t, `_asset` t, `_ubicazione` t, `_storno_di` f (l'UNIQUE lo indicizza già) | — |
| `COMMENT ON TABLE` | l'identità, il verso nella quantità, la UoM base, la sorgente obbligatoria: le quattro regole che un lettore deve sapere prima di scrivere | — |

### 4.5 `reservations` → `movimenti_attesi` (§7-bis, M-1, M-6, D-1, D-L1-b)

**La rinomina è di TUTTO** (lezione di `20260822-25`, cantiere incassi — §5): tabella,
`pk_mag_reservations`, sequenza `reservations_id_seq`, i vincoli `NOT NULL`
nominati (PG17+: `reservations_<col>_not_null` — P-0 ne conta **tredici**, di
cui otto sopravvivono al secondo file: `id`, `articolo_id`, `qta`, `meta`,
`storicizza`, `data_insert`, `data_update`, `user_insert`; `attivo`, `doc_id`,
`doc_schema`, `doc_table`, `stato_reservation` cadono con le colonne), gli indici
`ix_magazzino_reservations_{articolo,magazzino,ubicazione}_id` (`ix_mag_res_stato`
cade con la colonna), le FK `fk_mag_reservations_*`, i trigger generati —
**due si rinominano** (`trg_reservations_audit_data_user_upd`,
`trg_reservations_gen_tx_id_ins_upd`: un changeSet condizionale ciascuno, §5),
**tre si tolgono** (i `require_attivo` verso `articoli`/`magazzini`/`ubicazioni`:
portano `attivo` in `UPDATE OF` e bloccherebbero comunque il `DROP COLUMN` del
secondo file; `ci_apply` li rigenera col nome nuovo) — `storico.reservations`
(`DROP TABLE IF EXISTS`, zero righe al 14-09: `ci_apply`/pgagent riprovvede
`storico.movimenti_attesi`; ⛔ il vecchio `trg_reservations_z90_storico_upd_dlt`
porta l'argomento `'reservations_id'` e **non si rinomina, si toglie**), e i
**tre** `block_deact` sui padri che portano `'reservations'` come argomento —
`trg_magazzini_a10_reservations_block_deact_upd`, `trg_ubicazioni_a10_reservations_block_deact_upd`
e `trg_articoli_a10_reservations_block_deact_upd` su **`catalogo.articoli`**
(`DROP IF EXISTS` tutti e tre: col nome vecchio cercherebbero in `pg_attribute`
una tabella sparita → `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND`; si rigenerano col nome
nuovo). La prima stesura ne nominava uno su tre. Infine la riga **77** di
`storico_scope_policy.csv` (§4.10-bis): `nome_tabella` → `movimenti_attesi`.

| Cosa | Come | Decisione |
| --- | --- | --- |
| `doc_*`, `uq_mag_reservations_docref` | **DROP** | D-1, §7-bis |
| `sorgente_tipo_id` **nullable** FK, `sorgente_riga`, `sorgente_uid` | **ADD**; CHECK: `sorgente_tipo_id IS NULL OR ((sorgente_riga IS NOT NULL) <> (sorgente_uid IS NOT NULL))`; guard tipizzato montato | D-6 (nullable: il blocco manuale non ha documento) |
| `causale_id bigint NOT NULL` FK `causali` | **ADD** — la direzione **non è una colonna nuova** (§7-bis) | M-1 |
| `chk_mag_res_qta_pos` | **DROP**; **ADD** `chk_mag_movimenti_attesi_qta_non_zero` | M-1 |
| `stato_reservation` + `chk_mag_res_stato` + `ix_mag_res_stato` | **DROP**; **ADD** `stato varchar NOT NULL DEFAULT 'APERTA'` CHECK `IN ('APERTA','CHIUSA')`, `data_chiusura timestamptz`, CHECK `(stato = 'CHIUSA') = (data_chiusura IS NOT NULL)`; indice su `stato` | D-L1-b |
| `attivo` | **DROP** | D-L1-b |
| `magazzino_id` | **SET NOT NULL** | M-6 |
| `soggetto_ruolo_id bigint` FK `anagrafiche.soggetti_ruoli`; `nota text` | **ADD**; CHECK `chk_mag_movimenti_attesi_per_chi`: `sorgente_tipo_id IS NOT NULL OR soggetto_ruolo_id IS NOT NULL OR coalesce(btrim(nota), '') <> ''` — *un'attesa dice per chi è: dal documento, dal soggetto, o dalla nota*. ⭐ Il `coalesce` non è ornamentale (§7-bis, provato il 04-09) | §7-bis |
| `data_prevista` | resta; CHECK `chk_mag_movimenti_attesi_data_solo_senza_documento`: `sorgente_tipo_id IS NULL OR data_prevista IS NULL` — dove c'è un documento la data è la sua (§7-bis, punto 4) | §7-bis |
| ✅ **come scritto** (`20260915-06` + `-07`, 15-09) | tre scelte di forma, registrate nell'intestazione: (1) il CHECK della chiave è **più stretto** della riga sopra — senza documento **niente** chiave, con documento esattamente una — perché una `sorgente_riga` senza tipo è un numero appeso al nulla e sarebbe passata; (2) `chk_mag_movimenti_attesi_asset_qta_unitaria` anche qui, per simmetria col ledger (un pezzo serializzato atteso è un pezzo); (3) l'«indice su `stato`» è un **indice parziale** `(articolo_id, magazzino_id) WHERE stato = 'APERTA'` — un btree su due valori non seleziona, la domanda della disponibilità sì. ⚠️ Rinominati solo audit e `tx_id` (trigger semplici); i tre `require_attivo` sono **constraint trigger** e si rigenerano (vedi P-6) | — |
| `lotto_id`, `asset_id` | **ADD** nullable FK, come sul ledger: l'atteso eredita gli obblighi dell'articolo | M-5 |
| verso | guard di §4.9, stesso trigger function | M-1 |
| `fk_index_policy` | **DELETE** le tre `fk_mag_reservations_*`; **ADD** `fk_mag_movimenti_attesi_articolo` t, `_magazzino` t, `_ubicazione` t, `_causale` f, `_soggetto_ruolo` f, `_sorgente_tipo` f, `_lotto` f, `_asset` f | — |
| doc | `manual/reservations.md` **si cancella**, nasce `manual/movimenti_attesi.md` (regola di `AGENTS.md` §Documentazione: il `manual/` di un oggetto ritirato si cancella, l'indice è generato) | — |

### 4.6 `costo_medio` → `valore_giacenza` (M-4)

Rinomina di tutto: `pk_mag_costo_medio`, `uq_mag_costo_medio_art_mag`,
`ix_magazzino_costo_medio_magazzino_id`, `fk_mag_costo_medio_magazzino`,
sequenza `costo_medio_id_seq`, i `NOT NULL` nominati (P-0: **dieci**, nove
sopravvivono — `qta` cade), i generati condizionali — sono **due**, non tre:
`trg_costo_medio_audit_data_user_upd` e `trg_costo_medio_a10_magazzini_require_attivo_ins_upd`;
la tabella **non ha `tx_id` né `storicizza`** (colonne: `id, articolo_id,
magazzino_id, qta, valore, meta, audit`), quindi niente `tx_id`, niente
storico, e **nessuna riga** in `storico_scope_policy` —
`trg_magazzini_a10_costo_medio_block_deact_upd` su `magazzini` (`DROP IF EXISTS`,
argomento `'costo_medio'`).

| Cosa | Come |
| --- | --- |
| ⚠️ **trovato scrivendo (15-09)** | il `require_attivo` verso `magazzini` è un **CONSTRAINT TRIGGER**: provato, né `ALTER TRIGGER … RENAME` né `ALTER TABLE … RENAME CONSTRAINT` rinominano **entrambe** le voci (`pg_trigger`, `pg_constraint`) — ne resterebbe una col nome vecchio, e il pgTAP «nessun oggetto nomina più `costo_medio`» sarebbe rosso. ⇒ **non si rinomina: `DROP TRIGGER IF EXISTS`** (porta via entrambe) e `ci_apply` lo rigenera col nome nuovo. Vale per ogni `require_attivo` del lotto; audit e `tx_id` sono trigger semplici e si rinominano. La riga sopra («i generati (audit, `tx_id`) condizionali») è corretta per caso: `costo_medio` non ha `tx_id` |
| `qta` | **DROP** — la quantità vive **solo** nel registro. 🔴 **P-0: il `DROP COLUMN` è bloccato dalle tre viste** (`vw_costo_medio` e `vw_costo_medio_globale` leggono `qta`; `vw_giacenza_valorizzata` dipende da `vw_costo_medio`), e su un DB da zero esistono già quando gira `00_schema` (le crea `20251003-11/12/13` in `20_code`, con numero più basso). ⇒ P-6 fa **`DROP VIEW IF EXISTS`** delle tre, in quest'ordine (`vw_giacenza_valorizzata`, `vw_costo_medio_globale`, `vw_costo_medio`) **prima** del DROP della colonna; P-11 le ricrea. `vw_giacenza` non dipende da niente che cambia (il DROP di `movimenti.attivo` non la nomina) |
| `fk_mag_valore_giacenza_articolo` | **ADD** (oggi manca: può puntare a un articolo che non esiste) + riga `fk_index_policy` **f** (l'UNIQUE `(articolo, magazzino)` copre già l'accesso per articolo — scritto nella nota della riga) |
| `COMMENT ON TABLE` | «copia ricostruibile dal registro; il ricalcolo è una **ri-somma** dei `costo_unitario` scritti, non una ri-esecuzione» (M-4, precisazione del 04-09) |
| partizione `note_costo_medio` | **DROP** + `COSTO_MEDIO` fuori da `chk_note_target_tipo` del padre `magazzino.note` (D-L1-e). P-0: il `DROP TABLE` passa pulito (un solo trigger, l'audit, che cade con lei); riga **247** di `fk_index_policy.csv` (`fk_note_costo_medio_testata`) → `DELETE` |
| doc | `manual/costo_medio.md` **si cancella**, nasce `manual/valore_giacenza.md` |

### 4.7 `magazzini`, `assets`, le testate e le righe (M-6, M-5, D-2, D-3)

**`magazzini`**: `emittente_fiscale_id bigint` FK `anagrafiche.emittenti_fiscali`,
in **due passi nello stesso changeSet** — `ADD` nullable, poi `SET NOT NULL`
preceduto da `sqlCheck expectedResult: 0` sulle righe senza emittente (su CI la
tabella è vuota; su dev, se qualcuno ha creato magazzini a mano, il migrate si
ferma **dicendo perché** e il dato si sistema a mano — non con una migration:
`AGENTS.md` §Workflow Safety, «bug di dati in sviluppo»). Guard di scrittura
`script.trgfn_guard_emittente_scope('fiscale', 'emittente_fiscale_id')`
(stampo: `vendite.ordini`). `fk_index_policy` **f** (tabella minuscola).

**`assets`**: `emittente_fiscale_id` nello stesso modo (§7-sexies, correzione
del 04-09: **non** `magazzino_id NOT NULL`); **DROP** `ubicazione` (varchar),
`magazzino_id`, `ubicazione_id` (+ FK, indici, generati
`trg_assets_a10_magazzini_require_attivo_ins_upd` e
`trg_assets_a10_ubicazioni_require_attivo_ins_upd` — P-0: sono loro a bloccare
il `DROP COLUMN`, `UPDATE OF attivo, magazzino_id` / `attivo, ubicazione_id` —
e sui **due** padri `trg_magazzini_a10_assets_block_deact_upd` **e**
`trg_ubicazioni_a10_assets_block_deact_upd`, entrambi con la colonna sparita
come argomento; la prima stesura ne nominava uno) — *l'asset non è il suo
GPS* (§7-quater); `billing_account_id` e `contratto_id` **restano nullable**
(non sono l'ancora); `ownership_id` resta (è la **proprietà** — `config.assets_ownership`
esiste già con `ASSET_OWNED`/`ASSET_CONSIGNMENT`/`ASSET_CUSTOMER` — ed è la
dimensione che §7-ter prevede per la merce di terzi: nasce qui, non nella
valorizzazione). `fk_index_policy`: **DELETE** `fk_mag_assets_magazzino`,
`_ubicazione`; **ADD** `_emittente_fiscale` f. ⚠️ **`dbops.rls_perimetro_debito`
riga 65** (`magazzino.assets`, «quale delle due chiavi porta il perimetro»): la
risposta è la terza chiave, e **una riga di registro estinta fa rosso** quanto
una non dichiarata ⇒ via dal CSV **e** `DELETE` in un changeSet (`loadUpdateData`
non cancella) — forma di `brief-db-perimetro-emittente-righe-documento` §11.7.

**Le quattro testate** (`inventari`, `rettifiche`, `trasferimenti`, `eventi_assets`):
`sorgente_riga bigint` **ADD** su tutte; CHECK «tipo valorizzato ⇒ esattamente
una chiave» su tutte; guard tipizzato `trg_<t>_a10_guard_sorgente_ins_upd` su
tutte. 🔴 **Trovato scrivendo P-2**: `eventi_assets` porta **anche**
`doc_schema`, `doc_table`, `doc_id`, `doc_riga_id` — il riferimento libero che
D-1 ritira su ledger e attesi, e che qui la prima stesura non aveva visto.
**DROP** in P-8 (P-0: nessun trigger li nomina, cadono puliti). In più: `rettifiche` prende la **FK mancante** `fk_mag_rettifiche_sorgente_tipo`
(+ riga policy f); `trasferimenti` perde il **doppione** `sorgenti_tipo_id`/`sorgenti_uid`
con le sue due FK (`fk_mag_rettifiche_sorgenti_tipo` — sì, si chiama così —,
`fk_mag_trasferimenti_sorgenti_tipo`), le due righe di policy (264 e 265 del
CSV), il generato `trg_trasferimenti_a10_sorgenti_require_attivo_ins_upd`
(`DROP IF EXISTS` — P-0: è lui a bloccare il `DROP COLUMN`, `UPDATE OF
sorgenti_tipo_id`) e, sul padre `config.sorgenti`,
`trg_sorgenti_a10_trasferimenti_block_deact_upd`, che porta `'sorgenti_tipo_id'`
come argomento (`DROP IF EXISTS`; `ci_apply` lo rigenera su `sorgente_tipo_id`,
come già fa per `inventari` ed `eventi_assets`). ⚠️ `rettifiche` oggi **non ha**
il `require_attivo` verso `sorgenti` né il `block_deact` sul padre: nascono con
la FK, a `ci_apply`.
⚠️ `trasferimenti` ha **due** magazzini (`_from`, `_to`): il perimetro di §4.10
poggia su `_from`, e un guard piccolo `magazzino.trgfn_trasferimenti_guard_stesso_emittente`
(codice `E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI`, `DATO_ERRATO`, `campo =
magazzino_id_to`) impedisce che i due appartengano a emittenti diversi —
*nessuna operazione di magazzino attraversa due emittenti* (§7-sexies).

🔴 **Trovato scrivendo P-8, e corretto lì**: i due CHECK «da/a distinti» di
`trasferimenti` e `eventi_assets` **non verificavano niente** — `(from <> to)
OR (from IS NOT NULL) OR (to IS NOT NULL)` è sempre vero con colonne NOT
NULL, e vale NULL (passa) con entrambe NULL. Riscritti: `from <> to` sui
trasferimenti, `from IS NULL OR to IS NULL OR from <> to` sugli eventi. Un
trasferimento da un magazzino a se stesso ora è rifiutato (provato).

✅ **Deciso da Tid il 15-09 (sera)** — era: *«`magazzini` e `assets` non hanno
un trigger di default dell'emittente; tre strade: il BE lo passa, una sesta
copia, o un BB generico `script.trgfn_default_emittente_fiscale`; da decidere
quando il pannello servirà»*. **Decisione: il BB generico, E il ritiro delle
copie di vendite nello stesso giro** — *«che aspettiamo, la produzione, per
fare questi refactor?»*. Non «la BB ora e le copie dopo»: un refactor rimandato
è un debito che nessuno rilegge. 🔵 **È un brief suo, scritto il 15-09 sera:
[brief-db-emittente-di-default-un-bb-solo](brief-db-emittente-di-default-un-bb-solo.md)**
(tocca `vendite`, in esercizio), da applicare **prima del Lotto 2**, che lo
presuppone (il primo magazzino vero nasce lì). Censimento fatto il 15-09 per
non partire da un numero sbagliato — le cinque di vendite **non sono cinque
copie**:

| Funzione | Che cosa fa | Sorte |
| --- | --- | --- |
| `trgfn_ordini_default_emittente`, `_preventivi_`, `_contratti_` | dalla GUC di sessione via `fn_resolve_emittente_for_user`; **solleva** `E_ORDINE\|E_PREV\|E_CONTRATTO_EMITTENTE_NON_RISOLTO` (`DATO_ERRATO`) se GUC vuota o admin globale | **tre copie vere** → il BB in modo «solleva» |
| `trgfn_ddt_default_emittente` | stessa GUC, ma **non solleva**: lascia NULL a `trgfn_ddt_normalize`, che eredita dalla sorgente/BA | **variante morbida** → il BB in modo «lascia NULL» (`TG_ARGV`) |
| `trgfn_commesse_default_emittente` | dal **billing account** (`fn_get_emittente_fiscale_id`), colonna `emittente_soggetto_ruolo_id` | **non è una copia**: resta |

Tabelle ancorate su `emittente_fiscale_id NOT NULL` **senza** alcun default
(doc auto-gen, 15-09): `magazzino.magazzini`, `magazzino.assets`,
`vendite.resi`, `vendite.offerte_commerciali`, `pratiche.pratiche`,
`documenti.documenti_generati`/`template_documenti`/`template_asset`,
`anagrafiche.soggetti_titoli_iva` (le due `config.user_emittent*` sono la
mappa stessa: nessun default ha senso). ⇒ Il perimetro del BB è **più largo
di magazzino**, ed è la ragione per cui dev'essere generico: per ciascuna il
brief dice da dove si deriva (sessione o padre) o perché no. Lettori da
censire nel ritiro dei tre codici (`obsoleto_dal`, mai `DELETE`):
`error_ui_overrides.py` (`E_PREV_…` → `highlight_form_fields`), i cinque
ripieghi in `error_messages_fallback.py`, `error_policies_generated.py`,
dieci pgTAP che nominano codici o trigger (fra cui
`vendite/test-trgfn-preventivi-default-emittente-e-guard-coerenza`), i
`manual/` delle cinque funzioni. ⚠️ Il CRUD generico del pannello è
metadata-driven (`config_metadata_repository`: tutte le colonne non-audit
sono editabili): oggi mostrerebbe `emittente_fiscale_id` **e**
`indirizzo_dettaglio_id` come interi da digitare — il default risolve il
primo; il secondo è la ragione per cui un magazzino, prima o poi, vuole un
drawer suo (FE, non urgente).

**Le tre righe** (`inventari_righe`, `rettifiche_righe`, `trasferimenti_righe`):
`lotto varchar` → `lotto_id` FK `lotti`; `seriale varchar` → `asset_id` FK
`assets` (M-5 propagata: senza, l'operazione non ha niente da passare alla
primitiva — aggancio §8-quater); CHECK con seriale: `inventari_righe.qta_contata IN (0, 1)`,
`abs(rettifiche_righe.qta_delta) = 1`, `trasferimenti_righe.qta = 1`. Righe di
policy per le sei FK nuove: `_lotto` t, `_asset` t (la tracciabilità chiede
«dove è passato questo lotto»).

**File morti da togliere** con questo lotto: i CSV a sola intestazione **senza
loader** `80_data/sql/magazzino/{reservations,costo_medio,note_costo_medio}.csv`
(un nome vecchio in un file che nessuno carica è un CSV stantio in potenza: la
prossima modifica lo sveglierebbe contro una tabella che non c'è). P-0 ne conta
tre, non due.

### 4.8 Le viste (M-1, M-4, M-5, M-6)

| Vista | Che cosa cambia |
| --- | --- |
| `vw_giacenza` | **corpo invariato** (`sum(qta) GROUP BY articolo, magazzino`); **`COMMENT`** che dice *perché* è corretta senza join alle causali — e che aggiungerlo raddoppierebbe il segno (M-1); `security_invoker = true` **ri-specificata** (si azzera a ogni `CREATE OR REPLACE`: P-6 del brief modifiche certe l'ha pagato) |
| `vw_giacenza_ubicazione` — **nuova** | `sum(qta) GROUP BY articolo, magazzino, ubicazione`; senza, la coppia OUT/IN fra ubicazioni non significa niente (§7-quater, 5) |
| `vw_costo_medio` | rifatta: quantità da `vw_giacenza`, valore da `valore_giacenza`, `costo_medio = valore / qta` (NULL a quantità zero) |
| `vw_costo_medio_globale` | rifatta sullo stesso join, `GROUP BY articolo`; `COMMENT`: *«globale» = tutti i magazzini dell'emittente attivo di sessione* (§7-sexies, 6) |
| `vw_giacenza_valorizzata` | rifatta come join `vw_giacenza` × `valore_giacenza` (qta, valore, costo_medio): smette di essere tautologica perché la quantità non è più nell'accumulatore (rilievo del 04-09) |

Tutte con `security_invoker = true`: leggono coi diritti di chi interroga
(§7-sexies, 5).

### 4.9 Il guard del verso (M-1)

`magazzino.trgfn_movimenti_guard_verso()` — una funzione sola, montata come
`trg_movimenti_a10_guard_verso_ins_upd` (`BEFORE INSERT OR UPDATE OF qta,
causale_id`) e `trg_movimenti_attesi_a10_guard_verso_ins_upd`: legge
`causali.segno` e rifiuta se `sign(NEW.qta) <> segno`. È **la rete** (§4
c/s): la primitiva darà il messaggio comprensibile; qui il lettore è
`dbops.error_log`.

Codice: **`E_MAG_MOVIMENTO_VERSO_INCOERENTE`**, classe **`TECNICO`** — il verso
non lo digita mai una persona: lo compone l'operazione dalla causale, quindi
un mismatch è un chiamante rotto (`AGENTS.md` §«Sollevare un errore»: riuso o conio si decide su chi può rimediare, non sulla condizione). Messaggio con i
valori nel `VARIADIC` (causale, segno, quantità), **senza** nomi di parametro.
Registrato in `codici_errore.csv` + `messaggi_errore.csv` (`it`) + riga di
ripiego lato BE quando il BE arriverà (non ora).

⚠️ Un `BEFORE ROW` **oscura** il CHECK `qta <> 0` (un `BEFORE ROW` scatta
prima che i vincoli di tabella siano valutati): sull'`INSERT` con `qta = 0` parla il guard (`sign(0) = 0 ≠
segno` → `P0001`), non il CHECK (`23514`). Il pgTAP di §7 asserisce il guard con
`throws_like` sulla frase **e** l'esistenza del CHECK su `pg_constraint`.

### 4.10 Il perimetro RLS (M-6) — atterra con l'ancora

**Una variante nuova della famiglia**: `script.fn_scope_ef_whitelist_via_magazzino(p_auth_user_id, p_magazzino_id)`
— stampo `via_ddt`: `STABLE`, **non** `SECURITY DEFINER`, magazzino inesistente
→ emittente NULL → `false` (fail-closed). E le derivate a un salto: `via_asset`
(legge `assets.emittente_fiscale_id`), `via_movimento`, `via_inventario`,
`via_rettifica`, `via_trasferimento` (→ `magazzino_id_from`), `via_evento_asset`
(→ `via_asset`). Più lo smistatore delle note `script.fn_scope_note_magazzino_ef_whitelist(p_auth_user_id, p_target_tipo, p_target_id)`
sul modello di `fn_scope_note_ef_whitelist` (`ELSE false`: un `target_tipo`
nuovo rende le note invisibili, non pubbliche — presidiato dal pgTAP che
confronta i rami col CHECK del padre).

**Le policy**, tutte `rls_<tabella>_ef_whitelist`, `PERMISSIVE FOR ALL`,
`USING` = `WITH CHECK` = *«`app.ruolo_applicativo = 'OPERATORE'` AND scope»*,
poi `ENABLE ROW LEVEL SECURITY` — **senza `FORCE`** (nessuna tabella del
progetto lo usa e l'app non è owner: `COMMENT` di `vw_rls_perimetro_scoperto`):

| Tabella | Scope |
| --- | --- |
| `magazzini` | diretto su `emittente_fiscale_id` |
| `assets` | diretto |
| `ubicazioni`, `movimenti`, `movimenti_attesi`, `valore_giacenza`, `inventari`, `rettifiche` | `via_magazzino(magazzino_id)` |
| `trasferimenti` | `via_magazzino(magazzino_id_from)` + guard stesso emittente (§4.7) |
| `eventi_assets` | `via_asset(asset_id)` |
| `inventari_righe`, `rettifiche_righe`, `trasferimenti_righe` | via la testata |
| `note` (padre) | smistatore `fn_scope_note_magazzino_ef_whitelist` |
| le nove partizioni `note_asset`, `note_evento_asset`, `note_inventario`, `note_inventario_riga`, `note_movimento`, `note_rettifica`, `note_rettifica_riga`, `note_trasferimento`, `note_trasferimento_riga` | ciascuna via il proprio bersaglio (le policy delle partizioni **non risalgono** al padre — provato il 09-09 in vendite) |

⛔ **Fuori**: `causali`, `lotti`, `tipi_ubicazione`, `config.assets_ownership`
— vocabolari e definizioni, uguali per tutti (§7-sexies, 1). Nessuna di loro
ha una FK verso una tabella protetta, quindi il presidio non le chiede.

**Il registro del debito**: riga 65 via (§4.7). Dopo il lotto,
`dbops.vw_rls_perimetro_scoperto` per `magazzino` deve dare **zero righe** —
è l'asserzione 2 di `test-rls-perimetro-scoperto.sql`, che gira già. P-0: oggi
per `magazzino` la vista dà **una** riga, `assets`, `DEBITO_DICHIARATO`.

### 4.10-bis — Lo storico sotto la RLS: la mappa `dbops.storico_scope_policy` (🔴 trovato in P-0)

Il brief non lo nominava. `80_data/sql/dbops/storico_scope_policy.csv` porta
**tredici** righe `magazzino` (id 69-81: le tredici tabelle col trigger
`z90_storico`), tutte `modo = NESSUNO` con la ragione *«La madre non ha la row
level security accesa (letto il 2026-09-11) […] Quando entrerà in RLS il
presidio segnalerà questa riga e il modo andrà dichiarato»*. Il presidio è
`dbops.vw_storico_scope_da_dichiarare` (motivo `PROTETTA_NESSUNO`, pgTAP
`dbops/test-storico-scope-policy-v1` test 4, digest settimanale) — e P-10
accende la RLS su dieci di quelle tredici madri. **Il giorno dell'apply il
test farebbe rosso**, per costruzione.

⭐ La mappa è un dato: si edita il CSV (mirror `20260911-23`, `runOnChange` +
`ANY`), l'armatura delle shadow la fa `fn_storico_arma_scope_tutte` da sola
in `90_end/20260911-29` (runAlways) e in `ci_apply`. Le righe:

| id | tabella | `modo` | `colonna` | `padre` | Perché |
| --- | --- | --- | --- | --- | --- |
| 75 | `magazzini` | `EF` | `emittente_fiscale_id` | — | l'ancora (P-7) |
| 70 | `assets` | `EF` | `emittente_fiscale_id` | — | l'ancora (P-7) |
| 76 | `movimenti` | `PADRE` | `magazzino_id` | `magazzino.magazzini` | via il magazzino |
| 77 | `reservations` → **`movimenti_attesi`** | `PADRE` | `magazzino_id` | `magazzino.magazzini` | rinomina + via il magazzino (NOT NULL da P-5) |
| 73 | `inventari` | `PADRE` | `magazzino_id` | `magazzino.magazzini` | |
| 74 | `inventari_righe` | `PADRE` | `inventario_id` | `magazzino.inventari` | due salti |
| 78 | `rettifiche` | `PADRE` | `magazzino_id` | `magazzino.magazzini` | |
| 79 | `rettifiche_righe` | `PADRE` | `rettifica_id` | `magazzino.rettifiche` | |
| 80 | `trasferimenti` | `PADRE` | `magazzino_id_from` | `magazzino.magazzini` | lo stesso asse della policy |
| 81 | `trasferimenti_righe` | `PADRE` | `trasferimento_id` | `magazzino.trasferimenti` | |
| 72 | `eventi_assets` | `PADRE` | `asset_id` | `magazzino.assets` | |
| 71 | `causali` | `NESSUNO` | — | — | **invariata**: vocabolario, fuori dal perimetro — la ragione già scritta resta vera |
| 69 | `ambito_causale` | — | — | — | **`DELETE`** in P-3, con la tabella (altrimenti `RIGA_SENZA_MADRE`) |
| **nuova** | `lotti` | `NESSUNO` | — | — | nasce con `storicizza` ⇒ `ci_apply` le dà il trigger di storico ⇒ senza riga è `SENZA_RIGA`. Ragione: definizione senza `magazzino_id`, fuori dal perimetro (§4.3) |

⚠️ `ubicazioni`, `note` e le partizioni **non hanno** `storicizza` né trigger di
storico: nessuna riga. `valore_giacenza` nemmeno (§4.6). ⚠️ Il pgTAP della mappa
(test 7) verifica che la `colonna` sia **una FK monocolonna** verso il padre
dichiarato e (test 9) che ogni catena `PADRE` finisca in un `EF`/`SR`/`BA`: le
FK ci sono già, l'`EF` di `magazzini` nasce in P-7 — il CSV è `80_data`, viene
dopo, va bene. Una FK a NULL dà scope NULL (test 22), cioè versione invisibile:
fail-closed, ed è il verso giusto. ⚠️ `PADRE` a due salti (`inventari_righe` →
`inventari` → `magazzini`) è la forma di `fatture_righe`: ammessa e provata
(test 21).

---

## 5. Le trappole note, e dove morde ciascuna

> Tutte già pagate una volta dal progetto. Sono qui perché il changeSet si
> scrive guardando il database che si ha davanti, e su dev **tutto esiste da
> mesi**.

| Trappola | Dove morde in questo lotto | Forma giusta |
| --- | --- | --- |
| **DDL incondizionata su un trigger generato** (`linee-guida-sql.md` §11.5, `guardrail_ddl_su_trigger_automazione.py`) | ogni rinomina/drop di `trg_reservations_*`, `trg_costo_medio_*`, e ogni `DROP` dei `require_attivo`/`block_deact` che le colonne tolte lasciano orfani | **rinomina**: un changeSet per trigger, `onFail: MARK_RAN` + `sqlCheck` su `pg_trigger` (stampo `20260822-25-01/-02`); **drop**: `DROP TRIGGER IF EXISTS`, senza preCondition (`MARK_RAN` segna senza eseguire: su un DDL già idempotente un guardiano aggiunge solo un modo di fallire in silenzio — `20260818-66`). ⛔ Mai una preCondition sul changeSet della rinomina della tabella |
| **La rinomina non basta** | `movimenti_attesi`, `valore_giacenza` | PK, sequenza, `NOT NULL` nominati, indici, FK, **e il pgTAP** «nessun oggetto della tabella nomina più il nome vecchio» (lezione di `20260822-25`) |
| **`DROP COLUMN` fallisce per la lista `UPDATE OF` di un trigger**, non per i corpi | le colonne tolte da `movimenti` e `assets` | censire `pg_trigger` per colonna **prima** (query in §6, P-0); riscrivere/rimuovere il trigger con numero **inferiore** al DROP |
| **La CI esegue per fase, non per data** | il `DROP TABLE ambito_causale` contro il suo loader `80_data` con `HALT` | il loader **si cancella** (§4.1); verificare con `grep -rln ambito_causale 80_data 90_end` che non resti altro che lo pretenda |
| **Un unique parziale/speciale in YAML evapora** | `uq_mag_movimenti_identita NULLS NOT DISTINCT` | SQL esplicito; verifica **sull'oggetto vivo** (doc auto-gen, sezione Vincoli) |
| **`ADD COLUMN NOT NULL` su tabella con righe** | `emittente_fiscale_id` su `magazzini`/`assets` | due passi con `sqlCheck expectedResult: 0` (§4.7) |
| **FK nuova = guard generato che oscura** (precedente del 2026-08-19 su `emittenti_fiscali_billing_account`) | le FK nuove verso tabelle con `attivo` (`lotti`, `assets`, `causali` da attesi, `soggetti_ruoli`) | nessun guard a mano sulle stesse coppie; i `require_attivo` li scrive il framework a `ci_apply` e si **asseriscono in pgTAP**, non in preCondition |
| **`fk_index_policy.dll_command` sempre valorizzato** anche a `f` | ogni riga nuova | scrivere il `CREATE INDEX IF NOT EXISTS ix_<t>_<col> …` anche per i no |
| **Un loader `runOnChange` + `ANY` si modifica in place, uno senza no** | `causali` (`20251001-51`), `sorgenti` (`20251002-21`), il registro del debito RLS (`20260909-77`) e `storico_scope_policy` (`20260911-23`) sono `ANY` → in place. ⛔ **`fk_index_policy.csv` no**: il suo mirror è di gennaio e «svegliarlo rilegge 200 righe» (`20260913-12`, linee-guida-sql §11.2) — le righe nuove del lotto vanno in **un CSV dedicato** con loader suo (`fk_index_policy_magazzino_lotto1.csv`), le dodici da ritirare si tolgono con un `DELETE` SQL forward-only; il CSV base resta com'è, con dentro nomi che non esistono più: `apply_fk_index_policy` salta le righe `t` senza FK viva e fa `DROP INDEX IF EXISTS` a vuoto sulle `f` — innocuo, e nessun presidio lo conta | prima di toccare un loader: `grep validCheckSums` |
| **Prova = SQL ESTRATTO in `BEGIN … ROLLBACK`** (`AGENTS.md`: si prova ciò che Liquibase eseguirà, non una riscrittura) | tutto il lotto, e in particolare le due rinomine | `liquibase updateSQL` gira offline; si esegue **quello**, non una riscrittura; ⛔ un upsert CSV completo nella prova impicca il `dblink` — si prova con le sole righe nuove |
| **La suite pgTAP ha rossi noti** | `test-movimenti-vincoli-v1` **diventa rosso per costruzione** (asserisce i CHECK che questo lotto toglie e scrive `doc_*`) | si **riscrive** come `-v2` nello stesso lotto (§7); non entra in baseline |
| **Il numero libero scade nel minuto** | i file `20260914-NN` / `2026MMDD-NN` | si ricontrolla prima di salvare; oggi l'ultimo è `-14` (14-09) |
| **`MARK_RAN` autolesionista nel file che CREA un oggetto** → l'oggetto esiste solo su dev (🔴 trovato il 15-09 su `zeroerp_ci`) | `uq_mag_movimenti_docref` (P-4) e `uq_mag_reservations_docref` (P-5). In `20251005-11` i changeSet `-12/-13/-14` portano tutti `not columnExists doc_schema` + `MARK_RAN`, ma è `-12` a **creare** `doc_schema`: `-13` (NOT NULL) e `-14` (UNIQUE docref) su un DB da zero sono **sempre** `MARK_RAN`; identico `20251005-15` (`-17/-18`). Su dev esistono perché quel file girò una prima volta sotto `00_schema/vendite/` (`EXECUTED`) e fu poi ri-registrato `MARK_RAN` da `magazzino/`: nel repo c'è solo la seconda forma. Il file è mergiato e il debito (doc_* nullable e non unique su un DB nuovo) evapora col `DROP COLUMN` | `DROP CONSTRAINT IF EXISTS` **solo** su ciò che un `MARK_RAN` a monte può non aver creato; le altre `DROP` restano secche. ⭐ Prima di droppare o rinominare per nome un oggetto nato da un changeSet con preCondition, `exectype` si legge nel `databasechangelog` di **un DB da zero** (`zeroerp_ci`), non di dev: dice se è mai nato. ⚠️ `updateSQL` rende anche i changeSet che a runtime saranno `MARK_RAN` (`-06-01`, `-06-02`, `-08-01`: non sa valutare un `sqlCheck` su una tabella che al render non c'è): nella prova con l'SQL estratto si **tolgono**, non si contano come rossi |
| **Montare una funzione registrata come ORFANA = censire il registro che la dichiarava** (🔴 trovato il 15-09 col runner) | `script.trgfn_guard_sorgente_polimorfa_tipizzata` era l'**unica** voce di `dbops.riferimenti_morti_esenzioni` («senza alcun trigger», D6 aperta); il `-05` dice «primo montaggio di quella funzione» e non ha guardato chi la dichiarava orfana → `vw_riferimenti_morti_rientrati` a 1, test 4 rosso | è la forma «cancellare una fonte = censire i lettori» applicata a un **fatto**: prima di montare/smontare una funzione, `grep` del suo nome nei CSV e nei seed di `80_data/sql/dbops` (registri del debito). Il rimedio è il `DELETE` in avanti (`20260915-18`), mai allargare il registro |
| **Una fixture che CERCA un dato di macchina muore sul DB da zero** (🔴 `ci-local.sh --fresh`, 15-09) | `SELECT … FROM anagrafiche.indirizzi_dettaglio WHERE attivo LIMIT 1` in quattro file: su dev centinaia di righe, su `zeroerp_ci` zero → `ERRORE_FIXTURE`, zero asserzioni eseguite | si **fabbrica**: `dbops.fn_pgtap_crea_indirizzo_dettaglio(etichetta)` (`20260915-19`), come già `fn_pgtap_crea_emittente_operatore`. ⭐ Il discriminante è lo stesso del seed: **catalogo** (stradario, articoli `ONERE_*`, vocabolari `config.*`) si può cercare per nome, **macchina** (indirizzi, soggetti, emittenti) si costruisce |
| **Un indice del 2025 sopravvive alla rinomina sul DB da zero** (🔴 `zeroerp_ci`, 15-09) | `movimenti_attesi` portava ancora `ix_mag_res_articolo/_magazzino` e `ix_mag_reservations_ubicazione`: `apply_fk_index_policy` crea il suo indice **solo su una FK scoperta** (guardia 1), quindi dove il vecchio c'è la policy salta e il nome vecchio resta; su dev era stato tolto a mano e il `-06` rinominava (`IF EXISTS`) solo i nomi di policy | `DROP INDEX IF EXISTS` dei nomi vecchi (`20260915-20`), non una `RENAME` (collide dove il nome nuovo c'è già): la policy li rigenera nella stessa passata. ⭐ Prima di rinominare una tabella, gli indici si leggono su **`zeroerp_ci`**, non su dev — e il pgTAP «nessun oggetto nomina il nome vecchio» cerca anche l'**abbreviazione** (`mag_res_`) |
| **Cambiare una riga di CATALOGO = censire i pgTAP che la pinnano** (🔴 dev, 15-09) | D-L1-f riattiva le cinque `*_RIGA` di `config.sorgenti` e toglie `meta.archived`; `config/test-sorgenti-scope-pulizia-v1` (test 6 e 9) pinnava lo stato opposto — che era un `UPDATE` a mano su dbdev, e in CI il file era `ASSERZIONE` in baseline dal primo giorno | prima di toccare un CSV di `80_data`: `grep -rl <codice_interno\|scope> db/pgtap/`. Il test si riscrive sul contratto nuovo (per **nome**, non per conteggio: sei sorgenti di riga attive, nessuna marchiata) e in CI **rientra** dalla baseline — non si allarga la baseline |

---

## 6. I passi

> Fase: `00_schema` → `20_code` → `80_data` → `90_end`. In CI tutta una fase
> prima della successiva, **qualunque sia la data**. ⛔ Negli YAML si cita il
> **nome** di questo brief (`brief-db-magazzino-lotto-1-terreno-vuoto`), mai
> il path `work-in-progress/`.

| # | Passo | Fase |
| --- | --- | --- |
| **P-0** ✅ 14-09 | **Censimenti**, prima di scrivere una riga: (a) i trigger per colonna sulle tabelle toccate — `SELECT c.relname, t.tgname, pg_get_triggerdef(t.oid) FROM pg_trigger t JOIN pg_class c ON c.oid = t.tgrelid WHERE c.relnamespace = 'magazzino'::regnamespace AND NOT t.tgisinternal ORDER BY 1, 2`, più i `*_movimenti_block_deact_upd`/`*_reservations_*`/`*_costo_medio_*` sui padri **fuori** schema (`catalogo.articoli`, `catalogo.unita_misura`); (b) i lettori dei nomi che cambiano — `grep -rn "costo_medio\|reservations\|doc_schema\|magazzino_id_dest\|ubicazione_id_from\|impatto_valorizzazione\|ambito_causale" db/changelog/migrations_v2/20_code backend/apps frontend/src db/pgtap` — attesi: le tre viste, `test-movimenti-vincoli-v1`, e niente altro; (c) i changeSet di `80_data`/`90_end` che nominano `ambito_causale`, `reservations`, `costo_medio`; (d) le righe vive `config.sorgenti` 3/5/7/9/11 e i vincoli `NOT NULL` nominati di `reservations`/`costo_medio` in `pg_constraint`. ⭐ Il risultato è **nel riquadro §6-bis**, con la data | — |
| **P-1** ✅ 14-09 | `catalogo.articoli.requires_lotto`; `magazzino.lotti` (tabella, vincoli, `COMMENT`); riga `fk_index_policy` in un **CSV dedicato del lotto** (`fk_index_policy_magazzino_lotto1.csv` + loader suo, stampo `20260913-12`: il mirror base è di gennaio e non si sveglia — §5); riga `NESSUNO` in `storico_scope_policy.csv` (§4.10-bis) | `00_schema` + `80_data` |
| **P-2** ✅ 15-09 | `config.sorgenti`: `chk_sorgenti_scope` + `MAGAZZINO`; CSV con le **dieci** righe (cinque fantasma **attive**, `meta = {}` + cinque di magazzino); loader `20251002-21` invariato (le colonne sono le stesse) | `00_schema` + `80_data` |
| **P-3** ✅ 15-09 | `causali`: `DROP TRIGGER IF EXISTS trg_causali_a10_ambito_causale_require_attivo_ins_upd` (è lui a bloccare il DROP), DROP delle otto colonne, CHECK del segno, `DROP DEFAULT`; `DROP TABLE ambito_causale` (+ storico); **cancellazione** di `20251001-05` e di `ambito_causale.csv`; CSV `causali.csv` senza le otto colonne e con le **sei** righe nuove; loader `20251001-51` allineato in place; `DELETE` della riga 136 di `fk_index_policy` (`fk_mag_causali_ambito`) e della riga 69 di `storico_scope_policy`; `manual/ambito_causale.md` cancellato. 🔵 Richiesta BE/FE in D-L1-g | `00_schema` + `80_data` |
| **P-4** ✅ 15-09 | `movimenti`: tutto §4.4, in **questo ordine dentro il file** — i `DROP TRIGGER IF EXISTS` (i **cinque** su `movimenti` che portano `attivo` in `UPDATE OF`, quello su `note_movimento`, quello su `catalogo.unita_misura`), poi i DROP di colonne/vincoli, poi gli ADD, poi l'indice di identità, poi i `COMMENT`; guard tipizzato montato; righe `fk_index_policy` (DELETE di 124, 125, 126, 245 + ADD nel CSV dedicato); riga 76 di `storico_scope_policy` → `PADRE` (§4.10-bis) | `00_schema` + `80_data` |
| **P-5** ✅ 15-09 | `reservations` → `movimenti_attesi`: **un file** con il changeSet della rinomina (tabella, PK, sequenza, gli otto `NOT NULL` superstiti, tre indici, tre FK) **più** un changeSet condizionale per **ciascuno dei due** trigger da rinominare (audit, `tx_id`: `MARK_RAN` + `sqlCheck`), il `DROP IF EXISTS` dei tre `require_attivo`, del trigger storico vecchio, dei **tre** `block_deact` sui padri (`magazzini`, `ubicazioni`, `catalogo.articoli`) e di `storico.reservations`; poi il **secondo file** con le colonne di §4.5; guard tipizzato; `fk_index_policy` (DELETE di 121-123 + ADD); riga 77 di `storico_scope_policy` rinominata → `PADRE`; `manual/` | `00_schema` + `80_data` |
| **P-6** ✅ 15-09 | `costo_medio` → `valore_giacenza`, stessa forma di P-5 (due trigger da rinominare, uno sul padre da togliere); **`DROP VIEW IF EXISTS` delle tre viste prima** del `DROP qta`; FK articolo; partizione `note_costo_medio` via + CHECK del padre; `fk_index_policy` (DELETE di 135 e 247 + ADD); `manual/` | `00_schema` + `80_data` |
| **P-7** ✅ 15-09 | `magazzini` + `assets`: `emittente_fiscale_id` in due passi, guard `trgfn_guard_emittente_scope`, i DROP su `assets` (i due `require_attivo` che bloccano il DROP + i **due** `block_deact` sui padri), `fk_index_policy` (DELETE di 137 e 140 + ADD); **riga 65 del registro RLS**: via dal CSV + `DELETE`; righe 70 e 75 di `storico_scope_policy` → `EF` | `00_schema` + `80_data` |
| **P-8** ✅ 15-09 | Le quattro testate e le tre righe: §4.7 (sorgente_riga, CHECK, guard tipizzato, FK mancante, doppione — col `require_attivo` che blocca il DROP e il `block_deact` su `config.sorgenti` —, `lotto_id`/`asset_id`, CHECK seriale), `fk_index_policy` (DELETE di 264 e 265 + ADD); righe 72-74, 78-81 di `storico_scope_policy` → `PADRE` | `00_schema` + `80_data` |
| **P-9** ✅ 15-09 | `trgfn_movimenti_guard_verso` + i due trigger; `trgfn_trasferimenti_guard_stesso_emittente` + trigger; i due codici in `codici_errore.csv` + `messaggi_errore.csv` | `20_code` + `80_data` |
| **P-10** ✅ 15-09 | Le sette funzioni di scope + lo smistatore delle note (`script`); le **venti** policy + `ENABLE` (un file per famiglia, stampo `20260713-17`). ⚠️ Le righe di `storico_scope_policy` (§4.10-bis) sono già state portate dai passi P-1, P-4, P-5, P-7, P-8: qui si **verifica** che `vw_storico_scope_da_dichiarare` per `magazzino` sia vuota | `20_code` + `00_schema` |
| **P-11** ✅ 15-09 | Le cinque viste (§4.8), tutte `security_invoker = true`. ⚠️ `vw_costo_medio` e `vw_giacenza_valorizzata` rifatte «come join `vw_giacenza` × `valore_giacenza` (qta, valore, costo_medio)» sarebbero state **identiche**: si distinguono per domanda — la prima è il **tasso** (`articolo, magazzino, costo_medio`), la seconda la **situazione** (`qta, valore, costo_medio`), la globale il tasso per articolo sui magazzini **visibili**. Nessun lettore delle colonne vecchie (P-0). `LEFT JOIN` dal registro: una giacenza senza riga di valore mostra `NULL`, non sparisce | `20_code` |
| **P-12** ✅ 15-09 | pgTAP (§7): `test-movimenti-vincoli-v2` (16) sostituisce il v1 (`git rm`), più `test-movimenti-attesi-forma-v1` (14), `test-valore-giacenza-forma-v1` (12), `test-causali-e-sorgenti-seed-v1` (11), `rls/test-rls-magazzino-perimetro-v1` (12, runner **owner** con `FORCE` locale: due aziende costruite). Tutti provati in catena dopo l'SQL estratto: **65 asserzioni verdi**; l'unica rossa attesa è il test 2 degli attesi (i generati col nome nuovo), che vale **a `ci_apply` avvenuto** e lo dichiara in testa | `db/pgtap` |
| **P-13** ✅ 15-09 | Doc: `manual/` di ogni tabella toccata (§8) — 15 aggiornati, 6 nuovi in `magazzino/`, 8 nuovi in `script/`, 3 cancellati + le pagine auto-gen degli oggetti ritirati (`tabelle/{ambito_causale,costo_medio,note_costo_medio,reservations}.md`, `storico/tabelle/{reservations,ambito_causale}.md`: checklist del DROP TABLE, voce 4); `_dominio-magazzino.md` riscritto; `mappa-concentrica.md` riga `magazzino`; questo brief con lo stato di ogni passo | `docs/` |

⛔ **Stato finale `runOnChange: false`** su `00_schema` e `20_code`
(`guardrail_run_on_change.py`); `validCheckSums` **al plurale**. L'apply lo
fa Tid (`AGENTS.md` §Workflow Safety: è un cancello, non una raccomandazione); i pgTAP li lancia Tid col
runner — qui si provano con l'SQL estratto in transazione annullata.

### 6-bis — Riquadro P-0: i censimenti (2026-09-14, su dbdev, letto dal catalogo)

> Struttura, non popolazione: trigger, vincoli, dipendenze, lettori. Le sole
> fotografie sono i conteggi di righe, scritti come tali.

**(a) Trigger — 106 su 25 tabelle di `magazzino`, più 15 fuori schema che
nominano una tabella di `magazzino` negli argomenti.** Il fatto che decide:
un `DROP COLUMN` è bloccato **solo** dai trigger che portano la colonna in
`UPDATE OF` (dipendenza in `pg_depend`), mai dai corpi. Provato colonna per
colonna con `ALTER TABLE … DROP COLUMN` in transazione annullata — **37
colonne, 8 bloccate**:

| Colonna | Bloccata da |
| --- | --- |
| `causali.ambito_causale_id` | `trg_causali_a10_ambito_causale_require_attivo_ins_upd` |
| `movimenti.attivo` | `trg_movimenti_a10_{articoli,causali,magazzini,unita_misura}_require_attivo_ins_upd` + `trg_movimenti_a10_note_movimento_block_deact_upd` (cinque) |
| `movimenti.uom_id` | `trg_movimenti_a10_unita_misura_require_attivo_ins_upd` |
| `reservations.attivo` | `trg_reservations_a10_{articoli,magazzini,ubicazioni}_require_attivo_ins_upd` (tre) |
| `costo_medio.qta` | **le viste** `vw_costo_medio`, `vw_costo_medio_globale` (e `vw_giacenza_valorizzata` a cascata) |
| `assets.magazzino_id` · `assets.ubicazione_id` | `trg_assets_a10_magazzini_require_attivo_ins_upd` · `trg_assets_a10_ubicazioni_require_attivo_ins_upd` |
| `trasferimenti.sorgenti_tipo_id` | `trg_trasferimenti_a10_sorgenti_require_attivo_ins_upd` |

Le altre 29 (`doc_*`, `lotto`, `seriale`, `magazzino_id_dest`,
`ubicazione_id_from/_to`, le sette di `causali`, `stato_reservation`,
`assets.ubicazione`, `sorgenti_uid`, `lotto`/`seriale` sulle tre righe) cadono
pulite. `DROP TABLE ambito_causale` (a FK tolta) e `DROP TABLE note_costo_medio`
passano puliti.

⭐ **Le due funzioni di automazione non sono simmetriche**, ed è ciò che
decide quali trigger sui padri vanno tolti:

* `dbops.trgfn_prevent_deactivate_if_children` (i `block_deact` sui **padri**)
  cerca l'`attivo` della figlia **a runtime** con `fn_col_exists`: se manca,
  conta tutte le righe. Quindi togliere `movimenti.attivo` o
  `reservations.attivo` **non chiede nulla** ai padri. Ma cerca in
  `pg_attribute` la **tabella e la colonna FK** che porta come argomento: se
  una delle due sparisce solleva `E_ATTIVO_BLOCK_FKCOL_NOT_FOUND` a **ogni**
  disattivazione del padre (il caso `-10/-11` del 12-09). ⇒ Da togliere,
  `DROP IF EXISTS`, quelli con un nome che muore negli argomenti — **nove**:
  `trg_{magazzini,ubicazioni,articoli}_a10_reservations_block_deact_upd`,
  `trg_magazzini_a10_costo_medio_block_deact_upd`,
  `trg_unita_misura_a10_movimenti_block_deact_upd` (`uom_id`),
  `trg_sorgenti_a10_trasferimenti_block_deact_upd` (`sorgenti_tipo_id`),
  `trg_{magazzini,ubicazioni}_a10_assets_block_deact_upd`,
  `trg_ambito_causale_a10_causali_block_deact_upd` (`causali.ambito_causale_id`);
* `dbops.trgfn_child_requires_active_parent` (i `require_attivo` sulle
  **figlie**) legge `SELECT <attivo> FROM <padre> WHERE id = $1` con il nome
  della colonna **dagli argomenti**, senza `fn_col_exists`. ⇒
  `trg_note_movimento_a10_movimenti_require_attivo_ins_upd` morirebbe con
  `42703` a ogni nota su un movimento: da togliere, e non si rigenera.

Restano, e non si toccano: i `block_deact` di `causali`, `magazzini` e
`catalogo.articoli` verso `movimenti` (`articolo_id`, `causale_id`,
`magazzino_id` restano), quelli di `catalogo.articoli` verso le tre righe e
`assets`, quelli di `config.sorgenti` verso `inventari` ed `eventi_assets`,
quello di `anagrafiche.indirizzi_dettaglio` verso `magazzini`.

**(b) Lettori dei nomi che cambiano.** Attesi: le tre viste (`20251003-11/12/13`)
e `test-movimenti-vincoli-v1` (8 occorrenze) ✅. **Non attesi, trovati**:
`backend/apps/core/db/dbops_repository.py:107` e
`frontend/src/core/config-tables.js:63` nominano `magazzino.ambito_causale`
(→ D-L1-g); `20_code/dbops/20260727-37` nomina `costo_medio` in un
`DROP INDEX IF EXISTS` già applicato e nel `rollback:` — innocuo. In `pg_proc`
**zero** funzioni leggono `magazzino.{reservations,costo_medio,ambito_causale,note_costo_medio}`;
`magazzino` ha due funzioni (`fn_get_magazzino_note`, `trgfn_magazzini_normalize`)
e nessuna tocca ciò che cambia; `COSTO_MEDIO` come `target_tipo` ha zero lettori
ovunque.

**(c) `80_data`/`90_end`.** Loader `20251001-05` (ambito, `HALT` + `tableExists`)
e `20251001-51` (causali, `runOnChange` + `ANY`, colonne `ambito_causale_id`
e le altre sette nella lista) — attesi. **Non attesi**:
`dbops/fk_index_policy.csv` porta **quattordici** righe da ritirare (121-126,
135, 136, 137, 140, 245, 247, 264, 265 — la prima stesura non contava
`note_costo_medio` e il doppione `fk_mag_rettifiche_sorgenti_tipo`; una esce
con P-3, le altre tredici col `DELETE` di fine lotto `20260915-12`), e il suo
mirror è **di gennaio**: non si sveglia, si `DELETE` in SQL e le righe nuove
vanno in un CSV dedicato con loader suo (forma `20260913-12`);
`dbops/storico_scope_policy.csv` porta **tredici** righe `magazzino` a
`NESSUNO` «finché non entra in RLS» (→ §4.10-bis). I CSV a sola
intestazione senza loader `magazzino/{reservations,costo_medio}.csv` ci sono,
come previsto, e con loro `note_costo_medio.csv` (stessa natura, stessa sorte:
tre file da togliere, non due) — insieme ad altri **venti** gemelli a sola
intestazione dello stesso giorno (24-03), che non sono di questo lotto.

**(d) Righe vive e vincoli nominati.** `config.sorgenti` 3/5/7/9/11:
**esistono e sono `attivo = false`** con `meta.archived` (→ D-L1-f); il
guard tipizzato pretende `attivo = true`. `reservations`: 13 `NOT NULL`
nominati, PK `pk_mag_reservations`, sequenza `reservations_id_seq`, 3 FK, 2
CHECK, 1 UNIQUE, 6 indici, 6 trigger, **0 righe**; `storico.reservations` 0
righe. `costo_medio`: 10 `NOT NULL` nominati, PK, UNIQUE `(articolo_id,
magazzino_id)`, 1 FK (`ON UPDATE RESTRICT`), 3 indici, 2 trigger, niente
`tx_id`/`storicizza`, **0 righe**; nessuna `storico.costo_medio`.
`storico.ambito_causale` 0 righe.

**Altre premesse verificate.** `anagrafiche.emittenti_fiscali` **non** è in RLS
(→ correzione in §1); `vw_rls_perimetro_scoperto` per `magazzino` oggi: una
riga, `assets`, `DEBITO_DICHIARATO` (riga 65 del registro, mirror `20260909-77`
`runOnChange` + `ANY`). `chk_sorgenti_scope` ha sette valori (`PUSH_COMMESSA`,
`PIPELINE_MARKER`, `ROW_VALIDATOR`, `POST_INVOICE`, `DIRECT_ENTRY`,
`PUSH_CONTRATTO`, `REVERSE_FLOW`). `catalogo.articoli` ha `requires_serial`,
`gestito_a_magazzino`, `lead_time_giorni`, `uom_id`; **non** `requires_lotto`.
`chk_note_target_tipo` ha dieci valori, `COSTO_MEDIO` incluso; dieci
partizioni. Ultimo changeSet del giorno: `20260914-14` ⇒ si parte da `-15`.
`test-rls-policies-structure` enumera **per nome** (`rls_fatture_ba_ownership`…):
non va esteso, le venti policy nuove le asserisce il test di P-12.

---

## 7. I presidi

| Test | Che cosa prova |
| --- | --- |
| `magazzino/test-movimenti-vincoli-v2` | **sostituisce il v1**: la sorgente è obbligatoria e a catalogo (un `sorgente_tipo_id` inesistente e una `sorgente_riga` verso un record che non c'è sono rifiutati **dal guard tipizzato**, `throws_like` sulla frase); esattamente una chiave; `\|qta\| = 1` con `asset_id`; `qta = 0` rifiutata **dal guard del verso** (`P0001`, non `23514`) **e** il CHECK esiste ancora in `pg_constraint`; verso incoerente rifiutato con la frase di `E_MAG_MOVIMENTO_VERSO_INCOERENTE`; l'identità: due righe uguali senza lotto/seriale/ubicazione **collidono** (è il `NULLS NOT DISTINCT`), le due righe OUT/IN di un trasferimento **no**; `storno_di_movimento_id` unico. ⚠️ Fixture **costruita** (magazzino con emittente in whitelist, articolo, lotto, un `inventari_righe` come sorgente): il dominio è vuoto e un test che pesca dalla popolazione è muto in CI |
| `magazzino/test-movimenti-attesi-forma-v1` | il nome nuovo e **nessun oggetto** (vincolo, trigger, sequenza, indice) nomina più `reservations` — a `ci_apply` avvenuto (stampo `test-sistemazioni-registro` test 3); `qta` firmata e ≠ 0; il verso; `per_chi`: riga senza sorgente, soggetto **e** nota → rifiutata (è la riga muta che il `coalesce` serve a fermare); `data_prevista` con sorgente → rifiutata; `stato`/`data_chiusura` in coppia; `magazzino_id` obbligatorio |
| `magazzino/test-valore-giacenza-forma-v1` | nessun oggetto nomina `costo_medio`; la FK articolo; le tre viste: `costo_medio = valore / qta` con la quantità **dal registro** (⚠️ non `has_column`: si confronta il valore con la sorgente — brief modifiche certe §7: «un `has_column` sulle viste non basta»); `vw_giacenza_ubicazione` distingue due ubicazioni dello stesso magazzino; `security_invoker` **vera** su tutte e cinque (`pg_class.reloptions`) |
| `magazzino/test-causali-e-sorgenti-seed-v1` | `causali`: sedici righe, `segno ∈ {−1, +1}`, le otto colonne **non esistono**, `ambito_causale` non esiste; `config.sorgenti`: le dieci righe di P-2 esistono con `target_table` risolto (⭐ è il presidio che **la CI non aveva** per le cinque fantasma); `articoli.requires_lotto` esiste |
| `rls/test-rls-magazzino-perimetro-v1` | due emittenti, due magazzini: l'operatore del primo vede il suo e **zero** righe dell'altro su `magazzini`, `movimenti`, `movimenti_attesi`, `valore_giacenza`, `inventari` + righe, `rettifiche` + righe, `trasferimenti` + righe, `assets`, `eventi_assets`, `ubicazioni`, e su una nota per partizione **e dal padre**; un trasferimento fra magazzini di emittenti diversi è rifiutato; una `CLIENTE_PORTALE` vede zero ovunque; ⚠️ il **primo** emittente creato in una fixture è il default: la fixture ne crea **due** (stampo `test-rls-billing-account-returning-secondo-emittente`); `vw_rls_perimetro_scoperto` per `magazzino`: zero righe (è il test 2 di `test-rls-perimetro-scoperto`, che gira già: qui si asserisce **anche** il perimetro atteso, cioè che le venti tabelle abbiano `relrowsecurity` e almeno una policy — così un `ENABLE` dimenticato fa rosso qui e non solo là) |
| `rls/test-rls-policies-structure` (esistente) | ⚠️ da estendere se enumera le policy per nome — verificare in P-12 |

⚠️ Preambolo obbligatorio (`BEGIN;`, contesto operatore, `SET CONSTRAINTS ALL
IMMEDIATE`) presidiato da `guardrail_pgtap_preambolo.py`. I test girano
**come l'applicazione, sotto RLS**: una fixture che scrive dove l'app non
scrive non passa — ed è il motivo per cui M-7 sta qui e non prima.

⚠️ `throws_ok(…, NULL, NULL)` non vale: sempre lo SQLSTATE, e `throws_like`
dove la frase è la posta in gioco.

⭐ **Aggiunto la sera del 15-09, dopo il runner e il DB da zero** (§11, §12):

- le fixture **fabbricano** l'indirizzo con `dbops.fn_pgtap_crea_indirizzo_dettaglio(etichetta)`
  (`20260915-19`): `indirizzi_dettaglio` è dato di macchina, e un `SELECT … LIMIT 1` muore
  su `zeroerp_ci` in `ERRORE_FIXTURE`. L'articolo e i vocabolari `config.*` sono seed di
  catalogo e si possono cercare per nome;
- un `NOT NULL` sulla colonna-ancora di una policy si asserisce con `col_not_null`, non per
  `INSERT`: sotto RLS il `WITH CHECK` scatta prima del vincolo (`42501`, non `23502`);
- due presidi **fuori lotto** riscritti perché il lotto ne cambiava la materia:
  `dbops/test-trgfn-prevent-deactivate-if-children-pdp` (indirizzo dall'helper) e
  `config/test-sorgenti-scope-pulizia-v1` (test 6 e 9 sul contratto D-L1-f). ⚠️ Il primo era
  verde su GitHub per un indirizzo lasciato da altri nella suite; il secondo era in
  `baseline-rossi-ci.tsv` dal primo giorno. Nessuno dei due lo diceva.

---

## 8. Doc e cataloghi da toccare

- `docs/it/dbzero/magazzino/manual/`: `movimenti.md`, `causali.md`,
  `magazzini.md`, `assets.md`, `inventari.md`, `inventari_righe.md`,
  `rettifiche.md`, `rettifiche_righe.md`, `trasferimenti.md`,
  `trasferimenti_righe.md`, `eventi_assets.md`, `vw_giacenza.md`,
  `vw_costo_medio.md`, `vw_costo_medio_globale.md`, `vw_giacenza_valorizzata.md`
  **aggiornati**; `movimenti_attesi.md`, `valore_giacenza.md`, `lotti.md`,
  `vw_giacenza_ubicazione.md`, `trgfn_movimenti_guard_verso.md`,
  `trgfn_trasferimenti_guard_stesso_emittente.md` **nuovi**; `reservations.md`,
  `costo_medio.md`, `ambito_causale.md`, `note_costo_medio.md` **cancellati**
  (regola di `AGENTS.md` §Documentazione: l'indice di `manual/` è generato, un moncone resterebbe in elenco — la spiegazione del ritiro va nel `manual/` dell'oggetto che ha preso il posto). ⛔ `index.md`/`index.ci.md` non si
  toccano: sono generati. ⛔ La build della doc non si lancia.
- `docs/it/dbzero/script/manual/`: le otto funzioni di scope nuove.
- `docs/it/dbzero/magazzino/_dominio-magazzino.md`: il modello dopo il lotto.
- `docs/it/mappa-concentrica.md`, riga `magazzino`: da «modello disegnato, non in
  esercizio» a «forma decisa, perimetro armato, in attesa della primitiva».
- `docs/it/guide/sorgente-polimorfa.md` §5 dice che lo stato d'uso **non è una
  lista scritta lì**: niente da aggiornare, ma il pgTAP di P-12 diventa il
  presidio delle dieci righe.
- Questo brief: lo stato di ogni passo, il riquadro di P-0, e la data di ogni
  decisione D-L1-*.

---

## 9. Che cosa NON entra, e dove sta

| Cosa | Dove | Perché non qui |
| --- | --- | --- |
| la **primitiva** e le operazioni (M-2), il blocco advisory, i `GRANT` che chiudono `movimenti` alla sola primitiva | Lotto 2 | è codice che scrive; questo lotto è la forma su cui scriverà. ⚠️ Finché non c'è, `movimenti` resta scrivibile dall'app: il perimetro RLS c'è, la porta no |
| la `fn_check` di disponibilità e la **vista situazione merce** (M-3) | Lotto 2 | presuppone la primitiva per la formula «stessa in due posti»; le colonne «impegnata/in arrivo» aspettano il satellite D-17 di acquisti |
| la **vista degli orfani** (D-9) | Lotto 2 | generica su `config.sorgenti`, nasce col primo scrittore che può sbagliare |
| il **presidio di prontezza** su `gestito_a_magazzino` (vista `dbops` a una riga, natura `ZERO` in `presidi.csv`) | Lotto 2, col passo 2 | deciso da Tid il 14-09: si scrive quando la primitiva **legge** la colonna, o suona per mesi a vuoto |
| `causali.sorgente_tipo_id` 1:1 («questa causale accetta solo questa sorgente») | Lotto 2, candidata | la legge la primitiva; qui non ha consumatore (D-8) |
| la **utility di storno** (M-8) | Lotto 3 | è un'operazione |
| la sorgente del **ricevimento** e `ODL_*` | Lotti 4 e 5 | i loro record non esistono ancora |
| il roll-out del guard tipizzato sulle **nove** tabelle fuori `magazzino` (D-3) | cantiere `dbops` | perimetro suo |
| il ritiro di `storico.*` e lo storico sotto RLS | D3 di `migliorie-generali-da-test-valutazione` | non è di questo dominio |
| il **`FORCE ROW LEVEL SECURITY`** che §7-sexies chiedeva | nessuno: postura del progetto | nessuna tabella lo usa e l'app non è owner; si cambia per tutti o per nessuno |
| l'apply, i pgTAP col runner, il commit | Tid | decisione di Tid: l'apply e il commit non sono autonomi |

---

## 10. Riferimenti

- Le decisioni: [analisi carico e scarico](../work-in-progress/analisi-db-magazzino-carico-e-scarico.md)
  (M-1 → M-9, §8 lotti), [analisi aggancio §8 e §8-quater](../work-in-progress/analisi-db-magazzino-aggancio-documento-e-produzione.md)
  (D-1 → D-9), [analisi commessa](../work-in-progress/analisi-db-commessa-e-produzione-predisposizione.md)
  (§7 rinviata), [analisi acquisti §8 e §10](../work-in-progress/analisi-simmetria-ordini-acquisto.md)
  (ricezione, D-17).
- Le forme da copiare: rinomina con trigger condizionali
  `00_schema/pagamenti/20260822-25`; policy `00_schema/vendite/20260713-17`;
  adattatore di scope `20_code/script/20260909-36`; smistatore delle note
  `20_code/script/20260909-72` (+ la policy del padre `00_schema/vendite/20260909-73`); scope nuovo `00_schema/config/20260714-07`;
  loader modificato in place `80_data/changelog/20260614-08`; registro RLS
  `brief-db-perimetro-emittente-righe-documento` §11.7.
- Doc auto-gen letta: `docs/it/dbzero/magazzino/tabelle/*.md` (14-09),
  `docs/it/dbzero/config/tabelle/sorgenti.md`, `dbops/views/vw_rls_perimetro_scoperto.md`.

---

## 11. Registro delle revisioni

| Data | Cosa |
| --- | --- |
| 2026-09-17 (sera) | ✅ **CHIUSO, in `work-done/`.** Verifica delle competenze BE sui **file di HEAD** (`86deea82f`, non sul commit `6f786ed9f`, che un commit dopo avrebbe potuto disfare): `E_MAG_MOVIMENTO_VERSO_INCOERENTE` → `TECNICO` e `E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI` → `DATO_ERRATO` in `error_policies_generated.py`, le stesse classi di `config.vw_codici_errore_identita` su dbdev; due ripieghi senza segnaposto in `error_messages_fallback.py`, coerenti con causa/soluzione a catalogo; `ambito_causale` a **0** occorrenze in `backend/apps` e `frontend/src` (le tre voci `magazzino` superstiti — `causali`, `magazzini`, `ubicazioni` — puntano a tabelle vive); `requires_lotto` a 0 (Lotto 2, atteso). Corsa CI del merge #1601 (`35241276981`, 15:35 UTC) letta dal log: Django `Ran 4872 tests … OK (skipped=32)`, pgTAP «nessuna regressione», **sette** RIENTRATI. I tre «aperti» del mattino: gemello **applicato** alle 12:06 (`20260915-36 → -46`, `databasechangelog`; i due `default_emittente` montati su `magazzini`/`assets`) e già nel modulo BE; riga 58 **tolta** con `pgtap-baseline-ci-rientrati.sh` sulla corsa (372 → 365: con la nostra sono uscite sei righe di `pagamenti`/`vendite` che la corsa dichiarava rientrate — lo script per progetto toglie ciò che la CI ha misurato, non una selezione); `requires_lotto` UI è Lotto 2. ⚠️ Il gemello porta ancora in testa «in attesa di apply»: è un brief suo, con la sua checklist §12, e si aggiorna lì. Ripuntati i link relativi dei tre documenti di `work-in-progress/` che lo citavano per path, `mappa-concentrica.md` riga `magazzino`, `PROJECT_CONTEXT.md`. La baseline l'ha committata Tid alle 17:47 (`0198a092a`, «Aggiornamento baseline-rossi»: le sette righe); lo spostamento del brief e i documenti ripuntati restano **non committati** (decisione di Tid) |
| 2026-09-15 (sera, 17:10) | **Mergiato e verificato.** PR #1593 su `Tito-dev` (14:43 UTC); corsa del merge letta dal log: pgTAP senza regressioni, RIENTRATO confermato (riga 58 della baseline CI ancora da togliere), Django rosso **solo** per i due `E_MAG_*` — i cinque `E_PROCESSO_*` sono già rigenerati (#1592). **Tre correzioni di Tid**: (1) §4.7 **deciso** — BB generico dell'emittente di default **e ritiro delle copie di vendite nello stesso giro**, brief suo prima del Lotto 2; censite: tre copie vere, una variante morbida (ddt), una diversa (commesse), e nove tabelle ancorate senza default; (2) §4.3 — `requires_lotto` non si copia da `requires_serial` a occhi chiusi: quello è un flag di **struttura BoM** sotto lock, questo **no** per decisione; e la frase sul `security_invoker` di `vw_articoli_dettaglio` era **falsa** (la vista non ce l'ha e non deve averlo); (3) §12 p.2 — **nessun cantiere `dbops`**: le automazioni su dev si lanciano a mano nell'ordine della CI, scritto lì |
| 2026-09-15 15:18 → 15:30 | ✅ **Commit `61b4cb5d3` su `dev/db-tid`** (Tid, 15:18, pushato: `origin/dev/db-tid` allineato) — «Aggiornamento Db … Eseguiti test pgtap e aggiornata documentazione»: 23 changeSet nuovi + il loader `20251001-51` in place, 5 pgTAP nuovi + 2 riscritti, i CSV, 32 manuali, le pagine auto-gen rigenerate (`gen_db_docs.py`: indice `magazzino/` con rev 15-09, `lotti`/`movimenti_attesi`/`valore_giacenza`/`vw_giacenza_ubicazione`, le otto `fn_scope_*`, `fn_pgtap_crea_indirizzo_dettaglio`), questo brief. Le cancellazioni (`git rm`) erano già nel commit precedente `f6eb32841` e sono su `Tito-dev` dalla PR #1591 (12:47) **senza** il lotto — stato a metà innocuo, vedi §12 p.5 e p.6. **Verifica alle 15:30** (letta dal `databasechangelog` e dal catalogo di dbdev): 26 `EXECUTED` (`-18` alle 12:29, `-19`/`-20` alle 12:50 — non «tutti e tre alle 12:50»), 23 tabelle RLS / 23 policy, `vw_rls_perimetro_scoperto` e `vw_storico_scope_da_dichiarare` a 0 per `magazzino`, shadow su `lotti` e `movimenti_attesi`, 12 trigger sugli attesi, 0 `ix_mag_res*`, 0 esenzioni, 16 causali, oggetti ritirati assenti — la fotografia di §12 regge. 🔴 **Trovato verificando: una richiesta BE mancava a §12.** I due `E_MAG_*` sono a catalogo e hanno **0** occorrenze in `error_policies_generated.py` e `error_messages_fallback.py`; `test_il_file_generato_e_allineato_al_catalogo` è **già rosso su `Tito-dev`** dalla PR #1591 (i cinque `E_PROCESSO_*` di «Esegui ora», 23 righe) e questo lotto vi aggiunge due codici → §12 p.7, quarta voce. ⚠️ E la suite pgTAP in CI **non gira sulla PR** verso `Tito-dev` (`ci-validate.yaml`: PR verso `main`, push su `Tito-dev` che toccano `db/`): il RIENTRATO si legge nella corsa **del merge** |
| 2026-09-15 (notte) | ✅ **CHIUSO lato DB** (Tid): `-18`, `-19`, `-20` applicati su dbdev (12:50), automazioni passate, **`scripts/pgtap-baseline.sh` verde su dbdev e su `zeroerp_ci` ricostruito da zero** (`ci-local.sh --fresh --ci-apply`). Letto dal catalogo dopo: 0 righe in `vw_rls_perimetro_scoperto` e in `vw_storico_scope_da_dichiarare` per `magazzino`, shadow e `z90_storico` su `lotti` e `movimenti_attesi` (non su `valore_giacenza`: per progetto, §4.6), 7 `require_attivo` sugli attesi, indici degli attesi tutti col nome di policy, registro dei riferimenti morti a 0/0/0. Il bilancio della sera è in §12 e nelle ultime sei righe di §5 |
| 2026-09-15 (sera) | **Prima corsa su `zeroerp_ci` (`scripts/ci-local.sh`) rossa su P-4**: «il vincolo `uq_mag_movimenti_docref` non esiste». Non erano i sette `DROP TRIGGER` (tutti `IF EXISTS`): è il `MARK_RAN` autolesionista di `20251005-11/-15` (§5, riga nuova) — `-13/-14` e `-17/-18` sono `MARK_RAN` su **ogni** DB da zero (letto nel `databasechangelog` di `zeroerp_ci`), e i due `uq_*_docref` esistono solo su dev. Corretti `20260915-05` e `-07`: `DROP CONSTRAINT IF EXISTS` sul solo docref, intestazioni col perché. Censiti sullo `zeroerp_ci` **tutti** i nomi che il lotto droppa o rinomina senza `IF EXISTS` (10 `DROP CONSTRAINT`, 23 `RENAME CONSTRAINT`, sequenze): mancavano solo quei due. Provata la catena `00_schema`/`20_code` del lotto (11 changeSet, `-05` → `-17`) con l'SQL estratto da `updateSQL` contro `zeroerp_ci` in `BEGIN … ROLLBACK`, tolti i tre rename condizionali: **passa**. I cinque `80_data` del lotto precondizionano solo `tableExists`. ⚠️ Su dev i due changeSet sono già `EXECUTED` col checksum vecchio: il riallineamento è il passo 1-bis di §12. **Poi, prima corsa col runner** (Tid) di `test-movimenti-attesi-forma-v1`: 12/14 — il 2 è il momento sbagliato (`ci_apply` non passato), il **14 pinnava un `23502` che sotto RLS non arriva** (la policy scatta prima del vincolo: `42501`) → riscritto su `col_not_null` (§12, punto 3). Poi **14/14**, ma dopo **due** passate di automazioni: su dev `db-ci-apply` non le rilancia, sono dieci job pgAgent senza ordine, e `storico` gira prima di `storico_provision` → una madre nuova ha la shadow alla passata 1 e il trigger alla 2 (§12, punto 2: finestra di 24h, cantiere `dbops`). **Terzo rosso col runner**, `dbops/test-riferimenti-morti-v1` test 4: la voce «orfana di proposito» di `trgfn_guard_sorgente_polimorfa_tipizzata` (unica del registro dal 04-08) è **rientrata** — il lotto l'ha montata su sei tabelle e nessuno ha censito il registro che la dichiarava orfana. `20260915-18`: `DELETE` in avanti, provato in `BEGIN … ROLLBACK` (rientrati 0, da sanare 0). Lezione in §5. **Poi `ci-local.sh --fresh --ci-apply`** (Tid): tre `ERRORE_FIXTURE` — le fixture cercavano un `indirizzi_dettaglio` «attivo», dato di macchina assente da zero → helper `fn_pgtap_crea_indirizzo_dettaglio` (`20260915-19`) nelle quattro fixture; e il test 1 degli attesi rosso solo da zero: tre indici FK del 2025 sopravvissuti alla rinomina (la policy copre solo FK scoperte) → `20260915-20`, e il test cerca anche `mag_res_`. Provati i quattro file su `zeroerp_ci` con l'SQL estratto: tutti verdi. Due righe in §5. Terzo giro (`dbops` sul CI): `test-trgfn-prevent-deactivate-if-children-pdp` `ASSERZIONE` — stesso lookup dell'indirizzo, fuori lotto, verde su GitHub solo per contaminazione d'ordine (fonte non trovata: i quattro file che fanno `COMMIT` scrivono solo conti bancari) → helper anche lì, 13/13 con i test 7-12 finalmente eseguiti. Il lookup non esiste più in nessun pgTAP. Quarto: `config/test-sorgenti-scope-pulizia-v1` rosso su dev (test 6 e 9) — pinnava le cinque `*_RIGA` archiviate, cioè l'`UPDATE` a mano che D-L1-f ha disfatto; in CI era già `ASSERZIONE` in baseline (da zero quelle righe non esistevano). Riscritti sul contratto D-L1-f: 9/9 su `zeroerp_ci`, stessi valori su dev → **rientra** in CI (lo toglie `pgtap-baseline-ci-rientrati.sh` dalla corsa). Censimento mancato del lotto: riga in §5 |
| 2026-09-15 11:38 | **Apply su dbdev** (Tid): 22 changeSet `EXECUTED`, preCondition «zero righe» passate. Letto dal catalogo dopo l'apply: presidio RLS a zero per `magazzino`, 23 tabelle armate, oggetti ritirati spariti, seed e sequence a posto. `ci_apply` non ancora passato (solo il `runAlways` dell'armatura storico): `lotti` senza trigger/shadow, due `RIGA_SENZA_MADRE` transitorie. Restano `ci_apply`, pgTAP col runner, doc build, commit, richieste BE/FE (§12) |
| 2026-09-15 (notte, chiusura) | **P-12 e P-13 scritti**: cinque pgTAP (65 asserzioni, tutte verdi in catena tranne il test 2 degli attesi, che vale a `ci_apply` avvenuto), 32 manuali fra nuovi, riscritti e cancellati, `_dominio-magazzino.md`, la riga della mappa, la consegna in §12. Il lotto è **SCRITTO, in attesa di apply** |
| 2026-09-15 (notte) | **P-9 → P-11 scritti e provati** in catena P-1 → P-11: i due guard con `%TYPE` nel `DECLARE` (regola di Tid ricordata in sessione), i due codici a catalogo (id 1065, 1066) con frase composta dai valori, le **otto** funzioni di scope (STABLE, invoker) esatte su due aziende costruite con `fn_pgtap_crea_emittente_operatore`, **ventitré** policy (non venti: 13 tabelle + padre `note` + 9 partizioni) con `vw_rls_perimetro_scoperto` a zero per `magazzino`, le cinque viste `security_invoker` coi numeri che tornano. ⚠️ La RLS in transazione non si esercita (l'owner la bypassa senza FORCE, e `titodb` non può `SET ROLE zeroerp_app`): è il pgTAP di P-12 col runner applicativo a farlo |
| 2026-09-15 (sera) | **P-7 e P-8 scritti e provati**, catena completa P-1 → P-8 + i tre `DELETE` di registro in `BEGIN … ROLLBACK`: guard tipizzato su **sei** tabelle, zero righe morte in `fk_index_policy`, mappa storico a 13 righe (2 `RIGA_SENZA_MADRE` transitorie fino a `ci_apply`), `assets` `NON_DICHIARATO` fino a P-10. Trovato: due CHECK da/a tautologici (§4.7), il default dell'emittente su `magazzini` è un punto aperto BE/Lotto 2 (§4.7), quattordici righe di policy da ritirare (non dodici) |
| 2026-09-15 (pomeriggio) | **P-4 → P-6 scritti e provati.** Trovato scrivendo: un `require_attivo` è un **constraint trigger** e non si rinomina in modo pulito (→ DROP + rigenera, §4.6); sugli attesi il CHECK della chiave è più stretto del brief e l'indice è parziale sulle `APERTA` (§4.5). Il render offline + `BEGIN … ROLLBACK` in catena P-1 → P-6 passa con fixture costruita (magazzino, inventario, riga, lotto, asset): identità `NULLS NOT DISTINCT`, guard tipizzato (`E_SORG_NOT_FOUND`, `E_SORG_CONF`, `E_SORG_KEY_MISSING`), storno unico, `per_chi`, `chiusura`, nota su movimento senza `attivo` |
| 2026-09-15 | **Decisioni confermate** (§3) e **P-1 → P-3 scritti e provati** con l'SQL estratto in transazione annullata. Trovati scrivendo: le sei causali nuove sono id **23-28** (non 11-16); le sequence di `causali` e `sorgenti` vanno riallineate dopo i seed (`20260915-04`); `eventi_assets` porta i `doc_*` (→ P-8). File morti cancellati con `git rm`: loader `20251001-05`, `ambito_causale.csv`, `manual/ambito_causale.md` |
| 2026-09-14 (sera) | **P-0 eseguito**, riquadro in §6-bis. Quattro fatti smentiscono la prima stesura e la correggono in loco: (1) `emittenti_fiscali` non è in RLS — il presidio scatta da `magazzini` armata, non dalla FK (§1); (2) i `block_deact` sui padri **non** vanno toccati per il DROP di `attivo` (la funzione è dinamica) — vanno tolti i **nove** che portano un nome morto negli argomenti, e il `require_attivo` di `note_movimento` (§4.4, §6-bis); (3) `costo_medio.qta` è bloccata dalle **viste**, non dai trigger (§4.6); (4) `dbops.storico_scope_policy` ha tredici righe `magazzino` che la RLS di P-10 renderebbe `PROTETTA_NESSUNO` (§4.10-bis). Due decisioni nuove: **D-L1-f** (le cinque `*_RIGA` sono archiviate su dev, entrano attive) e **D-L1-g** (`ambito_causale` ha due lettori vivi in BE/FE: il `DROP TABLE` esce dal giro). Contati: dodici righe di `fk_index_policy` da ritirare (non nove), tre CSV morti (non due), tre `block_deact` su `reservations` (non uno), due su `assets` (non uno) |
| 2026-09-14 | **Nascita.** Dopo le cinque decisioni di Tid (aggancio §8-quater) e la conferma di D-6 come sorgente **obbligatoria** (*«mi hai convinto»*): il DDL deciso da M-1 → M-9 e D-1 → D-9, sul terreno vuoto, più il perimetro RLS — che entra qui e non nel Lotto 2 perché `vw_rls_perimetro_scoperto` non ammette un'ancora senza policy (§1). Cinque decisioni piccole emerse scrivendo le colonne (§3): UoM base, ciclo degli attesi, il verbo è la causale, le causali dello storno, la partizione delle note sull'accumulatore. Fatti di struttura trovati e non presenti nelle analisi: le cinque `*_RIGA` fantasma di `config.sorgenti`, la FK mancante su `rettifiche`, la coppia `sorgenti_*` duplicata su `trasferimenti`, `lotto`/`seriale` testo sulle righe delle testate, `is_installazione_asset` non censita, `config.assets_ownership` già esistente |

---

## 12. Consegna — che cosa c'è e che cosa resta a Tid

**I changeSet, nell'ordine della timeline** (l'autogen li mescola per numero: `00_schema`
e `20_code` prima, `80_data` dopo):

| # | File | Passo |
| --- | --- | --- |
| `20260914-15` | `00_schema/catalogo/…alter-articoli-add-requires-lotto` | P-1 |
| `20260914-16` | `00_schema/magazzino/…create-table-lotti` | P-1 |
| `20260914-17` | `80_data/…upsert-fk-index-policy-magazzino-lotto1` + `sql/magazzino/fk_index_policy_magazzino_lotto1.csv` (mirror vivo, 26 righe: cresce con i passi) | P-1 → P-8 |
| `20260915-01` | `00_schema/config/…alter-sorgenti-scope-add-magazzino` + `sorgenti.csv` (+10 righe) | P-2 |
| `20260915-02` | `00_schema/magazzino/…alter-causali-forma-decisa` + `causali.csv` (riscritto) + loader `20251001-51` in place; **cancellati** loader `20251001-05` e `ambito_causale.csv` | P-3 |
| `20260915-03` | `80_data/…delete-registri-ambito-causale` (+ riga 69 via da `storico_scope_policy.csv`) | P-3 |
| `20260915-04` | `80_data/…resync-seq-causali-sorgenti` | P-2/P-3 |
| `20260915-05` | `00_schema/magazzino/…alter-movimenti-forma-decisa` | P-4 |
| `20260915-06` | `00_schema/magazzino/…rename-reservations-in-movimenti-attesi` (3 changeSet) | P-5 |
| `20260915-07` | `00_schema/magazzino/…alter-movimenti-attesi-forma-decisa` | P-5 |
| `20260915-08` | `00_schema/magazzino/…rename-costo-medio-in-valore-giacenza` (2 changeSet) | P-6 |
| `20260915-09` | `00_schema/magazzino/…alter-magazzini-assets-ancora-emittente` | P-7 |
| `20260915-10` | `80_data/…delete-debito-rls-assets` (+ riga 65 via da `rls_perimetro_debito.csv`) | P-7 |
| `20260915-11` | `00_schema/magazzino/…alter-testate-e-righe-sorgente-lotto-asset` | P-8 |
| `20260915-12` | `80_data/…delete-fk-index-policy-righe-ritirate-lotto1` (13 righe) | P-4 → P-8 |
| `20260915-13` | `20_code/magazzino/…create-trgfn-movimenti-guard-verso` (+2 trigger) | P-9 |
| `20260915-14` | `20_code/magazzino/…create-trgfn-trasferimenti-guard-stesso-emittente` (+1 trigger) | P-9 |
| — | `codici_errore.csv` (+2), `messaggi_errore.csv` (+2, id 1065-1066) | P-9 |
| `20260915-15` | `20_code/script/…create-fn-scope-ef-whitelist-via-magazzino-famiglia` (8 funzioni) | P-10 |
| `20260915-16` | `00_schema/magazzino/…create-policy-rls-magazzino-perimetro` (23 policy + ENABLE) | P-10 |
| `20260915-17` | `20_code/magazzino/…update-viste-giacenza-e-valore` (5 viste) | P-11 |
| `20260915-18` | `80_data/…delete-esenzione-riferimenti-morti-guard-tipizzato` — la voce «orfana di proposito» del registro dei riferimenti morti è rientrata (il guard tipizzato è montato su sei tabelle): `DELETE` in avanti sulla chiave naturale. ✅ applicato (trovato dal test 4 di `dbops/test-riferimenti-morti-v1`, 15-09 sera) | P-4 |
| `20260915-19` | `20_code/dbops/…create-fn-pgtap-crea-indirizzo-dettaglio` — helper di fixture: un `indirizzi_dettaglio` si **fabbrica** sul primo stradario di seed (dato di macchina: zero righe su un DB da zero; `magazzini.indirizzo_dettaglio_id` NOT NULL). Le quattro fixture di magazzino/RLS lo chiamano, **più** `dbops/test-trgfn-prevent-deactivate-if-children-pdp` (fuori lotto: stesso lookup, test 6 rosso e 7-12 «skipped» sul DB da zero — su GitHub verde per un indirizzo lasciato da altri; ora fabbrica il suo, 13/13 su `zeroerp_ci`). ✅ applicato (trovato da `ci-local.sh --fresh`: tre `ERRORE_FIXTURE`) | P-12 |
| `20260915-20` | `00_schema/magazzino/…drop-indici-reservations-superstiti` — i tre indici FK del 2025 (`ix_mag_res_articolo`, `ix_mag_res_magazzino`, `ix_mag_reservations_ubicazione`) che su un DB da zero sopravvivono alla rinomina: la policy FK copre solo una FK **scoperta**, quindi non li sostituiva mai. `DROP IF EXISTS`, la policy li rigenera col nome suo nella stessa passata; no-op su dev. ✅ applicato (trovato dal test 1 degli attesi su `zeroerp_ci`) | P-5 |
| — | `storico_scope_policy.csv`: 12 righe `magazzino` riscritte (EF/PADRE), riga 69 via, riga 122 nuova (`lotti`) | P-1 → P-8 |

**I pgTAP** (§7, P-12) — **tutti verdi in baseline, su dbdev e su `zeroerp_ci`** (Tid,
15-09 notte): `magazzino/test-movimenti-vincoli-v2` (16, sostituisce il v1, `git rm`),
`test-movimenti-attesi-forma-v1` (14), `test-valore-giacenza-forma-v1` (12),
`test-causali-e-sorgenti-seed-v1` (11), `rls/test-rls-magazzino-perimetro-v1` (12, runner
`owner`). Nessuno dei cinque è in baseline. Le quattro fixture che creano un magazzino
fabbricano l'indirizzo con `dbops.fn_pgtap_crea_indirizzo_dettaglio` (`20260915-19`).
**Due file fuori lotto riscritti** perché il lotto li toccava:
`dbops/test-trgfn-prevent-deactivate-if-children-pdp` (indirizzo dall'helper: i test 7-12 ora
eseguono, prima erano «skipped» sul DB da zero) e `config/test-sorgenti-scope-pulizia-v1`
(test 6 e 9 sul contratto D-L1-f: sei sorgenti di riga attive, per nome; nessuna marchiata).
⚠️ Il secondo era `ASSERZIONE` in `baseline-rossi-ci.tsv` dal primo giorno: **rientra** alla
prossima corsa di GitHub, e la riga la toglie `scripts/pgtap-baseline-ci-rientrati.sh` — non a
mano.

**Fotografia finale (dbdev, 2026-09-15 sera, letta dal catalogo dopo apply + automazioni):**

| Cosa | Stato |
| --- | --- |
| `databasechangelog` | 26 changeSet del lotto `EXECUTED` (`20260914-15/16/17`, `20260915-01 → -20` coi sotto-changeSet `-06-01`, `-06-02`, `-08-01`); nessun `MARK_RAN`; i checksum di `-05` e `-07` riallineati dopo la correzione della sera |
| `vw_rls_perimetro_scoperto` per `magazzino` | **0 righe**; 23 tabelle con RLS accesa e policy; registro del debito senza righe di magazzino |
| `vw_storico_scope_da_dichiarare` per `magazzino` | **0 righe**: shadow e `trg_<t>_z90_storico_upd_dlt` su `lotti` e `movimenti_attesi`; `valore_giacenza` senza storico **per progetto** (copia ricostruibile, §4.6) |
| automazioni | passate (due giri dei job pgAgent, §12 p.2): 7 `require_attivo` su `movimenti_attesi`, audit e tx_id rinominati, `ambito_causale` e `reservations` senza più trigger orfani |
| indici di `movimenti_attesi` | solo nomi di policy + `ix_mag_movimenti_attesi_aperte` + PK: i tre del 2025 non esistono più (`-20`) |
| `dbops.riferimenti_morti_esenzioni` | **0 voci** su dbdev, 0 rientrate, 0 da sanare (in CI resta la sola riga pgAgent, voluta dal `20260914-03`) |
| oggetti ritirati | `reservations`, `costo_medio`, `ambito_causale`, `note_costo_medio`, `storico.reservations`, `storico.ambito_causale`: **non esistono** |
| seed | 16 causali, 10 sorgenti `MAGAZZINO` + le 6 `ROW_VALIDATOR` attive e senza marchio, 2 codici `E_MAG_*`, sequence riallineate, 0 righe morte in `fk_index_policy` |
| `zeroerp_ci` (`--fresh --ci-apply`) | stessa forma: 12 trigger su `movimenti_attesi`, baseline verde |

**Che cosa resta a Tid** (decisioni sue: `AGENTS.md` §Workflow Safety, memoria «no commit
autonomo»):

1. ✅ apply su dbdev (11:38 i primi 23 changeSet, 12:29 `-18`, 12:50 `-19/-20` — dal `databasechangelog`), checksum di `-05`/`-07`
   riallineati con `md5sum = NULL` (non `runAlways`: avrebbe **rieseguito** e la preCondition
   avrebbe fermato il migrate);
2. ✅ automazioni — in **due** passate, e il fatto resta scritto: su dev `make db-ci-apply`
   **non le rilancia** (`220250627-31` è `EXECUTED` una volta, né `runAlways` né `runOnChange`);
   le fanno i dieci job pgAgent `automations_*`, tutti `daily_21` senza ordine, e
   `automations_storico` gira **prima** di `automations_storico_provision`: una madre nuova ha
   la shadow alla passata 1 e il `z90_storico` alla 2 — alle 21:00 vuol dire il giorno dopo.
   ✅ **Nessun cantiere `dbops`** (Tid, 15-09 sera): *«le automazioni posso lanciarle a mano
   anch'io, se servono»*. La prima stesura chiedeva un job a `21:05` o una procedura unica; non
   serve. La regola operativa resta scritta qui: su dev, dopo un apply che crea una tabella in
   scope storico, si lanciano a mano **nell'ordine della CI** (`220250627-31`):
   `CALL maintenance.proc_automations_audit_update_job()` → `…_storico_provision_job()` →
   `…_storico_job()` → `…_tx_id_job()` → `…_attivo_job()` → `…_lock_columns_job()` →
   `…_delete_block_job()`. Un pgTAP che conta i generati di una tabella nuova si legge **dopo**
   quel giro, non dopo i job delle 21:00;
3. ✅ pgTAP col runner su dbdev e su `zeroerp_ci` da zero: baseline verde;
4. ✅ la doc: le pagine auto-gen sono **rigenerate e nel commit** (`scripts/gen_db_docs.py`,
   che è quello che scrive `dbzero/*` — non `build_docs_zensical.py`, che costruisce il sito):
   `movimenti_attesi`, `valore_giacenza`, `lotti`, `vw_giacenza_ubicazione`, le otto funzioni
   di `script`, `dbops/funzioni/fn_pgtap_crea_indirizzo_dettaglio`, e l'indice di `magazzino/`
   con la rev 15-09 e senza più `reservations`/`costo_medio`/`ambito_causale`. La build del
   sito non lascia traccia in git e da qui non si verifica;
5. ✅ il **commit** `61b4cb5d3` su `dev/db-tid` (15:18, pushato): i 23 file di changeSet +
   il loader `20251001-51` in place, i sette pgTAP, i CSV, i manuali, le pagine auto-gen e
   questo brief. ⚠️ Le cancellazioni (`git rm`: loader `20251001-05`, `ambito_causale.csv`,
   `test-movimenti-vincoli-v1`, i manuali e le pagine dei quattro oggetti ritirati) erano
   partite **prima**, col commit `f6eb32841` della PR #1591 (merge 12:47), quindi `Tito-dev`
   è oggi in uno stato a metà: la tabella `ambito_causale` la crea ancora `20251001-03` e
   nessuno la semina, il v1 dei vincoli è via e il v2 non c'è. **Innocuo, e letto dalla corsa,
   non supposto**: nel `causali.csv` di quel commit `ambito_causale_id` era vuoto per tutte le
   righe, e sul push di merge (`run 34959875667`) migrate e suite pgTAP sono verdi. Si chiude
   con il punto 6;
6. ✅ la **PR `dev/db-tid` → `Tito-dev`**: **#1593, mergiata il 15-09 alle 14:43 UTC**
   (commit `937acd83a`; poi #1594). **Corsa del merge `34984791746`, letta dal log** (non
   supposta): suite pgTAP «nessuna regressione: ogni rosso era già noto», e
   **RIENTRATO `db/pgtap/config/test-sorgenti-scope-pulizia-v1.sql`** — la riga 58 di
   `baseline-rossi-ci.tsv` ✅ **tolta il 17-09 sera** con
   `scripts/pgtap-baseline-ci-rientrati.sh 35241276981` (la corsa del merge #1601, che lo
   dichiarava ancora RIENTRATO insieme ad altri sei). «Django tests» **rosso: 2 FAIL su 4861** —
   `test_nessun_codice_nuovo_senza_policy` e `test_il_file_generato_e_allineato_al_catalogo`,
   ed **entrambi nominano solo i due `E_MAG_*`**: i cinque `E_PROCESSO_*` li ha già rigenerati
   il BE con #1592 (9 occorrenze in `error_policies_generated.py`). ⇒ Il rosso residuo su
   `Tito-dev` è **tutto di questo lotto**, e lo chiude la quarta voce del punto 7;
7. ✅ **richieste a BE/FE** — **chiuse, verificate il 17-09 sera sui file di HEAD**: il BE
   ha chiuso le prime due con `6f786ed9f` (PR #1595, 15-09 16:45 UTC; **CI su `Tito-dev`
   verde**, e ancora verde al merge #1601 del 17-09): `E_MAG_*` rigenerati e coi ripieghi
   (2 occorrenze in ciascun modulo, classi uguali a `vw_codici_errore_identita`),
   `ambito_causale` via da `_REL_CONSENTITE` e da `CONFIG_TABLES` (0 occorrenze). La terza
   — chi valorizza `magazzini.emittente_fiscale_id` — è il building block
   `script.trgfn_default_emittente_fiscale` di
   [brief-db-emittente-di-default-un-bb-solo](brief-db-emittente-di-default-un-bb-solo.md):
   `20260915-43` **applicato il 17-09 alle 12:06** (`trg_magazzini_a10_default_emittente_ins`,
   `trg_assets_a10_default_emittente_ins` letti da `pg_trigger`), e il BE lo ha già
   rigenerato (`E_EMITTENTE_NON_RISOLTO` a policy). Resta la sola **`requires_lotto` in
   UI**, che è del Lotto 2 (§4.3) e non trattiene questo brief. Sotto, il testo del 15-09
   com'era — **verificato
   il 15-09 alle 17:10 con `grep`: tutte e quattro ancora aperte** (0 occorrenze di `E_MAG_`
   nei due moduli, `ambito_causale` ancora a riga 107 e 63, 0 `requires_lotto` in BE/FE):
   togliere
   `"magazzino.ambito_causale"` da `_REL_CONSENTITE` (`backend/apps/core/db/dbops_repository.py`)
   e la riga di `CONFIG_TABLES` (`frontend/src/core/config-tables.js`) — finché restano, la
   voce «Ambito Causale» del pannello risponde 500 (D-L1-g); esporre `requires_lotto`
   accanto a `requires_serial` col Lotto 2 (§4.3); decidere chi valorizza
   `magazzini.emittente_fiscale_id` dal pannello (§4.7); 🔴 **e la quarta, trovata alla
   verifica del 15-09 (15:30) — mancava**: `manage.py genera_error_policies` + una frase
   **senza segnaposto** per ciascuno dei due codici in `error_messages_fallback.py`
   (`E_MAG_MOVIMENTO_VERSO_INCOERENTE`, `E_MAG_TRASFERIMENTO_EMITTENTI_DIVERSI`) —
   `api.md` §Tassonomia: *registrare un codice nuovo = rigenerare il modulo e scrivere il
   ripiego*, presidiato da `test_ogni_codice_vivo_ha_un_messaggio_di_ripiego`. È la stessa
   rigenerazione già chiesta da `brief-db-avvio-manuale-di-un-processo` §9 per i cinque
   `E_PROCESSO_*`: **una corsa sola le copre entrambe**, ma i due ripieghi vanno scritti
   a mano e nessuno li avrebbe cercati qui. Verificato: 0 occorrenze di `E_MAG_` nei due
   moduli.

**Il bilancio della sera, in una riga per lezione** (le stesse sei righe di §5, perché il
Lotto 2 le legga prima di scrivere): un `DROP` per nome si verifica su `zeroerp_ci`, non su
dev (`MARK_RAN` del 2025); sotto RLS la policy scatta prima del `NOT NULL`; montare una
funzione orfana = censire il registro che la dichiarava; una fixture che cerca un dato di
macchina muore da zero; gli indici del passato sopravvivono alla rinomina; cambiare una riga
di catalogo = `grep` nei pgTAP. Tutte e sette le cose erano «verdi in catena» in sessione.

---
