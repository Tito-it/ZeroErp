# Brief DB — Ritirare un articolo senza cancellarlo (`obsoleto_dal`)

## ⏭️ Chi riparte — aggiornato al 2026-11-06 (sera)

**Riparte: Tid**, con la conferma di O-9 affinata; poi il **team DB**, col changeSet dei `COMMENT` (D-C) e, quando
`brief-db-sorgente-documento-e-riga` ha il suo primo lotto, col lotto B riscritto lì sopra.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ Tid | il modello: vietata la scelta nuova, ammessa la derivazione (2026-11-04) | §3 | — |
| 2 | ✅ Tid | lo strumento: guard sulla riga; il motivo nella check condivisa con il picker, BB unico (2026-11-05) | §4 | — |
| 3 | ✅ DB | censimento delle relazioni verso `catalogo.articoli` e della loro derivazione (2026-11-04) | §5 | — |
| 4 | ✅ Tid | O-1…O-10, D, ambito (2026-11-04); via allo sviluppo (2026-11-05) | §6 | — |
| 5 | ✅ DB + Tid | lotto A (`20261105-01…-14`, CSV dei codici): scritto, applicato su dbdev e scratch, pgTAP verdi (2026-11-05) | §7.1 | — |
| 6 | ✅ DB + Tid | lotti C e D senza sorgente (`20261106-01…-03`, pgTAP, guida, manuali): applicati, pgTAP verdi (2026-11-06) | §7.2-bis | — |
| 7 | Tid | **confermare O-9 affinata**: l'`ONERE` con sorgente (dal push di ordine e bolla) passa | §7.2-bis | — |
| 8 | DB | **D-C**: riscrivere i `COMMENT` di questo cantiere secondo `linee-guida-sql` §5d | sotto | — |
| 9 | DB + Tid | lotto B (verbi): ✍️ riscritto sul modello nel giro R.1 di `brief-db-sorgente-documento-e-riga` (`20261106-51` … `-56`), provato in transazione, da applicare (2026-11-06). Righe d'acquisto e di fattura (lotto C), presidio per verbo (lotto D): ancora fermi | §7.2, §7.3 | `brief-db-sorgente-documento-e-riga` |
| 10 | BE / FE | `obsoleto_dal` ed `e_obsoleto` nel form e nella lista, `righe_saltate` del «Clona», policy, chiave i18n | §8 | — |

⛔ **Lotto B fermo (Tid, 2026-11-06):** non si applica finché non è deciso il modello della sorgente in
`brief-db-sorgente-documento-e-riga` (tipo + chiave del documento + `sorgente_riga` = la riga). I verbi
`20261105-15…-18` e il backfill `-19` sono **fuori dall'albero** e si riscrivono lì sopra, una volta sola (§7.2). Il
§9 qui sotto (e la sua M-1) confluisce in quel brief. Il lotto A resta: il guard legge solo «la sorgente c'è o no».

✅ **Lotto B riscritto (2026-11-06):** i sei verbi che generano righe di vendita (revisione, push preventivo→ordine,
ordine e contratto dall'offerta, bolla dall'ordine, riconsegna) scrivono la provenienza nel modello, col BB che
scrive, nel giro R.1 di `brief-db-sorgente-documento-e-riga` (`20261106-51` … `-56`). Il caso del buco qui sotto (la
revisione su un articolo ritirato) è il test 6 di `vendite/test-sorgente-righe-vendita-v1`. Il buco si chiude
all'apply.

⚠️ **Buco noto fino al lotto B:** il guard di riga del lotto A è applicato, ma oggi push, revisione e bolle non
scrivono la sorgente. Una riga **derivata** da un articolo ritirato viene quindi trattata come scelta nuova e
respinta. Il buco è del modello, non dei dati (fatto datato: 0 articoli ritirati su 739), e si chiude col lotto B.
Accettato perché non c'è produzione. La guida lo dice, con la data.

⚠️ **D-C — i `COMMENT` di questo cantiere vanno riscritti (emerso il 2026-11-06).** `linee-guida-sql` §5d (Tid,
2026-11-05, Q13 di `brief-db-revisione-dbops`): il `COMMENT` descrive l'oggetto al presente; niente nomi di brief,
marcatori `rev`, id di changeSet, sigle di decisione o misure, e vale **da subito** per ogni COMMENT nuovo o
riscritto. I COMMENT scritti da `20261105-01…-14` e `20261106-01…-03` non la rispettano (13 changeSet su 17: tabelle,
colonne, funzioni, trigger, vista). Sono applicati, quindi non si toccano: serve un changeSet nuovo di soli
`COMMENT ON`, scritti dal vivo e ripuliti, più il controllo di testo su `obj_description`.

Debito rinviato da Tid (2026-11-04): il ritiro di `preventivo_riga_id` (O-10), da riprendere all'archiviazione.
Committato il 2026-11-06 (lotti A, C, D, il fix da zero `20261103-29`, i due brief).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-11-04. **A chi:** Tid, poi il team DB, poi BE/FE.
> **Origine:** Tid, 2026-11-04: «per il codice articolo potrebbe essere utile un meccanismo di obsoleto,
> per ritirare l'articolo senza doverlo cancellare».
> **Brief vicini verificati:** `work-done/brief-db-deprecabilita-catalogo-vs-istanze.md` (decisione P1:
> `attivo` ≠ «selezionabile per il nuovo») e `work-done/brief-db-obsoleto-dal-filtro-lookup-e-guard.md`
> (lookup `p_includi_obsoleti`, guard generico): sono il pattern da cui si parte, chiusi, e non coprivano
> gli articoli. `work-done/brief-db-articoli-ammessi-per-documento.md` (A-10): blocca la struttura di
> un articolo usato; asse diverso, nessuna sovrapposizione. `work-in-progress/brief-db-magazzino-tutte-le-scritture-dal-verbo.md`:
> tocca le scritture di magazzino, che qui **non** si bloccano (O-5). Nessun brief aperto sul tema.
> **Ambito:** tocca le righe di tutti i documenti di vendita e d'acquisto. Rientra nel fermo allentato
> (PROJECT_CONTEXT, 2026-10-25) perché poggia su un pezzo comune, il guard generico, montato una volta
> per relazione.
> **Sviluppo:** non c'è produzione (2026-11-04). Si va per la strada più corta: niente compatibilità,
> rotture BE ammesse, colonna nuova senza backfill.
> **Ambito:** ✅ ok esplicito di Tid sull'ambito, 2026-11-04 (§6).

---

## 1. Il caso

Un articolo che non si vende più non si può cancellare (ha documenti, movimenti, listini) e non si può
disattivare: `attivo=false` è bloccato da circa trenta trigger `block_deact` su `catalogo.articoli`, e a
ragione. `attivo` vuol dire «riferimento valido», e un articolo usato lo resta per sempre.

Manca l'altro asse: **«si può scegliere per un uso nuovo»**. È lo stesso difetto che
`brief-db-deprecabilita-catalogo-vs-istanze` ha risolto su `tipi_prestazione` e `template_flussi` con
`obsoleto_dal`.

## 2. I fatti di struttura (doc auto-generata, 2026-11-04)

* `catalogo.articoli` non ha `obsoleto_dal`.
* Il pattern esiste: `dbops.fn_get_lookup_codici(…, p_includi_obsoleti)` e il guard generico
  `dbops.trgfn_child_requires_non_obsolete_parent` (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`), montato una
  volta per relazione. Oggi il guard **non distingue** una riga nuova da una derivata.
* La derivazione **non è scritta allo stesso modo** su tutte le righe: `vendite.ordini_righe` e
  `vendite.fatture_righe` hanno `sorgente_tipo_id`/`sorgente_uid`, mentre `vendite.ddt_righe` e
  `vendite.preventivi_righe` no.

## 3. Il modello (Tid, 2026-11-04)

`obsoleto_dal date NULL` su `catalogo.articoli`: `NULL` = si sceglie; una data passata = ritirato; una
data futura = ritiro programmato.

| Caso | Regola |
| --- | --- |
| riga **nuova** scelta dall'operatore su preventivo, ordine, listino, contratto | ⛔ respinta se l'articolo è obsoleto |
| riga **derivata** da un altro documento (ordine dal preventivo, bolla dall'ordine, fattura dalla bolla, reso) | ✅ passa: non è una scelta |
| cambio dell'articolo su una riga esistente, anche derivata | ⛔ è una scelta nuova |
| magazzino: movimenti, inventari, rettifiche, trasferimenti | ✅ mai bloccato (O-5) |

`attivo` non si tocca: resta `true`, e i `block_deact` non vengono mai sfiorati.

## 4. Lo strumento (Tid, 2026-11-04)

Un **guard sulla riga**, BEFORE INSERT OR UPDATE OF `articolo_id`: se la riga è derivata passa,
altrimenti un articolo obsoleto alla data viene respinto. La derivazione si legge **dalla riga**, mai da
un parametro che il chiamante dichiara: così il guard copre ogni strada (verbi, BE, import) senza che
nessuno debba ricordarsi di chiamare niente.

* Il guard generico `trgfn_child_requires_non_obsolete_parent` si estende con un argomento: la colonna
  che, valorizzata, esenta la riga. Si monta una volta per relazione (tier 2 del pattern).
* L'esenzione vale solo sull'`INSERT` (O-7). Sull'`UPDATE` il guard controlla **solo se l'articolo
  cambia** (`NEW.articolo_id IS DISTINCT FROM OLD.articolo_id`). Le righe già inserite con un articolo poi
  ritirato **restano** e si modificano liberamente (Tid, 2026-11-04). ⚠️ Il trigger `UPDATE OF articolo_id`
  da solo non basta: scatta ogni volta che la colonna è nel `SET`, anche con lo stesso valore. Lo fanno
  l'upsert di `fn_upsert_commessa_attivita` (`ON CONFLICT … SET articolo_id = EXCLUDED.articolo_id`) e ogni
  UPDATE che riscrive la riga intera.
* La derivazione si legge da `sorgente_tipo_id IS NOT NULL` (O-10), che non dipende dalla forma della chiave
  (`sorgente_uid` uuid o `sorgente_riga` bigint).
* Il picker filtra già: `p_includi_obsoleti=false` nella selezione per il nuovo. Il guard è la rete
  sotto il picker.

**Variante decisa da Tid, 2026-11-05.** Sulle righe c'era già un guard con la stessa domanda,
`script.trgfn_righe_guard_articolo_ammesso`, i cui motivi stanno in `script.fn_check_articolo_riga_su_contesto`.
Quella check la legge anche il picker degli articoli di riga, `catalogo.fn_articoli_ammessi`. Un secondo guard
accanto avrebbe fatto proporre al picker ciò che la riga poi respinge, contro il §12.6 delle linee guida SQL.

* **Dove serve la check**, cioè preventivo, ordine, bolla, offerta, contratto, versione di listino, distinta e
  promo, «ritirato» è un **motivo** della check: `E_ARTICOLO_OBSOLETO`, il primo, comune a tutti i documenti.
  Conta solo se la riga è una **scelta nuova**, un parametro in coda `p_scelta_nuova` che vale `false` di
  default. Lo dicono:
  * il guard di riga, calcolandolo dalla riga: all'INSERT, la colonna di esenzione (`TG_ARGV[2]`,
    `sorgente_tipo_id`) è vuota; all'UPDATE, cambia l'articolo o il documento padre (spostare una riga in
    un'altra versione di listino è un impegno nuovo, O-2);
  * il picker, sempre `true`, così l'articolo ritirato resta nell'elenco, fra gli esclusi, col suo motivo;
  * il guard della distinta, sempre `true` (O-4).

  Il default `false` resta a chi giudica righe che esistono già (`script.fn_check_riga_documento_su_contesto`:
  emissione, push, attivazione, ordine dall'offerta, correzione di struttura).
* **Dove la check non arriva**, cioè righe di fattura, `ONERE` di commessa, righe d'acquisto e kit di listino,
  si monta il guard generico `trgfn_child_requires_non_obsolete_parent` esteso con il sesto argomento opzionale
  `esenzione_col`, che vale solo all'INSERT.
* **Il predicato è un BB unico**, `script.fn_e_obsoleto(date)` (Tid, 2026-11-05: «non scriviamo un quinto
  punto»). Era scritto a mano in quattro oggetti (`fn_get_lookup_codici`, il guard generico,
  `vw_bersagli_non_dichiarati`, `trgfn_event_log_deriva_scope`), che ora passano tutti dal BB. I processi
  (`dbops.processi.obsoleto_dal`) seguono un'altra regola, «qualunque data spegne subito», e restano fuori.
* **Convenzione della chiave di sorgente**: è il «modello A» di `script.trgfn_guard_sorgente_polimorfa_tipizzata`.
  Con `key_selector = 'id'` la chiave sta in `sorgente_riga`, con `'uid'` in `sorgente_uid`. Le righe
  (`PREVENTIVO_RIGA`, `ORDINE_VENDITA_RIGA`, `RESO_VENDITA_RIGA`, …) scrivono quindi `sorgente_riga`. Il guard
  polimorfo si monta sulle righe di vendita che ora esentano, perché una sorgente che esenta deve essere vera.

## 5. Censimento (team DB, 2026-11-04)

Fonte: `pg_constraint` (`confrelid = 'catalogo.articoli'`) su dbdev, i verbi che generano le righe nella doc
auto-generata e, per le fatture, `pipeline_repository.py` (solo lettura). Sono **37 FK su 35 tabelle**. Due
non hanno né il `block_deact` su `articoli` né il trigger `child_requires_active_parent`:
`articoli_componenti.prodotto_id` e `fatture_righe.kit_articolo_padre_id`. È la prova che il censimento si fa
da `pg_constraint`.

### 5.1 Si monta il guard: famiglia «scelta»

| Tabella.colonna | Dove è scritta la provenienza | Quando, e da chi | Esito |
| --- | --- | --- | --- |
| `vendite.preventivi_righe.articolo_id` | nessuna colonna | `fn_crea_revisione_preventivo` copia le righe della revisione precedente senza marcarle | ⚠️ O-8 |
| `vendite.ordini_righe.articolo_id` | `preventivo_riga_id` **e** `sorgente_*`: due forme | `fn_push_preventivo_a_ordine`: `preventivo_riga_id` nello stesso `INSERT` ✅. `fn_genera_ordine_da_offerta`: **nessuna** | ⚠️ caso D; O-10 |
| `vendite.ddt_righe.articolo_id` | nessuna colonna; il legame sta in `ordini_righe_fulfillment` | `fn_genera_ddt_da_ordine` e `fn_genera_ddt_riconsegna`: il legame si scrive **dopo** la riga; nella riconsegna senza ordine non si scrive affatto | ⚠️ caso D (deciso: `sorgente_*`) |
| `vendite.fatture_righe.articolo_id`, `.kit_articolo_padre_id` | `sorgente_*` | pipeline BE: nello stesso `INSERT` ✅ | esenzione su `sorgente_uid` |
| `vendite.contratti_righe.articolo_id` | nessuna colonna | `fn_push_offerta_a_contratto`: nessuna | ⚠️ caso D |
| `vendite.offerte_commerciali_eccezioni.articolo_id` | — (è l'origine) | — | senza esenzione |
| `vendite.listini_righe.articolo_id`, `vendite.listini_kit.articolo_padre_id` | — (O-2) | `fn_clona_versione_listino`: l'obsoleto si salta (O-6), con i suoi kit e componenti | senza esenzione |
| `vendite.promo_articoli.articolo_id` | — | — | senza esenzione |
| `vendite.commesse_attivita.articolo_id` | `sorgente_tipo_id`/`sorgente_uid` (**text**), `contratto_id`, `listino_riga_id` | `fn_upsert_commessa_attivita`: nello stesso `INSERT`; senza sorgente solo `ONERE` e `RETTIFICA` (CHECK) | O-9: si controlla solo `ONERE` |
| `acquisti.ordini_righe.articolo_id` | `sorgente_*` | oggi nessun verbo né BE scrive righe d'acquisto | esenzione su `sorgente_uid` (O-3) |
| `acquisti.ddt_righe.articolo_id` | nessuna colonna; il legame sta in `acquisti.ordini_righe_fulfillment` | oggi nessuno scrive | ⚠️ caso D (deciso: `sorgente_*`) |
| `catalogo.articoli_componenti.componente_id` | — (O-4) | — | senza esenzione |

### 5.2 Non si monta: provenienza obbligatoria per costruzione

La FK di provenienza è `NOT NULL`, quindi la riga è sempre derivata e non c'è una scelta da controllare. La
scelta si controlla a monte: sulla distinta, sulla riga padre o sulla bolla.

* righe-componente: `preventivi_righe_componenti`, `ordini_righe_componenti`, `ddt_righe_componenti`,
  `contratti_righe_componenti`, `offerte_commerciali_eccezioni_componenti` (`.componente_id`) e
  `listini_righe_componenti` (`.articolo_figlio_id`, `.articolo_padre_id`): `articolo_componente_id NOT NULL`;
* `vendite.resi_righe.articolo_id`: `ddt_riga_id NOT NULL`;
* `vendite.attivita_fatturabili.articolo_id`: `commessa_attivita_id NOT NULL`.

### 5.3 Non si monta: magazzino (O-5) e configurazione dell'articolo

* magazzino: `movimenti`, `movimenti_attesi`, `inventari_righe`, `rettifiche_righe`, `trasferimenti_righe`,
  `lotti`, `assets`, `valore_giacenza`;
* configurazione: `articoli_uom_operativa`, `note_articoli`, `articoli_descrizioni_aggiuntive`,
  `articolo_regole_fatturazione`, `anagrafiche.soggetti_titoli_iva_ambiti`, e
  `articoli_componenti.prodotto_id`. Proposta DB: un articolo ritirato si continua a mantenere, quindi la
  distinta di un prodotto obsoleto non è una scelta di vendita.

### 5.4 Cosa cambia per il caso D

Il caso D non riguarda solo le bolle: ci sono altri verbi che generano righe derivate senza scriverne la
sorgente polimorfa (`fn_push_preventivo_a_ordine`, che scrive solo `preventivo_riga_id`;
`fn_genera_ordine_da_offerta`; `fn_push_offerta_a_contratto`; `fn_crea_revisione_preventivo` (O-8); la
riconsegna senza ordine).
Applicare la decisione D significa: **ogni verbo che genera una riga da un'altra scrive `sorgente_*` nello
stesso `INSERT`**. Le colonne nuove vanno su `vendite.ddt_righe`, `acquisti.ddt_righe` e
`vendite.contratti_righe`, più `vendite.preventivi_righe` se passa O-8.

## 6. Da decidere (Tid, dopo il censimento)

| # | Domanda | Proposta DB |
| --- | --- | --- |
| O-1 | A quale data si confronta `obsoleto_dal`: quella del documento o il giorno della scelta? | ✅ **Tid, 2026-11-04**: il giorno della scelta (`script.fn_data_operativa()`): il ritiro programmato è una scadenza |
| O-2 | La nuova versione di un listino copiata dalla precedente è derivata? | ✅ **Tid, 2026-11-04**: no, un listino nuovo è un impegno nuovo a vendere, e l'obsoleto non si ricopia |
| O-3 | Acquisti: si può ordinare al fornitore un articolo obsoleto? | ✅ **Tid, 2026-11-04**: stessa regola, respinto sulla riga nuova, ammesso su quella derivata |
| O-4 | Distinte: un componente obsoleto in una composizione nuova? | ✅ **Tid, 2026-11-04**: respinto; le righe-componente espanse da una distinta esistente sono derivate e passano |
| O-5 | Magazzino | ✅ **Tid, 2026-11-04**: mai bloccato, l'obsoleto non ha effetto sul magazzino: la giacenza residua va comunque scaricata |
| O-6 | La copia di una versione di listino incontra un articolo obsoleto | ✅ **Tid, 2026-11-04**: la riga **si salta**, la copia non si ferma |
| D | La derivazione scritta **dopo** la riga: `vendite.ddt_righe` e `acquisti.ddt_righe` non hanno colonne di provenienza (doc auto-generata, 2026-11-04) | ✅ **Tid, 2026-11-04**: si aggiungono `sorgente_tipo_id`/`sorgente_uid` alle `ddt_righe`, come su ordini e fatture, e il verbo che genera le scrive nello stesso `INSERT`. Il censimento dice se altre righe sono nello stesso caso |
| O-7 | Il cambio di articolo su una riga derivata: oggi `articolo_id` **non** è bloccato (`trgfn_lock_columns` blocca solo `natura_vendita_id`), quindi in bozza si cambia | ✅ **Tid, 2026-11-04**: l'esenzione vale solo sull'`INSERT`; sull'`UPDATE OF articolo_id` il guard controlla sempre. Scartata l'alternativa `articolo_id` immutabile sulle righe derivate (cambio di modello, ricaduta BE/FE) |

| O-8 | La revisione di un preventivo (`fn_crea_revisione_preventivo`) ricopia un articolo diventato obsoleto | ✅ **Tid, 2026-11-04**: **derivata**, quindi passa. È la stessa proposta allo stesso cliente, non un impegno nuovo come il listino (O-2). Saltare la riga cambierebbe in silenzio un'offerta già fatta; respingerla impedirebbe di rivedere il resto. L'operatore la toglie a mano. Serve `sorgente_*` su `preventivi_righe` (sorgente `PREVENTIVO_RIGA`) |
| O-9 | `commesse_attivita`: un'attività registrata su un articolo obsoleto | ✅ **Tid, 2026-11-04**: si respinge **solo l'inserimento della riga `ONERE`**; le righe già inserite restano (§4), l'unica inserita a mano dalla porta oneri. Tutte le altre passano, perché arrivano in commessa già predisposte per la fattura. La struttura lo conferma: `chk_commesse_attivita_senza_sorgente_onere_rettifica` obbliga ogni riga `NORMALE` ad avere una sorgente, e senza sorgente restano solo `ONERE` e `RETTIFICA`. La prima proposta DB («esente se `sorgente_uid` è valorizzato») **sbagliava**: avrebbe respinto la `RETTIFICA` senza sorgente, che è un accredito su una vendita già fatta. Montaggio: guard generico senza esenzione, con `WHEN (NEW.tipo_movimento = 'ONERE')` |
| O-10 | `ordini_righe` registra la provenienza in due forme: `preventivo_riga_id` e `sorgente_*` | ⏳ in discussione. Fatti (2026-11-04): `PREVENTIVO_RIGA` **è già** in `config.sorgenti`, ma `fn_push_preventivo_a_ordine` scrive `preventivo_riga_id` (FK vera, con `block_deact`) e non `sorgente_*` (polimorfa, senza FK). Lettori di `preventivo_riga_id`: 7 oggetti DB (tra cui `fn_documento_legami`, `fn_documento_lineage_legami`, `fn_documento_ritira_legami`, `trgfn_doc_righe_lock_fuori_bozza`, due viste di smistamento), 2 file BE, 11 pgTAP. ✅ **Tid, 2026-11-04**: il guard legge **solo la sorgente polimorfa** (`sorgente_tipo_id`), non `preventivo_riga_id`. Condizione: la sorgente deve essere **sempre** valorizzata sulle righe generate. ⚠️ Oggi (2026-11-04) su `ordini_righe` non la scrive nessun verbo: `fn_push_preventivo_a_ordine` scrive solo `preventivo_riga_id`, `fn_genera_ordine_da_offerta` niente. Rientra nel §5.4. Il presidio è nel §7. `preventivo_riga_id` **resta** e si continua a scrivere accanto alla sorgente, perché ha 7 lettori DB, 2 BE e 11 pgTAP: Tid, 2026-11-04, «momentaneamente non facciamo nulla». È un doppione di significato: all'archiviazione di questo brief va fra i residui |

**Ambito:** ✅ ok esplicito di Tid, 2026-11-04: il guard si monta su tutte le righe di vendita e d'acquisto.

**Listini e distinte, senza colonna di provenienza:** `listini_righe` è sempre una scelta (O-2), quindi il guard si
monta senza esenzione. Le righe-componente dei documenti hanno già `articolo_componente_id NOT NULL`, che punta alla
riga di distinta: la scelta avviene su `catalogo.articoli_componenti.componente_id` (O-4) e sulla riga padre, e lì si
monta il guard.

## 7. Sviluppo DB (via di Tid, 2026-11-05)

### 7.1 Lotto A — modello e regola (✅ scritto, ⏳ da applicare)

| changeSet | Che cosa |
| --- | --- |
| `00_schema/catalogo/20261105-01` | `catalogo.articoli.obsoleto_dal date NULL` |
| `00_schema/vendite/20261105-02` | `sorgente_tipo_id`/`sorgente_uid`/`sorgente_riga` + FK su `preventivi_righe`, `ddt_righe`, `contratti_righe` |
| `00_schema/acquisti/20261105-03` | le stesse su `acquisti.ddt_righe` |
| `20_code/script/20261105-04` | BB `script.fn_e_obsoleto(date)`, `BEGIN ATOMIC` (il planner lo incorpora: provato) |
| `-05`, `-06`, `-07`, `-08` | le quattro copie del predicato passano al BB; `-06` aggiunge anche `esenzione_col` al guard generico |
| `20_code/script/20261105-09` | check su contesto: `p_scelta_nuova` in coda (DROP + CREATE) e motivo `E_ARTICOLO_OBSOLETO` |
| `-10` | involucro `fn_check_articolo_riga`: `p_scelta_nuova` in coda, girato alla check |
| `-11` | guard di riga: calcola la scelta nuova, `TG_ARGV[2]` di esenzione |
| `20_code/catalogo/20261105-12`, `-13` | picker e guard della distinta passano `true` |
| `20_code/vendite/20261105-14` | guard di riga rimontato con `'sorgente_tipo_id'` su preventivi, ordini, bolle e contratti; guard polimorfo della sorgente sulle stesse quattro |
| CSV `codici_errore` / `messaggi_errore` | `E_ARTICOLO_OBSOLETO` (CONFLITTO_STATO, messaggio 1435, due valori: codice e data) |
| pgTAP | `test-guard-esclusione-figlio-bundle-v1` (t.1) e `test-contratto-righe-lista-v1` (t.12) leggono la firma a quattro argomenti |

Le FK nuove verso `config.sorgenti` non hanno indice: le registra `fn_populate_fk_index_policy` a
`consentito=false`, come quelle di ordini e fatture. Nessuno cerca per `sorgente_tipo_id`.

**Provato il 2026-11-05** su dbdev, come owner, con l'SQL estratto e le `sqlCheck` dentro `BEGIN … ROLLBACK`.
Dopo la prova il vivo è identico (md5 dei corpi).

* I 14 changeSet girano, con le precondizioni a OK, e `plpgsql_check` dà zero errori sulle otto funzioni toccate.
* Sul preventivo `DRAFT` del builder pgTAP, con l'articolo ritirato da ieri:
  * la riga nuova senza sorgente è respinta con `E_ARTICOLO_OBSOLETO`;
  * la derivata (`PREVENTIVO_RIGA`, `sorgente_riga`) passa;
  * la sorgente falsa è respinta dal guard polimorfo;
  * il ritiro programmato passa;
  * la riga esistente con l'articolo riscritto uguale passa;
  * il picker dà `E_ARTICOLO_OBSOLETO` con i valori codice e `DD/MM/YYYY`;
  * il default `false` non vede l'obsoleto.
* `fn_get_lookup_codici` con il BB dà lo stesso conteggio della copia in linea.

⚠️ **Finché il lotto B non è applicato**, un verbo che genera righe senza scrivere la sorgente farebbe
respingere la riga derivata di un articolo ritirato. Oggi non c'è nessun articolo ritirato (colonna nuova, tutta
`NULL`), quindi il rischio è solo d'ordine: i lotti si applicano insieme o in sequenza, prima di ritirare un
articolo.

✅ **Lotto A applicato da Tid il 2026-11-05** su dbdev e sullo scratch, con pgTAP senza regressioni. Verifica DB dello
stesso giorno: firme, `GRANT`, uso del BB, trigger, `plpgsql_check` e casi di comportamento sul vivo, tutti come attesi.
Le righe di `dbops.fk_index_policy` delle quattro FK nuove le scrive il prossimo `ci_apply`.

### 7.2 Lotto B — stato al 2026-11-05

✅ **Scritti e provati** (SQL estratto, `BEGIN … ROLLBACK` su dbdev; ogni verbo chiamato davvero dai builder pgTAP; zero
righe generate senza sorgente; la chiave punta alla riga d'origine):

| changeSet | Verbo | Sorgente scritta |
| --- | --- | --- |
| `20_code/vendite/20261105-15` | `fn_push_preventivo_a_ordine` | `PREVENTIVO_RIGA`, accanto a `preventivo_riga_id` |
| `-16` | `fn_crea_revisione_preventivo` | `PREVENTIVO_RIGA` (O-8: la revisione su un articolo ritirato passa, provato) |
| `-17` | `fn_genera_ddt_da_ordine` | `ORDINE_VENDITA_RIGA` |
| `-18` | `fn_genera_ddt_riconsegna` | `RESO_VENDITA_RIGA`, anche senza ordine |
| `90_end/20261105-19` | backfill di `ordini_righe` + `CHECK` | 314 righe su dbdev; `chk_ordini_righe_preventivo_ha_sorgente` |

Il backfill gira coi trigger spenti e riaccesi come erano (provato: trigger identici prima e dopo). Il `CHECK` respinge
`preventivo_riga_id` senza sorgente. I due pgTAP che scrivono a mano una riga d'ordine con `preventivo_riga_id`
(`test-fattura-origini-v1`, `test-documento-lineage-seminata-v1`) scrivono anche la sorgente.
`fn_documento_ritira_legami` azzera solo `preventivo_riga_id`: la sorgente resta, e il `CHECK` lo ammette.

✅ **Deciso (Tid, 2026-11-05/06):** i due verbi dell'offerta scrivono la **testata + progressivo**:
`OFFERTA_COMMERCIALE`, `sorgente_uid` = uid dell'offerta, `sorgente_riga` = progressivo della riga. `config.sorgenti`
ha solo la testata (chiave `uid`), e `fn_offerta_righe_espanse` non dice da quale riga (listino o eccezione) viene ogni
riga dell'ordine. L'ostacolo era l'indice unico «idempotenza import» `(sorgente_tipo_id, sorgente_uid)` su
`ordini_righe`: due righe della stessa offerta lo violano, e lo viola anche il secondo ordine dopo un annullo. Si
scioglie con la pulizia del §9, che **precede** i due verbi.

⛔ **Fermo (Tid, 2026-11-06).** I cinque file `20261105-15…-19` sono **fuori dall'albero delle migrazioni**: li carica
`changelog-master-v2.yaml` (`includeAll` su `90_end`, autogen per `20_code`) e girerebbero al primo migrate. Sono
conservati nella scratchpad della sessione del 2026-11-06 (`lotto-B-fermo/`) come base da riscrivere sul modello di
`brief-db-sorgente-documento-e-riga`. I due pgTAP del lotto B (`test-fattura-origini-v1`,
`test-documento-lineage-seminata-v1`) restano modificati: scrivono la sorgente a mano nella forma di oggi (modello A) e
si riscrivono con quel modello.

### 7.2-bis Lotti C e D senza sorgente — ✅ scritti e provati (2026-11-06), ⏳ da applicare

| changeSet / file | Che cosa |
| --- | --- |
| `20_code/vendite/20261106-01` | `fn_clona_versione_listino` salta riga, componenti e kit dell'articolo ritirato (O-6, BB `fn_e_obsoleto`); + `righe_saltate` in coda al risultato (DROP + CREATE, `REVOKE`/`GRANT`/`COMMENT` di nuovo) |
| `20_code/vendite/20261106-02` | guard generico su `commesse_attivita.articolo_id` (`WHEN ONERE`, esenzione `sorgente_tipo_id`) e su `listini_kit.articolo_padre_id` (senza esenzione) |
| `20_code/catalogo/20261106-03` | `vw_articoli_dettaglio`: + `obsoleto_dal` ed `e_obsoleto` (BB) in coda |
| pgTAP `db/pgtap/vendite/test-articolo-ritirato-v1.sql` | 17 casi: vista, copia, riga di listino nuova e programmata (lotto A), kit nuovo ed esistente, onere dalla porta, esistente, con e senza sorgente, montaggio, privilegi |
| guida `docs/it/guide/uso-di-obsoleto.md` | gli articoli come secondo caso; il sesto argomento del guard; «Dove è applicato» |
| manuali | `vendite/manual/fn_clona_versione_listino`, `listini_kit`, `commesse_attivita`; `catalogo/manual/vw_articoli_dettaglio`, `articoli` |

⚠️ **O-9 affinata, da confermare (Tid).** O-9 (2026-11-04) diceva «guard senza esenzione su `ONERE`», perché l'onere
nasceva solo dalla porta oneri, senza sorgente. Dal 2026-11-03 (`brief-db-addebito-trasporto-ordine`) un `ONERE`
arriva anche dal push di ordine e bolla **con la sorgente del documento**: senza esenzione quella riga derivata
sarebbe respinta, contro il §3. Il montaggio quindi esenta la riga con sorgente. Il motivo di O-9 («si controlla solo
l'onere scelto a mano») resta. Provato: con sorgente passa, senza è respinta.

**Provato il 2026-11-06** su dbdev, come owner, con l'SQL estratto e le `sqlCheck` dentro `BEGIN … ROLLBACK`:

* precondizioni OK; zero errori di `plpgsql_check` sulla copia;
* la copia di una versione (Q vivo, R ritirato, kit K ritirato col suo componente) dà `1|1|0|1`
  (copiate|saltate|componenti copiati|componenti saltati) e lascia solo Q;
* il kit nuovo su K è respinto (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`), quello esistente si modifica;
* la riga nuova di listino su R è respinta (`E_ARTICOLO_OBSOLETO`), il ritiro programmato passa;
* l'onere dalla porta su `ONERE_TRASFERTA` ritirato è respinto; quello già inserito si riscrive; la stessa riga
  copiata con una sorgente d'ordine passa, senza sorgente è respinta;
* la vista dà `e_obsoleto` vero sul ritirato e falso sul programmato;
* `GRANT` della copia ricreata: `EXECUTE` a `zeroerp_app`, non a `PUBLIC`.

Il vivo è rimasto identico (firma della copia, nessun trigger nuovo). Il pgTAP non l'ho lanciato: lo lancia Tid.

✅ **Applicato da Tid il 2026-11-06** su dbdev e sullo scratch. Il primo giro di pgTAP era rosso solo sullo scratch, per
due file. `test-articolo-ritirato-v1` (caso 14): il test prendeva un ordine già presente nel database, e da zero non
ce n'è nessuno; ora l'ordine se lo costruisce (`dbops.fn_pgtap_crea_ordine`). `test-documento-lineage-seminata-v1`:
non riprodotto (fixture e query delle asserzioni pulite, come app), verde alla corsa successiva. Corsa successiva:
verde.

### 7.3 Lotti da fare

* **B — i verbi scrivono la sorgente nello stesso INSERT** (O-10, D, O-8):
  * `fn_push_preventivo_a_ordine` scrive `PREVENTIVO_RIGA` accanto a `preventivo_riga_id`;
  * `fn_genera_ordine_da_offerta` scrive `OFFERTA_COMMERCIALE` (`sorgente_uid`);
  * `fn_push_offerta_a_contratto` scrive `OFFERTA_COMMERCIALE`;
  * `fn_crea_revisione_preventivo` scrive `PREVENTIVO_RIGA`;
  * `fn_genera_ddt_da_ordine` scrive `ORDINE_VENDITA_RIGA`;
  * `fn_genera_ddt_riconsegna` scrive `RESO_VENDITA_RIGA`.

  Poi il backfill di `ordini_righe` (`preventivo_riga_id` → sorgente) e il `CHECK`
  `preventivo_riga_id IS NULL OR sorgente_tipo_id IS NOT NULL`. ⚠️ Lo stesso cambio di modello vale per il
  legame `preventivo_riga_id` nei lettori: resta (debito di Tid).
* **C — il guard generico sulle righe che la check non serve**:
  * `fatture_righe.articolo_id` e `.kit_articolo_padre_id`, con esenzione `sorgente_tipo_id`;
  * `commesse_attivita`, con `WHEN (NEW.tipo_movimento = 'ONERE')` e senza esenzione (O-9);
  * `acquisti.ordini_righe` e `acquisti.ddt_righe`, con esenzione `sorgente_tipo_id` e guard polimorfo;
  * `listini_kit.articolo_padre_id`, senza esenzione.

  Inoltre `fn_clona_versione_listino` salta l'articolo ritirato con i suoi kit e componenti (O-6). Prima
  di montare, si censiscono i pgTAP e i seed `80_data` che scrivono quelle tabelle.
* **D — viste, pgTAP, guida**: `obsoleto_dal` in coda a `vw_articoli_dettaglio` e nelle viste dei picker; i
  pgTAP del §7 come file; il presidio per ogni verbo; la guida `uso-di-obsoleto.md`.

### 7.3 Le regole del lotto, come nel brief originale

* `00_schema`: `ALTER TABLE catalogo.articoli ADD COLUMN obsoleto_dal date NULL` (nessun backfill).
* `20_code`: il guard generico esteso, il montaggio per relazione, `obsoleto_dal` in coda a
  `vw_articoli_dettaglio` e nelle viste dei picker.
* pgTAP che **costruisce** i casi: riga nuova su articolo obsoleto respinta; riga derivata passa; cambio
  di articolo su riga derivata respinto; riga esistente con articolo poi ritirato modificabile, anche con
  `articolo_id` riscritto uguale; ritiro programmato (data futura) passa; magazzino passa.
* ⭐ Presidio «sorgente sempre valorizzata» (O-10): un `CHECK` non può esprimerlo, perché una riga manuale ha
  la sorgente `NULL` legittimamente. Si presidia con **un pgTAP per ogni verbo che genera**: costruisce il
  documento di partenza, chiama il verbo e verifica `sorgente_tipo_id IS NOT NULL` su **tutte** le righe
  generate. Dove esiste una FK di provenienza si aggiunge anche un `CHECK` di coerenza, per esempio su
  `ordini_righe`: `preventivo_riga_id IS NULL OR sorgente_tipo_id IS NOT NULL`.
* Con quale chiave e quale codice di sorgente scrive ogni verbo (`sorgente_uid` o `sorgente_riga`;
  `PREVENTIVO_RIGA`, `ORDINE_VENDITA_RIGA`, `RESO_VENDITA_RIGA`, `OFFERTA_COMMERCIALE`) si fissa allo
  sviluppo, sulla convenzione di `config.sorgenti.key_selector`. Le righe hanno chiave `bigint` e non
  entrano in `sorgente_uid uuid`.
* Guida `uso-di-obsoleto.md`: gli articoli come secondo caso, con la distinzione nuova/derivata.

## 8. Ricadute BE / FE (da dettagliare dopo il §6)

* BE: `obsoleto_dal` nominato in `ARTICOLI_DETAIL_COLUMNS`; `includi_obsoleti=false` nei picker di riga
  nuova; policy per il codice di errore.
* BE (lotto A, 2026-11-05): `E_ARTICOLO_OBSOLETO` (CONFLITTO_STATO → 409) va in
  `error_policies_generated.py` con la rigenerazione delle policy; campo `articolo_id`, o `componente_id` per la
  distinta. Il picker `catalogo.fn_articoli_ammessi` lo restituisce già come motivo dell'escluso: non serve un
  filtro in più.
* FE (lotto A): la chiave i18n `vendite.righe.articolo_reason.obsoleto`, il tooltip dell'escluso nel picker, con
  due valori, codice dell'articolo e data del ritiro.
* FE: `obsoleto_dal` nel drawer articolo (data, cancellabile per «riattivare»); l'obsoleto riconoscibile in
  lista; il messaggio del guard a video.
* BE (2026-11-06, `20261106-03`): `obsoleto_dal` ed `e_obsoleto` vanno nominati in `ARTICOLI_DETAIL_COLUMNS` (lista e
  drawer) e in `_LOOKUP_ARTICOLI_COLONNE` (picker). `e_obsoleto` è già calcolato alla data operativa: il FE non confronta
  date.
* BE (2026-11-06, `20261106-01`): `fn_clona_versione_listino` restituisce anche `righe_saltate`, in coda.
  `listini_repository.clone_versione` lo riceve già nel dizionario. Il service e la risposta del «Clona» possono dirlo
  all'operatore, come `componenti_saltati`.
* BE (2026-11-06, `20261106-02`): sull'onere dalla porta e sul kit di listino il codice è
  `E_CATALOGO_OBSOLETO_NUOVA_ISTANZA` (CONFLITTO_STATO, già nelle policy), non `E_ARTICOLO_OBSOLETO`.
* BE (§9): nessuna ricaduta attesa. Censito il 2026-11-06: nessun `ON CONFLICT` del backend né del DB si appoggia agli
  indici unici che il §9 ritira. Quelli trovati stanno tutti su tabelle di collegamento (`pratiche_sorgenti`,
  `documenti_fatturazione_canali`, coda di stampa), che il §9 non tocca.

## 9. Le colonne sorgente: un modello solo su tutti i documenti (Tid, 2026-11-06)

> ⏭️ **Confluito in `brief-db-sorgente-documento-e-riga`** (Tid, 2026-11-06): là il modello completo, le sette
> grammatiche e la dimensione. Qui resta la prima stesura, perché spiega da dove è partito.
>
> Fuori dal perimetro degli articoli, ma è nata qui (lotto B, verbi dell'offerta) e qui si scrive, **per coerenza su
> tutti i documenti** (Tid, 2026-11-06). Si fa nel lotto B, **prima** dei due verbi dell'offerta.

### 9.1 Il problema: due significati nelle stesse colonne

Le colonne `sorgente_tipo_id` + `sorgente_uid` nascono il **2025-09-06** su `vendite.ordini` come `source_tipo_id` /
`source_id`. Il commento dice «tipo sorgente import» e «Origine import (**id esterno**)», e c'è un indice unico
«Idempotenza import»: un record che arriva da un **altro sistema** (e-commerce, portale, gestionale precedente) non si
carica due volte. Il **2025-10-05** il rinomino in `sorgente_*` (20251005-01…-06) le ricrea uguali, con l'indice, su
testate e righe di ordini, ddt e fatture, e lo stesso giorno sulle testate di magazzino.

Dopo, le stesse colonne si usano per la **provenienza interna**: «questa riga deriva da quel documento» (contratti
dall'offerta, attività, resi, magazzino; O-10 lo rende la regola). Per la provenienza **l'unicità non è una regola**:
una testata genera molte righe, e un documento annullato si rigenera dalla stessa sorgente. C'è un precedente:
**2026-07-09**, `20260709-01` ha già sostituito l'indice unico su `vendite.ddt` con uno non unico, perché impediva più
bolle per lo stesso ordine. È stato sistemato un solo documento, e il gemello `acquisti.ddt` è rimasto com'era.

Fatto datato (2026-11-06): `config.sorgenti` ha 29 sorgenti, **tutte documenti di ZeroErp**; nessuna è un sistema
esterno.

### 9.2 Il modello (Tid, 2026-11-06)

* **Le colonne sorgente sono la provenienza interna**, e solo quella:
  * `sorgente_tipo_id` (FK a `config.sorgenti`) + la chiave tipizzata, `sorgente_riga` per `key_selector = 'id'` o
    `sorgente_uid` per `'uid'` (modello A);
  * il `CHECK` di chiave dove la tabella ha già le tre colonne;
  * il guard polimorfo;
  * un indice **non unico** per la ricerca «chi deriva da X».
* **Unicità solo dove il dominio ha una regola**, dichiarata col suo nome, nel `COMMENT`, e sulla chiave giusta.
  Esempi: `magazzino.movimenti` (identità dell'operazione) e le tabelle di collegamento (`commesse_sorgenti`,
  `pratiche_sorgenti`, `documenti_fatturazione_canali`). Mai un'unicità «per sorgente» generica.
* **L'import da un sistema esterno**, che è un'idea corretta e si farà, avrà una **tabella di collegamento
  propria**: un registro dei canali + `(canale, tipo_record, id_esterno text) → documento interno`, con l'unicità
  d'idempotenza lì e i dati dell'import (corsa, impronta, esito). Non usa le colonne sorgente. Il motivo: più canali per
  documento, corrispondenze non una a una, dati propri dell'import, nessuna tabella da allargare. Lo schema c'è già, è
  `vendite.commesse_sorgenti`. **Non si costruisce adesso**: si aggiunge senza toccare niente di esistente.

### 9.3 Il censimento (dbdev, 2026-11-06)

**Gruppo 1 — indice unico «Idempotenza import» su un documento: si sostituisce** con l'indice non unico sulle stesse
colonne e lo stesso predicato (forma di `20260709-01`), e si riscrive il `COMMENT`.

| Tabella | Indice | Righe con sorgente |
| --- | --- | --- |
| `vendite.ordini` | `uq_ordini_v_sorgente_fk` | 0 |
| `vendite.ordini_righe` | `uq_ordini_righe_v_sorgente_fk` | 0 |
| `vendite.fatture` | `uq_fatture_v_sorgente_fk` | 0 |
| `vendite.fatture_righe` | `uq_fatture_righe_v_sorgente_fk` | 8 (`COMMESSA`, solo dal builder `dbops.fn_pgtap_fattura_attivita`) |
| `acquisti.ordini` | `uq_ordini_v_sorgente_fk` | 0 |
| `acquisti.ordini_righe` | `uq_ordini_righe_v_sorgente_fk` | 0 |
| `acquisti.ddt` | `uq_ddt_v_sorgente_fk` | 0 |

**Gruppo 2 — commento sbagliato («Origine import», «tipo sorgente import», «Identificatore esterno documento»): si
riscrive** come provenienza interna (O-10, questo §9):

* `sorgente_tipo_id` / `sorgente_uid` / `sorgente_riga` delle tabelle del gruppo 1;
* `vendite.ddt` (l'indice è già a posto dal 2026-07, i commenti no);
* `vendite.attivita_fatturabili`;
* `magazzino.eventi_assets` e `magazzino.trasferimenti`.

**Gruppo 3 — magazzino, da decidere (M-1, §9.4):** `eventi_assets`, `inventari`, `rettifiche`, `trasferimenti`.

**Sani, non si toccano:** testate di preventivi e offerte (non hanno colonne sorgente), `contratti` e `resi`
(commento corretto, nessun indice d'import), le righe del lotto A (`preventivi_righe`, `ddt_righe`, `contratti_righe`,
`acquisti.ddt_righe`), `magazzino.movimenti` / `movimenti_attesi`, `documenti.documenti_generati`, e le tabelle di
collegamento (`commesse_sorgenti`, `pratiche_sorgenti`, `documenti_fatturazione_canali`).

**Documentazione:** si corregge con i `COMMENT`, nelle pagine `docs/it/dbzero/<schema>/tabelle/` e `…/manual/`
delle tabelle toccate. Pagine che nominano gli indici o «import»: `vendite` ordini, ordini_righe, fatture,
fatture_righe, attivita_fatturabili, trgfn_attivita_fatturabili_normalize; `acquisti` ordini, ordini_righe, ddt;
`magazzino` eventi_assets, inventari, rettifiche, trasferimenti; `script/funzioni/fn_check_preventivo_annullabile`.
I brief in `work-done/` che li citano restano come sono: sono storia.

### 9.4 M-1 — magazzino: gli indici unici delle quattro testate (⏳ Tid)

`inventari`, `rettifiche`, `trasferimenti` ed `eventi_assets` hanno ciascuna un indice unico su `(sorgente_tipo_id,
sorgente_uid)`, nato nell'ondata del 2025-10. Il 2026-09-15 il Lotto 1 del magazzino (`20260915-11`) ha aggiunto
`sorgente_riga` e il `CHECK` di chiave, ma **non ha toccato gli indici**: `analisi-db-magazzino-aggancio-documento-e-produzione`
§8, riga D-2, li lascia «da decidere se servono». Oggi:

* 27 sorgenti su 29 hanno chiave `id`, quindi la chiave va in `sorgente_riga` e `sorgente_uid` resta NULL: per quelle
  l'indice **non controlla niente**;
* l'indice morde solo con `PREVENTIVO` o `OFFERTA_COMMERCIALE` come sorgente di una testata di magazzino, cioè dove
  non ha senso;
* nessuna testata ha oggi una sorgente scritta (inventari 2 righe, rettifiche 81, tutte senza), e nessun verbo DB la
  scrive.

La domanda è di modello: **«al massimo un inventario / una rettifica / un trasferimento / un evento per documento di
partenza» è una regola del dominio?** Se sì, si scrive per quella testata, sulla chiave vera `(sorgente_tipo_id,
sorgente_riga)`, con il suo nome e il suo `COMMENT`. Se no, l'indice segue il gruppo 1.

### 9.5 Debito emerso dal censimento (non si risolve qui)

* `vendite.ddt`: 215 testate con `ORDINE_VENDITA` (chiave `id`) scrivono la chiave in `sorgente_uid`, fuori dal
  modello A. La testata non ha `sorgente_riga`.
* `magazzino.inventari.sorgente_tipo_id` **non ha la FK** verso `config.sorgenti`; le altre tre testate ce l'hanno.
* I guard polimorfi delle quattro testate di magazzino sono montati **senza argomenti**: ammettono qualunque sorgente.
* `vendite.fatture_righe` non ha il `CHECK` di chiave, e il builder pgTAP scrive insieme `sorgente_uid` e
  `sorgente_riga`.
