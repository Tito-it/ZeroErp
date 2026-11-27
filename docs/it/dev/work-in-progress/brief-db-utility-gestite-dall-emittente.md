# Brief DB — Le utility gestite da ciascun emittente: serve un elenco per azienda?

## ⏭️ Chi riparte — aggiornato al 2026-11-27

**Riparte: la sessione DB**, col piano dei giri (§8): tutte le decisioni sono prese. L'analisi è fatta (§4), e Tid ha
deciso il 2026-11-27: **sì, l'elenco per azienda serve, e sta nella stessa tabella** `emittenti_fiscali_utilities`
(la riga accesa = l'utility è attiva per l'azienda; i parametri restano facoltativi). È un **cambio di modello**:
revoca la politica ibrida C del 2026-04-08 (§2). Nasce il 2026-11-27 dalla decisione D-T8c-8 di
[brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) (§25.5).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE (in lettura sulla doc DB) | L'analisi: i lettori, i casi, le strade, le guide | §4 | — |
| 2 | ✅ Tid | D-U-0 … D-U-9 decise il 2026-11-27 | §6 | — |
| 3 | sessione DB | Il piano dei giri: C1 prima, poi la tabella, il guard, il BB delle utility ammesse, l'allineamento | §8 | — |
| 4 | sessione DB | Le pagine marcate ⚠️ riscritte nel giro che costruisce | §7 | 3 |
| 5 | team BE/FE | Il censimento dei lettori e la tendina sul BB unico | §8 | 3 |
| 6 | sessione DB | Archiviazione | — | 4, 5 |

**Decisioni aperte di Tid:** nessuna.
**Da committare:** l'analisi e le decisioni (2026-11-27), e le note ⚠️ di §7.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-27. **A chi:** Tid e team DB.
> **Brief vicini verificati:**
> [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md): T8a S18d (`emittenti_fiscali_utilities.utility_id`
> `bigint` contro `config.utilities.id` `integer`, §25.2) e T8b S54b (`fn_parametri_importo_utility` con un ruolo che
> non è `EF`, §25.3) toccano la **stessa tabella**: si fanno lì, e se questo brief porta a cambiarla l'ordine si
> concorda. Il [registro dei residui](registro-residui-aperti.md), voce B-8 di `brief-db-modelli-documento-standard`:
> la matrice utility dell'emittente nell'interfaccia mostra solo l'override grezzo; se la tabella cambia significato
> anche quella forma cambia. [brief-incassi-riconciliazione-rate-promemoria](brief-incassi-riconciliazione-rate-promemoria.md)
> legge le soglie della tabella (la fattura minima): non dipende da chi gestisce l'utility, ma ne è lettore.
> Nessun brief aperto ha per tema le utility abilitate per azienda.
> **Guide da verificare** (`scripts/guide_coinvolte.py --oggetti`, 6 oggetti, 2026-11-27), l'esito lo scrive l'analisi:
> [emittenti-fiscali](../../guide/emittenti-fiscali.md) (2 oggetti), [automazione-db](../../guide/automazione-db.md),
> [configurazione-liste](../../guide/configurazione-liste.md), [generazione-cliente](../../guide/generazione-cliente.md),
> [gestione-dei-pagamenti](../../guide/gestione-dei-pagamenti.md),
> [gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md). Orfani: `fn_lookup_utilities_per_ba`
> e `script.fn_guard_utility_tipo_ruolo`, che nessuna guida cita.

## 1. La domanda

Un'azienda del gruppo (l'emittente fiscale) vende certe utility e non altre: una solo gas, un'altra energia e
fonia. Il modello di oggi non lo dice per azienda. La domanda è se debba dirlo, e con quale effetto: che cosa si
rifiuta, o non si mostra, quando un'azienda tratta un'utility che non gestisce.

## 2. Che cosa esiste, e che cosa è deciso

* **La decisione presa: la politica ibrida C** (in
  [refactor-operatore-emittenti](../work-done/2026/refactor-operatore-emittenti.md) §3.2, archiviato).
  `anagrafiche.emittenti_fiscali_utilities` resta un **override di parametri**, non una «whitelist di abilitazione».
  La tendina delle utility di un billing account mostra l'intersezione delle utility ammesse per il ruolo del
  soggetto e per il ruolo `EF` nella matrice di sistema, decorate con l'override dell'emittente quando c'è. Il limite
  è scritto lì: l'admin di un emittente non può togliere un'utility alla sua azienda, se non dalla matrice globale.
  ⚠️ Un elenco per azienda **revoca** questa decisione: è un cambio di modello.
  ⚠️ **Revocata da Tid il 2026-11-27** (D-U-0, D-U-1 in §6).
* **La matrice di sistema** `config.utilities_tipi_ruolo`: utility per tipo di ruolo, con periodo e `attivo`. Il
  COMMENT: «se assente per utility resta fail-open; se presente limita ai ruoli configurati». La leggono
  `script.fn_guard_utility_tipo_ruolo` (il guard, montato dall'automazione sulle tabelle del registro
  `dbops.automazione_guard_utility_tipo_ruolo`) e `anagrafiche.fn_lookup_utilities_per_ba` (la tendina).
* **Il registro del guard** (scratch, 2026-11-27): acceso su `emittenti_fiscali_utilities` e
  `categorie_clienti_listini`; spento su `clienti`, `bank_branches`, `fornitori`, `vettori` e su una riga che nomina
  `anagrafiche.reseller`, tabella che non esiste (è `resellers`): da vagliare nell'analisi.
* **La tabella dell'emittente** `anagrafiche.emittenti_fiscali_utilities`: una riga per coppia azienda e utility, coi
  decimali, il metodo di arrotondamento e le soglie della fattura minima; `attivo`; nessuno la crea da sé. La leggono
  `anagrafiche.fn_parametri_importo_utility` (i tre livelli dei parametri), quindi `vendite.fn_ricalcola_totali_fattura`
  e `fn_lookup_utilities_per_ba`. La pagina `manual/`: «una riga è un'eccezione, non una configurazione obbligatoria».
* **`config.utilities`** non ha `attivo`: un'utility non si spegne per il sistema.
* **Il precedente ritirato**: `anagrafiche.gestori_utilities` diceva, nella prima generazione (2025-05), quali utility
  erano attive sul sistema per il gestore, l'azienda che gestiva il software (ricordo di Tid, 2026-11-27). Si ritira
  con T8c: la domanda di sistema la tiene la matrice.

## 3. Dove un elenco per azienda morderebbe

Le tabelle con `utility_id` verso `config.utilities` (catalogo dello scratch, 2026-11-27), da leggere nell'analisi
una per una per sapere se hanno anche l'emittente, e quindi dove la coppia «azienda e utility» si potrebbe giudicare:
`billing_account`, `clienti`, `pdp`, `istanze_dati_precontrattuali`, `categorie_clienti_listini` in `anagrafiche`;
`contratti`, `contratti_utilities`, `offerte_commerciali`, `offerte_commerciali_utilities`, `preventivi`, `ordini`,
`ddt`, `resi`, `commesse`, `listini`, `registri_fatturazione`, `fatturazione_lotti`, `fatturazione_pipeline`,
`fatture`, `fatture_arrotondamenti_scope`, `fatture_fondi_fattura_source` in `vendite`; `categoria_accisa`,
`tipi_utenze`, `listini_tipologie_utilities` in `config`.

## 4. L'analisi da fare

> ✅ **Fatta il 2026-11-27**, i risultati in §4-bis. Fatta dalla sessione BE sulla doc auto-generata e sul CSV
> del registro, senza interrogare il DB: chi costruisce rilegge i corpi dal catalogo se un changeSet è più
> recente della doc.

* [x] I lettori di `emittenti_fiscali_utilities` e della matrice, con il significato su cui contano (una riga =
      eccezione): se la riga diventasse anche «abilitazione», chi cambierebbe comportamento (regola della garanzia
      ritirata, `.codex/AGENTS.md`)
* [x] Per ogni tabella di §3: ha l'emittente (diretto o dal billing account)? Dove nasce la coppia, e chi la sceglie
* [x] I casi del modello, costruiti e non misurati: un'azienda nuova senza righe (oggi fattura tutto); un'utility
      tolta a un'azienda che ha già contratti, listini o fatture aperte di quell'utility; un billing account che
      passa a un'altra azienda (giro 6: il BA è sempre collegato, la storia dell'emittente); la madre plurale
* [x] Le strade, con quello che ciascuna rompe: (a) com'è, e il limite si scrive nella guida; (b) la stessa tabella
      diventa anche l'elenco, con una colonna o con «riga presente = gestita»; (c) una tabella nuova
      dell'abilitazione, separata dai parametri; (d) il registro del guard esteso ai documenti, con la coppia
      azienda e utility
* [x] Le guide di testata, ciascuna con il suo esito; la decisione C citata con la sua data
* [x] La ricaduta sul BE e sul FE (la tendina, la matrice di B-8, i drawer del cliente e del fornitore) come
      richiesta, senza leggere `backend/`

## 5. Le decisioni per Tid (dopo l'analisi)

> ⚠️ Le domande sono decise il 2026-11-27: le risposte, e quelle nate dall'analisi, sono in §6.

* **D-U-0**: l'elenco delle utility per azienda serve? No: la decisione C resta, e il limite si scrive. Sì: le altre.
* **D-U-1**: dove sta l'elenco (strade b, c, d di §4).
* **D-U-2**: un'azienda senza righe gestisce tutto (aperta) o niente (chiusa)?
* **D-U-3**: che cosa succede togliendo un'utility a un'azienda che ha documenti vivi di quell'utility.
* **D-U-4**: dove si giudica la coppia: solo alla nascita del billing account e del cliente, o anche su ogni documento.
* **D-U-5**: chi la scrive: il SUPER_ADMIN, l'admin dell'emittente, il pannello di configurazione.

## 4-bis. Che cosa ha trovato l'analisi (2026-11-27)

### Oggi le utility di un emittente sono le stesse per tutti

La matrice `config.utilities_tipi_ruolo` si legge per **tipo** di ruolo, e il tipo `EF` è uno solo: ciò che è
ammesso per `EF` è ammesso per ogni azienda. `emittenti_fiscali_utilities` è per azienda, ma porta solo i
parametri d'importo.

### Tre difetti che ci sono già

* **C1 — la stessa matrice letta in due modi opposti.** `script.fn_guard_utility_tipo_ruolo` è *fail-open*
  (un'utility senza righe nella matrice è aperta a tutti i ruoli); `anagrafiche.fn_lookup_utilities_per_ba` fa
  un `JOIN` interno sulla matrice, per il ruolo del soggetto e per `EF`, ed è *fail-closed* (quell'utility non
  compare). Lo stesso fa il lookup del BE `utilities-per-emittente`, stando alla sua pagina `manual/`.
  Un'utility senza righe si scrive ma non si vede. Deciso in D-U-7.
* **C2 — la regola «ammesse per `EF` e per il ruolo del soggetto» in tre sedi**: la funzione DB
  `fn_lookup_utilities_per_ba`, il lookup del BE (`LookupRepository.list_utilities_per_emittente`) e la matrice
  del drawer dell'emittente (`LookupRepository.list_entity_utility_matrix`), dalle pagine `manual/` del BE.
  Regola del 2: va estratta in un BB DB, e le copie si ritirano nello stesso giro (§8).
* **C3 — il registro del guard** (`80_data/sql/dbops/automazione_guard_utility_tipo_ruolo.csv`): acceso su
  `emittenti_fiscali_utilities` e `categorie_clienti_listini`; spento su `clienti`, `bank_branches`,
  `fornitori`, `vettori` e `reseller`, tabella che non esiste (è `resellers`, e non ha `utility_id`). Da
  pulire, nel giro del guard o in [brief-db-reseller](brief-db-reseller.md) per la sua riga.

### ⚠️ Una correzione: la strada (b) non era «già fallita»

È entrata due volte in modo implicito: il guard «almeno una riga per emittente», tolto dal changeSet
`20260408-01`, e il lookup del BE che fino al 2026-10-14 usava la tabella come elenco (un emittente coi soli
parametri della luce perdeva il gas: `work-done/2026/analisi-be-difetti-emersi-verifica-doc-api-core.md`). In
tutti e due i casi il difetto era l'**incoerenza** fra il significato dichiarato («una riga è un'eccezione») e
un lettore che la usava come elenco, non l'idea. Con la decisione esplicita di §6 il significato cambia per
tutti i lettori insieme (§7-bis).

### Dove la coppia «azienda e utility» si giudica

L'utility del billing account è immutabile (`trgfn_lock_columns`), e i documenti la ereditano per costruzione:
FK composta col BA su `clienti`, `istanze_dati_precontrattuali`, `contratti`, `offerte_commerciali`,
`preventivi`, `ordini`, `ddt` e `resi` (questi due dall'ordine e dal DDT). Le righe di contratto e offerta
seguono il padre. Hanno invece utility ed emittente senza passare dal BA: `vendite.listini`, `commesse` (nessuna
FK composta), `fatture` (utility nullable, nessuna FK col BA), `registri_fatturazione` e `fatturazione_lotti`
(utility nullable), `anagrafiche.categorie_clienti_listini`, e la stessa `emittenti_fiscali_utilities`.
`acquisti` e `magazzino` non hanno `utility_id`. Le tabelle di `config` (`categoria_accisa`, `tipi_utenze`,
`listini_tipologie_utilities`) e `fatturazione_pipeline` non hanno l'emittente: non si giudicano.

Il cambio d'azienda del BA è ammesso solo senza documenti, e ha già quattro cancelli (storia, albero, istanza,
chiave del cliente: `dbzero/anagrafiche/_emittente-del-billing-account.md`): l'utility gestita è il quinto.

### Le guide

| Guida | Esito |
| --- | --- |
| [emittenti-fiscali](../../guide/emittenti-fiscali.md) §«Le utilities: le eccezioni d'importo» | **contraddetta**: cambio di modello, deciso da Tid il 2026-11-27 (§6), revoca C del 2026-04-08. Marcata ⚠️, si riscrive nel giro (§7) |
| [configurazione-liste](../../guide/configurazione-liste.md) §11.1 («le stesse per ogni operatore») | **contraddetta**, idem |
| [automazione-db](../../guide/automazione-db.md) (registro del guard) | **guida indietro** nel giro del guard: il secondo livello e le righe di C3 |
| [gestione-dei-pagamenti](../../guide/gestione-dei-pagamenti.md) (le soglie della fattura minima) | coerente: le soglie restano parametri facoltativi della riga |
| [generazione-cliente](../../guide/generazione-cliente.md), [gestione-delle-istanze-utility](../../guide/gestione-delle-istanze-utility.md) | coerenti: citano `config.utilities` per `richiede_pdp`, non ne dipendono |

Orfani: `anagrafiche.fn_lookup_utilities_per_ba` e `script.fn_guard_utility_tipo_ruolo`. Sono il concetto
«utility ammesse», che è di dominio: vanno almeno nel «Vedi anche» di emittenti-fiscali; se serve una guida
propria lo decide Tid.

## 6. Le decisioni di Tid (2026-11-27)

* **D-U-0 — sì**: l'elenco delle utility per azienda serve. Revoca la politica ibrida C
  ([refactor-operatore-emittenti](../work-done/2026/refactor-operatore-emittenti.md) §3.2, 2026-04-08).
* **D-U-1 — strada (b)**: l'elenco sta in `anagrafiche.emittenti_fiscali_utilities`. La riga accesa vuol dire
  «l'azienda gestisce l'utility»; i parametri d'importo restano facoltativi sulla stessa riga. Una sede sola.
* **D-U-2 — chiusa**: un'azienda senza righe non gestisce nessuna utility.
* **D-U-3 — un'utility attivata non si spegne**: la riga si spegne **solo insieme all'emittente** (scelta (i)).
* **D-U-4 — dove si giudica**: alla nascita del collegamento del billing account con l'azienda, al cambio
  d'azienda del BA (quinto cancello), e sulle tabelle con l'emittente diretto di §4-bis. Non su ogni documento:
  quelli legati al BA ereditano l'utility per costruzione.
* **D-U-5 — chi scrive**: il SUPER_ADMIN.
* **D-U-7 (nata dall'analisi, C1) — «senza righe = nessun ruolo»**: un'utility senza righe nella matrice
  `config.utilities_tipi_ruolo` non è ammessa per nessuno. Il guard diventa *fail-closed* come la tendina. E
  **l'uscita di un'utility dalla matrice per il ruolo `EF` è rifiutata finché qualche azienda la tiene attiva.**
* **D-U-8 (nata dall'analisi) — la nascita di un'azienda**: alla creazione il drawer propone le utility da
  attivare (scelta (b)). L'attivazione resta un atto esplicito del SUPER_ADMIN.
* **D-U-9 (nata dall'analisi) — l'utility attivata per errore**: si **cancella** finché l'azienda non ha nessun
  billing account e nessun documento di quell'utility. Non è una disattivazione: corregge una scrittura senza
  conseguenze. Dopo, il DELETE è rifiutato.
* **D-U-6 — la riaccensione dell'azienda**: con D-U-3 le righe si spengono con l'azienda; quando l'azienda si
  riaccende, **si riaccendono tutte insieme**, da sole. Lo spegnimento e la riaccensione della riga seguono
  l'emittente, e solo lui.

## 7. I documenti che dicevano «la tabella non è l'elenco»

Marcati ⚠️ il 2026-11-27 con un rimando a questo brief: descrivono ancora il funzionamento **di oggi**, che resta
vero finché il giro DB non è applicato. Si **riscrivono** nel giro che costruisce, non prima.

* `docs/it/dbzero/anagrafiche/manual/emittenti_fiscali_utilities.md` — §«Una riga è un'eccezione»
* `docs/it/guide/emittenti-fiscali.md` — §«Le utilities: le eccezioni d'importo»
* `docs/it/guide/configurazione-liste.md` — §11.1
* `docs/it/backend/core/manual/api_lookup_dedicati.md` §4 e `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md`
  (la nota della tendina e §6.1): li riscrive il team BE/FE quando la tendina passa al BB
* `docs/it/dev/work-done/2026/refactor-operatore-emittenti.md` §3.2 — archiviato: la decisione C resta come
  storia, marcata revocata

### 7-bis. Garanzie ritirate

| Oggetto | La proprietà che i lettori davano per scontata | Lettori lato DB |
| --- | --- | --- |
| `emittenti_fiscali_utilities`, riga presente | «la riga c'è = l'azienda ha personalizzato i parametri» | `fn_parametri_importo_utility` (`personalizzata = e.id IS NOT NULL`): **va adeguato**, diventa «almeno un parametro valorizzato»; `fn_lookup_utilities_per_ba` (`is_personalizzata_per_ef`, lo prende da lì): segue; `vendite.fn_ricalcola_totali_fattura`: legge i valori effettivi, non il flag, da verificare nel giro |
| `arrotondamento_importi_dec`, `metodo_arrotondamento_importi` NOT NULL | «la riga decide decimali e metodo» | `fn_parametri_importo_utility`: regge, fa già `COALESCE` con policy e sistema; da provare col caso costruito della riga senza parametri |
| `attivo` della riga | «spenta = eccezione tolta, tornano i parametri di sistema» | cambia significato: spenta = utility non gestita (solo con l'emittente). Lettori: `fn_parametri_importo_utility`, `trgfn_child_requires_active_parent`, il blocco di spegnimento dell'emittente |
| la matrice `utilities_tipi_ruolo`, utility senza righe | «aperta a tutti i ruoli» (guard) | `script.fn_guard_utility_tipo_ruolo` **va adeguato**; i trigger del registro lo seguono |

Richiesta al team BE/FE: **censisci i lettori di `emittenti_fiscali_utilities` che contano su «riga presente =
parametri personalizzati»** (noti: la matrice del drawer, dove `record_id` null vuol dire «non configurata»; il
lookup `utilities-per-emittente`), e i lettori di `config.utilities_tipi_ruolo` che contano su «senza righe =
tutti».

## 8. Il piano dei giri (da scrivere dalla sessione DB)

1. **C1, la matrice coerente** (D-U-7): il guard *fail-closed*; il rifiuto dell'uscita di un'utility da `EF`
   con aziende che la tengono attiva. Prima del resto: il livello dell'azienda poggia su una matrice coerente.
2. **La tabella** (D-U-1, D-U-3, D-U-9): parametri nullable, `personalizzata` riscritto, `utility_id` ed
   emittente bloccati, DELETE solo senza BA né documenti, `attivo` che segue l'emittente nei due versi (D-U-3, D-U-6: si spegne e si riaccende con lui).
3. **Il guard di secondo livello** (D-U-4): sul registro esistente, quando il soggetto-ruolo è un `EF` si
   controlla anche la riga accesa dell'azienda; il quinto cancello del cambio d'azienda del BA; il registro
   esteso alle tabelle con l'emittente diretto di §4-bis, e le righe di C3 ripulite.
4. **Il BB delle utility ammesse** (C2): una funzione DB unica per BA e per emittente; richiesta al BE/FE di
   leggere solo lei e ritirare le due copie applicative, nello stesso giro.
5. **L'allineamento**: ogni azienda attiva ogni utility su cui ha già billing account o documenti. È la
   condizione di coerenza del modello (D-U-2 chiusa), non una scelta presa dai dati.
6. **La ricaduta FE** (D-U-5, D-U-8): il drawer «Gestisci utilities» diventa «attiva sì o no, più i parametri»
   (chiude B-8 del [registro dei residui](registro-residui-aperti.md)); la proposta delle utility alla nascita
   dell'azienda.
