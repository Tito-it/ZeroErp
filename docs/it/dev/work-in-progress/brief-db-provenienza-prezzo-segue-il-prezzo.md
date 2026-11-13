# Brief DB — La provenienza del prezzo viaggia con il prezzo, dal documento alla commessa

## ⏭️ Chi riparte — aggiornato al 2026-11-13

**Riparte: team BE/FE** con la richiesta K-1 … K-7 (§8.7), e in parallelo il **team DB** col giro 3 (le
copie a valle, R-4, e il contesto dei componenti, D-3), al via di Tid. I giri 1 e 2 sono applicati e verdi
(Tid, 2026-11-13, §8.6 e §8.7), non ancora committati.
Riverificato il 2026-11-13 sul catalogo di dbdev e su `backend/` (§7): R-3, R-4 e il §4 avevano
definizioni superate, marcate ⚠️ e corrette al §7.1. ⚠️ Il commit `a85b76d58` «Chiusura brief
brief-db-provenienza-prezzo-segue-il-prezzo» chiude in realtà
`brief-db-coerenza-listino-della-riga-di-commessa`: **questo brief è aperto**.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Il difetto, il contratto, la richiesta; il push non scrive più `listino_riga_id` | §1-§3, §6.0 | — |
| 2 | ✅ sessione BE | Le righe dell'offerta (`offerte_commerciali_eccezioni`) aggiunte al perimetro (2026-11-12) | §2, R-1 | 1 |
| 2b | ✅ team DB | Riverifica sul catalogo: cosa regge, cosa è superato, le decisioni nuove (2026-11-13) | §7 | 2 |
| 2c | ✅ Tid | D-1, D-2, D-3 come proposte dal team DB (2026-11-13) | §7.3 | 2b |
| 3 | ✅ team DB | Il progetto (2026-11-13) | §8 | 2c |
| 3b | ✅ Tid | Il via allo sviluppo, numerazione da `20261113-01` (2026-11-13) | §8 | 3 |
| 3c | ✅ team DB | Giro 1: dominio, coerenza, colonne, derivazione e decadenza, guard, kit; prova in transazione (2026-11-13) | §8.6 | 3b |
| 3d | ✅ Tid | Apply del giro 1 e pgTAP del §8.6: verdi (2026-11-13) | §8.6 | 3c |
| 3d-bis | ✅ Tid | D-4: sì, la riga di listino citata da un documento si blocca (2026-11-13) | §8.5 | — |
| 3e | ✅ team DB | Giro 2: il push porta la provenienza (R-3, R-5), D-4; prova in transazione (2026-11-13) | §8.7 | 3d |
| 3f | ✅ Tid | Apply del giro 2 e pgTAP del §8.7: verdi (2026-11-13) | §8.7 | 3e |
| 4 | **team BE/FE** ⏭️ | La richiesta K-1 … K-7: push, componenti, pricing gate, form, test | §8.7 «Richiesta BE» | 3f |
| 5 | **team DB** ⏭️ | Giro 3 (le copie a valle, R-4; il contesto dei componenti, D-3), poi giro 4 | §8.5 | 3f, via di Tid |

**Decisioni aperte di Tid:** nessuna. Decise il 2026-11-13: D-1, D-2, D-3 (§7.3), D-4 (§8.5). F-9 non è
servita: il cantiere degli stati non ha toccato `fn_list_ordini_da_pushare`, e il giro 2 riparte dal suo
corpo vivo. **Lavoro da committare:** i giri 1 e 2 (ventidue changeSet, tre CSV, due pgTAP nuovi, quattro
adeguati), il brief, la riga di PROJECT_CONTEXT.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB
> (`dev/db-tid`); poi BE (§6), che **attende** la consegna DB.
> **Origine:** revisione delle modifiche di
> [brief-db-riga-listino-propagata-dalla-commessa](../work-done/brief-db-riga-listino-propagata-dalla-commessa.md)
> (§7). **Decisione:** di Tid, 2026-10-09 (variante «B»): una riga di commessa
> cita una riga di listino **solo se il suo prezzo è venuto davvero da lì**, non
> perché il listino, interrogato dopo, darebbe quella riga.
> **Stato:** 🟡 da progettare (DB). Il BE ha già tolto la parte che contraddice la
> decisione (§6.0); il resto attende.

## 1. Il difetto, con un esempio

* Il listino dice: articolo X a **50 €** (riga di listino R).
* Un ordine confermato ha X a un prezzo trattato di **40 €**.
* Il push porta in commessa la riga a **40 €**: il prezzo dell'ordine, ed è giusto.
* Ma la provenienza la scrive **chiedendo al resolver** «quanto costerebbe X oggi?»
  (`commesse_source_handlers._resolve_pricing_audit` → `provenienza_da_resolver`).
  Il resolver risponde «50 €, riga R, versione V, origine `CATEGORIA`», e la riga
  di commessa dice: **prezzo 40 €, venuto dal listino R a 50 €**.

Due conseguenze:

1. **R diventa «propagata»** (`trgfn_listini_righe_guard_stato`): non si può più
   rettificare (N6) né cancellare, anche se nessun documento ha mai portato il suo
   prezzo. Il guard protegge la riproducibilità di un prezzo **usato**, e qui non
   c'è niente da proteggere: il prezzo della commessa è riproducibile
   dall'ordine, non dal listino.
2. **La provenienza mente** su tutti i campi, non solo sulla riga di listino:
   `origine_prezzo`, `prezzo_base_snapshot`, `promo_id`, `contratto_id`,
   `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`,
   `listino_versione_id` descrivono il prezzo del listino, accanto a un
   `prezzo_snapshot` che viene dal documento. La riga di listino è solo il primo
   campo in cui la bugia ha un effetto (un blocco).

## 2. Perché il push non può saperlo (contratto, doc auto-generata, 2026-10-09)

Il prezzo arriva in commessa dalla riga del documento, attraverso le
`fn_list_<sorgente>_da_pushare`, che restituiscono `prezzo_snapshot` e
`prezzo_bloccato` e **nient'altro** del prezzo.

| Tabella | Prezzo | Provenienza |
| --- | --- | --- |
| `preventivi_righe`, `ordini_righe`, `contratti_righe`, `ddt_righe` | `prezzo_unitario` (+ `sconto_percentuale`, non su contratti) | ❌ nessuna colonna |
| `*_righe_componenti` (le stesse quattro famiglie) | `prezzo_unitario` | ✅ `origine_prezzo` (NOT NULL tranne DDT) e `prezzo_resolver_context` |
| `offerte_commerciali_eccezioni` (le righe dell'offerta) | `prezzo_unitario` | ❌ nessuna colonna |
| `offerte_commerciali_eccezioni_componenti` | `prezzo_unitario` | ✅ `origine_prezzo` (NOT NULL) e `prezzo_resolver_context` |

Le righe dell'offerta sono aggiunte il 2026-11-12 (doc auto-generata del 2026-11-09): la tabella si
dichiara «mirror fedele di `contratti_righe`», copiata 1:1 da `fn_push_offerta_a_contratto`, ed è il
primo anello della catena offerta → contratto → commessa. Senza la provenienza lì, la catena la perde
all'origine.

> ⚠️ Tabella **incompleta** al 2026-11-13: lo sconto manca anche sull'offerta, i componenti citano la
> riga di listino dentro `prezzo_resolver_context` e il loro `CHECK` ha un valore in più
> (`LISTINO_BUNDLE`). I fatti corretti al §7.1, F-1.

Cioè: **i componenti dicono già da dove viene il loro prezzo, le righe padre no**.
È un'asimmetria del modello. Chi scrive il prezzo di una riga di documento (spesso
precompilato dal resolver: l'endpoint di pricing restituisce già
`listino_riga_id`, `views_pricing.py`) non lo dichiara, e a valle nessuno può
ricostruirlo.

⛔ **Soluzione da scartare: confrontare i prezzi.** «Se il prezzo del documento è
uguale a quello del resolver, allora viene dal listino» è una coincidenza, non un
fatto: un prezzo trattato può essere uguale per caso, e un prezzo preso da una
versione precedente risulta «diverso» pur essendo venuto dal listino.

## 3. Richiesta

| # | Cosa |
| --- | --- |
| **R-1** | **Le righe di documento dichiarano la provenienza del prezzo**, come i componenti. Su `preventivi_righe`, `ordini_righe`, `contratti_righe`, `ddt_righe` e `offerte_commerciali_eccezioni` (le righe dell'offerta, §2; la simmetria strutturale con `contratti_righe` va conservata): le colonne di provenienza che `commesse_attivita` ha già (`origine_prezzo` con lo stesso `CHECK`, `prezzo_base_snapshot`, `listino_versione_id`, `listino_riga_id`, `promo_id`, `contratto_id`, `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`, `tipo_variazione_applicata`, `valore_variazione_applicata`). L'insieme esatto lo decide il team DB; il criterio è «quello che serve a riprodurre il prezzo». ⭐ Simmetria piena con i componenti, nello stesso giro: o i componenti acquistano le stesse colonne, o si scrive perché non servono (cfr. D-2 del brief chiuso: il loro guard è già più severo). |
| **R-2** | **La regola su chi scrive.** Un prezzo scritto senza provenienza è `MANUALE`, e un prezzo `MANUALE` non cita listino (riga, versione, base `NULL`). Da decidere se la regola sta in un `CHECK` (coerenza fra `origine_prezzo` e colonne di listino) o in un guard. ⚠️ Una modifica del solo `prezzo_unitario` dopo la precompilazione dal listino deve far decadere la provenienza da listino: altrimenti si torna al §1 (prezzo a mano, provenienza dal listino). |
| **R-3** | ⚠️ **Superata in tre punti (2026-11-13, §7.1 F-2 … F-5):** i componenti non passano dalle `fn_list_*`; i contratti senza prezzo di riga escono **con** il prezzo del listino, risolto dal DB; il DDT prende il prezzo dall'ordine quando la sua riga non ce l'ha. Testo originale: **Il legame segue il prezzo nel push.** Le cinque `fn_list_*_da_pushare` restituiscono la provenienza della riga (o del componente) accanto a `prezzo_snapshot`. Per le righe che **non** hanno un prezzo alla sorgente (`prezzo_snapshot NULL`: contratti e DDT senza prezzo, `prezzo_bloccato = FALSE`), la provenienza resta `NULL`: il prezzo lo darà il listino più tardi, e chi lo scrive scrive anche la provenienza (riallinea, sblocca — già così lato BE). |
| **R-4** | ⚠️ Censimento fatto il 2026-11-13: le funzioni sono sette, non quattro (§7.1 F-7). **La copia a valle dei documenti.** Le funzioni che copiano una riga da un documento all'altro (revisione preventivo/offerta, offerta → contratto, ordine → DDT: `fn_crea_revisione_preventivo`, `fn_crea_revisione_offerta`, `fn_push_offerta_a_contratto`, `fn_genera_ddt_da_ordine`, e le altre che il team DB trova) copiano la provenienza con il prezzo. Da censire. |
| **R-5** | **Consumi.** `fn_list_consumi_da_pushare` ha `prezzo_bloccato = FALSE` «per una ragione diversa» (commento nella funzione): da dire che cosa vuol dire la provenienza per un consumo. |
| **R-6** | **pgTAP**, sul caso costruito: un ordine con prezzo trattato diverso dal listino → la riga di commessa ha origine `MANUALE` (o quella dichiarata) e `listino_riga_id NULL`, e la riga di listino resta rettificabile; un ordine con prezzo precompilato dal listino e non toccato → la riga di commessa cita R, e R è «propagata»; lo stesso ordine con il prezzo cambiato dopo la precompilazione → la provenienza da listino è decaduta (R-2). |

## 4. Rapporto con gli altri brief

* [brief-db-coerenza-listino-della-riga-di-commessa](../work-done/brief-db-coerenza-listino-della-riga-di-commessa.md) (chiuso il 2026-10-17)
  dice che cosa la colonna `listino_riga_id` **può** contenere (stessa versione,
  stesso emittente, versione in vigore). Questo dice **quando** si scrive. Il guard
  di quel brief va montato anche sulle righe di documento di R-1: la stessa regola,
  in più tabelle — candidato building block. ⚠️ Superato (2026-11-13, §7.1 F-8): il BB esiste già
  (`vendite.fn_check_listino_provenienza`), ma prende la commessa; va generalizzato, non estratto.
* Il percorso rapido del resolver che legge una versione in `BOZZA` (stesso brief,
  §1) riguarda anche la precompilazione delle righe di documento.
* Il 2026-10-21 (richiesta BE dello smoke `smoke-group-attivita-contratto`, D-1 di
  Tid) è nata la regola gemella su `contratto_id`: il contratto citato è del billing
  account della commessa (`vendite.fn_check_contratto_provenienza` +
  `vendite.trgfn_attivita_guard_contratto`, `20261021-64…66`), su `commesse_attivita`
  e `attivita_fatturabili`. Dice che cosa `contratto_id` **può** contenere, come il
  brief qui sopra per `listino_riga_id`. Se R-1 porta `contratto_id` sulle righe di
  documento, la stessa regola va montata anche lì; la coerenza fra `origine_prezzo
  CONTRATTO_*` e `contratto_id` valorizzato resta di R-2.

## 5. Fuori da questo brief

* Il recupero delle righe esistenti: il progetto non è in produzione. Le righe di
  documento già scritte restano senza provenienza (cioè, per R-2, `MANUALE`, se il
  team DB sceglie un default).
* Il riallineamento e lo sblocco: prendono **davvero** il prezzo dal listino, e già
  scrivono la provenienza intera, riga di listino compresa. Corretti per la
  decisione B, non si toccano.

## 6. Ricaduta BE

**6.0 — Già fatto il 2026-10-09 (non attende il DB).** Il push non scrive più
`listino_riga_id` preso dal resolver (`commesse_source_handlers._build_attivita_input`):
oggi non sa se il prezzo viene dal listino, e per la decisione B il valore onesto è
`NULL`. Non c'è rischio da questo lato: il prezzo della riga di commessa è
riproducibile dal documento, non dalla riga di listino. Il resto della provenienza
del push (origine, base, versione…) **resta** dal resolver fino alla consegna: il
guard «versione cambiata» del riallineamento la legge, e cambiarla da sola sarebbe un
tampone.

**Dopo la consegna DB:**

1. `PushableRow` acquista le colonne di provenienza restituite da R-3;
   `_build_attivita_input` le copia e **smette di chiamare il resolver per la
   provenienza** (`_resolve_pricing_audit` e la sua cache spariscono, se nient'altro
   li usa).
2. Le scritture delle righe di documento (service di preventivi, ordini, contratti,
   DDT) passano la provenienza ricevuta dalla precompilazione; un prezzo modificato a
   mano la passa `MANUALE` (o la lascia decadere al DB, secondo R-2).
3. FE: il form della riga conserva la provenienza restituita dall'endpoint di pricing
   e la manda con il prezzo; se l'operatore cambia il prezzo, la provenienza decade.
4. Test sul DB vero: i tre casi di R-6, dal push in su.

## 7. Riverifica per la ripartenza (team DB, 2026-11-13)

Fonte: il catalogo di dbdev (`pg_get_functiondef`, `information_schema`, `pg_constraint`), perché dal
2026-11-09 (ultima doc auto-generata citata sopra) sono stati applicati changeSet sugli stessi oggetti
(`20261112-02 … -07`, `-09`, `-11`, `-23`, `-24`); e `backend/` per il §6.0. Sono letture di
**struttura**, non conteggi.

**Reggono:** il difetto del §1 (il push chiama ancora il resolver per origine, base, versione, promo,
contratto, categoria, classe: `_build_attivita_input` → `_resolve_pricing_audit` →
`provenienza_da_resolver`); le righe padre senza alcuna colonna di provenienza (§2); la decisione B; il
§5; il §6.0 (`listino_riga_id` non è più passato dal push); le funzioni nominate in R-4 e nel §4
esistono tutte; il commento di `fn_list_consumi_da_pushare` citato da R-5 è ancora quello.

### 7.1 Che cosa è superato o incompleto

* **F-1 — la tabella del §2.** Lo `sconto_percentuale` manca su `contratti_righe` **e** su
  `offerte_commerciali_eccezioni` (c'è su preventivi, ordini, DDT). I componenti non hanno solo
  `origine_prezzo`: la riga di listino la scrivono le cinque `fn_*_riga_componenti_init` dentro
  `prezzo_resolver_context` (`jsonb`, chiave `listino_riga_id`), dove nessun guard di coerenza la
  vede. Il loro `CHECK` ammette **sei** origini, con `LISTINO_BUNDLE`; quello di `commesse_attivita` e di
  `attivita_fatturabili` **cinque**, e il BE trasforma in silenzio `LISTINO_BUNDLE` in `NULL`
  (`origine_ammessa`, «whitelist contro il CHECK DB»). Quindi «`origine_prezzo` con lo stesso `CHECK`»
  di R-1 non dice quale dei due: D-2. Accanto al prezzo c'è anche il workflow L3 di approvazione
  (`stato_approvazione_prezzo`, `pratica_approvazione_prezzo_id`) su preventivi, contratti, offerta e
  su tutti i componenti, non su ordini e DDT: è un vicino di R-2 (un prezzo fuori policy è per
  definizione non del listino), non un pezzo di questo brief.
* **F-2 — R-3, i componenti.** Le `fn_list_*_da_pushare` restituiscono **solo righe padre**: i
  componenti li espande il BE (`BoMComponentExpander`, loader sulle `*_righe_componenti`, chiave
  `#CMP:<id>`), e portano già `origine_prezzo` nel `meta`. «Restituiscono la provenienza della riga
  (o del componente)» è sbagliato per i componenti: per loro la provenienza viaggia dalla proiezione
  del loader, ed è un lavoro BE (§7.2), con base, versione e riga ancora presi dal resolver anche per
  loro.
* **F-3 — R-3, i contratti** (superato da `20261030-01` e `20261031-35`). `fn_list_contratti_da_pushare`
  legge ora `vendite.fn_contratti_addebiti_maturati`, che per una riga senza prezzo suo (l'ADESIONE, la
  quota fissa del listino senza riga di contratto) **risolve lei il prezzo**
  (`fn_resolve_prezzo_listino_v2_esito`, o la somma dei componenti del kit da
  `fn_contratto_kit_componenti`), lo restituisce in `prezzo_snapshot` con `prezzo_bloccato = FALSE`, e
  scarta (`SENZA_PREZZO`) chi resta senza. Non esistono più righe di contratto «senza prezzo» che
  partono: R-3 per i contratti diventa «la funzione che ha in mano il risultato del resolver lo
  restituisce intero, invece del solo `prezzo_finale`». Oggi la sola riga di listino esce, ma nel
  **`meta`** (rami 1 e 3, chiave `listino_riga_id`), che finisce in `commesse_attivita.meta`: una seconda
  sede della provenienza, in `jsonb`, che il guard di coerenza non vede. Il ramo 2 (storni) prende il
  prezzo dalla riga di commessa che storna (`ca.prezzo_snapshot`): la sua provenienza è quella della
  riga stornata. Il kit a somma di componenti non ha una riga di listino sola: la sua origine va
  scritta (D-2).
* **F-4 — R-3, il DDT.** Il prezzo è `COALESCE(ddt_righe.prezzo_unitario, ordini_righe.prezzo_unitario)`
  e `prezzo_bloccato` è «prezzo valorizzato»: la provenienza va presa con lo **stesso** `COALESCE`, dalla
  riga d'ordine quando la riga del DDT non ha prezzo.
* **F-5 — R-3, il preventivo.** `prezzo_bloccato = fatturazione_immediata`: un preventivo esce con un
  prezzo **valorizzato e non bloccato**. La dicotomia di R-3 («prezzo `NULL` ⇒ non bloccato ⇒
  provenienza `NULL`») non lo copre: la provenienza del documento viaggia comunque, e il riallineamento,
  se riscrive il prezzo, riscrive anche la provenienza (§5).
* **F-6 — R-3, la riga-onere** (`20261103-38`, `-40`, addebito trasporto). Ordini e DDT restituiscono
  anche righe `ONERE` con `causale_onere_id`: stessa regola, nessun ramo a parte; va solo nel pgTAP.
* **F-7 — R-4, il censimento.** Le funzioni che inseriscono righe nelle cinque tabelle padre sono sette:
  `fn_crea_revisione_preventivo`, `fn_crea_revisione_offerta`, `fn_push_offerta_a_contratto`,
  `fn_genera_ddt_da_ordine` (le quattro del §3) e in più `fn_push_preventivo_a_ordine`,
  `fn_genera_ordine_da_offerta`, `fn_genera_ddt_riconsegna`. Le cinque `fn_*_riga_componenti_init`
  scrivono la provenienza dei componenti dal resolver (giusto, per B). ⭐ **Nessuna funzione DB aggiorna
  il `prezzo_unitario` di una riga padre**: lo scrive il BE in diretta. La regola di R-2 (il prezzo
  cambiato fa decadere la provenienza) non può stare in un verbo: sta sulla tabella (`CHECK` + trigger).
* **F-8 — §4, il building block.** Esiste: `vendite.fn_check_listino_provenienza(p_commessa_id,
  p_articolo_id, p_uom_id, p_listino_versione_id, p_listino_riga_id)` + `trgfn_attivita_guard_listino_riga`,
  montato su `commesse_attivita` e `attivita_fatturabili`; gemello `fn_check_contratto_provenienza
  (p_commessa_id, p_contratto_id)`. Tutti e due prendono **la commessa** per ricavare l'emittente e il
  billing account: per le righe di documento il primo argomento va generalizzato (il documento, o
  direttamente emittente e billing account), con le due sedi attuali riportate sulla firma nuova nello
  stesso giro (regola del 2). In più `commesse_attivita` ha `chk_commesse_attivita_listino_riga_con_versione`
  (riga ⇒ versione), da riportare su R-1.
* **F-9 — vicino nuovo.** [brief-db-stati-documento-dal-vocabolario](brief-db-stati-documento-dal-vocabolario.md)
  riscrive, nei suoi giri, `fn_list_ordini_da_pushare` (la «cintura» FATTURATO, ⑤) e cita
  `fn_crea_revisione_preventivo`: le stesse funzioni di R-3 e R-4. Il secondo cantiere che le tocca
  riparte dal catalogo dopo l'apply del primo, mai dal suo YAML; l'ordine lo dà Tid.

### 7.2 Ricaduta BE in più (da aggiungere al §6 alla consegna)

* Il loader dei componenti del push (proiezione delle `*_righe_componenti`) restituisce la provenienza
  intera, e `_build_attivita_input` smette di chiedere al resolver base e versione anche per loro.
* `origine_ammessa` sparisce (D-2): oggi nasconde un disaccordo fra due `CHECK` del DB.
* Chi legge `listino_riga_id` da `prezzo_resolver_context` o dal `meta` delle righe di commessa passa alla
  colonna (D-3): l'elenco chiuso dei punti lo dà il team DB col progetto.

### 7.3 Decisioni — prese da Tid il 2026-11-13

Tutte e tre come proposte dal team DB («accetto le tue proposte e condizioni»).

* **D-1 — il fermo: il brief parte, con la condizione.** Il brief è nato il 2026-10-09, prima del fermo
  dei temi trasversali (PROJECT_CONTEXT, 2026-10-21, allentato il 2026-10-25, scelta C), e non era mai
  partito. R-1 tocca le righe di cinque documenti di vendita: entra nel ramo «ammesso» perché poggia su un
  pezzo comune. ⛔ **Condizione:** le colonne e la regola nascono **una volta** — il BB di F-8
  generalizzato (dalla commessa al documento, con le due sedi attuali riportate sulla firma nuova nello
  stesso giro) e un trigger generico di decadenza montato per argomenti sulle cinque tabelle — non
  ricopiate documento per documento. Un progetto che chiede cinque corpi di funzione uguali non rispetta
  D-1.
* **D-2 — un solo insieme di origini.** `origine_prezzo` ha lo stesso dominio dalle righe di documento ai
  componenti, a `commesse_attivita` e ad `attivita_fatturabili`: `LISTINO_BUNDLE` entra anche in commessa
  e nelle attività fatturabili, e il BE toglie `origine_ammessa` (§7.2). Il dominio si scrive in una
  sede sola (il team DB propone la forma: dominio, vocabolario o `CHECK` generato). Dentro c'è il kit a
  somma di componenti di F-3: la sua origine la propone il team DB col progetto.
* **D-3 — una sede sola per la riga di listino: la colonna.** `listino_riga_id` (con la versione) è una
  colonna, controllata dal BB di F-8, sulle righe di documento (R-1) **e** sui componenti. Esce da
  `prezzo_resolver_context` dei componenti e dal `meta` del push dei contratti (rami 1 e 3 di
  `fn_contratti_addebiti_maturati`), dove nessun guard la vede.

## 8. Il progetto (team DB, 2026-11-13) — via allo sviluppo di Tid lo stesso giorno

Tid ha dato il via allo sviluppo il 2026-11-13 («procedi con lo sviluppo»), con la numerazione da
`20261113-01`. Il progetto qui sotto lo applica in quattro giri; ognuno si prova in transazione e si
consegna a Tid per l'apply e i pgTAP prima del successivo.

### 8.1 Un fatto nuovo: le righe principali hanno già una provenienza, nel `meta`, e decisa confrontando i prezzi

Trovato scrivendo il progetto (`backend/apps/vendite/services/_pricing_gate_helpers.py`,
`resolve_or_check_override_prezzo`, chiamato da preventivi, offerte, contratti): il BE scrive nel `meta`
della riga `origine_prezzo` e `prezzo_resolver_context` (origine, listino, contratto, promo, variazione;
**né riga né versione** di listino). E decide che il prezzo «viene dal listino» quando il prezzo del
payload è **uguale** a quello del resolver, a 4 decimali: è la soluzione che il §2 scarta. Con questo
brief la sede diventa la colonna, e il BE smette di decidere per confronto: la provenienza la dichiara
chi precompila (§8.5, richiesta BE).

### 8.2 Le colonne (D-3) e il dominio delle origini (D-2)

| Tabelle | Colonne nuove |
| --- | --- |
| le cinque righe principali (`preventivi_righe`, `ordini_righe`, `contratti_righe`, `ddt_righe`, `offerte_commerciali_eccezioni`) | `origine_prezzo`, `listino_versione_id` (FK), `listino_riga_id` (FK), `prezzo_resolver_context` (`jsonb`) |
| i cinque componenti (`*_righe_componenti`, `offerte_commerciali_eccezioni_componenti`) | `listino_versione_id` (FK), `listino_riga_id` (FK): `origine_prezzo` e `prezzo_resolver_context` li hanno già |

* ⭐ **Simmetria con i componenti** (R-1): righe principali e componenti portano la provenienza nella
  stessa forma. In colonna ciò che un guard deve giudicare (origine, versione, riga: D-3); nel `jsonb`
  il resto del risultato del resolver (base, variazione, promo, contratto, categoria, classe), come i
  componenti fanno già. Il push lo porta nelle colonne di `commesse_attivita` (giro 2). `contratto_id`
  e `promo_id` sulle righe di documento non sono riferimenti giudicati: è la fotografia del resolver,
  e il guard del contratto resta dove il contratto è un riferimento, in commessa.
* **Il dominio delle origini** (D-2) ha una sede sola, `vendite.fn_origine_prezzo_ammessa`, letta dai
  `CHECK` di tutte le tabelle (i sette `CHECK` di oggi, con gli stessi nomi, e i cinque nuovi). Sette
  valori: i cinque di oggi, `LISTINO_BUNDLE` (fin qui solo sui componenti) e **`COMPONENTI`, nuovo**:
  «il prezzo è la somma dei componenti, la provenienza sta su ciascuno di loro». È l'origine della
  riga principale di un kit, il cui prezzo lo scrive `script.fn_ricalcola_prezzo_padre_da_componenti`,
  e del kit a somma del push contratti (F-3).
* **La coerenza** ha una sede sola, `vendite.fn_provenienza_prezzo_coerente`, letta da un `CHECK` su
  ciascuna delle dieci tabelle: senza prezzo, nessuna provenienza; con un prezzo, un'origine; una riga
  di listino porta la sua versione; `MANUALE` e `COMPONENTI` non citano listino.
* **Le righe che ci sono** (§5): `COMPONENTI` dove la riga ha componenti, `MANUALE` dove ha un prezzo,
  nessuna origine senza prezzo. L'allineamento passa senza i trigger della tabella (colonna nuova, non
  un fatto di dominio: la forma di `20261011-69`).
* Le FK nuove: `CON_INDICE` parziale (`WHERE … IS NOT NULL`, come `commesse_attivita`) in
  `fk_index_policy.csv`; esenti dal guard ATTIVO generato (`automazione_attivo_eccezioni.csv`): una
  riga di documento cita la riga di listino da cui il prezzo **è venuto**, anche se poi la si spegne, e
  il guard REQUIRE scatta a ogni `UPDATE` della riga e fermerebbe la revisione o la modifica della
  quantità.

### 8.3 Chi scrive (R-2): un trigger generico, montato sulle dieci tabelle

`vendite.trgfn_riga_documento_provenienza_prezzo`, `BEFORE INSERT OR UPDATE`, fase `a20` (derivazione):

* un prezzo senza origine è `MANUALE`; senza prezzo origine, riga e versione si svuotano;
* ⭐ **la decadenza**: se in un `UPDATE` cambiano prezzo, articolo o unità di misura e la provenienza
  (origine, versione, riga, contesto) resta com'era, una provenienza da listino decade a `MANUALE`, con
  riga, versione e contesto a `NULL`. `MANUALE` e `COMPONENTI` non decadono. Chi riprende davvero il
  prezzo dal listino scrive la provenienza nuova nella stessa istruzione, e passa.
* Il trigger non conosce i nomi diversi: l'articolo della riga è `articolo_id` sulle righe principali e
  `componente_id` sui componenti, ed entra come argomento del montaggio.

### 8.4 Il guard di coerenza (F-8): il BB generalizzato

* `vendite.fn_check_listino_provenienza_emittente(emittente, articolo, uom, versione, riga)`: le tre
  regole di oggi (riga coerente con articolo, UoM e versione; listino dell'emittente; mai una bozza),
  con l'**emittente** al posto della commessa. `vendite.fn_check_listino_provenienza(commessa, …)` resta
  con la sua firma e diventa l'adattatore della commessa (ricava l'emittente e chiama il BB): la regola
  è scritta una volta, il guard della commessa e i suoi pgTAP non cambiano.
* `vendite.trgfn_riga_documento_guard_listino_provenienza`, `AFTER INSERT OR UPDATE`, sulle dieci
  tabelle: ricava l'emittente dalla testata del documento (`emittente_fiscale_id` →
  `anagrafiche.emittenti_fiscali.soggetto_ruolo_id`; per i componenti, attraverso la riga principale) e
  solleva il primo motivo, con gli stessi codici della commessa. La frase di
  `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO` diventa «del suo documento o della sua commessa».
* L'unità di misura confrontata è `uom_operativa_id`: è quella con cui il BE chiama il resolver
  (`preventivi_service`, `offerte_service`) e con cui le `fn_*_riga_componenti_init` lo chiamano.

### 8.5 I giri

| Giro | Che cosa | changeSet |
| --- | --- | --- |
| **1** | §8.2, §8.3, §8.4: dominio, coerenza, colonne, allineamento, trigger, BB, kit a `COMPONENTI`; CSV di FK, eccezioni ATTIVO, messaggio; pgTAP nuovo | `20261113-01 …` |
| 2 | R-3: le cinque `fn_list_*_da_pushare` e `fn_contratti_addebiti_maturati` restituiscono la provenienza (F-3 … F-6); il `meta` del push contratti perde `listino_riga_id`. D-4: la riga di listino citata da un documento è «propagata» | dopo il giro 1 |
| 3 | R-4: le sette funzioni di copia e le cinque `fn_*_riga_componenti_init` scrivono le colonne; `listino_riga_id`/`listino_versione_id` escono da `prezzo_resolver_context` (D-3) | dopo il giro 2 |
| 4 | R-5 (consumi: nessuna provenienza, il prezzo lo dà il listino più tardi), R-6 dal push in su, doc `manual/`, la richiesta BE chiusa | dopo il giro 3 |

**Richiesta BE** (si consegna al giro 2, quando il contratto del push è scritto; elenco completo allora):
il pricing gate scrive le colonne (`origine_prezzo`, `listino_versione_id`, `listino_riga_id`,
`prezzo_resolver_context`) invece del `meta`, e smette di dedurre la provenienza confrontando i prezzi
(§8.1); `origine_ammessa` sparisce (D-2); `PushableRow`, il loader dei componenti e
`_build_attivita_input` come al §6 e al §7.2.

**D-4 — decisa da Tid il 2026-11-13: sì, si blocca.** Una riga di listino citata da una riga di documento
(righe principali e componenti delle cinque famiglie) è «propagata» come quella citata da una commessa:
in una versione ATTIVA non si rettifica e non si cancella (`E_RIGA_LISTINO_PROPAGATA`). Basta anche una
bozza: il prezzo è stato usato, e per cambiarlo si fa una versione nuova del listino. Scartata la via di
mezzo «solo fuori bozza»: legherebbe la regola agli stati di ogni documento. Sede: la sola
`vendite.trgfn_listini_righe_guard_stato`, che oggi guarda commesse e attività fatturabili; le venti FK
hanno già il loro indice parziale (§8.2). Entra nel **giro 2**, col suo pgTAP (rettifica e cancellazione
rifiutate per una riga citata da un preventivo in bozza e da un componente; ammesse per una non citata).
Fino ad allora la rettifica (`UPDATE`) di una riga citata passa, e la cancellazione la ferma la FK
(`23503`, senza frase di dominio).

### 8.6 Giro 1 — scritto e provato il 2026-11-13, applicato e verde lo stesso giorno (Tid)

| changeSet | Che cosa |
| --- | --- |
| `20261113-01` | `vendite.fn_origine_prezzo_ammessa`: l'elenco unico delle origini (sette valori) |
| `20261113-02` | `vendite.fn_provenienza_prezzo_coerente`: la coerenza fra prezzo e provenienza |
| `20261113-03` | i sette `CHECK` sulle origini (commessa, attività fatturabili, cinque componenti) leggono l'elenco unico, stessi nomi |
| `20261113-04` | le colonne sulle dieci tabelle, l'allineamento delle righe che ci sono (senza i trigger della tabella), i dieci `CHECK` di coerenza |
| `20261113-05` | `vendite.fn_check_listino_provenienza_emittente`: il BB con l'emittente al posto della commessa |
| `20261113-06` | `vendite.fn_check_listino_provenienza` (commessa) diventa l'adattatore del BB: firma, proprietà e privilegi invariati |
| `20261113-07` | `vendite.fn_riga_documento_emittente`: l'azienda del documento di una riga o di un componente, `SECURITY DEFINER` |
| `20261113-08` | `vendite.trgfn_riga_documento_provenienza_prezzo`: derivazione e decadenza (§8.3) |
| `20261113-09` | `vendite.trgfn_riga_documento_guard_listino_provenienza`: il guard `AFTER` sulla riga di listino (§8.4) |
| `20261113-10` | i due trigger montati sulle dieci tabelle |
| `20261113-11` | `vendite.fn_upsert_commessa_attivita`: la sua copia dell'elenco delle origini (cinque valori, avrebbe rifiutato `LISTINO_BUNDLE` e `COMPONENTI`) chiede l'elenco unico; testata ancorata con `%TYPE`. Trovata scrivendo il giro: era una terza sede del dominio |
| `20261113-12` | `script.fn_ricalcola_prezzo_padre_da_componenti`: con il prezzo del kit scrive `COMPONENTI`, senza listino |

CSV: `config/messaggi_errore.csv` (la frase di `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO` dice «documento o
commessa»), `dbops/fk_index_policy.csv` (venti FK nuove, `CON_INDICE` parziale), `dbops/automazione_attivo_eccezioni.csv`
(le stesse venti, esenti dal guard ATTIVO generato, §8.2).

**pgTAP.** Nuovo `vendite/test-provenienza-prezzo-riga-documento-v1` (17): le due regole come funzioni pure,
la forma (colonne, `CHECK`, montaggi per funzione), MANUALE alla nascita, la provenienza dichiarata che
passa, la quantità che non la tocca, il prezzo che la fa decadere, prezzo e provenienza insieme che la
tengono, i tre rifiuti del guard e quello del `CHECK`, il kit a `COMPONENTI`, la commessa che ammette le
origini nuove. Adeguati, con la ragione sopra l'asserzione: i conteggi dei trigger di
`test-ordini-righe-componenti-v1` (16), `test-ddt-righe-componenti-v1` (17),
`test-contratti-righe-componenti-v1` (16) e l'elenco per funzione di `test-preventivi-righe-componenti-v1`.

**Prova** (`scripts/prova_changeset.py`, transazione ritirata, catalogo identico prima e dopo):

* sullo scratch, l'estratto con 48 pgTAP: il nuovo 17/17; i vicini (guard della commessa, i cinque
  componenti, righe gemelle, esclusione, approvazione del prezzo, lineage, accredito kit, prezzi
  autorizzati, distinta alla data, le righe di contratto, ordine, offerta, DDT) e i presidi trasversali
  (numerici finiti, riferimenti morti, politica FK, eccezioni ATTIVO, motivi nominati, catalogo dei
  messaggi) senza un rosso nuovo. `test-refactor-qta-operativa-preventivi-v1` ha 5 rossi uguali con e senza
  l'estratto: le sue fixture cercano dati che lo scratch non ha;
* su dbdev, l'estratto col pgTAP nuovo: allineamento e validazione dei dieci `CHECK` sulle righe vere
  passano, 17/17.
* La preCondition di `-04` (la funzione di `-02` esiste) è falsa in prova, perché si legge prima
  dell'estratto: all'apply `-02` è già passato.

**Da lanciare dopo l'apply (Tid):** il pgTAP nuovo, i quattro adeguati, e i presidi
`dbops/test-fk-index-policy-decisione-v1`, `dbops/test-automazione-attivo-eccezioni-v1` (in prova i CSV non
sono caricati: le venti FK nuove li toccano solo dopo il migrate). Il guard ATTIVO generato non deve
comparire sulle colonne nuove (`ci_apply` legge le eccezioni).

⚠️ **Il BE oggi.** Il BE non scrive ancora le colonne: le righe che scrive nascono `MANUALE`, e il pricing
gate continua a mettere la sua provenienza nel `meta` (§8.1). Nessuna rottura: le colonne sono nullable
dove il BE non le passa, e il trigger le deriva. `origine_ammessa` del BE resta innocua (ora il DB ammette
di più, non di meno). La richiesta BE si consegna col giro 2.

### 8.7 Giro 2 — il push porta la provenienza (R-3, R-5) e D-4; scritto e provato il 2026-11-13, applicato e verde lo stesso giorno (Tid)

| changeSet | Che cosa |
| --- | --- |
| `20261113-13` | `vendite.fn_provenienza_prezzo_esplosa(origine, versione, riga, contesto)`: le dieci colonne della provenienza di una riga di commessa. Sede unica della lettura del contesto (regola del 2: la usano cinque lister e i contratti) |
| `20261113-14` | `vendite.fn_contratti_addebiti_maturati_con_provenienza`: il corpo degli addebiti dei contratti con la provenienza in coda (F-3); `listino_riga_id` esce dal `meta` (D-3) |
| `20261113-15` | `vendite.fn_contratti_addebiti_maturati`: firma invariata, proiezione della `-14` |
| `20261113-16 … -20` | i cinque `fn_list_*_da_pushare` (preventivi, ordini, DDT, contratti, consumi): in coda le dieci colonne della provenienza; `DROP` + `CREATE`, `COMMENT` e `GRANT` di ritorno; gli id nudi del `RETURNS` ancorati a `vendite.commesse` |
| `20261113-21` | `vendite.trgfn_listini_righe_guard_stato`: D-4, le dieci tabelle delle righe di documento rendono «propagata» la riga di listino che citano |
| `20261113-22` | la scheda di `prezzo_resolver_context` sulle cinque righe principali dice le chiavi |

CSV: `config/messaggi_errore.csv`, causa e soluzione di `E_RIGA_LISTINO_PROPAGATA` (anche i documenti;
«si fa una versione nuova del listino»).

**Le scelte del giro.**

* **Il contratto delle colonne del push.** Ogni lister restituisce, in coda, `origine_prezzo`,
  `listino_versione_id`, `listino_riga_id`, `prezzo_base_snapshot`, `tipo_variazione_applicata`,
  `valore_variazione_applicata`, `promo_id`, `prezzo_contratto_id`, `categoria_cliente_id_snapshot`,
  `classe_utenza_id_snapshot`: i nomi e i tipi della riga di commessa, con `contratto_id` che esce come
  `prezzo_contratto_id` (in alcuni lister `contratto_id` è già il documento). Il BE le copia una a una in
  `CommessaAttivitaInput`.
* **Il contratto del contesto.** Le chiavi di `prezzo_resolver_context` sono i nomi delle colonne del
  risultato del resolver (`vendite.fn_resolve_prezzo_listino_v2_esito`). Così il risultato del resolver,
  passato intero (`to_jsonb`), è già un contesto: lo usano i contratti per ADESIONE e quote fisse, e lo
  userà il BE al pricing gate. Il contesto conta solo per un'origine da listino: con `MANUALE` o
  `COMPONENTI` i sette campi escono `NULL`, anche se qualcuno li ha scritti.
* **Per ramo:** preventivo e ordine, la riga (anche col prezzo non bloccato del preventivo, F-5, e per la
  riga-onere, F-6); DDT, la riga della bolla se ha il prezzo, altrimenti quella d'ordine, con lo stesso
  `COALESCE` del prezzo (F-4); contratto, la riga se ha il prezzo, `COMPONENTI` per il kit a somma, il
  resolver per ADESIONE e quota fissa, il pezzo stornato per lo storno (F-3); consumo, nessuna (R-5: il
  prezzo lo dà il listino più tardi, e chi lo scrive scrive la provenienza).
* **Perché una funzione nuova per i contratti.** Cambiare il `RETURNS` di `fn_contratti_addebiti_maturati`
  vuol dire toglierla, e la tiene `vw_dash_fatturazione_contratti` con cinque viste a valle (documenti,
  backlog, aperto, i riepiloghi) che il cantiere degli stati sta toccando. La vecchia resta come
  proiezione della nuova: la regola è scritta una volta. Ritirarla vuol dire riscrivere quella catena di
  viste: non è debito di questo brief, lo si fa quando la catena si riscrive per altro.

**Prova** (`scripts/prova_changeset.py`, transazione ritirata, catalogo identico prima e dopo):

* sullo scratch, l'estratto con 85 pgTAP: il nuovo `vendite/test-provenienza-prezzo-push-v1` 14/14; i
  lister (tutte le versioni), il push dei contratti, le dashboard, il listino (kit, UoM, rettifica,
  elimina versione, propagata dalla commessa), le capability, gli stati, il giro 1 e i presidi trasversali:
  nessun rosso nuovo. Rossi già presenti, uguali con e senza l'estratto: `test-chiudi-legame-con-prezzi-v1`,
  `test-fn-available-actions-ddt-reason-catch-all-v1`, `test-lista-competenza-gruppi-colonna-emittente-v1`,
  `test-annullo-documento-con-legami-v1` (1 ciascuno). Non lanciato: `test-fn-list-ordini-da-pushare-v1`,
  che non chiude in `ROLLBACK` (committa);
* su dbdev, il test nuovo, `test-push-contratto-canoni-v1` e `test-vw-dash-contratti-giudizio-v1`: verdi;
  la proiezione dei contratti confrontata sugli addebiti veri.

**Da lanciare dopo l'apply (Tid):** `vendite/test-provenienza-prezzo-push-v1`,
`vendite/test-fn-list-ordini-da-pushare-v1` (committa: non provato in transazione), i test dei lister e
del push dei contratti.

#### Richiesta BE (`dev/backend-tid`) — elenco chiuso del percorso

Il DB del giro 2 è il contratto. Il percorso intero, dalla riga del documento alla commessa:

| # | Dove | Che cosa |
| --- | --- | --- |
| K-1 | `db/commesse_repository.py` (`_PUSHABLE_SHARED_COLS`, `PushableRow`, `_map_pushable_row`) | le dieci colonne nuove dei lister |
| K-2 | `services/commesse_source_handlers.py` (`_build_attivita_input`) | la provenienza della riga va in `CommessaAttivitaInput` così com'è, `listino_riga_id` e `contratto_id` ← `prezzo_contratto_id` compresi; spariscono `_resolve_pricing_audit`, la sua cache e la lettura di `meta.origine_prezzo` (§6.1). `provenienza_da_resolver` resta per riallinea e sblocca, che il prezzo lo prendono davvero dal listino |
| K-3 | `services/prezzo_riga_commessa.py` (`origine_ammessa`) | sparisce (D-2): il DB ammette le stesse origini dalla riga alla commessa |
| K-4 | `db/_componenti_repo_mixin.py` e l'espansione dei componenti (`_build_componente_row_from_snapshot`) | il componente porta la sua provenienza al posto del solo `origine_prezzo` nel `meta`: la proiezione del loader legge `vendite.fn_provenienza_prezzo_esplosa(c.origine_prezzo, c.listino_versione_id, c.listino_riga_id, c.prezzo_resolver_context)` in `LATERAL`, senza ricopiarne la regola. Fino al giro 3 le colonne di riga e versione dei componenti sono vuote e il loro contesto ha chiavi vecchie: escono origine e poco altro, ed è corretto |
| K-5 | `services/_pricing_gate_helpers.py` (`resolve_or_check_override_prezzo`; chiamanti `preventivi_service`, `offerte_service`, `contratti_service`) e i repository che scrivono le righe | la provenienza va nelle colonne (`origine_prezzo`, `listino_versione_id`, `listino_riga_id`, `prezzo_resolver_context` = il risultato del resolver) e non più nel `meta`. ⛔ Non si deduce più «viene dal listino» da un prezzo uguale a quello del resolver (§2, §8.1): è da listino la riga precompilata (payload senza prezzo) o quella che dichiara la provenienza ricevuta dall'endpoint di pricing (K-6); il resto è `MANUALE`. Le chiavi d'audit dell'override (`prezzo_applicato`, `override_user_id`, `delta_override`…) restano nel `meta`: non sono provenienza |
| K-6 | FE, il form della riga (preventivo, offerta, contratto, ordine, DDT) | conserva la provenienza che l'endpoint di pricing restituisce già (`views_pricing.py`: origine, versione, riga) e la manda col prezzo; se l'operatore cambia il prezzo non la manda. Sull'`UPDATE` la decadenza la fa comunque il DB |
| K-7 | test sul DB vero | i tre casi di R-6 dal push in su: prezzo trattato → commessa `MANUALE` senza riga di listino; prezzo precompilato e non toccato → la commessa cita R e R è propagata; prezzo cambiato dopo la precompilazione → decaduta |

Gli ordini e i DDT oggi non passano dal pricing gate (`ordini_repository`, `ddt_repository` scrivono la
riga col prezzo del payload): le loro righe nascono `MANUALE` finché K-5/K-6 non li raggiungono, e quelle
copiate da un documento a monte prenderanno la provenienza dalla copia (giro 3, DB).
