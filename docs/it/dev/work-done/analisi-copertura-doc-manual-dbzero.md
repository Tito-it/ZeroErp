# Copertura documentazione manuale `docs/it/dbzero` — il buco misurato

> Analisi del 2026-08-21 — **misura**, non piano approvato.
> Riguarda solo `docs/it/dbzero/<schema>/manual/`: la doc concettuale scritta a mano
> che si affianca a quella auto-generata da `scripts/gen_db_docs.py`.
>
> ### 📌 Stato al 2026-08-21 — **CANTIERE CHIUSO**
>
> **Copertura: 99,4 %** — 8 oggetti senza pagina manuale su 1279, e sono **esattamente** gli 8
> della fascia H, lasciati così per decisione esplicita.
>
> Tutte le fasce sono chiuse: **A** (35 trigger function), **C** (9 viste), **E** (12 presidio
> codici errore), **B** (10 verbi e check), **D** (14 tabelle), **I** (102 storico + pagina
> condivisa), **F** (39 magazzino e acquisti), **G** (18 fixture e utility). **H**: si lasciano
> dove sono.
>
> Partenza: **247** oggetti senza documentazione, copertura 80,7 %.
>
> ⛔ **Migrati e verdi** anche i quattro interventi sul database emersi strada facendo (§7 e
> §4/C): lock su `offerte_commerciali.codice`, lock su `preventivi_righe.natura_vendita_id`,
> generazione automatica di `vettori.codice`, `security_invoker` sulle 7 viste
> `vw_stato_sorgente_*`.
>
> 🔴 **Resta aperto un difetto trovato e non corretto**: il CHECK
> `chk_mag_movimenti_da_destinazione_distinti` su `magazzino.movimenti` rende inseribili **solo
> i trasferimenti** — un carico o uno scarico semplice viene rifiutato. È latente perché il
> dominio magazzino è vuoto. Dettaglio e forma corretta nella pagina di `magazzino.movimenti`.

---

## 1. Come è stata fatta la misura

`scripts/gen_db_docs.py` scrive in testa a ogni file auto-generato un tag `include-markdown`
che punta a `it/dbzero/<schema>/manual/<nome>.md` — **solo se quel file manuale esiste già**
(funzione `include_manual`, righe 54-58). Quindi:

> **un documento auto-generato che NON comincia con il tag `include-markdown` è
> esattamente un oggetto senza doc manuale.**

Il conteggio è quello, su tutti i `.md` in `<schema>/tabelle|views|funzioni`:

```bash
cd docs/it/dbzero
find . -path './*/tabelle/*.md' -o -path './*/views/*.md' -o -path './*/funzioni/*.md' \
  | while read -r f; do head -3 "$f" | grep -q 'include-markdown' || echo "$f"; done
```

Le date di comparsa citate più sotto vengono da `git log --diff-filter=A` sul file auto-generato.

## 2. Perché il buco non si vede

Non produce nessun errore di build, e nemmeno un warning. Produce due effetti silenziosi:

1. In `<schema>/index.md` l'oggetto **c'è**, ma come link nudo, senza la riga di descrizione
   (`- [fn_accoda_stampe_lotto](funzioni/fn_accoda_stampe_lotto.md)` e basta).
2. In `<schema>/index.ci.md` — l'indice «solo contenuti manuali» — l'oggetto **non compare
   affatto**. Chi consulta quell'indice non sa che l'oggetto esiste.

Non esiste oggi nessun guardrail CI su questa copertura (`scripts/` ha solo
`guardrail_no_db_migrate.py`, `guardrail_pgtap_preambolo.py`, `guardrail_run_on_change.py`).

## 3. I numeri

- **1278** documenti auto-generati (tabelle + views + funzioni) su 16 cartelle schema
  popolate (`contabilita`, `preventivi`, `public`, `tools`, `topology` sono vuote).
- **247** senza doc manuale alla misura iniziale → copertura **80,7 %**.
  Dopo la fascia A: **212** → **83,4 %**. Dopo la fascia C: **203** → **84,1 %**.
- Ripartizione per tipo alla misura iniziale: **155 tabelle**, **73 funzioni**, **19 viste**.
  Oggi: **155 tabelle**, **38 funzioni** (fascia A fatta), **10 viste** (fascia C fatta).
  ⚠️ Le tabelle non sono calate di una sola unità: **102 su 155 sono `storico`**, e la
  decisione su come trattarle (fascia I) è ancora aperta.
- **0** casi di tag `include-markdown` che punta a un file manuale mancante: il buco è
  sempre e solo «manuale mai scritto», mai «manuale cancellato».
- **5** file manuali orfani (§5).

| Schema | tabelle | views | funzioni | mancanti | tot autogen | copertura |
|---|---:|---:|---:|---:|---:|---:|
| `storico` | 102 | — | — | **102** | 111 | 8% |
| `magazzino` | 25 | 4 | 2 | **31** | 32 | 3% |
| `vendite` | — | 5 | 21 | **26** | 375 | 93% |
| `dbops` | 5 | 4 | 16 | **25** | 116 | 78% |
| `script` | — | — | 15 | **15** | 154 | 90% |
| `config` | 11 | 2 | 1 | **14** | 139 | 90% |
| `anagrafiche` | 2 | 4 | 6 | **12** | 139 | 91% |
| `acquisti` | 6 | — | 2 | **8** | 11 | 27% |
| `pratiche` | — | — | 7 | **7** | 96 | 93% |
| `catalogo` | 2 | — | 3 | **5** | 27 | 81% |
| `maintenance` | 1 | — | — | **1** | 19 | 95% |
| `pagamenti` | 1 | — | — | **1** | 17 | 94% |

In tabella solo gli schemi con almeno un buco: `documenti` (21), `ui` (19) e `shop` (2)
sono al 100 %.

Il buco non è un arretrato di un periodo: le date di comparsa si distribuiscono su tutta la
storia del repo, con **30 oggetti nati nel solo agosto 2026** (presidio codici errore,
riferimenti morti, accrediti resi, guard immutabilità).

---

## 4. Le fasce, in ordine di quanto costa non averle

### ✅ Fascia A — regole di business non descritte da nessuna parte (35 trigger function) — **CHIUSA 2026-08-21**

Sono i `trgfn_*`: guard di transizione, default, snapshot, normalizzazioni. Il corpo SQL è
nell'auto-gen, ma **il perché** (quale regola di dominio difendono, quale codice errore
sollevano, che cosa rompe toglierli) non era scritto. Era la fascia che valeva di più.

**Tutti e 35 i manuali sono stati scritti.** Ogni pagina riporta: scopo di dominio, aggancio
esatto (trigger, timing, `UPDATE OF`, clausola `WHEN`), regole applicate, tabella dei codici
errore e le trappole emerse leggendo il codice. Elenco sotto, per riferimento.

Le trappole ricorrenti trovate scrivendo — utili di per sé, indipendentemente dalla doc:

* **La condizione che rende il guard corretto sta spesso nel `WHEN` del trigger, non nella
  funzione.** Vale per `trgfn_unita_misura_guard_tipo_update`,
  `trgfn_sospensioni_giornale_riattivazione`,
  `trgfn_contratti_righe_guard_esclusione_figlio_bundle`. Riagganciare la funzione altrove
  senza copiare il `WHEN` cambia il comportamento in silenzio.
* **L'ordine alfabetico dei `BEFORE ROW` decide quale errore vede l'utente.** Su
  `vendite.preventivi` `guard_annullamento` parla prima di `guard_transizione`; sui
  `gen_codice`, `gen_codice` gira prima di `lock_columns`.
* **Due `E_GENERICO` nello schema `catalogo`** (`trgfn_unita_misura_guard_tipo_update`,
  `trgfn_uom_conversioni_guard_tipo`) e **una `RAISE EXCEPTION` diretta**
  (`trgfn_event_log_append_only`, che quindi non registra nulla in `error_log`).
* **Tre presidi che il database non ha**, scoperti confrontando tabelle gemelle:
  `vendite.offerte_commerciali.codice` senza `lock_columns` (un `UPDATE` che lo azzera ne
  rigenera uno nuovo), `vendite.preventivi_righe.natura_vendita_id` modificabile a mano
  aggirando l'ereditarietà, `anagrafiche.vettori.codice` `NOT NULL` senza nessun generatore.
* **`trgfn_vettori_normalize` è un no-op** e il suo `COMMENT` rimanda a un `sistema_codici`
  che per i vettori non ha nessuna riga.

- `anagrafiche.trgfn_billing_account_gen_codice` — dal 2026-01-18
- `anagrafiche.trgfn_fornitori_gen_codice` — dal 2026-03-29
- `anagrafiche.trgfn_istanze_utilities_gen_codice` — dal 2026-01-18
- `anagrafiche.trgfn_soggetti_gen_codice` — dal 2026-01-18
- `anagrafiche.trgfn_vettori_guard_ruolo_vettore`
- `anagrafiche.trgfn_vettori_normalize`
- `catalogo.trgfn_articoli_seed_uom_base` — dal 2026-04-07
- `catalogo.trgfn_unita_misura_guard_tipo_update` — dal 2026-04-28
- `catalogo.trgfn_uom_conversioni_guard_tipo` — dal 2026-04-28
- `config.trgfn_stati_doc_guard_esito_verdetto` — dal 2026-07-02
- `pratiche.trgfn_calcoli_tempo_set_periodo` — dal 2026-04-13
- `pratiche.trgfn_flussi_guard_esito_completato` — dal 2026-06-08
- `pratiche.trgfn_pratiche_gen_codice` — dal 2026-03-29
- `pratiche.trgfn_sospensioni_giornale_ins` — dal 2026-03-06
- `pratiche.trgfn_sospensioni_giornale_riattivazione` — dal 2026-03-06
- `pratiche.trgfn_sospensioni_set_periodo` — dal 2026-04-13
- `script.trgfn_righe_default_fonte_qta`
- `vendite.trgfn_attivita_fatturabili_guard_quantita_immutabile` — dal 2026-07-21
- `vendite.trgfn_commesse_attivita_guard_prezzo_rettifica` — dal 2026-08-20
- `vendite.trgfn_commesse_attivita_guard_quantita_immutabile` — dal 2026-07-21
- `vendite.trgfn_contratti_default_valuta` — dal 2026-05-30
- `vendite.trgfn_contratti_righe_guard_esclusione_figlio_bundle` — dal 2026-05-16
- `vendite.trgfn_contratti_set_categoria_cliente_snapshot` — dal 2026-04-17
- `vendite.trgfn_contratti_sync_is_abortito_snapshot` — dal 2026-05-21
- `vendite.trgfn_contratti_utilities_guard_tipo_classe` — dal 2026-04-14
- `vendite.trgfn_event_log_append_only` — dal 2026-02-27
- `vendite.trgfn_listini_righe_guard_tipologia` — dal 2026-04-14
- `vendite.trgfn_lotto_fatture_guard_stato_coerente` — dal 2026-07-22
- `vendite.trgfn_offerte_commerciali_default_valuta` — dal 2026-05-30
- `vendite.trgfn_offerte_commerciali_gen_codice` — dal 2026-05-25
- `vendite.trgfn_offerte_commerciali_guard_transizione` — dal 2026-05-24
- `vendite.trgfn_preventivi_default_valuta` — dal 2026-05-30
- `vendite.trgfn_preventivi_guard_annullamento` — dal 2026-08-04
- `vendite.trgfn_preventivi_guard_transizione` — dal 2026-08-05
- `vendite.trgfn_preventivi_righe_set_natura_vendita` — dal 2026-06-08

### ✅ Fascia B — verbi, check e madri di dominio (10 funzioni) — **CHIUSA 2026-08-21**

**Tutte e 10 le pagine sono scritte.** Due gruppi: i cinque `fn_check_*` (una famiglia con lo
stesso contratto) e cinque verbi/madri.

**Il pattern `fn_check_*`**, ora scritto una volta e richiamato su tutte e cinque: funzione
pura (`STABLE`, nessuna scrittura, nessun raise di dominio) che ritorna `[]` o un array
ordinato di `{codice, reason, reason_key, dettaglio}`. ⭐ **Sorgente unica** per il guard di
transizione (che solleva il primo motivo) e per `fn_available_actions_*` (che espone
`disabled` + `reasons`): il bottone della UI e il rifiuto del DB non possono divergere, perché
leggono lo stesso verdetto.

**Difetti nuovi: nessuno.** Ma questa è la fascia che *registra* i difetti più istruttivi già
trovati e corretti dal progetto — e le pagine li conservano perché la classe di errore ricade:

* 🔴 **`fn_check_preventivo_annullabile`: il MOTIVO 1 non è mai scattato per tre changeSet.**
  Cercava l'ordine figlio su `ordini.sorgente_uid` — che è l'origine *import*, **0 righe
  valorizzate su 90** — invece che su `(documento_origine_tipo, documento_origine_id)`, 66 su
  90. Era stato scritto **per simmetria col gemello sui DDT**, dove la colonna omonima *è* il
  legame al padre ed *è* popolata: la stessa parola per due cose diverse. ⭐ Un guard che non
  scatta mai è indistinguibile da uno che funziona, finché non si misura la **popolazione**
  delle colonne su cui poggia. Nessun test era rosso.
* 🔴 **`fn_check_ordine_annullabile`: «asimmetria latente, oggi non morde» — su dati di TEST.**
  Contava anche i DDT annullati; la lacuna era stata archiviata perché nessun DDT bloccante
  risultava annullato. In esercizio annullare un DDT è ordinario, e l'ordine il cui unico
  figlio fosse annullato sarebbe rimasto bloccato per sempre. Corretta il 2026-08-15.
* ⚠️ **Un limite reale, verificato oggi**: `fn_guard_lotto_fatture_stato_coerente` esce in
  silenzio se il lotto ha `stato_doc_fiscale_id` nullo — e quella colonna **è nullable**. Un
  lotto senza stato non viene mai verificato. Misurato: **0 lotti su 45** oggi, quindi il buco
  non ha occupanti — ma è la colonna ad ammetterlo, non i dati a escluderlo.
* 🔴 **Il vincolo reciproco su TRE posti** (`fn_annulla_accredito_riga_reso`): che l'annullo
  **cancelli** le righe di ponte invece di marcarle è ciò che fa auto-riparare
  `fn_check_rinuncia_reversibile` e la guardia `E_RESO_ANNULLO_CON_ACCREDITO`. Nessuno dei due
  sa niente dell'altro: tornano permissivi solo perché la riga sparisce davvero. ⛔ Un
  soft-delete al posto del `DELETE` vieterebbe **per sempre e in silenzio** una rinuncia ormai
  reversibile e un annullo ormai ammesso — e nessuno dei tre lati sarebbe sbagliato da solo.

Elenco, per riferimento:

- `pratiche.fn_log_evento_dominio` — dal 2026-06-08
- `script.fn_check_commessa_annullabile` — dal 2026-07-24
- `script.fn_check_commessa_chiudibile` — dal 2026-07-24
- `script.fn_check_commessa_pronta_fatturazione` — dal 2026-08-04
- `script.fn_check_ordine_annullabile` — dal 2026-08-04
- `script.fn_check_preventivo_annullabile` — dal 2026-08-04
- `script.fn_disdetta_cliente` — dal 2026-03-01
- `vendite.fn_accoda_stampe_lotto` — dal 2026-07-20
- `vendite.fn_annulla_accredito_riga_reso` — dal 2026-08-18
- `vendite.fn_guard_lotto_fatture_stato_coerente` — dal 2026-07-22

### ✅ Fascia C — viste consumate da BE/FE (9 viste) — **CHIUSA 2026-08-21**

Viste di lista UI, riepiloghi IVA, liste di lavoro. Chi le consuma aveva bisogno di sapere
che cosa garantiscono — scope? snapshot o live? — e quella riga non c'era.

**Tutte e 9 le pagine sono scritte.** Ogni pagina risponde alle tre domande che il consumatore
si pone davvero: *applica uno scope o lo eredita*, *cosa fa sparire una riga*, *cosa la vista
NON garantisce*.

Quello che è emerso misurando, e che nessun commento diceva:

* **`security_invoker` è la linea di faglia.** Sei viste su nove ce l'hanno e quindi
  **ereditano** la RLS di chi interroga; tre no (`vw_fornitori_dettaglio`, `vw_pdp`,
  `vw_preventivi_riepilogo_iva_dettaglio`) e girerebbero coi diritti del proprietario.
  ⭐ **Verificato che oggi è innocuo**: nessuna delle tabelle lette da quelle tre ha la RLS
  attiva. Non è un buco aperto — è una rete che non c'è, e che nessun test segnalerebbe il
  giorno in cui servisse. Su `vw_preventivi_riepilogo_iva_dettaglio` è anche un'asimmetria col
  gemello DDT, che invece è `security_invoker`.
* **`JOIN` interno + RLS = la riga sparisce, non arriva incompleta.** Vale per
  `vw_clienti_lista` e `vw_contratti_lista` sul billing account (RLS attiva, 4 policy):
  un conteggio più basso del previsto può essere il perimetro, non i dati.
* **Due viste sui clienti, due risposte opposte**: `vw_clienti_lista` usa `JOIN` interno sul
  BA (fuori perimetro ⇒ cliente sparito), `vw_clienti_codice_ba` un `LEFT JOIN` (cliente
  presente, codice `NULL`). È lista contro ricerca, ed è deliberato.
* **`vw_ddt_righe_iva_base` esclude le righe senza prezzo** (`prezzo_unitario IS NOT NULL`):
  compaiono sul documento ma non contribuiscono a nessun imponibile, in silenzio. Da tenere
  presente quando il totale di un DDT non torna — e collegato al cantiere «righe DDT senza
  prezzo».
* **Snapshot contro live confermato e scritto**: preventivi legge la tabella congelata, DDT
  ricalcola da zero. Le due viste **non vanno unificate**, e ora la ragione è in pagina.
* **`vw_lotti_fatture_incoerenti` è vuota anche fuori perimetro**: per una lista di lavoro
  «zero incoerenze» può voler dire «nessuna che io possa vedere».

Corretto anche un link morto preesistente in `vendite/manual/vw_preventivi.md`
(`vw_preventivi_list` → `vw_preventivi_lista`).

---

#### ✅ Finding CHIUSO E APPLICATO: la famiglia `vw_stato_sorgente_*` era fuori dal presidio scope

Nato da una domanda di Tid — *«le viste senza security_invoker erano giuste?»*. Le tre della
fascia C **sì**: per il criterio del progetto (dichiarato in
`db/pgtap/vendite/test-vw-dash-security-invoker.sql`) ciò che conta non è il nome ma
**«legge tabelle in RLS»**, e nessuna delle tre lo fa.

Verificando quel criterio su **tutto** il database, però, ne escono **sette** che lo violano:

| Vista | Legge (in RLS) |
|---|---|
| `vendite.vw_stato_sorgente_contratto` | `vendite.contratti` |
| `vendite.vw_stato_sorgente_ddt` | `vendite.ddt` |
| `vendite.vw_stato_sorgente_offerta` | `vendite.offerte_commerciali` |
| `vendite.vw_stato_sorgente_ordine` | `vendite.ordini` |
| `vendite.vw_stato_sorgente_preventivo` | `vendite.preventivi` |
| `vendite.vw_stato_sorgente_reso` | `vendite.resi` |
| `script.vw_stato_sorgente` | (union delle sei) |

Tutte owned da `titodb`, che è owner anche delle tabelle ed **esente dalla RLS non-forced**:
è esattamente la condizione che il fix V-1 (`20260706-15`) corresse per la famiglia
`vw_dash_*`. `SELECT` è concesso a `zeroerp_app`, e la union è **enumerabile** (347 righe).
A valle c'è `pratiche.fn_stato_sorgente`, che è `STABLE` e non `SECURITY DEFINER`: eredita
quindi ciò che la vista concede.

**È una dimenticanza, non una scelta.** Il changeset `20260701-17` documenta quattro
decisioni (dispatch, placement, `risolto=true`, uso liste) e **non nomina mai** RLS, scope o
`security_invoker`. La cronologia lo conferma: la famiglia nasce l'1-2 luglio 2026, il fix
delle `vw_dash_*` arriva il **6** luglio, e il 18 luglio due rami nuovi (ddt, reso) vengono
aggiunti senza ripensarci.

⚠️ **Il bypass non è dimostrabile sui dati di sviluppo**, e la ragione è istruttiva: tutti i
165 preventivi appartengono a **un solo emittente** (id 32) su due attivi, quindi tabella e
vista restituiscono lo stesso conteggio comunque. È precisamente il motivo per cui il test
`test-vw-dash-security-invoker.sql` presidia la **reloption** e non il comportamento —
lo dice nella sua intestazione. La domanda giusta resta *«può succedere?»*, non *«è
successo?»*.

**Chiuso su decisione di Tid (2026-08-21). ⛔ Scritto e fermo: serve una migrazione.**

| Cosa | Dove |
|---|---|
| `security_invoker = on` sulle 6 viste di dominio | `20_code/vendite/20260821-08-alter-vw-stato-sorgente-security-invoker` |
| `security_invoker = on` sulla union | `20_code/script/20260821-09-alter-vw-stato-sorgente-union-security-invoker` |
| Presidio esteso a **due schemi**, coda allungata, soglia 13 → 20 | `db/pgtap/vendite/test-vw-dash-security-invoker.sql` |
| 3 fixture: emittente **derivato** e non pescato | `test-proiezione-stato-sorgente.sql` (2), `test-vw-stato-sorgente-ddt-reso-v1.sql` (1) |

⭐ **`ALTER VIEW ... SET (security_invoker = on)`, non `CREATE OR REPLACE`.** Tocca solo le
reloptions e lascia intatta la definizione. Ricopiare il corpo sarebbe stato il rischio vero:
è esattamente così che il progetto ha già perso il flag una volta
(`vw_dash_fatturazione_contratti`, `20260707-03`, ripristinato dal `-10`). E su
`script.vw_stato_sorgente` varrebbe doppio — il suo changeset di nascita dichiara «MAI
modificare questo file dopo il merge» e prevede rami `UNION ALL` additivi: fotografare il
corpo a oggi rischierebbe di perdere i rami `ddt` e `reso`, arrivati il 18 luglio.

🔴 **Serve su OGNI anello della catena**: `security_invoker` non si propaga fra viste. Una
union col flag che legge viste senza darebbe la falsa impressione di aver chiuso il buco —
peggio che non averlo toccato. Per questo i changeset sono due, e il `-09` ha una
preCondition che verifica che il `-08` sia passato.

**Le fixture.** Tre punti pescavano l'emittente con `ORDER BY id LIMIT 1` invece di derivarlo
da chi agisce, contro la regola del template pgTAP. Oggi i due valori coincidono — un solo
emittente ha documenti — quindi i test passavano **per coincidenza, non per costruzione**:
con lo scope attivo un documento intestato a un altro emittente sarebbe invisibile alla vista.
Corretti in `script.fn_pgtap_emittente_operatore()`; entrambi i test restano verdi (28 e 9
asserzioni).

**✅ Migrato il 2026-08-21. Verificato sul DB:**

* tutte e sette le viste hanno `security_invoker = on`;
* `test-vw-dash-security-invoker.sql` è **verde** (2/2);
* baseline: **nessuna regressione**;
* ⭐ e la misura che conta: rifatta su **tutto il database**, la query
  «viste senza `security_invoker` che dipendono da tabelle con `relrowsecurity`»
  restituisce ora **zero trasgressori**.

⚠️ **Conseguenza voluta a valle**: con lo scope attivo `pratiche.fn_stato_sorgente` degraderà a
`UNKNOWN` per i documenti fuori perimetro invece di restituirne lo stato — fail-closed, ed è il
fallback già previsto dal wrapper, ma **cambia il risultato** per
`backend/apps/pratiche/db/pratiche_repository.py`. `zeroerp_batch_fatturazione` ha `BYPASSRLS`
e non è toccato.

- `anagrafiche.vw_clienti_codice_ba` — dal 2026-03-12
- `anagrafiche.vw_clienti_lista` — dal 2026-05-08
- `anagrafiche.vw_fornitori_dettaglio` — dal 2026-03-25
- `anagrafiche.vw_pdp` — dal 2025-12-07
- `vendite.vw_contratti_lista` — dal 2026-06-02
- `vendite.vw_ddt_riepilogo_iva_dettaglio` — dal 2026-07-11
- `vendite.vw_ddt_righe_iva_base` — dal 2026-07-11
- `vendite.vw_lotti_fatture_incoerenti` — dal 2026-07-22
- `vendite.vw_preventivi_riepilogo_iva_dettaglio` — dal 2026-05-02

### ✅ Fascia D — tabelle di dominio e vocabolari `config` (14 tabelle) — **CHIUSA 2026-08-21**

14 e non 13: si è aggiunta `anagrafiche._legacy_risorse_umane_auth_user`, spostata qui dalla
fascia H quando la misura ha mostrato che è viva (§4/H3).

**Nessun bug attivo** — ma per una ragione che va detta: **metà di queste tabelle appartiene a
domini non ancora in esercizio**, e su una tabella vuota non ci sono difetti in corso, ci sono
scelte da verificare prima di attivarla.

**Lo stato reale, misurato il 2026-08-21** (è la cosa che nessun `COMMENT` diceva):

| Tabella | Righe | Lettura |
|---|---:|---|
| `config.ambiti` | **0** | predisposizione per magazzino |
| `config.categoria_accisa` | **0** | predisposizione fiscale utilities |
| `config.tipi_tariffe_ee` | **0** | predisposizione mercato elettrico |
| `anagrafiche.vettori` | **0** | ruolo previsto, mai anagrafato |
| `pagamenti.sepa_mandati` | **0** | ciclo incassi non in esercizio |
| `config.classi_utenze` / `tipi_utenze` | **1** / **1** | dominio energia appena abbozzato |
| `config.nature_vendita` | 3 | **in uso** (smistamento preventivi) |
| `config.tipi_ubicazione` | 6 | vocabolario pronto, dominio no |
| `config.aspetti_beni` | 10 | **in uso** (DDT) |
| `catalogo.note_articoli` | 59 | **in uso** |

Documentare una tabella vuota come se fosse operativa sarebbe stato il difetto peggiore di
tutta l'operazione: ogni pagina dice esplicitamente se ciò che descrive è **in esercizio** o
**predisposto**.

**Le cose da sapere prima di attivare quei domini** — tutte annotate nelle pagine:

* ⭐ **`config.tipi_utenze` decide un regime, non solo un valore.** Il guard sui contratti
  deduce se una utility «ha la dimensione tipo/classe» dall'**esistenza di almeno una riga**.
  Svuotarla cambia il regime, e da quel momento i contratti già scritti con tipo/classe
  valorizzati **non sono più aggiornabili** — anche se erano corretti quando sono stati creati.
* ⚠️ **`config.classi_utenze`**: `pot_contratto_min_ee`/`max_ee` sono obbligatorie ma **nessun
  CHECK impone `min <= max`**; e `tipo_utenza_id` è nullable, quindi una classe senza tipo è
  scrivibile ma **non passerà mai** su un contratto — con un errore che parla di «incoerenza
  fra tipi» invece che di «classe senza tipo».
* ⚠️ **`pagamenti.sepa_mandati`**: `stato` e le tre date (`firma`, `attivazione`, `revoca`)
  sono **assi separati senza vincolo di coerenza** — un mandato può risultare attivo per stato
  e avere `data_revoca` valorizzata. E nulla impedisce `istanza_utility_id` **senza**
  `billing_account_id`, combinazione che il modello non prevede.
* ⚠️ **`config.aspetti_beni`** usa `attivo` e non `obsoleto_dal`: è il pattern vecchio, quello
  che rompe le istanze già referenziate (memoria di progetto). Sui DDT il danno è attenuato —
  l'aspetto è un dato di stampa — ma è una differenza rispetto ai cataloghi recenti.
* ⚠️ **`config.nature_vendita`**: cambiare il `destinazione_tipo` di una natura esistente
  **cambia il comportamento del guard** per tutte le righe future, e nulla lo segnala. È una
  colonna di configurazione con effetti di codice.

Elenco, per riferimento:

- `anagrafiche.vettori` — dal 2025-09-05
- `catalogo.note_articoli` — dal 2026-01-13
- `catalogo.note_articoli_componenti` — dal 2026-01-13
- `config.ambiti` — dal 2025-05-23
- `config.aspetti_beni` — dal 2025-09-05
- `config.categoria_accisa` — dal 2025-08-30
- `config.classi_utenze` — dal 2025-08-30
- `config.nature_vendita` — dal 2026-06-08
- `config.tipi_tariffe_ee` — dal 2025-08-30
- `config.tipi_ubicazione` — dal 2025-10-06
- `config.tipi_utenze` — dal 2025-08-30
- `config.user_emittente_attivo` — dal 2026-08-04
- `pagamenti.sepa_mandati` — dal 2025-08-31

### ✅ Fascia E — presidio codici errore e riferimenti morti (12 oggetti) — **CHIUSA 2026-08-21**

Infrastruttura nata da poco, con `COMMENT` già ricchi: qui il lavoro era portarli in pagina e
aggiungere ciò che il `COMMENT` non dice — le relazioni fra gli oggetti e come si leggono
insieme. **Tutte e 12 le pagine sono scritte.**

Le due famiglie e il filo che le lega:

**Codici errore (8).** Il modello ha **tre lati** — `classi_errore` (che *tipo* di rifiuto),
`codici_errore` (quale, e se è in servizio), `messaggi_errore` (la frase, per lingua) — più
due registri di debito e due misure che leggono il codice PL/pgSQL vivo.

**Riferimenti morti (4).** `fn_check_funzioni_riferimenti_morti` più il registro delle
esenzioni e le sue **due** viste guardiane.

Quello che è emerso scrivendo:

* ⭐ **I due registri di debito hanno ciascuno la sua vista di rientro.** È la parte che di
  solito manca a un registro di eccezioni, ed è ciò che gli impedisce di gonfiarsi: senza
  `vw_riferimenti_morti_rientrati`, un'esenzione sanata resterebbe per sempre e il guardrail
  resterebbe verde presidiando sempre meno. Documentato che le due viste **devono essere
  vuote insieme**: una sola vuota non distingue «nessun difetto» da «tutto esentato».
* ⭐ **I falsi positivi sono classificati, non filtrati** (`FP_TRANSITION_TABLE`,
  `FP_RAMO_ALTRA_TABELLA`, `FP_SQL_DINAMICO`). Un filtro li avrebbe fatti sparire anche quando
  smettono di essere falsi positivi. Misura al 2026-08-21: 20 `FP_*`, **1 `ORFANA`**, zero
  `REALE`, registro con 1 voce, entrambe le viste guardiane **vuote**.
* ⚠️ **`vw_codici_errore` non è uno a uno**: il join con le traduzioni non filtra la lingua.
  Misurato: 726 codici → **727 righe**, perché un codice ha già due lingue. Oggi lo scarto è
  di uno — cresce col catalogo tradotto. Chi conta i codici da lì sbaglia *di poco*, che è il
  modo peggiore. Per quello esiste `vw_codici_errore_identita`, e ora la differenza fra le due
  è dichiarata su entrambe le pagine.
* 🔴 **Il punto cieco che tocca la fascia A**: `vw_codici_errore_da_dichiarare` non vede i
  `RAISE EXCEPTION` diretti. `vendite.trgfn_event_log_append_only` ne usa uno — il suo rifiuto
  non è in nessun catalogo, non compare in quella misura e non finisce in `error_log`. È
  **invisibile a tutte e tre** le misure del presidio, ed è ora scritto in entrambe le pagine.
* ⚠️ **`fn_check_funzioni_riferimenti_morti` è costosa** (gira `plpgsql_check` su ogni funzione
  × ogni tabella agganciata). ⭐ Avevo scritto anche che comporre le due viste in una query
  sola fosse rischioso, per via della temp table condivisa: **misurato, è falso** — due
  chiamate nella stessa istruzione restituiscono entrambe 21 righe, PostgreSQL materializza la
  set-returning function. Avvertenza corretta nelle tre pagine.

#### La domanda che vale: in fascia E ci sono difetti, o solo documentazione?

Posta da Tid a fascia chiusa. Verificato oggetto per oggetto: **la fascia E non ha prodotto
nessun difetto nuovo.** È infrastruttura fatta bene, e due delle avvertenze che avevo scritto
si sono rivelate infondate alla misura:

| Sospetto | Esito della verifica |
|---|---|
| Temp table condivisa fra le due viste | ❌ **infondato** — le chiamate non interferiscono |
| `vw_codici_errore` moltiplica per lingua e qualcuno ci conta sopra | ❌ **già presidiato** — `genera_error_policies` usa la gemella uno-a-uno e porta in testa un divieto esplicito di usare questa vista |

⭐ Il secondo caso è istruttivo: il progetto non solo evitava la trappola, ma ne aveva
documentato **una variante peggiore** che da solo non avrei visto — filtrare per
`lingua = 'it'` non è un rimedio, perché il `LEFT JOIN` fa comparire con `lingua IS NULL` i
codici privi di messaggio, e il filtro li scarterebbe in silenzio.

🔴 **L'unico difetto vero che la fascia E illumina non è suo**: è
`vendite.trgfn_event_log_append_only` (fascia A), che solleva con `RAISE EXCEPTION` diretta.
Non ha un codice in catalogo, non compare in `vw_codici_errore_da_dichiarare`, non scrive in
`error_log`: **invisibile a tutte e tre le misure del presidio**, e non registrato in nessuno
dei due registri di debito. Non è un difetto che il presidio ha mancato — è un difetto che il
presidio, per costruzione, non può vedere. Resta aperto e non tracciato.

Elenco, per riferimento:

- `config.classi_errore` — tabelle · dal 2026-08-07
- `config.codici_errore` — tabelle · dal 2026-08-07
- `config.vw_codici_errore` — views · dal 2026-08-07
- `config.vw_codici_errore_identita` — views · dal 2026-08-07
- `dbops.fn_check_funzioni_riferimenti_morti` — funzioni · dal 2026-08-04
- `dbops.codici_errore_senza_policy` — tabelle · dal 2026-08-05
- `dbops.messaggi_errore_codici_legacy` — tabelle · dal 2026-08-05
- `dbops.riferimenti_morti_esenzioni` — tabelle · dal 2026-08-04
- `dbops.vw_codici_errore_da_dichiarare` — views · dal 2026-08-05
- `dbops.vw_codici_errore_forme_condizione` — views · dal 2026-08-07
- `dbops.vw_riferimenti_morti_da_sanare` — views · dal 2026-08-04
- `dbops.vw_riferimenti_morti_rientrati` — views · dal 2026-08-04

### Fascia F — schema `magazzino` quasi interamente scoperto (31 oggetti, 1 solo manuale esistente)

`magazzino/manual/` contiene **un** file (`assets.md`). Tutto il resto — ledger movimenti,
costo medio, inventari, rettifiche, trasferimenti, ubicazioni, prenotazioni — è senza doc
concettuale. Stessa storia, in scala minore, per `acquisti` (8 oggetti).

- `magazzino.fn_get_magazzino_note` — funzioni · dal 2025-10-05
- `magazzino.trgfn_magazzini_normalize` — funzioni
- `magazzino.ambito_causale` — tabelle · dal 2025-10-02
- `magazzino.causali` — tabelle · dal 2025-10-02
- `magazzino.costo_medio` — tabelle · dal 2025-10-05
- `magazzino.eventi_assets` — tabelle · dal 2025-10-02
- `magazzino.inventari` — tabelle · dal 2025-10-05
- `magazzino.inventari_righe` — tabelle · dal 2025-10-05
- `magazzino.magazzini` — tabelle · dal 2025-09-05
- `magazzino.movimenti` — tabelle · dal 2025-10-02
- `magazzino.note` — tabelle · dal 2025-10-05
- `magazzino.note_asset` — tabelle · dal 2025-10-05
- `magazzino.note_costo_medio` — tabelle · dal 2025-10-05
- `magazzino.note_evento_asset` — tabelle · dal 2025-10-05
- `magazzino.note_inventario` — tabelle · dal 2025-10-05
- `magazzino.note_inventario_riga` — tabelle · dal 2025-10-05
- `magazzino.note_movimento` — tabelle · dal 2025-10-05
- `magazzino.note_rettifica` — tabelle · dal 2025-10-05
- `magazzino.note_rettifica_riga` — tabelle · dal 2025-10-05
- `magazzino.note_trasferimento` — tabelle · dal 2025-10-05
- `magazzino.note_trasferimento_riga` — tabelle · dal 2025-10-05
- `magazzino.reservations` — tabelle · dal 2025-10-02
- `magazzino.rettifiche` — tabelle · dal 2025-10-05
- `magazzino.rettifiche_righe` — tabelle · dal 2025-10-05
- `magazzino.trasferimenti` — tabelle · dal 2025-10-05
- `magazzino.trasferimenti_righe` — tabelle · dal 2025-10-05
- `magazzino.ubicazioni` — tabelle · dal 2025-10-06
- `magazzino.vw_costo_medio` — views · dal 2025-10-05
- `magazzino.vw_costo_medio_globale` — views · dal 2025-10-05
- `magazzino.vw_giacenza` — views · dal 2025-10-05
- `magazzino.vw_giacenza_valorizzata` — views · dal 2025-10-05

E `acquisti`:

- `acquisti.fn_get_acquisti_note` — funzioni · dal 2025-10-05
- `acquisti.trgfn_acq_ordini_only_consegna_tipo_con` — funzioni
- `acquisti.ddt` — tabelle · dal 2025-09-17
- `acquisti.ddt_indirizzi` — tabelle · dal 2025-09-17
- `acquisti.ddt_righe` — tabelle · dal 2025-09-17
- `acquisti.ordini` — tabelle · dal 2025-09-17
- `acquisti.ordini_righe` — tabelle · dal 2025-09-17
- `acquisti.ordini_righe_fulfillment` — tabelle · dal 2025-09-17

### Fascia G — fixture pgTAP e utility tecniche (7 + 11)

Qui una pagina per oggetto è sproporzionata: meglio **una pagina sola** per famiglia
(«le fixture pgTAP», «le façade di log») e i manuali dei singoli che ci rimandano.

Fixture pgTAP:

- `dbops.fn_pgtap_cf_libero` — dal 2026-08-19
- `dbops.fn_pgtap_crea_soggetto_pg` — dal 2026-08-19
- `dbops.fn_pgtap_crea_soggetto_ruolo` — dal 2026-08-19
- `dbops.fn_pgtap_piva_libera` — dal 2026-08-19
- `script.fn_pgtap_emittente_operatore` — dal 2026-08-05
- `script.fn_pgtap_emittente_sr_operatore` — dal 2026-08-07
- `script.fn_pgtap_set_contesto_operatore` — dal 2026-08-05

Utility e façade:

- `dbops.fn_admin_merge_comune` — funzioni · dal 2025-05-23
- `dbops.fn_admin_merge_stradario` — funzioni · dal 2025-05-23
- `dbops.fn_col_exists` — funzioni · dal 2025-08-21
- `dbops.fn_list_indices` — funzioni · dal 2025-05-23
- `dbops.fn_normalize_indirizzo` — funzioni · dal 2025-05-23
- `dbops.ai_query_log` — tabelle · dal 2026-03-31
- `script.fn_get_vie_discendenti` — funzioni · dal 2025-05-23
- `script.fn_log` — funzioni · dal 2026-08-07
- `script.fn_norm_testo` — funzioni · dal 2025-09-05
- `script.fn_norm_via` — funzioni · dal 2025-09-05
- `script.log` — funzioni · dal 2025-08-22

### ✅ Fascia H — **decisa 2026-08-21: si lasciano così** (8, dopo lo spostamento di H3)

**Decisione di Tid**: gli oggetti `dbops` della fascia H restano dove sono. Non sono un
problema — non li chiama nessuno, non fanno danno, e il costo di toglierli (un changeSet
forward-only in v2, perché la v1 li ricrea) non è giustificato. Niente doc, niente rimozione:
la misura qui sotto resta come registro del perché la domanda è stata chiusa così.

⚠️ Resta valida la sola conseguenza operativa: **non vanno documentati**, quindi continueranno
a contare nel buco di copertura. Se un giorno nascesse un guardrail sulla copertura, questi
otto vanno in una whitelist dichiarata, non sanati.

⚠️ La classificazione iniziale era fatta **sui nomi**, non su una misura. Misurata davvero, la
fascia non è omogenea: si spacca in tre gruppi con destini diversi, e uno degli oggetti era
classificato male.

**H1 · Sette residui veri** — le 6 funzioni `dbops` + `maintenance.test_pgagent_log`.

* Nascono in `db/changelog/migrations` (la **v1**, settembre 2025) o in `db/changelog/baseline`,
  mai in `migrations_v2`.
* **Zero chiamanti, ovunque**: nessun changeSet v2, nessun pgTAP, nessuno script, nessun file
  del backend, e nessun corpo plpgsql del DB vivo li nomina.
* `maintenance.test_pgagent_log` ha **0 righe** e **nessun job pgAgent** che la scriva: serviva
  a collaudare pgAgent al bootstrap del 2025-08-08.
* Sono utilità di manutenzione trigger (rinomina, token di evento, pulizia suffissi `_2`)
  già consumate: owner `titodb`, nessun `COMMENT`.

⚠️ **Ma un `DROP` a mano non basta.** `changelog-master-v2.yaml` include ancora
`changelog-master.yaml` (v1), che a sua volta applica `baseline` e `migrations`: questi
oggetti **rinascono a ogni ricostruzione da zero**. Per toglierli davvero serve un changeSet
forward-only in `migrations_v2`, posizionato dopo la v1.

**H2 · Un backup di lavoro** — `dbops._defaults_backup_usercols`, **73 righe**, citata da un
solo changeSet: `20_code/dbops/20251008-01-utility-correct-user-default-value`. È lo snapshot
preso prima di quella correzione, dell'8 ottobre 2025. L'underscore iniziale nel nome dichiara
già che era temporanea. Decisione: se quella correzione è consolidata, si butta.

**H3 · Uno classificato male da me** — `anagrafiche._legacy_risorse_umane_auth_user`
**è viva**, e va in fascia D (da documentare), non qui:

* ha **6 righe** e sopra ci sta la vista di compatibilità `anagrafiche.risorse_umane_auth_user`;
* è citata da **4 changeSet v2** e da **2 pgTAP**
  (`test-permessi-strutture-base.sql`, `test-user-emittenti-fiscali-immutable.sql`).

Toglierla romperebbe la vista e due test. È una tabella archiviata dal cutover multi-face-auth
del 2026-04-19, non un residuo dimenticato.

---

#### L'elenco originale, per riferimento

- `anagrafiche._legacy_risorse_umane_auth_user` — tabelle · dal 2026-04-19
- `dbops.fn_cleanup_triggers_suffix_2` — funzioni · dal 2025-09-22
- `dbops.fn_fix_lock_codice_interno_triggers` — funzioni · dal 2025-09-22
- `dbops.fn_fix_triggers_event_tokens` — funzioni · dal 2025-09-22
- `dbops.fn_fix_triggers_events_noorder` — funzioni · dal 2025-09-22
- `dbops.fn_migrate_add_indirizzo_normalizzato` — funzioni · dal 2025-05-23
- `dbops.fn_rename_triggers_by_order` — funzioni · dal 2025-09-22
- `dbops._defaults_backup_usercols` — tabelle · dal 2025-10-08
- `maintenance.test_pgagent_log` — tabelle · dal 2025-08-11

### ✅ Fascia I — `storico` (102 tabelle) — **CHIUSA 2026-08-21: una pagina sola per tutte**

**Decisione di Tid.** Le tabelle di `storico` sono repliche di quelle degli schemi principali:
non serve prosa per ciascuna. Si scrive **una pagina condivisa** che descrive genericamente
a cosa serve lo storico, e ogni tabella rimanda alla propria tabella-fonte per la descrizione
del contenuto.

⚠️ **Nota di attuazione**: una pagina sola non chiude 102 auto-gen. Il generatore cerca
`storico/manual/<nome>.md` per **ogni** oggetto, quindi servono comunque 102 file — ma
possono essere **file minimi** che includono lo stesso testo condiviso:

```
storico/manual/<nome>.md   →  titolo + rimando alla tabella fonte
                              + include del testo comune
```

Il preprocess espande gli `include-markdown` **ricorsivamente**, quindi il contenuto vero
resta in un posto solo e si mantiene una volta. È il modo per ottenere ciò che la decisione
chiede senza 102 testi da tenere allineati.

⚠️ Le **9** pagine `storico/manual/` già esistenti hanno testo proprio e restano come sono.

**Fatto.** `storico/_tabelle-storico.md` contiene il testo comune; i **102** file minimi in
`storico/manual/` lo includono e rimandano ciascuno alla propria tabella di origine.
Copertura dello schema: **111 / 111**.

Che cosa dice la pagina comune, e che nessuna delle 9 pagine preesistenti diceva:

* ⚠️ **Il trigger è `BEFORE UPDATE OR DELETE`, non `INSERT`**: lo storico registra lo stato
  *precedente* a una modifica, quindi **la nascita di una riga non è tracciata**. Una riga
  creata e mai più toccata non ha storia.
* ⚠️ **Il flag `storicizza` sulla riga viva decide**: se è `false` la modifica non viene
  archiviata. Un buco nella storia può essere un flag, non una perdita di dati.
* ⭐ **Il dato vive dentro `snapshot` (JSONB), non in colonne proprie**: è ciò che rende
  l'archivio immune all'evoluzione della fonte — nessuna migrazione quando la tabella viva
  cambia colonne — al prezzo di doverlo interrogare con gli operatori JSONB.
* **`tx_id` è la chiave di correlazione** fra righe archiviate dalla stessa operazione, anche
  su tabelle diverse.

**Quattro storici non hanno più una tabella di origine**, e la misura lo dice:
`comune_trasformazioni`, `stradario_trasformazioni`, `fatturazione_lotti_attivita` — tutti e
tre **vuoti**, candidati a una potatura dello schema — e `risorse_umane_auth_user`, che invece
ha **12 righe** vere: sono associazioni pre-cutover multi-face-auth, e restano l'unica traccia
di com'erano prima. ⭐ È il caso che mostra perché lo storico **non segue** la sorte della
fonte.

⭐ **Dividendo inatteso: 10 link morti chiusi.** Le 9 pagine preesistenti puntavano a
`script.trgfn_upd_dlt_storico_generic` e a due trigger function specifiche, **tutte rinominate
o rimosse** — oggi la storicizzazione passa da `script.trgfn_storico_generic`. Corretti; in
`stradario.md` anche la prosa e l'esempio SQL, con la nota di che cosa è cambiato.

Le 9 pagine `storico/manual/` esistenti sono tutte lo stesso testo con il nome cambiato
(«mantiene la cronologia completa dei record di `X`…»). Per **83** delle 102 mancanti la
tabella-fonte **ha già** una doc manuale da cui derivare il testo: è generazione, non scrittura.

Le altre **19** non hanno fonte documentata (documentare prima la fonte, poi lo storico):

`storico.ambito_causale`, `storico.causali`, `storico.comune_trasformazioni`, `storico.eventi_assets`, `storico.fatturazione_lotti_attivita`, `storico.inventari`, `storico.inventari_righe`, `storico._legacy_risorse_umane_auth_user`, `storico.magazzini`, `storico.movimenti`, `storico.reservations`, `storico.rettifiche`, `storico.rettifiche_righe`, `storico.sepa_mandati`, `storico.stradario_trasformazioni`, `storico.trasferimenti`, `storico.trasferimenti_righe`, `storico.user_emittente_attivo`, `storico.vettori`

---

## 5. Il verso opposto: manuali orfani (5)

File in `manual/` senza nessun auto-generato corrispondente. O l'oggetto è stato rinominato
o rimosso dal DB e la pagina è rimasta, oppure sono pagine tematiche messe nella cartella
sbagliata (`catasto-architettura`, `trigger_business_overview` sembrano il secondo caso).

- `anagrafiche/manual/catasto-architettura.md`
- `anagrafiche/manual/trgfn_emittenti_fiscali_guard_attivo.md`
- `pratiche/manual/trgfn_sospensioni_giornale.md`
- `pratiche/manual/trigger_business_overview.md`
- `public/manual/version_info.md`

---

## 6. Proposta operativa

L'ordine seguito è stato **A → C → E → B → D → I → F → G**, con **H** decisa e non eseguita.

* ✅ **A** — fatta (35 manuali + i 3 presidi di §7).
* ✅ **H** — decisa: si lasciano così.
* ✅ **C** — fatta (9 viste) + finding scope `vw_stato_sorgente_*` chiuso e applicato.
* ✅ **E** — fatta (12 oggetti).
* ✅ **B** — fatta (10 funzioni).
* ✅ **D** — fatta (14 tabelle).
* ✅ **I** — fatta (102 file + pagina condivisa).
* ✅ **F** — fatta (39: magazzino 31 + acquisti 8), con due pagine di dominio condivise che
  dichiarano lo stato reale: **entrambi gli schemi sono a zero righe**, predisposti e mai avviati.
* ✅ **G** — fatta (18), come concordato: **pagina-famiglia** per le 7 fixture pgTAP, pagine
  brevi per le 9 utility, e per le **2 façade di log** un rimando al motore invece di una
  pagina propria — sono a **zero chiamanti**, e descriverle come «il modo per loggare» sarebbe
  stato fuorviante.

⭐ **Nessuna fascia resta aperta.** Gli 8 oggetti della fascia H sono gli unici privi di pagina
manuale, ed è il residuo dichiarato del cantiere.

---

## 8. Link morti nelle pagine manuali preesistenti — **89 trovati, 35 chiusi**

Il controllo finale sui riferimenti `/dbzero/...` di **tutte** le pagine `manual/` del progetto
ne ha trovati **89 rotti**. ⚠️ **Nessuno nelle pagine scritte in questo cantiere** — quelle
sono state verificate una per una man mano. Sono tutti in documentazione preesistente.

**Non sono presidiati da niente**: il guardrail dei riferimenti morti controlla i corpi
plpgsql, non i link markdown, e la build della doc non fallisce su un link interno inesistente.

Si raggruppano in poche classi ricorrenti, quindi sono in gran parte correggibili in blocco:

| Classe | Esempio | Occorrenze |
|---|---|---:|
| Oggetto **rinominato** | `trgfn_upd_audit_data_user_generic` → `trgfn_audit_data_user_generic` | 9 |
| Oggetto **cambiato di natura** | `anagrafiche/tabelle/risorse_umane_auth_user` — oggi è una **vista** | 12 |
| **Schema sbagliato** | `dbops/funzioni/fn_log_and_raise_error` — sta in `script` | 4 |
| **Path errato** | `/viste/` e `/view/` invece di `/views/` | 6 |
| Link a **`manual/`** | i riferimenti vanno all'auto-gen, non alla pagina manuale | 3 |
| Oggetto **inesistente** | `ddt_testata`, `fatture_testata`, `attivita_fatturabili_lotti` | ~8 |
| Refusi | `trgfn_dati_societari_gauard_...` | alcuni |

⭐ Le prime quattro classi (31 link) sono **meccaniche**: una sostituzione verificata contro
l'auto-gen. Le ultime due richiedono di decidere caso per caso dove il link *dovrebbe* portare,
o se la frase che lo contiene sia ancora vera — un oggetto che non esiste più spesso segnala
una pagina che descrive un modello superato.

### ✅ Le quattro classi meccaniche: corrette il 2026-08-21

Su mandato di Tid. **37 link** sostituiti in 30 file — più dei 31 stimati, perché il conteggio
iniziale era sui link *unici* e alcuni comparivano più volte nello stesso file:

| Classe | Da | A | Link |
|---|---|---|---:|
| rinominata | `trgfn_upd_audit_data_user_generic` | `trgfn_audit_data_user_generic` | 9 |
| tabella → vista | `anagrafiche/tabelle/risorse_umane_auth_user` | `.../views/...` | 12 |
| schema sbagliato | `dbops` e `anagrafiche` `/funzioni/fn_log_and_raise_error` | `script/...` | 5 |
| path errato | `/viste/`, `/view/` | `/views/` | 11 |

Ogni destinazione è stata **verificata contro l'auto-gen prima** di sostituire, e il testo del
link è stato allineato al path (`dbops.fn_log_and_raise_error` → `script.fn_log_and_raise_error`).

⭐ **In coda, 16 riferimenti errati nel testo** (non nei link) allo stesso gruppo di oggetti —
prosa e tabelle che dicevano `anagrafiche.fn_log_and_raise_error` o il vecchio nome del trigger
di audit. Sono la stessa classe di errore e la stessa correzione: un riferimento sbagliato in
una frase è sbagliato quanto uno in un link, e lasciarlo avrebbe lasciato la doc a dire il
falso su *dove* vive una funzione.

**Residuo: 54 link rotti**, tutti da decidere caso per caso. Non sono meccanici: puntano a
oggetti che **non esistono affatto** — `ddt_testata`, `fatture_testata`,
`attivita_fatturabili_lotti`, `stato_approvazione_prezzo`, `fn_crea_operatore`,
`fn_crea_risorsa_umana`. ⚠️ Diversi di questi non sono refusi: sono i nomi di un **modello
superato**, e il link morto segnala una pagina che descrive un'architettura che non c'è più.
Correggerli significa rileggere la frase che li contiene, non sostituire una stringa.

⛔ Quelli restano non corretti: vanno affrontati con un mandato loro. Il comando che li elenca:

```bash
cd docs/it/dbzero
for f in */manual/*.md; do
  grep -o '(/dbzero/[a-z_]*/[a-z]*/[a-z_0-9]*)' "$f" | tr -d '()' | while read -r l; do
    [ -e "${l#/dbzero/}.md" ] || echo "$f -> $l"
  done
done
```

⭐ Vale la pena considerare un **guardrail** su questo: il cantiere ha appena dimostrato che la
doc auto-gen si rigenera e i manuali no, quindi i link invecchiano in silenzio. Sarebbe lo
stesso ragionamento del presidio `security_invoker` — verificare la forma, non fidarsi della
disciplina.

Due cose da tenere presenti mentre si scrive:

- ⚠️ **Non toccare mai i file in `tabelle/`, `views/`, `funzioni/`**: si rigenerano e il tag
  `include-markdown` compare da solo alla prima rigenerazione dopo la creazione del manuale.
- ⚠️ I link interni vanno nella forma `/dbzero/<schema>/<tipo>/<nome>` (senza `.md`), come
  nelle pagine esistenti. Il guardrail dei riferimenti morti gira **dopo** `manage.py migrate`.

**Da decidere prima di partire** (non lo decido io):

1. Fascia H: documentare o rimuovere?
2. Fascia I (`storico`): 102 pagine generate da template, oppure **una** pagina di schema e
   nessuna pagina per tabella?
3. Fascia G: pagina-famiglia o pagina per oggetto?
4. Serve un guardrail CI che impedisca al buco di riaprirsi (fallisce se un oggetto nuovo
   di dominio nasce senza manuale)?

---

## 7. I tre presidi mancanti — chiusi il 2026-08-21

Scrivere la fascia A ha fatto emergere tre lacune vere. Non erano incendi — nessuna era
raggiungibile dal percorso applicativo corrente — ma tutte e tre erano raggiungibili con un
`UPDATE` diretto. Decisione di Tid: **tutte e tre da chiudere.**

⛔ **Niente è applicato.** Tutto quanto sotto è preparato e fermo: serve una migrazione.

### Cosa è stato scritto

Tutto passa dai **CSV mirror `runOnChange`**: nessun changeSet nuovo per i seed, nessun DDL
scritto a mano. È il punto della faccenda — i tre presidi si dichiarano, non si programmano.

| Cosa | Dove | Effetto |
|---|---|---|
| Lock `offerte_commerciali.codice` | append a `80_data/sql/dbops/automation_lock_columns.csv` | l'automazione `LOCK_COLUMNS` genera `trg_offerte_commerciali_a10_lock_columns_upd` |
| Lock `preventivi_righe.natura_vendita_id` | idem | idem, con codice errore dedicato |
| Codice errore `E_PREV_RIGA_NATURA_IMMUTABILE` (938) | append a `codici_errore.csv` + `messaggi_errore.csv` | classe `CONFLITTO_STATO`; un solo `%s`, come vuole `trgfn_lock_columns` |
| Codice automatico dei vettori | append a `80_data/sql/config/sistema_codici.csv` (riga 19, `VET-`) | il trigger di sync crea da sé sequenza, funzione e trigger `gen_codice` |
| Allineamento sequenza vettori | `80_data/changelog/20260821-06-setval-sequenza-codice-vettori-mctit.yaml` | evita che il primo `nextval` produca un codice già occupato (`uq_vettori_codice`) |
| **Provisioning immediato dei due lock** | `90_end/20260821-07-provision-lock-offerte-codice-e-preventivi-righe-natura-mctit.yaml` | fa girare `fn_run_automations_lock_columns` su `vendite` senza aspettare `ci_apply` o il pgagent |

I due changeSet non contengono DDL scritto a mano: `-06` fa un `setval` difensivo, `-07`
invoca il runner. La numerazione segue la sequenza globale per data (`20260821-01..05` erano
già usati in `20_code/vendite`).

### ⚠️ Il passo che avevo dimenticato — corretto dopo il primo migrate

Alla prima migrazione (2026-08-21) il test del codice vettore è uscito **verde**, quello dei
lock **rosso**: «no exception thrown». I due trigger non esistevano.

Non era un difetto del seed — le righe in `dbops.automation_lock_columns` erano caricate
correttamente — ma dei **tempi**, e la differenza merita di essere capita perché riguarda
due meccanismi che sembrano uguali e non lo sono:

| Meccanismo | Chi lo esegue | Quando |
|---|---|---|
| `config.sistema_codici` → sequenza + funzione + trigger `gen_codice` | un **trigger `AFTER`** sulla tabella di configurazione | nell'istante in cui il loader scrive la riga |
| `dbops.automation_lock_columns` → trigger di lock | un'**automazione batch** (`fn_run_automations_lock_columns`) | solo in `ci_apply`, o col pgagent la sera |

Entrambi sono dichiarativi, ma solo il primo è immediato. Per il secondo il progetto ha già
il suo rimedio, e io non l'avevo usato: un changeSet in `90_end` che fa girare il
provisioning subito. Il precedente è `90_end/20260818-23`, che documenta esattamente questo
inciampo — «su un migrate manuale il trigger non comparirebbe subito e il pgTAP resterebbe
rosso per una ragione che non è sua».

`20260821-07` è modellato su quello. Sta in `90_end` e non in `00_schema`/`20_code` perché il
runner deve **leggere** il seed di `80_data`: più in alto girerebbe prima del loader e non
provisionerebbe nulla, in silenzio.

### La scoperta che vale più dei tre presidi

Le `trgfn_*_gen_codice` **non sono scritte a mano**: le genera con DDL dinamico
`script.trgfn_config_sistema_codici_sync_gen_codice`, il trigger `AFTER` di
`config.sistema_codici`, che dalla sola riga di configurazione crea sequenza + funzione +
trigger. È il motivo per cui tutte e sette hanno corpo identico su una riga sola.

Modificarne una a mano non serve a niente — il loader `runOnChange` la riscrive al primo
migrate — e si spengono portando `usa_sequenza` a `false`, non con un `DROP`. Il fatto è ora
scritto in tutte e sei le pagine `gen_codice` della fascia A.

### Test

| File | Contenuto |
|---|---|
| `db/pgtap/vendite/offerte_commerciali/test-offerte-commerciali-codice-lock.sql` | nuovo, 6 asserzioni |
| `db/pgtap/anagrafiche/test-vettori-gen-codice.sql` | nuovo, 6 asserzioni |
| `db/pgtap/vendite/test-preventivi-righe-guard-natura-ricorrente-v1.sql` | esteso da 7 a 11 asserzioni |

`scripts/guardrail_pgtap_preambolo.py` è verde e il debito `throws_ok` resta a 131: i nuovi
test usano `throws_like`, mai uno SQLSTATE nudo.

**✅ Chiuso il 2026-08-21: tutto applicato, tutti i test verdi.**

Esito del **primo** migrate, tenuto come storia perché spiega il passo che mancava:

* `test-vettori-gen-codice.sql` → **6/6 verde** dopo una correzione di fixture
  (`vettori.descrizione` è `NOT NULL` senza default e l'`INSERT` la ometteva: il codice
  `VET-0000002` era già stato generato correttamente, a fallire era il vincolo accanto);
* `test-preventivi-righe-guard-natura-ricorrente-v1.sql` → 10/11, rosso il **test 9** perché
  il trigger di lock non era ancora stato provisionato (vedi sopra);
* `test-offerte-commerciali-codice-lock.sql` → stesso motivo.

Dopo il **secondo** migrate (con `20260821-07`, il provisioning dei lock) sono verdi tutti e
tre. Copertura finale misurata sul DB: **1279** auto-gen, **212** senza manuale, **83,4 %**.

### ⚠️ Il lock ha rotto due test esistenti — e la verifica che avevo fatto era difettosa

Col lock attivo sono usciti rossi due pgTAP **preesistenti**:
`test-fn-list-preventivi-da-pushare-natura-aware-v1.sql` e
`test-vw-preventivi-smistamento-v1.sql`. Entrambe le fixture azzeravano
`natura_vendita_id` con un `UPDATE` diretto — e il loro commento lo diceva apertamente:
*«il trigger di derivazione fira solo su INSERT/cambio articolo_id, non su UPDATE della
natura»*. **Sfruttavano consapevolmente il buco che stavamo chiudendo.**

🔴 **La verifica preventiva l'avevo fatta, ma con il grep sbagliato**:
`grep "natura_vendita_id" db/pgtap/ | grep -i update` cerca le due parole **sulla stessa
riga**, mentre in SQL `UPDATE tabella` e `SET colonna` stanno su righe diverse. Ha trovato
1 file su 3. Serve una ricerca multi-riga (regex con `re.S`), e non solo su `db/pgtap`:
anche `backend/apps`, `db/changelog`, `scripts`.

Rifatta come si deve: **3 punti in tutto**, di cui uno è il nuovo test che si aspetta il
blocco. **Zero nel backend** — ed è questa misura che conferma che il lock non toglie
nessuna operazione supportata.

**Come sono state riparate.** Non riscrivendo lo scenario: la riga a natura `NULL` è uno
stato **reale** — 45 righe su 197 nel DB di sviluppo, righe legacy nate prima del trigger di
ereditarietà — e non è più riproducibile passando dall'articolo, perché
`catalogo.articoli.natura_vendita_id` è `NOT NULL`. Le fixture usano quindi la porta di
manutenzione che `script.trgfn_lock_columns` prevede apposta, **richiudendola subito**:

```sql
SET LOCAL zeroerp.allow_lock_columns_override = 'on';
UPDATE vendite.preventivi_righe SET natura_vendita_id = NULL WHERE ...;
SET LOCAL zeroerp.allow_lock_columns_override = 'off';
```

⚠️ Richiudere non è cosmesi: lasciata aperta, la GUC renderebbe verdi **per sottrazione**
tutte le asserzioni successive che toccano colonne lockate.

**Baseline dopo la riparazione**: `vendite` 5 rossi su 199 e `anagrafiche` 11 su 57,
**tutti già noti** — nessuna regressione introdotta.

⭐ Il test 10 di `test-preventivi-righe-guard-natura-ricorrente-v1.sql` merita una riga a
parte: presidia l'**ordine alfabetico** fra `lock_columns` e `set_natura_vendita`. Il lock
funziona *perché* gira per primo e legge la natura non ancora riscritta; invertire i due nomi
bloccherebbe il cambio articolo legittimo, e quel test è l'unica cosa che se ne accorgerebbe.

### Documentazione aggiornata

Le tre pagine che dicevano «questo presidio non c'è» sono riscritte al presente, tenendo la
storia in una nota: `trgfn_offerte_commerciali_gen_codice`,
`trgfn_preventivi_righe_set_natura_vendita`, `trgfn_vettori_normalize`.

### Cosa resta da fare

1. ✅ **Migrato il 2026-08-21**, in due passate: la prima per seed/codici errore/codice
   vettore, la seconda per `20260821-07` (provisioning dei lock).
2. ✅ **I tre pgTAP sono verdi.**
3. Resta solo, se serve, togliere dalla baseline eventuali voci rientrate.
