# Brief DB — Le utility gestite da ciascun emittente: serve un elenco per azienda?

## ⏭️ Chi riparte — aggiornato al 2026-11-28

**Riparte: il team BE/FE**, con la richiesta di §10. Tid, in parallelo: la corsa su dbdev di `ui/test-fn-preset-di-base-v1`, corretto il 2026-11-28 (§8-bis, coda dei giri; da committare). Il lato DB è finito: U1 … U4 applicati e committati (2026-11-27); alla fine, l'archiviazione. La richiesta resta qui, §10: nessun brief nuovo. Le decisioni sono in §6 (D-U-0 … D-U-13).
⚠️ Il resto di questo paragrafo è del mattino. L'analisi è fatta (§4), e Tid ha
deciso il 2026-11-27: **sì, l'elenco per azienda serve, e sta nella stessa tabella** `emittenti_fiscali_utilities`
(la riga accesa = l'utility è attiva per l'azienda; i parametri restano facoltativi). È un **cambio di modello**:
revoca la politica ibrida C del 2026-04-08 (§2). Nasce il 2026-11-27 dalla decisione D-T8c-8 di
[brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) (§25.5).

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE (in lettura sulla doc DB) | L'analisi: i lettori, i casi, le strade, le guide | §4 | — |
| 2 | ✅ Tid | D-U-0 … D-U-9 decise il 2026-11-27 | §6 | — |
| 2-bis | ✅ sessione DB | La verifica critica dell'analisi e del piano sul catalogo | §9 | — |
| 2-ter | ✅ Tid | D-U-10 (a), D-U-11 (a), D-U-12 (a), decise il 2026-11-27 | §6 | — |
| 3 | ✅ sessione DB | U1 scritto e provato sullo scratch | §8-bis | — |
| 3-bis | ✅ Tid | L'apply di U1, i pgTAP, la doc rigenerata, B-7 (2026-11-27) | §8-bis | — |
| 3-ter | ✅ sessione DB | U2 scritto e provato sullo scratch; D-U-13 deciso | §8-bis | — |
| 3-quater | ✅ Tid | L'apply di U2, pgTAP, doc rigenerata; B-7 (sessione DB) (2026-11-27) | §8-bis | — |
| 3-quinquies | ✅ sessione DB | U3 scritto e provato sullo scratch | §8-bis | — |
| 3-sexies | ✅ Tid | L'apply di U3, i pgTAP, la doc rigenerata; B-7 (sessione DB) (2026-11-27) | §8-bis U3 | — |
| 3-septies | ✅ sessione DB | U4 scritto e provato sullo scratch; la richiesta al BE/FE scritta | §8-bis U4, §10 | — |
| 3-octies | ✅ Tid | L'apply di U4, i pgTAP, la doc rigenerata; B-7 (sessione DB) (2026-11-27) | §8-bis U4 | — |
| 3-nonies | ✅ sessione DB | Il commit dei quattro giri, su richiesta di Tid (2026-11-27); `/verifica-db` non lanciato | — | — |
| 4 | ✅ sessione DB | Le pagine marcate ⚠️ riscritte nei giri U2 … U4; restano al BE `configurazione-liste` §11.1 e le due pagine `manual/` del BE | §7, §10 R-5 | — |
| 5 | team BE/FE | La richiesta: censimento dei lettori, tendina e drawer sul BB, traduzione dei vincoli | §10 | 3-nonies |
| 6 | sessione DB | Archiviazione | — | 5 |

**Decisioni aperte di Tid:** nessuna.
**Da committare:** niente (commit locale del 2026-11-27, non ancora pushato).

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-27. **A chi:** Tid, team DB e (§10) team BE/FE.
> **Brief vicini verificati:**
> ⚠️ **S18d e S54b sono già fatti** (verificato sul catalogo dello scratch, 2026-11-27): `utility_id` è `integer`
> (`20261127-13`), `fn_parametri_importo_utility` rifiuta un ruolo che non è un emittente (`20261126-87`). Nessun
> ordine da concordare: i giri di questo brief partono dai corpi attuali.
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
  ⚠️ Precisata da D-U-11: la riga non si spegne affatto; «gestita» = riga presente ed emittente acceso.
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
* ⚠️ **D-U-6 superata da D-U-11** (Tid, 2026-11-27): non c'è niente da riaccendere, la riga non ha uno stato suo.
  Il testo resta come storia.
* **D-U-6 — la riaccensione dell'azienda**: con D-U-3 le righe si spengono con l'azienda; quando l'azienda si
  riaccende, **si riaccendono tutte insieme**, da sole. Lo spegnimento e la riaccensione della riga seguono
  l'emittente, e solo lui.
* **D-U-10 — (a)** (Tid, 2026-11-27, §9 V1): la matrice `config.utilities_tipi_ruolo` ha un seed caricato, con
  le righe `EF` e dei ruoli dei soggetti per ogni utility del catalogo.
* **D-U-11 — (a)** (Tid, 2026-11-27, §9 V3): la riga non ha uno stato suo. «Gestita» = riga presente ed emittente
  acceso; i lettori leggono l'`attivo` dell'emittente. D-U-7 conta le righe presenti.
* **D-U-12 — (a)** (Tid, 2026-11-27, §9 V5): la coppia azienda e utility si giudica con FK composte verso
  `emittenti_fiscali_utilities (emittente_soggetto_ruolo_id, utility_id)`, differite; sul collegamento del BA
  entra `utility_id`, legato al BA da una FK composta.
* **D-U-13 — il blocco resta** (Tid, 2026-11-27, nato nel giro U2): un'azienda con righe non si spegne
  (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`, blocco generato dall'automazione ATTIVO). Con D-U-11 la riga è sempre
  accesa: un'azienda che gestisce un'utility si spegne solo dopo aver cancellato le sue righe, ammesso senza
  billing account né documenti (D-U-9); riaccesa, le utility si riattivano a mano. Un'azienda con billing account
  non si spegneva già (il collegamento del BA non ha `attivo`, e il blocco conta ogni riga). Scartata l'eccezione
  sulla FK in `automazione_attivo_eccezioni`. ⚠️ Con D-U-11 e D-U-13, D-U-3 («si spegne solo con l'emittente») non
  ha più un caso: la riga non si spegne mai.

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

> ⚠️ **Superato dalla verifica critica (§9)** e dalle decisioni D-U-10 … D-U-12: il piano che vale è §8-bis.
> Resta come storia.

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

## 8-bis. Il piano a spunta (2026-11-27, dopo D-U-10 … D-U-12)

Nessun seed di `80_data` ha righe con emittente e utility (billing account, listini, commesse, righe
dell'emittente): l'allineamento di V6 riguarda **dbdev** e i **fixture pgTAP**, non i CSV.

* [x] Verifica critica sul catalogo, decisioni D-U-10 … D-U-12 (2026-11-27, §9, §6)
* **U1 — la matrice coerente** (D-U-7, D-U-10, V1, V2)
  * [x] Il censimento dei pgTAP (2026-11-27): 29 file nominano gli oggetti; scrivono la matrice solo
        `script/test-guard-utility-tipo-ruolo` (cancellava la matrice della prima utility per provare il
        *fail-open*: riscritto, l'utility senza righe si costruisce nuova), `anagrafiche/test-fn-lookup-utilities-per-ba`
        e `vendite/test-parametri-importo-utility-v1` (aggiungono righe, reggono). Gli altri scrivono righe
        dell'emittente o listini per categoria con le utility del catalogo, che col seed hanno la riga `EF`.
        Nessun pgTAP crea un'utility che poi un'azienda gestisce; nessun seed di `80_data` scrive le due tabelle
  * [x] pgTAP nuovo `config/test-utilities-tipi-ruolo-guard-uscita-ef-v1` (14): montaggio, data di fine, gesti
        liberi senza aziende, i quattro gesti rifiutati con un'azienda, il ritocco che passa, le righe degli
        altri ruoli non giudicate, il seed (2026-11-27)
  * [x] `utilities_tipi_ruolo.csv` riscritto sulla chiave naturale, senza `id` (righe `EF` e `CL` per ogni utility,
        `FO` per energia, gas e acqua; gas riacceso), caricato da `80_data/20261127-33`, **primo impianto per riga**
        (Tid, 2026-11-27): riga 7 di `automazione_seed_primo_impianto.csv`, lucchetto su `utility_id` e
        `tipo_ruolo_id` in `automation_lock_columns.csv` (2026-11-27)
  * [x] `20_code/script/20261127-31`: `script.fn_guard_utility_tipo_ruolo` *fail-closed*, COMMENT della matrice;
        `20_code/config/20261127-32`: `config.trgfn_utilities_tipi_ruolo_guard_uscita_ef`, fase `a12` dopo il
        lucchetto; codici `E_UTILITY_EF_GESTITA` (CONFLITTO_STATO) ed `E_UTILITY_EF_SENZA_SCADENZA` (DATO_ERRATO),
        messaggi 1569 e 1570 (2026-11-27).
        ⚠️ **Una precisazione di V2, costruita così**: la riga `EF` non ha **mai** data di fine, gestita o no. Una
        data di fine messa prima che un'azienda attivi l'utility la farebbe uscire da sola dopo: il divieto sulla
        sola riga gestita non lo vede. **Confermata da Tid il 2026-11-27**: su ogni riga `EF`
  * [x] Prova sullo scratch (2026-11-27), con il seed e i due codici simulati in un file dello scratchpad (un
        `loadUpdateData` non ha SQL da estrarre): il pgTAP nuovo 0 → 14 ok; `test-guard-utility-tipo-ruolo`
        9 ok / 1 not ok → 10 ok (il rosso senza estratto è il test 4, che ora asserisce il rifiuto); invariati e
        verdi `test-fn-lookup-utilities-per-ba`, `test-parametri-importo-utility-v1`,
        `test-automazione-guard-utility-tipo-ruolo` e gli undici che scrivono righe dell'emittente o listini per
        categoria. Guardrail dei changeSet verdi
  * [x] Doc scritta a mano: `automazione-db` §4.6, le pagine `manual/` della matrice e del guard (2026-11-27)
  * [x] Apply (Tid), pgTAP verdi, doc auto-generata rigenerata (2026-11-27)
  * [x] B-7 (2026-11-27, scratch): 213 codici, zero accumuli e zero restringimenti. I tre codici del giro sono fuori dalla baseline: `dbops.vw_codici_errore_forme_condizione` legge le loro condizioni come `IGNOTO`. Nessuna riga da cambiare
        ⚠️ Su dbdev la prima corsa del seed riscrive anche le righe EF già configurate (stessi valori) e riaccende
        GAS-FO; dbdev ha billing account TEL ed ENE, utility che nessuna azienda ha fra le sue righe: è
        l'allineamento di U3
  * [ ] Richiesta al BE (con U4): `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md` (righe 84 e 635)
        dice ancora «fail-open»
* **U2 — la tabella** (D-U-1, D-U-11, D-U-13, §7-bis)
  * [x] Censimento dei lettori lato DB (catalogo, `pg_get_functiondef`, 2026-11-27): leggono la tabella
        `anagrafiche.fn_parametri_importo_utility` (si adegua), `vendite.fn_ricalcola_totali_fattura` (solo `%TYPE`
        delle variabili: i valori li prende dal BB, regge), `config.trgfn_utilities_tipi_ruolo_guard_uscita_ef`
        (conta le righe, non ne dipende); nessuna vista. Nessun default sui due parametri. Nessun seed e nessuna
        funzione la scrivono; nessun pgTAP la spegne o ne sposta la chiave
  * [x] `00_schema/anagrafiche/20261127-34`: decimali e metodo nullable; `chk_emittenti_fiscali_utilities_attivo`
        (`attivo IS TRUE`); COMMENT della tabella e delle tre colonne. `attivo` resta: porta l'automazione ATTIVO
        nei due versi (D-U-13)
  * [x] Lucchetto su `emittente_soggetto_ruolo_id` e `utility_id` (`automation_lock_columns.csv`,
        `E_CODICE_NON_MODIFICABILE`)
  * [x] `20_code/anagrafiche/20261127-35`: `fn_parametri_importo_utility`, `personalizzata` = almeno un parametro
        (`num_nonnulls`), cade `e.attivo IS TRUE`; resta `BEGIN ATOMIC`, firma invariata, testata coi `%TYPE`
  * [x] pgTAP `vendite/test-parametri-importo-utility-v1` da 14 a 20: le colonne facoltative, la riga senza
        parametri (valori di sistema, non personalizzata), la riga con le sole soglie (personalizzata), il `CHECK`,
        il lucchetto (comportamento e registro)
  * [x] Prova sullo scratch (2026-11-27), col lucchetto simulato nello scratchpad (righe del registro e runner):
        il pgTAP dei parametri 14 ok / 1 not ok (interrotto) → 20 ok (senza estratto si ferma al 16, il `NOT NULL`
        di oggi); invariati e verdi gli altri 20 pgTAP che leggono la tabella, i parametri, il lookup o il ricalcolo.
        ⚠️ `config/test-utilities-tipi-ruolo-guard-uscita-ef-v1` ha un rosso in tutte e due le corse, il 10: la prova
        gira da proprietario, cioè come il migratore, e le righe che il test scrive nascono «dal seed»; la loro
        cancellazione la ferma per primo il seed di primo impianto (`E_SEED_RIGA_NON_CANCELLABILE`). Come app
        (il runner) è verde
  * [x] La pagina `manual/` della tabella riscritta (§7, 2026-11-27)
  * [x] Apply (Tid), pgTAP verdi, doc auto-generata rigenerata (2026-11-27); B-7 sullo scratch: zero accumuli,
        zero restringimenti, nessuna riga da cambiare (U2 non porta codici nuovi)
  * [ ] Richiesta al BE (con U4): il drawer «Gestisci utilities» scrive decimali e metodo come obbligatori, può
        spegnere la riga (ora `23514` su `chk_emittenti_fiscali_utilities_attivo`, da aggiungere alla mappa dei
        `CHECK` del service), e cancella la riga per «togliere l'override»: ora toglie l'utility all'azienda. La
        matrice del drawer legge `record_id` null come «non configurata» e `is_personalizzata_per_ef` cambia
        significato (§7-bis)
* **U3 — le FK composte** (D-U-4, D-U-9, D-U-12, V4, V5, V6)
  * [x] **Allineamento fatto il 2026-11-27** dalla sessione DB, su richiesta di Tid, dopo un primo apply di `-36`
        fermato (annullato per intero) dalla riga mancante PGTAPEF202 TEL: dbdev 6 righe, scratch 1 più le utility
        ammesse per PGTR0001 (ora ACQ, BASE, ENE, GAS, TEL). La verifica in lettura dà zero righe mancanti su
        tutti e due.
  * [x] ~~Allineamento di dbdev, a mano (Tid), prima dell'apply~~ (sopra): le FK si convalidano alla nascita, e un'azienda
        senza la riga di un'utility dei suoi BA o documenti ferma il changeSet `-36` o `-38`. Su dbdev (2026-11-27,
        fatto datato) mancano 6 righe, tutte di aziende accese: DEVA BASE, DEVB BASE ed ENE, EMITEST BASE,
        PGTAPEF202 ENE e TEL. Sullo scratch manca PGTR0001 ENE; PGTR0001 è un'azienda di fixture rimasta, e la
        fixture nuova le darebbe ogni utility ammessa (la prova le ha dato quelle). La query, prima in lettura:

        ```sql
        WITH usate AS (
            SELECT l.emittente_soggetto_ruolo_id AS e, ba.utility_id AS u
              FROM anagrafiche.emittenti_fiscali_billing_account l
              JOIN anagrafiche.billing_account ba ON ba.id = l.billing_account_id
            UNION SELECT emittente_soggetto_ruolo_id, utility_id FROM anagrafiche.categorie_clienti_listini
            UNION SELECT emittente_soggetto_ruolo_id, utility_id FROM vendite.listini
            UNION SELECT emittente_soggetto_ruolo_id, utility_id FROM vendite.commesse
            UNION SELECT emittente_soggetto_ruolo_id, utility_id FROM vendite.fatture
            UNION SELECT emittente_soggetto_ruolo_id, utility_id FROM vendite.registri_fatturazione
            UNION SELECT emittente_soggetto_ruolo_id, utility_id FROM vendite.fatturazione_lotti)
        INSERT INTO anagrafiche.emittenti_fiscali_utilities (emittente_soggetto_ruolo_id, utility_id)
        SELECT DISTINCT e, u FROM usate WHERE u IS NOT NULL
        ON CONFLICT (emittente_soggetto_ruolo_id, utility_id) DO NOTHING;
        ```
  * [x] `00_schema/anagrafiche/20261127-36`: `uq_billing_account_id_utility (id, utility_id)`; `utility_id` sul
        collegamento, riempito dal BA coi trigger sospesi per nome, `chk_emittenti_fiscali_ba_utility` (NULL solo
        sulla riga predefinita), FK composta col BA; FK differite verso la riga dell'azienda dal collegamento e da
        `categorie_clienti_listini` (2026-11-27)
  * [x] `20_code/anagrafiche/20261127-37`: il collegamento nasce con l'utility del suo BA
        (`trgfn_emittenti_fiscali_ba_set_utility`, `a20`), letta da proprietario
        (`fn_utility_del_billing_account`, DEFINER: il BA appena nato può non essere ancora nel perimetro di chi
        scrive). Nessuna modifica ai due scrittori (`trgfn_billing_account_link_ef`, `fn_crea_billing_account`):
        la colonna la deriva il database. Lucchetto su `utility_id` (`automation_lock_columns.csv`)
  * [x] `00_schema/vendite/20261127-38`: FK differite da `listini`, `commesse`, `fatture`,
        `registri_fatturazione`, `fatturazione_lotti`; `MATCH SIMPLE`, quindi una riga senza utility non si
        giudica (i registri «per tutte le utility» del provisioning nascono così)
  * [x] Il rifiuto (2026-11-27): una violazione di FK arriva al backend come `23503` col nome del vincolo, e il
        BE la traduce per nome (come fa già coi vincoli della tabella): i sette nomi `fk_…_utility_gestita` vanno
        nella richiesta al BE. Nessun codice di dominio nuovo
  * [x] Indici: `SENZA_INDICE` per le sette FK (`fk_index_policy.csv`): il padre si cancella solo per correggere
        (D-U-9). Le FK composte restano fuori dall'automazione ATTIVO (automazione-db §4.2)
  * [x] Le aziende dei pgTAP nascono tutte da `dbops.fn_pgtap_crea_emittente`, anche quella del contesto
        operatore di default: `20_code/dbops/20261127-39` le fa gestire ogni utility ammessa oggi per `EF`, senza
        parametri (il verbo di dominio non le attiva, D-U-8). `20_code/anagrafiche/20261127-40`: i dati di
        sviluppo (`fn_provisiona_dati_di_sviluppo`) attivano `BASE` per DEVA e DEVB
  * [x] pgTAP nuovo `anagrafiche/test-utility-gestita-fk-v1` (10): la forma delle sette FK, la riga predefinita,
        il BA su un'utility gestita e la sua utility sul collegamento, la cancellazione con e senza BA, il BA e il
        listino su un'utility non gestita, il cambio d'azienda, il lucchetto. Adeguati: i test che inserivano a
        mano la riga dell'emittente ora la completano (`test-parametri-importo-utility-v1`,
        `test-fondi-fattura-governo`, `test-nc-rata-unica-v1`, `test-numerazione-guard-coerenza-v1`,
        `test-stati-doc-fiscale-congela-fiscale`); `test-numero-prefisso-registro-v1` dà all'azienda che cerca le
        due utility del test; `test-fn-crea-emittente-fiscale-v1` (14) cerca la tabella dell'azienda con `\M`,
        non `emittenti_fiscali_utilities`
  * [x] Prova sullo scratch (2026-11-27), con l'allineamento e il lucchetto simulati: 63 pgTAP mirati (chi nomina
        la riga dell'emittente, il collegamento, i listini per categoria, la creazione di BA ed emittenti), nessuna
        regressione. I rossi presenti anche senza U3 restano gli stessi (`test-distinta-numerazione-registro-v1` 2,
        `test-rls-billing-account-returning-secondo-emittente` 1, `test-lista-colonna-vuoto-ordinato-come-massimo-v1`
        1, `test-numero-prefisso-registro-v1` 1, `test-utilities-tipi-ruolo-guard-uscita-ef-v1` 1: la prova gira da
        proprietario). ⚠️ U3 tocca ogni pgTAP che crea un billing account: la suite intera la lancia Tid dopo l'apply
  * [x] Guide (2026-11-27): `emittenti-fiscali` §«Le utilities che l'azienda gestisce» riscritta (era ⚠️ in §7) e
        «Vedi anche» con gli orfani; `generazione-cliente` §Billing account (guida indietro: il BA nasce solo su
        un'utility gestita); la nota `_emittente-del-billing-account.md` (il quinto cancello, l'utility del
        collegamento); la pagina `manual/` della tabella (chi usa la riga). Coerenti: `gestione-listini`,
        `fatturazione`, `gestione-commesse`, `gestione-delle-istanze-utility`, `soggetti-e-ruoli-anagrafici`,
        `_chiave-unica-cliente.md` (nominano gli oggetti per altro)
  * [x] Registro del guard (C3): la riga di `reseller` resta a [brief-db-reseller](brief-db-reseller.md)
  * [x] Apply (Tid), pgTAP verdi, doc auto-generata rigenerata (2026-11-27); B-7 sullo scratch: zero accumuli,
        zero restringimenti (U3 non porta codici nuovi: i rifiuti sono `23503` delle FK)
  * [ ] Richiesta al BE (con U4): i sette nomi `fk_…_utility_gestita` nella traduzione dei vincoli (`23503` →
        «l'azienda non gestisce questa utility», sulla cancellazione «la riga è usata»); il drawer del cliente non
        propone utility che l'azienda non gestisce
* **U4 — il BB delle utility ammesse e la chiusura** (C2, §7, §7-bis)
  * [x] `20_code/anagrafiche/20261127-41`: `anagrafiche.fn_utilities_emittente(emittente, ruolo del soggetto
        facoltativo)`, sede unica della regola: una riga per utility ammessa oggi per `EF` (e per il ruolo, se
        dato), con `gestita` (riga presente, azienda accesa), `riga_id` e i parametri effettivi; un ruolo che non è
        un emittente è `E_PARAMETRO_INVALIDO` (2026-11-27)
  * [x] `20_code/anagrafiche/20261127-42`: `fn_lookup_utilities_per_ba` legge il BB e propone solo le utility
        gestite; firma, guard e risoluzione dell'azienda invariati (2026-11-27)
  * [x] pgTAP nuovo `anagrafiche/test-fn-utilities-emittente-v1` (9). Prova sullo scratch: 0 → 9 ok; invariati e
        verdi `test-fn-lookup-utilities-per-ba`, `…-legge-il-ba-v1`, `test-parametri-importo-utility-v1`; guardrail
        verdi (2026-11-27)
  * [x] Doc: la pagina `manual/` del lookup, il «Vedi anche» e il testo di `emittenti-fiscali` (2026-11-27)
  * [x] Apply (Tid), pgTAP verdi, doc auto-generata rigenerata (2026-11-27); B-7 sullo scratch: zero accumuli,
        zero restringimenti. Gli oggetti nuovi dei quattro giri sono tutti citati da una guida o nota (`guide_coinvolte`)
  * [ ] La richiesta al BE/FE (§10): da girare dopo l'apply. Restano del BE: `configurazione-liste` §11.1 (la
        tendina, ⚠️ in §7) e le due pagine `manual/` del BE, che si riscrivono quando la tendina passa al BB
* Coda dei giri (2026-11-28): un censimento saltato da D-U-13
  * [x] Baseline di Tid del 2026-11-28: `ui/test-fn-preset-di-base-v1` si fermava al test 7 su
        `E_ATTIVO_BLOCK_CHILDREN_ACTIVE`. Spegneva l'azienda di `dbops.fn_pgtap_crea_emittente`, che da U1 nasce
        gestendo le sue utility. Il censimento di U2 aveva cercato chi spegne un'azienda nei verbi e nei builder,
        non nei pgTAP. Corretto il test: prima cancella le righe dell'azienda (senza BA né documenti, la strada di
        D-U-13), poi la spegne. Censimento su tutto `db/pgtap/`: l'unico altro file che spegne un'azienda,
        `vendite/test-registri-per-emittente-v1`, si aspetta il rifiuto. Sullo scratch: 25/25 (2026-11-28)
  * [ ] La corsa di Tid su dbdev
* [ ] Archiviazione

## 9. Verifica critica della sessione DB (2026-11-27)

Fatta sul catalogo dello scratch (`pg_get_functiondef`, `pg_trigger`, `pg_constraint`) e sui seed di `80_data`:
l'analisi di §4-bis era stata fatta sulla doc, senza interrogare il DB. Le decisioni di §6 reggono nel verso
(l'elenco serve, chiuso, una sede); cambiano l'ordine del piano e due sedi.

### V1 — La matrice non ha seed: con D-U-7 un'installazione nuova non scrive niente

`80_data/sql/config/utilities_tipi_ruolo.csv` **non lo carica nessun changeSet** (è un mirror dormiente), e non
ha righe per `EF`: solo `CL` e `FO`, col gas spento. Su un database costruito da zero (CI, installazione nuova)
la matrice è vuota (sullo scratch: zero righe, 2026-11-27, fatto datato coerente col seed non caricato). Oggi il
guard *fail-open* lascia passare tutto e la tendina non mostra niente. Con D-U-7 *fail-closed* nessuna azienda
attiva un'utility e nessun listino per categoria si scrive finché qualcuno non popola la matrice; la proposta
di D-U-8 è vuota. I fixture pgTAP che scrivono `emittenti_fiscali_utilities` o `categorie_clienti_listini`
devono costruirsi anche le righe della matrice.

* **D-U-10 — la matrice del primo impianto.** (a) Il seed si carica (un changeSet `80_data` nuovo), con le
  righe `EF` e quelle dei ruoli dei soggetti per ogni utility del catalogo; (b) resta vuota, la popola il
  SUPER_ADMIN, e la guida scrive il primo impianto: prima la matrice, poi le utility dell'azienda.
  Proposta **a**: un catalogo di utility senza una matrice è un'installazione che non fattura, e D-U-2 chiusa
  lo rende un blocco, non un default.

### V2 — L'uscita da `EF` avviene anche senza scrivere

La matrice ha `valido_dal`/`valido_al` (e `validita`, storicizzata). Un'utility esce da `EF` **quando passa la
data**, senza nessuna scrittura da rifiutare: il rifiuto di D-U-7 sull'«uscita» non la vede. Il rifiuto va
messo sul **gesto**, non sul giorno: con aziende che tengono l'utility, su una riga `EF` si rifiutano
`attivo → false`, `valido_al` valorizzato, `DELETE` e il cambio di `utility_id`/`tipo_ruolo_id`. Non chiede
una decisione: è la forma corretta di D-U-7.

### V3 — D-U-3 e D-U-6 fanno dell'`attivo` della riga una copia di quello dell'emittente

> ⚠️ **Corretta il 2026-11-27 (sera), nel giro U2**: la frase «su `emittenti_fiscali` c'è solo il blocco di
> `user_emittente_attivo`» è falsa. C'è anche il blocco generato dall'automazione ATTIVO sulla FK della riga
> (`trg_emittenti_fiscali_a10_emittenti_fiscali_utilities_bl_fafe8a`, `trgfn_prevent_deactivate_if_children`):
> un'azienda con righe accese non si spegne. La ricerca aveva filtrato i trigger per nome, non per funzione.
> Con D-U-11 (la riga sempre accesa) ne nasce D-U-13 (§8-bis, U2). La conclusione di V3 regge: la cascata non
> esiste, e una copia dell'`attivo` dell'emittente resta da evitare.

Con D-U-3 la riga si spegne solo con l'emittente, con D-U-6 si riaccende solo con lui: `attivo` della riga e
`emittenti_fiscali.attivo` dicono la stessa cosa in due sedi, tenute allineate da un trigger a cascata nei due
versi che **oggi non esiste** (su `emittenti_fiscali` c'è solo il blocco di `user_emittente_attivo`;
`trgfn_child_requires_active_parent` della riga scatta quando si scrive la riga, non il padre). E apre un buco:
emittente spento → righe spente → nessuna azienda «tiene attiva» l'utility → `EF` esce dalla matrice →
emittente riacceso → righe riaccese da sole. Il guard della matrice non scatta: il trigger è `UPDATE OF
utility_id, emittente_soggetto_ruolo_id`, non di `attivo`. Risultato: una riga accesa su un'utility non
ammessa.

* **D-U-11 — l'`attivo` della riga.** (a) La riga non ha uno stato suo: «gestita» = riga presente ed emittente
  acceso; `attivo` resta fisso a `true` (un `CHECK`) o si toglie, e i lettori leggono quello dell'emittente.
  D-U-6 non serve più (non c'è niente da riaccendere), e D-U-7 conta le righe presenti. (b) Come deciso, con la
  cascata nei due versi e il guard della matrice esteso a `attivo`. Proposta **a**: una verità, una sede.

### V4 — Il billing account nasce sull'azienda predefinita, poi si sposta

Il collegamento nasce in `trgfn_billing_account_link_ef` con l'azienda di chi agisce o la predefinita, e
`fn_crea_billing_account` senza sessione lo **modifica** subito verso l'azienda chiesta
(`_emittente-del-billing-account.md`, che descrive già lo stesso difetto per albero e istanza). Un controllo
immediato alla nascita giudica la predefinita: un BA del gas chiesto per un'azienda che il gas lo gestisce è
rifiutato se la predefinita non lo gestisce. Il controllo di D-U-4 sul collegamento va **differito** (a fine
transazione), e la modifica subito dopo la nascita passa dallo stesso controllo del quinto cancello.

### V5 — La sede del controllo: c'è già la chiave per una FK composta

Il piano (§8 punto 3) mette la regola dell'azienda nel guard generico `trgfn_guard_utility_tipo_ruolo_by_cols`,
che ragiona per **tipo** di ruolo: è una seconda regola nel BB di un'altra, e su `emittenti_fiscali_utilities`
stessa sarebbe circolare (la riga controllerebbe se stessa). Ma la tabella ha già
`uq_emittenti_fiscali_utilities_emittente_utility (emittente_soggetto_ruolo_id, utility_id)`, e le tabelle con
l'emittente diretto hanno le stesse due colonne: `listini`, `commesse`, `categorie_clienti_listini` (NOT NULL),
`fatture`, `registri_fatturazione`, `fatturazione_lotti` (utility nullable: una FK `MATCH SIMPLE` non giudica il
NULL, che è ciò che D-U-4 vuole). Una FK composta verso quella chiave dà in un colpo D-U-4 sulle tabelle
dirette e D-U-9 (il `DELETE` è rifiutato dalla FK, senza un trigger di `anagrafiche` che legga `vendite`).
Per il billing account serve `utility_id` sul collegamento `emittenti_fiscali_billing_account`, legato al BA
da una FK composta (sul BA serve un `UNIQUE (id, utility_id)` che oggi non c'è); la riga predefinita ha il BA
NULL e non si giudica. La FK `DEFERRABLE INITIALLY DEFERRED` chiude anche V4 e il quinto cancello.

* **D-U-12 — dove si giudica la coppia.** (a) FK composte verso `emittenti_fiscali_utilities`, con
  `utility_id` sul collegamento del BA; (b) guard di secondo livello sul registro dell'automazione, come in §8.
  Proposta **a**: è dichiarativa, copre la cancellazione senza codice, e la colonna in più non può divergere
  (l'utility del BA è immutabile e la FK la lega).

### V6 — L'allineamento viene prima del vincolo, e non è un `UPDATE`

Il punto 5 di §8 va **prima** dei punti 2 e 3: in CI i dati di seed che hanno emittente e utility, e i fixture
pgTAP che creano BA, listini, commesse, fatture, sarebbero rifiutati dal vincolo nuovo. Serve: le righe di
`emittenti_fiscali_utilities` nel seed per le aziende di seed (se ce ne sono), un seed di macchina dichiarato
per dbdev (§11.7) oppure la correzione a mano di Tid, e il **censimento dei fixture pgTAP** che scrivono le
tabelle di V5. È il costo vero del giro, e va nel piano come voce sua.

### Le guide, in più

D-U-4 tocca il collegamento del BA, che l'elenco di testata non aveva fra gli oggetti. Rilanciato
`scripts/guide_coinvolte.py --oggetti` con `anagrafiche.emittenti_fiscali_billing_account` (2026-11-27):

| Guida o nota | Esito |
| --- | --- |
| `dbzero/anagrafiche/_emittente-del-billing-account.md` | **guida indietro** nel giro del vincolo: il quinto cancello e la nascita differita (V4) |
| [soggetti-e-ruoli-anagrafici](../../guide/soggetti-e-ruoli-anagrafici.md), `_chiave-unica-cliente.md` | da leggere nel giro: nominano il collegamento per la chiave del cliente, non per l'utility |

## 10. La richiesta al team BE/FE (2026-11-27, dopo U1 … U4)

> **Da:** sessione DB (`dev/db-tid`). **A:** team BE/FE. **Quando:** all'arrivo del giro U4 (`/arrivi-db`), prima di
> cominciare. Se un lettore chiede qualcosa al DB, la richiesta torna tutta insieme.

Il modello è cambiato (§6): `anagrafiche.emittenti_fiscali_utilities` è l'**elenco delle utility che l'azienda
gestisce**, e un'azienda tratta solo quelle. Il database lo fa valere; il backend oggi lo ignora in quattro punti
noti, e il censimento deve trovare gli altri.

### R-1 — Il censimento (prima di tutto)

Censisci, in `backend/` e `frontend/`, **tutti** i lettori che contano su una di queste proprietà ritirate. L'elenco
dei file qui sotto è il punto di partenza, non il confine:

| Proprietà ritirata | Ora | File già noti |
| --- | --- | --- |
| «la riga c'è = l'azienda ha personalizzato i parametri» (`record_id` NULL = «non configurata») | la riga c'è = l'azienda **gestisce** l'utility; personalizzata = almeno un parametro | `LookupRepository.list_entity_utility_matrix`, `EmittentiFiscaliUtilitiesRepository` |
| «decimali e metodo sono obbligatori sulla riga» | facoltativi: NULL = policy dell'azienda e valori di sistema | `EmittentiFiscaliUtilitiesRepository.create_record` |
| «`attivo` della riga si spegne e si riaccende» | sempre `true` (`chk_emittenti_fiscali_utilities_attivo`, `23514`) | il drawer «Gestisci utilities» |
| «cancellare la riga = togliere l'override» | cancellare la riga = **togliere l'utility all'azienda**, ammesso solo senza billing account né documenti (`23503`) | `EmittentiFiscaliUtilitiesRepository.delete_record` |
| «un'utility senza righe nella matrice è aperta a tutti» (`fail-open`) | non è ammessa per nessuno | `api_emittenti_fiscali.md` righe 84 e 635 |
| «la tendina propone ogni utility ammessa per `EF` e per il ruolo» | solo quelle che l'azienda gestisce | `LookupRepository.list_utilities_per_emittente`, endpoint `utilities-per-emittente` |

### R-2 — Le due copie della regola si ritirano (regola del 2)

La regola delle utility ammesse ha una sede sola: `anagrafiche.fn_utilities_emittente(emittente_soggetto_ruolo_id,
ruolo_codice_soggetto DEFAULT NULL)`. Colonne: `utility_id`, `codice`, `descrizione`, `gestita`, `riga_id`
(la riga dell'azienda, NULL se non c'è), `arrotondamento_importi_dec`, `metodo_arrotondamento_importi`,
`minimo_soglia_min`, `minimo_soglia_max`, `personalizzata`. Un ruolo che non è un emittente è
`E_PARAMETRO_INVALIDO`.

* **La tendina** (`utilities-per-emittente`, `LookupRepository.list_utilities_per_emittente`): legge il BB e tiene
  `gestita`; con un billing account c'è già `anagrafiche.fn_lookup_utilities_per_ba`, che fa lo stesso. La copia
  applicativa si ritira nello stesso giro.
* **Il drawer dell'azienda** (`LookupRepository.list_entity_utility_matrix` con `overrides_table` =
  `emittenti_fiscali_utilities`): legge il BB senza ruolo (tutte le utility attivabili, con `gestita` e
  `riga_id`). Se il metodo generico serve ad altre tabelle, resta per quelle; per l'emittente no.

### R-3 — Il drawer «Gestisci utilities» diventa «attiva sì o no, più i parametri» (D-U-5, D-U-8, B-8)

* lo scrive solo il **SUPER_ADMIN** (D-U-5);
* **attivare** = inserire la riga, senza parametri obbligatori;
* **i parametri** = modificare la riga; «togli l'override» = riportare i parametri a NULL, **non** cancellare;
* **disattivare** = cancellare la riga: il database la rifiuta (`23503`) se un billing account o un documento la
  usa. Non c'è un interruttore `attivo`;
* **alla nascita di un'azienda** il drawer propone le utility da attivare (il BB sull'azienda nuova: tutte
  `gestita = false`); l'attivazione resta un gesto esplicito (D-U-8);
* un'azienda che gestisce utility non si spegne (`E_ATTIVO_BLOCK_CHILDREN_ACTIVE`): prima si cancellano le sue
  righe (D-U-13). Il messaggio va reso comprensibile nel drawer dell'azienda.

Chiude B-8 del [registro dei residui](registro-residui-aperti.md).

### R-4 — I rifiuti nuovi da tradurre

| Che cosa | Codice / vincolo | Dove nasce |
| --- | --- | --- |
| Un BA, un listino, un listino per categoria, una commessa, una fattura, un registro, un lotto su un'utility che l'azienda non gestisce; il cambio d'azienda di un BA verso un'azienda che non la gestisce | `23503` su `fk_emittenti_fiscali_ba_utility_gestita`, `fk_categorie_clienti_listini_utility_gestita`, `fk_listini_utility_gestita`, `fk_commesse_utility_gestita`, `fk_fatture_utility_gestita`, `fk_registri_fatturazione_utility_gestita`, `fk_fatturazione_lotti_utility_gestita` (al COMMIT: sono differite) | creazione cliente, cambio d'azienda, listini, commesse, fatturazione |
| La cancellazione della riga dell'azienda ancora usata | `23503` sulle stesse FK, dal lato del padre | drawer «Gestisci utilities» |
| Una riga dell'azienda spenta | `23514` su `chk_emittenti_fiscali_utilities_attivo` | drawer |
| Azienda o utility della riga cambiate | `E_CODICE_NON_MODIFICABILE` | drawer |
| La riga `EF` della matrice con una data di fine | `E_UTILITY_EF_SENZA_SCADENZA` | pannello della matrice utility/ruoli |
| La riga `EF` della matrice spenta, cancellata, spostata o con data d'inizio futura mentre un'azienda gestisce l'utility | `E_UTILITY_EF_GESTITA` | pannello della matrice |
| Un'utility senza nessuna riga nella matrice | `E_UTILITY_RUOLO_NON_AMMESSO` (prima passava) | ogni tabella del registro del guard |

Il servizio dell'emittente traduce già i `CHECK` della tabella per nome: le voci nuove si aggiungono alla stessa
mappa, con il campo dove c'è.

### R-5 — Le pagine del BE

* `docs/it/backend/core/manual/api_lookup_dedicati.md` §4 e `docs/it/backend/anagrafiche/manual/api_emittenti_fiscali.md`
  (la nota della tendina, §6.1, le righe 84 e 635 sul `fail-open`);
* `docs/it/guide/configurazione-liste.md` §11.1 (la combo «Utility»), marcata ⚠️: si riscrive quando la tendina
  passa al BB, togliendo il rimando a questo brief (una guida non rimanda ai brief).

