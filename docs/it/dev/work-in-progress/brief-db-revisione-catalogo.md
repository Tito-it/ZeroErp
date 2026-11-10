# Brief DB — Revisione dello schema `catalogo`: la documentazione, i difetti di codice, i doppioni

## ⏭️ Chi riparte — aggiornato al 2026-11-10 (giro 2 applicato e committato; giro BE del giro 2 fatto, da committare; Q19-Q21 decise → giro 2-bis, §14)

**Riparte: Tid**, col via al giro 2-bis (§14) o al giro 3 (§7), coi loro numeri, e il commit del giro BE (§13.7). Il **team BE** ha fatto le ricadute dei giri 1, 1-bis e 2 (§5, §11.6, §13.7); restano BE4 per il giro 3
(D19) e BE5-BE7, quando il giro corrispondente è applicato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione DB | Censimento in sola lettura dei 37 oggetti: doc, codice, metadati, doppioni, pgTAP | §1-§5 | — |
| 2 | ✅ Tid | Le decisioni Q1-Q14, tutte come da proposta (2026-11-08) | §6 | 1 |
| 3 | ✅ Tid | Il via al giro 0 (2026-11-08) | §7 | 1 |
| 4 | ✅ sessione DB | Giro 0: le 35 pagine `manual/` allo standard, il blocco comune delle note, la doc fuori schema | §9 | 3 |
| 4-bis | ✅ sessione DB, su richiesta di Tid | Commit del giro 0 (2026-11-08) | §9.5 | 4 |
| 5 | ✅ Tid | Via al giro 1, dal `20261110-62` (2026-11-09) | §10 | 2 |
| 5-bis | ✅ sessione DB | Giro 1 (la distinta): `20261110-62` … `-71`, due codici, pgTAP; provato sullo scratch | §10 | 5 |
| 5-ter | ✅ Tid | Apply del giro 1 su dbdev e scratch; pgTAP come app verdi (2026-11-09) | §10.6 | 5-bis |
| 5-quater | ✅ Tid | Commit del giro 1 (`eef662024d`, 2026-11-09) | §10.6 | 5-ter |
| 5-quinquies | ✅ sessione DB | Censimento del giro 1-bis in sola lettura: i lettori della distinta, il piano | §11 | 5-quater |
| 5-sexies | ✅ Tid | Q15-Q18 come da proposta; via al giro 1-bis dal `-85` (2026-11-09) | §11.4 | 5-quinquies |
| 5-septies | ✅ sessione DB | Giro 1-bis: nove changeSet, CSV dei codici, pgTAP, doc; provato sullo scratch | §11.7, §11.8 | 5-sexies |
| 5-octies | ✅ Tid | Apply del giro 1-bis su dbdev e scratch, pgTAP come app verdi (2026-11-09) | §11.9 | 5-septies |
| 5-nonies | ✅ sessione DB, su richiesta di Tid | Commit del giro 1-bis (2026-11-09) | §11.9 | 5-octies |
| 5-decies | ✅ Tid | Via al giro 2, dal `20261111-01` (2026-11-09) | §13 | 5-nonies |
| 5-undecies | ✅ sessione DB | Giro 2 (le unità): tredici changeSet, sei codici, pgTAP, doc; provato sullo scratch | §13 | 5-decies |
| 5-duodecies | ✅ Tid | La riga di prova corretta; apply del giro 2 su dbdev e scratch, pgTAP come app verdi (2026-11-09) | §13.6 | 5-undecies |
| 5-terdecies | ✅ sessione DB, su richiesta di Tid | Commit del giro 2 (2026-11-09) | §13.6 | 5-duodecies |
| 5-quaterdecies | **Tid** ⏭️ | Via al giro 3 coi suoi numeri; le scelte di §13.3 e §10.3 da guardare | §7, §13.3, §10.3 | 5-terdecies |
| 6 | sessione DB | Giri 3-5, ognuno col suo via, i suoi numeri e il suo apply | §7 | 5-quaterdecies |
| 7 | team BE ✅ (giri 1, 1-bis, 2) | BE8-BE15 fatte e committate (§5, §11.6); BE1-BE4 e BE16-BE18 fatte il 2026-11-09 (§13.7); le altre quando il giro corrispondente lo è | §5, §11.6, §13.5, §13.7 | — |
| 7-bis | **Tid** ⏭️ | Commit del giro BE del giro 2 | §13.7 | 7 |
| 7-ter | ✅ Tid | Le tre domande di §13.7.3: Q19 bloccato, Q20 per tutto il periodo, Q21 in questo brief (2026-11-10) | §6, §14 | 7 |
| 7-quater | **Tid** ⏭️ → sessione DB | Via al giro 2-bis coi suoi numeri; poi D24-D26, pgTAP, doc, apply | §14 | 7-ter |
| 7-quinquies | team BE | BE19-BE21, a giro 2-bis applicato | §14.4 | 7-quater |
| 8 | sessione DB | Pagine `manual/` riallineate a ogni difetto chiuso, insieme al COMMENT; brief in `work-done/` | §7, §8 | 6 |

**Decisioni aperte di Tid:** le scelte dentro il giro 2 (§13.3) e il giro 1 (§10.3), da guardare; le scelte di §14.1 (unità e date della
mappatura) e di §14.2 (il terzo lato), che la sessione DB proporrà. **Da committare:** il giro BE del giro 2 (§13.7, `dev/backend-tid`); i giri DB 1, 1-bis e 2 sono committati.
Prossimi numeri: li dà Tid.
⚠️ **Numerazione:** il giro 1 ha preso `20261110-62` … `-71`, il giro 1-bis `-85` … `-93` (dato da Tid). Messaggi
d'errore: il giro 1-bis non ne aggiunge; ne riscrive due righe.

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-08. **A chi:** Tid e team DB; §5 al team BE.
> **Origine:** richiesta di Tid del 2026-11-08: una revisione di `catalogo` sullo stile di
> [brief-db-revisione-dbops](brief-db-revisione-dbops.md). Si parte dalla documentazione da riportare allo
> standard, poi si guarda che cosa è obsoleto, che cosa non è fatto come descritto (e quindi forse non
> funziona), che cosa si può cancellare e dove la regola del 2 trova doppioni.
> **Metodo:** quattro revisori in sola lettura (articoli; distinta; unità di misura e note; trasversale)
> sui corpi di `pg_get_functiondef`, su `pg_trigger`/`pg_constraint`/`obj_description` di dbdev e sulle
> schede auto-generate. Chi scrive il brief ha ricontrollato sul corpo D1, D2, D3, D4 e D7 (✔︎).
> **Brief vicini verificati:**
> * [brief-db-articoli-obsoleto-dal](brief-db-articoli-obsoleto-dal.md): il suo **D-C** riscrive i COMMENT di quel
>   cantiere (`obsoleto_dal`, `fn_articoli_ammessi`, `trgfn_articoli_componenti_guard_componente`,
>   `vw_articoli_dettaglio.e_obsoleto`). Si sovrappone a M3: chi lo fa lo decide Tid (Q11).
> * [brief-db-revisione-dbops](brief-db-revisione-dbops.md): il suo **D28** (le `condition_expr` di
>   `lock_columns_conditional` ricopiano gli `EXISTS` del guard flags) tocca gli stessi predicati di D9. D28 resta
>   lì; il giro 1 di qui va fatto **dopo** o **con** D28, perché cambia la finestra del predicato che D28 estrae.
> * [brief-db-addebito-trasporto-ordine](brief-db-addebito-trasporto-ordine.md): tocca `trgfn_articoli_guard_onere_natura`,
>   `vw_articoli_dettaglio` (`causale_onere_id`, `e_onere`) e `fn_articolo_righe_vive_non_ammesse`. Qui non si
>   rifà niente di quel cantiere: si toccano solo i metadati (M3) e l'etichetta dei flag (R5).
> * `analisi-db-magazzino-carico-e-scarico` (analisi, non brief): tocca `requires_lotto`, quindi Q4.
> * Nessun brief aperto tratta il fattore delle unità di misura (D2, D3, D12-D15) né l'immutabilità della
>   distinta (D1, D9).

⚠️ Il DDL e il corpo di ogni oggetto si prendono dalla doc auto-generata (`docs/it/dbzero/<schema>/…`) o da
`pg_get_functiondef`, non dagli YAML. Prima di scrivere un changeSet si riverifica sulla scheda del giorno.

## 1. Il perimetro

Lo schema `catalogo`: 9 tabelle (`articoli`, `articoli_componenti`, `articoli_uom_operativa`, `unita_misura`,
`uom_tipi`, `unita_misura_conversioni`, `note` partizionata con `note_articoli` e `note_articoli_componenti`), 5
viste, 23 funzioni. Il database e la doc auto-generata coincidono: ogni oggetto ha la scheda e la pagina `manual/`.

Ci sono anche i difetti di altri schemi trovati leggendo i chiamanti. Il caso principale è
`script.trgfn_qta_from_operativa`, che è l'unico lettore operativo di `articoli_uom_operativa`.

Ogni difetto si regge sul modello. Dove compare un numero, è un fatto datato al 2026-11-08.

## 2. I difetti di codice

Forma compatta: **fatto** · **correzione** · **presidio**. Classi come nel brief `dbops`:

* **A**: contraddice un contratto deciso, oppure è sbagliato ogni volta che il ramo si percorre.
* **B**: un caso che il modello ammette (un NULL, una data futura, una riga chiusa) e che non è gestito.
* **C**: pulizia e metadati.

| Classe | Difetti |
| --- | --- |
| **A** | D1, D2, D3, D4, D5, D6, D7, D8 |
| **B** | D9, D10, D11, D12, D13, D14, D15, D16, D17, D18, D19, D20, D22 |
| **C** | D21, §2.4 (rami irraggiungibili), §3 (metadati), §2.6 (pgTAP deboli) |

### 2.1 Classe A

#### D1 ✔︎ — La distinta non è immutabile su `prodotto_id`

* **Fatto.** `trg_articoli_componenti_a10_block_modifica_struttura_upd_dlt` scatta `BEFORE DELETE OR UPDATE OF
  coeff_qta, componente_id, obbligatorio, esposizione_in_fattura, valido_dal, valido_al`. `prodotto_id` non è
  né nella lista né nel confronto del corpo. Il modello lo dichiara immutabile
  (`dev/manual/modello-componenti-bom.md:38`). Una riga di distinta passa quindi sotto un altro padre, e le righe
  `*_righe_componenti` che la puntano (cinque FK in vendite, più la temporale del listino) restano legate a un
  altro kit, in silenzio. Gli unici a scattare su `UPDATE OF prodotto_id` sono i guard di regola (composito,
  solo componente, componente), e non giudicano l'immutabilità. `valido_al` sta nella lista, ma il corpo non lo
  confronta: fa scattare il trigger per niente.
* **Correzione.** `prodotto_id` entra nella lista e nel confronto `IS DISTINCT FROM`; `valido_al` esce dalla lista,
  se Q1 non decide altrimenti.
* **Presidio.** In `catalogo/test-articoli-componenti-immutabilita.sql`: `SET prodotto_id = <altro composito>` →
  `E_BOM_MODIFICA_VIETATA`.

#### D2 ✔︎ — Il fattore di conversione ha due sedi, e quella che conta usa 1 quando non sa

* **Fatto.** `script.trgfn_qta_from_operativa`, montato sulle righe di vendita, cerca solo la mappatura
  dell'articolo in `articoli_uom_operativa`; poi fa `v_factor_map := COALESCE(v_factor_map, 1)`. Prendiamo una
  riga in un'unità operativa diversa dalla base, senza mappatura (o con la mappatura spenta, o fuori validità):
  la quantità base diventa `qta_operativa × 1`, senza errore. Le conversioni globali di
  `unita_misura_conversioni` non le legge mai. `catalogo.fn_get_uom_factor` ha la regola completa (mappatura,
  poi conversione diretta, poi inversa, altrimenti NULL), ma nel DB non la chiama nessuno: la usano solo due
  wrapper BE che a loro volta non hanno chiamanti. Sono due copie della stessa regola, già in disaccordo
  (regola del 2), e la copia che conta è quella sbagliata. Contraddice `manual/unita_misura_conversioni.md`:
  «fallback quando non esiste conversione articolo-specifica».
* **Correzione.** Il trigger prende il fattore da `catalogo.fn_get_uom_factor`. Con NULL solleva un codice
  registrato (`E_UOM_MISSING` esiste già; Q7). `fn_get_uom_base` resta il solo lettore di `articoli.uom_id`.
* **Presidio.** pgTAP su `vendite.ordini_righe`: articolo con base G, riga in KG senza mappatura. Con la
  conversione globale KG→G = 1000, la quantità vale 1000 × qta; senza conversione, la riga è rifiutata.

#### D3 ✔︎ — Le regole di input dell'unità operativa sono promesse senza esecutore

* **Fatto.** `trgfn_qta_from_operativa` legge `max_decimals` in `v_max_dec` e poi non lo usa. `rounding_mode` non
  lo legge nessuna funzione: il calcolo arrotonda sempre con `ROUND(…, 6)`. Il COMMENT di `require_lot` dice «se
  TRUE richiede lotto nei documenti», ma la colonna non ha lettori; la regola vera del lotto è
  `articoli.requires_lotto`. Sono due flag con lo stesso significato, e uno dei due è inerte. COMMENT e
  `manual/articoli_uom_operativa.md:24,30` dicono che le regole vengono applicate.
* **Correzione.** Q4: applicarle, con un codice per i decimali, oppure ritirare le colonne (e `require_lot` in
  ogni caso, a favore di `requires_lotto`).
* **Presidio.** Con `max_decimals = 0` e `qta_operativa = 2.5` la riga è rifiutata (se applicate); altrimenti
  il presidio è che le colonne non ci sono più.

#### D4 ✔︎ — Con un legame attivo, l'IVA di un kit e dei suoi componenti non si cambia più

* **Fatto.** `trgfn_articoli_guard_iva_bom_attiva` è `BEFORE UPDATE OF iva_id`, riga per riga e non
  differibile. Confronta `NEW.iva_id` con l'IVA **attuale** dell'articolo collegato. Se si aggiorna prima il
  padre, i figli hanno ancora la vecchia; se prima un figlio, il padre ha ancora la vecchia. Nemmeno un UPDATE
  unico passa: la prima riga elaborata vede le altre col valore vecchio. Il filtro è il solo `ac.attivo = TRUE`,
  senza `validita`, quindi contano anche i legami chiusi. Col modello «chiudi e inserisci» quei legami restano
  attivi, e `trgfn_prevent_deactivate_if_children` impedisce di spegnerli appena una riga di documento li cita.
  Contraddice `manual/articoli.md` («`iva_id` libera, l'aliquota cambia per legge»), e la procedura della pagina
  del guard («prima i partner, poi l'articolo») non si può eseguire.
* **Correzione.** L'invariante si controlla a fine transazione (constraint trigger `DEFERRABLE INITIALLY
  DEFERRED`), oppure con un verbo che cambia l'IVA del kit intero (Q6). La finestra diventa «legami da oggi in
  poi», come il check 3 del guard flags (D9).
* **Presidio.** In una transazione si cambia l'IVA di un kit e di tutti i componenti: passa. Un legame chiuso
  ieri non blocca. Cambiare solo il padre: rifiutato al COMMIT.

#### D5 — `trgfn_articoli_guard_listino_se_composito`: il rimedio suggerito non funziona, e la porta lo contraddice

* **Fatto.** L'errore suggerisce di «disattivare le righe listino prima di rendere composito». Però
  `fn_articolo_usato` conta `vendite.listini_righe` in qualunque stato, quindi dopo la disattivazione scatta
  `trgfn_articoli_guard_struttura_se_usato` (`E_ARTICOLO_USATO_STRUTTURA_IMMUTABILE`). Fuori dalla porta
  amministratore il guard è assorbito dal guard «usato»: scatta prima solo per l'ordine alfabetico dei nomi.
  Dentro la porta (`fn_articolo_correggi_struttura`) blocca anche le righe di una versione `CHIUSA`, mentre
  `fn_articolo_righe_vive_non_ammesse` le esclude per contratto («un documento chiuso non blocca»). È una terza
  copia della regola (R4), già divergente.
* **Correzione.** Si ritira il guard (Q5): la regola vive lato riga (`fn_check_articolo_riga_su_contesto`) e,
  per la porta, in `righe_vive`.
* **Presidio.** Correzione a composito di un articolo con righe solo in una versione chiusa → passa. Oggi nessun
  pgTAP prova il lato articolo.

#### D6 — I due guard di tipologia sollevano un errore tecnico e registrano il trigger al posto della funzione

* **Fatto.** `trgfn_uom_conversioni_guard_tipo` e `trgfn_unita_misura_guard_tipo_update` sollevano `E_GENERICO`
  (classe TECNICO, messaggio `%s`) con una frase libera. Un errore di dato arriva quindi all'operatore come
  errore tecnico. Inoltre passano `TG_NAME` come nome della funzione, così in `error_log` c'è il trigger e i
  consumatori cercati dal nome della funzione non lo trovano.
* **Correzione.** Due codici registrati (per esempio `E_UOM_CONVERSIONE_TIPO_DIVERSO`, `E_UOM_TIPO_IN_USO`), il
  nome qualificato della funzione, `EXISTS` al posto di `COUNT(*)`.
* **Presidio.** `throws_ok` sui codici nuovi. `trgfn_unita_misura_guard_tipo_update` oggi non ha nessun test.

#### D7 ✔︎ — Un articolo creato non attivo non si salva

* **Fatto.** `trgfn_articoli_seed_uom_base` scrive la riga base sempre con `attivo = TRUE`. Il constraint
  trigger generato `…_articoli_require_attivo_ins_upd` di `articoli_uom_operativa` pretende un padre attivo. Il
  modello ammette `INSERT articoli (attivo = false)`, e l'insert fallisce al COMMIT con
  `E_ATTIVO_PADRE_NON_ATTIVO`. È verificato sui corpi, non eseguito: va provato prima di scrivere il giro.
* **Correzione.** `attivo := NEW.attivo`.
* **Presidio.** pgTAP con `SET CONSTRAINTS ALL IMMEDIATE`: l'articolo non attivo nasce, con la sua riga base
  spenta.

#### D8 — Cambiare unità su una riga lascia il fattore della vecchia

* **Fatto.** Su un UPDATE che cambia `uom_operativa_id` senza toccare `factor_to_base`, il trigger usa
  `COALESCE(NEW.factor_to_base, …)`. `NEW.factor_to_base` ha ancora il fattore della unità precedente (da
  CARTONE ×6 a PZ, il fattore resta 6). Nessun lock impedisce il cambio di unità. Verificato sul corpo; da
  vedere se il BE azzera il fattore (§5, BE3).
* **Correzione.** Se l'unità cambia e il fattore non è stato toccato, il fattore si ricalcola.
* **Presidio.** UPDATE che cambia solo l'unità: la quantità segue il fattore nuovo.

### 2.2 Classe B

#### D9 — «Distinta in vigore» ha più finestre, e i guard non ri-giudicano i ritorni in vigore

* **Fatto.** Le definizioni oggi sono quattro:
  * `fn_articolo_padre_di_distinta_in_vigore` e `…componente_di_distinta_in_vigore`: `attivo` e
    `validita @> fn_data_operativa()`;
  * `fn_articolo_primo_padre_da_oggi`: `validita && [oggi,∞)`;
  * il guard IVA: solo `attivo` (D4);
  * `script.fn_check_articolo_riga_su_contesto`: `COALESCE(ac.attivo, TRUE)`, senza validità.

  Ne nascono tre varchi:
  * **Padre con distinta solo futura.** Il check 1 di `trgfn_articoli_guard_flags_struttura_bom_attiva` guarda
    solo «in vigore oggi», quindi un padre con legami solo futuri passa `is_composito` (o `requires_serial`) a
    false. Il check 3, sul componente, include invece il futuro.
  * **Riattivazione o arrivo di `valido_dal`.** `guard_is_composito` e `guard_solo_componente` scattano solo su
    `INSERT OR UPDATE OF prodotto_id`, non su `attivo`/`valido_*`.
  * **Riapertura di un legame chiuso.** `guard_componente` scatta su `UPDATE OF componente_id, prodotto_id,
    attivo`, non su `valido_al`. Dopo che il componente è diventato composito o obsoleto, `SET valido_al = NULL`
    passa. Ne esce una distinta a due livelli, o con un componente obsoleto, o con un padre non composito.

  La distinta a un livello di `modello-componenti-bom.md` §9.2 regge solo finché questi varchi restano chiusi.
* **Correzione.** Una finestra sola, «da oggi in poi», per tutti i guard che proteggono la struttura (il BB di
  R2). I motivi sul padre vanno nella check `ARTICOLO` condivisa (R3), giudicata anche su `attivo`, `valido_dal`
  e `valido_al`. Con D28 del brief `dbops` (vedi testata).
* **Presidio.** Tre casi costruiti in `test-distinta-predicati-guard-e-form-v1`:
  * padre con sola distinta futura che smette di essere composito → rifiutato;
  * riattivazione di un legame con padre non composito → `E_ARTICOLO_NON_COMPOSITO`;
  * riapertura di un legame il cui componente è diventato composito → `E_BOM_COMPONENTE_COMPOSITO`.

#### D10 — `valido_al` si sposta in ogni direzione

* **Fatto.** Il trigger d'immutabilità ammette qualunque `valido_al ≥ valido_dal`: la chiusura retroattiva e la
  riapertura a NULL. La pagina del trigger dice «protegge la storia da correzioni retroattive», e il modello
  «garantisce ricostruzione storica». La capability della vista (`data_min_chiusura = valido_dal`) offre la
  chiusura nel passato.
* **Correzione.** Q1. Se la regola è «si chiude, non si riapre né si retrodata»: vietati `data → NULL` e
  `valido_al < fn_data_operativa()` sui legami già in vigore, con `data_min_chiusura` allineata.

#### D11 — Un articolo può essere composito e solo componente insieme

* **Fatto.** Nessun CHECK esclude `is_composito AND is_solo_componente`. Un articolo così è inerte: non fa da
  padre (guard solo componente) e non fa da componente (un livello). Il check 2 del guard flags protegge il lato
  componente, ma il lato padre, quello della regola di `guard_solo_componente`, non lo protegge nessun guard
  sull'articolo.
* **Correzione.** Q2: un CHECK `NOT (is_composito AND is_solo_componente)`. Con il CHECK, `guard_solo_componente`
  diventa superfluo e si ritira (R3).

#### D12 — La riga base di `articoli_uom_operativa` non è protetta

* **Fatto.** Nessun CHECK impone `NOT is_base OR factor_to_base = 1`; c'è solo l'indice unico parziale
  `uq_artuomop_one_base`. Nel BE la regola è parziale: `catalogo_service.py:844` controlla solo se il payload ha
  insieme `is_base` e il fattore. `uom_id`, `is_base` e `factor_to_base` sono fra le colonne scrivibili. Il
  DELETE della riga base lo vieta solo il FE (capability `puo_eliminarsi`). Così si ottiene un articolo senza
  base, con la base su un'unità diversa da `articoli.uom_id`, o con fattore diverso da 1, e quel fattore D2 lo
  usa nel calcolo.
* **Correzione.** Il CHECK, più un guard che sulla riga base vieta UPDATE di `uom_id`/`is_base`/`factor_to_base`
  e il DELETE, ma lascia passare il CASCADE dalla cancellazione dell'articolo.
* **Presidio.** `throws_ok` per i tre UPDATE e per il DELETE; `lives_ok` per la cancellazione dell'articolo.

#### D13 — `articoli_uom_operativa`: date di validità con un UNIQUE senza tempo

* **Fatto.** Ci sono `valido_dal`/`valido_al`/`validita`, ma anche `UNIQUE (articolo_id, uom_id)`. Il pattern
  «chiudi e inserisci» non si può applicare. La validità vuol dire solo «fuori dalla finestra non c'è
  mappatura», e lì si ricade in D2.
* **Correzione.** Q3: `UNIQUE … WITHOUT OVERLAPS` (come la distinta), oppure si ritira la validità.

#### D14 — Le due direzioni della stessa conversione possono contraddirsi

* **Fatto.** `uq_uom_conv_no_overlap` vale per la coppia orientata. A→B = 10 e B→A = 0,2 convivono attive, e
  `fn_get_uom_factor` prende la diretta senza dire niente.
* **Correzione.** Un'esclusione sulla coppia non orientata (`LEAST`/`GREATEST` più la validità): una
  conversione per coppia, l'inversa la calcola la funzione.
* **Presidio.** Con A→B in vigore, l'inserimento di B→A è rifiutato.

#### D15 — Due transazioni possono far nascere una conversione fra tipologie diverse (sospetto)

* **Fatto.** T1 cambia `tipo_uom_id` di un'unità e conta zero conversioni. T2 inserisce una conversione e il suo
  guard legge il tipo vecchio: la FK prende `KEY SHARE`, che è compatibile col `NO KEY UPDATE` di T1. Nessuna
  delle due aspetta l'altra.
* **Correzione.** Il guard delle conversioni legge le unità con `FOR SHARE`.
* **Presidio.** Prova a due sessioni.

#### D16 — Le note di catalogo non hanno la forma delle note degli altri schemi

* **Fatto.**
  * Manca `chk_note_testo_non_vuoto`, che vendite e acquisti hanno.
  * `anchor_tipo = 'RIGA'` è ammesso, con un `target_riga_id` senza FK né `trgfn_note_validate_generic`, mentre
    su un'anagrafica «riga» non ha significato.
  * `user_*` è `varchar(80)` invece di `text`, e manca `tx_id`.
  * La FK `target_tipo → config.tipi_entita` ammette codici senza partizione, e lì l'errore esce grezzo.
  * La partizione non ha `attivo`, quindi il `block_deact` generato impedisce di disattivare un articolo che ha
    una nota (verificare se è voluto).
* **Correzione.** Il CHECK sul testo; `anchor_tipo = 'DOCUMENTO' AND target_riga_id IS NULL` sulle partizioni di
  catalogo; Q12 per `tx_id`, `user_*` e il caso `block_deact`.
* **Presidio.** `throws_ok` per il testo vuoto e per l'àncora `RIGA`.

#### D17 — `unita_misura.conta_dal_calendario` non è legato alla tipologia TEMPO (sospetto)

* **Fatto.** Il modello ammette un'unità di massa che conta i giorni dal calendario.
* **Correzione.** Un guard sulla tipologia, o un CHECK attraverso il tipo.

#### D18 — `fn_articolo_usato` non guarda a quale colonna punta la FK

* **Fatto.** Filtra `confrelid` e `array_length(conkey) = 1`, poi confronta la colonna con l'`uuid`
  dell'articolo. Una FK verso `uq_articoli_codice`, che il modello ammette, fallisce con un errore di tipo, e con
  lei guard e form. Una FK composita viene saltata in silenzio, contro il «fail-closed» del COMMENT.
* **Correzione.** Si filtra `confkey` sulla colonna `id`. Una FK verso un'altra chiave si conta confrontando il
  valore di quella chiave, non si salta.
* **Presidio.** Tabella in `pg_temp` con una FK verso `articoli(codice)`: il predicato risponde true, senza
  errore.

#### D19 — `fn_articolo_correggi_struttura`: un JSON nullo o del tipo sbagliato esce come errore grezzo

* **Fatto.** `jsonb_populate_record`: `{"natura_vendita_id": null}` → 23502; `"forse"` su un boolean → 22P02.
  Nessuno dei due è un codice registrato.
* **Correzione.** Tipo e NOT NULL delle chiavi si validano prima di scrivere, con `E_PARAMETRO_INVALIDO`.
* **Presidio.** `null` su una colonna NOT NULL → `E_PARAMETRO_INVALIDO`.

#### D20 — `fn_articolo_colonne_struttura` lega la porta alle regole del form (sospetto)

* **Fatto.** Legge le regole `enabled` di `lock_columns_conditional` confrontando `condition_expr` come testo.
  Se si spegne una regola del form, il guard continua a bloccare la colonna, ma il verbo la rifiuta
  (`E_PARAMETRO_INVALIDO`): la colonna non si corregge più da nessuna parte. Il pgTAP
  `test-articolo-colonne-struttura-v1` lo presidia, ma è un presidio, non una garanzia del modello.
* **Correzione.** Q10. Si chiude con D28 del brief `dbops`, se il predicato diventa una funzione che leggono
  guard, form e porta.

#### D22 — Il fattore della mappatura si sceglie alla data di oggi, non alla data del documento

* **Fatto** (emerso nel giro 0). `trgfn_qta_from_operativa` filtra la mappatura dell'articolo con
  `fn_data_operativa()`, non con la data del documento. Con D13 risolto, cioè con le mappature versionate,
  una riga scritta oggi su un documento datato in un altro periodo prende il fattore di oggi. Una volta
  fotografato sulla riga, il fattore non cambia più. Va pesato insieme a D13 (Q13).
* **Correzione.** Se la mappatura si versiona, il fattore si legge alla data del documento.

### 2.3 La stessa regola scritta più volte (regola del 2)

| # | Regola | Dove sono le copie | Correzione |
| --- | --- | --- | --- |
| R1 | **Il fattore di conversione** | `catalogo.fn_get_uom_factor` contro `script.trgfn_qta_from_operativa` (D2); il trigger rilegge anche `articoli.uom_id` invece di `fn_get_uom_base` | Una sede, `fn_get_uom_factor`; il trigger la chiama |
| R2 | **La distinta di un padre alla data** | Il filtro `attivo + validita @> D` è riscritto a mano nei 5 `vendite.fn_*_riga_componenti_init`, nei 5 `*_preview`, in `script.trgfn_componenti_guard_coerenza_bom` e in `script.trgfn_listini_righe_comp_guard_coerenza_bom`. `vw_articoli_dettaglio.has_componenti_alla_data` ricopia `fn_articolo_padre_di_distinta_in_vigore`. Il guard IVA e `fn_check_articolo_riga_su_contesto` hanno ognuno la sua finestra (D9) | Un BB di catalogo parametrico per data (l'insieme dei legami del padre a D), e un predicato «da oggi in poi» per i guard. ⚠️ Tocca le funzioni di tutti i documenti di vendita: serve l'ok di Tid (Q8). Prima di usarlo nella vista si cronometra |
| R3 | **Il padre ha il flag giusto** | `trgfn_articoli_componenti_guard_is_composito` e `…_guard_solo_componente` hanno la stessa forma: leggono un flag di `prodotto_id` e sollevano. Il lato componente sta già nella check `ARTICOLO` (`fn_check_articolo_riga`); `script.trgfn_componenti_guard_coerenza_bom` ricontrolla a mano «padre `is_composito`» | I due motivi sul padre entrano nella check `ARTICOLO`; i due trgfn si ritirano nello stesso giro (Q5). Chiude anche D9 per il lato padre |
| R4 | **Il composito non sta in listino** | `trgfn_articoli_guard_listino_se_composito`, il motivo `E_LISTINO_RIGA_COMPOSITO_VIETATO` della check lato riga, `fn_articolo_righe_vive_non_ammesse` | Si ritira il guard (D5) |
| R5 | **L'etichetta leggibile dei flag** | Il `CASE` di `trgfn_articoli_guard_struttura_se_usato` e quello di `trgfn_articoli_guard_onere_natura` | Una funzione `catalogo.fn_articolo_flag_etichetta`, o un vocabolario, se le copie restano due |
| R6 | **La proiezione di una nota** | `vw_articoli_note` e `vw_articoli_componenti_note`: stesse 19 colonne di nota, stile e lingua. `script.fn_get_note` non serve, perché vuole un `target_id bigint` | Una vista base su `catalogo.note`, con le due viste sottili sopra |
| R7 | **Le FK ripetute come `*_ref_id`** | `vw_articoli_dettaglio`: `uom_ref_id`, `tipologia_ref_id`, `gruppo_ref_id`, `spesa_ref_id`, `iva_ref_id` duplicano le FK | Richiesta al BE (§5, BE5) |
| R8 | **«È composito», deciso fuori dal DB** | `backend/apps/vendite/services/offerte_service.py:1178,1209,1273`, `frontend/src/vendite/_shared/righe/RigheEccezioniDrawer.vue:668` (sospetto) | Richiesta al BE (§5, BE6): verificare se ricopiano una regola che il DB ha già |

⚠️ Le tre `fn_articolo_*_di_distinta_in_vigore` / `primo_padre_da_oggi` **non** sono copie: dicono tre cose
diverse (padre in vigore, componente in vigore, componente da oggi con il codice del padre). Restano.

### 2.4 Che cosa si può cancellare

| Oggetto | Perché | Condizione |
| --- | --- | --- |
| `trgfn_articoli_guard_listino_se_composito` e il suo trigger | D5, R4 | Q5 |
| `trgfn_articoli_componenti_guard_is_composito`, `…_guard_solo_componente` e i trigger | R3 (e D11 per il secondo) | Q5, Q2 |
| `uq_articoli_componenti_prodotto_componente_from` | Implicato da `uq_articoli_componenti_no_overlap`: `valido_dal` è NOT NULL, e due righe con lo stesso inizio si sovrappongono sempre | Nessuna; `uq_articoli_componenti_id_temporal` resta, perché regge la FK temporale |
| `ix_uom_tipi_codice_interno_upper`, `ix_artuomop_art_isbase` | Accanto a `uq_uom_tipi_codice_interno` (con `trgfn_codice_maiuscolo`) e all'unico parziale `uq_artuomop_one_base` (sospetto) | Verificare che nessuna query usi la forma `upper()` |
| `uom_tipi.codice` o `codice_interno` | Stessi valori, stessi COMMENT; il lock sta solo su `codice_interno` | Q9 |
| `articoli_uom_operativa.require_lot` (e forse `max_decimals`, `rounding_mode`) | D3 | Q4 |
| La FK semplice di `vendite.listini_righe_componenti` verso `articoli_componenti` | Implicata dalla FK temporale `PERIOD` (sospetto, fuori schema) | Verificare i lettori di `pg_constraint` |
| I wrapper BE `get_uom_base`/`get_uom_factor` (`catalogo_uom_repository.py:230-241`) | Senza chiamanti | Restano se D2 non li fa diventare utili: §5, BE2 |
| Rami irraggiungibili | `COALESCE` su colonne NOT NULL (`is_composito`, `attivo`, nei guard flags, listino, componente e in 10 `vendite.fn_*_componenti_*`); `TG_OP` e `prodotto_id IS NULL` in `guard_is_composito`/`solo_componente`; il ramo fail-open su `tipo_uom_id` NULL in `guard_tipo` (NOT NULL con FK); `v_factor > 0` e `LIMIT 1` su chiave UNIQUE in `fn_get_uom_factor`; `p_campi IS NULL OR` ripetuto nel verbo | Nello stesso giro che apre l'oggetto |

Nessuna funzione o vista è senza lettori: ognuna ha un chiamante nel DB, nel BE o in `ui.lista_definizione`.
Le colonne `is_sell_uom`, `is_purchase_uom`, `is_logistic_uom` e `gtin` sono dati d'anagrafica letti solo dal
CRUD: restano, ma il COMMENT non deve promettere un comportamento.

### 2.5 Codici errore

* Tutti i codici sollevati dalla distinta e dagli articoli sono registrati. `E_BOM_VALIDO_AL_INVALIDO`, ritirato,
  non è più sollevato.
* Codici generici al posto di codici registrati: D6.
* Errori grezzi: D19, e la FK delle note (D16).
* La nota di `E_BOM_MODIFICA_VIETATA` (`codici_errore.csv:78`) nomina solo il trigger d'immutabilità, ma lo
  solleva anche il guard flags (check 1 e 2).
* `fn_riattiva_articolo` (commento nel corpo e pagina) cita `E_PARENT_INACTIVE`, che non esiste: il codice vero
  è `E_ATTIVO_PADRE_NON_ATTIVO`, e arriva al COMMIT (trigger differito).
* L'area di log è disomogenea: `'database'` nei trigger della distinta, nel check 1-2 e in `fn_riattiva_articolo`,
  `'catalogo'` altrove. I guard IVA e listino passano `NULL::uuid` invece di `NEW.tx_id`.

#### D21 — Con `iva_id` NULL il messaggio del guard IVA esce col segnaposto vuoto

`iva_id` è nullable: il `SELECT … INTO` non trova righe e il `COALESCE(…, '—')` non scatta. Si chiude con D4.

### 2.6 Le fixture e i test pgTAP

`db/pgtap/catalogo` ha 25 file; nessuna riga di catalogo è nelle baseline dei rossi.

* **Senza presidio:** D1, D2, D3, D4 (legami chiusi), D5 lato articolo, D6 (`guard_tipo_update` non ha nessun
  test), D7, D8, D9, D11, D12, D16.
* **Deboli:**
  * `test-articoli-componenti-solo-componente.sql:77` usa `throws_ok(…, NULL, NULL)`: passa con qualunque errore
    e non lega `E_ARTICOLO_SOLO_COMPONENTE`.
  * `test-articoli-natura-vendita-notnull-default-v1.sql:49-53` conta i NULL di una colonna NOT NULL su tutta la
    popolazione: è tautologico, e in CI passa a vuoto.
  * `test-vw-articoli-dettaglio-e-onere-v1.sql:56-62` (test 3) itera su tutto il catalogo. I casi 1 e 2 sono
    costruiti: il test 3 si dichiara presidio o si toglie.
  * Le fixture che clonano «il primo articolo esistente» (`test-articoli-componenti-solo-componente.sql:52`,
    `ORDER BY a.id LIMIT 1`) dipendono dal seed. Vanno sui builder.

## 3. I metadati

Nessuno cambia il comportamento, ma ognuno dice una cosa falsa a chi legge. Si correggono con un changeSet nuovo,
nel giro che apre l'oggetto, oppure nel giro 5.

### 3.1 Dicono il falso

| # | Dove | Che cosa |
| --- | --- | --- |
| M1 | COMMENT `trgfn_articoli_guard_flags_struttura_bom_attiva` | «Lato articolo di `trgfn_articoli_componenti_guard_un_livello`»: non esiste. Il lato legame è `guard_componente` |
| M2 | COMMENT `vw_articoli_dettaglio` | «`requires_lotto` senza lock né fra i `non_editable_fields`»: falso, lo spegne una regola di `lock_columns_conditional` con `fn_articolo_usato`. «Non escono finché il BE non le nomina»: il BE le proietta già (`catalogo_repository.py:170,215-229`). Cita «ui.lista_definizione 26» per id |
| M3 | COMMENT `articoli.natura_vendita_id` | «NULL = non ancora classificato; a regime NOT NULL»: è già `NOT NULL DEFAULT 1` |
| M4 | COMMENT `articoli_componenti.id`, `.attivo` | «sequence `articoli_componenti_id_seq`»: è `uuid DEFAULT uuidv7()`. «del articolo» |
| M5 | COMMENT `articoli_uom_operativa.require_lot`, `.max_decimals`, `.rounding_mode` | Promettono un comportamento che nessuno applica (D3) |
| M6 | COMMENT `fn_get_uom_base` | «Senza UoM base»: `articoli.uom_id` è NOT NULL |
| M7 | COMMENT `magazzino.note` | Dice che `script.fn_get_note` legge anche le note di catalogo: falso, per via dell'uuid |
| M8 | Nota di `automation_lock_columns` su `catalogo.articoli.uom_id` | Cita `trg_articoli_a10_protect_uom_id_upd`, che non esiste più (oggi è `trg_articoli_a10_lock_columns_upd`); il codice `E_CODICE_NON_MODIFICABILE` è usato per un'unità di misura |

### 3.2 Senza COMMENT

* `vw_articoli_uom_operativa_dettaglio`: niente, né sulla vista né sulle colonne.
* Colonne delle altre 4 viste, di `note`, `note_articoli`, `note_articoli_componenti`, e tutte le colonne di
  `unita_misura_conversioni`; le 4 colonne d'audit di `uom_tipi`.
* I trigger dei guard di catalogo, tranne `trg_articoli_a10_guard_onere_natura_ins_upd` e
  `trg_articoli_componenti_a10_guard_is_composito_ins_upd`.

### 3.3 Marcatori di revisione, nomi di brief, id nei COMMENT (`linee-guida-sql.md` §5d)

* **Funzioni.** 11 su 23: `fn_articoli_ammessi`, `fn_articolo_colonne_struttura`, `fn_articolo_correggi_struttura`,
  `fn_articolo_righe_vive_non_ammesse`, `fn_articolo_usato`, `trgfn_articoli_componenti_block_modifica_struttura`,
  `trgfn_articoli_componenti_guard_componente`, `trgfn_articoli_guard_iva_bom_attiva`,
  `trgfn_articoli_guard_listino_se_composito`, `trgfn_articoli_guard_onere_natura`,
  `trgfn_articoli_guard_struttura_se_usato`.
* **Viste e tabelle.** 4 viste su 5 (`vw_articoli_componenti_dettaglio`, `vw_articoli_componenti_note`,
  `vw_articoli_dettaglio`, `vw_articoli_note`) e la tabella `note`.
* **Colonne.**
  * `articoli`: `causale_onere_id`, `gestito_a_magazzino`, `modo_approvvigionamento_id`, `note_target_tipo`,
    `obsoleto_dal`, `requires_lotto`;
  * `articoli_componenti`: `esposizione_in_fattura`, `note_target_tipo`, `validita`;
  * `validita` di `articoli_uom_operativa` e di `unita_misura_conversioni`;
  * `note.target_tipo`, `unita_misura.conta_dal_calendario`;
  * in `vw_articoli_dettaglio`: `causale_onere_id`, `e_obsoleto`, `e_onere`, `obsoleto_dal`.
* **Id di messaggio invece della chiave naturale** (§6b): «(387)», «(445)», «(446)» nei guard.
* **Cronaca nei corpi**: `-- rev 2026-10-19 (20261019-98…)` in `guard_onere_natura`, `Rev 20261002-61` in
  `block_modifica_struttura`, il nome di un brief in `guard_componente`.

Una parte coincide con D-C di `brief-db-articoli-obsoleto-dal` (Q11).

## 4. La documentazione

### 4.1 Le 35 pagine `manual/`

Nessuna passa la verifica di `standard-guide.md` §«Verifica di una pagina `manual/`». Il giro 0 le riscrive tutte
allo standard. La pagina descrive il comportamento di **oggi**, difetti compresi (come in `dbops`), e si riallinea
quando il difetto si chiude.

**Gli scostamenti comuni** (quasi tutte le pagine):
* manca «Ultimo aggiornamento»;
* «Vedi anche» con righe senza `>`, bullet `•`, etichette mancanti, link a `manual/` invece che alle schede;
* il primo paragrafo dello Scopo è un marcatore (`(latest review …)`, `(rev …)`, `(nasce …, brief …)`), e così
  finisce come descrizione dell'oggetto nell'indice dello schema (`catalogo/index.md`);
* nomi di brief, «Lotto», «Fase», id di changeSet nel corpo;
* blocchi `sql`, `json` o `python`, elenchi di colonne o di trigger agganciati ricopiati, sezioni «Best practice».

**Le pagine da rifare da capo** (formato vecchio: titolo `#`, otto o nove `##`, niente Scopo Principale, quindi
nessuna descrizione nell'indice): `unita_misura`, `uom_tipi`, `unita_misura_conversioni`,
`trgfn_articoli_guard_flags_struttura_bom_attiva`, `trgfn_articoli_guard_iva_bom_attiva`,
`trgfn_articoli_guard_listino_se_composito` (le ultime tre anche senza firma). Senza firma anche
`articoli_uom_operativa`.

**Il contenuto falso oggi**, da correggere nella riscrittura:

| Pagina | Che cosa |
| --- | --- |
| `articoli.md` | `voce_utility` non esiste; «tutte le FK ON UPDATE CASCADE» (falso per `uom_id` e `causale_onere_id`); «consigliato proteggere il codice», «valuta un trigger uppercase» (esistono lock e `trgfn_codice_maiuscolo`); «`requires_lotto` fuori dal registro»; destinazione `ORDINE` (oggi `ORDINE_VENDITA`); una sezione `🔄 rev` dopo la firma |
| `vw_articoli_dettaglio.md` | `ORDINE/COMMESSA/CONTRATTO`; «senza il lock BoM», «il BE non le nomina» (come M2) |
| `articoli_componenti.md` | `EXCLUDE USING gist` e `ix_…_no_overlap_gist`: oggi c'è `uq_articoli_componenti_no_overlap … WITHOUT OVERLAPS`; «`valido_al > valido_dal`»: è ammesso `=`; «i REQUIRE non sono generati»: li genera la regola ATTIVO; il controllo su `is_composito` chiamato «vincolo applicativo opzionale» (è un trigger); un id per numero |
| `vw_articoli_componenti_dettaglio.md` | `valid_from`/`valid_to` non esistono (`valido_dal`/`valido_al`); mancano `esposizione_*` e le capability |
| `trgfn_articoli_componenti_block_modifica_struttura.md` | `ex_articoli_componenti_no_overlap` e `chk_articoli_componenti_valid_dates` non esistono; `validita` fra i campi bloccati (è generata); «protegge da correzioni retroattive» (D10); non dice che `prodotto_id` è libero (D1) |
| `trgfn_articoli_componenti_guard_is_composito.md`, `…_guard_solo_componente.md` | Esempi con `valid_from`; «nessun effetto se NULL» (la colonna è NOT NULL) |
| `trgfn_articoli_componenti_guard_componente.md` | «L'IVA non cambia, la tiene il lato articolo»: vero per l'IVA, falso per composito e obsoleto (D9). Manca «Codici errore» |
| `trgfn_articoli_guard_flags_struttura_bom_attiva.md` | «Padre e figlio in BoM diverse» contro il livello unico |
| `trgfn_articoli_guard_iva_bom_attiva.md` | La procedura «prima i partner» (D4) |
| `trgfn_articoli_guard_listino_se_composito.md` | «Simmetrico di `trgfn_listini_righe_guard_no_composito`», ritirato; il rimedio suggerito (D5) |
| `fn_articolo_righe_vive_non_ammesse.md`, `fn_articolo_correggi_struttura.md` | Citano `fn_check_articolo_riga`: dal 2026-10-21 il corpo usa `fn_check_riga_documento_su_contesto`. «Il backend lo espone nel giro BE/FE»: lo espone già |
| `fn_articoli_ammessi.md` | Firma in un blocco sql |
| `fn_articolo_*_di_distinta_in_vigore.md`, `fn_articolo_primo_padre_da_oggi.md` | Id di changeSet nelle Note di migrazione |
| `fn_riattiva_articolo.md` | `E_PARENT_INACTIVE` (§2.5); «13+ relazioni», un conteggio; `()` nel titolo |
| `note_articoli.md`, `note_articoli_componenti.md` | «Partizione di `vendite.note`»: il padre è `catalogo.note`; ipotizza `ON DELETE RESTRICT`, ma la FK è `CASCADE`; conteggi di righe. Tace il `block_deact` (D16) |
| `uom_tipi.md` | `VALUTA` non è nel seed; «conversioni SMC↔KWH/MJ già presenti»: il CSV è vuoto; chiama `codice` l'identificativo stabile, ma il codice bloccato è `codice_interno` |
| `unita_misura.md` | Non nomina `conta_dal_calendario` |
| `unita_misura_conversioni.md` | Il fallback della funzione non è usato da nessuno (D2); `valido_dal` è NOT NULL |
| `articoli_uom_operativa.md` | Le regole di input applicate (D3); «`factor_to_base = 1` sulla base» non è un vincolo (D12); «Migliorie» stantie (l'indice unico parziale c'è) |
| `trgfn_uom_conversioni_guard_tipo.md` | «Resta scoperta l'unità senza tipologia»: `tipo_uom_id` è NOT NULL con FK |
| `trgfn_unita_misura_guard_tipo_update.md` | I consumatori si cercano dal nome della funzione, ma in `error_log` c'è il trigger (D6) |
| `trgfn_articoli_seed_uom_base.md` | Il caso «riga già esistente» non capita all'INSERT di un id nuovo; tace D7 e D12 |
| `fn_get_uom_base.md` | «Senza UoM base» (M6) |

**Il blocco comune delle note.** Manca un `catalogo/_note-partizioni.md` sul modello di
`magazzino/_note-partizioni.md`. Le due pagine delle partizioni diventano cornice, Scopo e include, più la sola
specificità (chiave uuid, il legame della distinta).

### 4.2 Doc fuori schema

| File | Correzione |
| --- | --- |
| `guide/gestione-listini.md:383` | `ex_articoli_componenti_no_overlap` «exclusion constraint» → `uq_articoli_componenti_no_overlap`, `UNIQUE … WITHOUT OVERLAPS` |
| `guide/gestione-listini.md:374` | I campi immutabili senza `prodotto_id`: si allinea con D1 |
| `guide/gestione-listini.md:380-381` | «Chiudi con `valido_al = oggi`, poi la nuova con `valido_dal = oggi`»: con `validita` `'[]'` le due righe si sovrappongono sul giorno, e il vincolo le rifiuta. Va verificata, poi corretta (la nuova parte da domani, o la vecchia chiude ieri) |
| `dev/manual/modello-componenti-bom.md` | §9.2 «un livello, i cicli non si costruiscono»: vero solo a D9 chiuso; `partecipa_qta`/`esposto_in_fattura` come cronaca (stanno già nel changelog delle decisioni). Link a `manual/` alle righe 128, 328, 330, 467 |
| `dbzero/script/manual/trgfn_righe_guard_articolo_ammesso.md:31,57`, `fn_articolo_riga_contesto.md:7`, `fn_check_articolo_riga.md:9,19`, `fn_check_articolo_riga_su_contesto.md:9,45`, `trgfn_listini_righe_comp_guard_coerenza_bom.md:15`; `dbzero/vendite/manual/promo_articoli.md:65` | Link `/dbzero/catalogo/manual/…` ripuntati alle schede |

## 5. Ricadute su BE e FE

Da girare al team quando il giro DB corrispondente è applicato.

| # | Giro | Che cosa |
| --- | --- | --- |
| BE1 | 2 | `fn_delete_uom_operativa` (`catalogo_service.py:1700`) cancella anche la riga base: col guard di D12 il DB rifiuta. Il servizio non la offre più, e il controllo parziale di `:844` si ritira (lo fa il DB) |
| BE2 | 2 | `get_uom_base`/`get_uom_factor` (`catalogo_uom_repository.py:230-241`) non hanno chiamanti: si ritirano, a meno che non servano al form |
| BE3 | 2 | Verificare se il servizio delle righe azzera `factor_to_base` quando cambia l'unità (D8). Dopo il giro non serve più |
| BE4 | 2, 3 | I codici nuovi (D2, D6, eventualmente D3) nella mappa degli errori e nell'i18n; `E_PARAMETRO_INVALIDO` da `fn_articolo_correggi_struttura` (D19) |
| BE5 | 5 | Se la vista perde i `*_ref_id` (R7), la proiezione del repository li prende dalle FK |
| BE6 | — | `offerte_service.py:1178,1209,1273` e `RigheEccezioniDrawer.vue:668` decidono su `is_composito`: verificare se ricopiano una regola del DB (R8) |
| BE7 | 3 | Se il cambio d'IVA diventa un verbo del kit (Q6), il form dell'articolo lo chiama |
| BE16 | 2 | Q4 ritira `rounding_mode` e `require_lot`: il lookup `GET /api/v1/catalogo/lookup/rounding-modes/` (`api_catalogo.md` §2.3, `_ROUNDING_MODE_VALIDI` in `catalogo_service`) e i campi del form dell'unità operativa si ritirano nello stesso giro BE |
| BE8 | 1 | I due codici nuovi `E_BOM_CHIUSURA_RETROATTIVA` (DATO_ERRATO, campo `valido_al`) ed `E_BOM_LEGAME_CHIUSO` (CONFLITTO_STATO, campo `valido_al`): mappa degli errori generata (`error_policies_generated.py`) e i18n. `E_ARTICOLO_NON_COMPOSITO` ora porta `campo = prodotto_id` e un bersaglio `ARTICOLO` |
| BE9 | 1 | «Chiudi riga» della distinta: `data_min_chiusura` è ieri (non più `valido_dal`); il datepicker la legge dalla vista, nessun calcolo nel FE. Da allineare anche `docs/it/backend/catalogo/manual/api_catalogo.md:601` (dice «`valido_dal` se chiudibile») e §4.3 (`valido_al` «unico campo modificabile»: va detto che la fine non cambia i giorni passati e che una fine già passata non si tocca) |
| BE10 | 1 | Il form dell'articolo: `is_composito` e `is_solo_componente` insieme li rifiuta ora un CHECK (23514, `chk_articoli_composito_non_solo_componente`). Il form spegne l'uno quando l'altro è acceso, e il servizio mappa il vincolo a un messaggio |
| BE11 | 1 | `catalogo_bom_repository.delete_componente` (`:270`) non può mai riuscire: il trigger d'immutabilità rifiuta ogni DELETE. Si ritira con il suo endpoint, oppure diventa «chiudi». `api_catalogo.md` §4.4 documenta ancora il `DELETE` |
| BE12 | 1 | Il picker degli articoli ammessi per la distinta (`catalogo.fn_articoli_ammessi` con `ARTICOLO`) su un padre non composito solleva `E_ARTICOLO_NON_COMPOSITO` invece di restituire una lista vuota: il FE apre il picker solo con `puo_gestire_bom` |
| BE8 ✅ (2026-11-09) | 1 | I due codici nuovi `E_BOM_CHIUSURA_RETROATTIVA` (DATO_ERRATO, campo `valido_al`) ed `E_BOM_LEGAME_CHIUSO` (CONFLITTO_STATO, campo `valido_al`): mappa degli errori generata (`error_policies_generated.py`) e i18n. `E_ARTICOLO_NON_COMPOSITO` ora porta `campo = prodotto_id` e un bersaglio `ARTICOLO` |
| BE9 ✅ (2026-11-09) | 1 | «Chiudi riga» della distinta: `data_min_chiusura` è ieri (non più `valido_dal`); il datepicker la legge dalla vista, nessun calcolo nel FE |
| BE10 ✅ (2026-11-09) | 1 | Il form dell'articolo: `is_composito` e `is_solo_componente` insieme li rifiuta ora un CHECK (23514, `chk_articoli_composito_non_solo_componente`). Il form spegne l'uno quando l'altro è acceso, e il servizio mappa il vincolo a un messaggio |
| BE11 ✅ (2026-11-09) | 1 | `catalogo_bom_repository.delete_componente` (`:270`) non può mai riuscire: il trigger d'immutabilità rifiuta ogni DELETE. Si ritira con il suo endpoint, oppure diventa «chiudi» |
| BE12 ✅ (2026-11-09) | 1 | Il picker degli articoli ammessi per la distinta (`catalogo.fn_articoli_ammessi` con `ARTICOLO`) su un padre non composito solleva `E_ARTICOLO_NON_COMPOSITO` invece di restituire una lista vuota: il FE apre il picker solo con `puo_gestire_bom` |

## 6. Le decisioni di Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| Q1 ✅ | D10: un legame di distinta si può chiudere nel passato, o riaprire? | No a tutte e due, per i legami già in vigore: si chiude da oggi in poi, e una riapertura è una riga nuova — **✅ Tid, 2026-11-08: come da proposta** |
| Q2 ✅ | D11: CHECK `NOT (is_composito AND is_solo_componente)`? | Sì, e `guard_solo_componente` si ritira — **✅ Tid, 2026-11-08: come da proposta** |
| Q3 ✅ | D13: la mappatura dell'unità operativa si versiona? | Sì, `UNIQUE … WITHOUT OVERLAPS` come la distinta; altrimenti si ritirano le date — **✅ Tid, 2026-11-08: versionata, UNIQUE WITHOUT OVERLAPS** |
| Q4 ✅ | D3: `max_decimals`, `rounding_mode`, `require_lot` | `max_decimals` si applica (codice nuovo); `rounding_mode` e `require_lot` si ritirano (il lotto è `articoli.requires_lotto`) — **✅ Tid, 2026-11-08: come da proposta** |
| Q5 ✅ | R3, R4, D5: si ritirano `guard_listino_se_composito`, `guard_is_composito`, `guard_solo_componente`, e i motivi sul padre vanno nella check `ARTICOLO`? | Sì — **✅ Tid, 2026-11-08: come da proposta** |
| Q6 ✅ | D4: cambio d'IVA di un kit con un constraint trigger differito, o con un verbo? | Constraint trigger differito: non cambia il contratto del BE — **✅ Tid, 2026-11-08: come da proposta** |
| Q7 ✅ | D2: senza mappatura né conversione, la riga si rifiuta? | Sì, `E_UOM_MISSING` — **✅ Tid, 2026-11-08: come da proposta** |
| Q8 ✅ | R2: il BB «distinta alla data» tocca le funzioni di tutti i documenti di vendita. Si fa qui, in un giro a parte, o in un brief di vendite? | Qui, giro 1-bis, dopo il giro 1 e insieme a D28 di `dbops` — **✅ Tid, 2026-11-08: come da proposta, ok alla famiglia dei documenti di vendita** |
| Q9 ✅ | `uom_tipi`: `codice` o `codice_interno`? | Resta `codice_interno` (bloccato); `codice` si ritira, se il BE non lo espone come etichetta — **✅ Tid, 2026-11-08: come da proposta** |
| Q10 ✅ | D20: la porta amministratore deve dipendere dalle regole del form? | No: le colonne strutturali si dichiarano in un posto, che leggono guard, form e porta (con D28) — **✅ Tid, 2026-11-08: come da proposta** |
| Q11 ✅ | M3 e D-C di `brief-db-articoli-obsoleto-dal`: chi riscrive i COMMENT? | Tutti qui, nel giro 5; D-C si chiude rimandando qui — **✅ Tid, 2026-11-08: tutti qui; D-C di brief-db-articoli-obsoleto-dal si chiude rimandando qui** |
| Q12 ✅ | D16: le note di catalogo prendono `tx_id` e `user_* text` come le altre? E un articolo con una nota si deve poter disattivare? | Sì alla forma comune; sì alla disattivazione (la nota non è un figlio vivo: va esclusa dal `block_deact`) — **✅ Tid, 2026-11-08: come da proposta** |
| Q13 ✅ | D22: il fattore della mappatura si legge alla data del documento? | Sì, se Q3 versiona la mappatura; altrimenti la domanda cade — **✅ Tid, 2026-11-08: il fattore si legge alla data del documento** |
| Q14 ✅ | §2.4: si ritirano gli indici che ripetono un vincolo? | `uq_articoli_componenti_prodotto_componente_from` sì; `ix_uom_tipi_codice_interno_upper` e `ix_artuomop_art_isbase` solo dopo la verifica dei lettori e dei piani — **✅ Tid, 2026-11-08: come da proposta** |
| Q19 ✅ | D24 (§13.7.3, domanda 1): il fattore di una mappatura già scritta si cambia sul posto? | No: **bloccato**. Un fattore nuovo è una riga nuova (chiudi e inserisci, Q3) — **✅ Tid, 2026-11-10** |
| Q20 ✅ | D25 (§13.7.3, domanda 2): l'unità della riga di listino deve valere alla decorrenza della versione o per tutto il suo periodo? | **Per tutto il periodo** della versione, regola a DB — **✅ Tid, 2026-11-10** |
| Q21 ✅ | D26 (§13.7.3, domanda 3): il fattore 1 per difetto delle commesse va in un brief nuovo? | No, **in questo brief** — **✅ Tid, 2026-11-10** |

## 7. I giri, nell'ordine in cui si fanno

Per gravità; i lavori sugli stessi oggetti vanno insieme, così ogni oggetto si apre una volta sola. Ogni giro
comprende changeSet, pgTAP del presidio, COMMENT e pagine `manual/` riallineati, poi l'apply di Tid e il via al
giro dopo.

| Giro | Classe | Contenuto | Perché insieme |
| --- | --- | --- | --- |
| 0 | doc | §4: le 35 pagine, il blocco comune delle note, la doc fuori schema | Non tocca il DB; descrive l'oggi e rende leggibili i giri dopo |
| 1 | A + B | **La distinta.** D1, D9, D10 (Q1), D11 (Q2), R3 (Q5); pgTAP di §2.6 sulla distinta | Gli stessi trigger di `articoli_componenti` e il guard flags. Dopo D28 di `dbops`, o con D28 |
| 1-bis | B | **Il BB della distinta alla data** (R2, Q8) | Tocca vendite e `script`: un giro a parte, con l'ok di Tid |
| 2 | A + B | **Le quantità e le unità.** D2 (Q7), D3 (Q4), D8, D12, D13 (Q3), D22 (Q13), D14, D15, D6, D17; BE1-BE4 | `trgfn_qta_from_operativa`, `articoli_uom_operativa` e i due guard di tipologia |
| 2-bis | A + B | **Le tre decisioni del giro BE.** D24 (Q19), D25 (Q20), D26 (Q21); BE19-BE21 (§14) | Nascono dal giro BE del giro 2; tocca anche `vendite` (listini, commesse) |
| 3 | A + B | **I guard degli articoli.** D4 (Q6) + D21, D5 (R4), D7, D18, D19, D20 (Q10), R5 | Gli oggetti di `catalogo.articoli` |
| 4 | B | **Le note.** D16 (Q12), R6 | Tabella `note`, partizioni e due viste |
| 5 | C | **Pulizia e metadati.** §3 (Q11), §2.4 (indici ridondanti, rami irraggiungibili, `uom_tipi.codice` con Q9), §2.5, pgTAP deboli di §2.6, R7 | Quello che nessun giro precedente ha già aperto |

## 8. Alla chiusura

* Ogni pagina `manual/` toccata passa la verifica di `standard-guide.md`, e la sua data è aggiornata.
* I pgTAP nuovi costruiscono i propri soggetti: nessuno itera su ciò che c'è.
* Il brief va in `work-done/` quando tutti i giri sono applicati e le ricadute BE sono chiuse o passate a un
  brief BE.

## 9. Giro 0 — la documentazione, 2026-11-08

Scritto dalla sessione DB su via di Tid, con quattro agenti per area (articoli, distinta e doc fuori schema, unità
di misura, note). Le pagine descrivono il comportamento di oggi, letto dai corpi (`pg_get_functiondef`), da
`pg_trigger`/`pg_constraint` di dbdev e dalle schede auto-generate. I difetti di §2 sono scritti al presente,
in una sezione «⚠️ Che cosa oggi non copre», senza rimandi a questo brief. Si chiudono pagina per pagina con il
giro che li corregge.

### 9.1 Che cosa è scritto

* **Le 35 pagine `docs/it/dbzero/catalogo/manual/`.** Tutte riscritte nella cornice dello standard. Le sei in
  formato vecchio sono rifatte da capo. Le falsità di §4.1 sono tolte.
* **Il blocco comune `docs/it/dbzero/catalogo/_note-partizioni.md`** (nuovo). È incluso dalle due partizioni.
* **Doc fuori schema.**
  * `guide/gestione-listini.md` §5.3: la procedura «chiudi e versiona» ora funziona. La vecchia versione chiude
    all'ultimo giorno e la nuova parte dal giorno dopo, perché `validita` comprende i due estremi. Il nome del
    vincolo è corretto.
  * `dev/manual/modello-componenti-bom.md`: link ripuntati alle schede.
  * `script/manual/`: `trgfn_righe_guard_articolo_ammesso`, `fn_articolo_riga_contesto`, `fn_check_articolo_riga`,
    `fn_check_articolo_riga_su_contesto` e `trgfn_listini_righe_comp_guard_coerenza_bom`.
  * `vendite/manual/promo_articoli`.
  * Su questi file sono cambiati solo i link verso `/dbzero/catalogo/manual/` e la data. Erano puliti in
    `git status`.

### 9.2 Le verifiche

Su tutte le 35 pagine, i sei controlli di `standard-guide.md` §«Verifica di una pagina `manual/`» passano:
* nessuna etichetta senza `>`;
* uno Scopo Principale che non comincia con `(`;
* marcatori solo nelle Note di migrazione;
* un solo `##`;
* firma in fondo e nessun link `/dbzero/…` morto;
* nessun blocco di codice.

In più: nessun id di changeSet, nessun link a `/dbzero/…/manual/`, data all'8 novembre 2026. La build della doc
non è stata lanciata, quindi l'include del blocco comune non è provato al rendering.

### 9.3 Fatti emersi nella riscrittura

* **Un legame di distinta non si cancella mai.** `trgfn_articoli_componenti_block_modifica_struttura` rifiuta ogni
  DELETE (`E_BOM_MODIFICA_VIETATA`). Con il `block_deact` della nota, un legame annotato si può solo chiudere con
  `valido_al`. È coerente con «chiudi e inserisci»: un fatto, non un difetto. Ora è scritto nelle pagine.
* **D22**, nuovo (§2.2): il fattore della mappatura si sceglie alla data di oggi.
* **D7 resta da eseguire.** L'articolo creato non attivo è descritto nelle pagine come difetto. L'affermazione si
  regge sui corpi, ma non è stata provata.

### 9.4 Residuo

* Le date delle Note di migrazione vengono dalle pagine vecchie, dagli header dei pgTAP e da `git log -S`, non da
  un controllo changeSet per changeSet.
* La pagina d'esempio `dbops/manual/fn_resolve_scope.md` ha ancora un id di changeSet nelle Note di migrazione,
  contro lo standard. È fuori perimetro: la sistema il brief `dbops`.

### 9.5 Commit (2026-11-08)

* Una parte del giro 0 è finita nel commit `ecd35e08cf` di un'altra sessione DB: le tre pagine delle note
  (`note`, `note_articoli`, `note_articoli_componenti`), i link di `script/manual`, `promo_articoli` e
  `modello-componenti-bom`. Quel commit include il blocco comune, ma non lo contiene.
* Il resto è in un commit di questo cantiere: le altre 32 pagine `manual/`, il blocco
  `_note-partizioni.md`, `guide/gestione-listini.md` e questo brief.
* Le schede auto-generate di `catalogo` modificate nel working tree (`tabelle/`, `funzioni/`, `index*.md`)
  sono di altre sessioni e restano fuori.

## 10. Giro 1 — la distinta, 2026-11-09

Via di Tid il 2026-11-09, coi numeri dal `20261110-62`. Difetti del giro: D1, D9, D10 (Q1), D11 (Q2), R3 (Q5). D28 del
brief `dbops` è già chiuso (giro 10a): il giro parte dai suoi predicati.

### 10.1 Che cosa è scritto

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/catalogo/20261110-62` | `catalogo.fn_articolo_padre_di_distinta_da_oggi`: padre di una distinta in vigore o futura, la stessa finestra del lato componente |
| `20_code/catalogo/20261110-63` | Guard flags: il check 1 chiede il predicato da oggi (D9); area di log `catalogo`; COMMENT secondo §5d |
| `20_code/script/20261110-64` | `script.fn_articolo_riga_contesto`: la testata della distinta è un composito, altrimenti `E_ARTICOLO_NON_COMPOSITO` (Q5). Sede unica della regola del padre |
| `20_code/catalogo/20261110-65` | `trgfn_articoli_componenti_guard_componente` e il suo trigger: `UPDATE OF` anche `valido_al`; giudica la riattivazione e l'allungamento della fine; la chiusura no (D9) |
| `20_code/catalogo/20261110-66` | `trgfn_articoli_componenti_block_modifica_struttura` e il suo trigger: `prodotto_id` immutabile (D1); la fine non cambia i giorni già passati (Q1, D10) |
| `20_code/catalogo/20261110-67` | Ritirati `trgfn_articoli_componenti_guard_is_composito` e `…_guard_solo_componente`, coi trigger (R3, Q5) |
| `20_code/catalogo/20261110-68` | `vw_articoli_componenti_dettaglio`: `data_min_chiusura` = la più tarda fra `valido_dal` e ieri (Q1) |
| `80_data/changelog/20261110-69` | `lock_columns_conditional`: le regole 1-2 del form chiamano il predicato da oggi, come il guard |
| `90_end/20261110-70` | Ritirata `catalogo.fn_articolo_padre_di_distinta_in_vigore` (dopo le regole del form) |
| `90_end/20261110-71` | CHECK `chk_articoli_composito_non_solo_componente` su `catalogo.articoli` (Q2) |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_BOM_CHIUSURA_RETROATTIVA` (1462), `E_BOM_LEGAME_CHIUSO` (1463); note e causa di `E_BOM_MODIFICA_VIETATA` riscritte |

`%TYPE` in firma, `DECLARE` e nelle firme di `COMMENT`/`DROP`; i corpi di partenza da `pg_get_functiondef` su dbdev;
rollback = corpi, COMMENT e trigger di prima.

### 10.2 La forma della regola di Q1

Q1 (Tid, 2026-11-08) dice: la fine di un legame in vigore non si sposta nel passato e non si toglie. Scritta sul
modello, la regola è **«la fine non cambia i giorni già passati»**, al giorno aziendale:

* una fine **già passata** non si tocca più: né spostata, né tolta (`E_BOM_LEGAME_CHIUSO`). Per rimettere il componente
  si inserisce un legame nuovo;
* le altre fini vanno **a vuoto o da ieri in avanti** (`E_BOM_CHIUSURA_RETROATTIVA`, con la prima data ammessa);
* **chiudere a ieri** è ammesso, perché la storia resta com'era, ed è il modo di far valere da oggi la versione nuova
  (la `validita` comprende i due estremi);
* **togliere una fine futura** è ammesso, perché il passato non cambia; lo giudica il guard del legame come composizione
  nuova (componente ritirato o composito, padre non composito).

### 10.3 Le scelte dentro il giro (da guardare, Tid)

1. **Il padre non composito è un controllo del documento, non un motivo.** L'ho messo in `fn_articolo_riga_contesto`,
   come il padre mancante, e non fra i motivi del componente. Ne segue che il picker della distinta su un padre non
   composito solleva invece di proporre una lista vuota (BE12). In compenso la regola ha una sede sola, ed è il lato
   documento della stessa check che già giudicava il componente.
2. **Il check 2 del guard flags non cambia finestra.** Resta «componente di una distinta in vigore»: D9 parla
   del padre, e la regola del check 2 (un componente non cambia `is_solo_componente`) è sospetta di suo (§2.2, D11).
   Il suo predicato `fn_articolo_componente_di_distinta_in_vigore` resta.
3. **Una fine prima di `valido_dal` resta alla regola del periodo.** Il trigger d'immutabilità non la giudica, così
   l'operatore legge la frase della regola del periodo, come prima.
4. **L'area di log `database` diventa `catalogo`** nei corpi che il giro riscrive (guard flags, immutabilità), e
   l'immutabilità registra il `tx_id` della riga.

### 10.4 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di Liquibase, `BEGIN … ROLLBACK`)

* **Estratto e preCondition.** Le dieci `changes` in ordine di fase e numero, con le `preConditions` come asserzioni
  dopo i changeSet precedenti, più le righe nuove dei CSV: passano tutte in una transazione. Dopo il `ROLLBACK` lo
  scratch è com'era (il predicato vecchio c'è, il nuovo no). Le `preConditions` lette anche su dbdev, prima: stesse
  risposte dello scratch.
* **I pgTAP che toccano gli oggetti del giro**: tutti quelli di `catalogo/`, più quelli che nominano la distinta, la
  check, le regole del form o il picker, cioè 73 file, con e senza l'estratto in testa.
  * Verdi con l'estratto, tranne `catalogo/test-articolo-usato-struttura-v1` test 17, rosso uguale anche senza: il file
    stesso lo dichiara «rosso da owner, verde come app».
  * Cambiati nel giro, perché asserivano la regola di prima: `catalogo/test-distinta-predicati-guard-e-form-v1` (il
    predicato nuovo, un padre con distinta solo futura), `catalogo/test-vw-articoli-componenti-dettaglio-capabilities-v1`
    (la prima fine è ieri), `vendite/test-fatture-righe-kit-qta-periodo-v1` test 21 (`prodotto_id` fra i campi bloccati),
    `catalogo/test-vw-articoli-dettaglio-bom-capability-v1` (la fixture costruiva un kit solo componente),
    `catalogo/test-articoli-componenti-solo-componente` (riscritto sulle due sedi della regola).
  * ⚠️ `catalogo/test-articoli-componenti-guard-attivo-composito` cercava per nome il guard ritirato: senza correzione il
    caso «padre non composito» sarebbe diventato uno skip verde. Ora cerca il guard del legame.
  * Nuovo: `catalogo/test-distinta-storia-e-ritorni-v1` (15 test: padre immutabile, le regole della fine, riattivazione
    e allungamento giudicati, padre con distinta solo futura, la capability della vista). Senza l'estratto: 9 rossi
    su 15, cioè prova davvero la regola nuova.
  * Commenti che nominavano il guard ritirato in sette pgTAP: ripuntati alla check della distinta.
* **Deadlock.** Una prima corsa ha incontrato una corsa pgTAP di un'altra sessione sullo scratch: sei file in
  deadlock. Rilanciati a scratch libero, verdi.
* **Non provato:** la corsa come app (la fa Tid dopo l'apply), e il migrate vero (pgjdbc, ordine reale).

### 10.5 Doc

Pagine `manual/` riallineate al giro: cancellate quelle dei tre oggetti ritirati, creata quella del predicato nuovo,
aggiornate le pagine della distinta, del guard flags, degli articoli, del contesto e della check, la guida dei listini
§5.3 e il modello della distinta. Le sezioni «⚠️ Che cosa oggi non copre» perdono i punti che il giro chiude. La scheda
auto-generata del predicato nuovo nasce alla rigenerazione della doc, dopo l'apply.

### 10.6 Chiusura (2026-11-09)

* **Applicato** da Tid su dbdev e sullo scratch: `20261110-62` … `-71` e le due righe nuove dei CSV dei codici. Su dbdev
  i dieci changeSet sono nel `databasechangelog` (letto il 2026-11-09). pgTAP come app verdi.
* **Da committare** (il giro 1 intero):
  * i changeSet `20_code/catalogo/20261110-62`, `-63`, `-65` … `-68`, `20_code/script/20261110-64`,
    `80_data/changelog/20261110-69`, `90_end/20261110-70`, `-71`;
  * `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (solo le righe di questo giro);
  * i pgTAP: `catalogo/test-distinta-storia-e-ritorni-v1.sql` (nuovo), `test-articoli-componenti-solo-componente.sql`,
    `test-distinta-predicati-guard-e-form-v1.sql`, `test-vw-articoli-componenti-dettaglio-capabilities-v1.sql`,
    `test-vw-articoli-dettaglio-bom-capability-v1.sql`, `test-articoli-componenti-guard-attivo-composito.sql`,
    `test-articoli-componenti-immutabilita.sql`, `vendite/test-fatture-righe-kit-qta-periodo-v1.sql`, e i commenti
    in `vendite/test-righe-e-componenti-le-altre-famiglie-v1.sql`, `vendite/test-righe-e-componenti-debiti-residui-v1.sql`,
    `vendite/test-componenti-propaga-qta-da-operativa-v1.sql`, `vendite/test-ddt-componenti-senza-prezzo-v1.sql`,
    `script/test-fn-check-prezzi-autorizzati-v1.sql`, `dbops/test-fn-non-editable-fields-conditional.sql`;
  * `scripts/guardrail_pgtap_preambolo.py`: la soglia dei `throws_ok` senza discriminante da 110 a 109;
  * la doc di §10.5 (le pagine `manual/` di `catalogo`, `script/manual/fn_articolo_riga_contesto.md` e
    `fn_check_articolo_riga.md`, `dbops/manual/fn_non_editable_fields.md` e `lock_columns_conditional.md`,
    `guide/gestione-listini.md`, `dev/manual/modello-componenti-bom.md`), con le tre pagine cancellate;
  * questo brief e `brief-db-articoli-obsoleto-dal` (il rimando di D-C).
* ⚠️ Nel working tree ci sono file di altre sessioni (fra cui i `fk_index_policy_*.csv` cancellati, schede auto-generate e
  pagine `dbops/manual/`): non entrano nel commit del giro.
* **Doc auto-generata:** alla prossima rigenerazione nasce la scheda di `catalogo.fn_articolo_padre_di_distinta_da_oggi`
  e spariscono quelle dei tre oggetti ritirati. Fino ad allora tre pagine `manual/` hanno un link a una scheda che non
  c'è ancora.
* **Il giro 1 è chiuso** per la parte DB. Restano BE8-BE12 al team BE e le scelte di §10.3 da guardare.
* **Committato** da Tid il 2026-11-09: `eef662024d`.

## 11. Giro 1-bis — il BB della distinta alla data: il censimento e il piano, 2026-11-09

Il giro chiude R2 (Q8). Questa sezione è stata scritta **in sola lettura**, prima del via: nessun changeSet, nessun pgTAP.
I corpi vengono da `pg_get_functiondef` e `pg_get_viewdef` su dbdev, letti il 2026-11-09, dopo l'apply del giro 1.

### 11.1 Chi legge la distinta, e che cosa chiede

R2 elencava i 5 `*_riga_componenti_init`, i 5 `*_preview`, i due guard di coerenza e la vista. Il censimento ha preso
tutte le funzioni e le viste che nominano `catalogo.articoli_componenti`. Le domande che fanno sono di quattro forme, e
solo la prima è R2:

| Forma | Chi la fa | Filtro oggi | Nel giro |
| --- | --- | --- | --- |
| **L'insieme dei legami di un padre alla data D** | `vendite.fn_{preventivo,ordine,ddt,contratto}_riga_componenti_init`, `fn_offerta_eccezione_componenti_init` e i cinque `_preview` gemelli | `prodotto_id = padre AND COALESCE(attivo, TRUE) AND validita @> D`, ricopiato dieci volte | ✅ chiamano il BB |
| | `catalogo.vw_articoli_dettaglio.has_componenti_alla_data` | `EXISTS (… validita @> fn_data_operativa() AND attivo)`: è il BB a oggi | ✅ `EXISTS` sul BB, cronometrata |
| | ⚠️ BE `vendite/db/listini_repository.py` `list_bundle_preview` (`:1238`) | lo stesso filtro, scritto in Python | ➡️ BE13 (§11.6) |
| **Questo legame sta nella distinta del padre alla data D?** | `script.trgfn_componenti_guard_coerenza_bom`, sulle cinque tabelle `*_righe_componenti` dei documenti | il guard 2 legge il legame per `id` e `prodotto_id`; il guard 4 chiede `validita @> D` e **non guarda `attivo`** | ✅ il guard 4 chiede il BB (Q16) |
| **Il kit ha una distinta?** (senza data) | `script.fn_check_articolo_riga_su_contesto`, motivo `KIT_SENZA_COMPONENTI`, scritto due volte nello stesso corpo | `COALESCE(attivo, TRUE)`, nessuna validità | Q15 |
| | `catalogo.trgfn_articoli_guard_iva_bom_attiva` | solo `attivo` | ⛔ giro 3 (D4) |
| **Altro** (non è la distinta del catalogo alla data) | `fn_espandi_listino_versione`, `fn_contratto_kit_componenti`, `fn_documento_righe_preview`: leggono la distinta **del listino** o del documento e vanno sul legame solo per gli attributi. `fn_clona_versione_listino`: sovrapposizione del legame con il periodo della versione. `trgfn_listini_righe_comp_guard_coerenza_bom`: il periodo sta alla FK temporale. `trgfn_componenti_check_prezzo_obbligatorio`, `…_guard_obbligatorio`: leggono `obbligatorio` per `id`. I tre predicati di catalogo, il trigger d'immutabilità e il guard del legame | — | restano |

Fatti emersi:

* **Il guard dei documenti non guarda `attivo`.** Un componente di documento può puntare un legame spento, mentre gli
  init non lo scriverebbero mai. È una seconda risposta alla stessa domanda, e diverge già.
* **Rami irraggiungibili.** `COALESCE(ac.attivo, TRUE)` nei dieci init e preview (`attivo` è NOT NULL). Lo skip del guard
  4 con `v_data_rif IS NULL`: la colonna data delle cinque testate (`data`, e `validita_dal` per l'offerta) è NOT NULL.
  Si tolgono nello stesso giro, perché il giro apre quegli oggetti (§2.4).
* **Il futuro consumatore.** `analisi-simmetria-ordini-acquisto` (D-9, chiusa) prevede in `acquisti` i gemelli di
  `fn_ordine_riga_componenti_init` e `_preview`. Con il BB nascono senza copiare il filtro.
* **Fuori perimetro**, come osservazione: i cinque init sono gemelli interi, non solo nel filtro (il commento nel corpo
  lo dice: «Gemello di `fn_contratto_riga_componenti_init`»). Unirli è un altro tema. Il giro tocca solo il filtro.

### 11.2 Il BB

`catalogo.fn_distinta_alla_data(p_prodotto_id, p_data) RETURNS TABLE(id, componente_id, coeff_qta, obbligatorio,
esposizione_in_fattura)`, `LANGUAGE sql STABLE`, `BEGIN ATOMIC` (le dipendenze stanno in `pg_depend`, come i tre predicati
di catalogo). Risponde: i legami **attivi** del padre la cui `validita` contiene `p_data`.

* Con `p_data` NULL **non** risponde «la distinta di oggi»: risponde zero righe. Chi vuole oggi passa
  `fn_data_operativa()`, come la vista. Un NULL che vale «oggi» renderebbe la data implicita (Regola zero: un parametro
  non è un filtro nascosto).
* ⚠️ **Non `SETOF catalogo.articoli_componenti`**, come proposto nel censimento. Provato sullo scratch in `BEGIN …
  ROLLBACK`: una `BEGIN ATOMIC` che restituisce la riga della tabella muore («troppe poche colonne») appena la tabella
  prende una colonna. Con le colonne nominate l'`ADD COLUMN` non la tocca. Le colonne sono quelle di struttura che i
  chiamanti leggono; il resto si legge per `id`.
* **Espansione nel chiamante, provata:** con la data passata come colonna, parametro o chiamata diretta, `EXPLAIN` non ha
  `Function Scan`. Con la data in una sottoquery (`(SELECT script.fn_data_operativa())`) invece no.
* **La vista, cronometrata su dbdev** (811 articoli, letto il 2026-11-09, in `BEGIN … ROLLBACK`). Con
  `fn_data_operativa()` passata direttamente, la colonna costava circa 3,4 volte tanto (6,7 ms contro 2,0 ms), perché il
  giorno aziendale si ricalcola per ogni legame. Con il giorno calcolato una volta, in una sottoquery recintata
  (`CROSS JOIN (SELECT script.fn_data_operativa() AS data_operativa OFFSET 0) oggi`), il tempo torna quello di prima
  (2,0 ms). Stessi valori su tutti gli articoli.
* Il predicato «da oggi in poi» per i guard **c'è già**: `fn_articolo_padre_di_distinta_da_oggi` (giro 1). Il giro
  1-bis non ne fa un secondo.

### 11.3 Che cosa cambia nei chiamanti

| Oggetto | Cambio | Comportamento |
| --- | --- | --- |
| 5 init + 5 preview | `FROM catalogo.fn_distinta_alla_data(padre, p_data_riferimento) ac JOIN catalogo.articoli a …` al posto del filtro; via il `COALESCE` | Uguale |
| `vw_articoli_dettaglio` | `has_componenti_alla_data` = `EXISTS (SELECT 1 FROM catalogo.fn_distinta_alla_data(a.id, oggi.data_operativa))`, con il giorno in una sottoquery recintata (§11.2) | Uguale; la vista oggi non ha opzioni (`reloptions` vuoto, letto il 2026-11-09): il `CREATE OR REPLACE` non ne perde |
| `script.trgfn_componenti_guard_coerenza_bom` | Il guard 4 chiede se il legame è nell'insieme del BB alla data della testata; via lo skip su data NULL | **Cambia** (Q16): un legame spento è rifiutato dal guard con `E_DOC_COMPONENTE_BOM_NON_VALIDA`. Prima lo rifiutava comunque, a fine istruzione, il vincolo differito generato `…_a10_articoli_componenti_…` (`dbops.trgfn_child_requires_active_parent`, `E_ATTIVO_PADRE_NON_ATTIVO`): il rifiuto non è nuovo, lo sono il momento e il codice |
| `script.fn_check_articolo_riga_su_contesto` | Solo se Q15 dice di cambiare la finestra; le due copie del motivo nello stesso corpo diventano una | Secondo Q15 |

### 11.4 Le decisioni di Tid

| # | Domanda | Proposta |
| --- | --- | --- |
| Q15 ✅ | Il motivo `KIT_SENZA_COMPONENTI` della check guarda «almeno un legame attivo, in qualunque periodo». Un kit con la distinta tutta chiusa nel passato passa la check, e poi l'init lo rifiuta a ogni data da oggi in poi. La check non ha la data del documento. Che finestra prende? | **«Da oggi in poi»** (`fn_articolo_padre_di_distinta_da_oggi`), la stessa del guard flags (D9, «una finestra sola per i guard»). Il caso del documento con data passata resta all'init, alla sua data, come dice già il commento del corpo. ⚠️ Un kit con la sola distinta passata non si propone più nel picker — **✅ Tid, 2026-11-09: come da proposta** |
| Q16 ✅ | Il guard dei componenti di documento deve rifiutare un legame spento? | **Sì.** «Il legame sta nella distinta alla data» è una regola sola, e la risponde il BB. Oggi un legame citato da un documento non si spegne (`trgfn_prevent_deactivate_if_children`), quindi le righe esistenti non sono toccate. Il guard scatta su ogni UPDATE della riga componente: va provato che un UPDATE di prezzo su una riga valida passi — **✅ Tid, 2026-11-09: come da proposta** |
| Q17 ✅ | Il guard 1 di `trgfn_componenti_guard_coerenza_bom` («la riga padre è un composito», `E_DOC_RIGA_NON_COMPOSITO`). R3 lo contava come copia della regola del padre | **Resta.** Giudica la riga del **documento**, non la testata della distinta: dopo il giro 1 la regola del padre della distinta ha la sua sede in `fn_articolo_riga_contesto`. Sono due domande diverse. R3 si corregge così — **✅ Tid, 2026-11-09: come da proposta** |
| Q18 ✅ | ChangeSet: uno per documento (init e preview insieme) o uno per funzione? | **Uno per documento**: è lo stesso cambio sullo stesso documento, e il rollback rimette i due corpi insieme. Totale in §11.5 — **✅ Tid, 2026-11-09: come da proposta** |

### 11.5 I changeSet

Nove (Q15 cambia la finestra). Il BB prende il numero più basso, perché la vista lo chiama al CREATE.

| # | Fase / schema | Che cosa |
| --- | --- | --- |
| 1 | `20_code/catalogo` | `fn_distinta_alla_data`; COMMENT in un secondo `- sql:` (pgjdbc e `BEGIN ATOMIC`) |
| 2-6 | `20_code/vendite` | Preventivo, ordine, DDT, contratto, eccezione d'offerta: init e preview |
| 7 | `20_code/script` | `trgfn_componenti_guard_coerenza_bom` (Q16) |
| 8 | `20_code/catalogo` | `vw_articoli_dettaglio.has_componenti_alla_data` |
| 9 | `20_code/script` | `fn_check_articolo_riga_su_contesto` (solo con Q15) |

Corpi di partenza da `pg_get_functiondef`/`pg_get_viewdef` del giorno, `%TYPE` in firma e `DECLARE`, rollback = corpi di
prima. Prima di riscrivere `vw_articoli_dettaglio` si confronta il suo corpo col brief vicino
`brief-db-addebito-trasporto-ordine`, che tocca la stessa vista (`causale_onere_id`, `e_onere`).

**pgTAP previsti:**

* nuovo `catalogo/test-distinta-alla-data-v1`: un kit costruito con legami passati, in vigore, futuri e spenti; il BB a
  più date (compresi i due estremi chiusi della `validita`) e con `p_data` NULL; init e preview di un documento seguono
  il BB; il guard rifiuta il legame spento e lascia passare l'UPDATE di prezzo; Q15, se cambia;
* un presidio statico: nessun corpo di `vendite`/`script` ripete `articoli_componenti` con `validita @>` su
  `prodotto_id`. Così la copia non rientra;
* i pgTAP esistenti che toccano init, preview, guard e vista, con e senza l'SQL estratto in testa (come al §10.4).

### 11.6 Ricadute su BE e FE

| # | Che cosa |
| --- | --- |
| BE13 ✅ (2026-11-09) | `listini_repository.list_bundle_preview` (`:1238`) ricopia il filtro della distinta alla data: legge da `catalogo.fn_distinta_alla_data(%s, %s)` e tiene il `LEFT JOIN` sui prezzi del listino |
| BE14 ✅ (2026-11-09) | Un kit con la sola distinta passata non compare più fra gli articoli ammessi (Q15). Il FE non ha niente da fare: legge i motivi dalla check |
| BE15 ✅ (2026-11-09) | Il messaggio di `E_ARTICOLO_KIT_SENZA_COMPONENTI` cambia («non ha componenti in vigore da oggi in poi»): va allineata la frase di riserva in `backend/apps/core/services/error_messages_fallback.py:82`, e l'i18n se la ripete |

### 11.7 Che cosa è scritto (2026-11-09)

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/catalogo/20261110-85` | `catalogo.fn_distinta_alla_data`, il BB (§11.2) |
| `20_code/vendite/20261110-86` … `-90` | Preventivo, ordine, DDT, contratto, eccezione d'offerta: init e preview leggono la distinta dal BB. Cambia solo il `FROM`: via il filtro e il `COALESCE` su `attivo` |
| `20_code/script/20261110-91` | `trgfn_componenti_guard_coerenza_bom`: il guard 4 chiede il BB (Q16); via lo skip con la data NULL; COMMENT, punto (4) |
| `20_code/catalogo/20261110-92` | `vw_articoli_dettaglio.has_componenti_alla_data` dal BB, col giorno calcolato una volta (§11.2). Colonne, ordine e COMMENT invariati |
| `20_code/script/20261110-93` | `fn_check_articolo_riga_su_contesto`: `KIT_SENZA_COMPONENTI` con `fn_articolo_padre_di_distinta_da_oggi` (Q15), un motivo costruito una volta e aggiunto dai due rami. COMMENT di questa funzione e di `fn_check_articolo_riga` riscritti secondo §5d |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_ARTICOLO_KIT_SENZA_COMPONENTI`: messaggio, causa e nota sulla finestra nuova. `E_DOC_COMPONENTE_BOM_NON_VALIDA`: causa e nota col legame spento |

I corpi di partenza vengono da `pg_get_functiondef` e `pg_get_viewdef` (`search_path = pg_catalog`) su dbdev, letti il
2026-11-09. Un generatore li ha cambiati con sostituzioni che dovevano trovare **esattamente un** punto, altrimenti si
fermava. Il rollback è il corpo di prima, con i COMMENT di prima dove cambiano.

**Residuo, non toccato:** negli init restano `COALESCE(v_is_composito, FALSE)` e `COALESCE(v_comp.obbligatorio, TRUE)`
su valori che non possono essere NULL, e i marcatori `rev …` nei commenti dei corpi. Va col giro 5 (§2.4). Nella check
anche il motivo `SOLO_COMPONENTE` è scritto in più rami: anche questo è giro 5.

### 11.8 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di numero, `BEGIN … ROLLBACK`)

* **Estratto e preCondition.** I nove changeSet, con le `preConditions` trasformate in asserzioni, passano in una
  transazione.
* **Il pgTAP nuovo** `catalogo/test-distinta-alla-data-v1` (17 test): verde con l'estratto. Con il solo BB e i chiamanti
  di prima sono rossi esattamente i tre test dei cambi (11 legame spento, 14 kit con la sola distinta passata, 17 il
  presidio). Gli altri sono uguali per costruzione. Il presidio 17, sullo scratch di oggi, trova le undici copie: i dieci
  init e preview e la vista.
* **I pgTAP che toccano gli oggetti del giro** (55 file: init, preview, guard, check, picker, vista, componenti delle
  righe) con e senza l'estratto: stesse risposte, a parte il file nuovo. L'unico rosso,
  `vendite/test-fn-contratto-righe-preview-nuovi-campi-v1` test 2, è uguale senza l'estratto ed è già nelle due
  baseline (`ASSERZIONE`).
* **Cambiato:** `catalogo/test-articoli-ammessi-picker-v1` test 24 cercava la frase vecchia del messaggio del kit; ora
  cerca quella nuova. Era verde nella prova solo perché l'estratto non ricarica i CSV: provato con la riga del messaggio
  aggiornata a mano nella stessa transazione, 26/26.
* **Guardrail:** `run_on_change`, `precondition_seed`, `ddl_su_trigger_automazione`, `grant_ruolo_batch`,
  `sql_letterali`, `timestamp_senza_fuso` verdi; `pgtap_preambolo` segnala solo un file dell'altra sessione
  (`dbops/test-presidi-codici-corpo-leggibile-v1`). La soglia dei `throws_ok` senza discriminante resta 109: il test nuovo
  usa `throws_like`.
* **Non provato:** la corsa come app (la fa Tid dopo l'apply), il caricamento dei CSV e il migrate vero (pgjdbc). Il
  COMMENT del BB è in un `- sql:` separato dalla `BEGIN ATOMIC`, come vuole pgjdbc.

### 11.9 Doc e chiusura

* **Doc:** nuova `catalogo/manual/fn_distinta_alla_data.md`. Aggiornate `catalogo/manual/vw_articoli_dettaglio.md` (tolto
  il punto «riscrive la regola a mano») e `fn_articolo_padre_di_distinta_da_oggi.md` (il terzo lettore), poi
  `script/manual/trgfn_componenti_guard_coerenza_bom.md`, `fn_check_articolo_riga.md` e
  `fn_check_articolo_riga_su_contesto.md`. Nelle sei pagine `vendite/manual/` degli init e del preview del preventivo è
  cambiata solo la frase sul filtro: sono in formato vecchio, senza data, e restano così. La scheda auto-generata del BB
  nasce alla rigenerazione della doc dopo l'apply: fino ad allora i link `/dbzero/catalogo/funzioni/fn_distinta_alla_data`
  non hanno una pagina.
* **Da committare** (il giro 1-bis):
  * `20_code/catalogo/20261110-85`, `-92`; `20_code/vendite/20261110-86` … `-90`; `20_code/script/20261110-91`, `-93`;
  * `80_data/sql/config/codici_errore.csv` e `messaggi_errore.csv` (solo le quattro righe di questo giro: i due file hanno
    anche modifiche dell'altra sessione);
  * i pgTAP `catalogo/test-distinta-alla-data-v1.sql` (nuovo) e `catalogo/test-articoli-ammessi-picker-v1.sql`;
  * la doc del punto sopra e questo brief.
* **Numeri:** mentre il giro si scriveva, un file dell'altra sessione aveva anche lui il `-85`; è stato spostato al `-99`,
  poi Tid l'ha rinumerato `-94`. Nessun numero del giorno `20261110` è doppio.
* **Applicato** da Tid su dbdev e sullo scratch, pgTAP come app verdi (2026-11-09). **Committato** lo stesso giorno, con le
  schede auto-generate rigenerate dei soli oggetti del giro; delle modifiche dell'altra sessione ai due CSV non è entrato
  niente.

## 12. Verifica di coerenza con guide e documenti, 2026-11-09

Richiesta di Tid dopo il giro 1-bis: c'è qualche guida o documento che contraddice i giri 1 e 1-bis, o il giro 2 che
viene? Ho cercato le regole una per una (non le parole), in `guide/`, `dev/manual/`, `backend/*/manual/`,
`dev/frontend/` e nelle pagine `manual/` di `vendite`, `script`, `magazzino` e `acquisti`. Ho escluso `work-done/`, che è
storia.

**Contraddizioni vere, corrette nello stesso giorno:**

* `dbzero/script/manual/trgfn_componenti_guard_obbligatorio.md`: per togliere un componente obbligatorio diceva di
  «disattivare la riga BoM o cambiarne il flag `obbligatorio`». Il database rifiuta tutte e due le cose: `obbligatorio` è
  un campo di struttura, e un legame citato da un documento non si spegne. Ora dice «chiudi il legame e inseriscine uno
  nuovo».
* `guide/gestione-ordini.md`, `gestione-ddt.md`, `gestione-preventivi.md`, `gestione-offerte-commerciali.md`: «kit senza
  componenti» ora è «kit senza componenti in vigore da oggi in poi» (Q15). Prima non era falso, ma era impreciso.

**Contraddizioni nella doc del backend** (`docs/it/backend/`, sede del team BE): `api_catalogo.md` su
`data_min_chiusura`, sulle regole della fine (§4.3) e sul `DELETE` (§4.4). Sono aggiunte a BE9 e BE11 (§5).

**Nessuna contraddizione** con:

* `linee-guida-sql.md` §7b (validità, `'[]'`), `dev/manual/modello-componenti-bom.md` (già riallineato nel giro 1) e
  `guide/gestione-listini.md` §5.3;
* il fermo dei temi trasversali sui documenti di vendita (`.codex/PROJECT_CONTEXT.md`): il giro 1-bis tocca tutti i
  documenti, ma lo fa con un building block comune, ed è il caso ammesso. Tid ha dato l'ok in Q8.

**Per il giro 2** (le unità): nessuna guida promette il «fattore 1 quando manca la conversione». Però le guide che
descrivono la quantità operativa (`gestione-preventivi.md` §2.2, `gestione-contratti.md`, `gestione-ordini.md`,
`gestione-ddt.md`) dicono solo «fattore fotografato sulla riga». Col giro 2 vanno completate con tre regole: il fattore
viene dalla mappatura dell'articolo o dalla conversione generale, alla data del documento, e senza nessuna delle due la
riga si rifiuta (Q7, Q13). `api_catalogo.md` documenta il lookup dei modi di arrotondamento, che Q4 ritira: è BE16.

## 13. Giro 2 — le unità di misura, 2026-11-09

Via di Tid il 2026-11-09, coi numeri dal `20261111-01`. Difetti del giro: D2 (Q7), D3 (Q4), D6, D8, D12, D13 (Q3), D14,
D15, D17, D22 (Q13); in più D7, che era del giro 3 ma vive nella funzione che questo giro apre, e D23, nuovo (§13.2).

### 13.1 Che cosa è scritto

| ChangeSet | Che cosa |
| --- | --- |
| `20_code/catalogo/20261111-01` | `trgfn_articoli_seed_uom_base`: la riga base nasce attiva o spenta come l'articolo (D7), senza `ON CONFLICT` (nominava il vincolo che `-02` sostituisce) |
| `00_schema/catalogo/20261111-02` | `articoli_uom_operativa`: `UNIQUE (articolo_id, uom_id, validita WITHOUT OVERLAPS)` al posto di quello senza tempo (D13); `chk_articoli_uom_operativa_base_fissa`, cioè riga base con fattore 1 e senza date (D12); ritirate `rounding_mode` e `require_lot` (D3, Q4); COMMENT di tabella e colonne |
| `20_code/catalogo/20261111-03` | `vw_articoli_uom_operativa_dettaglio` ricreata senza le due colonne, col GRANT e un COMMENT |
| `20_code/catalogo/20261111-04` | `trgfn_articoli_uom_operativa_guard_base` (nuovo) e il suo trigger: la riga base non cambia unità né articolo, non smette di essere la base, non si toglie, e non se ne crea una su un'altra unità (`E_UOM_RIGA_BASE_IMMUTABILE`). La cancellazione dell'articolo la porta via (D12) |
| `20_code/catalogo/20261111-05` | `fn_uom_operativa_alla_data` (nuovo, BB): la mappatura di un'unità per un articolo alla data, col fattore e le regole della quantità |
| `20_code/catalogo/20261111-06` | `fn_get_uom_factor(articolo, unità, data)`: base, mappatura alla data, conversione generale nei due versi; NULL senza data. Firma nuova (R1, D22) |
| `20_code/script/20261111-07` | `trgfn_qta_from_operativa`: fattore della riga, altrimenti `fn_get_uom_factor` alla data del documento; senza fattore `E_UOM_MISSING` (D2, Q7); `max_decimals` applicato (`E_QTA_OPERATIVA_DECIMALI`, D3); un UPDATE che cambia solo l'unità rilegge il fattore (D8) |
| `20_code/vendite/20261111-08` | I sei montaggi del trigger prendono la testata e la sua data (argomenti [2]-[4]) |
| `00_schema/vendite/20261111-09` | `factor_to_base` di `ordini_righe`, `ddt_righe`, `resi_righe` senza `DEFAULT 1` (D23) |
| `00_schema/catalogo/20261111-10` | `unita_misura_conversioni`: `ex_unita_misura_conversioni_coppia_no_overlap`, una conversione per coppia non orientata e periodo, al posto di `uq_uom_conv_no_overlap` (D14) |
| `20_code/catalogo/20261111-11` | `trgfn_uom_conversioni_guard_tipo`: `E_UOM_CONVERSIONE_TIPO_DIVERSO`, il nome della funzione nel log, le unità lette `FOR SHARE` (D6, D15) |
| `20_code/catalogo/20261111-12` | `trgfn_unita_misura_guard_tipo` (nuovo) al posto di `trgfn_unita_misura_guard_tipo_update`, ritirato col suo trigger: `E_UOM_TIPO_IN_USO` (D6) e `E_UOM_CALENDARIO_NON_TEMPO` (D17) |
| `80_data/changelog/20261111-13` | Ritirato il parametro `CATALOGO_UOM_OP_DEFAULT_ROUNDING_MODE` (anche da `parameters.csv`) |
| `codici_errore.csv`, `messaggi_errore.csv` | `E_UOM_MISSING` riscritto («l'unità … non si converte nell'unità base … alla data …»); nuovi `E_QTA_OPERATIVA_DECIMALI`, `E_UOM_RIGA_BASE_IMMUTABILE`, `E_UOM_CONVERSIONE_TIPO_DIVERSO`, `E_UOM_TIPO_IN_USO`, `E_UOM_CALENDARIO_NON_TEMPO` (id 1466-1470) |

Corpi di partenza da `pg_get_functiondef`, `pg_get_viewdef` (`search_path = pg_catalog`) e `pg_get_triggerdef` su dbdev,
2026-11-09; rollback = gli oggetti di prima. I COMMENT nuovi o riscritti seguono §5d.

### 13.2 Fatti emersi

* **D23, nuovo: il `DEFAULT 1` del fattore.** Su `ordini_righe`, `ddt_righe` e `resi_righe` `factor_to_base` è NOT NULL
  con `DEFAULT 1`. Il default si applica prima dei trigger BEFORE: una riga inserita senza fattore arrivava al trigger
  con 1 già scritto, e la mappatura non si leggeva mai. È la regola di D2 («quando non so, 1») su altre tre tabelle. Il
  NOT NULL resta, perché lo soddisfa il trigger.
* **La data del documento.** Il trigger è montato su sei tabelle di righe, ognuna con la sua testata. In un BEFORE INSERT
  la riga non esiste ancora, quindi i risolutori per id (`script.fn_get_testata_id_di_riga`) non servono. Il montaggio
  dichiara tabella, colonna FK e colonna data, come fa il guard dei componenti di documento. L'offerta usa la decorrenza
  (`validita_dal`).
* **Le commesse non calcolano la quantità**: `commesse_attivita` la riceve dal documento sorgente, col suo fattore. Non
  c'è un trigger da cambiare, e restano fuori dal giro.
* **Il backend ha una copia della regola «unità ammessa per l'articolo»** (`listini_repository.py:968`: base o mappatura,
  senza le conversioni generali). È BE17.
* **`fn_get_uom_factor` aveva solo chiamanti BE** (due wrapper senza chiamanti): con la firma nuova smettono di
  funzionare. BE2 li ritira.

### 13.3 Le scelte dentro il giro (da guardare, Tid)

1. **`E_UOM_MISSING` riusato (Q7), con la frase riscritta.** Il suo secondo uso nel trigger non poteva scattare
   (`articolo_id` e `catalogo.articoli.uom_id` sono NOT NULL), quindi il codice ora ha un significato solo: «manca la
   conversione». La frase vecchia era tecnica («Unità misura mancante.(%s %s)»).
2. **D7 anticipato dal giro 3.** La funzione si apriva comunque per D13. Il fix è una riga.
3. **La riga base vale sempre**: il CHECK vieta anche le date sulla riga base, non solo il fattore diverso da 1. Una
   base con validità lascerebbe l'articolo senza base fuori dal periodo.
4. **Un guard solo per la tipologia di un'unità** (in uso nelle conversioni; TEMPO se si conta dal calendario): sono
   regole della stessa colonna. Per questo cambia nome (`_guard_tipo` invece di `_guard_tipo_update`).
5. **Il fattore scritto sulla riga si rispetta** anche all'INSERT: è la fotografia che i documenti derivati copiano dalla
   sorgente (ordine da preventivo, bolla da ordine). Il trigger non lo ricontrolla contro la mappatura.
6. **La conversione generale spenta occupa il periodo**: l'EXCLUDE non filtra `attivo`, come il vincolo che sostituisce.
7. **Testata che non si vede: il trigger non decide.** Il trigger gira prima della RLS e legge la testata con i diritti di
   chi scrive. Se non la vede (documento di un altro perimetro) o non c'è, la data è NULL e il trigger esce senza
   calcolare: rifiutano la RLS o la FK, che vengono dopo. La prima versione sollevava `E_UOM_MISSING` («… alla data —»),
   e i sei `rls/test-rls-*-satelliti` lo hanno visto (§13.4).
8. **L'unità base vale 1 anche senza data**: il suo fattore non dipende dal giorno. Per le altre unità
   `fn_get_uom_factor` senza data risponde NULL.

### 13.4 Le prove (scratch `zeroerp_ruoli`, come owner, SQL estratto dagli YAML in ordine di numero, `BEGIN … ROLLBACK`)

* **Estratto e preCondition.** I tredici changeSet, con le `preConditions` come asserzioni, passano in una transazione.
  Nella prova sono state aggiunte a mano anche le righe nuove dei CSV dei codici, che nel migrate vero carica il mirror.
* **Il pgTAP nuovo** `catalogo/test-uom-fattore-e-regole-v1` (31 test): verde con l'estratto. Senza, la fixture muore al
  primo passo, sulla mappatura versionata che il vincolo di prima rifiuta (D13).
* **I pgTAP che toccano unità e quantità** (221 file) con e senza l'estratto. La prima corsa ha trovato:
  * i sei `rls/test-rls-*-satelliti`: la scrittura su un documento altrui si fermava sul trigger della quantità invece
    che sulla RLS. Corretto nel trigger (§13.3, scelta 7): verdi;
  * cambiati nel giro perché asserivano la regola di prima: `catalogo/test-fn-get-uom` (la firma con la data),
    `catalogo/test-articoli-vincoli-note-uom-overlap` 17-18 (il doppione è 23P01 del vincolo temporale; la seconda riga
    base la rifiuta il guard), `script/test-trgfn-guard-date-validita-v1` (le date stavano sulla riga base: ora su una
    mappatura costruita), `config/test-parameters-uom-defaults-cascade-v1` (la cascata degli override provata su
    `MAX_DECIMALS`, il parametro di `rounding_mode` è ritirato), `dbops/test-anti-overlap-enforcement-gate-v1` (i vincoli
    temporali nuovi);
  * seconda corsa, con le correzioni: rispetto alla corsa senza estratto cambiano solo i quattro file che provano le regole
    nuove (verdi con l'estratto, rossi o fermi senza). Tutti gli altri rossi sono uguali con e senza: quelli già noti
    alle baseline.
* **D15, a due sessioni.** Il guard nuovo non si può provare a due sessioni senza applicarlo, quindi si è provato il
  meccanismo su una riga vera di `catalogo.unita_misura`, sempre in `ROLLBACK`. Con un `UPDATE` della riga in volo, una
  lettura `FOR SHARE` aspetta (`lock_timeout` di 2 s scaduto: 2054 ms); nel verso opposto, lo stesso. Una lettura
  semplice, come quella del guard di prima, passa subito (38 ms).
* **Guardrail** verdi; `pgtap_preambolo` segnala solo un file dell'altra sessione.
* **Non provato:** la corsa come app, il caricamento dei CSV, il migrate vero (pgjdbc).
* **Dopo l'apply (Tid, 2026-11-09), come app:** `catalogo/test-articoli-vincoli-note-uom-overlap` arrivava a 20/20 e poi
  moriva nel cleanup in coda, una `DELETE` delle righe di unità operativa dell'articolo, riga base compresa, che il guard
  nuovo rifiuta. Nella prova come owner l'esito dei test non lo mostrava: il rosso era dopo l'ultimo `ok`. Tolta la `DELETE`,
  come quelle della distinta nel 2026-08: il file finisce in `ROLLBACK`, che toglie tutto. Nessun altro pgTAP cancella
  righe di unità operativa fuori da un'asserzione.
* **Dopo l'apply, su dbdev:** `catalogo/test-fn-get-uom` sceglieva tre unità fra quelle esistenti e ci scriveva delle
  conversioni; su dbdev fra due di loro c'è già una conversione nel verso opposto, che il vincolo nuovo (una per coppia)
  non lascia affiancare. Sullo scratch era verde perché la conversione non c'è: misurava la macchina. Ora il test
  costruisce le sue unità. Verde su dbdev e scratch; gli altri due pgTAP che scrivono conversioni le costruiscono già.
* **Chiusura:** Tid, 2026-11-09 — migrate applicato su dbdev e scratch, pgTAP come app verdi.

### 13.5 Ricadute su BE e FE

| # | Che cosa |
| --- | --- |
| BE1-BE4 ✅ (2026-11-09, §13.7; BE4 resta aperta per D19, giro 3) | Come in §5, ora sul giro applicato. BE4: i sei codici di §13.1 nella mappa degli errori generata e nell'i18n; `E_UOM_MISSING` ha una frase nuova |
| BE16 ✅ (2026-11-09) | `rounding_mode` e `require_lot` non ci sono più: il form e il servizio delle unità operative (`ArticoloUomForm.vue`, `RoundingModeSelect.vue`, `catalogo_service`, il lookup `rounding-modes` di `api_catalogo.md` §2.3) non le scrivono e non le leggono più. Fino ad allora un salvataggio che le nomina fallisce |
| BE17 ✅ (2026-11-09) | `listini_repository.py:968` (`uom_compatibile`) ricopia «l'unità vale per l'articolo» senza le conversioni generali: legge `catalogo.fn_get_uom_factor(articolo, unità, data) IS NOT NULL` |
| BE18 ✅ (2026-11-09) | Le mappature si versionano: «cambiare il fattore» di un'unità operativa diventa «chiudi e inserisci», e due periodi sovrapposti li rifiuta `uq_articoli_uom_operativa_no_overlap` (23P01). Anche una conversione generale nei due versi sovrapposta (`ex_unita_misura_conversioni_coppia_no_overlap`, 23P01): il servizio mappa i due vincoli a un messaggio |

### 13.6 Chiusura

* ⚠️ **Prima dell'apply su dbdev**: la riga base dell'articolo di prova `ART_TEST_BASE` (`catalogo.articoli_uom_operativa`
  id 9001) ha `valido_dal = 2026-01-01`, e `chk_articoli_uom_operativa_base_fissa` farebbe fallire `-02`. Va corretta a
  mano (`valido_dal` a NULL). Sullo scratch non ci sono righe così (letto il 2026-11-09). Come fatto datato: su dbdev 20
  articoli di prova non hanno nessuna riga base; il fattore della loro unità base resta 1, e il guard nuovo non lo
  cambia.
* **Doc** (scritta il 2026-11-09): nuove `catalogo/manual/fn_uom_operativa_alla_data.md`,
  `trgfn_articoli_uom_operativa_guard_base.md`, `trgfn_unita_misura_guard_tipo.md`; cancellata
  `trgfn_unita_misura_guard_tipo_update.md`; aggiornate in `catalogo/manual/` `fn_get_uom_factor`, `fn_get_uom_base`,
  `articoli_uom_operativa`, `unita_misura_conversioni`, `unita_misura`, `uom_tipi`, `trgfn_uom_conversioni_guard_tipo`,
  `trgfn_articoli_seed_uom_base`, `vw_articoli_uom_operativa_dettaglio`, `articoli`; riscritta allo standard
  `script/manual/trgfn_qta_from_operativa.md`; nelle guide `gestione-preventivi`, `gestione-ordini`, `gestione-ddt`,
  `gestione-contratti` la regola del fattore. Le schede auto-generate dei tre oggetti nuovi nascono dopo l'apply.
  ⚠️ Trovata e lasciata: `guide/gestione-contratti.md` (verso la riga 141) dice ancora che con la fonte «derivata dai
  componenti» la quantità la scrive il sistema, ma quella fonte è ritirata dal 2026-10-21. Va col giro 5.
* **Committato** (2026-11-09, su richiesta di Tid): i tredici changeSet; `codici_errore.csv`, `messaggi_errore.csv` e `parameters.csv` (solo le righe di
  questo giro); i pgTAP `catalogo/test-uom-fattore-e-regole-v1.sql` (nuovo), `catalogo/test-fn-get-uom.sql`,
  `config/test-parameters-uom-defaults-cascade-v1.sql`, `dbops/test-anti-overlap-enforcement-gate-v1.sql`,
  `catalogo/test-articoli-vincoli-note-uom-overlap.sql`, `script/test-trgfn-guard-date-validita-v1.sql`; la doc del punto
  sopra; la verifica di coerenza di §12 con le sue correzioni;
  questo brief.

### 13.7 Giro BE del giro 2 (team BE, 2026-11-09, da committare su `dev/backend-tid`)

#### 13.7.1 Che cosa è fatto

| # | Che cosa |
| --- | --- |
| BE16 | `rounding_mode` e `require_lot` fuori da repository (scrittura e proiezione), service, schema OpenAPI e form. Ritirati il lookup `GET /catalogo/lookup/rounding-modes/` (view, rotta, `fn_list_uom_rounding_modes`, `_ROUNDING_MODE_*`), `lookupUomRoundingModes` e `RoundingModeSelect.vue` (file cancellato, nel piano approvato da Tid), le chiavi i18n e il parametro letto dal form. Una PATCH o una POST che li nomina è un 400. `api_catalogo.md` §2.3 e §3.2 riscritti |
| BE1 | `is_base` **non si scrive più**: fuori dalla whitelist di repository e service (400 se arriva). La riga base nasce con l'articolo e il guard rifiuta ogni altra strada, quindi offrirla voleva dire offrire solo un rifiuto. Ritirato il controllo parziale di `:844`; il CHECK `chk_articoli_uom_operativa_base_fissa` ha la sua frase (`_UOM_OPERATIVA_CHECK`). La DELETE della riga base riceve `E_UOM_RIGA_BASE_IMMUTABILE` dal DB, intatto fino al middleware |
| BE1, form | ⚠️ **Difetto trovato nel form**: un `watch` ricavava `is_base` dal fattore (`fattore 1 → base`). Un'unità con fattore 1 che base non è (una confezione da uno, un sinonimo) finiva marcata base, e col guard nuovo il salvataggio veniva rifiutato. Ritirato: il form mostra «Base» in sola lettura sulla riga base, e lì spegne fattore e date (il CHECK) |
| BE2 | Ritirati `get_uom_base` / `get_uom_factor` del repository: nessun chiamante, e il secondo chiamava la firma vecchia |
| BE3 | Verificato: nessun service delle righe azzera `factor_to_base` al cambio d'unità. `contratti_service` accetta `factor_to_base: null`, che il trigger ora riempie alla data (D8). Niente da ritirare |
| BE4 | Policy rigenerata (`genera_error_policies`: le sole sette voci dei giri, nessun codice del DB oltre git) e ripieghi senza `%s` per i sei codici di §13.1 e per `E_SOGGETTO_ID_FISCALE_IMMUTABILE`; `E_UOM_MISSING` riscritto. Il FE non ha i18n per codice: la frase arriva dal DB |
| BE17 | `get_articolo_uom_validation` legge `catalogo.fn_get_uom_factor(articolo, unità, data) IS NOT NULL` alla **decorrenza della versione** (`listini_versioni.valido_dal`, NOT NULL); il rifiuto accende `uom_id` |
| BE18 | `_UOM_OPERATIVA_UNIQUE` su `uq_articoli_uom_operativa_no_overlap` (frase «chiudere quella in vigore prima di aprirne una nuova», senza campo). Le conversioni passano dal BB `map_integrity_error` per nome (`ex_unita_misura_conversioni_coppia_no_overlap`, `chk_uom_conv_no_self`, le due FK col campo): via il riconoscimento dal testo («overlap», «foreign») e il ramo `E_GENERICO` della tipologia, che ora ha il suo codice |

#### 13.7.2 Le prove

* **Sul DB vero** (`ZEROERP_TEST_DB_E2E=1`, casi costruiti, transazione annullata):
  `catalogo/tests/db/test_vincoli_catalogo_db` da 3 a 8 test (mappatura doppia e versionata, chiudi e inserisci, riga base
  fissa, riga base che non si toglie, conversione nel verso opposto, tipologie diverse);
  `vendite/tests/db/test_listino_uom_compatibile_db` (nuovo, 4 test: base, nessuna conversione, conversione generale,
  mappatura chiusa prima della decorrenza: gli ultimi due sono i casi che la copia vecchia sbagliava).
* Test unitari: `test_catalogo_service` (rounding ritirati; 4 nuovi), `test_catalogo_api`, `test_listini_service`.
* **Suite backend intera sul DB vero** (7221 test): tre rossi, tutti fixture che scrivevano ciò che i giri 1 e 2 ora
  rifiutano, corretti nello stesso giro. `catalogo/tests/db/test_articoli_ammessi_db` 1 e 2 aprivano il picker della
  distinta su un padre non composito (BE12); il test 1 per di più leggeva «un articolo attivo qualunque», una popolazione:
  ora il padre composito si costruisce. `core/tests/db/test_date_validita_guard_comune_db` 7 metteva le date sulla riga
  base: ora su una mappatura costruita, come il pgTAP gemello. Rilanciati: verdi.
* `genera_error_policies --check` pulito, presidi delle policy verdi, ruff, mypy (0 rilievi), vitest 1104/1104, build FE.

#### 13.7.3 Domande per Tid — ✅ risposte il 2026-11-10 (Q19-Q21, §6): il lavoro è in §14

1. **Il fattore di una mappatura si cambia sul posto?** Il DB lo lascia fare (nessun lock su `factor_to_base` delle righe
   non base), e il form lo lascia modificabile. Col modello «chiudi e inserisci» (D13, Q3) il cambio sul posto riscrive il
   passato di `fn_uom_operativa_alla_data`. Se il fattore di una mappatura va fermato, serve il lock a DB (o la riga in
   `lock_columns_conditional`, con il suo guard): allora il form lo spegne da `non_editable_fields`, senza copia.
2. **BE17, la data.** La compatibilità della riga di listino si chiede alla decorrenza della versione. Una mappatura che
   comincia dopo la decorrenza, o che finisce durante la versione, non è vista: è il giorno da cui il prezzo vale. Se la
   regola deve essere «per tutto il periodo della versione», va scritta a DB.
3. **Fuori dal giro, da guardare:** `commesse_repository._map_pushable_row` mette `factor_to_base = 1` quando la riga
   sorgente lo ha NULL. Le colonne nullable sono quelle di `contratti_righe`, `preventivi_righe`,
   `offerte_commerciali_eccezioni`, e lì NULL vuol dire «quantità già nella base», quindi 1 è giusto. È però la forma di
   D2 («quando non so, 1») in un posto del backend, e `commesse_attivita.factor_to_base` ha ancora `DEFAULT 1` (la forma
   di D23). §13.2 tiene le commesse fuori dal giro: lo segnalo, non lo tocco.

## 14. Giro 2-bis — le tre decisioni del giro BE, 2026-11-10

Le tre domande di §13.7.3 hanno risposta (Q19-Q21, §6). Diventano D24-D26: lavoro **DB**, con le ricadute BE in §14.4.
Il giro aspetta il via di Tid e i suoi numeri.

### 14.1 D24 — Il fattore di una mappatura si cambia sul posto (Q19: bloccato)

* **Fatto.** `articoli_uom_operativa` non ha lock su `factor_to_base` delle righe non base: un UPDATE lo cambia, e
  `fn_uom_operativa_alla_data` / `fn_get_uom_factor` rispondono il valore nuovo **anche per le date passate**. Il modello
  di Q3 (versionata, chiudi e inserisci) ha già la strada per cambiare il fattore: la riga nuova.
* **Correzione.** Il fattore di una mappatura scritta non si cambia: `script.trgfn_lock_columns`, con un codice suo
  (proposta: `E_UOM_FATTORE_IMMUTABILE`, la frase dice «chiudere la mappatura e aprirne una nuova»). La riga base è già
  ferma dal CHECK `chk_articoli_uom_operativa_base_fissa`: il lock non la cambia.
* **Da guardare nella stessa colonna di ragionamento (proposta della sessione DB, poi Tid):**
  * **`uom_id`** oggi non è bloccato neppure lui: cambiare l'unità di una mappatura sul posto riscrive il passato come il
    fattore. Proposta: bloccato insieme, stesso codice o uno gemello.
  * **Le date.** `valido_al` resta modificabile, perché chiudere è la strada. Spostare `valido_dal`, o chiudere nel
    passato una mappatura già in vigore, riscrive il passato come il fattore: è la stessa domanda di Q1 per la distinta.
    Proposta: la stessa risposta di Q1.
* **Prova (pgTAP):** UPDATE del fattore su una mappatura costruita → il codice; chiudi e inserisci → passa; la riga base
  resta del CHECK.

### 14.2 D25 — L'unità della riga di listino deve valere per tutto il periodo della versione (Q20)

* **Fatto.** Oggi la regola sta solo nel backend (BE17, §13.7.1), alla **decorrenza** della versione: una mappatura che
  finisce durante la versione passa, e da quel giorno il listino dà un prezzo in un'unità che per l'articolo non si
  converte. Una regola del modello non sta nel backend.
* **Correzione.** Regola a DB: l'unità della riga è convertibile per l'articolo **in ogni giorno** del periodo della
  versione (`valido_dal` … `valido_al`; `valido_al` NULL vuol dire «senza fine»). «Convertibile» è quello che dice
  `catalogo.fn_get_uom_factor` (base, mappatura dell'articolo, conversione generale): la regola si scrive **sul BB del
  periodo**, non come copia — la sessione DB valuta se serve un BB «unità convertibile per tutto il periodo», da
  `fn_get_uom_factor` o accanto a lui (regola del 2: lo leggono il guard del listino e, oggi, il backend).
* **Tutte e due le direzioni (simmetria).** La regola si rompe da tre lati, e ognuno va presidiato:
  1. la riga di listino scritta o cambiata (il guard della riga);
  2. il periodo della versione allungato o riaperto (`valido_al` spostato o tolto);
  3. il catalogo che cambia sotto: una mappatura chiusa, una conversione generale chiusa o spenta, mentre un listino
     vivo la usa.
  Il terzo lato è il più facile da dimenticare: va deciso se rifiutare la chiusura o no, e la sessione DB lo propone a
  Tid con le alternative.
* **Prova (pgTAP):** i tre lati, con articolo, unità, mappature e versione costruiti; versione senza fine; unità base
  sempre valida.

### 14.3 D26 — Le commesse: il fattore 1 per difetto (Q21)

* **Fatto.** `commesse_attivita.factor_to_base` ha `DEFAULT 1`: la forma di D23, che il giro 2 ha tolto da `ordini_righe`,
  `ddt_righe` e `resi_righe`. In più il backend (`vendite/db/commesse_repository.py`, `_map_pushable_row`) scrive 1 quando
  la riga sorgente ha il fattore NULL. Oggi è giusto, perché NULL sulla sorgente vuol dire «quantità già nella base»; ma
  se arriva una riga senza fattore in un'unità che base non è, l'1 la fa passare come se lo fosse (3 cartoni → 3 pezzi),
  senza rifiuto. È D2 («quando non so, 1»).
* **Correzione (DB).** Via il `DEFAULT 1`. La regola «senza fattore la quantità è nella base» si scrive a DB, in un posto:
  una riga di `commesse_attivita` senza fattore prende 1 **solo se** l'unità è la base dell'articolo, altrimenti si
  rifiuta (codice del giro 2, `E_UOM_MISSING`, se il significato coincide; la sessione DB lo verifica). La sessione DB
  censisce prima chi scrive in `commesse_attivita` (push dal documento sorgente e altre porte), perché ognuno lo
  attraversa.
* **Prova (pgTAP):** riga senza fattore nella base → 1; riga senza fattore in un'altra unità → il rifiuto; riga col
  fattore → quello scritto, come la fotografia di §13.3 punto 5.

### 14.4 Ricadute su BE e FE (team BE, quando il giro è applicato)

| # | Che cosa |
| --- | --- |
| BE19 | D24: il lock entra in `vw_non_editable_fields`. Verificare che il dettaglio delle unità operative passi `non_editable_fields` al form (la prop `nonEditableFields` di `ArticoloUomForm.vue` c'è; va provato chi la riempie). Policy e ripiego del codice nuovo. Test sul DB vero: UPDATE del fattore → il codice col campo |
| BE20 | D25: `ListiniRepository.get_articolo_uom_validation` (BE17) si ritira, o legge il BB del periodo se ne nasce uno. Il rifiuto del guard arriva col campo `uom_id`. Policy e ripiego dei codici nuovi. `test_listino_uom_compatibile_db` riscritto sui tre lati |
| BE21 | D26: `_map_pushable_row` smette di scrivere 1: il NULL passa al DB, che decide. Il test delle commesse prova il rifiuto per una riga senza fattore fuori dalla base |
