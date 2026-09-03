# Brief BE — migrazione a `sql_order_clause`, per lotti

> Origine: `dev/backend-tid` · aperto e **chiuso** il 2026-09-02
> **Esito: 7 lotti su 7 · 29 call-site migrati · 12 esclusi con la ragione.**
> BB estratto il 2026-09-02 (regola del 2, ok Tid) — vedi
> [catalogo BB backend](../backend/catalogo-building-block-backend.md).

## 1. Che cosa si migra, e perché a lotti

`sql_order_clause` unifica le tre righe che ogni lista scrive per costruire il
suo `ORDER BY`:

```python
order_col   = COLS.get(order_by, COLS[DEFAULT])
direction   = sql_order_direction(order_dir, default_desc=…)
tiebreak_dir = sql_tiebreak_direction(direction)
...  f"ORDER BY {order_col} {direction}, x.id {tiebreak_dir}"
```

⚠️ **A lotti e non in un colpo solo**, ed è una scelta di rischio: la maggior
parte di questi repository **non ha test propri**. La rete che li copre è
`test_lista_proiezione_campo_sorgente`, che esercita ogni colonna di whitelist
in entrambi i versi **contro il database vero** — ma solo per le liste che sono
a registro. Un lotto per dominio è la dimensione in cui, se qualcosa si rompe,
si sa **dove**.

⛔ **Il numero non è un obiettivo.** Il conteggio serve a sapere quanto manca,
non a decidere che cosa fare: un call-site che il BB non descrive va **lasciato
com'è**, e la sua riga qui diventa un'esclusione motivata. Forzare la forma
sarebbe la duplicazione al contrario — una sede unica che dice una cosa falsa su
metà dei suoi consumatori.

## 2. Il criterio, deciso prima di guardare i file

| Forma | Esito |
| --- | --- |
| whitelist + **un** tiebreak allineato alla direzione | ✅ si migra |
| default a più criteri con le direzioni dentro | ✅ si migra, con `default_clause` |
| tiebreak **gerarchico** (non segue la direzione: `v.reso_id DESC, v.resi_riga_id ASC`) | ⛔ resta — non è uno spareggio tecnico, è ordine logico |
| tiebreak **composito** (`commessa_codice ASC, commessa_id {dir}`) | ⛔ resta — il BB appende la direzione in coda, e qui la prima chiave ha la sua |
| clausola che cambia **ramo** su `sort_col is None` | ⛔ resta — non è un ordinamento, sono due |

⭐ **Le esclusioni si scrivono con la ragione**, non si contano e basta: una
riga «non migrato» senza motivo è indistinguibile da una dimenticata, e fra sei
mesi qualcuno la migra lo stesso.

## 2-bis. ⛔ Che cosa questi lotti NON fanno: `colonne_desc`

Il BB sa esprimere la regola «gli ordinamenti per DATA partono DESC»
(`colonne_desc`), e i 4 call-site della prima ondata la usano. **I lotti qui
sotto NON la estendono agli altri**, ed è una scelta, non una dimenticanza:

* sarebbe un **cambio di comportamento**, non una migrazione di forma — e i due
  mescolati in 41 posti insieme rendono impossibile dire quale dei due ha rotto
  qualcosa;
* ⚠️ **dall'interfaccia sarebbe comunque invisibile**: il frontend manda sempre
  `order_dir` (`f.order_dir || 'asc'`), quindi `colonne_desc` non entra mai in
  gioco da lì. Il primo click su una data parte già DESC, e lo decide
  `<ListaConfigurabile>` leggendo `tipo_dato` dal catalogo;
* ⛔ e soprattutto: **quali colonne siano date lo direbbe il mio giudizio, una
  whitelist alla volta**, mentre l'autorità esiste già ed è
  `ui.lista_colonna.tipo_dato`. Una lista di nomi scritta a mano in 41
  repository è una seconda verità in 41 copie.

⇒ Se la si vuole anche lato BE, è un lavoro **suo**, e vuole il suo presidio:
un test che confronti il set dichiarato da ogni repository con le colonne
`date`/`datetime` del seed — come `test_whitelist_copre_le_colonne_ordinabili`
fa già per le whitelist.

## 3. I lotti

Ordine dal più piccolo al più grosso: i primi servono anche a verificare che il
BB regga la varietà vera prima di arrivare ai file grandi.

| # | Lotto | File | Siti | Stato |
| --- | --- | --- | --- | --- |
| L1 | config — le due matrici | `utilities_tipi_ruolo`, `tipi_ruolo_tipi_indirizzo` | 2 | ✅ **2/2** |
| L2 | anagrafiche — le liste semplici | `soggetti`, `clienti`, `fornitori`, `indirizzi`, `categorie_clienti`, `categorie_clienti_listini`, `emittenti_fiscali` (2) | 8 | ✅ **7 migrati · 1 escluso** |
| L3 | anagrafiche — geo | `geo_repository` | 6 | ✅ **6/6** |
| L4 | pratiche + amministrazione | `pratiche_repository`, `amm_software_repository` | 2 | ✅ **1 migrato · 1 escluso** |
| L5 | vendite — i documenti | `contratti`, `ddt`, `famiglie`, `fatture`, `ordini`, `preventivi`, `promo_articoli`, `registri`, `resi` | 9 | ✅ **9/9** |
| L6 | vendite — il repository grande | `vendite_repository` | 9 | ✅ **0 migrati · 9 esclusi** |
| L7 | pagamenti — i residui | `pagamenti_repository` | 5 | ✅ **4 migrati · 1 escluso** |
| | **totale** | | **41** | |

⚠️ **Il conteggio è delle OCCORRENZE, non dei metodi migrabili**: la
classificazione del §2 si applica dentro ogni lotto, e le esclusioni si
annotano nella riga del lotto quando si incontrano.

## 4. Come si chiude un lotto

1. si migrano i siti che rispettano il criterio, uno per uno;
2. si eseguono **`ZEROERP_TEST_DB_E2E=1 ./manage-test.sh`** (suite intera) e
   `test_lista_proiezione_campo_sorgente` — ⭐ è quest'ultimo che prova le
   clausole **contro il database**, colonna per colonna e in entrambi i versi:
   una clausola malformata è SQL che non parte, e senza database non si vedrebbe;
3. si spunta la riga qui, con il numero di siti migrati e quelli esclusi;
4. ⛔ **non si accorpano due lotti** perché «tanto sono simili»: il punto della
   suddivisione è sapere dove guardare quando qualcosa si rompe.

## 5. Diario

### L1 · config — ✅ 2/2 (2026-09-02)

Forma canonica su entrambi, nessuna sorpresa. `utilities_tipi_ruolo` e
`tipi_ruolo_tipi_indirizzo` sono le due matrici slot/override: whitelist,
`.get(chiave, default)`, tiebreak singolo (`utr.id` / `trti.id`).

### L2 · anagrafiche semplici — ✅ 7 migrati, 1 escluso (2026-09-02)

Migrati: `soggetti`, `clienti`, `fornitori`, `categorie_clienti`,
`categorie_clienti_listini`, `emittenti_fiscali` (lista emittenti), `indirizzi`.

⭐ **`indirizzi` ha richiesto una modifica in più, ed è un miglioramento**: la sua
whitelist era un `set` e la colonna si usava per identità
(`order_col = order_by if order_by in _ORDER_COLS else …`). È diventata una mappa
`{c: c}` — le due metà uguali **apposta**, perché su quella vista il nome logico
*è* l'espressione SQL. ⚠️ `set(_ORDER_COLS)` continua a dare le chiavi, quindi
`_whitelist_indirizzi` del presidio seed non è cambiato.

⛔ **Escluso — `emittenti_fiscali.list_by_emittente` (il tab BA)**, e la ragione è
del §2: la clausola porta un **prefisso condizionale**
(`m.is_default DESC, `) che dipende **dalla colonna risolta** — se l'operatore
ordina proprio per `is_default`, il prefisso vincerebbe sulla sua scelta e la
freccia non ordinerebbe. Il BB non espone la colonna risolta, di proposito:
per calcolare il prefisso bisognerebbe risolverla **una seconda volta**, cioè
due sedi per lo stesso lookup — esattamente la duplicazione che si sta togliendo.

🔴 **Un difetto mio, corretto nello stesso lotto e vale la pena scriverlo**: lo
script che ripuliva gli import usava la soglia sbagliata (`> 1` invece di `>= 1`)
per decidere se un helper fosse ancora usato, e ha tolto due import ancora
necessari a `emittenti_fiscali` — che ha un **secondo** call-site, quello
escluso. ⇒ Da qui in avanti ogni lotto passa da un **audit AST** (nomi usati vs
nomi importati) prima dei test: un `NameError` dentro un metodo non si vede
finché qualcuno non lo chiama, e non tutte queste liste sono a registro.

### L3 · geo — ✅ 6/6 (2026-09-02)

Sei liste, tutte a identità come `indirizzi`: le whitelist erano insiemi e la
colonna si usava per sé stessa. Sono diventate mappe `{c: c}` via un piccolo
`_identita(...)`, che dice a voce quello che prima era implicito.

### L4 · pratiche + amministrazione — ✅ 1 migrato, 1 escluso (2026-09-02)

`pratiche` è forma canonica.

⛔ **Escluso — `amm_software.list_operatori`**: `if order_column: … else:` con un
ramo `else` che è un ordinamento **diverso**
(`soggetto_cognome ASC, au.username ASC, au.id`) e che **ignora del tutto
`order_dir`**. Il BB, sul ramo di default, allineerebbe il tiebreak alla
direzione richiesta: con un `order_by` fuori whitelist e un `order_dir=desc`
espliciti l'ordine cambierebbe. ⚠️ È un caso di bordo stretto — ma una
migrazione di forma che cambia semantica non è una migrazione di forma, e il
criterio del §2 lo diceva prima di guardare il file.

### L5 · vendite documenti — ✅ 9/9 (2026-09-02)

Tutti e nove a forma canonica. `fatture` porta `default_desc=True` (nasce dalla
più recente), gli altri il default `asc`.

### L6 · `vendite_repository` — ⛔ 0 migrati, 9 esclusi (2026-09-02)

⭐ **È il risultato più interessante dei sette lotti, e non è un fallimento.**
Il file con più occorrenze è quello in cui **nessuna** è la forma meccanica: qui
l'ordinamento è logica di dominio, non sintassi ripetuta.

| Riga | Perché resta |
| --- | --- |
| 112 `_giornale_order_clause` | il secondo criterio non è uno spareggio ma **significato**: `t.quando DESC` sta dentro la gravità e non deve girarsi |
| 645 lotti di fatturazione | ramo `else` con un ordinamento **diverso** (`fl.data_insert DESC`) che ignora `order_dir` |
| 933 · 2474 dashboard aperto/backlog | **due** chiavi di spareggio: `area ASC, documento_id {dir}` — la prima fissa, la seconda che segue |
| 1235 · 1386 · 1520 attività e commesse | idem: `commessa_codice ASC, <chiave tecnica> {dir}` |
| 1855 gruppi fatturabili | idem con `gruppo_key ASC, stadio {dir}` |
| 2714 fondi da decidere | **due** chiavi di spareggio, che seguono entrambe la direzione |

⛔ **Il BB scrive UNA colonna e UNA chiave di spareggio**, con la seconda nella
stessa direzione della prima. A questi serve altro — due chiavi, o due chiavi
con regole diverse — e per dargliela il BB smetterebbe di essere una forma sola.

🔴 **Correzione (2026-09-02, stessa giornata).** La prima stesura di questa nota
motivava le esclusioni dicendo che una chiave di raggruppamento «resta ASC
qualunque cosa scelga l'operatore, altrimenti l'elenco per cliente sparpaglia i
documenti dello stesso cliente». **Non è vero**: ordinare per `commessa_codice`
in un verso o nell'altro tiene comunque adiacenti le righe con lo stesso valore
— cambierebbe solo l'ordine dei gruppi. ⚠️ La motivazione era più suggestiva di
quella vera, ed è il modo in cui una ragione sbagliata sopravvive: sembra
spiegare, e nessuno la verifica perché la conclusione è giusta lo stesso. La
ragione vera è strutturale, ed è quella scritta qui sopra.

### L7 · pagamenti — ✅ 4 migrati, 1 escluso (2026-09-02)

Migrati: distinte, righe della coda, rate fuori capienza, canali di incasso.

⛔ **Escluso — `list_eccedenze`**: tiebreak composito
`cliente_soggetto_ruolo_id, fattura_id`. ⚠️ E la ragione è scritta nel codice
accanto: ordinando per eccedenza **di cliente**, i documenti dello stesso cliente
devono restare insieme — un tiebreak solo li sparpaglierebbe.

🔴 **Un secondo difetto mio, e la correzione vale come metodo**: la stringa
`ORDER BY {sort_col} {direction}, id {tiebreak}` è **identica su tre metodi** di
questo file, e sostituire «la prima occorrenza» avrebbe potuto riscrivere il
metodo sbagliato. L'assert su `count == 1` l'ha fermato prima che scrivesse
alcunché; da lì la sostituzione è **ancorata alla posizione** del blocco appena
riscritto. ⚠️ Un `replace(..., 1)` su codice ripetuto è un difetto che non dà
errore: produce un file che compila e una query che ordina un'altra cosa.

---

## 6. Verifica finale, quando i lotti sono chiusi

```bash
# quanti call-site restano sulla forma vecchia
grep -rn "sql_tiebreak_direction(" backend/apps --include=*.py \
  | grep -v __pycache__ | grep -v _helpers.py | wc -l
```

⚠️ **Il numero atteso NON è zero**, ed è il punto del §2: a fine migrazione
restano i siti esclusi con la loro ragione. Un zero, qui, vorrebbe dire che
qualcuno ha forzato la forma dove non andava.

### ✅ Misurato a chiusura (2026-09-02)

| Misura | Valore |
| --- | --- |
| call-site che usano `sql_order_clause` | **33** (29 dei lotti + 4 della prima ondata) |
| call-site rimasti sulla forma vecchia | **12**, tutti esclusi con la ragione |
| di cui in `vendite_repository` | **9** |
| gli altri 3 | `amm_software` (ramo che ignora la direzione), `emittenti_fiscali` (prefisso condizionale), `pagamenti.list_eccedenze` (tiebreak composito) |
| suite backend | **4418 test OK** con `ZEROERP_TEST_DB_E2E=1` |

⭐ **Il rapporto 33 / 12 dice la cosa giusta sul codice**: due terzi di questi
`ORDER BY` erano la stessa frase ripetuta, un terzo è logica di dominio che
somigliava a una frase ripetuta. ⛔ Il modo di sbagliare, qui, era guardare solo
il primo numero.

⚠️ **Nessuna di queste 12 righe è un debito.** Se un giorno qualcuno riapre
questo file per «finire il lavoro», la risposta è nel §2 e nel diario del L6:
il BB appende **una** direzione in coda al tiebreak, e su una chiave che
*raggruppa* quella direzione sarebbe sbagliata.
