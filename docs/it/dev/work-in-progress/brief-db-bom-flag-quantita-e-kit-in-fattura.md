# Brief DB — Distinta: due flag senza effetto da ritirare, e quantità e UoM del kit in fattura

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-02. **A chi:** team DB; poi BE/FE (§5).
> **Origine:** domande di Tid sulla distinta (unità di misura dei componenti, `partecipa_qta`,
> `determina_qta_padre`, esposizione in fattura), 2026-10-02. Tutto ciò che segue è letto dalla
> **struttura** (doc auto-gen, corpo vivo di trigger e viste, codice BE), non da conteggi.
> **Stato:** ✅ **tutte le decisioni prese da Tid il 2026-10-02** (D-1, D-2, D-3, D-3.1, D-4 — §3).
> ✅ **Lato DB CHIUSO il 2026-10-02** (§8): changeSet `20261002-60 → -67` **applicati su dbdev da
> Tid**, corsa pgTAP **verde** (adattati e nuovo compresi). ➡️ **La palla passa al BE/FE** (§5).
> Tid ha scelto di fare **tutto il DB subito**, ritiro delle colonne compreso, accettando
> l'interruzione del BE/FE fino al loro giro (nessuna produzione): dopo l'apply ⛔ **non si genera
> nessuna fattura** finché il BE non scrive il periodo (R-BE-B1), e ⛔ **la distinta non salva**
> finché il BE manda i due flag (R-BE-A1). Richieste in §5.
> La documentazione di modello e i `manual/` sono aggiornati (§7).
>
> **In una riga:** (A) `partecipa_qta` e `determina_qta_padre` si impostano ma nessuna logica li
> legge: si ritirano. (B) In fattura la riga del kit si ricava quantità e UoM **dai componenti**:
> con coefficienti diversi la fattura si blocca, con coefficienti uguali ma ≠ 1 o con più
> competenze esce sbagliata senza errore, e con un kit di unità diverse stampa un'unità a caso.
> Quantità e UoM del padre vanno congelate sulla fattura.

---

## 1. Parte A — due flag che non fanno niente

`catalogo.articoli_componenti` ha `partecipa_qta boolean NOT NULL DEFAULT true` e
`determina_qta_padre boolean NOT NULL DEFAULT false`. Dove compaiono (censimento completo,
2026-10-02):

| Dove | Come |
| --- | --- |
| colonne | `articoli_componenti` |
| guard di immutabilità | `trgfn_articoli_componenti_block_modifica_struttura` li confronta, e il trigger li ha nella lista `UPDATE OF` |
| vista | `vw_articoli_componenti_dettaglio` li proietta |
| parametri | `parameters.csv` righe 23 e 25: `CATALOGO_BOM_DEFAULT_PARTECIPA_QTA`, `CATALOGO_BOM_DEFAULT_DETERMINA_QTA_PADRE` |
| messaggio | `messaggi_errore.csv`, descrizione di `E_BOM_MODIFICA_VIETATA` (387) |
| BE | serializer in `catalogo/api/views.py` 133-134, whitelist in `catalogo_bom_repository.py` 36-37 e `catalogo_service.py` 997-998, smoke `smoke-test-catalogo-phase3.sh` e `smoke-test-preventivi-componenti.sh` |
| FE | `ArticoloBomDrawer.vue` (default, campi, payload), chiavi `catalogo.field_partecipa_qta` / `field_determina_qta_padre` |
| pgTAP | nove file li inseriscono o li verificano (§4.3) |

**Nessun lettore di logica.** La quantità di ogni componente è **sempre** `quantità padre ×
coeff_qta`: `script.trgfn_componenti_calcola_quantita`, `script.trgfn_componenti_propaga_qta`, e
al push in commessa `BoMComponentExpander._build_componente_pushable_row`. Nessuno dei tre guarda i
flag. Non sono nemmeno colonne di lista (`lista_colonna.csv`). Lo storico salva la riga come
`snapshot` jsonb: nessuna colonna da toccare.

Il modello lo diceva già («scheletro per logiche future», `modello-componenti-bom` §2), ma il
drawer li mostra: chi compila la distinta crede di decidere qualcosa e non succede nulla.

## 2. Parte B — quantità e UoM del kit in fattura

### 2.1 Come funziona oggi

`vendite.fatture_righe` per una riga di kit porta `kit_key`, `kit_esposizione`,
`kit_articolo_padre_id`, `kit_descrizione_padre`: **non** la quantità né la UoM del padre.
`vendite.vw_fattura_righe_esposte` le ricava dai componenti, nel CTE `kit`:

| Della riga del kit | Come |
| --- | --- |
| quantità | `avg(r.qta)` sui componenti |
| UoM | `max(r.uom_id)` sui componenti |
| prezzo unitario | `imponibile_totale / qta_media` |

raggruppando per `(fattura, kit_key, iva, BA, padre, descrizione)`. Il BE, per non stampare una
media senza significato, ferma la generazione se i componenti di un kit hanno quantità diverse
(R10, `FattureRigheService._guard_quantita_kit_omogenee`, `E_KIT_QUANTITA_DISOMOGENEE`).

### 2.2 Cosa ne segue — tutti casi che il modello ammette

1. **La distinta ammette ciò che la fattura rifiuta.** `coeff_qta` è libero per componente (la
   sedia con 8 viti è l'esempio della doc della tabella): la sua fattura non si genera.
2. **Coefficienti uguali ma ≠ 1: sbagliata senza errore.** 3 kit con tutti i componenti a
   `coeff_qta = 2` → riga del kit «6» a metà prezzo. Il totale torna, quantità e prezzo no.
3. **Kit con unità diverse: unità a caso.** Un kit installazione (caldaia in pezzi, tubo in metri,
   manodopera in ore) è legittimo: nessun vincolo lega la UoM del componente a quella del padre
   (l'unico vincolo padre-figli è l'IVA). In fattura la riga del kit esce con la UoM di un
   componente (`max(uom_id)`), e la quantità è una media fra metri, pezzi e ore.
4. **Lo stesso kit su più competenze nella stessa fattura.** `fatture_righe` non ha colonne di
   competenza: la competenza sta nella chiave di raggruppamento del BE, quindi un componente
   fatturato su due competenze dà **due** righe, ma la vista le rimette nello **stesso** kit. Un
   kit da 1 fatturato su due mesi: `avg(qta) = 1`, imponibile di due mesi → prezzo unitario doppio.
   R10 passa (le quantità sono uguali).

⭐ Un componente `NASCOSTO` non si vede, ma entra lo stesso nella media e nel `max`: è da lì che
nasce l'impressione di «unità mescolate».

### 2.3 Componente senza UoM nel documento

`uom_operativa_id` è **nullable** sulle quattro `*_righe_componenti` (preventivi, ordini,
contratti, DDT). Le `fn_*_riga_componenti_init` la valorizzano sempre con `articoli.uom_id` del
componente (`NOT NULL` sull'articolo), ma il BE al push ripiega sulla UoM **del padre**
(`componente.get("uom_operativa_id") or row.uom_id`, `commesse_source_handlers.py`). In un kit misto
un componente senza UoM diventerebbe «3 kit» invece di «3 metri». Il dato si può sempre fornire:
`NOT NULL`, e il ripiego si ritira.

## 3. Decisioni

| # | Domanda | Esito |
| --- | --- | --- |
| D-1 | `partecipa_qta` / `determina_qta_padre`: implementare o ritirare? | ✅ **Ritirare entrambi** (Tid, 2026-10-02). Un'impostazione senza effetto è il caso più fuorviante; se un giorno serve un componente a quantità fissa, nasce con la sua semantica e il suo cantiere |
| D-2 | Vietare `NASCOSTO` ai componenti con UoM diversa dal kit? | ✅ **No** (Tid, 2026-10-02). Il miscuglio nasce da §2.1, non dall'esposizione: con quantità e UoM del padre congelate, ogni riga stampata porta la sua unità e il nascosto non ne stampa nessuna. Il vincolo curerebbe il sintomo e vieterebbe il kit a prezzo unico, che è il caso più normale |
| D-3 | Caso 4: come si somma la quantità del kit su più competenze? | ✅ **Strada b, allargata** (Tid, 2026-10-02): `fatture_righe` porta **`competenza_dal` / `competenza_al` NOT NULL** (il sistema va predisposto per le utilities, gas ed energia fatturano per periodo); la riga del kit si separa per periodo come le righe normali. Righe esistenti: valore fittizio, anche la data della fattura. ⏳ Resta **D-3.1**: quando si stampa il periodo (§4.2) |
| D-4 | Righe già in `fatture_righe` (senza i dati nuovi) | ✅ **Nessun riguardo** (Tid, 2026-10-02): sono tutte di test, basta un valore **valido**. `competenza_dal = competenza_al = ` data della fattura (nessun periodo stampato); sulle righe di kit `kit_qta = 1` e `kit_uom_id` NULL (la UoM del padre non sta sulla riga; quella del componente darebbe unità discordanti nello stesso kit, provato). Niente ricostruzione dalle attività né fotografia della stampa di oggi |

## 4. Proposta DB

### 4.1 Parte A

⚠️ **Superato dalla scelta di Tid (2026-10-02)**: il DB va per primo, ritiro compreso, e il BE/FE
segue (§5). Testo originale: ordine: **prima BE e FE smettono di mandarli** (R-BE-A1, R-FE-A1). Finché le colonne esistono hanno
un default, quindi non si rompe nulla; poi il DB le ritira. Niente merge simultaneo.

1. Trigger di immutabilità: DROP + CREATE **senza** le due colonne nella lista `UPDATE OF` (la
   colonna nella lista è una dipendenza: è ciò che ha fatto fallire `20261001-42`), e corpo di
   `trgfn_articoli_componenti_block_modifica_struttura` senza i due confronti. La lista si prende
   dallo YAML vivo, non dalla doc auto-gen (che stampa l'evento senza le colonne).
2. `vw_articoli_componenti_dettaglio`: DROP prima delle colonne, ricreata senza nel `20_code`
   (`security_invoker` ri-dichiarato).
3. DROP delle due colonne.
4. `parameters.csv` righe 23 e 25: ritiro secondo la regola dei mirror (da verificare sulle linee
   guida prima di scrivere); `messaggi_errore.csv` 387: descrizione senza i due campi.
5. pgTAP adattati (§4.3).

### 4.2 Parte B

1. **`fatture_righe.kit_qta numeric`, `kit_uom_id`** (FK `unita_misura`): quantità e UoM della
   riga padre del documento, congelate alla generazione come `kit_descrizione_padre`.
   `chk_fatture_righe_kit_coerente` le include (tutte valorizzate o tutte NULL).
   **`fatture_righe.competenza_dal`, `competenza_al` date NOT NULL** (D-3), su **tutte** le righe:
   il periodo come entra nella chiave di raggruppamento del BE; per le righe puntuali `dal = al` =
   la data più recente fra le attività aggregate (D-3.1). La vista separa il kit anche per periodo
   ed espone il periodo da stampare (`dal ≠ al`) per PDF, SDI e portale.
2. **Da dove arrivano**: dal `meta` dell'attività di commessa, dove il BE le scrive al push
   (R-BE-B1). Una riga di fattura somma `kit_qta` sulle attività che aggrega, come somma `qta`.
3. **La vista** legge `kit_uom_id` e la quantità del kit da `kit_qta`, non più `avg`/`max`.
   ✅ **D-3 decisa: strada (b)**, il testo sotto resta come storia della scelta. A monte
   `commesse_attivita` e `attivita_fatturabili` hanno **già** `competenza_dal`/`competenza_al`
   `NOT NULL` (con `chk_attivita_competenza_dal_al`): è `fatture_righe` che oggi le perde. Il BE le
   mette nella chiave di raggruppamento solo se l'attività è un **periodo vero**
   (`_build_group_key`: `dal ≠ al` oppure `dal ≠ data_attivita`), altrimenti `None`.
   ✅ **D-3.1 decisa** (Tid, 2026-10-02): **si stampa il periodo quando `dal ≠ al`**, nessun flag.
   Una riga puntuale ha `dal = al`; se raggruppa più attività puntuali di date diverse porta
   **la data più recente** in entrambe (mai `min`–`max`: la regola lo stamperebbe come un periodo
   che non esiste). La stessa regola valorizza `DataInizioPeriodo`/`DataFinePeriodo` dell'SDI: una
   risposta sola per PDF, SDI e portale, in sede unica nella vista.
   Testo originale: con più righe dello stesso componente (caso 4), la quantità del kit è la somma di
   `kit_qta` sulle righe di **un** componente. Due forme da scegliere:
   * **(a)** `sum(kit_qta) / count(DISTINCT articolo_id)` sul kit: regge perché un componente sta
     una volta sola in una BoM alla data (`uq_articoli_componenti_no_overlap`) e ogni attività del
     padre porta tutti i componenti; ma è una derivazione, e va pinnata da un test;
   * **(b)** la riga del kit si separa per competenza come le righe normali: serve la competenza su
     `fatture_righe`, che oggi non c'è. Più lavoro, e cambia la rappresentazione.
   Proposta: **(a)**, con una regola che rifiuti un kit in cui i componenti non danno la stessa
   somma (è l'unico R10 che ha senso: «i componenti dicono lo stesso numero di kit»), in sede unica
   nella vista o in un guard DB, non in Python.
4. **R10 si ritira** dal BE (R-BE-B2): i coefficienti diversi non sono più un errore.
5. **`uom_operativa_id NOT NULL`** sulle quattro `*_righe_componenti` (§2.3), con verifica che
   nessun percorso di scrittura la lasci vuota (le `_init`, gli overrides, gli UPDATE del BE).
6. **D-4 (deciso)**: righe esistenti con valori validi qualsiasi (§3). ⚠️ Il guard `a10` blocca
   l'`UPDATE` oltre EMESSA: il riempimento va fatto senza far scattare guard di riga (DDL, sulla
   forma di `20261001-45`) o con un bypass di manutenzione esplicito — da scegliere leggendo il
   guard prima di scrivere. Poi `NOT NULL` sulle competenze e `chk_fatture_righe_kit_coerente`
   esteso alle due colonne kit.

### 4.3 pgTAP

* **Adattati (A)**: `catalogo/test-articoli-componenti-immutabilita` (tolti i test 6 e 7),
  `test-vw-articoli-componenti-dettaglio-capabilities-v1`, `test-vw-articoli-componenti-note`,
  `test-guard-iva-reactivation-v1`, `test-articoli-vincoli-note-uom-overlap`,
  `test-articoli-componenti-solo-componente`, `test-articoli-componenti-guard-attivo-composito`,
  `vendite/test-listini-righe-comp-guard-coerenza-bom-v1`, `vendite/test-vw-righe-dettaglio-sorgente-lista-v1`
  (test 8).
* **Nuovo (B)**, costruendo i casi, nessun confronto con la popolazione — un kit misto (caldaia PZ ×1,
  tubo MT ×3, manodopera ORE ×4), venduto in quantità 2:
  * **tre volte, una per modo** (tutto `NASCOSTO`, tutto `DESCRITTIVO`, tutto `VALORIZZATO`): la
    riga del kit dice sempre «2» nella UoM del padre; ogni componente esposto porta la sua unità
    e la sua quantità (2, 6, 8);
  * prezzo unitario del kit = importo del kit / 2;
  * lo stesso kit su **due competenze** nella stessa fattura: quantità 4 (o 2 + 2 con D-3 b),
    prezzo unitario invariato;
  * il totale del documento uguale in tutti i casi;
  * un componente senza UoM nel documento: rifiutato.

## 5. Richieste a BE/FE

⚠️ **Dall'apply del DB**, i punti ⛔ falliscono, non degradano: è l'interruzione accettata da Tid.

### BE

| # | Cosa | Dove |
| --- | --- | --- |
| **R-BE-A1** ⛔ | smettere di leggere e scrivere `partecipa_qta` / `determina_qta_padre`: serializer, whitelist di scrittura e lettura, smoke. Senza, il salvataggio di una riga di distinta fallisce sulla colonna che non c'è | `catalogo/api/views.py` 133-134, `catalogo_bom_repository.py` 36-37, `catalogo_service.py` 997-998, `smoke-test-catalogo-phase3.sh`, `smoke-test-preventivi-componenti.sh` |
| **R-BE-B1** ⛔ | **periodo sulla riga di fattura**: i tre `INSERT INTO vendite.fatture_righe` scrivono `competenza_dal`, `competenza_al` (NOT NULL, senza default). Il valore è quello della chiave di raggruppamento (`_build_group_key`): il periodo se l'attività ne ha uno; per una riga puntuale `dal = al` = **la data più recente** fra le attività aggregate (D-3.1). Per una rettifica, quello della riga rettificata. Senza, **nessuna fattura si genera** | `pipeline_repository.py` 2016, 3325, 3502; `fatture_righe_service.py` |
| **R-BE-B2** ⛔ | **quantità e UoM del kit**: al push, nel `meta` del componente, la quantità e la UoM della **riga padre** (chiavi nuove nel contratto `_kit_meta`, accanto a `componente_di` e `coeff_qta`); in generazione `kit_qta` = **somma** della quantità padre sulle attività aggregate (come `qta`), `kit_uom_id` = la UoM padre. `kit_qta` è obbligatoria sulle righe di kit: senza, una fattura con un kit non si genera | `_kit_meta.py`, `commesse_source_handlers.py` (`_build_componente_pushable_row`), `fatture_righe_service.py`, `pipeline_repository.py` |
| R-BE-B3 | ritiro di R10 (`_guard_quantita_kit_omogenee`) e dei suoi test: coefficienti diversi non sono più un errore. Poi il codice `E_KIT_QUANTITA_DISOMOGENEE` si ritira dal catalogo errori (R-DB al giro dopo: oggi il BE lo nomina ancora) | `fatture_righe_service.py` |
| R-BE-B4 | ritiro del ripiego `componente.get("uom_operativa_id") or row.uom_id`: la colonna è NOT NULL | `commesse_source_handlers.py` |
| R-BE-B5 | le attività **già in commessa** non hanno le chiavi nuove nel `meta`: script una tantum su dbdev (stampo di `allegati/esposizione-kit-meta-attivita-una-tantum.sql`), lanciato al merge di R-BE-B2. Valore: quantità padre = `quantita / coeff_qta` del meta dove `coeff_qta > 0`, altrimenti 1; UoM padre = quella dell'articolo padre (`componente_di`). Nessuna lettura di ripiego nel codice | script |
| R-BE-B6 | builder fattura: `competenza_dal`, `competenza_al`, `ha_periodo` di riga (da `vw_fattura_righe_lista`), e la quantità del kit che può essere **NULL** (nota parziale). È una **forma nuova** del contesto (patto versione/forma): numerazione da verificare con l'esigibilità (forma 4 / v6, `brief-db-esigibilita-iva-per-cassa-emittente` §11.3) | builder, template |
| R-BE-B7 | ⚠️ `vw_fattura_righe_lista.riga_key` del padre di kit cambia valore (il periodo entra nella tupla): se qualcuno la memorizza, va rigenerata. È calcolata, il DB non la salva da nessuna parte | chi la usa |

### FE

| # | Cosa | Dove |
| --- | --- | --- |
| **R-FE-A1** ⛔ | togliere i due campi dal drawer della distinta, i default letti dai due parametri (ritirati: oggi `paramBool` ripiega su `true`/`false`), le chiavi `catalogo.field_partecipa_qta` / `field_determina_qta_padre` | `ArticoloBomDrawer.vue` 213-243, 375-377; `it.json`, `en.json` |
| R-FE-B1 | drawer fattura: il periodo sulla riga quando `ha_periodo` è vero; una riga di kit con quantità vuota (nota parziale) non è un errore | `FatturaDrawer.vue` |

### Template

* **Una versione nuova della fattura** che stampa il periodo dove `ha_periodo` è vero (sulla riga del
  kit e sulle righe normali, non sui componenti, che stanno sotto il loro kit) e lascia vuota la
  quantità di un kit che non ne ha una. Dichiara la forma di R-BE-B6.

## 6. Fuori perimetro, dichiarato

* La stampa dei kit in preventivi, ordini e DDT: altra logica, già esclusa dal brief
  dell'esposizione (§7).
* Un componente a quantità fissa (ciò che `partecipa_qta = false` sembrava promettere): se arriva
  un caso, nasce come cantiere a sé.
* Kit annidati: vietati dal modello (`modello-componenti-bom` §9.2).

## 7. Documentazione — aggiornata (2026-10-02)

* `dev/manual/modello-componenti-bom.md`: §2 (flag ritirati, UoM libera e NOT NULL nei documenti),
  §7.1 riscritto (quantità, UoM e periodo del kit dalla riga padre del documento).
* `dev/manual/changelog-decisioni-componenti.md`: le due decisioni del 2026-10-02.
* `guide/gestione-listini.md` §5.3: i due flag tolti dai campi di struttura.
* `dbzero/catalogo/manual/`: `articoli_componenti`, `vw_articoli_componenti_dettaglio`,
  `trgfn_articoli_componenti_block_modifica_struttura`.
* `dbzero/vendite/manual/`: `fatture_righe` (colonne, CHECK, FK), `vw_fattura_righe_esposte`
  (convenzioni, colonne in coda), `vw_fattura_righe_lista`, e i cinque `*_componenti` (UoM NOT NULL).
* La doc auto-gen si rigenera dopo l'apply (non da questa sessione).

## 8. Lato DB — cosa è stato scritto (applicato su dbdev il 2026-10-02)

> ✅ **Apply e pgTAP di Tid, 2026-10-02**: migrazione applicata (nessun
> componente senza UoM su dbdev: `-66` è passato), corsa pgTAP **verde**. Da qui su dbdev le due
> colonne della distinta e i due parametri non esistono più, e `fatture_righe` vuole il periodo:
> finché R-BE-A1, R-BE-B1 e R-BE-B2 non arrivano, il BE fallisce dove li scrive (salvataggio della
> distinta, generazione di ogni fattura, fattura con un kit). Resta da confermare la scelta di §8.1
> (nessun rifiuto al posto di R10).

### 8.1 I changeSet

| # | Fase | Cosa |
| --- | --- | --- |
| `-60` | `00_schema/catalogo` | DROP delle due colonne. Prima droppa la vista dettaglio e il trigger di immutabilità (le colonne sono nella sua lista `UPDATE OF`: la trappola di `20261001-42`), poi lo ricrea con la stessa lista meno le due |
| `-61` | `20_code/catalogo` | corpo del guard senza i due confronti (corpo vivo, sostituzioni contate) |
| `-62` | `20_code/catalogo` | `vw_articoli_componenti_dettaglio` ricreata senza le due colonne |
| `-63` | `00_schema/vendite` | `fatture_righe`: `competenza_dal/_al` NOT NULL (fast default `CURRENT_DATE` per le righe esistenti, poi DROP DEFAULT), `chk_fatture_righe_competenza_dal_al`; `kit_qta` (riempita a 1 sulle righe di kit con `ALTER TYPE … USING`, senza trigger di riga), `kit_uom_id` (NULL sulle esistenti) con FK; `chk_fatture_righe_kit_coerente` esteso |
| `-64` | `20_code/vendite` | `vw_fattura_righe_esposte` (CREATE OR REPLACE): quantità e UoM del kit da `kit_qta`/`kit_uom_id` componente per componente, `NULL` se discordanti; kit separato per periodo; in coda `competenza_dal`, `competenza_al`, `ha_periodo` |
| `-65` | `20_code/vendite` | `vw_fattura_righe_lista` (CREATE OR REPLACE): periodo nella partizione dei componenti e nella `riga_key` del padre; le tre colonne in coda |
| `-66` | `00_schema/vendite` | `uom_operativa_id` NOT NULL sui quattro `*_righe_componenti` e su `offerte_commerciali_eccezioni_componenti` |
| `-67` | `80_data` | DELETE dei due parametri `CATALOGO_BOM_DEFAULT_*` e dei loro override (forward-only, §11.2) |

CSV: `parameters.csv` (righe 23 e 25 tolte), `messaggi_errore.csv` (descrizione di
`E_BOM_MODIFICA_VIETATA`, 387).

⭐ **Scelta fatta scrivendo, da confermare (Tid)**: al posto di R10 **nessun rifiuto**. Con la strada (b) un
kit i cui componenti non dicono lo stesso numero di kit è una **nota di credito parziale** (si rende
un componente solo): un caso legittimo, dove il kit non ha una quantità. La vista lo stampa con
quantità e prezzo `NULL` e il suo importo. Il §4.2 proponeva una regola che rifiutasse: valeva per
la strada (a).

⚠️ **Se il migrate si ferma su `-66`**: una riga di componente di documento è senza UoM su dbdev. Il
changeSet lo dice per tabella; si trova con `SELECT id FROM vendite.<tabella> WHERE uom_operativa_id IS NULL`
e si corregge a mano con la UoM del componente. Tutte le funzioni che scrivono quelle righe la
valorizzano già.

### 8.2 pgTAP

* **Nuovo**: `vendite/test-fatture-righe-kit-qta-periodo-v1.sql` (24 test) — il kit misto (tre unità
  diverse, 2 kit) nei tre modi, lo stesso kit su gennaio e febbraio, la nota parziale, il componente
  spezzato per prezzo, il totale invariato, la lista, i vincoli nuovi, i flag e i parametri ritirati,
  e la lista `UPDATE OF` del trigger ricreato letta da `pg_trigger.tgattr`.
* **Parte A** (9 file): tolte le due colonne dagli INSERT sulla distinta (parser che toglie colonna e
  valore nella stessa posizione); `test-articoli-componenti-immutabilita` senza i test 6 e 7
  (numerazione degli altri invariata, piano 16); `test-vw-righe-dettaglio-sorgente-lista-v1` test 8
  rovesciato (le due colonne **non** devono esserci).
* **Parte B**: i 49 INSERT su `fatture_righe` in 29 file portano `competenza_dal, competenza_al`
  (`CURRENT_DATE`, riga puntuale); le righe di kit di `tre-modi`, `lista` e `importo-e-kit` portano
  `kit_qta`; gli 8 INSERT di componenti in 7 file portano la UoM vera del componente — tre `throws_ok`
  aspettavano il CHECK sull'origine, e il NOT NULL sarebbe scattato prima; altri tre accettavano
  qualunque errore e sarebbero passati per il motivo sbagliato.
* ⚠️ **Il nono, sfuggito (corsa di Tid, 2026-10-02)**: `script/test-fn-check-prezzi-autorizzati-v1.sql`,
  INSERT su `ddt_righe_componenti` (fixture dei casi DDT) senza `uom_operativa_id` → `23502`, 13/44
  rossi. Il censimento di prima aveva corretto le due sorelle dello stesso file (preventivi, ordini)
  e non questa. Corretta allo stesso modo (UoM del componente); provato sullo scratch in
  transazione annullata: 44/44. Ricensimento con un parser su tutti i `db/pgtap/**` e sui changelog
  (INSERT sulle cinque tabelle del `-66` senza la colonna): nessun altro caso.
* ⚠️ **`vendite/test-vw-fattura-righe-esposte-tre-modi-v1.sql` test 8 (corsa di Tid, 2026-10-02)**:
  il padre KV usciva con `qta = 2` invece di 1. La vista `-64` raggruppa il kit **componente per
  componente**, cioè per `articolo_id`; la fixture scriveva le righe di kit **senza articolo**, e i
  due componenti di KV cadevano nello stesso gruppo `NULL`: `sum(kit_qta)` = 1 + 1. Corretta la
  fixture (tre articoli componente, uno per posizione nel kit); scratch in transazione annullata:
  18/18.
  ⛔ **Ma il difetto non è solo della fixture: il modello lo ammette.** `chk_fatture_righe_kit_coerente`
  non pretende `articolo_id` su una riga di kit, e su due componenti senza articolo la vista dà una
  quantità del kit **sbagliata, senza errore**. Chi scrive le righe di kit in fattura è il BE
  (`fatture_righe_service`, `pipeline_repository`). Decisione per Tid in §8.2.1.
  Stessa forma, verdi **per coincidenza** (non asseriscono la quantità del padre):
  `vendite/test-vw-fattura-righe-lista-v1.sql` (KA, tre componenti senza articolo → la vista gli dà 3
  kit) e `vendite/test-fatture-righe-importo-e-kit-v1.sql` (K-TEST). Da allineare insieme alla §8.2.1.

#### 8.2.1 Una riga di kit senza articolo — ✅ decisa la strada (a) (Tid, 2026-10-02)

> ✅ **Scritto il 2026-10-02**: `00_schema/vendite/20261002-43` (CHECK
> `chk_fatture_righe_kit_articolo`: `kit_key IS NULL OR articolo_id IS NOT NULL`, un CHECK suo e non
> dentro quello di coerenza: due regole, due nomi). `preCondition` HALT sulle righe di kit senza
> articolo già scritte (su dbdev non le ho contate: come app sotto RLS uno zero non direbbe
> niente; se il migrate si ferma, la query è nel messaggio). Censimento dei writer: solo il BE
> (`pipeline_repository`, l'articolo del gruppo è il `componente_id` della riga del documento);
> nessuna funzione del DB scrive righe di kit. Nessuna richiesta al BE.
> pgTAP: `test-fatture-righe-kit-qta-periodo-v1` **test 25** nuovo (`throws_like` sul nome del
> vincolo, piano 25); fixture allineate in `test-vw-fattura-righe-lista-v1` (KA, KB) e
> `test-fatture-righe-importo-e-kit-v1` (K-TEST). Prova sullo scratch con l'SQL estratto in testa,
> transazione annullata: `kit-qta-periodo` 25/25, `tre-modi` 18/18, `lista` 14/14 (precondizioni a
> 0). ⚠️ `importo-e-kit` sullo scratch si ferma prima, sul difetto di fixture già in baseline
> (`ERRORE_FIXTURE`, registro senza emittente): la sua modifica la prova solo la corsa su dbdev.
> Pagina `manual/` di `fatture_righe` aggiornata.
> ✅ **Applicato su dbdev il 2026-10-02 da Tid (`20261002-43`), corsa pgTAP verde**: la
> `preCondition` non ha trovato righe di kit senza articolo, e i file corretti in questo giro
> (`test-fn-check-prezzi-autorizzati-v1`, `tre-modi`, `lista`, `importo-e-kit`,
> `kit-qta-periodo` con il test 25) sono verdi.
> Fuori da questo cantiere, nello stesso giro: `vendite/test-fn-list-ddt-da-pushare-v1.sql` sceglieva
> «l'ultimo articolo attivo», senza il filtro `is_composito IS FALSE` dei fratelli; su dbdev era un
> kit con componenti gestiti, la bolla muoveva merce e la porta del registro (`20260928-71`)
> rifiutava l'`UPDATE` a EMESSO. Ora costruisce un articolo semplice non gestito; verde.


Un componente di kit è un articolo della distinta (`articoli_componenti.componente_id` è NOT NULL),
e la vista lo identifica per `articolo_id`. Due strade:

* **(a, consigliata)** CHECK: `kit_key IS NOT NULL → articolo_id IS NOT NULL`, aggiunto a
  `chk_fatture_righe_kit_coerente` (o un CHECK suo). Il contratto lo dice la tabella, e la vista
  resta com'è. Prima: censire i writer del BE (devono già scriverlo: una riga di kit nasce da un
  componente) e le righe di kit su dbdev senza articolo (`preCondition` HALT, si correggono a
  mano); poi le due fixture qui sopra.
* **(b)** la vista tratta una riga senza articolo come un componente a sé (`COALESCE(articolo_id,
  id)` nel raggruppamento). Non rifiuta niente, ma dà un significato a una riga che il modello non
  sa spiegare («componente di quale distinta?»).

### 8.3 Come è stato provato, e cosa la prova NON copre

* **Cancelli statici** verdi: `guardrail_sql_letterali`, `_run_on_change`, `_precondition_seed`,
  `_ddl_su_trigger_automazione`, `_grant_ruolo_batch`, `_timestamp_senza_fuso`, `_pgtap_preambolo`
  (che segnala il debito `throws_ok` sceso a 115: la soglia nel cancello si può abbassare).
* **SQL estratto** dagli YAML (`changes[].sql.sql`, non riscritto) su **cluster PG18 usa-e-getta**,
  sopra stub con la forma della doc auto-gen e gli oggetti di prima presi dai loro YAML (`-42` trigger,
  `-43`, `-44`, `-46`, `-47`). Un trigger stub che **rifiuta ogni UPDATE** su `fatture_righe`
  dimostra che `-63` riempie senza toccare righe. Verde in avanti; i casi del modello tornano tutti
  (kit misto «2 kit a 250» nei tre modi, due periodi «1 a 250» ciascuno invece di «1 a 500», nota
  parziale con quantità vuota, totali uguali alla tabella); i rifiuti attesi scattano (periodo
  mancante o rovesciato, kit senza `kit_qta`, `kit_uom_id` fuori kit, componente senza UoM, modifica
  di un campo di struttura); verde **all'indietro** (rollback `-67 → -60`, stato di prima ripristinato).
  ⚠️ Trovato e corretto durante la prova: `kit_uom_id` riempita con la UoM del componente dava unità
  discordanti nello stesso kit, quindi ora resta NULL sulle righe di prima (D-4).
* ⚠️ **Non copre**: i dati veri, la RLS, `plpgsql_check`, i presidi trasversali, le automazioni di
  `ci_apply` (il `require_attivo` che nascerà su `kit_uom_id`, come su `uom_id`), il mirror di
  `parameters.csv` (risvegliato ieri senza errori), il pgTAP vero. ✅ Apply e corsa pgTAP di Tid
  il 2026-10-02: verdi.
