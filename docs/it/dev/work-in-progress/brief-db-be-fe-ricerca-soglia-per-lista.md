# Brief DB · BE · FE — La soglia della ricerca è un fatto della lista

> **Destinatari:** team DB (`dev/db-tid`) per §1 e §4; backend e frontend
> (`dev/backend-tid`) per §5, **dopo** il DB.
>
> **Tipo:** brief di cantiere. Nasce il 2026-09-24 sera dalla chiusura di due
> brief che hanno portato la ricerca libera delle liste sul catalogo:
> [brief-be-ricerca-full-liste-residue](../work-done/brief-be-ricerca-full-liste-residue.md)
> e [brief-db-ricerca-full-colonne-da-accendere](../work-done/brief-db-ricerca-full-colonne-da-accendere.md).
> Quello che restava aperto in coda a entrambi era un argomento solo — **quanti
> caratteri servono per cercare, e chi lo decide** — più una richiesta di seed
> ancora da applicare (§1). Qui sono raccolti; il resto dei residui è in
> PROJECT_CONTEXT § «Aperto — Media priorità».
>
> **Stato 2026-09-24 sera:** §1 ✅ **scritta** dal team DB (seed, tre righe),
> da applicare. ⏳ Resta al **team DB** §4 (colonna, seed, lettura, pgTAP). BE
> e FE aspettano §4. La decisione di §6 a resta aperta per Tid e non blocca
> niente.

---

## 1. Richiesta al team DB — tre frecce di ordinamento ✅ scritta

> Ex brief DB `ricerca-full-colonne-da-accendere` §8 (2026-09-24 sera). ⚠️ Da
> applicare per prima: finché manca, la suite BE ha **due rossi**, ed è il
> segnale voluto, non un difetto del BE.
>
> ✅ **Fatto 2026-09-24 (team DB)**: `ordinabile = t` sulle righe 932, 933 e
> 934 di `80_data/sql/ui/lista_colonna.csv`. Nessun changeSet nuovo: il CSV lo
> ricaricano i due `loadUpdateData` con `runOnChange: true` già esistenti (il
> loader `20260507-07` e il mirror `20260806-15`). Controllato prima di
> scrivere: nessun UPDATE nei changelog riscrive `ordinabile`, nessun pgTAP
> fissa il valore di queste righe, e i tre `campo_sorgente` sono chiavi delle
> due `_ORDER_COLS`. ⏳ **Da applicare** (`db-migrate`), poi la suite BE deve
> tornare verde su
> `test_seed_offre_tutto_cio_che_il_backend_sa_ordinare`.

Convertite le liste al catalogo, la suite BE ha un rosso che viene dal seed:
`test_liste_configurabili_seed.test_seed_offre_tutto_cio_che_il_backend_sa_ordinare`
(sottocasi `vendite.promo_articoli` e `anagrafiche.categorie_clienti_listini`).

Il seed del 2026-09-24 aveva scelto `ordinabile = f` su tutte le righe nuove,
perché «`ordinabile = t` pretende la colonna nella whitelist di ordinamento del
repository». Per tre righe la whitelist **c'era già**, da prima di quel
cantiere:

| Riga | Lista · `campo_sorgente` | Whitelist BE che la ordina |
| --- | --- | --- |
| 932 | `vendite.promo_articoli` · `articolo_descrizione` | `promo_articoli_repository._ORDER_COLS` → `a.descrizione` |
| 933 | `anagrafiche.categorie_clienti_listini` · `categoria_descrizione` | `categorie_clienti_listini_repository._ORDER_COLS` → `cc.descrizione` |
| 934 | `anagrafiche.categorie_clienti_listini` · `listino_descrizione` | idem → `l.descrizione` |

**Richiesta**: `ordinabile = t` sulle tre righe di
`80_data/sql/ui/lista_colonna.csv` (dal CSV, linee guida SQL §11.2). Togliere
le colonne dalla whitelist vorrebbe dire spegnere una capacità che il BE ha
già: il test chiede proprio di non farlo. Le altre righe nuove (930, 931,
935-938) restano `ordinabile = f`, perché le loro whitelist non le conoscono.

## 2. Il difetto — la soglia «da un carattere» non arriva a video

Le liste di configurazione cercano da **un** carattere (decisione di Tid del
2026-09-23), ma solo **nel backend**. La soglia oggi vive in tre sedi che non
si conoscono:

| Sede | Forma |
| --- | --- |
| repository | `add_ricerca_full_condition(…, min_caratteri=1)`, quattordici chiamate |
| schema OpenAPI della view | `param_ricerca_full(min_caratteri=1)`, ripetuto per view |
| frontend | nessuna: manda il termine da `RICERCA.MIN_CARATTERI` (3) per ogni lista |

Quindi «KG» su unità di misura o «FT» sulle famiglie: la casella lo accetta, la
richiesta parte **senza** `search`, e la lista resta intera — senza nessun
errore. È un contratto dichiarato che nessun client esercita.

⭐ Il lato frontend della soglia ha già una sede sola dal 2026-09-24 (regola
del 2, ok Tid): `paramsRicerca(f, {minCaratteri})` e
`termineCorto(termine, {minCaratteri})` in `core/utils/listParams.js`, sulla
costante `RICERCA.MIN_CARATTERI`. Manca solo **da dove prendere
`minCaratteri` per ogni lista**.

## 3. Il modello — decisione di Tid del 2026-09-24

Quanti caratteri servono per cercare dipende da **cosa è la lista** (una tabella
di configurazione a codici corti, o un archivio che cresce), non da chi la
chiama. È una proprietà della lista, e le proprietà della lista stanno in
`ui.lista_definizione`: il catalogo diventa la sede unica della soglia, come lo
è già delle colonne.

Le strade valutate (ex brief BE §13.6):

1. ✅ **la soglia nella configurazione della lista**, da una colonna di
   `ui.lista_definizione`, letta anche dal BB al posto di `min_caratteri`;
2. ⛔ un'opzione dello store FE (`ricercaMinCaratteri: 1`) sulle liste di
   configurazione: rapida, ma è la quarta copia dello stesso fatto.

## 4. Richiesta al team DB

> Ex brief DB §9. La forma la sceglie il team DB, come per
> `fn_lista_colonne_ricerca_full`.

1. **colonna** in `ui.lista_definizione`, per esempio `ricerca_min_caratteri`
   `smallint NOT NULL`, `CHECK (ricerca_min_caratteri >= 1)`. Il default è la
   soglia di progetto, 3 (`RICERCA_MIN_CARATTERI` nel BE,
   `RICERCA.MIN_CARATTERI` nel FE). ⚠️ Scritto anche qui diventa la terza copia
   del numero: se il team preferisce `NULL` = «default di progetto» e il
   numero solo nel codice, al BE va bene lo stesso. Basta che la scelta sia una;
2. **seed** `80_data/sql/ui/lista_definizione.csv` (dal CSV, §11.2): **1**
   sulle liste di configurazione che oggi il BE chiama con `min_caratteri=1`:
   `catalogo.uom_tipi`, `catalogo.unita_misura`, `catalogo.conversioni_uom`,
   `config.tipi_ruolo_tipi_indirizzo`, `config.utilities_tipi_ruolo`,
   `config.email_account`, `config.email_template`,
   `anagrafiche.categorie_clienti`, `anagrafiche.categorie_clienti_listini`,
   `documenti.template_documenti`, `documenti.template_asset`,
   `vendite.registri_numerazione`, `vendite.famiglie_documento`,
   `amm.processi`. Tutte le altre al default;
3. **lettura**: il valore deve arrivare a **due** lettori, dalla stessa fonte:
   - la **configurazione della schermata**: nel jsonb di
     `ui.fn_resolve_lista_config`, accanto a `pagina_dimensione` (il FE la
     legge da lì, come `ricerca_full`);
   - il **BB di ricerca** del BE, che oggi legge solo
     `ui.fn_lista_colonne_ricerca_full(lista_codice)`: una colonna in più nel
     suo risultato, o una funzione piccola (`STABLE`, grant `zeroerp_app`).
     Scelta del team. ⚠️ Lista inesistente → lo stesso
     `E_UI_LISTA_NON_TROVATA` delle altre letture;
4. **pgTAP** col caso **costruito**: il `CHECK` rifiuta 0; una lista a 1 e una
   al default rispondono ciascuna col suo valore, in **entrambe** le letture.

## 5. Dopo il DB — BE e FE, nello stesso giro

**Backend**

- `add_ricerca_full_condition` legge la soglia dal catalogo; l'argomento
  `min_caratteri` sparisce dalle quattordici chiamate. ⚠️ Oggi il BB legge il
  catalogo solo **sopra** soglia (aprire una lista senza cercare non costa
  niente): con la soglia nel catalogo la lettura parte a termine non vuoto.
  Una query leggera, e il frontend non manderà più termini corti;
- `param_ricerca_full` smette di dichiarare la soglia per view: dice «soglia
  dal catalogo della lista» (lo schema OpenAPI non può leggere il DB
  all'import);
- `get_lista_config_per_video` porta la soglia al FE (dal jsonb di §4.3);
- presidi: `test_ricerca_full_seed` (nessuna chiamata passa `min_caratteri`),
  `test_ricerca_full_db` (una lista a 1 filtra con un carattere, una al
  default no).

**Frontend**

- `useListaConfigurabilePage.onConfigLoaded` scrive la soglia nello store
  accanto a `ricercaFull` (dichiarata dallo stesso BB di stato,
  `useListaEmptyStateFetch`);
- `paramsRicerca` e `termineCorto` la ricevono come `minCaratteri`: nessun
  numero nuovo nel codice.

⛔ Fino ad allora i quattordici `min_caratteri=1` e i
`param_ricerca_full(min_caratteri=1)` restano dove sono: niente passo a metà.

## 6. Decisioni aperte per Tid — non bloccano §4

**a. Sotto soglia, sulle liste NON di configurazione: 400 o termine ignorato?**
(ex brief BE §6). Oggi convivono due comportamenti:

| Comportamento | Dove |
| --- | --- |
| **400** `E_SEARCH_VALIDATION` (`require_min_search_length`) | testate e disponibilità di magazzino, anagrafiche di magazzino, `catalogo.articoli`, `vendite.listini`, `pagamenti.rate` (`saldi_service`) |
| **ignorato** (il BB non filtra) | le dieci liste di vendite e tutte le altre sul BB senza 400 nella view |

Il frontend manda il termine a ogni tasto (`useSearchTable`): il 400 durante la
digitazione va guardato a video prima di sceglierlo. ⭐ Con la soglia nel
catalogo la domanda cambia forma: il frontend non manda più un termine sotto
la soglia **della lista**, quindi il 400 diventa una difesa contro un client che
non legge la configurazione, non un evento della digitazione. Fino alla
decisione i 400 esistenti **restano** nelle view.

**b. `MIN_SEARCH_LENGTH_SOGGETTI = 3`** (ex brief BE §13.3 f) in
`anagrafiche/db/soggetti_repository.py`: la soglia della ricerca soggetti del
`SoggettoResolver`, esposta al FE dal resolver (`min_search_length`,
`SoggettoResolver.vue`). Stesso valore di `RICERCA_MIN_CARATTERI`, seconda
sede. ⚠️ Il resolver **non** è una lista a catalogo, quindi §4 non la copre. Da
decidere se legge `RICERCA_MIN_CARATTERI` (e il FE `RICERCA.MIN_CARATTERI`) o se
è una soglia sua, e allora con un nome che lo dica.

## 7. Ordine

1. ⏳ **Team DB**: §4, coi pgTAP. (§1 ✅ scritta il 2026-09-24, da applicare.)
2. ⏳ **BE + FE**: §5, nello stesso giro, dopo l'apply.
3. ⏳ **Tid**: §6 a e b, quando vuole: non bloccano.

Fine cantiere: nessuna chiamata al BB passa `min_caratteri`, nessuna view
dichiara la soglia a mano, e «KG» su unità di misura filtra a video.
