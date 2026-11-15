# Brief DB — Il mese di un giorno si calcola sul calendario, non passando da un istante

## ⏭️ Chi riparte — aggiornato al 2026-11-15

**Riparte: il team BE**, con R-BE-1 (§7): le sei copie del calcolo nel SQL del backend passano a
`script.fn_mese_di` / `fn_fine_mese_di`. Poi il team DB chiude e archivia. **Il lato DB è
finito:** i quattro giri sono applicati e i pgTAP sono verdi (Tid, 2026-11-15). Nel catalogo vivo
nessuna vista e nessuna funzione tronca più con `date_trunc`, e lo dice il presidio
`script/test-mese-di-un-giorno-v1` (test 17); i tre CHECK del primo del mese poggiano su
`fn_mese_di` (test 18); il cancello `date-trunc` ferma le copie nuove nei changeSet. Giri: 1
(`20261114-82`, `-83`), 2 (le viste, `20261115-01…-07`), 3 (le funzioni di `vendite`,
`-08…-26`), 4 (CHECK e helper, `-27…-33`). Via di
Tid e numeri `-82…-83` del 2026-11-15; D-1, D-2 e D-3 decise (a) lo stesso giorno.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Ricognizione sul catalogo vivo, progetto, giri (2026-11-15) | §2, §4, §6 | — |
| 1b | ✅ Tid | Perimetro: tutte le copie, fine mese compreso (2026-11-15) | §3 | 1 |
| 2 | ✅ Tid | D-1 (a), D-2 (a), D-3 (a) (2026-11-15) | §5 | 1b |
| 2b | ✅ Tid | Il via allo sviluppo e i numeri `20261114-82…-83` (2026-11-15) | — | 2 |
| 3 | ✅ team DB | Giro 1: i due BB, il pgTAP, la regola `date-trunc`, §11.10, due `manual/`; prova in transazione (2026-11-15) | §6.1 | 2b |
| 4 | ✅ Tid | Apply del giro 1 e pgTAP: verdi (2026-11-15) | §6.1 | 3 |
| 4b | **team BE** ⏭️ | R-BE-1: le sei copie nel SQL del backend passano ai BB | §7 | 4 ✅ |
| 5 | ✅ team DB | Giro 2: le viste, `20261115-01…-07` (numeri di Tid); scritti e provati in transazione (2026-11-15) | §6.2 | 4 ✅; stati-dal-vocabolario senza giri aperti sulle viste ✅ |
| 5b | ✅ Tid | Apply del giro 2 e pgTAP delle viste: verdi (2026-11-15) | §6.2 | 5 |
| 6 | ✅ team DB | Giro 3: le funzioni di `vendite`, `20261115-08…-26` (numeri di Tid); scritti e provati in transazione (2026-11-15) | §6.3 | 4 ✅ |
| 6a | ✅ team DB | I cinque pgTAP senza `ROLLBACK;` corretti, invariante E del preambolo (decisione di Tid, 2026-11-15) | §6.3 | — |
| 6b | ✅ Tid | Apply del giro 3 e pgTAP: verdi (2026-11-15) | §6.3 | 6 |
| 7 | ✅ team DB | Giro 4: CHECK (D-1), helper pgTAP, presidio vivo, `20261115-27…-33`; provati in transazione (2026-11-15) | §6.4 | 5 ✅, 6 ✅ |
| 7b | ✅ team DB | I due pgTAP col `DO` di pulizia prima del `BEGIN;` corretti (decisione di Tid, 2026-11-15) | §6.4 | — |
| 8 | ✅ Tid | Apply del giro 4 e pgTAP: verdi (2026-11-15) | §6.4 | 7 |
| 9 | team DB | Chiusura e archiviazione; il debito D-2 (aritmetica dei mesi) va in un brief nuovo | — | 8 ✅, 4b |

**Decisioni aperte di Tid:** nessuna. Decise il 2026-11-15: i due pgTAP col `DO` di pulizia (§6.4); i cinque pgTAP senza `ROLLBACK;` (§6.3); D-1 (a), D-2 (a), D-3 (a) (§5). **Lavoro da committare:** il giro 1
(`20261114-82`, `-83`, il pgTAP, `scripts/guardrail_forme_changeset.py`, `linee-guida-sql.md`
§11.10, le due pagine `manual/`), il giro 2 (`20261115-01…-07`), il giro 3 (`20261115-08…-26`), il giro 4 (`20261115-27…-33`, il pgTAP del mese a 18), i due pgTAP senza il `DO` di pulizia, i cinque pgTAP con il `ROLLBACK;`,
`scripts/guardrail_pgtap_preambolo.py`, la guida pgTAP e questo brief.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-15. **A chi:** Tid, poi il team DB.
> **Origine:** il cancello `guardrail_timestamp_senza_fuso.py` rosso in CI su `20261114-07`.
> **BE e FE:** il FE nulla; il BE ha sei copie del calcolo nel suo SQL (R-BE-1, §7).
> **Brief vicini verificati:**
> [valutazione-modello-di-dominio-db](valutazione-modello-di-dominio-db.md) V-3 (chiusa il
> 2026-09-21): ha lasciato questi `date_trunc` «fuori perimetro» e dichiarati; questo brief la
> completa, non la revoca.
> [brief-db-stati-documento-dal-vocabolario](brief-db-stati-documento-dal-vocabolario.md) e
> [brief-db-provenienza-prezzo-segue-il-prezzo](brief-db-provenienza-prezzo-segue-il-prezzo.md):
> stesso perimetro di oggetti (viste `vw_dash_*`, `vw_lotti_fase`, lister `*_da_pushare`,
> `fn_get_or_create_lotto`, `fn_create_fatturazione_lotto`, `fn_genera_scadenze_fattura`,
> `fn_upsert_commessa_attivita`, `fn_contratti_addebiti_maturati_con_provenienza`), tema diverso.
> Non si fondono: si **coordinano** i giri (§6). Nessun altro brief tratta il tema.

## 1. Il difetto

Un mese di competenza è un **giorno del calendario**: il primo del mese. Ricavarlo da un altro
giorno è aritmetica sulle date e non ha bisogno di sapere che ora è né dove.

Nel database lo si scrive invece `date_trunc('month', <date>)::date`. `date_trunc` non ha una
variante per `date`, e PostgreSQL sceglie quella su `timestamptz`: la data diventa la mezzanotte
**nel fuso della sessione**, si tronca nel fuso della sessione e torna `date`. Il risultato oggi è
giusto, perché il fuso entra e esce dalla stessa sessione. Ma il calcolo di un giorno passa da un
istante, e se ne pagano tre conseguenze:

* **Due forme della stessa regola.** Dove il giorno viene da `fn_giorno_operativo`, la forma
  scritta è `date_trunc('month', giorno::timestamp)::date`, che evita il fuso della sessione ma è
  un `timestamp` nudo. Il cancello §11.10 la ferma, e ogni volta va dichiarata.
* **La dichiarazione si moltiplica da sola.** `vw_dash_competenza_attivita` dipende da
  `vw_lotti_fase`. Ogni changeSet che ricrea `vw_lotti_fase` ricrea anche lei dalla definizione
  viva, e ne ricopia il cast: così sono nati `20261020-80`, `20261107-94`, `20261114-07`, ciascuno
  con la sua dichiarazione. Finché la definizione viva porta il cast, la prossima ricreazione lo
  ricopierà.
* **Il calcolo è `STABLE` invece che `IMMUTABLE`.** Una funzione o un'espressione che lo contiene
  non può stare in un indice, in una colonna generata o in un CHECK, anche quando il suo
  significato è puramente di calendario.

Il gemello è **l'ultimo giorno del mese**, scritto `(date_trunc('month', x) + interval '1 month -
1 day')::date`: stessa strada, più un `interval` che sommato a una data restituisce un
`timestamp`.

## 2. Ricognizione sul catalogo vivo (fatto del 2026-11-15, scratch `zeroerp_ruoli`)

La struttura si legge dal catalogo (`pg_get_viewdef`, `pg_proc.prosrc`, `pg_constraint`,
`pg_index`, `pg_attrdef`). ⚠️ Per una funzione `BEGIN ATOMIC` il corpo non sta in `prosrc`
(linee-guida §5c): al giro 1 il censimento si rifà con `pg_get_functiondef`.

### 2.1 Il `::timestamp` esplicito

* `vendite.vw_dash_competenza_attivita`, colonna `emessa_in_ritardo`: l'unica vista viva che lo
  porta. È la sorgente delle tre dichiarazioni; la terza (`20261114-07`) è stata aggiunta il
  2026-11-15 per far passare il cancello, in testa al file, fuori dal checksum.
* `vendite.fn_genera_scadenze_fattura`: `date_trunc('month', v_data_rata::timestamp) + interval
  '1 month - 1 day'`. Nata prima del perimetro del cancello (`20260920`).

### 2.2 Il mese di un giorno, `date_trunc('month', <date>)`

* **Viste** (7): `vw_dash_backlog_documenti`, `vw_dash_competenza_attivita`,
  `vw_dash_competenza_errori`, `vw_dash_fatturazione_ddt`, `vw_dash_fatturazione_offerte`,
  `vw_dash_fatturazione_ordini`, `vw_dash_fatturazione_preventivi`.
* **Funzioni di `vendite`** (19): `fn_accredita_riga_reso`, `fn_aggiungi_onere_commessa`,
  `fn_calcola_data_documento`, `fn_canone_periodi`,
  `fn_contratti_addebiti_maturati_con_provenienza`, `fn_create_fatturazione_lotto`,
  `fn_diagnostica_gruppi_fatturabili`, `fn_genera_scadenze_fattura`, `fn_get_next_progressivo`,
  `fn_get_or_create_lotto`, `fn_get_pavimento_emissione`, `fn_list_commessa_attivita`,
  `fn_list_commesse_emittibili`, `fn_list_ddt_da_pushare`, `fn_list_emittibili_lane`,
  `fn_list_ordini_da_pushare`, `fn_list_preventivi_da_pushare`,
  `fn_select_attivita_fatturabili`, `fn_upsert_commessa_attivita`.
* **Helper pgTAP di `dbops`** (4): `fn_pgtap_crea_commessa`, `fn_pgtap_crea_commessa_attivita`,
  `fn_pgtap_crea_consumo`, `fn_pgtap_crea_lotto`.
* `script.fn_giorno_operativo` nomina `date_trunc` solo nel commento (lo sostituisce per gli
  istanti): non è una copia.

Gli usi sono di due specie, e la sostituzione è la stessa:

* **normalizzare un parametro** (`date_trunc('month', p_competenza_mese)::date`, nei lister e nei
  builder del lotto);
* **proiettare o filtrare una colonna `date`** (`date_trunc('month', d.data)::date =
  p_competenza_mese`, nei lister `*_da_pushare` e nelle viste).

### 2.3 L'ultimo giorno del mese

Nove copie in sette funzioni: `fn_calcola_data_documento`, `fn_canone_periodi` (2),
`fn_contratti_addebiti_maturati_con_provenienza`, `fn_genera_scadenze_fattura`,
`fn_get_pavimento_emissione` (2), `fn_pgtap_crea_commessa`, `fn_pgtap_crea_commessa_attivita`.
Sono tutte funzioni già nell'elenco del §2.2.

### 2.4 La stessa regola, dal lato del vincolo

Tre CHECK dicono «è il primo del mese» con `EXTRACT(day FROM competenza_mese) = 1`:
`vendite.attivita_fatturabili.chk_attivita_competenza_mese_primo`,
`vendite.preventivi.chk_preventivi_competenza_mese_primo`,
`vendite.commesse_attivita.chk_commesse_attivita_comp_mese_primo`. È la regola del §4.1 scritta in
una terza forma (D-1).

### 2.5 Che cosa non c'è

Nessun indice, default o colonna generata col calcolo; nessuna altra forma dello stesso
significato (`make_date`, `to_char(…, 'YYYY-MM')`, `- (extract(day …) - 1)`). `script.fn_segment_key`
formatta un mese già calcolato (`to_char(p_mese, 'YYYY-MM')`): non è una copia.
`fn_canone_periodi` ha anche `make_date(anno, 12, 31)` e aritmetica di mesi (`make_interval`,
`generate_series(…, interval '1 month')`): è il tema di D-2.

## 3. Perimetro (deciso da Tid il 2026-11-15)

**Tutte le copie** del §2.2 e del §2.3, nello stesso cantiere: la regola del 2 (AGENTS.md) vuole
il building block e il ritiro delle copie nello stesso giro, e un BB accanto alle copie sarebbe
una terza versione. **L'ultimo giorno del mese entra** con il mese.

## 4. Il progetto

### 4.1 Due building block in `script`

```text
script.fn_mese_di(p_giorno date)      RETURNS date   -- il primo giorno del mese di p_giorno
script.fn_fine_mese_di(p_giorno date) RETURNS date   -- l'ultimo giorno del mese di p_giorno
```

* **Solo aritmetica di `date`**: `date - integer` e `date + integer` restituiscono `date`. Il
  primo del mese è `p_giorno - (EXTRACT(day FROM p_giorno)::int - 1)`; la fine del mese è il
  giorno prima del primo del mese successivo, e il mese successivo si raggiunge con
  `fn_mese_di(p_giorno) + 31` (dal primo di un mese, 31 giorni dopo si è sempre nel mese seguente,
  mai in quello dopo ancora). Niente `interval`, niente `timestamp`, niente fuso.
* **`IMMUTABLE`, `STRICT`, `PARALLEL SAFE`**: NULL → NULL, e il calcolo vale in ogni indice, CHECK
  o colonna generata.
* **`LANGUAGE sql` con corpo a stringa**, non `BEGIN ATOMIC`: non legge tabelle, quindi non ha
  dipendenze da tenere in `pg_depend` (§5c), e una funzione SQL semplice viene espansa dal
  planner nel punto in cui la si chiama. Nelle viste e nei filtri non costa una chiamata.
* Il COMMENT dice che cosa restituiscono e che lavorano su un **giorno**: un istante passa prima
  da `fn_giorno_operativo`.
* Pagina `manual/` per ciascuna, nella famiglia di `fn_giorno_operativo`.

### 4.2 La sostituzione

* `date_trunc('month', x)::date` → `script.fn_mese_di(x)`, con `x` di tipo `date`.
* `date_trunc('month', fn_giorno_operativo(t)::timestamp)::date` →
  `script.fn_mese_di(script.fn_giorno_operativo(t))`.
* `(date_trunc('month', x) + interval '1 month - 1 day')::date` → `script.fn_fine_mese_di(x)`.
* ⛔ **Dove l'argomento è un istante** (`timestamptz`), la sostituzione non è meccanica: il
  giorno si prende prima con `fn_giorno_operativo`. Nel censimento del §2 gli argomenti sono tutti
  `date`; al giro 3 lo si verifica sul tipo di ogni argomento, non sul nome della variabile.
* Il corpo di ogni oggetto si prende dal **catalogo vivo** al momento di scrivere il changeSet
  (con `SET search_path = pg_catalog`, §5c), mai da uno YAML: questi oggetti sono anche nei
  cantieri vicini e cambiano di settimana in settimana.

### 4.3 Il cancello: la porta si chiude

⚠️ *Superato dal giro 1 (§6.1): la regola scritta si chiama `date-trunc` e guarda ogni
`date_trunc(`, non solo il mese.* Il testo d'origine: una regola nuova in
`scripts/guardrail_forme_changeset.py` (`mese-dal-calendario`), con perimetro dai changeSet del
giro 1, che rifiuta `date_trunc('month'` e `interval '1 month - 1 day'` nella sezione `changes`,
con il rimando ai due BB. Esclusione dichiarata in testa al file, come per le altre regole. È
questa regola che impedisce alle copie di tornare; il presidio §4.4 lo dice sul database vivo.

Le tre dichiarazioni `timestamp-senza-fuso` già scritte (`20261020-80`, `20261107-94`,
`20261114-07`) restano: descrivono il contenuto di quei file, che non cambia. Dal giro 2 nessun
changeSet nuovo ne avrà bisogno.

### 4.4 Il presidio vivo

`db/pgtap/script/test-mese-di-un-giorno-v1.sql`:

* **i casi costruiti** dei due BB: primo e ultimo giorno del mese, 29 febbraio di un anno
  bisestile, 28 febbraio di uno che non lo è, 31 dicembre → mese di dicembre e fine 31 dicembre,
  1° gennaio, NULL; volatilità `IMMUTABLE` letta da `pg_proc`;
* **l'equivalenza col calcolo di oggi**, su ogni giorno di un intervallo costruito che copre
  bisestili e cambi d'ora, sotto **due** `TimeZone` di sessione (`UTC` ed `Europe/Rome`): è la
  prova che la sostituzione non cambia nessun risultato;
* **l'invariante sul catalogo** (giro 4): nessuna vista (`pg_get_viewdef`) e nessuna funzione
  (`pg_get_functiondef`) degli schemi applicativi contiene `date_trunc('month'` o
  `1 mon -1 day`, salvo dichiarazione. Il testo che PostgreSQL stampa va letto prima di scrivere
  il pattern (`'1 mon'::interval`, `'month'::text`).

## 5. Decisioni per Tid

* **D-1 · I tre CHECK del §2.4.**
  (a) diventano `CHECK (competenza_mese = script.fn_mese_di(competenza_mese))`: la regola ha una
  sede sola, e il BB è `IMMUTABLE` proprio per poterlo fare. Il vincolo si toglie e si rimette
  in `00_schema`, con la rivalidazione delle righe (sono già conformi, il vincolo di oggi lo
  garantisce).
  (b) restano `EXTRACT(day …) = 1`: dicono la stessa cosa e non dipendono da una funzione.
  ✅ **Decisa (a)** (Tid, 2026-11-15).
* **D-2 · L'aritmetica dei mesi** (`+ interval '1 month'`, `make_interval(months => n)`,
  `generate_series(…, interval '1 month')`, in `fn_canone_periodi` e
  `fn_get_pavimento_emissione`). Sommata a una `date` restituisce un `timestamp` nudo, ed è la
  stessa famiglia.
  (a) fuori da questo cantiere, registrata come debito con un rimando;
  (b) dentro, con un terzo BB (`fn_mesi_dopo(date, int)`).
  ✅ **Decisa (a)** (Tid, 2026-11-15). È un significato diverso (sommare mesi, con la regola del
  giorno che non esiste nel mese d'arrivo), e i consumatori vanno letti uno per uno; la regola del
  §4.3 non la tocca. Alla chiusura di questo brief il debito passa a un brief nuovo «aperto, non
  iniziato» (AGENTS.md, «Un tema, un brief»).
* **D-3 · I filtri su una colonna** (`fn_mese_di(d.data) = p_competenza_mese` nei lister
  `*_da_pushare`). La sostituzione del §4.2 lascia il filtro com'è, con la funzione applicata
  alla colonna.
  (a) si sostituisce e basta;
  (b) già che si tocca, si riscrive come intervallo (`d.data BETWEEN p_competenza_mese AND
  fn_fine_mese_di(p_competenza_mese)`), che un indice su `data` può usare.
  *Proposta: (a).* Il cantiere è un cambio di forma a risultato identico, e la prova del §4.4 lo
  dimostra; un cambio di piano va provato con il metodo del §13, ed è un altro lavoro.

  **Verifica degli indici** (catalogo dello scratch, 2026-11-15; Tid ricordava un indice già
  fatto). Gli indici ci sono, ma **sulla parte del modello che conserva il mese**, non sui
  documenti:
  * `competenza_mese` è una **colonna** con il suo indice in `attivita_fatturabili`
    (`ix_attivita_fatturabili_competenza_mese`, `ix_attivita_billing_competenza`) e in
    `commesse_attivita` (`ix_commesse_attivita_lane_candidate`). Lì il filtro è già
    `competenza_mese = <mese del parametro>`: la funzione sta sul parametro, non sulla colonna,
    e l'indice si usa. La sostituzione non cambia niente.
  * Sui documenti (`ddt.data`, `ordini.data`, `preventivi.data`/`validita_dal`) il mese **non si
    conserva**: si calcola dalla data. Lì `data` è solo l'**ultima** colonna di indici composti
    (`ix_ddt_vendita_dest_stato_data` e `ix_ordini_v_cliente_statoid_data`, che partono dal
    soggetto e dallo stato); su `preventivi` non c'è nessun indice con quelle colonne. Un filtro a
    intervallo nei lister `*_da_pushare`, che non partono dal soggetto, non userebbe nessuno di
    questi indici.
  * Nessun filtro del mese è già scritto a intervallo.

  Quindi «non sempre» è la descrizione giusta: dove il mese è una colonna c'è l'indice e il filtro
  lo usa; dove si calcola dalla data, non c'è un indice che l'intervallo potrebbe usare. La (b)
  oggi cambierebbe la forma senza cambiare il piano; servirebbe solo insieme a un indice nuovo,
  ed è il lavoro del §13. ✅ **Decisa (a)** (Tid, 2026-11-15).

## 6. Giri

Ogni giro: changeSet scritti nella forma definitiva, provati con `scripts/prova_changeset.py`
(insieme al pgTAP del giro), poi apply e pgTAP di Tid. I numeri li dà Tid.

### 6.1 Giro 1 — i building block

* `20_code/script`: `fn_mese_di`, `fn_fine_mese_di` (§4.1), GRANT come le altre di `script`.
* pgTAP §4.4, prime due parti.
* La regola `mese-dal-calendario` del §4.3, con perimetro dal primo changeSet del giro 2: il
  giro 1 non ha copie da ritirare, e la regola non deve bloccare i cantieri vicini prima che i
  BB esistano.
* Le due pagine `manual/`.

**✅ Fatto il 2026-11-15** (via di Tid, numeri `-82…-83`). **Applicato, pgTAP verde** (Tid,
2026-11-15).

* `20_code/script/20261114-82-create-fn-mese-di` e `-83-create-fn-fine-mese-di`, come il §4.1.
  `STRICT` è il significato (il mese di nessun giorno è nessun mese), non igiene: il pgTAP lo
  asserisce (linee-guida §13). La preCondition di `-83` chiede che `fn_mese_di` esista: sullo
  scratch, prima di `-82`, dà 0 com'è giusto; all'apply, in ordine, dà 1.
* `db/pgtap/script/test-mese-di-un-giorno-v1.sql`, 16 asserzioni: firma, tipo di ritorno,
  `IMMUTABLE`, `STRICT`, i casi costruiti, l'uguaglianza col calcolo con `date_trunc` su ogni
  giorno 1899-2101 sotto `UTC` ed `Europe/Rome`, l'espansione nel piano.
* **Prova** (`scripts/prova_changeset.py`, scratch, ROLLBACK): estratto eseguito per intero,
  pgTAP 16/16, catalogo identico prima e dopo. **Mutazioni:** fine mese con `+ 28` al posto di
  `+ 31` → rossi 10, 13, 15 e solo quelli; `SET search_path` sulla funzione → rosso 16 e solo
  quello.
* ⚠️ **Il cancello è diverso dal §4.3, e parte prima.** La regola si chiama `date-trunc` e
  rifiuta **ogni** `date_trunc(` nel codice (commenti, letterali e prosa dei COMMENT esclusi):
  nel testo spogliato il primo argomento è un letterale e sparisce, quindi l'unità non si
  distingue, e su un istante `date_trunc` è comunque il fuso della sessione, che
  `fn_giorno_operativo` sostituisce. Le copie di fine mese partono tutte da un `date_trunc`, e la
  stessa regola le prende. **Perimetro dal `20261114-84`**, cioè dal primo changeSet dopo i BB, e
  non dal giro 2: i numeri del giro 2 non si conoscono, e un changeSet di un cantiere vicino che
  ricrea una vista o una funzione con `date_trunc` deve già passare ai BB (è la sostituzione
  stessa) o dichiararsi. Sul perimetro il cancello è verde; sulla storia intera (`--tutto`) trova
  483 righe (fatto del 2026-11-15), che i giri 2-4 tolgono dal vivo. Provato a mano su
  `20261114-07` (lo prende) e sui due BB (verdi).
* `linee-guida-sql.md` §11.10, il paragrafo del §6.4 anticipato qui: la regola è attiva, e chi
  incontra il rosso deve trovarne la sede.
* `docs/it/dbzero/script/manual/fn_mese_di.md` e `fn_fine_mese_di.md` (checklist di
  standard-guide passata). I link alle schede `/dbzero/script/funzioni/fn_mese_di` e
  `fn_fine_mese_di` valgono dopo la rigenerazione della doc auto-generata.

### 6.2 Giro 2 — le viste

Le sette viste del §2.2, ricreate dal vivo con le dipendenti che il DROP porta via (la catena di
`vw_lotti_fase`: `20261114-07` la elenca intera). ⚠️ Stesse viste del cantiere degli stati: il
giro parte quando quel cantiere non ha un giro scritto e non applicato su di loro, e i numeri
vengono dopo i suoi.

**Scritto il 2026-11-15** (numeri di Tid `20261115-01…-07`; il primo range, `20261114-92…-98`,
l'aveva preso nel frattempo l'altra sessione DB in `anagrafiche`, e i file sono stati tolti prima
di qualunque prova). Verificato prima: il cantiere degli stati riparte dal giro 6f (il listino),
nessun suo giro scritto e non applicato tocca queste viste.

| # | Vista | Espressioni |
| --- | --- | --- |
| `-01` | `vw_dash_backlog_documenti` | 2 (i due rami, preventivo e ordine) |
| `-02` | `vw_dash_competenza_attivita` | 1 (`emessa_in_ritardo`, il `::timestamp` del §2.1) |
| `-03` | `vw_dash_competenza_errori` | 1 |
| `-04` | `vw_dash_fatturazione_ddt` | 1 |
| `-05` | `vw_dash_fatturazione_offerte` | 1 (sul `COALESCE` di validità e giorni aziendali) |
| `-06` | `vw_dash_fatturazione_ordini` | 1 |
| `-07` | `vw_dash_fatturazione_preventivi` | 2 |

* ⭐ **`CREATE OR REPLACE VIEW`, non la catena di DROP del §6.2.** Nomi, ordine e tipi delle
  colonne non cambiano (`fn_mese_di` restituisce `date`, come il `::date` che sostituisce), quindi
  le dipendenti restano in piedi (fino a 30 per vista) e COMMENT e GRANT non si toccano.
  `WITH (security_invoker = on)` si ripete: il REPLACE sostituisce le opzioni.
* Il corpo è la definizione viva letta con `SET search_path = pg_catalog`; la sostituzione la fa
  uno script su quel testo, e fallisce se resta un `date_trunc`. Gli argomenti sono tutti `date`
  (PostgreSQL stampa il cast implicito a `timestamptz`, o il `::timestamp` dichiarato). Il
  rollback rimette la definizione di oggi.
* La preCondition chiede la vista e `fn_mese_di`: dà 2 su tutti e sette.
* Guardrail `forme_changeset` e `timestamp_senza_fuso` verdi sui sette file e sul perimetro.
* **Prova** (`scripts/prova_changeset.py`, scratch, ROLLBACK, 2026-11-15): estratto eseguito per
  intero, catalogo identico prima e dopo. I 30 pgTAP che nominano le sette viste hanno lo stesso
  esito senza e con l'estratto. Un rosso c'era già prima ed è lo stesso dopo:
  `ui/test-lista-competenza-gruppi-colonna-emittente-v1` test 7, «almeno una vista del perimetro
  ha righe», cioè il controllo contro il verde per sottrazione. Sullo scratch quelle viste non
  hanno righe, e il cambio non c'entra.
* ✅ **Applicato, pgTAP verdi** (Tid, 2026-11-15).
* ⚠️ Uguale prima e dopo vuol dire che **nessuna regressione è visibile**, non che il mese sia
  provato su queste viste: l'uguaglianza del calcolo la prova `script/test-mese-di-un-giorno-v1`
  (12-15), e la sostituzione è testuale sull'espressione.

### 6.3 Giro 3 — le funzioni di `vendite`

Le 19 funzioni del §2.2, con le nove copie di fine mese del §2.3. Un changeSet per funzione. Per
ciascuna, prima di scrivere: corpo vivo, tipo degli argomenti dei `date_trunc` (§4.2), giri
aperti dei brief vicini che la toccano. `fn_contratti_addebiti_maturati_con_provenienza` e
`fn_upsert_commessa_attivita` sono anche in provenienza-prezzo; i lister `*_da_pushare`,
`fn_get_or_create_lotto`, `fn_create_fatturazione_lotto` e `fn_genera_scadenze_fattura` anche
negli stati.

⛔ **`%TYPE` (Tid, 2026-11-15).** Il corpo vivo (`pg_get_functiondef`) scioglie i `%TYPE` di
firma, `RETURNS TABLE` e `DECLARE` nel tipo nudo: ricopiato così, ogni ancoraggio alla colonna
si perde in silenzio. Per ogni funzione la **firma e il `DECLARE`** si prendono dall'ultimo YAML
che l'ha scritta, verificato uguale al vivo nel corpo, e la sostituzione tocca solo le
espressioni del §4.2. Le variabili nuove, se servono, si ancorano alla colonna con `%TYPE`. Presidi:
`guardrail_forme_changeset.py`, regole `type-perso` e `id-senza-type` (linee-guida-sql §5g).

**Scritto il 2026-11-15** (numeri di Tid `20261115-08…-26`, occupati subito con file scheletro e
poi riempiti; un changeSet per funzione, in ordine alfabetico).

* **Da dove viene il corpo.** Per ognuna delle 19 funzioni, l'ultimo YAML che la crea, con il corpo
  **uguale carattere per carattere** a `prosrc` sul vivo (una sola firma, tutte plpgsql). Il
  `CREATE` d'origine porta firma e `DECLARE` con i loro `%TYPE`. La sostituzione la fa uno script
  sul testo, con le regole del §4.2, e si ferma se resta un `date_trunc`. Gli argomenti sono tutti
  `date`: colonne `date` (`contratti.valido_dal`/`data`, `ordini.data`, `ddt.data`,
  `preventivi.validita_dal`/`data`) o variabili e parametri ancorati a colonne `date`.
* **Tre forme oltre la sostituzione semplice.**
  * `fn_get_pavimento_emissione`: il primo del mese dopo, `(date_trunc + interval '1 month')::date`,
    diventa `fn_fine_mese_di(x) + 1`. È lo stesso giorno, ottenuto senza aritmetica di mesi.
  * `fn_canone_periodi`: dentro `make_interval(months => …)` e `generate_series(…, interval
    '1 month')` resta l'aritmetica dei mesi (D-2, fuori perimetro); cambia solo il giorno di
    partenza, ora `date` da `fn_mese_di` invece di `timestamptz`, con lo stesso giorno. Le due
    copie di fine mese sul passo, `(g + interval '1 month' - interval '1 day')::date`, diventano
    `fn_fine_mese_di(g::date)`.
  * `fn_genera_scadenze_fattura`: il `v_data_rata::timestamp` del §2.1 se ne va con il
    `date_trunc`.
  * I due commenti «date_trunc anche se la competenza è il primo del mese»
    (`fn_calcola_data_documento`, `fn_get_pavimento_emissione`) dicono ora «si tronca al mese»: il
    motivo resta, cambia lo strumento.
* ⭐ **`%TYPE` sugli id (richiamo di Tid, 2026-11-15).** Il cancello `id-senza-type` ha fermato tre
  firme nate con id nudi: `fn_accredita_riga_reso` (`p_resi_riga_id` → `resi_righe.id`; le tre
  colonne id del `RETURNS TABLE` → le colonne omonime di `resi_righe_accrediti`, che quel risultato
  ricalca), `fn_aggiungi_onere_commessa` (le quattro FK di `commesse_attivita`: `commesse`,
  `istanze_utilities`, `articoli`, `tipi_doc_fiscale`), `fn_genera_scadenze_fattura`
  (`p_fattura_id` → `fatture.id`). Lo stesso tipo è verificato sul catalogo, e l'identità della
  funzione non cambia.
* **Prova** (scratch, ROLLBACK, 2026-11-15): estratto eseguito per intero; un pgTAP di servizio
  dopo l'estratto conferma che le 19 funzioni hanno **lo stesso oid, la stessa identità, lo stesso
  risultato e gli stessi attributi** (volatilità, `STRICT`, `SECURITY`, `SET`, costo, righe, ACL,
  owner), e che `plpgsql_check` non trova errori.
* **Regressione** (scratch, ROLLBACK, 2026-11-15, in due corse per l'interruzione qui sotto): i 142
  file di `db/pgtap` che nominano le 19 funzioni. **Nessun esito cambia con l'estratto.** Sette
  file sono rossi già senza l'estratto, con lo stesso numero di rossi dopo:
  `test-soglia-congelamento-sede-unica` (2), `test-fn-available-actions-ddt-reason-catch-all-v1`,
  `test-esito-gruppi-giro-v1`, `test-fn-af-merce-per-riga-chiusura-v1`,
  `test-fn-partite-merce-chiusura-v1`, `test-fn-resi-da-accreditare-chiusura-v1`,
  `test-vw-situazione-merce-ordine-v1` (1 ciascuno). Non provati: `test-vw-giornale-entita`, che
  si interrompe in entrambe le corse; il fixture `S0-fotografia-partita-merce-20260817.md`, che
  non è un test; e **`vendite/test-fn-list-ordini-da-pushare-v1`**, che lo script rifiuta perché
  finisce con `finish()` senza `ROLLBACK;`. ⚠️ Quest'ultimo controlla una funzione del giro
  (`fn_list_ordini_da_pushare`), quindi per quella funzione la prova copre gli altri pgTAP che la
  nominano, non quello.
* ⚠️ **Debito trovato: cinque pgTAP senza `ROLLBACK;`.** Oltre a quello di sopra:
  `config/test-profili-accesso-guard-ultimo-super-admin`,
  `config/test-profili-accesso-bindings-guard-coerenza`,
  `anagrafiche/test-identita-digitali-guard-coerenza`, `script/test-fn-get-uo-id-for-user`. Non
  lasciano dati solo perché `psql -f`, uscendo, annulla la transazione aperta.
  `guardrail_pgtap_preambolo.py` controllava `BEGIN;` ma non la chiusura.
  ✅ **Corretto il 2026-11-15** (Tid: «correggi i 5 pgtap e aggiungi la regola»). `ROLLBACK;` in
  coda ai cinque, dopo `finish()`; nessuna asserzione toccata. Nuova invariante **E** del
  preambolo: ogni `BEGIN;` si chiude con `ROLLBACK;` prima del `BEGIN;` successivo o della fine del
  file, e niente `COMMIT;` (esclusione dichiarabile `-- pgtap-transazione: escluso — <perché>`).
  Misurata su tutto `db/pgtap` prima di scriverla: trovava esattamente i cinque, nessun `COMMIT;`.
  ⚠️ Un vicolo cieco: la prima forma pensata, «l'ultima istruzione è `ROLLBACK;`», segnalava
  anche `anagrafiche/test-soggetti-indirizzi-required` e `-ruoli-indirizzi-required`, che sono
  giusti: `plan()` fuori da ogni transazione, un `BEGIN;` … `ROLLBACK;` per caso, `finish()` dopo.
  La regola guarda le coppie, non la coda. Prove costruite: rossa senza `ROLLBACK`, con `COMMIT`,
  con un `BEGIN` doppio; verde con più transazioni e con `BEGIN` in un commento o in un `DO`.
  Guida pgTAP, §«Le tre righe del preambolo», aggiornata.
  Con il `ROLLBACK;`, `vendite/test-fn-list-ordini-da-pushare-v1` è entrato nella prova del
  giro 3: 10/10 senza e con l'estratto. La regressione del giro copre ora anche quel file.
* ✅ **Applicato, pgTAP verdi** (Tid, 2026-11-15).

### 6.4 Giro 4 — la coda

* I quattro helper pgTAP di `dbops`.
* I tre CHECK (D-1 (a)).
* L'invariante sul catalogo del §4.4.
* ~~`linee-guida-sql.md` §11.10~~: fatto al giro 1 (§6.1).
* Censimento finale con `pg_get_functiondef` (copre le `BEGIN ATOMIC`): zero copie fuori
  dichiarazione.

**Scritto il 2026-11-15** (Tid: «procedi dal primo disponibile», `20261115-27…-33`, occupati
subito con file scheletro; l'altra sessione DB riparte da `-34`).

| # | Dove | Che cosa |
| --- | --- | --- |
| `-27` | `00_schema/vendite` | `attivita_fatturabili.chk_attivita_competenza_mese_primo` |
| `-28` | `00_schema/vendite` | `commesse_attivita.chk_commesse_attivita_comp_mese_primo` |
| `-29` | `00_schema/vendite` | `preventivi.chk_preventivi_competenza_mese_primo` |
| `-30` | `20_code/dbops` | `fn_pgtap_crea_commessa` (1 mese, 1 fine mese) |
| `-31` | `20_code/dbops` | `fn_pgtap_crea_commessa_attivita` (2 mese, 1 fine mese) |
| `-32` | `20_code/dbops` | `fn_pgtap_crea_consumo` (1 mese) |
| `-33` | `20_code/dbops` | `fn_pgtap_crea_lotto` (1 mese) |

* **I CHECK (D-1 (a)).** `competenza_mese = script.fn_mese_di(competenza_mese)`, **stesso nome**:
  chi legge il vincolo da un 23514 non vede differenze. DROP e ADD nello stesso `ALTER TABLE`,
  quindi la tabella non resta mai senza vincolo; un COMMENT che dice la regola. NULL passa come
  prima, perché un CHECK NULL è soddisfatto. **Ordine da zero (§11.14):** due vincoli nascono nella
  prima generazione (`migrations/00_bootstrap`, inclusa in testa al master v2), il terzo in
  `20260224-07`; `fn_mese_di` nasce in `20261114-82`, e `00_schema` e `20_code` girano mescolati
  per numero. Il nuovo vincolo dice la stessa cosa del vecchio, quindi nessuno di chi scrive le
  tabelle (seed, funzioni, fixture) può essere rifiutato. Nessuno dei tre nomi compare in
  `80_data`, `90_end` o nel backend.
* **Gli helper.** Stesso metodo del giro 3: ultimo YAML uguale al vivo, `%TYPE` conservati,
  generatore che si ferma su un `date_trunc` residuo. Argomenti tutti `date`
  (`fn_data_operativa()`, variabili e parametri ancorati a colonne `date`). Il cancello
  `id-senza-type` non ha trovato id nudi.
* **Il presidio vivo** in `script/test-mese-di-un-giorno-v1`, ora 18 asserzioni:
  * **17**: nessuna vista e nessuna funzione degli schemi applicativi contiene `date_trunc(`.
    Il testo delle funzioni viene da `pg_get_functiondef`, che copre anche le `BEGIN ATOMIC`. I
    commenti `--` si tolgono prima di cercare: `fn_giorno_operativo` nomina `date_trunc` nel
    suo, per dire che lo sostituisce. Le estensioni si escludono per dipendenza. Sul vivo, prima
    del giro 4, trova esattamente i quattro helper.
  * **18**: i tre CHECK sono `fn_mese_di(competenza_mese)` e nessuno usa più `EXTRACT`. I nomi si
    leggono dal catalogo, non da `regclass::text`, che dipende dal `search_path`.
* **Prova** (scratch, ROLLBACK, 2026-11-15): estratto eseguito per intero, catalogo identico
  dopo. `test-mese-di-un-giorno-v1`: 16 ok e 2 rossi senza l'estratto (17 e 18, come deve
  essere), 18 su 18 con, anche con `PGTZ=Pacific/Kiritimati`. **Regressione** su 129 pgTAP che
  usano i quattro helper o scrivono nelle tre tabelle: **nessun esito cambia** a parte il test del
  mese. Sono rossi già senza l'estratto, con lo stesso numero di rossi dopo:
  `test-fn-get-stato-push-segment-v1`, `test-annullo-documento-con-legami-v1`,
  `test-esito-gruppi-giro-v1`, `test-fn-partite-merce-chiusura-v1`,
  `test-fn-resi-da-accreditare-chiusura-v1`, `test-fn-situazione-merce-ordine-chiusura-v1`
  (1 ciascuno), `test-refactor-qta-operativa-preventivi-v1` (5).
* ⚠️ **Debito trovato: due pgTAP con un `DO` di pulizia prima del `BEGIN;`.**
  `anagrafiche/test-billing-account-guard-parent` e
  `vendite/test-commessa-sorgente-emittente-omogeneo-v1` cominciano con un blocco `DO` che fa
  `DELETE` delle righe di prova di corse vecchie (`TST-GUARD-PARENT-%`, `TST-SORG-EMITT-%`). È
  fuori dalla transazione, quindi viene confermato a ogni esecuzione. Sono residui di quando i
  test confermavano i dati; con l'invariante E del preambolo quelle righe non possono più
  nascere. In più `prova_changeset.py` rifiuta i due file, che restano fuori dalle regressioni
  (anche da questa). ✅ **Corretto il 2026-11-15** (Tid: «correggi i 2 file»): i due `DO` sono
  tolti, e al loro posto c'è un commento che dice perché. Prima di toglierli: nessuna riga con
  quei codici né sullo scratch né su dbdev, quindi i codici fissi che il primo test crea ancora
  (`TST-GUARD-PARENT-IU-01…03`) non trovano doppioni. Asserzioni invariate; preambolo verde.
  Provati col giro 4: 7/7 e 7/7 senza e con l'estratto. La regola sulla prima istruzione non è
  stata chiesta, e non c'è.
* ✅ **Giro 4 applicato, pgTAP verdi** (Tid, 2026-11-15).

## 7. Backend e frontend

**Dalla parte DB, nulla si rompe.** Le firme non cambiano, i risultati sono identici (§4.4),
nessuna colonna di vista cambia nome o tipo. Il frontend non è toccato.

**Richiesta al team BE (R-BE-1), dopo l'apply del giro 1.** Il backend scrive lo stesso calcolo
nel suo SQL: sono copie della regola su un altro livello (PROJECT_CONTEXT, «no logica duplicata»).
Ricognizione del 2026-11-15, `grep` su `backend/` esclusi i test:

| File | Riga | Oggi | Diventa |
| --- | --- | --- | --- |
| `backend/apps/vendite/db/commesse_repository.py` | 821 | `date_trunc('month', %s::date)::date` | `script.fn_mese_di(%s::date)` |
| `backend/apps/vendite/db/commesse_repository.py` | 1857 | `ca.competenza_mese = date_trunc('month', %s::date)::date` | `… = script.fn_mese_di(%s::date)` |
| `backend/apps/vendite/db/vendite_repository.py` | 1003 | `date_trunc('month', f_r.data)::date = %s` | `script.fn_mese_di(f_r.data) = %s` |
| `backend/apps/vendite/db/vendite_repository.py` | 1807 | `date_trunc('month', competenza_mese)::date AS mese` | `script.fn_mese_di(competenza_mese) AS mese` |
| `backend/apps/vendite/db/vendite_repository.py` | 3017 | `date_trunc('month', e.competenza_mese)::date = %s` | `script.fn_mese_di(e.competenza_mese) = %s` |
| `backend/apps/core/db/maintenance_repository.py` | 344 | `to_char(date_trunc('month', script.fn_giorno_operativo(started_at)::timestamp), …)` | `to_char(script.fn_mese_di(script.fn_giorno_operativo(started_at)), …)` |

I commenti vicini (`vendite_repository.py` 1800 e 3015, `maintenance_repository.py` 340) parlano
di `date_trunc` e vanno riletti insieme. Elenco chiuso alla data: il BE lo rifà sul suo albero
prima di cambiare. Chi cambia per primo: il DB (i BB devono esistere); il BE non ha scadenza
legata ai giri 2-4, che non cambiano niente di ciò che legge.
