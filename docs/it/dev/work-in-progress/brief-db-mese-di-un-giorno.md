# Brief DB — Il mese di un giorno si calcola sul calendario, non passando da un istante

## ⏭️ Chi riparte — aggiornato al 2026-11-15

**Riparte: Tid**, col via allo sviluppo e il range dei numeri. D-1, D-2 e D-3 decise (a) il
2026-11-15.
Il progetto è scritto (§4) e la ricognizione è fatta (§2). **Nessun changeSet, nessun pgTAP,
nessuna modifica a script scritti.**

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ team DB | Ricognizione sul catalogo vivo, progetto, giri (2026-11-15) | §2, §4, §6 | — |
| 1b | ✅ Tid | Perimetro: tutte le copie, fine mese compreso (2026-11-15) | §3 | 1 |
| 2 | ✅ Tid | D-1 (a), D-2 (a), D-3 (a) (2026-11-15) | §5 | 1b |
| 2b | **Tid** ⏭️ | Il via allo sviluppo e il range dei numeri | — | 2 |
| 3 | team DB | Giro 1: i due building block, il loro pgTAP, la regola del cancello | §6.1 | 2 |
| 4 | Tid | Apply del giro 1 e pgTAP | §6.1 | 3 |
| 4b | team BE | R-BE-1: le sei copie nel SQL del backend passano ai BB | §7 | 4 |
| 5 | team DB | Giro 2: le viste | §6.2 | 4 e il giro in corso di stati-dal-vocabolario sulle stesse viste |
| 6 | team DB | Giro 3: le funzioni di `vendite` | §6.3 | 4, coordinato con i brief vicini (§1) |
| 7 | team DB | Giro 4: helper pgTAP, CHECK (D-1), presidio vivo, doc | §6.4 | 5, 6 |
| 8 | Tid | Apply dei giri 2-4, pgTAP, regressione | §6 | 5, 6, 7 |
| 9 | team DB | Chiusura e archiviazione | — | 8, 4b |

**Decisioni aperte di Tid:** nessuna. Decise il 2026-11-15: D-1 (a), D-2 (a), D-3 (a) (§5). **Lavoro da committare:** questo brief e la riga
di dichiarazione aggiunta in testa a `20261114-07` (§2.1), che non entra nel checksum.

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

Una regola nuova in `scripts/guardrail_forme_changeset.py` (`mese-dal-calendario`), con perimetro
dai changeSet del giro 1: rifiuta `date_trunc('month'` e `interval '1 month - 1 day'` nella
sezione `changes`, con il rimando ai due BB. Esclusione dichiarata in testa al file, come per le
altre regole. È questa regola che impedisce alle copie di tornare; il presidio §4.4 lo dice sul
database vivo.

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

### 6.2 Giro 2 — le viste

Le sette viste del §2.2, ricreate dal vivo con le dipendenti che il DROP porta via (la catena di
`vw_lotti_fase`: `20261114-07` la elenca intera). ⚠️ Stesse viste del cantiere degli stati: il
giro parte quando quel cantiere non ha un giro scritto e non applicato su di loro, e i numeri
vengono dopo i suoi.

### 6.3 Giro 3 — le funzioni di `vendite`

Le 19 funzioni del §2.2, con le nove copie di fine mese del §2.3. Un changeSet per funzione. Per
ciascuna, prima di scrivere: corpo vivo, tipo degli argomenti dei `date_trunc` (§4.2), giri
aperti dei brief vicini che la toccano. `fn_contratti_addebiti_maturati_con_provenienza` e
`fn_upsert_commessa_attivita` sono anche in provenienza-prezzo; i lister `*_da_pushare`,
`fn_get_or_create_lotto`, `fn_create_fatturazione_lotto` e `fn_genera_scadenze_fattura` anche
negli stati.

### 6.4 Giro 4 — la coda

* I quattro helper pgTAP di `dbops`.
* I tre CHECK (D-1 (a)).
* L'invariante sul catalogo del §4.4.
* `linee-guida-sql.md` §11.10: un paragrafo «il mese di un giorno», che rimanda ai due BB e
  toglie la ragione per cui oggi si dichiara il `::timestamp` su un giorno.
* Censimento finale con `pg_get_functiondef` (copre le `BEGIN ATOMIC`): zero copie fuori
  dichiarazione.

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
