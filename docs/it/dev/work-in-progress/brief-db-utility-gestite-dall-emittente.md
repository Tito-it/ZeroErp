# Brief DB — Le utility gestite da ciascun emittente: serve un elenco per azienda?

## ⏭️ Chi riparte — aggiornato al 2026-11-27

**Riparte: la sessione DB**, con l'analisi (§4), quando Tid dà il via. Il brief è **aperto, non iniziato**: è
un'analisi, non uno sviluppo. Nasce il 2026-11-27 dalla decisione D-T8c-8 di
[brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) (§25.5): `gestori_utilities` si ritira, e Tid
chiede di valutare se all'emittente serva l'associazione con le utility che gestisce.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | sessione DB | L'analisi: i lettori, i casi, le strade, le guide | §4 | via di Tid |
| 2 | Tid | D-U-0: l'elenco per azienda serve? Se sì, D-U-1 … D-U-5 | §5 | 1 |
| 3 | sessione DB | Se D-U-0 è sì: il piano dei giri, DB e richiesta al BE/FE | — | 2 |
| 4 | sessione DB | Archiviazione, o il brief di sviluppo che ne nasce | — | 2 o 3 |

**Decisioni aperte di Tid:** D-U-0 … D-U-5, dopo l'analisi.
**Da committare:** questo brief, nato il 2026-11-27.

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

* [ ] I lettori di `emittenti_fiscali_utilities` e della matrice, con il significato su cui contano (una riga =
      eccezione): se la riga diventasse anche «abilitazione», chi cambierebbe comportamento (regola della garanzia
      ritirata, `.codex/AGENTS.md`)
* [ ] Per ogni tabella di §3: ha l'emittente (diretto o dal billing account)? Dove nasce la coppia, e chi la sceglie
* [ ] I casi del modello, costruiti e non misurati: un'azienda nuova senza righe (oggi fattura tutto); un'utility
      tolta a un'azienda che ha già contratti, listini o fatture aperte di quell'utility; un billing account che
      passa a un'altra azienda (giro 6: il BA è sempre collegato, la storia dell'emittente); la madre plurale
* [ ] Le strade, con quello che ciascuna rompe: (a) com'è, e il limite si scrive nella guida; (b) la stessa tabella
      diventa anche l'elenco, con una colonna o con «riga presente = gestita»; (c) una tabella nuova
      dell'abilitazione, separata dai parametri; (d) il registro del guard esteso ai documenti, con la coppia
      azienda e utility
* [ ] Le guide di testata, ciascuna con il suo esito; la decisione C citata con la sua data
* [ ] La ricaduta sul BE e sul FE (la tendina, la matrice di B-8, i drawer del cliente e del fornitore) come
      richiesta, senza leggere `backend/`

## 5. Le decisioni per Tid (dopo l'analisi)

* **D-U-0**: l'elenco delle utility per azienda serve? No: la decisione C resta, e il limite si scrive. Sì: le altre.
* **D-U-1**: dove sta l'elenco (strade b, c, d di §4).
* **D-U-2**: un'azienda senza righe gestisce tutto (aperta) o niente (chiusa)?
* **D-U-3**: che cosa succede togliendo un'utility a un'azienda che ha documenti vivi di quell'utility.
* **D-U-4**: dove si giudica la coppia: solo alla nascita del billing account e del cliente, o anche su ogni documento.
* **D-U-5**: chi la scrive: il SUPER_ADMIN, l'admin dell'emittente, il pannello di configurazione.
