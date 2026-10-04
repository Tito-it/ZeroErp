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
> ✅ **Lato BE/FE scritto il 2026-10-03** (§9, `dev/backend-tid`, non committato): R-BE-A1, B1, B2,
> B3, B4, B6 e R-FE-A1 fatti, test verdi; R-BE-B5 è uno script da lanciare (§9.3); il template v7 è
> da pubblicare. ✅ ~~Restano al team DB due richieste nuove (§9.4)~~ (fatte, §10): `fn_accredita_riga_reso`
> deve scrivere la quantità padre **accreditata** (oggi la eredita dalla riga rettificata: la
> nota di credito di un kit si ferma, voluto) e la colonna `periodo` della lista 102.
> ✅ **Secondo giro DB scritto il 2026-10-03 (§10)**: R-DB-B8, B9 (strada 3 di Tid: due colonne
> «Periodo dal» / «Periodo al»), B10. changeSet `20261003-05`, `-06` + due CSV.
> ✅ **Applicato su dbdev da Tid il 2026-10-03, baseline `vendite` senza regressioni**: lato DB
> di nuovo CHIUSO.
> ➡️ Restano FE (R-FE-B1 rivista, §10.4) e BE (rigenerare le policy dei codici errore).
> ⭐ **Plafond e kit (§11)**: il kit si spezza come un'unità sola (D-5, D-5.1 di Tid, 2026-10-03).
> DB `20261003-07`, `-08`, `-09` ✅ **applicato su dbdev da Tid il 2026-10-03, baseline verdi**.
> ✅ **Terzo giro BE/FE scritto il 2026-10-03 (§12, non committato)**: R-FE-B1 rivista, R-BE-B8,
> R-BE-P1…P6, test verdi. ✅ Script R-BE-B5 lanciato da Tid lo stesso giorno (§9.3).
> ➡️ Restano a Tid il migrate che accende le due colonne (CSV) e la pubblicazione della v7; al
> team DB due ritocchi (§12.4).
> ⛔ **E un difetto della madre da correggere (R-DB-B13, §12.5, Tid 2026-10-03)**:
> `fn_consuma_plafond_titolo_iva_righe` rifiuta i componenti a imponibile `<= 0`, che il modello
> ammette. Il BE oggi li tiene fuori dalla chiamata: è un ramo **provvisorio**, si ritira col fix.
> ⭐ **Da leggere per primo: §13 — decisione C di Tid (2026-10-04)**: il plafond si consuma sul
> **netto** della fattura, le righe negative restituiscono. Comprende R-DB-B13. ✅ Lato DB
> **scritto il 2026-10-04** (§13.8: `20261004-02 → -06` + grant `90_end`), ✅ **applicato su dbdev
> da Tid il 2026-10-04, pgTAP verdi, nessuna regressione**; poi un giro BE solo (§13.6, §13.9). Firme **aggiunte in coda**, nessuna riordinata: dopo
> l'apply il BE di oggi continua a funzionare, tranne un caso (§13.9: il kit con un componente a
> zero o negativo, finché il BE non fa il giro C).
> ✅ **§14 — strada A di Tid (2026-10-04)**: una fattura che ha consumato plafond non si disfa più
> (le tre porte di reset e la pulizia la fermano con `E_FATTURE_PLAFOND_CONSUMATO`). DB scritto
> (`20261004-07 → -11` + CSV), ✅ applicato su dbdev da Tid il 2026-10-04, pgTAP verdi.
> ✅ **Lato DB CHIUSO**. ➡️ Resta il giro BE/FE: R-BE-C1…C9 (§13.6, §13.9), R-BE-A1 e R-FE-A1 (§14.4).
> ✅ **Quarto giro BE/FE scritto il 2026-10-04 (§15, non committato)**: R-BE-C1…C9, R-BE-A1,
> R-FE-A1, test verdi. ➡️ **Al team DB due richieste nuove (§15.4)**: ritirare il ramo di
> proiezione del risolutore (decisione di Tid: orfano → si ritira) e dare alla fattura singola la
> sua chiave di motivo (`fattura_plafond_consumato`, scelta A di Tid).
> ✅ **Quinto giro DB scritto il 2026-10-04 (§16)**: R-DB-C10 (`20261004-15`: la proiezione si
> ritira, un importo solleva) e R-DB-A2 (`20261004-16`), più il testo di
> `E_IVA_RESOLVE_NON_INVOCABILE`. ⏳ **Da applicare** (Tid), poi corsa pgTAP. Al BE solo un
> ritocco facoltativo (§16.4).
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
> distinta, generazione di ogni fattura, fattura con un kit). La scelta di §8.1 è confermata (Tid, 2026-10-03)
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

⭐ **Scelta fatta scrivendo, ✅ confermata da Tid il 2026-10-03**: al posto di R10 **nessun rifiuto**. Con la strada (b) un
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

## 9. Lato BE/FE — cosa è stato scritto (2026-10-03)

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-03. **A chi:** Tid (commit, script,
> pubblicazione del template), team DB (§9.4).
> **Stato:** scritto, **non committato**. Test: `apps.vendite`, `apps.catalogo`, `apps.core` 3828
> verdi (103 skip); i test sul DB provvisto toccati (`catalogo/tests/db`, righe fattura lista,
> scritture dinamiche, guardrail pipeline, seed liste e ricerca) verdi; frontend `vitest` 574 verdi,
> `guards` e lint verdi. ⚠️ Nessun giro di generazione **su dbdev**: i test della generazione sono
> mockati, la giuntura con le colonne nuove la prova solo il primo lotto vero (§9.5).

### 9.1 Le richieste del §5

| # | Stato | Dove |
| --- | --- | --- |
| R-BE-A1 | ✅ via da serializer, whitelist di scrittura, normalizzatore del service, due smoke | `catalogo/api/views.py`, `catalogo_bom_repository.py`, `catalogo_service.py`, `smoke-test-catalogo-phase3.sh`, `smoke-test-preventivi-componenti.sh`; `api_catalogo.md` |
| R-BE-B1 | ✅ le tre `INSERT` scrivono il periodo | `pipeline_repository.py`: generazione (`batch_insert_righe_and_mark`), parte di plafond (copia quello della capofila). La terza, `insert_fattura_riga`, non aveva chiamanti: **ritirata** (§9.5) |
| R-BE-B2 | ✅ push e generazione | `_kit_meta.py` (`qta_padre`, `uom_padre_id` + i due lettori), `commesse_source_handlers.py`, `fatture_righe_service.py` |
| R-BE-B3 | ✅ R10 ritirata coi suoi test | `fatture_righe_service.py`. `E_KIT_QUANTITA_DISOMOGENEE` nessun punto di chiamata: **al team DB il ritiro dal catalogo** (resta in `error_policies_generated.py` e nel ripiego finché il catalogo lo porta) |
| R-BE-B4 | ✅ `componente["uom_operativa_id"]`, niente ripiego | `commesse_source_handlers.py` |
| R-BE-B5 | ✅ **lanciato da Tid il 2026-10-03** (§9.3) | [`allegati/kit-qta-uom-padre-meta-attivita-una-tantum.sql`](allegati/kit-qta-uom-padre-meta-attivita-una-tantum.sql), §9.3 |
| R-BE-B6 | ✅ builder alla **forma 5** | `fattura_document_context_builder.py`: per riga `competenza_dal`/`_al` (italiano) + `_iso` + `ha_periodo` (trasportato, non ricalcolato); `quantita`/`prezzo_unitario` NULL restano NULL. `api_fattura_dettaglio.md` |
| R-BE-B7 | ✅ niente da fare | nessun consumatore memorizza `riga_key`: lista e drawer la leggono a ogni caricamento |
| R-FE-A1 | ✅ campi, default dai parametri, chiavi i18n | `ArticoloBomDrawer.vue`, `it.json`, `en.json` |
| R-FE-B1 | ✅ a metà, **aspetta il DB** | slot `#cell-periodo` in `FatturaDrawer.vue` + chiavi `vendite.fatture.col_periodo`/`periodo_valore`: si accende quando il catalogo ha la colonna (R-DB-B9, §9.4). Il kit con quantità vuota non rompe niente: la colonna numerica mostra il vuoto |
| Template | ✅ **v7 scritta, da pubblicare** | [`template-fattura-v7.html`](template-fattura-v7.html) = v6 + periodo sotto la descrizione quando `ha_periodo` + quantità e prezzo vuoti (non «-») sul kit senza quantità. Dichiara la **forma 5**. Prova: resa Jinja con i due casi |

⚠️ **Dal deploy del BE, finché la v7 non è pubblicata, la fattura non si stampa**: il builder
produce la forma 5 e nessuna versione la dichiara. È il patto versione/forma che fa il suo
mestiere; la sequenza è quella di sempre (riavvio, bozza dall'app, pubblicazione).

### 9.2 Scelte fatte scrivendo

* **Il periodo di una rettifica è quello della riga rettificata**, e vince anche su un periodo
  vero dell'attività: come prezzo, sconto e IVA (N-1). L'attività di rettifica porta la data
  dell'accredito, non quella del fatto che corregge. Letto nella stessa proiezione
  (`rett_competenza_dal/_al` da `fatture_righe`), una riga rettificata senza periodo è un errore.
* **Riga puntuale**: `dal = al = max(competenza_al)` sulle attività aggregate — su un'attività
  puntuale `competenza_al` è la data dell'attività (è la definizione di puntuale in
  `_build_group_key`). Il periodo vero si legge dalla chiave, non si ricalcola.
* **`uom_padre_id` entra nel bucket** come padre ed esposizione: è del kit, e una riga ne porta una
  sola.
* **Nessun ripiego per le chiavi mancanti**: un componente senza `qta_padre` o `uom_padre_id` nel
  meta ferma la generazione con `E_GROUP_ATTIVITA_INVALID_DATA` (lo stesso codice delle altre
  attività incomplete — prezzo, BA — col dettaglio che nomina la chiave).
* **Il segno**: la quantità padre e quella del componente descrivono la stessa attività (D-NC-2),
  quindi devono avere lo stesso segno. Se non ce l'hanno la generazione si ferma, con lo stesso
  codice. È il presidio del difetto in §9.4 R-DB-B8.
* La quantità padre nel meta è la quantità della riga padre **com'è** (`PushableRow.quantita`), con
  la sua UoM (`uom_id`): è la coppia che la riga avrebbe in fattura se non fosse un kit, ed è
  quella su cui il push moltiplica `coeff_qta`.

### 9.3 R-BE-B5 — lo script delle attività già in commessa

Stessa forma dello stampo: prova in `ROLLBACK` di default, `-v applica=1` per il `COMMIT`, ruolo
superuser o `BYPASSRLS`, savepoint per riga con l'elenco delle rifiutate, bypass di manutenzione
per le attività già fatturate. Aggiunge le due chiavi ai componenti di kit (`componente_di` nel
meta) che non le hanno; le chiavi già scritte dal push vincono. In coda due controlli: chi è
rimasto senza chiavi, e chi ha la quantità padre di segno opposto (attese zero righe).
⚠️ **Non l'ho lanciato** (azione su DB): va lanciato da Tid col merge del BE. Prima di allora una
fattura con un componente di kit già in commessa non si genera, e lo dice.
✅ **Lanciato da Tid il 2026-10-03** (`postgres`, prova e poi `-v applica=1`, `COMMIT`): componenti
senza le chiavi da 24 → 0 su `commesse_attivita` e da 21 → 0 su `attivita_fatturabili`, nessuna riga
rifiutata, nessuna quantità padre di segno discorde. Prima del lancio corretto un difetto dello
script: senza `coeff_qta` valido scriveva `1` anche su una rettifica (ora `-1`, col segno della
quantità), che il controllo del segno avrebbe fermato.

### 9.4 Richieste al team DB

> ✅ **Tutte e tre scritte e applicate il 2026-10-03 (§10)**. R-DB-B9 non nella forma chiesta qui: due
> colonne invece di una, scelta di Tid (§10.2).

| # | Cosa | Perché |
| --- | --- | --- |
| **R-DB-B8** ⛔ | `vendite.fn_accredita_riga_reso`: nel `jsonb_build_object` a destra del `\|\|` del `p_meta` aggiungere `'qta_padre', - v_quota` (sui componenti; `v_quota` è già in unità padre) | Il meta della rettifica **eredita** quello della riga rettificata (P-7): dal push di R-BE-B2 porta la quantità padre dell'**originale**, positiva, su componenti negativi. Scritta così, la nota di credito direbbe «+2 kit». Il BE la rifiuta (segno opposto, §9.2): ⇒ **oggi l'accredito di un kit non si fattura** finché questo non arriva. È la terza chiave che «potrebbe mentire», accanto a `tipo_consumo` e `segment_key` che il commento della funzione già nomina. `uom_padre_id` ereditata è giusta |
| R-DB-B9 | lista 102 (`vendite.fattura_righe`): una colonna `periodo` (`campo_sorgente` `competenza_dal`, data, non ordinabile, esportabile, `etichetta_i18n_key` `vendite.fatture.col_periodo`), sulla forma di `riga_rettificata` | Il drawer la rende con lo slot `#cell-periodo` (già scritto); a catalogo vale anche per l'export. Senza, il periodo a video non c'è |
| R-DB-B10 | ritiro di `E_KIT_QUANTITA_DISOMOGENEE` dal catalogo errori | R-BE-B3 fatto: nessun punto di chiamata |

### 9.5 Cosa resta, dichiarato

* ⚠️ **Il primo lotto vero su dbdev** è la prova che manca: la `INSERT` della generazione ha
  quattro array nuovi nell'`unnest`, e i test la mockano. Va guardato il primo giro dopo lo script.
* ✅ `insert_fattura_riga` del repository **ritirata** (2026-10-03, ok di Tid): nessun chiamante —
  verificato anche per nome in stringa —, solo un omonimo nel mock dei test, tolto con lei insieme
  al contatore `insert_calls` che asseriva uno zero ormai senza significato.
* **Plafond e kit, difetto preesistente**: la parte di una riga spezzata dal plafond
  (`insert_parte_plafond`) non copia le colonne kit, quindi la parte di un componente esce dal
  kit come riga sciolta. Non è di questo cantiere e non l'ho toccato; con `kit_qta` la domanda
  diventa anche «come si divide la quantità padre fra capofila e parte». Da decidere.
* Il guard `test_error_codes_db_policy_guardrail` sul DB provvisto è rosso per
  `E_EMITTENTE_REGIME_CONFERMA_DERIVATA` (cantiere esigibilità, non questo): manca il
  `genera_error_policies`.

### 9.6 Revisione critica del codice (2026-10-03)

* 🔴 **Corretto un difetto che non dava errore.** La «data più recente» di D-3.1 era calcolata **per
  riga**: se un componente di un kit finisce in due righe (prezzi diversi nel tempo) e un altro in
  una sola, le righe dello stesso kit prendevano date diverse, la vista separava il kit in due
  padri e la quantità del kit usciva NULL. Ora le righe **puntuali** di un'istanza di kit
  (fattura, `kit_key`) portano tutte la data più recente del kit (`_allinea_periodo_kit`); periodo
  vero e periodo della rettifica non si toccano. Test 48, provato che cade senza la correzione.
* Controllo del segno più stretto: un componente non nullo con la quantità padre a zero passava;
  ora è rifiutato (test 49).
* Regola del 2: il `require` di `E_GROUP_ATTIVITA_INVALID_DATA` era scritto **12 volte** nello stesso
  file (7 di prima, 5 mie): ora è `_richiedi_dati_attivita`, copie ritirate. Il nome funzione
  della generazione, cablato in cinque punti, è una costante.
* Builder: `competenza_dal`, `competenza_al` e `ha_periodo` si leggono **stretti** — una colonna
  sparita dalla vista ferma la stampa invece di diventare «nessun periodo» su ogni riga.
* Messaggi del `meta`: «senza una … valida» (la chiave può esserci con un valore illeggibile).

## 10. Lato DB, secondo giro — le richieste del §9.4 (2026-10-03)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-03. **A chi:** Tid (apply, pgTAP), poi
> FE e BE (§10.4).
> **Stato:** ✅ **applicato su dbdev da Tid il 2026-10-03**; baseline pgTAP `vendite` di Tid
> **senza regressioni**, file toccati compresi (`test-accredito-kit-meta-v1` con il test 9,
> `test-fatture-righe-kit-qta-periodo-v1` con il test 26). Non committato.

### 10.1 R-DB-B8 — la rettifica di un kit dice quanti kit rende

`20_code/vendite/20261003-05-update-fn-accredita-riga-reso-qta-padre`. Nel `p_meta` della
rettifica, a destra del `||`, una chiave in più:
`'qta_padre', CASE WHEN v_cmp.e_componente THEN - v_quota END`. `v_quota` è già in unità
padre. Su una riga che non è di kit la chiave non nasce (`jsonb_strip_nulls`). `uom_padre_id`
resta quella ereditata, che è giusta. Il corpo è quello del `20260921-30`, verificato riga per
riga uguale al corpo vivo della doc auto-gen; firma e `RETURNS TABLE` ancorati con `%TYPE`.
Aggiornati anche il commento interno («le chiavi che potrebbero mentire», ora tre) e il
`COMMENT`.

pgTAP: `vendite/test-accredito-kit-meta-v1.sql`, **test 9** (piano 9). La fixture ora scrive il
meta come il push di oggi (`qta_padre` = quantità / coefficiente, cioè +10), e il test pretende
`-3` su entrambe le rettifiche. Senza `-05` è rosso.

### 10.2 R-DB-B9 — il periodo nella lista 102, in due colonne

Tid ha scelto la **strada 3** (2026-10-03). La richiesta del BE era una colonna `periodo` con
`campo_sorgente = competenza_dal`. Ma l'export legge il `campo_sorgente`: avrebbe mostrato solo
l'inizio del periodo, e una data anche sulle righe puntuali, dove il drawer mostra «—».

* `20_code/vendite/20261003-06-update-vw-fattura-righe-lista-periodo-da-mostrare`:
  `vw_fattura_righe_lista` (CREATE OR REPLACE, `security_invoker` ri-dichiarato) con in coda
  `periodo_dal` e `periodo_al`: `competenza_dal`/`_al` quando `ha_periodo`, altrimenti NULL. La
  regola «quando c'è un periodo» resta una sola, in `vw_fattura_righe_esposte`: la lista legge
  `ha_periodo`, non la rifà.
* `ui/lista_colonna.csv`, righe **1098** `periodo_dal` e **1099** `periodo_al`: data
  (`date_short`), esportabili, non ordinabili né filtrabili, `ordine_default` 22 e 24 (subito
  dopo la descrizione), priorità 25, chiavi `vendite.fatture.col_periodo_dal` /
  `col_periodo_al`. ⚠️ **Nascono `attivo = f`**: le due chiavi non sono nei locales, e
  `check_i18n_keys.py` legge le colonne attive del CSV. Le accende il FE nello stesso commit in
  cui aggiunge le chiavi (§10.4). Il repository fa `SELECT v.*`, quindi le colonne arrivano al
  FE senza lavoro BE.

pgTAP: `vendite/test-fatture-righe-kit-qta-periodo-v1.sql`, **test 26** (piano 26):
`periodo_dal/_al` uguali al periodo sul kit di gennaio e febbraio, NULL sulle righe puntuali.

### 10.3 R-DB-B10 — `E_KIT_QUANTITA_DISOMOGENEE` ritirato

`config/codici_errore.csv`: `obsoleto_dal = 2026-10-03`, con la nota del perché. Il codice si
ritira, non si cancella (guida Messaggi di errore, «Ritirare un codice»): `error_log` può
puntarci. Il messaggio in `messaggi_errore.csv` resta, per lo stesso motivo.

### 10.4 Richieste a FE e BE

| # | Cosa | Dove |
| --- | --- | --- |
| **R-FE-B1 (rivista)** | Le due chiavi `vendite.fatture.col_periodo_dal` («Periodo dal» / «Period from») e `col_periodo_al` («Periodo al» / «Period to») in `it.json` e `en.json`, e **nello stesso commit** `attivo = t` sulle righe 1098 e 1099 di `lista_colonna.csv`. Lo slot `#cell-periodo` di `FatturaDrawer.vue` e le chiavi `col_periodo` / `periodo_valore` non servono più: nessuna colonna si chiama `periodo`, e le due colonne nuove sono già vuote dove non c'è un periodo | `FatturaDrawer.vue`, locales, `lista_colonna.csv` |
| R-BE-B8 | Rigenerare `error_policies_generated.py` (`genera_error_policies`): il codice ritirato esce con «⚠️ RITIRATO». Da guardare anche la voce in `error_messages_fallback.py` | `apps/core/services/` |

### 10.5 Come è stato provato, e cosa la prova NON copre

* **SQL estratto** dagli YAML (`changes[].sql.sql`) su `zeroerp_ci` come `zeroerp`, dentro
  `BEGIN … ROLLBACK` con il `BEGIN` in testa al file ricomposto. Impronta (`md5` di
  `pg_get_functiondef` e `pg_get_viewdef`) presa prima e confrontata dopo: oggetti vivi
  invariati.
* `test-fatture-righe-kit-qta-periodo-v1`: **26/26** con l'SQL estratto; senza, il test 26
  muore su «la colonna periodo_dal non esiste» (il test vede il difetto).
* `plpgsql_check_function_tb` sulla funzione nuova: **0 segnalazioni**.
* Le due righe di `lista_colonna` inserite dopo la vista nuova, anche accese: il guard
  `a10_valida_campo_sorgente` le accetta, e rifiuta un `campo_sorgente` inesistente.
* Cancelli statici verdi: `guardrail_sql_letterali`, `_run_on_change`, `_precondition_seed`,
  `_ddl_su_trigger_automazione`, `_grant_ruolo_batch`, `_timestamp_senza_fuso`,
  `_pgtap_preambolo`. `check_i18n_keys` ha un rosso che non è di questo cantiere
  (`amministrazione.accessi.blocca_reason.credenziale_di_sistema`, dalla credenziale).
* ⚠️ **Non provato prima dell'apply: il test 9 di `test-accredito-kit-meta-v1`.** Su
  `zeroerp_ci` il file si ferma sulla fixture (nessun billing account): è già in
  `baseline-rossi-scratch.tsv` e `baseline-rossi-ci.tsv` come `ERRORE_FIXTURE`. Lo prova solo
  la corsa su dbdev. ✅ Coperto dalla baseline `vendite` di Tid del 2026-10-03: nessuna
  regressione.
* ⚠️ **Dati su dbdev, non toccati**: un accredito di kit fatto **dopo** il deploy del push
  R-BE-B2 e **prima** di `-05` porta la `qta_padre` positiva ereditata, e lo script R-BE-B5 non
  lo corregge (lascia vincere le chiavi già scritte). Se ce ne sono, la loro fattura si ferma
  sul controllo del segno. Si trovano con
  `SELECT id, meta->>'qta_padre', quantita FROM vendite.commesse_attivita WHERE meta->>'accredito_da' = 'RESO' AND meta ? 'qta_padre' AND (meta->>'qta_padre')::numeric > 0`.
  ✅ **Chiusa da Tid (2026-10-03)**: sono dati di test, nessun problema; se servirà li
  corregge a mano. Nessuno script di bonifica.

## 11. Plafond e kit — la regola di Tid e cosa serve (2026-10-03)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-03. Riprende il difetto preesistente del
> §9.5. **Stato:** D-5 e D-5.1 decise da Tid. ✅ Lato DB **scritto, non applicato** (§11.5):
> `20261003-07`, `-08`, `-09` ✅ **applicati su dbdev da Tid il 2026-10-03, baseline verdi**.
> ➡️ Resta il BE (§11.6).

### 11.1 Come funziona oggi

`PlafondFatturaService._consuma_riga` lavora **riga per riga** (`list_righe_per_plafond`, in
ordine di `riga_nr`), e i componenti di un kit sono righe come le altre. Su un plafond residuo che
non copre tutto il kit, quindi, i primi componenti vengono coperti per intero, uno viene spezzato
(`qta_coperta = quota / prezzo effettivo`) e gli ultimi restano all'aliquota ordinaria: ogni
componente con una frazione diversa. In più la parte nuova (`insert_parte_plafond`) **non copia
le colonne kit**, ed esce dal kit come riga sciolta. Il `COMMENT` di `vw_fattura_righe_esposte`
dice «oggi il backend non spezza i componenti di kit»: è superato, li spezza.

### 11.2 D-5 — la regola (Tid, 2026-10-03)

**Il kit si spezza come un'unità sola, con la stessa frazione per tutti i componenti.** Un kit di
quantità 3 che deve scendere a 1,2 per stare nel plafond diventa una riga di kit da 1,2 (tutti i
componenti a 1,2/3 della loro quantità, aliquota del titolo) e una da 1,8 (gli stessi componenti
a 1,8/3, aliquota ordinaria).

In pratica:

* la frazione è `f = quota coperta / imponibile del kit` (la somma dei componenti, non uno alla
  volta). In generale non è tonda (1,2345 kit), come oggi la quantità di una riga sciolta
  spezzata: è il metodo «la quantità si deriva dall'imponibile» già scelto da Tid;
* ogni componente: capofila `qta × f`, parte `qta × (1 − f)`; `kit_qta` allo stesso modo
  (`kit_qta × f` e `kit_qta × (1 − f)`), e la parte **copia le colonne kit**;
* ⭐ **la vista è già pronta**: `vw_fattura_righe_esposte` costruisce il padre per (fattura, kit,
  **IVA**, BA, periodo) e una riga che è insieme componente e parte di plafond «cade nei rami del
  kit». Le due metà, con aliquote diverse, escono da sole come due righe padre: «1,2 kit» e
  «1,8 kit», ciascuna con la sua quantità coerente. Da aggiornare solo il `COMMENT`.

### 11.3 Dove vive, proposta

* **DB**: una madre che consuma il plafond **per un kit intero** (lock del titolo una volta,
  quota coperta sulla somma dei componenti, un movimento per componente, i centesimi distribuiti
  in modo che la somma dei movimenti sia la quota coperta) e restituisce la quota di ogni riga.
  Oggi `anagrafiche.fn_consuma_plafond_titolo_iva` lavora su una riga sola
  (`p_fattura_riga_id`): chiamarla N volte non dà una frazione unica, perché il residuo cambia a
  ogni chiamata.
* **BE**: `PlafondFatturaService` raggruppa per `kit_key`, chiama la madre per il gruppo, scrive
  le due parti di ogni componente con la stessa frazione e copia le colonne kit sulla parte.
* pgTAP: il kit misto del §10 (tre unità) su un plafond che copre 1,2 kit su 3.

### 11.4 D-5.1 — un titolo che copre solo una parte del kit — ✅ decisa la (a) (Tid, 2026-10-03)

Il titolo IVA ha un **ambito**: `TUTTO`, oppure un elenco di articoli, gruppi voce o tipi voce
(`soggetti_titoli_iva_ambiti`, letto da `fn_resolve_iva_riga_it` allo stadio B **sull'articolo
della riga**). Un kit installazione (caldaia, tubo, manodopera) con un titolo il cui ambito
comprende la caldaia ma non la manodopera si risolverebbe in modo diverso componente per
componente. Con la regola di D-5 le righe uscirebbero discordi: nella metà ordinaria, i componenti
coperti dicono 1,8 kit e quelli fuori ambito 3, e la vista dà al kit una quantità NULL.

* **(a, consigliata)** **il titolo si giudica sull'articolo PADRE del kit**: se il padre è
  nell'ambito, tutti i componenti seguono il titolo con la stessa frazione; se non lo è, nessuno.
  È coerente con quello che il modello fa già allo stadio A, dove l'IVA dei componenti è
  vincolata a quella del padre (l'unico vincolo padre-figli): il kit è la cosa venduta.
* **(b)** si giudica componente per componente, e la frazione si applica solo ai componenti
  nell'ambito; quelli fuori restano interi all'ordinaria. Rispetta l'ambito alla lettera, ma la
  metà ordinaria del kit non ha più una quantità (NULL), e il kit a video si legge male.

### 11.5 Lato DB — cosa è stato scritto (2026-10-03, ✅ applicato, baseline verdi)

> ✅ **Apply e baseline di Tid, 2026-10-03**: migrazione applicata su dbdev, baseline pgTAP
> verdi, compresi il test nuovo e i due dei titoli IVA che passano dall'involucro.

| # | Fase | Cosa |
| --- | --- | --- |
| `-07` | `20_code/anagrafiche` | `fn_consuma_plafond_titolo_iva_righe(titolo, fattura, righe[], imponibili[], data, tx)`: un lock, la quota coperta sulla somma del gruppo, ogni riga `round(imponibile × f, scala del suo imponibile)`, l'ultima il resto; un movimento per riga con quota > 0; ritorna per riga quota coperta, quota ordinaria, **frazione effettiva**, residuo, movimento. Diventa la sede delle regole di consumo (guard, lock, validità, titolo senza tetto, idempotenza, capienza). Guard nuovo: le righe devono essere della fattura passata |
| `-08` | `20_code/anagrafiche` | `fn_consuma_plafond_titolo_iva` diventa l'**involucro** a una riga (`ARRAY[riga]`, `ARRAY[imponibile]`): firma e risultato invariati, anche la scala. Così la capienza non si ricopia (regola del 2). Corpo di prima nel rollback |
| `-09` | `20_code/vendite` | solo il `COMMENT` di `vw_fattura_righe_esposte`: il «limite dichiarato» sui componenti di kit spezzati dal plafond diventa la regola D-5. Corpo invariato |

pgTAP: **nuovo** `anagrafiche/test-consuma-plafond-titolo-iva-righe-v1.sql` (12 test): il kit da 500
su plafond 200 (80, 24, 96 con frazione 0,4), i movimenti, l'idempotenza, il centesimo (tre
righe da 10 su plafond 10: 3,33 3,33 3,34), copertura piena, capienza zero, titolo senza tetto,
quattro guard. La forma a una riga resta provata da `test-soggetti-titoli-iva` (18-22) e
`test-soggetti-titoli-iva-due-emittenti`, che ora passano dall'involucro.

Doc `manual/`: pagina nuova `anagrafiche/manual/fn_consuma_plafond_titolo_iva_righe.md`;
aggiornate `fn_consuma_plafond_titolo_iva.md` e `vendite/manual/vw_fattura_righe_esposte.md`.

⚠️ Un guard di gruppo usa `E_TITOLO_IVA_CONSUMO_NON_INVOCABILE` («Consumo di plafond invocato
senza %s.»): sulla riga di un'altra fattura la frase dice «senza fattura_riga_ids», che è
impreciso. È un errore TECNICO (un chiamante rotto), e il contesto porta righe e fattura: non
ho coniato un codice nuovo. La `soluzione` del messaggio nomina ancora solo la forma a una riga.

**Come è stato provato** (SQL estratto su `zeroerp_ci` come `zeroerp`, `BEGIN … ROLLBACK`,
impronta degli oggetti vivi uguale prima e dopo):

* `test-consuma-plafond-titolo-iva-righe-v1`: **12/12**;
* `test-soggetti-titoli-iva` **23/23** e `test-soggetti-titoli-iva-due-emittenti` **5/5** con
  l'involucro, uguali a senza: la parità c'è, compresi i confronti testuali
  (`'(700.00,300.00)'`). ⚠️ Sullo scratch oggi passano, e le due baseline (scratch e CI) li
  registrano ancora come `ERRORE_FIXTURE`: il registro è indietro, non è un effetto di questo giro;
* `test-fatture-righe-kit-qta-periodo-v1` 26/26 con il `-09` in testa;
* `plpgsql_check` sulle due funzioni: **0 segnalazioni** (una prima stesura dichiarava a mano
  il contatore dei `FOR`, che il ciclo dichiara da sé: tolto);
* cancelli statici verdi.

⚠️ **Non provato prima dell'apply**: la RLS come app (la prova è da owner), i dati veri, il
pgTAP vero. ✅ RLS e pgTAP coperti dalle baseline di Tid del 2026-10-03. Resta vero che il BE che
usa la funzione non esiste ancora: oggi nessun chiamante passa più di una riga.

### 11.6 Richieste al BE

| # | Cosa | Dove |
| --- | --- | --- |
| **R-BE-P1** | `list_righe_per_plafond` porta anche le colonne kit (`kit_key`, `kit_esposizione`, `kit_articolo_padre_id`, `kit_descrizione_padre`, `kit_qta`, `kit_uom_id`) | `pipeline_repository.py` |
| **R-BE-P2** | `PlafondFatturaService` raggruppa le righe per `kit_key` (una riga sciolta è un gruppo di uno). Per un kit: **D-5.1 (a)**, il risolutore si chiama con l'articolo **padre** (`kit_articolo_padre_id`) e l'imponibile del kit intero; il titolo, se c'è, vale per tutti i componenti | `plafond_fattura_service.py` |
| **R-BE-P3** | Il consumo di un kit passa da `anagrafiche.fn_consuma_plafond_titolo_iva_righe` con le righe in ordine di `riga_nr`, e la ripartizione si legge **da lì** (è lei che prende il lock). Frazione 1: copertura piena su tutte. Frazione 0: niente. Altrimenti ogni componente si spezza con il metodo di oggi (`qta_coperta = quota_coperta / prezzo effettivo`, parte = resto) | idem |
| **R-BE-P4** | `kit_qta` della capofila = `kit_qta × frazione`, della parte = `kit_qta −` quella, **calcolati una volta per il kit** e scritti uguali su tutti i componenti: è ciò che fa dire alla vista lo stesso numero di kit su ogni metà | idem, `aggiorna_capofila_plafond` |
| **R-BE-P5** | `insert_parte_plafond` copia le colonne kit dalla capofila (`kit_key`, `kit_esposizione`, `kit_articolo_padre_id`, `kit_descrizione_padre`, `kit_uom_id`) e scrive il `kit_qta` della parte. Senza, la parte esce dal kit come riga sciolta (il difetto del §9.5) | `pipeline_repository.py` |
| R-BE-P6 | Test: il kit misto su un plafond che copre 1,2 kit su 3 → due righe padre «1,2» e «1,8», ciascuna con i suoi tre componenti; totale invariato | test del servizio |

## 12. Lato BE/FE, terzo giro — R-FE-B1 rivista, R-BE-B8, plafond e kit (2026-10-03)

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-03. **A chi:** Tid (commit, migrate
> del CSV), team DB (§12.4).
> **Stato:** scritto, **non committato**. Test: `apps.vendite`, `apps.core`, `apps.catalogo`
> 3847 verdi (103 skip); sul DB provvisto (`ZEROERP_TEST_DB_E2E=1`) `apps.vendite.tests.db` e i
> due presidi dei codici errore (divergenza, policy) 150 verdi; frontend `vitest` 623 verdi,
> `lint`, `guards` e `check_i18n_keys` puliti.

### 12.1 Le richieste

| # | Stato | Dove |
| --- | --- | --- |
| R-FE-B1 (rivista, §10.4) | ✅ chiavi `vendite.fatture.col_periodo_dal` / `col_periodo_al` (it, en); `attivo = t` sulle righe 1098 e 1099 di `lista_colonna.csv`; ritirati lo slot `#cell-periodo` e le chiavi `col_periodo` / `periodo_valore` della fattura (la `col_periodo` della dashboard è un'altra chiave e resta) | `FatturaDrawer.vue`, `it.json`, `en.json`, `lista_colonna.csv` |
| R-BE-B8 | ✅ `genera_error_policies`: `E_KIT_QUANTITA_DISOMOGENEE` esce «⚠️ RITIRATO» ed entra in `CODICI_RITIRATI` (99 ritirati su 971). La voce in `error_messages_fallback.py` **resta**: un codice ritirato si legge ancora nel diario, ed è la convenzione del modulo | `error_policies_generated.py` |
| R-BE-P1 | ✅ le sei colonne kit nella proiezione | `pipeline_repository.list_righe_per_plafond` |
| R-BE-P2 | ✅ gruppi di consumo: i componenti di un kit (stessa `kit_key`) insieme, ogni riga sciolta da sola; per un kit il risolutore si chiama con `kit_articolo_padre_id` e l'imponibile del kit intero (D-5.1 a) | `plafond_fattura_service._gruppi_di_consumo`, `_consuma_gruppo` |
| R-BE-P3 | ✅ una chiamata a `fn_consuma_plafond_titolo_iva_righe` per gruppo, righe in ordine di `riga_nr`; frazione 1 → copertura piena, 0 → niente, altrimenti ogni riga si spezza col metodo di oggi (`quota / prezzo effettivo`) | `pipeline_repository.consuma_plafond_titolo_righe` |
| R-BE-P4 | ✅ `kit_qta × frazione` alla capofila, il resto alla parte (vedi §12.2 sul «per riga») | `_spezza`, `aggiorna_capofila_plafond` |
| R-BE-P5 | ✅ la parte copia `kit_key`, `kit_esposizione`, `kit_articolo_padre_id`, `kit_descrizione_padre`, `kit_uom_id` dalla capofila e scrive il suo `kit_qta` | `pipeline_repository.insert_parte_plafond` |
| R-BE-P6 | ✅ nove casi nuovi (18-26), fra cui il kit misto 1,2 + 1,8 su 3, il padre al risolutore, una chiamata per kit, il componente a imponibile zero, il componente su due righe | `test_plafond_fattura_service.py` |

### 12.2 Scelte fatte scrivendo

* **Una strada sola.** La riga sciolta è un gruppo di uno e passa anch'essa da
  `fn_consuma_plafond_titolo_iva_righe`: due strade di consumo sarebbero due copie delle regole di
  spezzatura. Il wrapper a una riga del repository (`consuma_plafond_titolo`) aveva quel solo
  chiamante ed è **sostituito** da `consuma_plafond_titolo_righe`. Per una riga sola la madre dà
  la stessa ripartizione dell'involucro (`-08`).
* **`kit_qta` è per riga, non per kit.** Un componente fatturato a due prezzi ha due righe, ognuna
  con la quota di kit delle sue attività, e la vista le **somma** per componente. Ogni riga si
  divide con la stessa frazione, quindi la somma per componente resta uguale fra componenti. Nel
  caso comune (un componente, una riga) è proprio il «calcolato una volta e scritto uguale» di
  R-BE-P4. Il prodotto `kit_qta × frazione` si fa in un contesto `Decimal` a 100 cifre: un
  arrotondamento lì farebbe dire ai componenti due numeri di kit diversi, e la vista darebbe NULL.
* ⛔ **Componente a imponibile zero o negativo — ramo PROVVISORIO, la sede giusta è la madre
  (R-DB-B13, §12.5).** Il modello lo ammette (nessun CHECK di segno su `qta` e
  `prezzo_unitario`), la madre lo rifiuta. Oggi il BE non lo passa alla madre e lo spezza con la
  frazione del kit (`qta × f`), così la sua `kit_qta` non resta intera sulla metà del titolo. ⚠️
  Sul **negativo** il ramo è anche sbagliato: la frazione si calcola sulla somma dei soli
  componenti positivi, quindi un kit con un componente negativo consuma più plafond del suo
  valore netto. Si ritira col fix del DB.
* **Due controlli nuovi, stesso codice (`E_PIPELINE_VALIDATION`)**: la madre deve ripartire
  **tutte** le righe passate, e in copertura parziale la frazione sta in (0, 1). Sono contratti di
  chiamata, non regole di dominio.
* **Ordine fra gruppi**: quello della loro prima riga. A plafond quasi esaurito decide chi resta
  coperto, e resta l'ordine di stampa come prima.
* **Rilancio**: alla seconda passata la madre rilegge il registro (frazione 1 sulle capofila già
  ridotte): copertura piena, quantità e `kit_qta` riscritte uguali, nessuna parte nuova.

### 12.3 Cosa la prova NON copre

* I test del servizio mockano repository e madre. Il SQL nuovo è provato sul DB vero **senza
  scrivere**: `INSERT … SELECT` e `UPDATE` su un id inesistente (zero righe) in una transazione
  annullata — colonne e tipi accettati — e la firma della madre con `to_regprocedure`. ⚠️ La
  chiamata vera della madre con gli array, e un kit spezzato letto da `vw_fattura_righe_esposte`,
  li prova solo il primo lotto con un titolo a plafond su dbdev.
* ⚠️ **Le due colonne del periodo si accendono col migrate** del CSV (`lista_colonna.csv`, mirror
  `80_data`): fino ad allora la lista resta senza periodo, come oggi. Lo lancia Tid.

### 12.4 Al team DB (due ritocchi, nessun blocco)

| # | Cosa | Perché |
| --- | --- | --- |
| R-DB-B11 | `config/codici_errore.csv`, nota di `E_KIT_QUANTITA_DISOMOGENEE`: gli apici sono **raddoppiati** (`quantita''`, `piu''`) | Il CSV non è SQL: il raddoppio arriva com'è fino al commento di `error_policies_generated.py` |
| R-DB-B12 | `dbzero/vendite/manual/fatture_righe.md`, paragrafo «Non si confonde con le righe di un kit»: dice che sulla spezzatura del plafond le colonne `kit_*` «non vanno usate» | Dal D-5 la parte di un **componente** le copia (R-BE-P5). Resta vero per una riga sciolta; per un componente va detto il contrario |

### 12.5 R-DB-B13 — la madre deve accettare i componenti a imponibile zero o negativo

> **Decisione di Tid, 2026-10-03:** il rifiuto è un difetto del DB, da correggere lì. Non si
> aggira nel BE.

**Il difetto.** `fn_consuma_plafond_titolo_iva_righe` solleva `E_TITOLO_IVA_CONSUMO_NON_INVOCABILE`
se un imponibile del gruppo è `NULL` o `<= 0`. Ma un kit può avere un componente a importo zero
(un omaggio nel kit) o negativo: `fatture_righe` non ha CHECK di segno su `qta` né su
`prezzo_unitario`, per scelta (manual di `fatture_righe`, «Note progettuali»). Il guard copiava
quello della forma a una riga, dove una riga a zero non ha niente da coprire; in un gruppo il
componente fa parte del kit, e il kit si spezza **tutto** (D-5).

**Cosa vuole il modello** (D-5: «la frazione è quota coperta / imponibile del kit, la somma dei
componenti»):

* la base della frazione è l'imponibile **netto** del kit, componenti a zero e negativi compresi;
* ogni riga del gruppo torna nel risultato, con la sua quota e la stessa `frazione`, così il
  chiamante spezza tutte le righe con la madre come unica autorità (oggi il BE ricalcola `qta × f`
  per le righe escluse: è la seconda sede che va ritirata);
* resta il rifiuto per `NULL` (un imponibile che non c'è) e per un gruppo il cui totale netto è
  `<= 0` (non c'è niente da coprire: il BE già non chiama);
* **zero**: quota 0, nessun movimento.

**La decisione da prendere: il negativo e il registro.** Il registro vuole un movimento `FATTURA`
positivo (`chk_stiva_movimenti_segno`) e uno per riga (`uq_stiva_movimenti_documento`). Con un
componente negativo, i movimenti positivi dei soli componenti positivi sommano **più** della quota
coperta del kit netto. Due strade:

* **(a, consigliata)** le quote per riga si calcolano sul netto (`round(imponibile × f)`, negative
  sui negativi, l'ultima riga il resto), ma i **movimenti** si scrivono solo sulle righe positive,
  ridotti in proporzione in modo che la loro somma sia la quota coperta netta. Il registro resta
  «solo positivi, uno per riga», la ripartizione per riga resta esatta per la fattura. È il punto da
  provare con un pgTAP che costruisce il kit con il componente negativo;
* **(b)** un movimento solo per gruppo, ancorato alla prima riga positiva, con la quota netta. Più
  semplice nel registro, ma una riga coperta senza il suo movimento non si spiega più dal registro.

**Lato BE, dopo il fix** (si prenota qui, si fa al giro dopo): `_consuma_gruppo` passa **tutte**
le righe del gruppo; si ritirano il filtro `consumanti` e il ramo `coperta is None` di `_spezza`
(`qta × f`); i test 21 e 25 si riscrivono sulla risposta della madre, più un caso col componente
negativo.

> ⚠️ **§12.5 superato dal §13** (Tid, 2026-10-04): la strada (a) e le sue correzioni sono
> diventate la decisione C, che le comprende e va oltre (le righe negative restituiscono plafond).

## 13. Decisione C — il plafond si consuma sul NETTO della fattura (2026-10-04)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-04. **A chi:** Tid, team BE (§13.6).
> **Decisioni di Tid** (conversazione del 2026-10-03/04): R-DB-B13 con la strada (a) e i punti
> 1-3 della proposta DB; sul punto 4 la **C**: *le righe negative si accettano e restituiscono
> plafond*. «Non ho produzione, inutile fare mille giri»: un giro solo, in ordine, fino a C.

### 13.1 La regola, in una frase

Sotto un titolo con tetto, una fattura consuma il suo **valore netto**: le righe positive
consumano, le negative restituiscono, e nessuna fattura consuma più della capienza né
restituisce più di quanto essa stessa consuma.

Esempio: plafond residuo 500, fattura con merce 1000 e uno sconto −100, tutto nell'ambito del
titolo. Netto 900, coperti 500: merce 600 al titolo e 400 all'ordinaria, sconto −100 al titolo.
Movimenti: +600 e −100, cioè 500 consumati. È lo stesso risultato che darebbe lo sconto spalmato
su tutta la merce (900 netti, 500 coperti, 400 all'ordinaria), ma senza inventare una
ripartizione dello sconto che in fattura non c'è.

### 13.2 Come si calcola (la madre, per un titolo e una fattura)

La madre riceve **tutte le righe della fattura che il chiamante ha attribuito a quel titolo**, in
una chiamata sola, e:

1. **raggruppa da sé**: le righe con la stessa `kit_key` sono un gruppo (un kit si spezza come
   un'unità sola, D-5), ogni riga senza `kit_key` è un gruppo di uno. I gruppi vanno
   nell'ordine della loro prima riga (`riga_nr`): è l'ordine di stampa, ed è lui che decide chi
   resta coperto a plafond quasi esaurito;
2. **legge l'imponibile dalla riga** (`fatture_righe.imponibile_riga`, `NOT NULL`). Il parametro
   `p_imponibili` resta dov'è (la firma non si riordina, regola di Tid del 2026-10-04) e diventa un
   **contratto di coerenza**: deve dire lo stesso della riga, o la chiamata si ferma (il chiamante
   ha ragionato su una riga che nel frattempo è cambiata);
3. calcola il **netto di ogni gruppo**: positivo, negativo o zero (un kit con un componente
   negativo è positivo se il totale lo è);
4. **i gruppi negativi** si coprono fino a quanto valgono i positivi della stessa chiamata
   (`N− = min(negativi, positivi)`), in ordine: una fattura non restituisce più di quanto
   consuma. Il negativo che avanza resta all'aliquota ordinaria: restituire plafond consumato da
   un **altro** documento è il mestiere della nota di credito, che quel documento lo nomina (P4,
   fuori da questo giro);
5. **i gruppi positivi** si coprono, in ordine, fino a `min(positivi, capienza + N−)`: il
   primo per intero, poi uno spezzato, poi gli altri all'ordinaria, come oggi;
6. **un gruppo a netto zero** (un kit con un omaggio, o con +50 e −50) è coperto per intero,
   frazione 1: non consuma niente, quindi il titolo non ha motivo di lasciarlo;
7. dentro un gruppo la frazione è **una** (`f = quota del gruppo / netto del gruppo`): ogni
   riga prende `round(imponibile × f, scala del suo imponibile)`, e il resto dei centesimi va
   alla riga col **valore assoluto più grande dello stesso segno del gruppo** (a pari merito
   l'ultima), poi, se non basta il suo margine, alla successiva. Così ogni quota resta fra zero e
   il suo imponibile, col suo segno, e la somma è esatta;
8. **un movimento per riga, col segno della riga**: positivo dove la quota è positiva, negativo
   dove è negativa, nessuno dove è zero. Prima tutti i positivi, poi i negativi: l'accumulatore
   rifiuta un conto sotto zero **riga per riga**, e un negativo scritto per primo su un titolo
   intonso lo farebbe scattare;
9. **idempotenza**: se una delle righe ha già un movimento su questo titolo e questa fattura, si
   rilegge il registro (quota = movimento, zero dove non c'è) e la frazione di ogni gruppo si
   ricava da lì (netto zero → 1). Con i movimenti col segno questa rilettura è esatta: era il
   difetto della strada (a), dove movimenti e quote non coincidevano.

Il titolo senza tetto copre tutto e non scrive, come oggi.

### 13.3 Il registro: un movimento `FATTURA` può essere negativo

`chk_stiva_movimenti_segno` oggi vuole `FATTURA > 0`. Diventa `FATTURA <> 0`.

⭐ **Perché `FATTURA` col segno e non `NOTA_CREDITO`** (correzione di quanto avevo scritto il
2026-10-03): il tipo dice **quale documento** ha prodotto il movimento. Una riga negativa di una
fattura è la fattura che si nettizza, non una nota di credito: scriverla `NOTA_CREDITO`
farebbe dire al registro che c'è un documento che non esiste, e la riconciliazione col fatturato
cercherebbe una NC che non c'è. `NOTA_CREDITO` resta `< 0` e resta della P4. Lo zero resta
vietato: non è un movimento.

### 13.4 Il risolutore: nel giro serve sapere QUALE titolo, non quanto copre

Per consumare sul netto il BE deve sapere, gruppo per gruppo, quale titolo vale e quali sono i due
trattamenti (titolo e ordinario). Il risolutore oggi non lo dice in modo affidabile:

* con un imponibile **proietta** la spezzatura sul residuo del momento: a residuo zero il titolo
  sparisce dalla risposta, e con le righe negative la proiezione per gruppo è sbagliata per
  costruzione (è la madre a sapere il netto);
* un imponibile **negativo** lo rifiuta;
* il trattamento ordinario esce solo quando la proiezione spezza.

Si **aggiunge** una domanda, senza toccare quelle che ci sono:

* parametro nuovo **in coda alla firma**: `p_consumo boolean DEFAULT false`, nel guscio (dopo
  `p_e_cessione_beni`) e in `_it` (dopo `p_emittente_fiscale_id`). ⛔ `p_imponibile` e la colonna
  `quota` **restano dove sono**: la firma non si riordina (Tid, 2026-10-04). ⚠️ La prima stesura
  sostituiva `p_imponibile` in terza posizione e toglieva `quota`: corretta lo stesso giorno;
* `p_consumo = false`: **tutto come prima** (anteprima con `p_imponibile` NULL, proiezione con
  l'importo);
* `p_consumo = true` (il giro): nessun titolo → una riga, l'ordinaria; titolo senza tetto → una
  riga, il titolo; titolo con tetto → **due righe sempre**, prima il titolo e poi l'ordinaria,
  `quota` NULL, **senza leggere il residuo**: la spezzatura la decide la madre;
* guard nuovi: `p_consumo` NULL; `p_consumo` con `p_imponibile` valorizzato (il consumo non prende
  un importo).

⚠️ Aggiungere un parametro crea un overload: `DROP` della firma vecchia prima del `CREATE`.
Chiamanti di oggi invariati: il BE (`iva_resolver_repository.py`, per posizione) continua a
funzionare senza toccare niente, e i pgTAP esistenti del risolutore non cambiano.

⚠️ **Da decidere (Tid)**: quando il BE passa al consumo (R-BE-C2), il ramo di **proiezione**
(`p_imponibile` valorizzato) resta senza chiamanti. Per ora resta, dichiarato qui; ritirarlo è una
decisione a sé (togliere il ramo, non il parametro).

### 13.5 La forma a una riga si ritira

`anagrafiche.fn_consuma_plafond_titolo_iva` (l'involucro del `-08`) non ha più chiamanti dal
terzo giro BE (§12.2) e la firma della madre cambia: tenerlo vorrebbe dire riscriverlo per
nessuno. Si **ritira**: `DROP`, `manual/` cancellato, il grant di `90_end/20260829-34`
(`runOnChange`) passa alla madre, i due pgTAP che la usavano (`test-soggetti-titoli-iva` 18-22,
`test-soggetti-titoli-iva-due-emittenti`) passano alla madre. Con lei va la forma storica «riga
`NULL`»: un movimento di fattura nomina sempre la sua riga.

### 13.6 Richieste al BE (un giro solo, sostituisce il §12.5 «Lato BE dopo il fix»)

| # | Cosa | Dove |
| --- | --- | --- |
| **R-BE-C1** | Il repository del risolutore impara il parametro nuovo **in coda** (`p_consumo`, dopo `p_emittente_fiscale_id`; i tre paesi in mezzo restano NULL). Le chiamate di oggi non cambiano | `iva_resolver_repository.py`, `iva_resolver_service.py` |
| **R-BE-C2** | Il giro risolve ogni gruppo (kit per `kit_key`, giudicato sul **padre**, D-5.1; riga sciolta sul suo articolo) con `p_consumo = true`. Nessun titolo → niente da fare; titolo senza tetto → tutto il gruppo al titolo, senza chiamare la madre; titolo con tetto → il gruppo va nel **secchio di quel titolo** | `plafond_fattura_service.py` |
| **R-BE-C3** | Una chiamata alla madre **per titolo**, con tutte le righe del suo secchio, **firma invariata**: `(titolo, fattura, righe[], imponibili[], data, tx)`. Gli imponibili sono quelli delle righe lette (anche negativi e zero): la madre li confronta con la riga e si ferma se divergono. L'ordine non conta: lo decide la madre | `pipeline_repository.consuma_plafond_titolo_righe` |
| **R-BE-C4** | Per gruppo, dalla frazione restituita: `1` → tutte le righe col trattamento del titolo; `0` → tutte col trattamento **ordinario**, scritto esplicitamente (la riga può essere nata col titolo dall'anteprima di generazione); altrimenti ogni riga si spezza: capofila = quota coperta col titolo, parte = resto con l'ordinario. Quantità coperta = `qta × quota_coperta / imponibile` se l'imponibile non è zero, `qta × f` se lo è; `kit_qta × f` come oggi | `_consuma_gruppo`, `_spezza` |
| **R-BE-C5** | Si ritirano: il filtro `consumanti` e il ramo provvisorio `coperta is None`, il guard «prezzo effettivo > 0» (una riga negativa ha prezzo negativo o quantità negativa, e la formula del C4 regge entrambi), `_parte_ordinaria` con la sua seconda chiamata al risolutore (l'ordinario arriva sempre come seconda riga), l'ordinamento dei gruppi (lo fa la madre) | idem |
| **R-BE-C6** | I commenti che nominano `fn_consuma_plafond_titolo_iva` (ritirata) | `titoli_iva_repository.py`, `titoli_iva_service.py` |
| **R-BE-C7** | Test: lo sconto −100 su merce 1000 e plafond 500 (600 + −100 al titolo, 400 all'ordinaria); il kit con componente negativo; il gruppo a netto zero (frazione 1); la riga negativa senza positivi (ordinaria); i test 21 e 25 sulla risposta della madre | test del servizio |

### 13.7 Lato DB — cosa si scrive

| # | Fase | Cosa |
| --- | --- | --- |
| C-1 | `00_schema/anagrafiche` | `chk_stiva_movimenti_segno`: `FATTURA <> 0` (§13.3) |
| C-2 | `20_code/vendite` | `fn_resolve_iva_riga_it`: `p_consumo` in coda (§13.4) |
| C-3 | `20_code/vendite` | `fn_resolve_iva_riga` (guscio): idem |
| C-4 | `20_code/anagrafiche` | `DROP` di `fn_consuma_plafond_titolo_iva` (§13.5) |
| C-5 | `20_code/anagrafiche` | `fn_consuma_plafond_titolo_iva_righe` sul netto (§13.2), firma invariata |
| C-6 | `90_end` | `20260829-34` (grant, `runOnChange`): EXECUTE dalla forma ritirata alla madre |

pgTAP: la madre riscritta sui casi del §13.2; i due dei titoli IVA portati sulla madre; i due del
risolutore sulla firma nuova. Doc: `manual/` della madre, del registro e del risolutore; guida
`iva-risolutore-di-riga.md`; `manual/` della forma ritirata cancellato.

### 13.8 Lato DB — scritto il 2026-10-04 (✅ applicato da Tid lo stesso giorno, pgTAP verdi)

> ✅ **Apply e corsa pgTAP di Tid, 2026-10-04: verdi, nessuna regressione.** La prima corsa aveva
> dato tre file rossi (la scala delle quote, §14.3 «Regressione»): il `-06` corretto è stato
> rieseguito su dbdev con il giro `runOnChange: true` → migrate → `false` (il changeSet non era
> ancora committato né pushato; `runOnChange` è di nuovo `false` nel file, come vuole il
> guardrail). ⚠️ Lezione: il `-06` era già applicato quando l'ho riscritto — prima di ritoccare un
> changeSet del giorno si legge il `databasechangelog`.

| # | File | Cosa |
| --- | --- | --- |
| C-1 | `00_schema/anagrafiche/20261004-02-alter-chk-stiva-movimenti-segno-fattura-col-segno` | `FATTURA <> 0`; `COMMENT` della tabella aggiornato (nominava la forma ritirata) |
| C-2 | `20_code/vendite/20261004-03-update-fn-resolve-iva-riga-it-domanda-di-consumo` | `DROP` + `CREATE`: `p_consumo` in coda, il resto invariato. Corpo dal vivo (`20261001-07`) con tre inserimenti mirati |
| C-3 | `20_code/vendite/20261004-04-update-fn-resolve-iva-riga-guscio-domanda-di-consumo` | idem sul guscio (vivo = `20260829-50`) |
| C-4 | `20_code/anagrafiche/20261004-05-drop-fn-consuma-plafond-titolo-iva` | ritiro della forma a una riga; il rollback la ricrea |
| C-5 | `20_code/anagrafiche/20261004-06-update-fn-consuma-plafond-titolo-iva-righe-sul-netto` | `CREATE OR REPLACE` della madre sul netto, **firma e `RETURNS TABLE` del `-07`** |
| C-6 | `90_end/20260829-34-grant-titoli-iva-app` (`runOnChange` + `ANY`) | EXECUTE dalla forma ritirata alla madre (firma del `-07`); intestazione aggiornata |

Ogni changeSet ha una `preCondition` `HALT` sulla firma che trova (`to_regprocedure`) e il
rollback col corpo di prima.

**pgTAP**

* `anagrafiche/test-consuma-plafond-titolo-iva-righe-v1` **riscritto, 21 test** (il 21: un
  imponibile diverso da quello della riga è rifiutato): i casi di prima
  (kit 0,4, centesimo, copertura piena, capienza zero, senza tetto, idempotenza) più lo sconto
  (600 / −100, movimenti col segno, utilizzato 500), il kit con componente negativo (+50 / −15,
  frazione 0,5), il kit a netto zero, la riga negativa sola, l'ordine di stampa, cinque guard
  e la forma ritirata. Le righe si passano in ordine **inverso**: l'ordine lo decide la madre;
* `anagrafiche/test-soggetti-titoli-iva` (18-22) e `test-soggetti-titoli-iva-due-emittenti`:
  portati sulla madre con righe vere (300, 1000, 5000; 400, 1000), stesse asserzioni;
* `vendite/test-fn-resolve-iva-riga`: i 15 di prima **invariati**; nuovi 16-18 (consumo = due
  righe in ordine con `quota` NULL; a residuo zero il consumo vede ancora il titolo, l'anteprima
  no; consumo con importo rifiutato). Lo smontaggio non cancella più i titoli (il 17 scrive una
  forzatura, e il registro è append-only);
* `vendite/test-esigibilita-iva-per-cassa-v1`: **invariato** (la firma esistente non cambia);
* `vendite/test-cleanup-fattura-copertura-figlie-v1`: solo testo, vedi sotto.

**Come è stato provato.** ⚠️ `zeroerp_ci` non era raggiungibile da questa sessione (le
credenziali non sono leggibili), quindi:

* cluster PostgreSQL 18 **usa-e-getta** con uno schema minimo (titoli, registro col CHECK nuovo e
  la UNIQUE, accumulatore che rifiuta il conto sotto zero, righe di fattura con `kit_key`,
  capofila e rettifica): **SQL estratto dai cinque YAML**, avanti e rollback in transazione,
  puliti; dopo l'avanti una sola firma per funzione;
* 23 casi della madre su quello schema (firma invariata, imponibili compresi): **23 verdi**
  (seconda prova, dopo la correzione delle firme);
* i due corpi del risolutore compilano (con stub dei tipi); cancelli statici tutti verdi
  (letterali, `runOnChange`, preCondition, DDL su trigger, grant batch, preambolo pgTAP, fuso).

⚠️ **Non provato prima dell'apply**: il DB vero (trigger delle righe, RLS come app, fixture
vere), `plpgsql_check` e i presidi trasversali (`test-riferimenti-morti`,
`test-catalogo-messaggi-errore-completo`), i cinque pgTAP toccati. Restano alla corsa di Tid.

**Altri ritocchi dello stesso giro**

* `codici_errore.csv` e `messaggi_errore.csv`: le note di `E_TITOLO_IVA_CONSUMO_NON_INVOCABILE` e
  `E_TITOLO_IVA_CONSUMO_FUORI_VALIDITA` nominavano la forma ritirata; la prima ora elenca anche i
  guard di gruppo. ⚠️ Svegliano i due mirror al migrate;
* `manual/`: madre riscritta; registro (`FATTURA ±`), accumulatore, titoli, risolutore e guscio
  aggiornati; `fn_consuma_plafond_titolo_iva.md` cancellato. Guida `iva-risolutore-di-riga.md`:
  §4 riscritto (le due domande, il netto), `quota` tolta dal §6.

**Da sapere (debiti trovati, non aperti da questo giro)**

* ✅ ~~`test-cleanup-fattura-copertura-figlie-v1` classifica `soggetti_titoli_iva_movimenti` come
  `SCOPERTA_NOTA` con il presupposto «nessuno scrittore», scaduto~~ → **deciso e fatto nel §14**
  (strada A);
* R-DB-B11 (gli apici raddoppiati in `codici_errore.csv`): corretti a mano da Tid il 2026-10-04;
  ⚠️ resta la riga di `E_UTENTE_TECNICO_NON_TROVATO` (`E''`, `c''e''`).

### 13.9 Richieste al BE, oltre al §13.6

| # | Cosa |
| --- | --- |
| R-BE-C8 | Rigenerare `error_policies_generated.py` (e il ripiego dei messaggi, se lo legge) dopo il migrate: cambiano le note di due codici |
| — | ⚠️ **Fra l'apply e il giro C del BE**: le firme sono invariate e quasi tutto funziona. Si ferma **un caso solo**: un kit con un componente a zero o negativo. Il ramo provvisorio del BE (§12.2) lo lascia fuori dalla chiamata, e la madre nuova vuole il kit **intero** (guard «kit incompleto», errore tecnico). Le righe sciolte negative il BE di oggi non le passa: restano all'ordinaria come oggi |
| R-BE-C9 | `docs/it/backend/anagrafiche/manual/api_titoli_iva_soggetto.md` riga 206: nomina `fn_consuma_plafond_titolo_iva`, ritirata |

## 14. Strada A — una fattura che ha consumato plafond non si disfa più (2026-10-04)

> **Decisione di Tid, 2026-10-04**: strada A (la B — tornare indietro restituendo il plafond —
> non regge: anche uno storno nomina la fattura, quindi la cancellazione resterebbe bloccata, a
> meno di cancellare righe dal registro, cioè fatti contabili). Chiude la decisione I5 rimasta
> aperta dal cantiere IVA.

### 14.1 Il difetto

Il plafond si consuma all'emissione, nel task `consuma_plafond_lotto`, **prima** di
`numera_fatture`. Se fra i due qualcosa si ferma, la fattura ha movimenti nel registro e nessun
numero. Le tre porte di reset (riporta a draft, annulla lotto, elimina fattura) rifiutano solo i
documenti **numerati**: la lasciano passare, e `fn_cleanup_fatture_by_ids` esplode con un 23503
grezzo sulle FK NO ACTION del registro (append-only).

### 14.2 La regola

Il consumo del plafond è un **punto di non ritorno**, come il numero. Il lotto va **avanti**:
DEFINITIVA riprende fattura per fattura, e il consumo è idempotente (§13.2 punto 9).

### 14.3 Lato DB — scritto il 2026-10-04 (✅ applicato da Tid lo stesso giorno, pgTAP verdi)

| # | File | Cosa |
| --- | --- | --- |
| A-1 | `20_code/script/20261004-07-create-fn-check-fatture-con-plafond-consumato` | il building block, sullo stampo di `fn_check_fatture_con_rettifiche`: `[]` o `{E_FATTURE_PLAFOND_CONSUMATO, PLAFOND_CONSUMATO, reason_key, dettaglio = quante fatture}`. Conta qualunque movimento che nomini la fattura |
| A-2 | `20_code/script/20261004-08-update-fn-check-fattura-eliminabile-da-lotto-plafond-consumato` | motivo 6 |
| A-3 | `20_code/script/20261004-09-update-fn-check-lotto-riportabile-a-draft-plafond-consumato` | motivo 5 |
| A-4 | `20_code/script/20261004-10-update-fn-check-lotto-annullabile-plafond-consumato` | motivo 5 |
| A-5 | `20_code/vendite/20261004-11-update-fn-cleanup-fatture-by-ids-guard-plafond` | secondo guard fail-loud, accanto a quello delle rettifiche |
| A-6 | `codici_errore.csv`, `messaggi_errore.csv` | `E_FATTURE_PLAFOND_CONSUMATO`, `CONFLITTO_STATO`, messaggio 1191: «Non si puo' disfare: %s fattura/e ha/hanno gia' consumato il plafond di una dichiarazione d'intento.» |

Firme invariate dappertutto (`CREATE OR REPLACE`); il motivo nuovo va **in coda** all'elenco di
ogni check, quindi i motivi di prima restano primi. Corpi dal vivo (doc auto-gen), con un solo
inserimento ciascuno.

**pgTAP**

* **nuovo** `vendite/test-reset-fattura-plafond-consumato-v1` (11 test): la check (vuoto, senza
  movimenti, con un movimento → 1 fattura su 2), le tre porte, la madre «elimina fattura» e la
  pulizia che sollevano il codice invece del 23503, la fattura di controllo che si elimina
  ancora, il codice a catalogo. Tutto costruito: cliente, due fatture DRAFT, un lotto DRAFT, un
  titolo, un movimento;
* `vendite/test-cleanup-fattura-copertura-figlie-v1`: il registro passa da `SCOPERTA_NOTA` a
  `BLOCCO_VOLUTO` nei due inventari, esce dal test 5, e il test 9 pretende anche il guard nuovo.

⚠️ **Correzione del 2026-10-04 (Tid)**: le firme di `-03`, `-04`, `-08`, `-09`, `-10`, `-11` (avanti
e rollback) e i rollback di `-05` e `-06` erano state prese dalla doc auto-gen, che scioglie i
`%TYPE`: riprese dall'ultimo YAML che le ancorava (`20260829-49`, `-50`, `20260909-52/-53/-54`,
`20260912-34`, `20261003-07`, `-08`). Nella madre gli scalari che portano importi di riga sono ora
ancorati a `fatture_righe.imponibile_riga` (non al registro, `numeric(15,2)`, che
arrotonderebbe a metà calcolo). Riprovato: i dieci changeSet avanti, rollback e avanti puliti, le
identità delle funzioni invariate, i 23 casi della madre verdi.

⛔ **Regressione trovata dalla corsa di Tid (2026-10-04) e corretta lo stesso giorno**: tre file
rossi (`test-consuma-plafond-titolo-iva-righe-v1` 5 e 7, `test-soggetti-titoli-iva` 19-22,
`test-soggetti-titoli-iva-due-emittenti` 5), una causa sola. `fatture_righe.imponibile_riga` è
`numeric(18,6)` (la doc auto-gen **non mostra la scala**) e il registro è `numeric(15,2)`. La madre
del `-07` calcolava al centesimo **per caso**: la quota passava per una variabile ancorata al
registro, che arrotondava. La prima stesura del `-06` calcolava a 6 decimali: quote come
`3.333333`, e l'`INSERT` nel registro arrotondava in silenzio — una frazione di centesimo diventava
uno zero rifiutato da `chk_stiva_movimenti_segno`, e il movimento smetteva di essere la quota.
**Correzione, sul modello**: la quota diventa un movimento, quindi si calcola alla scala del
registro, **dichiarata**: la madre legge la scala della colonna dal catalogo e calcola su
`trunc(imponibile, scala)` (verso lo zero: una quota non supera mai il suo imponibile; le frazioni
di centesimo restano nella quota ordinaria). Gli scalari del calcolo tornano ancorati al registro.
L'imponibile restituito è quello dichiarato (`p_imponibili`, uguale alla riga per guard). Caso
nuovo nel pgTAP (22): un articolo che arrotonda a 6 decimali, tre righe da 3,333333/3,333333/
3,333334 su plafond 5 → movimenti 1,67 + 1,67 + 1,66. ⚠️ Il mio schema di prova non tipizzava le
colonne come il DB vero: per questo non l'aveva visto. Riprovato con `numeric(18,6)` e
`numeric(15,2)`.

**Come è stato provato**: cluster usa-e-getta, SQL estratto dagli YAML. I quattro changeSet
`script` avanti, rollback e di nuovo avanti puliti; con un movimento le tre porte rispondono col
motivo e la fattura senza movimenti no. Il `-11` (pulizia) compila, avanti e rollback. Cancelli
statici verdi. ⚠️ Non provati prima dell'apply: il DB vero, le fixture del pgTAP nuovo (lotto
costruito a mano: se un trigger dei lotti pretende altro, il test lo dirà), i presidi
trasversali (`test-riferimenti-morti`, `test-catalogo-messaggi-errore-completo`).

### 14.4 Richieste a BE/FE

| # | Cosa |
| --- | --- |
| R-FE-A1 | Chiave i18n `vendite.lotti.azione_reason.plafond_consumato` (it, en): il motivo spento dei tre pulsanti di reset. Testo proposto: «Il lotto contiene fatture che hanno già consumato il plafond di una dichiarazione d'intento: non si disfa, va portato avanti.» |
| R-BE-A1 | Rigenerare `error_policies_generated.py` (codice nuovo, insieme a R-BE-C8) |

## 15. Lato BE/FE, quarto giro — decisione C e strada A (2026-10-04)

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-10-04. **A chi:** Tid (commit), team DB
> (§15.4).
> **Decisioni di Tid nella sessione:** chiave di motivo per la fattura singola → **(A)**, una sua,
> chiesta al DB; ramo di proiezione del risolutore → **se orfano si ritira** (lo è, §15.3).
> **Stato:** scritto, **non committato**. Test: `apps.vendite`, `apps.anagrafiche`, `apps.core`
> 4280 verdi (116 skip); sul DB provvisto (`ZEROERP_TEST_DB_E2E=1`) `apps.vendite.tests.db` 144
> verdi e i due presidi dei codici errore verdi; `check_i18n_keys` pulito.

### 15.1 Le richieste

| # | Stato | Dove |
| --- | --- | --- |
| R-BE-C1 | ✅ `p_consumo` passato **per nome** in coda (i tre parametri del dispatch restano al loro default); `p_imponibile` sempre `NULL` (§15.3) | `iva_resolver_repository.py` |
| R-BE-C2 | ✅ ogni gruppo (kit sul padre, riga sciolta sul suo articolo) si risolve con `consumo=True`: nessun titolo → niente; titolo senza tetto → tutte le righe al titolo, la madre non si chiama; titolo a tetto → secchio del titolo | `plafond_fattura_service._consuma_fattura`, `_risolvi_gruppo` |
| R-BE-C3 | ✅ una chiamata alla madre **per titolo**, con tutte le righe del secchio (negative e a zero comprese), firma invariata | `_consuma_titolo` |
| R-BE-C4 | ✅ per gruppo dalla frazione: 1 → titolo, 0 → ordinario **scritto**, altrimenti spezzatura. ⚠️ Quantità coperta con una formula diversa da quella del §13.6, vedi §15.2 | `_consuma_titolo`, `_spezza` |
| R-BE-C5 | ✅ ritirati: filtro `consumanti`, ramo `coperta is None`, guard «prezzo effettivo > 0», `_parte_ordinaria` con la seconda chiamata al risolutore, l'ordine dei gruppi come requisito (il raggruppamento resta: serve a chiedere il titolo una volta per kit) | `plafond_fattura_service.py` |
| R-BE-C6 | ✅ i due commenti (e «dentro la transizione a DEFINITIVA» → «all'emissione del lotto», §14.1) | `titoli_iva_repository.py`, `titoli_iva_service.py` |
| R-BE-C7 | ✅ 32 casi, fra cui i quattro del brief in `PlafondNettoTests` (sconto 600/−100, kit +50/−15, kit a netto zero, negativo solo) e i nuovi: domanda di consumo, frazione 0 scrive l'ordinario, titolo senza tetto, una chiamata per titolo, due titoli due chiamate, frazione fuori da [0, 1], capofila che ricalcola la quota con imponibile arrotondato | `test_plafond_fattura_service.py` |
| R-BE-C8, R-BE-A1 | ✅ policy rigenerata dal catalogo e ripiego di `E_FATTURE_PLAFOND_CONSUMATO` (già nel commit `609df1f4a`) | `error_policies_generated.py`, `error_messages_fallback.py` |
| R-BE-C9 | ✅ | `api_titoli_iva_soggetto.md` |
| R-FE-A1 | ✅ `vendite.lotti.azione_reason.plafond_consumato` (già nel commit `609df1f4a`) e, per la scelta A, `fattura_plafond_consumato` (it, en): la usa il DB quando fa la R-DB-A2 | `it.json`, `en.json` |
| — | `IvaResolverService.risolvi`: `imponibile` → `consumo`; il guard di forma diventa «una parte, oppure nel consumo due: la prima col titolo, la seconda senza». Test del BB aggiornati. Catalogo BB aggiornato | `iva_resolver_service.py`, `catalogo-building-block-backend.md` |

### 15.2 Scelta fatta scrivendo — la quantità coperta (R-BE-C4)

Il §13.6 dice `qta × quota_coperta / imponibile`. **Non l'ho usata**: `imponibile_riga` è
**arrotondato** (`trgfn_fatture_righe_importo`, decimali e metodo dell'articolo), quindi quel
rapporto non è l'inverso della formula del DB. Esempio: 3 × 3,333 = 9,999 → `imponibile_riga`
10,00; quota 5,00 → `qta` 1,5 → la capofila ricalcola 4,9995, cioè un centesimo di distanza dal
suo movimento a seconda del metodo. Due conseguenze: il documento e il registro dicono due numeri
diversi, e al rilancio la madre rilegge il registro, vede una frazione diversa da 1 e spezza di
nuovo.

Resta il metodo già scelto da Tid, **esteso ai segni**: `qta = quota / prezzo_effettivo` (inverso
esatto: la capofila ricalcola la quota, che è il movimento). Su una riga negativa quota e prezzo
(o quota e quantità) hanno segni che si compensano, quindi regge senza guard. Solo a **prezzo
effettivo zero** (omaggio, sconto 100%) la quota è zero e non c'è niente da invertire: lì
`qta × f`, come dice il §13.6. Il guard «prezzo effettivo > 0» è ritirato come chiesto. Presidio:
test 15.

### 15.3 La proiezione del risolutore è orfana — ritirata dal BE

Verificato sui chiamanti: dopo R-BE-C2 nessuno passa più un importo. Il giro del plafond usa il
consumo; preventivi, ordini, DDT, righe di fattura e l'endpoint di anteprima usano
`risolvi_anteprima`; nessuna funzione DB chiama `fn_resolve_iva_riga` con un importo. Dal lato
BE: il parametro `imponibile` esce da `IvaResolverService.risolvi` e dal repository, e la query
passa `NULL::numeric`. Il ramo nel DB lo ritira il team DB (R-DB-C10).

### 15.4 Al team DB

| # | Cosa | Perché |
| --- | --- | --- |
| **R-DB-C10** | `fn_resolve_iva_riga_it` (e il guscio, se ha logica sua sul ramo): togliere il ramo di **proiezione** (`p_imponibile` valorizzato con `p_consumo = false`). Il parametro **resta** (la firma non si riordina, §13.4); consiglio di **rifiutare** un `p_imponibile` valorizzato con lo stesso codice del guard «consumo con importo», così un chiamante futuro non riceve in silenzio l'anteprima credendo di aver chiesto una proiezione. pgTAP: i casi di proiezione del `test-fn-resolve-iva-riga` diventano casi di rifiuto | Decisione di Tid (2026-10-04): orfano → si ritira. Nessun chiamante dal BE (§15.3) |
| **R-DB-A2** | `script.fn_check_fattura_eliminabile_da_lotto`, motivo 6: `reason_key` → `vendite.lotti.azione_reason.fattura_plafond_consumato` (la chiave esiste già in it ed en) | Scelta A di Tid: le due porte del lotto dicono «il lotto contiene fatture…», l'eliminazione di una fattura sola parla di **quella** fattura. È la stessa coppia che il catalogo ha già per i numeri (`fattura_numerata` / `fatture_numerate`) e lo stato (`fattura_non_pre_fiscale` / `fatture_non_pre_fiscali`). Fino ad allora il pulsante della fattura mostra il testo del lotto |

### 15.5 Cosa la prova NON copre

* I test del giro mockano repository e madre: la regola del netto la prova il pgTAP della madre,
  qui si prova che il BE ne applica le risposte. Il **binding** della query del risolutore è
  provato sul DB vero (`EXPLAIN` e una chiamata reale con `consumo` falso e vero), ma su un
  articolo **senza** titolo: ⚠️ la risposta a due parti (titolo a tetto) e la madre con un secchio
  misto (positivi e negativi) sul DB vero le prova solo il primo lotto con una dichiarazione
  d'intento su dbdev.
* Le righe senza articolo restano fuori dal giro (`list_righe_per_plafond`), come prima: senza
  articolo il risolutore non ha niente da giudicare, quindi uno sconto **senza articolo** non
  restituisce plafond. È coerente col modello di oggi (il titolo si giudica sull'articolo); lo
  segnalo perché con la decisione C uno sconto in fattura diventa un caso che conta.


### 15.6 Revisione critica del codice (2026-10-04)

* **Ripieghi silenziosi tolti.** `prezzo_unitario` e `qta` sono NOT NULL e la madre dà sempre la
  quota: la prima stesura trasformava un NULL in zero (`or Decimal(0)`), cioè una proiezione rotta
  in una riga divisa con la frazione invece che con la quota. Ora il giro si ferma
  (`E_PIPELINE_VALIDATION`), con un messaggio che distingue le righe mancanti dalle quote assenti.
* **Articolo del kit scelto in modo esplicito.** Il ripiego «padre, altrimenti il componente»
  avrebbe giudicato il kit sul primo componente se il padre fosse mancato: violazione muta di
  D-5.1. Il padre lo garantisce `chk_fatture_righe_kit_coerente`; un `None` lo ferma il guard del
  risolutore.
* **Secchi in ordine di titolo.** Ogni chiamata tiene il lock del suo titolo fino a fine
  transazione: un ordine fisso evita lock presi in versi opposti nello stesso giro. Non cambia il
  risultato (capienze indipendenti). ⚠️ Fra **lotti** concorrenti resta possibile un deadlock fra
  due titoli: PostgreSQL lo rileva, il task fallisce e il rilancio è idempotente.
* Tre test nuovi (33-35). Suite `vendite`, `anagrafiche`, `core`: 4283 verdi (116 skip).

## 16. Lato DB, quinto giro — le richieste del §15.4 (2026-10-04)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-10-04. **A chi:** Tid (apply, pgTAP), poi BE
> (§16.4, una cosa facoltativa).
> **Stato:** scritto, ⏳ **da applicare** (Tid). Non committato.

### 16.1 R-DB-C10 — la proiezione del risolutore si ritira

`20_code/vendite/20261004-15-update-fn-resolve-iva-riga-it-ritiro-proiezione`, solo su
`vendite.fn_resolve_iva_riga_it`. Il guscio non si tocca: inoltra `p_imponibile` senza logica sua.

* si toglie il **ramo**, non il parametro: firma e `RETURNS TABLE` invariati (quelli del `-03`, coi
  `%TYPE`), `CREATE OR REPLACE`;
* `p_imponibile` valorizzato **solleva** `E_IVA_RESOLVE_NON_INVOCABILE`, con qualunque `p_consumo`
  (la forma consigliata dal BE). Un solo guard, che assorbe i due di prima (consumo con importo,
  importo negativo). Il perché: un importo accettato e ignorato farebbe credere al chiamante di aver
  avuto una spezzatura;
* `quota` resta ed esce sempre `NULL`; anteprima e consumo invariati;
* corpo dal vivo (doc auto-gen = `-03`, verificato uguale), sostituzioni mirate contate; rollback =
  il corpo del `-03`.

⚠️ **Il messaggio del codice diceva il falso** per il caso nuovo (e già per «consumo con importo»):
«Risoluzione IVA invocata **senza** imponibile», quando l'importo c'è. `messaggi_errore.csv`
(1023) ora dice «invocata con un parametro assente o non valido: %s.», e la causa nomina l'importo.
Un `%s` come prima. ⚠️ Sveglia il mirror al migrate.

pgTAP:

* `vendite/test-fn-resolve-iva-riga.sql`: **12** diventa il rifiuto di un importo, costruito sul
  titolo a tetto incapiente, cioè dove la proiezione avrebbe risposto qualcosa di plausibile;
  **13** l'anteprima sullo stesso titolo (una riga, `TITOLO`, quota `NULL`). Gli altri casi che
  passavano `100.00` senza provare la proiezione (2-6, 8-11, 14, 15) passano `NULL`.
  ⛔ L'11 era il caso pericoloso: con l'importo il guard nuovo avrebbe sollevato un `P0001` e il
  `throws_ok` sui titoli ambigui sarebbe rimasto **verde per il motivo sbagliato**. Piano 18
  invariato;
* `vendite/test-esigibilita-iva-per-cassa-v1.sql` test 19: `100.00` → `NULL` (asserisce la coppia
  esigibilità/split, non la quota).

### 16.2 R-DB-A2 — eliminare una fattura: la frase parla di quella fattura

`20_code/script/20261004-16-update-fn-check-fattura-eliminabile-da-lotto-motivo-plafond-singolare`.
Il motivo 6 resta delegato alla sede unica (`fn_check_fatture_con_plafond_consumato`); sul suo
risultato si sostituisce solo la `reason_key` con
`vendite.lotti.azione_reason.fattura_plafond_consumato` (già in `it.json`/`en.json`). Codice,
`reason` e dettaglio restano della sede; le due porte del lotto non cambiano.

⚠️ Scritta con `motivo || jsonb_build_object('reason_key', '…')` e non con `jsonb_set`: è la forma
che `scripts/check_i18n_keys.py` (controllo 4) riconosce, quindi la chiave resta presidiata contro
i locales dopo la rigenerazione della doc.

pgTAP: `vendite/test-reset-fattura-plafond-consumato-v1.sql`, test **5-7** pretendono anche la
`reason_key`: quella della fattura sulla porta singola, quella del lotto sulle altre due. Prima
guardavano il solo codice, e sarebbero rimasti verdi con la frase sbagliata a video. Piano 11
invariato.

### 16.3 Come è stato provato, e cosa la prova NON copre

* **Cluster PostgreSQL 18 usa-e-getta**, stub con la forma della doc auto-gen, **SQL estratto
  dagli YAML**: stato di prima (`-03`, `-04`, `-07`, `-08`), precondizioni (1 e 2), avanti `-15`
  `-16`, rollback, di nuovo avanti — tutto pulito, una firma per funzione.
* Casi: anteprima senza titolo (una riga, `ARTICOLO`); anteprima su titolo a tetto (una riga,
  `TITOLO`); consumo (due righe, titolo poi ordinario); importo 250 sul titolo a tetto **accettato
  prima, rifiutato dopo** e di nuovo accettato dopo il rollback; importo negativo e consumo con
  importo rifiutati prima e dopo. Check: fattura con movimento → `fattura_plafond_consumato`
  (prima: `plafond_consumato`), fattura senza → `[]`, sede unica invariata al plurale.
* Cancelli statici verdi: letterali, `runOnChange`, preCondition, DDL su trigger, grant batch,
  fuso, preambolo pgTAP (debito `throws_ok` 115, soglia 115: il `throws_like` nuovo non lo alza).
* ⚠️ **Non copre**: il DB vero (RLS come app, fixture vere), `plpgsql_check`, i presidi trasversali,
  i pgTAP toccati, il mirror di `messaggi_errore.csv`. Restano alla corsa di Tid.

### 16.4 Al BE (facoltativo, nessun blocco)

| # | Cosa |
| --- | --- |
| R-BE-C10 | `error_messages_fallback.py` 507, `E_IVA_RESOLVE_NON_INVOCABILE`: il ripiego dice «invocata senza i dati necessari…». Non è falso come lo era il catalogo, ma se il ripiego si allinea al catalogo va riletto dopo il migrate. Nessuna policy cambia (classe e codice invariati) |
