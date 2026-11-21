# Brief DB — La provenienza del prezzo viaggia con il prezzo, dal documento alla commessa

## ⏭️ Chi riparte — aggiornato al 2026-11-21 (sera)

**Riparte: il team FE**, con la chiave i18n del §8.19 (8i): sblocca il commit della doc rigenerata, che oggi
`check_i18n_keys.py` ferma. Poi il BE (la policy, 8l) e la chiusura DB. Il giro 5 e il 5-bis sono applicati e verdi
(Tid, 2026-11-21, §8.21). Il giro 5 è scritto e provato in transazione il 2026-11-21 (§8.17): chiude il residuo offerta → ordine
del §8.8 con D-6 «a», e corregge un difetto trovato verificando il caso del §8.16 (l'OVERRIDE su un kit perdeva il
prezzo negoziato). La documentazione rimasta alle regole di prima (due guide, due manuali) è
riallineata il 2026-11-21 (§8.16). Il BE
ha consegnato l'estrazione il 2026-11-21 (§8.15), rivista con `/verifica` e committata lo stesso giorno su `dev/backend-tid`; la policy era già rigenerata dal 2026-11-15 (`940a4e6b6`). Il BE/FE ha consegnato il 2026-11-15 (§8.13):
R-8.3 (policy rigenerata, ripiego), la metà BE di R-7 (6b), K-5 con D-5 nel gate dei **cinque** documenti — ordine e
DDT compresi, con L1/L2 sul prezzo a mano (strada A, decisione di Tid del 2026-11-15) —, K-6 (il solo form che
precompila dal pricing, il preventivo) e K-7 sul DB vero. Da committare (Tid). I giri 1, 2 e 3 sono applicati, verdi e
committati (`33f85e641`, `11273227f`). ⚠️ Il commit `a85b76d58` «Chiusura brief
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
| 4 | ✅ team BE | K-1 … K-4: il push copia la provenienza della riga, i componenti la loro (2026-11-14) | §8.7, §8.9 | 3f |
| 4a | ✅ team BE | La PATCH dei componenti scrive il solo prezzo: la provenienza la fa decadere il trigger (decisione di Tid, strada «a», 2026-11-14) | §8.11 | — |
| 4a-bis | ✅ Tid | D-5: la provenienza dichiarata dal form si verifica sul resolver; se non torna, 409 (2026-11-14) | §8.11 | — |
| 4a-ter | ✅ team DB | **R-8**: il codice `E_PRICING_PROVENIENZA_SUPERATA` (classe `CONFLITTO_STATO`) nel catalogo dei messaggi; scritto il 2026-11-15 | §8.11, §8.12 | — |
| 4b | ✅ team BE/FE | K-5 … K-7: pricing gate e scritture delle righe dei cinque documenti, form, test dal push in su (2026-11-15) | §8.13 | 6a |
| 4b-bis | ✅ Tid | Strada A: ordine e DDT passano dal gate come gli altri tre, prezzo a mano compreso (L1/L2) (2026-11-15) | §8.13 | — |
| 5 | ✅ team DB | Giro 3: le copie a valle (R-4), override con provenienza, contesto dei componenti (D-3); prova in transazione (2026-11-13) | §8.8 | 3f |
| 5b | ✅ Tid | Apply del giro 3 e pgTAP del §8.8: verdi (2026-11-14) | §8.8 | 5 |
| 6 | ✅ team DB | Giro 4: R-8, R-7, il terzo caso di R-6 dal push in su, doc `manual/`; prova in transazione (2026-11-15) | §8.12 | 5b, 4 (✅) |
| 6a | ✅ Tid | Apply del giro 4 e pgTAP del §8.12: verdi (2026-11-15) | §8.12 | 6 |
| 6b | ✅ team BE | La metà BE di R-7: loader del kit dal listino con le colonne `prov_*`, un ramo solo in `_provenienza_componente` (2026-11-15) | §8.13 | 6a |
| 6c | ✅ team DB | La `note` di `E_PRICING_PROVENIENZA_SUPERATA` dice i cinque documenti (strada A); dal CSV, senza changeSet (2026-11-15) | §8.14 | 4b-bis |
| 6d | ✅ Tid | Estrazione della regola del 2 approvata (2026-11-15) | §8.13 «Da decidere» | — |
| 6e | ✅ team BE | L'estrazione: `_resolve_prezzo_riga` + `_gate_prezzo_riga` di ordine e DDT (con `_resolve_emittente_sr_id` e `_data_riferimento`) in `RegolePrezzoTestata`; i due wrapper di offerta e contratto su `resolve_or_check_override_prezzo_con_listino`. La policy era già rigenerata (`940a4e6b6`, 2026-11-15) (2026-11-21) | §8.15 | 6c, 6d |
| 6f | ✅ Tid | Commit dell'estrazione su `dev/backend-tid`, dopo la revisione `/verifica` (2026-11-21) | §8.15 | 6e |
| 6g | ✅ team DB | Guide e manuali riallineati alla provenienza (`gestione-commesse`, `gestione-listini`, `api_run_commesse_push`, `api_commesse_pricing`) (2026-11-21) | §8.16 | 6f |
| 6h | ✅ Tid | Il residuo offerta → ordine (§8.8) si chiude in questo brief, come giro 5 (2026-11-21) | §8.16 | — |
| 8a | ✅ Tid | D-6 «a» (`CONTRATTO_LISTINO`) e il via al giro 5, «verifica anche il caso» (2026-11-21) | §8.16 | 6h |
| 8b | ✅ team DB | Giro 5: `20261120-13 … -17`, un pgTAP nuovo e uno corretto; prova in transazione (2026-11-21) | §8.17 | 8a |
| 8c | ✅ Tid | Apply del giro 5: fatto in 8h, col giro 5-bis | §8.17 | 8b |
| 8d | ✅ Tid | D-7 «b»: un OVERRIDE su un kit nasce coi componenti; prima scoprire chi crea quelle eccezioni (2026-11-21) | §8.17, §8.18 | — |
| 8e | ✅ team DB | Chi crea gli OVERRIDE su un kit senza componenti: la revisione di prima del 2026-10-05, e oggi lo svuotamento dei componenti (2026-11-21) | §8.18 | 8d |
| 8f | ✅ Tid | D-7-bis «b2»: la regola all'emissione, kit a consumo esente; riparare le quattro righe (2026-11-21) | §8.18 | 8e |
| 8g | ✅ team DB | Le quattro righe di dbdev riparate; giro 5-bis `20261120-18 … -20`, codice nuovo, pgTAP; prova in transazione (2026-11-21) | §8.19 | 8f |
| 8g-bis | ✅ team DB | Revisione `/verifica-db` del giro 5 e 5-bis: due pgTAP estesi, chiamanti della `-14` completati (2026-11-21) | §8.20 | 8g |
| 8h | ✅ Tid | Apply di `-13 … -20` e dei CSV, pgTAP del §8.17, del §8.19 e del §8.20 verdi; doc auto-generata rigenerata, non committata (2026-11-21) | §8.21 | 8b, 8g-bis |
| 8i | **team FE** ⏭️ | La chiave i18n `vendite.offerte.azione_reason.kit_senza_componenti`, it ed en: senza, `check_i18n_keys.py` è rosso sulla doc rigenerata | §8.19, §8.21 | 8h |
| 8i-bis | Tid | Commit della doc rigenerata, con la chiave del FE o dopo | §8.21 | 8i |
| 8l | team BE | La policy di `E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI` rigenerata | §8.19 | 8h |
| 7 | team DB | Chiusura: archiviazione | — | 8i-bis, 8l |

**Decisioni aperte di Tid:** nessuna. Decise il 2026-11-21: D-7-bis «b2», kit a consumo esente, le quattro
righe da riparare (§8.18); il residuo del §8.8 si chiude qui come
giro 5; D-6 «a» (§8.16); D-7 «b» (§8.17). Decise il 2026-11-15: l'estrazione della regola del 2 (§8.13 «Da decidere»,
approvata), R-1 e R-2 della revisione (in fondo al §8.13), la strada A (§8.13). Decisa il 2026-11-14: D-5 (§8.11). Decise il 2026-11-13: D-1, D-2, D-3 (§7.3), D-4 (§8.5). F-9 non è
servita: il cantiere degli stati non ha toccato `fn_list_ordini_da_pushare`, e il giro 2 riparte dal suo
corpo vivo. **Lavoro da committare:** il giro 5 e il 5-bis, applicati e verdi (§8.21); la doc auto-generata rigenerata, che
aspetta la chiave del FE (8i); il resto come prima (otto changeSet, due righe di CSV, tre pgTAP nuovi o corretti, le pagine
`manual/` e la guida delle offerte, §8.17 e §8.19), le quattro
pagine riallineate del 2026-11-21 e questo brief; l'estrazione del §8.15 e questo brief sono committati su `dev/backend-tid` (2026-11-21). La riga del CSV del §8.14
è nel commit `f4959f97d`; la consegna del §8.13 nel commit `d16a9a973d` (PR #126).
Il giro 4 (il changeSet `20261114-73`, due righe di CSV, due pgTAP adeguati, la
pagina `manual/`) è nel commit «Stati dal vocabolario: giri 6g e 6g-bis; provenienza del prezzo: giro 4» (2026-11-15). I giri 1-3 e la PATCH dei componenti sono committati (`33f85e641`,
`11273227f`, `c4b0915f3`).

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-10-09. **A chi:** team DB
> (`dev/db-tid`); poi BE (§6), che **attende** la consegna DB.
> **Origine:** revisione delle modifiche di
> [brief-db-riga-listino-propagata-dalla-commessa](../work-done/2026/brief-db-riga-listino-propagata-dalla-commessa.md)
> (§7). **Decisione:** di Tid, 2026-10-09 (variante «B»): una riga di commessa
> cita una riga di listino **solo se il suo prezzo è venuto davvero da lì**, non
> perché il listino, interrogato dopo, darebbe quella riga.
> **Stato:** ⚠️ superato, vedi «Chi riparte». Al 2026-10-09: 🟡 da progettare (DB). Il BE ha già tolto la
> parte che contraddice la decisione (§6.0); il resto attende.

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

* [brief-db-coerenza-listino-della-riga-di-commessa](../work-done/2026/brief-db-coerenza-listino-della-riga-di-commessa.md) (chiuso il 2026-10-17)
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

### 8.8 Giro 3 — le copie a valle (R-4) e il contesto dei componenti (D-3); applicato e verde il 2026-11-14

| changeSet | Che cosa |
| --- | --- |
| `20261113-23` | `vendite.fn_componente_override(valore)`: un override di componente è un prezzo (`MANUALE`) o un oggetto `{prezzo, origine_prezzo, listino_versione_id, listino_riga_id, prezzo_resolver_context}` che dichiara la provenienza |
| `20261113-24` | `vendite.fn_prezzo_resolver_contesto(risultato)`: dal risultato del resolver il contesto da salvare, senza le chiavi che hanno una colonna (prezzo, origine, versione, riga) e senza l'esito |
| `20261113-25 … -29` | le cinque `fn_*_riga_componenti_init`: il resolver scrive versione e riga nelle colonne (D-3) e il contesto dal BB `-24`; l'override passa dal BB `-23` |
| `20261113-30 … -36` | le sette copie: revisione preventivo e offerta, offerta → contratto, preventivo → ordine, offerta → ordine, ordine → DDT, riconsegna. La provenienza viaggia col prezzo |
| `20261113-37` | dal contesto dei componenti già scritti escono `listino_id`, `listino_versione_id`, `listino_riga_id`, `origine`; la scheda della colonna sui componenti dice le chiavi |

**Le scelte del giro.**

* **Le copie.** Righe e componenti copiano origine, versione, riga e contesto insieme al prezzo. Il padre di
  un kit no: nasce a 0 (o col prezzo della sorgente) e la somma dei componenti lo riscrive `COMPONENTI`.
  La riconsegna copia la provenienza solo quando copia il prezzo (riga senza ordine).
* **Gli override con provenienza.** Preventivo → ordine passa ai componenti dell'ordine il prezzo del
  componente a monte **con** la sua provenienza: prima l'override nasceva sempre `MANUALE`. Il BE passa
  ancora numeri, e per lui non cambia niente.
* **Le chiavi del contesto dei componenti si tolgono, non si spostano.** Riga e versione non le aveva mai
  giudicate nessuno: portarle nelle colonne senza i trigger le farebbe entrare non giudicate, coi trigger
  fermerebbe la migrazione su un dato vecchio. Le righe esistenti restano senza riga di listino (§5).
* ⚠️ **Residuo: offerta → ordine, il prezzo dal listino dell'offerta.** La riga d'ordine prende il prezzo
  dall'eccezione (OVERRIDE, AGGIUNTA: la provenienza si copia) o dall'espansione del listino dell'offerta con
  la variazione globale (`DA_LISTINO`, `vendite.fn_offerta_righe_espanse`), che non porta la riga di
  listino: quella riga nasce `MANUALE`, e così i componenti del kit (override numerici). Non mente, tace:
  la decisione B è rispettata. Per chiuderlo l'espansione dovrebbe restituire versione e riga di listino
  (e il risultato della variazione come contesto). Va al giro 4 o a un brief suo: lo decide Tid alla chiusura.
  ⚠️ Deciso da Tid il 2026-11-21: si chiude in questo brief, giro 5 (§8.16).

**Un fatto trovato provando: un rosso del giro 1.** `vendite/test-fn-crea-revisione-preventivo-riga-completa-v1`,
test 1, presidia che ogni colonna di `preventivi_righe` sia nominata nella copia della revisione o
dichiarata esclusa: dal giro 1 era rosso (le quattro colonne nuove), su dbdev fino all'apply del giro 3. Non
era nell'elenco dei pgTAP del §8.6: il censimento del giro 1 aveva cercato i test che nominano le colonne,
non quelli che leggono l'elenco delle colonne della tabella. Il giro 3 lo chiude (8/8). ⚠️ Lo stesso
presidio legge l'elenco fino alla prima parentesi chiusa: un commento con una parentesi dentro l'elenco
delle colonne lo rompe, e i commenti degli `INSERT` qui stanno fuori dall'elenco.

**Prova** (`scripts/prova_changeset.py`, transazione ritirata, catalogo identico prima e dopo):

* sullo scratch, l'estratto con 150 pgTAP (ogni file che nomina le dodici funzioni, i componenti o il loro
  contesto, i test dei giri 1 e 2, i presidi trasversali): il nuovo `vendite/test-provenienza-prezzo-copie-v1`
  8/8; il presidio della revisione da 7/8 a 8/8; nessun rosso nuovo. Rossi già presenti, uguali con e
  senza l'estratto, letti uno per uno dove toccano le funzioni del giro (`test-ddt-righe-evase-dall-ordine-v1`
  43 e `test-ordine-al-modello-v1` 17 sono rossi da owner per costruzione) e gli altri da `test-annullo-documento-con-legami-v1`,
  `test-chiudi-legame-con-prezzi-v1`, `test-doc-verbo-comune-e-porta-v1`, `test-fn-available-actions-ddt-reason-catch-all-v1`,
  e i quattro sulla chiusura della merce e dei resi;
* su dbdev, il test nuovo e il presidio della revisione: verdi; la pulizia del contesto passa sui 20
  componenti di preventivo che tenevano la riga di listino.

**Apply e pgTAP (Tid, 2026-11-14): verdi.** `vendite/test-provenienza-prezzo-copie-v1`,
`vendite/test-fn-crea-revisione-preventivo-riga-completa-v1` (il rosso del giro 1 chiuso), i test delle
sette copie e dei componenti.

**La richiesta BE non cambia.** K-4 (il loader dei componenti) trova ora riga e versione nelle colonne e il
contesto con le chiavi del resolver; K-5 può passare il risultato del resolver così com'è: il DB lo filtra
nelle init, e al pricing gate lo legge `vendite.fn_provenienza_prezzo_esplosa`.

### 8.9 K-1 … K-4 consegnati (team BE, 2026-11-14)

* **Una forma sola per la provenienza**, `backend/apps/vendite/db/_provenienza_prezzo.py`:
  `ProvenienzaPrezzo` (i dieci campi coi nomi della riga di commessa), `COLONNE_PROVENIENZA_PREZZO` (spostata
  qui dal repository, che la riesporta), `COLONNA_DEL_LISTER` (l'unica traduzione:
  `contratto_id` ← `prezzo_contratto_id`) e il frammento SQL del `LATERAL` su
  `vendite.fn_provenienza_prezzo_esplosa`.
* **K-1**: le dieci colonne sono **obbligatorie** in `_PUSHABLE_SHARED_COLS` (le restituiscono tutti e cinque i
  lister, i consumi vuote); `PushableRow.provenienza`. Il presidio sul catalogo
  (`test_commesse_porta_nomi_db`, test 3) le pretende da ogni lister.
* **K-2**: `_build_attivita_input` copia la provenienza così com'è. Ritirati `_resolve_pricing_audit`, la sua
  cache, il `pricing_service` dell'handler e la lettura di `meta.origine_prezzo`.
* **K-3**: ritirate `origine_ammessa` e `ORIGINI_PREZZO_AMMESSE`; `provenienza_da_resolver` (riallinea,
  sblocca) passa l'origine com'è. Visto sul DB vero: riallineare un componente di kit scrive ora
  `LISTINO_BUNDLE` sulla riga di commessa, e il CHECK lo accetta (`test_prezzo_riga_commessa_db`, test 3).
* **K-4**: `list_componenti_riga(con_provenienza=True)` aggiunge le colonne `prov_*` dal BB del DB; la usa solo il
  loader del push, e la forma delle API dei componenti non cambia. Il componente porta la sua provenienza, non
  quella del padre; il kit dal listino del contratto (`fn_contratto_kit_componenti`) dice la sola origine.
  `meta.origine_prezzo` dei componenti non si scrive più. Provata sul DB vero sulle cinque tabelle
  (`test_commesse_porta_nomi_db`, test 5).
* **Per il giro 4**: il push di oggi cita `listino_riga_id` solo se la riga del documento lo porta. Le righe
  scritte dal BE lo porteranno con K-5 (oggi il gate scrive la provenienza nel `meta`); le copie a valle lo
  portano già dal giro 3.
* ⚠️ **La revisione del 2026-11-14 ha trovato un buco sul kit dal listino del contratto**: è una richiesta al
  team DB, al §8.10 (R-7).

### 8.10 Richiesta al team DB — R-7, il kit dal listino del contratto porta la sua provenienza (revisione BE, 2026-11-14)

> **Chi scrive:** sessione di revisione BE (`dev/backend-tid`), 2026-11-14. **A chi:** team DB
> (`dev/db-tid`), nel giro 4. **Chi cambia per primo:** il DB. Il BE legge il risultato della funzione per
> nome (`SELECT k.*` in `ContrattiRepository.list_componenti_kit_dal_listino`), quindi le colonne in più non
> lo rompono; la sua metà arriva dopo il DB.

**Il difetto.** `vendite.fn_contratto_kit_componenti` dà i componenti del kit che il contratto non negozia
(la quota fissa del listino, l'ADESIONE). Il prezzo di ogni componente lo prende da
`fn_resolve_prezzo_listino_v2_esito`, sulla versione di listino del contratto
(`fn_documento_listino_operativo`). Il resolver restituisce la provenienza intera: base, variazione,
`listino_versione_id`, `listino_riga_id`, promo, contratto, categoria, classe. La funzione però ne tiene solo
`prezzo_finale` e `origine` (`RETURNS TABLE(…, prezzo_unitario, esposizione_in_fattura, origine_prezzo)`).

Il push porta quel componente in commessa come una riga a sé (`BoMComponentExpander`, ramo
`componenti_listino_loader`). La riga nasce con `origine_prezzo = 'LISTINO_BUNDLE'` e senza
`listino_versione_id`, `listino_riga_id` né contesto. Ne seguono due cose:

* la riga di listino che **ha dato il prezzo** non viene citata, e quindi non diventa «propagata» (D-4):
  resta rettificabile, mentre il suo prezzo è già in commessa;
* `fn_riallinea_prezzo` confronta la versione con NULL, cioè il difetto che il 2026-10-08 si era chiuso per
  le righe del push (`prezzo_riga_commessa`, intestazione).

È il difetto di R-3, quello trovato al §7.1 F-3 («la funzione che ha in mano il risultato del resolver lo
restituisce intero, invece del solo `prezzo_finale`»), su una funzione che il giro 2 non ha toccato.

**La richiesta.**

| # | Che cosa |
| --- | --- |
| R-7.1 | `fn_contratto_kit_componenti` restituisce anche `listino_versione_id`, `listino_riga_id` e `prezzo_resolver_context` (`to_jsonb` della riga del resolver: è un contesto valido per `fn_provenienza_prezzo_esplosa`, dal suo `COMMENT`). Così la forma è quella delle `*_righe_componenti`, che è ciò che il suo `COMMENT` promette («nella forma che l'espansore del backend legge dalle *_righe_componenti»). Versione e riga si prendono dal risultato del resolver (`r.listino_versione_id`, `r.listino_riga_id`), non da `lo.listino_versione_id`: la provenienza la dice chi ha dato il prezzo. In alternativa, le dieci colonne di `fn_provenienza_prezzo_esplosa` già esplose: la scelta è del team DB, ma il BE preferisce la prima (un `LATERAL` solo, lo stesso delle tabelle) |
| R-7.2 | ⚠️ Cambiare la `RETURNS TABLE` vuole `DROP` + `CREATE`. Due lettori a DB, `fn_contratti_addebiti_maturati` e `fn_contratti_addebiti_maturati_con_provenienza` (la somma `prezzo_unitario × coeff_qta_snapshot` del kit), da riverificare: con `BEGIN ATOMIC` le dipendenze stanno in `pg_depend` |
| R-7.3 | pgTAP sul caso costruito: un contratto con una quota fissa a kit dal listino, componente con prezzo da una riga R della versione del contratto → la funzione restituisce versione e riga R; dopo il push la riga di commessa del componente cita R (`listino_riga_id`) e la versione, e R è «propagata» |
| R-7.4 | `COMMENT` della funzione aggiornato, e la sua pagina `manual/` se c'è |

**La metà BE (`dev/backend-tid`), dopo il DB.** È un elenco, non un lavoro DB:

* `backend/apps/vendite/db/contratti_repository.py` (`list_componenti_kit_dal_listino`): la proiezione legge
  la provenienza con lo stesso frammento delle tabelle (`_provenienza_prezzo.sql_provenienza_esplosa("k")`),
  e restituisce le colonne `prov_*`;
* `backend/apps/vendite/services/commesse_source_handlers.py`
  (`BoMComponentExpander._provenienza_componente`): perde il ramo «la sola origine». Oggi quel metodo sceglie
  la forma guardando se c'è la chiave `prov_origine_prezzo`, ed è fragile: un loader nuovo senza le colonne
  passerebbe in silenzio con la sola origine. Quando i due loader avranno la stessa forma, le colonne `prov_*`
  diventano obbligatorie (`KeyError` se mancano), come i campi obbligatori del lister in `_map_pushable_row`;
* test: quelli dell'espansore sul kit dal listino (`test_commesse_source_handlers`), e un caso sul DB vero
  accanto a `test_commesse_porta_nomi_db`, test 5.

**Nel frattempo** il BE non ripiega: il componente porta l'origine e basta, com'è scritto al §8.9.

⚠️ **Risposta del team DB (2026-11-15): R-7 fatta, con due correzioni ai fatti** (§8.12):

* **R-7.2**: i due lettori sono `plpgsql`, non `BEGIN ATOMIC`. Non stanno in `pg_depend`, il `DROP` non li
  ferma e leggono le colonne per nome: niente da riscrivere. La riverifica è dei pgTAP (§8.12).
* **R-7.3**: per costruzione il componente **non cita una riga di listino**. La funzione passa la versione
  del contratto come preferita, e il componente ha la sua riga in `listini_righe_componenti` (la stessa del
  join): il resolver risponde `LISTINO_BUNDLE` con la versione e con `listino_riga_id` NULL. Il prezzo sta
  in `listini_righe_componenti`, che nessuna riga di documento cita (vale anche per i componenti nati dalle
  init), e che fuori dalla bozza è già immutabile (`trgfn_listini_righe_comp_guard_immutabilita_v5`): non
  c'è una «propagata» da accendere. Il guadagno di R-7 è la versione citata (`fn_riallinea_prezzo` non
  confronta più con NULL) e il contesto. La colonna resta il riflesso del resolver: se la regola del
  resolver cambia, cambia lì. Il pgTAP prova la funzione, non il push (il push è Python): il caso «dopo il
  push» è nei test BE della metà BE.

### 8.11 La PATCH dei componenti, D-5 e la richiesta R-8 (sessione BE, 2026-11-14)

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-14. **A chi:** team DB (`dev/db-tid`) per R-8;
> poi BE/FE per K-5 … K-7. **Chi cambia per primo:** il DB (R-8). Il BE oggi non emette il codice.

**Il rosso dello smoke, chiuso.** `smoke-test-preventivi-componenti`, passo 8: la PATCH di un componente
con un prezzo scritto a mano rispondeva `E_DATABASE` (400), per il CHECK `chk_prevrighe_comp_provenienza_prezzo`.
La init del giro 3 scrive versione e riga di listino nelle colonne del componente; il BE
(`dati_patch_componente`) cambiava la **sola** origine in `MANUALE`. Per il trigger
`trgfn_riga_documento_provenienza_prezzo` era una provenienza nuova, quindi niente decadenza, e il CHECK
rifiutava un `MANUALE` che cita il listino. Valeva per i cinque documenti.

* **Decisione di Tid (strada «a», 2026-11-14):** il BE scrive il solo prezzo, e la provenienza la decide il
  trigger: il prezzo cambiato fa decadere a `MANUALE` (versione, riga e contesto a NULL), il prezzo tolto
  svuota origine, versione e riga. Scartata la strada «b» (il BE scrive la provenienza intera): sarebbe la
  seconda copia di una regola che ha la sua sede nel DB.
* Fatto: `backend/apps/vendite/services/_componenti_service_helpers.py` (`dati_patch_componente`) e i test
  (`test_componenti_patch_operatore`, `test_preventivi_service`). 504 test dei service di vendita verdi; lo
  smoke rilanciato: 23 PASS, 0 FAIL.
* ⚠️ **Da sapere, non è un difetto:** quando il prezzo si toglie, il trigger svuota origine, versione e riga,
  ma non `prezzo_resolver_context`. La coerenza (`fn_provenienza_prezzo_coerente`) non giudica il contesto,
  e `fn_provenienza_prezzo_esplosa` non lo legge senza un'origine da listino: non si vede. Se il team DB
  vuole la simmetria, è una riga nel trigger.
  ⚠️ **Vicolo cieco, verificato dal team DB il 2026-11-15: la simmetria non si fa.** Senza prezzo il contesto
  può essere il **motivo** per cui il prezzo manca: `fn_ddt_riga_componenti_init` scrive apposta
  `esito_codice` nel contesto di un componente senza prezzo (brief-ddt-righe-senza-prezzo, C5), e il trigger
  è `BEFORE INSERT`: svuotarlo cancellerebbe quel motivo appena nato. L'asimmetria è voluta.

**D-5 — la provenienza dichiarata dal form (decisione di Tid, 2026-11-14).** Con K-6 il form manda il prezzo
**con** la provenienza ricevuta dall'endpoint di pricing (origine, versione, riga). Il guard del DB giudica la
coerenza della riga di listino (articolo, UoM, versione, emittente), non il prezzo. Il BE la **verifica**:
rilancia il resolver e, se provenienza dichiarata e prezzo coincidono con quello che il listino dà adesso,
la riga è da listino, con le colonne scritte dal risultato del resolver. Se non coincidono — il listino è
cambiato fra la precompilazione e il salvataggio, o la dichiarazione è falsa — risponde **409** e non salva.
Scartate: «se non torna, `MANUALE`» (un operatore senza il permesso di override riceverebbe un 403 su un
prezzo che non ha toccato) e «ci si fida della dichiarazione» (un prezzo da listino che il listino non dà).

⚠️ **Perché K-5 aspetta R-8, e non esce a metà.** Il form di oggi rimanda il prezzo precompilato anche se
l'operatore non lo tocca. Un K-5 senza il ramo della dichiarazione farebbe `MANUALE` ogni riga precompilata,
passandola dai gate L1/L2: 403 per chi non ha il permesso di override. Il ramo della dichiarazione vuole il
codice del 409, e un codice nuovo nasce nel catalogo del DB.

#### Richiesta R-8 al team DB

✅ **Fatta dal team DB il 2026-11-15** (§8.12): nome e testi come proposti. Il «sollevato dal BE» (R-8.2)
non ha una colonna sua nel catalogo: sta nelle `note` di `codici_errore.csv`, come per
`E_DOCUMENTI_VALORE_NUMERICO_NON_FINITO`.

| # | Che cosa |
| --- | --- |
| R-8.1 | Codice `E_PRICING_PROVENIENZA_SUPERATA`, classe `CONFLITTO_STATO` (409), in `config/messaggi_errore.csv` e nella classificazione. Messaggio senza `%s`, per esempio: «Il prezzo del listino è cambiato dopo che la riga è stata compilata.» Causa: «La riga dichiara un prezzo preso dal listino, ma il listino oggi dà un'altra riga o un altro prezzo per questo articolo, unità di misura e data.» Soluzione: «Ricaricare il prezzo dal listino, oppure scriverlo a mano.» Il nome e il testo li sceglie il team DB |
| R-8.2 | Lo solleva il **BE** (pricing gate di preventivo, offerta e contratto), non una funzione del DB: va dichiarato come tale nella colonna del catalogo che lo dice, se c'è |
| R-8.3 | Alla consegna, il BE rigenera la policy (`genera_error_policies`) col DB allineato a git e scrive il ripiego senza `%s` |

**La metà BE/FE, dopo R-8** (è K-5 … K-7 del §8.7, con D-5 dentro):

* `_pricing_gate_helpers.resolve_or_check_override_prezzo`: la provenienza nelle colonne (`origine_prezzo`,
  `listino_versione_id`, `listino_riga_id`, `prezzo_resolver_context`), non nel `meta`. Tre casi: payload
  senza prezzo → il risultato del resolver; prezzo **con** provenienza dichiarata → verifica D-5 (o 409);
  prezzo senza dichiarazione → `MANUALE`, gate L1/L2/L3. Sparisce il confronto «prezzo uguale a quello del
  resolver, a 4 decimali». Le chiavi d'audit dell'override restano nel `meta`;
* le tre chiamate (preventivi, offerte, contratti) e i repository che scrivono le righe;
* FE (K-6): i cinque form di riga conservano la provenienza dell'endpoint di pricing e la rimandano col prezzo
  finché l'operatore non lo cambia; il 409 si legge come «ricarica il prezzo»;
* K-7, sul DB vero.

### 8.12 Giro 4 — R-8, R-7, il terzo caso di R-6; scritto e provato il 2026-11-15

Numeri concordati con le altre sessioni DB del giorno: questo giro tiene il solo `20261114-73`.

| Che cosa | Dove |
| --- | --- |
| **R-8**: `E_PRICING_PROVENIENZA_SUPERATA`, classe `CONFLITTO_STATO`. Frase senza `%s`: «Il prezzo del listino è cambiato dopo che la riga è stata compilata.» Causa e soluzione come al §8.11. La nota dice che lo solleva il BE, e perché `CONFLITTO_STATO` | `config/codici_errore.csv`, `config/messaggi_errore.csv` (id 1491) |
| **R-7**: `vendite.fn_contratto_kit_componenti` restituisce in coda `listino_versione_id`, `listino_riga_id` e `prezzo_resolver_context`, dal risultato del resolver; il contesto è quello che si salva sulle righe (`fn_prezzo_resolver_contesto(to_jsonb(r))`), cioè la forma delle `*_righe_componenti`. `DROP` + `CREATE` (§5f), sempre `BEGIN ATOMIC`; `COMMENT` e `GRANT` riscritti | `20261114-73` |
| **R-6, terzo caso**: un ordine col prezzo cambiato dopo la precompilazione esce dal lister `MANUALE`, senza listino né contesto, e la riga di listino che citava torna rettificabile. I primi due casi c'erano già, dal giro 2 (test 6-7 e 9-12) | `vendite/test-provenienza-prezzo-push-v1` (14 → 16) |
| Il kit dal listino porta la provenienza: `LISTINO_BUNDLE`, la versione, nessuna riga, il contesto, coerente col prezzo | `vendite/test-listino-kit-e-periodicita-v1` (20 → 21) |
| La pagina `manual/` della funzione | `vendite/manual/fn_contratto_kit_componenti.md` |

**R-5 nel giro 4: niente da fare.** I consumi escono senza provenienza dal giro 2 (§8.7, «Per ramo»):
il prezzo lo dà il listino più tardi, e chi lo scrive scrive la provenienza.

**Prova** (`scripts/prova_changeset.py`, sullo scratch, transazione ritirata, catalogo identico prima e
dopo):

* `test-listino-kit-e-periodicita-v1`: senza il `-73` si ferma al test 21, con il `-73` 21/21;
* `test-provenienza-prezzo-push-v1`: 16/16 con e senza (il terzo caso di R-6 non dipende dal `-73`: prova
  il trigger e il lister del giro 1-2);
* i lettori dei contratti, `test-push-contratto-canoni-v1` (15), `test-push-contratto-dalla-madre-v1` (12),
  `test-vw-dash-contratti-giudizio-v1` (11): verdi con e senza;
* dopo l'estratto c'è una sola firma, con gli stessi attributi e privilegi (`STABLE`, `INVOKER`,
  `zeroerp_app` in `EXECUTE`), sempre `BEGIN ATOMIC`.

**Da lanciare dopo l'apply (Tid):** i due pgTAP adeguati, i tre dei contratti e il presidio del catalogo dei
messaggi.

**Ricaduta BE (alla consegna):** con il DB allineato a git il BE rigenera la policy
(`genera_error_policies`) e scrive il ripiego senza `%s` (R-8.3); poi K-5 … K-7 (§8.11) e la metà BE di R-7
(§8.10). Il caso «dopo il push» di R-7.3 è un test BE: la riga di commessa del componente cita la versione e
non la riga.

**Verifica (revisione DB, 2026-11-15, a `-73` già applicato).** Il corpo coincide con la doc auto-generata
rigenerata; `STABLE`, `INVOKER`, `BEGIN ATOMIC`, e i privilegi sono quelli del `20261031-34` (niente `PUBLIC`,
`zeroerp_app` in `EXECUTE`). I lettori a DB stanno in `fn_contratti_addebiti_maturati_con_provenienza` (due
`LATERAL`, per nome); il BE legge `k.*` e prende le chiavi per nome (`_build_componente_row_from_snapshot`):
le tre colonne in coda non rompono niente prima della metà BE. Niente da correggere.

### 8.13 K-5 … K-7, la metà BE di R-7 e R-8.3 — consegnati (sessione BE, 2026-11-15)

> **Chi scrive:** sessione BE/FE (`dev/backend-tid`), 2026-11-15. **A chi:** team DB per la chiusura; Tid per il
> commit. Nessuna richiesta nuova al DB.

**Decisione di Tid (2026-11-15), la strada A.** K-6 chiedeva la provenienza dichiarata ai cinque form, K-5 la verifica
ai soli tre gate di preventivo, offerta e contratto: ordine e DDT scrivevano il prezzo del payload senza gate, e il
prezzo a mano **senza L1 né L2** (chi non ha l'override su un preventivo poteva aggirarlo con un ordine). Tid: ordine e
DDT passano dallo stesso gate, prezzo a mano compreso. Senza L3: i due documenti non hanno il workflow di approvazione,
e una violazione L2 è un rifiuto.

| # | Che cosa | Dove |
| --- | --- | --- |
| R-8.3 | Policy rigenerata col DB allineato a git (`-81` su dbdev e nel repo); ripiego senza `%s` | `error_policies_generated.py`, `error_messages_fallback.py` |
| 6b | Il kit dal listino legge la provenienza col frammento delle tabelle; le `prov_*` obbligatorie (`KeyError`), il ramo «la sola origine» ritirato | `contratti_repository.list_componenti_kit_dal_listino`, `BoMComponentExpander._provenienza_componente` |
| K-5 | Il gate scrive le quattro colonne (`COLONNE_PROVENIENZA_RIGA`, tutte o nessuna) e non più il `meta`; tre casi: senza prezzo il resolver, con la dichiarazione la verifica D-5 (o 409), senza dichiarazione `MANUALE` + L1/L2(/L3). Esito unico `EsitoPrezzoRiga` con `applica()`: era ricopiato in quattro punti | `_pricing_gate_helpers`; i service e i repository dei cinque documenti |
| K-5 | Il contesto lo calcola il DB: `vendite.fn_prezzo_resolver_contesto(to_jsonb(r))` nella query del resolver, la stessa espressione delle funzioni che scrivono righe e componenti | `pricing_repository._COLONNE_DECORATE` |
| K-5 | Ordine e DDT dal gate (strada A): l'ordine col guscio (il prezzo assente è un errore, BE-3/DEC-2 di brief-ddt-righe-senza-prezzo), il DDT col nucleo (il prezzo assente torna con `esito_codice`) | `ordini_service._gate_prezzo_riga`, `ddt_service._gate_prezzo_riga` |
| K-6 | Il form del preventivo rimanda `provenienza_prezzo` col prezzo dell'endpoint finché l'operatore non lo cambia (anche «Usa prezzo listino» in modifica); sul 409 ricarica il prezzo dal listino | `PreventiviRigaForm.vue` (+ 3 test) |
| K-7 | Sul DB vero, righe scritte dal service col resolver vero: da listino → cita R, R propagata; lo stesso prezzo a mano → `MANUALE`; cambiato dopo → decaduto, R di nuovo rettificabile; dichiarazione verificata o 409; il lister del push restituisce ciò che il gate ha scritto | `vendite/tests/db/test_provenienza_prezzo_dal_gate_db` (5) |
| 6b | La proiezione del kit dal listino sul DB vero restituisce le `prov_*` | `test_commesse_porta_nomi_db`, test 6 |

**Fatti trovati facendolo** (si leggano prima di riprendere):

* ⚠️ **K-6 tocca un form solo.** Solo il form del preventivo precompila il prezzo dall'endpoint di pricing. Su contratto e
  offerta «Modifica prezzo» parte dal prezzo del listino, ma è per definizione una sovrascrittura (OVERRIDE), già
  riservata a chi ha `prezzo_override_manuale`: resta `MANUALE`, ed è giusto. L'ADESIONE non ha prezzo. Ordine e DDT non
  precompilano: senza prezzo lo prende il server, che sa da dove viene. Il BE accetta comunque la dichiarazione da tutti e
  cinque (simmetria del contratto).
* **In modifica un prezzo che non cambia non ripassa dal gate** (BB `prezzo_invariato`, stessa unità di misura,
  tolleranza di trasporto): chi corregge la sola quantità riceverebbe un 403 su un prezzo scritto da un altro, o un 409 su
  un listino cambiato nel frattempo. La provenienza resta quella della riga.
* **Senza prezzo nel payload l'errore del resolver risale** col suo codice. Fino a oggi il gate lo inghiottiva e il
  chiamante riceveva un `None` da spiegare con un messaggio suo; il «best-effort» serve ad accettare un prezzo a mano, e
  senza prezzo non c'è niente da accettare. Effetto: il padre composito del preventivo non passa più dal gate (il suo
  prezzo è la somma dei figli), come negli altri quattro documenti.
* **Il motivo del prezzo assente del DDT sta nella colonna** `prezzo_resolver_context` della riga, come sui componenti
  (`fn_ddt_riga_componenti_init`): stava nel `meta` quando la riga principale la colonna non l'aveva. Nessun lettore del
  `meta` (FE, BE, DB) — verificato.
* **Il reset dell'approvazione rifiutata del preventivo** puliva `approvazione_rifiuto` dal `meta` dei campi, che c'era
  sempre perché il gate ci scriveva l'origine; un prezzo da listino ora non porta audit, e la motivazione sarebbe rimasta.
  Ora pulisce il `meta` della riga quando i campi non lo portano.
* **R-7.3 (correzione del team DB)**: il componente del kit dal listino cita la versione e non la riga (il prezzo sta in
  `listini_righe_componenti`); i test BE provano questo, non «cita R».
* Due test che non parlano di prezzo mandavano un prezzo del listino senza dichiararlo, e senza operatore
  (`test_righe_erogazione_obbligatoria_db`, i test IVA del DDT): con K-5 è un prezzo a mano. Il gate L1 vi è neutralizzato,
  dichiarandolo.

**Da decidere (regola del 2, proposta — non estratta):** ⚠️ approvata da Tid il 2026-11-15 ed estratta il 2026-11-21 (§8.15). `_resolve_prezzo_riga` di ordine e DDT erano già due copie (stessi
controlli di testata, stessa chiamata al `PricingService`), e ora hanno accanto due `_gate_prezzo_riga` gemelli. Le
differenze sono di dominio (guscio contro nucleo, codice d'errore), quindi sono parametri: si estraggono in un BB del
contesto di testata. Lo stesso vale per i due wrapper `resolve_or_check_override_prezzo_riga_offerta` / `_contratto` (il
salto senza listino e la data normalizzata), copie già prima di oggi. Serve l'ok di Tid.

**Verifiche (2026-11-15):** suite intera del backend col DB vero, 7324 test: verdi tranne 4, nessuno di questo
lavoro — dalle 11:35 un'altra sessione DB ha applicato su dbdev `20261114-82` … `20261115-26`, non ancora in git
(due codici d'indirizzo senza policy, la capability del documento interno di magazzino, la madre degli indirizzi);
⛔ la policy NON si rigenera finché quei changeSet non sono nel repo. `apps.vendite` tutta verde, coi test sul DB vero
(5 nuovi in `test_provenienza_prezzo_dal_gate_db`, 1 in `test_commesse_porta_nomi_db`); FE 1185 verdi; mypy pulito
sui sette moduli toccati.

**Revisione BE/FE (`/verifica`, sessione nuova, 2026-11-15)** — corretto, col suo test:

* ⛔ **Il form dichiarava «dal listino» ogni prezzo uguale a quello del listino**, anche riscritto a mano: la deduzione
  dal confronto che il gate ha ritirato (§2, §8.1) rientrava dal FE. Ora la dichiarazione vale solo se nel campo il
  prezzo l'ha **scritto** il listino (precompilazione, «Usa prezzo listino») e nessuno l'ha cambiato da allora
  (`prezzoDalListino` in `PreventiviRigaForm.vue`; spec 3, 4b, 4c, rossi col codice di prima).
* **Contratto: una PATCH col solo prezzo invariato era un 404** «Riga contratto non trovata»: `prezzo_invariato`
  toglie il prezzo, l'UPDATE resta senza campi e `execute_dynamic_update` torna `False`. Gli altri quattro documenti
  ignorano l'esito o saltano l'UPDATE vuoto (`contratti_service.update_riga`;
  `test_update_riga_solo_prezzo_invariato_non_e_un_404`, rosso col codice di prima).
* Il motivo dello smistamento del preventivo letto a mano (`_reason_key` senza valori) → `caps.motivoFlag` +
  `testoMotivi`, la sede che FE-G1 dichiara unica (`PreventiviDrawer.vue`). Oggi nessun valore cambia la frase.
* `S608` di ruff sul frammento del kit dal listino (`contratti_repository`), annotato come gli altri lettori del BB.

**Da decidere, dalla revisione (Tid):**

* ✅ **R-1 — il prezzo a mano senza L1 quando il listino non risponde.** Con un prezzo nel payload, se mancava il
  contesto del resolver o il resolver sollevava (articolo fuori listino, categoria non mappata), il gate accettava il
  prezzo **senza** L1: con la strada A, la scappatoia restava aperta su ordine e DDT per gli articoli senza prezzo di
  listino. **Decisa da Tid il 2026-11-15, (a): L1 si applica anche lì** (L2/L3 no: non c'è un prezzo da cui misurare lo
  scostamento); la riga è `MANUALE`, con l'audit dell'override. Chi non ha l'override non prezza un articolo fuori
  listino. Effetto collaterale corretto nello stesso giro: il padre composito del **contratto** passava dal gate col
  segnaposto «0» (il resolver ne rifiutava l'articolo, e il gate lo inghiottiva); ora non ci passa, come negli altri
  quattro documenti (`contratti_service.create_riga`/`update_riga`). ⚠️ Resta come prima, per decisione del
  2026-05-20, il contratto e l'offerta **senza listino**: lì il prezzo è negoziato e non passa da nessun gate.
  Test: `test_pricing_gate_helpers` 8 e 8b (rossi senza L1), `test_resolve_or_check_override_missing_context_skips`;
  tre test di servizio e `test_righe_canone_periodicita_db` neutralizzano L1, che non è il loro soggetto.
* ✅ **R-2 — offerta e contratto senza listino ignoravano la dichiarazione** (la riga diventava `MANUALE` in silenzio),
  dove il gate, senza contesto, risponde 409. Corretto il 2026-11-15 (ok Tid): il 409 esce dal gate in
  `rifiuta_provenienza_dichiarata`, e i due wrapper lo usano senza ricopiarlo (`test_pricing_gate_helpers`
  `SenzaListinoTests`, rosso col codice di prima). L'estrazione dei due wrapper resta la proposta qui sopra.
* ✅ **Per la chiusura DB (non bloccante):** la `note` di `E_PRICING_PROVENIENZA_SUPERATA` a catalogo dice «pricing gate di
  preventivo, offerta e contratto»; con la strada A sono cinque documenti. Si corregge dal CSV, poi si rigenera. Fatta, §8.14.

Verifiche della revisione: `apps.vendite` col DB vero (`ZEROERP_TEST_DB_E2E=1`) 2719 verdi; spec FE di `vendite` e
`useEntityCapabilities` 228 verdi; `npm run guards`, `check_i18n_keys`, `check_classi_morte`, ruff sui file toccati:
puliti.

### 8.14 La `note` del codice e chi chiude (sessione DB, 2026-11-15)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-15. **A chi:** team BE (6e); Tid per l'apply e il commit.

* **La `note` di `E_PRICING_PROVENIENZA_SUPERATA`** in `80_data/sql/config/codici_errore.csv` dice ora «pricing gate dei
  cinque documenti, preventivo, offerta, contratto, ordine e DDT - strada A, decisione di Tid del 2026-11-15». La classe
  (`CONFLITTO_STATO`) e il messaggio non cambiano. Niente changeSet nuovo: il CSV lo carica
  `20260614-08-upsert-messaggi-errore-chiusura-flusso-prematuro` (`loadUpdateData`, `runOnChange: true`), che al
  prossimo `update` riscrive la riga. Il nome citato, `resolve_or_check_override_prezzo`, esiste ancora in
  `_pricing_gate_helpers.py`: se l'estrazione 6e lo rinomina, il BE lo scrive qui e il team DB riallinea la `note`.
* **Verificato sulla doc auto-generata** ciò che la consegna del §8.13 usa: le quattro colonne di
  `COLONNE_PROVENIENZA_RIGA` (`origine_prezzo`, `listino_versione_id`, `listino_riga_id`, `prezzo_resolver_context`) su
  `preventivi_righe`, `contratti_righe`, `ordini_righe`, `ddt_righe`, e `vendite.fn_prezzo_resolver_contesto`. Torna.
* **La policy, per il BE (6e):** il blocco del §8.13 («la policy NON si rigenera finché quei changeSet non sono nel
  repo») è caduto, perché i changeSet dell'altra sessione DB sono in git (`b8180da711`, `42a8fa7847`). Nella policy
  rigenerata mancano ancora cinque codici di brief-db-copia-indirizzo-soggetto: `E_INDIRIZZO_SOGGETTO_TIPO_GIA_PRESENTE`,
  `E_INDIRIZZO_RUOLO_TIPO_GIA_PRESENTE`, `E_INDIRIZZO_SOGGETTO_NON_TROVATO`, `E_INDIRIZZO_RUOLO_NON_TROVATO`,
  `E_INDIRIZZO_COPIA_NESSUN_TIPO`. È probabile che siano loro i 4 rossi della suite del §8.13. Una rigenerazione sola, dopo
  l'apply della `note`, li porta tutti.
* **La chiusura (7)** aspetta l'estrazione 6e, approvata da Tid il 2026-11-15: un brief con un debito aperto non si
  archivia. ⚠️ Fatta il 2026-11-21, §8.15.

### 8.15 L'estrazione della regola del 2 (6e) — consegnata (sessione BE, 2026-11-21)

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-21. **A chi:** Tid per il commit; team DB per la chiusura (7).
> Nessuna richiesta nuova al DB.

**Prima di cominciare, riverificato** che dopo la consegna del §8.13 (`d16a9a973`) nessuno avesse toccato il gate: sui
file del gate e del pricing c'è un solo commit (`44ba001ec`, `scadenza_mese` nei contratti, estraneo); il brief l'ha
toccato solo il §8.14; `origin` non aveva niente di nuovo su `dev/backend-tid` né su `dev/db-tid`. La policy chiesta in
6e era già rigenerata dal 2026-11-15 (`940a4e6b6`: `E_PRICING_PROVENIENZA_SUPERATA` e i cinque `E_INDIRIZZO_*`, coi
ripieghi); la `note` del §8.14 non cambia la classe, e non c'è niente da rigenerare.

| Che cosa | Dove |
| --- | --- |
| **`RegolePrezzoTestata`**: dataclass immutabile coi parametri di dominio (`documento`, `error_code`, `function_name`, `prezzo_assente_ammesso`); metodi `emittente_sr_id`, `data_riferimento`, `resolve_prezzo_riga`, `gate_prezzo_riga`. Ordine e DDT la costruiscono una volta (`_REGOLE_PREZZO`) e ne chiamano i metodi. ⚠️ Fino alla revisione del 2026-11-21 i quattro nomi privati restavano come alias dei metodi: tolti, vedi «Le scelte» | `apps/vendite/services/_prezzo_riga_testata.py`; `ordini_service`, `ddt_service` |
| **`resolve_or_check_override_prezzo_con_listino`**: il salto senza listino col 409 sulla dichiarazione e la data dal `campo_data`. I due wrapper di offerta e contratto restano come nomi del dominio e lo chiamano col loro resolver | stesso modulo; `offerte_service`, `contratti_service` |
| Test del BB: il flag guscio/nucleo e l'obbligo del prezzo (provati per mutazione: rossi con il ramo invertito), le frasi col nome del documento, l'alias della data | `tests/services/test_prezzo_riga_testata` (6: il sesto, dalla revisione, prova che una patch sulla classe arriva al gate) |
| `data_di_riferimento`: la data della testata in una sede, per il risolutore IVA e per il prezzo di riga | `_iva_contesto_documento.py` |
| Catalogo BB (riga nuova accanto al gate, caller e riga del contratto aggiornati, riga del contesto IVA) e indice rigenerato | `catalogo-building-block-backend.md`, `indice-building-block-backend.md` |

**Le scelte.**

* **Le copie erano quattro, non due.** Accanto a `_resolve_prezzo_riga` e `_gate_prezzo_riga`, ordine e DDT avevano
  gemelle anche `_resolve_emittente_sr_id` e `_data_riferimento` (usate pure dall'init dei componenti): stessa regola,
  diverse solo nel codice e nel soggetto della frase. Sono entrate nello stesso BB, dichiarate a Tid prima di farlo.
* ⛔ **Un flag solo per la differenza fra i due domini** (`prezzo_assente_ammesso`): guscio + prezzo obbligatorio
  sull'ordine, nucleo + prezzo assente ammesso sul DDT. Due flag potrebbero divergere, e darebbero un ordine che accetta
  una riga senza prezzo o un DDT che ferma una riga che brief-ddt-righe-senza-prezzo ammette.
* **Il resolver di offerta e contratto non si fissa in una factory**: il wrapper lo passa a ogni chiamata, leggendolo dal
  suo modulo. È il punto che i test patchano (`contratti_service.contratti_suggerisci_prezzo_riga`); fissato all'import,
  i patch non lo intercetterebbero e i test chiamerebbero il resolver vero.
* **Cambiato, voluto:** le frasi dicono «… impossibile risolvere prezzi e componenti» per tutti e due i domini
  (l'ordine diceva «i componenti», il DDT spiegava il trigger normalize, ora nel commento del service); l'unità di
  misura mancante accende il campo anche nel resolver dell'ordine, come già nel DDT.
* **Nome del gate invariato**: `resolve_or_check_override_prezzo` resta, quindi la `note` del §8.14 resta giusta.
* Un test (`test_offerte_service` 57) patchava il gate col nome importato in `offerte_service`: ora lo chiama il BB, e
  il patch è sul modulo del BB.
* ⛔ **Niente alias di modulo per i metodi** (revisione `/verifica` del 2026-11-21, ok Tid). La prima stesura teneva
  `_gate_prezzo_riga = _REGOLE_PREZZO.gate_prezzo_riga` e gli altri tre nomi. Ma i metodi si chiamano fra loro (il gate
  passa da `resolve_prezzo_riga`, che passa da `emittente_sr_id` e `data_riferimento`): una patch su
  `ordini_service._resolve_emittente_sr_id` non sarebbe arrivata al gate, e col repository mockato `int(MagicMock)` dà
  `1`, un test verde su un emittente inventato. Ora il service chiama `_REGOLE_PREZZO.<metodo>`, e i test di
  `test_ordini_service` patchano la classe (`RegolePrezzoTestata.<metodo>`; l'istanza è `frozen`). Il presidio è
  `test_la_patch_sulla_classe_arriva_al_gate`, rosso se un metodo ricopia la regola invece di chiamare il gemello
  (provato per mutazione).

**La terza sede della data (ok Tid, 2026-11-21).** `_iva_contesto_documento.contesto_da_testata` leggeva la stessa data
della testata (`data` obbligatoria, ISO o `date`) con una frase sua sull'IVA. La regola sta ora nel BB
`data_di_riferimento` dello stesso modulo, puro, con la frase passata dal chiamante; lo chiamano `contesto_da_testata` e
`RegolePrezzoTestata.data_riferimento`. La sede è il modulo IVA, che è già il BB del contesto di testata ed è leggero: il
verso dell'import (prezzo → IVA) non chiude cicli. Le frasi non cambiano.

**Verifiche (2026-11-21):** `apps.vendite` col DB vero (`ZEROERP_TEST_DB_E2E=1`): 2731 verdi, i 5 nuovi compresi, rilanciata dopo la terza sede
della data; dopo la revisione senza alias, 2732 verdi (il sesto test del BB compreso); mypy a
cricchetto (`check_mypy_baseline.py`): nessun rilievo nuovo; ruff sui file toccati: pulito. `apps.core`: 1861, un rosso
solo e non di questo lavoro, il presidio autospec su `apps/ui/tests/db/test_cancellazione_colonna_db.py:111`, file non
tracciato di un'altra sessione (brief-db-revisione-ui) che lavora sullo stesso tree.

### 8.16 Giro 5 — offerta → ordine: la provenienza dal listino dell'offerta (team DB, 2026-11-21)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-21. **A chi:** Tid, per D-6 e il via allo sviluppo.
> **Origine:** il residuo del §8.8; Tid il 2026-11-21: «invece di aprire un nuovo brief prosegui l'attività
> aggiornando questo con quello che manca».

**Prima, la documentazione (6g, fatta).** Quattro pagine descrivevano ancora il push di prima di K-1/K-2: le
origini in cinque, `_resolve_pricing_audit`, l'audit «diagnostico, best-effort», `LISTINO_BUNDLE` ridotto a
`NULL`, la provenienza nel `meta`, il prezzo uguale al suggerito che «passa sempre». Riallineate:
`guide/gestione-commesse.md` (§«La provenienza del prezzo», già «Snapshot pricing v5 — 8 colonne audit», e
il flusso del push), `guide/gestione-listini.md` (§6: i tre casi del gate e D-5),
`backend/vendite/manual/api_run_commesse_push.md` e `api_commesse_pricing.md`.

**Il residuo, letto sul corpo vivo** (`20261112-09` per `vendite.fn_offerta_righe_espanse`, `20261113-34` per
`vendite.fn_genera_ordine_da_offerta`). Le righe d'ordine che oggi nascono `MANUALE` senza che nessuno abbia
scritto il prezzo sono tre casi, non uno:

| Caso | Da dove viene il prezzo | Oggi sulla riga d'ordine | Che cosa manca |
| --- | --- | --- | --- |
| **R1** riga semplice dal listino (`DA_LISTINO`, anche con l'`ADESIONE`) | `listini_righe.prezzo` della versione operativa dell'offerta, ± la variazione globale (`fn_espandi_listino_versione`) | `MANUALE` | l'espansione non restituisce la riga di listino; nessuna origine dice «listino del documento con la sua variazione» (D-6) |
| **R2** kit dal listino (`DA_LISTINO`, `is_composito`) | i prezzi di `listini_righe_componenti`, senza variazione | il padre `COMPONENTI` (giusto), i componenti `MANUALE` (override numerici) | il componente è `LISTINO_BUNDLE` con la versione e senza riga, come nel kit dal listino del contratto (R-7.3) |
| **R3** kit in `AGGIUNTA` | `offerte_commerciali_eccezioni_componenti.prezzo_unitario` | i componenti `MANUALE` | i componenti dell'eccezione hanno la provenienza in colonna dal giro 1, ma il `jsonb` dell'espansione porta il solo prezzo |

Le righe da eccezione (`OVERRIDE`, `AGGIUNTA` semplice) copiano già la provenienza dal giro 3: non cambiano.

**D-6 — l'origine di R1 (da decidere, Tid).** Il prezzo è il listino fissato dal documento a monte, con la
variazione globale che l'offerta ha negoziato. Un fatto che pesa: per le righe dell'offerta stessa il resolver
risponde già con il fast path `CONTRATTO_LISTINO` (`listino_versione_id_preferito`, `offerte_service`, «come
contratti»; senza contratto e con variazione `NESSUNA`). Cioè nel modello di oggi `CONTRATTO_LISTINO` vuol dire
«il listino fissato dal documento», non «il listino di un contratto».

* **(a) — proposta: `CONTRATTO_LISTINO`, con versione, riga e la variazione dell'offerta nel contesto.** È
  l'origine che la stessa offerta dà alle sue righe quando le prezza col resolver: un'origine sola per lo stesso
  fatto, e il dominio (`vendite.fn_origine_prezzo_ammessa`) non cambia. Il nome resta impreciso («contratto»
  per un'offerta), ma lo è già nel fast path: correggerlo è rinominare un'origine in tutta la catena, cioè un
  cambio di modello da fare a parte se Tid lo vuole.
* (b) un'origine nuova (`OFFERTA_LISTINO`, otto valori nel dominio). Il nome è più preciso, ma le righe
  dell'offerta prezzate dal resolver resterebbero `CONTRATTO_LISTINO`: due origini per lo stesso fatto, a meno
  di cambiare anche il fast path del resolver.
* Scartata: `CATEGORIA`. Il prezzo non viene dalla matrice delle categorie, e direbbe il falso.

**Il progetto (dopo D-6; i numeri al via, da `scripts/prossimo_changeset.py`).**

| Passo | Che cosa |
| --- | --- |
| 5-1 | `vendite.fn_espandi_listino_versione`: in coda `listino_riga_id` (`lr.id` per la riga semplice, `NULL` per il kit). Cambia il `RETURNS`, quindi `DROP` + `CREATE`, con il censimento di `pg_depend` prima. I due chiamanti (`fn_offerta_righe_espanse` e `fn_documento_righe_preview`, che fa da corpo a `fn_offerta_righe_preview` e `fn_contratto_righe_preview`) sono `plpgsql` e leggono le colonne per nome (`base.<colonna>`): niente da riscrivere, ma si riprovano i loro pgTAP |
| 5-2 | `vendite.fn_offerta_righe_espanse` restituisce la provenienza della riga: `origine_prezzo`, `listino_versione_id`, `listino_riga_id`, `prezzo_resolver_context`. R1: l'origine di D-6, versione e riga dal listino, contesto con base e variazione dal BB `vendite.fn_prezzo_resolver_contesto`. `OVERRIDE` e `AGGIUNTA`: la provenienza dell'eccezione (la lettura che oggi sta in `fn_genera_ordine_da_offerta` si sposta qui: una sede sola). Il kit: nessuna, il padre lo scrive `COMPONENTI` la somma. Nel `jsonb` dei componenti, per R2 e R3, la provenienza di ciascuno nella forma che `vendite.fn_componente_override` già legge (`origine_prezzo`, `listino_versione_id`, `listino_riga_id`, `prezzo_resolver_context`) |
| 5-3 | `vendite.fn_genera_ordine_da_offerta`: copia la provenienza della riga espansa così com'è, e passa a `fn_ordine_riga_componenti_init` override oggetto, non numeri. Restano esclusi gli override a 0, che la init rifiuta |
| 5-4 | pgTAP: `vendite/test-offerta-righe-espanse` (le colonne nuove, i tre casi) e `vendite/test-provenienza-prezzo-copie-v1` (offerta → ordine: R1 cita la riga e la versione, R propagata per D-4; R2 `LISTINO_BUNDLE` con la versione; R3 la provenienza dell'eccezione); si riprovano quelli dei chiamanti di 5-1 e i presidi della revisione |

**Da sapere prima del via.**

* ⛔ **Effetto voluto di D-4:** dopo il giro 5 la riga di listino di R1 citata da un ordine è «propagata»: in una
  versione attiva non si rettifica e non si cancella. Oggi non lo è, perché l'ordine non la cita.
* Le righe d'ordine già scritte restano `MANUALE` (§5): niente recupero.
* ⚠️ **Verificato il 2026-11-21: il difetto c'è**, ed è corretto nel giro (§8.17, Tid: «verifica anche il caso»).
  Da verificare scrivendo 5-2: un `OVERRIDE` su un kit prende oggi i componenti dal listino (`base.componenti`)
  e il prezzo del padre dall'eccezione, ma il padre nasce a 0 e lo riscrive la somma. Se l'offerta ammette
  l'`OVERRIDE` su un composito, il prezzo negoziato del padre si perde già oggi: è un fatto da accertare e, se
  c'è, da portare a Tid, non da correggere nel giro.
* ⚠️ Il progetto diceva cinque passi su tre funzioni: sono diventati cinque changeSet su cinque, §8.17
  (il BB dei componenti dell'eccezione e `script.fn_check_righe_offerta_in_ordine`).
* **Ricaduta BE: nessuna richiesta.** Né `fn_offerta_righe_espanse` né `fn_espandi_listino_versione` hanno
  chiamanti nel BE o nel FE (verificato con `grep` il 2026-11-21), e con (a) il dominio non cambia. Un solo
  commento fermo alle cinque origini, `backend/apps/vendite/db/commesse_repository.py:353`
  (`origine_prezzo: … # PROMO|CONTRATTO_OVERRIDE|CONTRATTO_LISTINO|CATEGORIA|MANUALE`): il team BE lo allinea
  al prossimo passaggio sul file. Con (b) si aggiunge la verifica dei badge dell'origine nel FE.

### 8.17 Giro 5 — scritto e provato il 2026-11-21 (team DB)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-21. **A chi:** Tid, per l'apply, i pgTAP e D-7.
> D-6 «a» e il via allo sviluppo: Tid, 2026-11-21 («D-6 opzione a, procedi con lo sviluppo del giro 5, verifica
> anche il caso»). Numerazione da `scripts/prossimo_changeset.py`.

**Il caso, verificato: il difetto c'è.** Un `OVERRIDE` su un kit ha i suoi componenti negoziati in
`offerte_commerciali_eccezioni_componenti` (li crea `fn_offerta_eccezione_componenti_init`, e il trigger del padre
ne fa la somma), ma `fn_offerta_righe_espanse` passava all'ordine quelli **del listino** (`base.componenti`). L'ordine
nasceva col prezzo del listino, non con quello negoziato. Su dbdev, il 2026-11-21: offerta 57, `ART-COMP-001` forzato a
25,90 (componenti dell'eccezione per 25,90), componenti espansi per 6,00. Il gemello `fn_push_offerta_a_contratto`
copia invece i componenti dell'eccezione: l'ordine era l'unico fuori regola. Corretto nel giro, perché la correzione
sta nella stessa espressione che il giro riscrive (i componenti del kit) e il modello è già deciso: il prezzo forzato
prevale, e un kit vale la somma dei suoi componenti.

| changeSet | Che cosa |
| --- | --- |
| `20261120-13` | BB `vendite.fn_offerta_eccezione_componenti_espansi(eccezione)`: i componenti attivi di un'eccezione composita in `jsonb`, con la provenienza di ciascuno nella forma di `fn_componente_override`. Era scritto dentro la parte 2b dell'espansione col solo prezzo; ora lo chiamano due rami (AGGIUNTA composita, OVERRIDE su un kit): regola del 2. `BEGIN ATOMIC` |
| `20261120-14` | `vendite.fn_espandi_listino_versione`: `listino_riga_id` in coda (`lr.id` per la riga semplice, `NULL` per il kit). `DROP` + `CREATE`; COMMENT riscritto al presente |
| `20261120-15` | `script.fn_check_righe_offerta_in_ordine`: le righe espanse **per nome**, la posizione da `r.ordinality`. Con l'elenco di alias posizionale `riga_nr` sarebbe finito, senza errore, sulla prima colonna nuova: era la seconda volta (`20261106-50`). Viene prima del `-16` e regge le due forme |
| `20261120-16` | `vendite.fn_offerta_righe_espanse`: la provenienza in coda (`origine_prezzo`, `listino_versione_id`, `listino_riga_id`, `prezzo_resolver_context`, coi tipi della riga d'ordine). R1 `CONTRATTO_LISTINO` (D-6) con versione, riga e nel contesto prezzo base e variazione globale; OVERRIDE e AGGIUNTA semplice quella dell'eccezione (la lettura che stava nell'ordine si sposta qui); il kit nessuna. Componenti: dell'eccezione per AGGIUNTA e OVERRIDE (il caso), del listino `LISTINO_BUNDLE` con la versione. `DROP` + `CREATE` |
| `20261120-17` | `vendite.fn_genera_ordine_da_offerta`: copia la provenienza della riga espansa e passa ai componenti l'override-oggetto (l'elemento del `jsonb`); le righe espanse per nome |

**Le scelte.**

* **La riga di listino si cita solo se l'unità della riga è la sua.** Il guard F-8 confronta la riga citata con
  `uom_operativa_id`: un'ADESIONE con un'altra unità fermerebbe «Genera ordine» su un dettaglio di provenienza. In quel
  caso restano origine e versione, che la coerenza ammette. Su dbdev nessuna ADESIONE così (fatto datato).
* **Il contesto della riga dal listino** ha le chiavi che `fn_provenienza_prezzo_esplosa` legge
  (`prezzo_base_snapshot`, `tipo_variazione_applicata`, `valore_variazione_applicata`), `NESSUNA` e 0 senza variazione.
  Nessuna chiave di listino nel contesto (D-3; il presidio 8 di `test-provenienza-prezzo-copie-v1` lo pretende).
* **Il componente del kit dal listino** è `LISTINO_BUNDLE` con la versione, senza riga e senza variazione, come quello
  del kit dal listino del contratto (R-7.3).
* **Nessun alias posizionale sulle righe espanse**, nei due lettori: la prossima colonna in coda non sposta niente.

**D-7 — da decidere (Tid): l'OVERRIDE su un kit senza componenti suoi.** Se l'eccezione non ha componenti (nessuno ha
chiamato la init), il kit resta sui componenti del listino, com'era: il prezzo forzato non ha componenti da cui
ricomporsi, e l'ordine nasce con la somma del listino. Su dbdev, il 2026-11-21, quattro eccezioni così (42, 43, 45,
46), a quantità fissa, canone. Le strade: (a) l'ordine rifiuta l'offerta con un motivo in
`fn_check_righe_offerta_in_ordine` («kit col prezzo forzato senza componenti»), come già fa per il kit senza distinta;
(b) un guard sull'eccezione: un OVERRIDE su un kit nasce coi componenti, o non nasce; (c) com'è oggi. Il team DB
propone (b) con (a) come rete: il difetto sta dove l'eccezione nasce, non dove si copia. Prima serve sapere chi crea
quelle eccezioni senza init (BE, revisione dell'offerta, seed): è il prossimo passo, se Tid sceglie (a) o (b).

**Prova** (`scripts/prova_changeset.py` sullo scratch, transazione ritirata, catalogo identico prima e dopo):

* l'estratto dei cinque changeSet passa per intero; attributi (`provolatile`, `prosecdef`, `proparallel`, `procost`,
  `prorows`, `proconfig`) e privilegi delle cinque funzioni identici prima e dopo, una firma per nome;
* ⚠️ esteso dalla revisione (§8.20: 10 test, K2 a 70 con un componente `LISTINO_BUNDLE`, il kit aggiunto K3). Il pgTAP nuovo `vendite/test-provenienza-prezzo-offerta-ordine-v1` (9): senza l'estratto muore al test 1, con
  l'estratto 9/9. Tutto costruito: A dal listino a 100 con -10 % (l'ordine cita la riga, `CONTRATTO_LISTINO`, 90),
  B forzato a 80 (la provenienza dell'eccezione), il kit K dal listino (`COMPONENTI` a 50, componenti
  `LISTINO_BUNDLE` con la versione), il kit K2 forzato coi componenti a 20 e 25 (l'ordine vale 65, non 50: il caso);
* `vendite/test-offerta-righe-espanse`: i test 6-8 (il nucleo) erano rossi senza l'estratto, perché la fixture
  prendeva «il primo listino attivo» e «il primo articolo» del database, che sullo scratch non ci sono. La fixture ora
  si costruisce il suo mondo, e c'è il test 10 sulla colonna nuova: 10/10;
* i 21 pgTAP che nominano le funzioni toccate o i loro lettori (anteprime di contratto e offerta, ADESIONE,
  esclusioni, provenienza documentale, commenti al presente, il rubinetto, le copie): uguali con e senza l'estratto.
  Un rosso già presente, `vendite/test-fn-contratto-righe-preview-nuovi-campi-v1` test 2, è la stessa fixture legata
  ai dati («4 articoli disponibili»), e salta 3-5: non tocca l'espansione dell'offerta, e l'anteprima dei contratti è
  provata verde da `test-contratto-righe-lista-v1` e `-uom-riga-v1`. Debito di quel file, non di questo giro;
* guardrail (forme, COMMENT al presente, letterali, timestamp, runOnChange, preCondition) e `pre-commit` sui file del
  giro: puliti.

**Per Tid, dopo l'apply:** `vendite/test-provenienza-prezzo-offerta-ordine-v1`, `vendite/test-offerta-righe-espanse`,
`vendite/test-provenienza-prezzo-copie-v1`, `vendite/test-sorgente-righe-vendita-v1`, `script/test-rubinetto-primo-motivo-v1`,
`vendite/offerte_commerciali/test-righe-ammesse-ai-passi-e-annullo-v1`; poi la rigenerazione della doc auto-generata
(la pagina del BB nuovo non c'è ancora, e la pagina `manual/` dell'espansione la cita).

**Doc scritta a mano, riallineata:** `dbzero/vendite/manual/fn_offerta_righe_espanse.md` (firma e la sezione «La
provenienza del prezzo»), `dbzero/vendite/manual/fn_espandi_listino_versione.md` (la colonna nuova),
`guide/gestione-offerte-commerciali.md` (§«Cosa viene copiato»).

**Ricaduta BE: nessuna.** Le funzioni toccate non hanno chiamanti nel BE né nel FE; il commento fermo alle cinque
origini in `backend/apps/vendite/db/commesse_repository.py:353` resta la sola nota del §8.16.

### 8.18 D-7 «b»: chi crea un OVERRIDE su un kit senza componenti (team DB, 2026-11-21)

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-21. **A chi:** Tid, per D-7-bis.
> D-7 «b» di Tid, 2026-11-21: «D-7 opzione b, prima scopri chi crea quelle eccezioni».

**Chi scrive `offerte_commerciali_eccezioni`** (censito sul vivo, `pg_get_functiondef`, e nel backend): due strade sole.

* **Il backend** (`offerte_service.crea_eccezione` → `OfferteRepository.create_eccezione`, poi
  `init_componenti_eccezione`): su un composito OVERRIDE o AGGIUNTA chiama sempre la init, nella stessa transazione,
  in una **seconda istruzione**.
* **La revisione dell'offerta** (`vendite.fn_crea_revisione_offerta`): copia le eccezioni e poi, una per una, i loro
  componenti, anche qui in un'istruzione successiva. Nessun seed e nessun'altra funzione del DB scrive la tabella.

**Le quattro eccezioni di dbdev (42, 43, 45, 46): la revisione di prima del 2026-10-05.** Sono nate nella stessa
transazione delle loro offerte, 83 e 84, coi prezzi dell'offerta 63 (5,99 e 67,20), che i componenti li ha. 83 è la
revisione 2 di 63, 84 la 3 di 83, del 2026-05-28. Fino a `20261005-19-update-fn-crea-revisione-offerta-copia-componenti`
la revisione non copiava i componenti («una revisione di un'offerta con un bundle nasceva senza componenti»): il
difetto è già corretto, le righe sono quello che ha lasciato. ⚠️ 84 è ACCETTATA: oggi «Genera ordine» su 84 dà i kit al
prezzo del listino.

**Le strade che oggi lasciano un kit col prezzo forzato senza componenti** (dal modello, non dai dati):

* **Svuotarlo**: il backend spegne o toglie i componenti uno per uno (`delete_componente_eccezione`), e il guard
  `trg_oce_comp_a10_guard_obbligatorio_upd` ferma solo gli obbligatori. Un kit coi soli opzionali si spegne tutto:
  il padre va a 0 (`fn_ricalcola_prezzo_padre_da_componenti`: «nessun figlio attivo → 0»), e dal giro 5 l'ordine
  ricadrebbe sui componenti del listino.
* **L'eccezione a consumo**: la init non fa niente quando la quantità è NULL, cioè con una fonte diversa da `FISSA`
  (`chk_offerte_eccezioni_quantita_per_fonte`). Su dbdev nessun kit così (fatto datato): resta da dire se il modello
  ammette un kit a consumo col prezzo forzato.

**Perché la regola non può stare alla nascita dell'eccezione.** Tutte e due le strade scrivono l'eccezione **prima**
dei suoi componenti, in due istruzioni. Un guard sull'`INSERT` dell'eccezione la fermerebbe sempre. Le forme possibili:

* **(b1) un vincolo differito al commit** (constraint trigger `DEFERRABLE INITIALLY DEFERRED` sull'eccezione e sui suoi
  componenti): giudica la transazione finita, e vede anche lo svuotamento. Costo: i pgTAP girano con
  `SET CONSTRAINTS ALL IMMEDIATE`, e ogni fixture che crea un OVERRIDE su un kit in due istruzioni andrebbe riscritta;
  in più ogni scrittura dei componenti rifà il controllo.
* **(b2) — proposta: la regola al passaggio fuori dalla bozza.** Un'offerta si modifica solo in bozza
  (`E_RIGA_DOC_NON_BOZZA` su eccezioni e componenti): basta giudicarla quando la si emette. La sede c'è già: i motivi
  di «Emetti» (`script.fn_available_actions_offerta`, oggi `fn_check_listino_congelabile` e
  `fn_check_prezzi_autorizzati`) e il guard della transizione che li rilegge
  (`vendite.trgfn_offerte_commerciali_guard_transizione`): una check nuova entra in tutti e due, come le altre. Copre in un punto solo il backend, la revisione e lo svuotamento,
  e non dipende dall'ordine delle istruzioni. Con **(a) come rete** in `script.fn_check_righe_offerta_in_ordine` per le
  offerte già accettate (84), e lo stesso motivo nel push a contratto, che copierebbe un kit senza componenti.

Se Tid sceglie (b2), il giro dice anche che cosa fare del kit a consumo (esente, o rifiutato) e delle quattro righe di
dbdev (non è produzione: la init sulle due offerte, o niente).

### 8.19 Giro 5-bis — un kit col prezzo negoziato esce dalla bozza coi suoi componenti; scritto e provato il 2026-11-21

> **Chi scrive:** sessione DB (`dev/db-tid`), 2026-11-21. **A chi:** Tid per l'apply; team FE e BE per le due
> richieste in fondo. Decisione di Tid, 2026-11-21: «D-7-bis opzione b2, kit a consumo esente, sistema le quattro righe».

**Le quattro righe di dbdev, riparate (2026-11-21).** Si è fatto ciò che la revisione corretta avrebbe fatto: alle
eccezioni 42, 43 (offerta 83) e 45, 46 (offerta 84) sono stati copiati i componenti delle loro origini nell'offerta
radice 63 (36 e 40, stesso articolo e stesso tipo), con le colonne di `fn_crea_revisione_offerta`. Il ricalcolo del padre
le porta a `COMPONENTI`, come le origini, allo stesso prezzo (5,99 e 67,20). Le due offerte sono fuori bozza: i due lock
di riga (`trg_oce_comp_a05_doc_bozza_ins_upd_dlt`, `trg_offerte_commerciali_eccezioni_a05_doc_bozza_ins_upd_dlt`) sono
stati spenti **solo dentro la transazione**, con `SET CONSTRAINTS ALL IMMEDIATE` perché i trigger differiti scattassero
e non restassero in sospeso; provata prima con ROLLBACK, poi eseguita, trigger riaccesi e verificati. Componenti nuovi:
id 1990 … 1999. Disfarla: `DELETE` di quegli id, coi due lock spenti nello stesso modo. Non è un changeSet: sono dati di
sviluppo, e da zero non ci sono.

| changeSet | Che cosa |
| --- | --- |
| `20261120-18` | `script.fn_check_offerta_kit_con_componenti(offerta)`, `BEGIN ATOMIC`: un motivo per ogni eccezione attiva OVERRIDE o AGGIUNTA su un composito, a quantità fissa, senza componenti attivi. Codice `E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI` (`DATO_ERRATO`: il rimedio è nella stessa offerta), reason `KIT_SENZA_COMPONENTI`, valori offerta e articolo |
| `20261120-19` | `vendite.trgfn_offerte_commerciali_guard_transizione`: all'emissione dallo stato iniziale, dopo le righe, il primo motivo della check |
| `20261120-20` | `script.fn_available_actions_offerta`: «Emetti» spento con lo stesso motivo, per ultimo, come il guard (§12.2) |
| CSV | `config/codici_errore.csv` e `config/messaggi_errore.csv` (id 1518): li carica `20260614-08` (`loadUpdateData`), senza changeSet nuovo |

**Le scelte.**

* ⚠️ **AGGIUNTA compresa, oltre all'OVERRIDE di D-7.** È l'altro tipo col prezzo negoziato (`_TIPI_ECCEZIONE_CON_GATE`
  del backend): un kit aggiunto senza componenti ha lo stesso difetto, e lo stesso modello. Se Tid vuole il solo
  OVERRIDE, è una riga della check.
* **Il kit a consumo, esente (D-7-bis).** Un fatto del modello trovato scrivendo il test: un composito si vende solo a
  quantità fissa (`vendite.fn_articolo_erogazioni`, I-D6 del 2026-10-21), quindi un kit a consumo oggi non nasce.
  L'esenzione sta nella check lo stesso (`quantita IS NOT NULL`), perché la decisione resti scritta se I-D6 cambiasse;
  il pgTAP non può costruire il caso, e lo dice.
* ⚠️ **Niente rete su «Genera ordine» e sul push a contratto**, che il §8.18 proponeva. ACCETTATA si raggiunge solo da
  EMESSA (matrice `config.stati_doc_offerte_transizioni`), e in EMESSA si entra dalla bozza (il controllo nuovo) o
  rientrando da SUPERATA, a contenuto invariato: fuori dalla bozza eccezioni e componenti non si scrivono. Riparate le
  quattro righe, un'offerta accettata con un kit così non può esistere: una rete non scatterebbe mai.
* **Lo svuotamento** (componenti tolti o spenti uno per uno in bozza) è coperto: lo vede l'emissione.

**Prova** (`scripts/prova_changeset.py` sullo scratch, estratto degli otto changeSet `-13 … -20`, transazione ritirata,
catalogo identico prima e dopo):

* ⚠️ esteso dalla revisione (§8.20: l'AGGIUNTA e l'OVERRIDE semplice). Il pgTAP nuovo `vendite/test-offerta-emissione-kit-con-componenti-v1` (7): con l'estratto 7/7, senza muore al primo
  test. Il kit forzato coi componenti non dà motivi; tolti i componenti, un motivo che nomina il kit, «Emetti» spento con
  `KIT_SENZA_COMPONENTI`, emissione rifiutata col codice nuovo; rimessi i componenti, l'emissione passa. ⚠️ Nella prova le
  due righe dei CSV sono state inserite in testa alla copia del test (lo scratch non carica i CSV fuori da Liquibase): il
  file nel repo non le ha, e dopo l'apply le trova nel catalogo;
* 74 pgTAP che emettono offerte, ne leggono la capability o toccano le funzioni del giro 5: uguali con e senza
  l'estratto. I rossi già presenti sono quelli da owner per costruzione (`magazzino/test-documenti-interni-guard-v1`
  7, 7b, 10; `vendite/test-annullo-documento-con-legami-v1` 27; `script/test-fn-is-proprietario-tabella-v1`), le misure
  sui documenti presenti di `script/test-capability-annulla-aspetto-e-stato-leggibile-v1` (zero sullo scratch) e la
  fixture di `test-fn-contratto-righe-preview-nuovi-campi-v1` (§8.17);
* guardrail sugli otto changeSet e `pre-commit` sui file del giro, CSV compresi: puliti. `%TYPE` su ogni parametro e su
  ogni colonna nuova dei `RETURNS TABLE`.

**Per Tid, dopo l'apply:** i pgTAP del §8.17 più `vendite/test-offerta-emissione-kit-con-componenti-v1`; poi la
rigenerazione della doc auto-generata (le pagine dei due BB nuovi non ci sono ancora, e le pagine `manual/` e la guida
le citano). ⚠️ La doc rigenerata porta la reason_key nuova: `scripts/check_i18n_keys.py` (pre-commit e CI frontend) la
pretende nei locales, quindi il commit della doc va **dopo** la richiesta FE qui sotto.

**Doc scritta a mano:** `guide/gestione-offerte-commerciali.md` (§3.2, il quinto controllo dell'emissione, e la tabella
dei codici), `dbzero/vendite/manual/fn_offerta_righe_espanse.md`.

#### Richiesta FE (`dev/backend-tid`) — elenco chiuso

**Chi cambia per primo:** il FE, prima del commit della doc rigenerata. Oggi il DB non emette la chiave finché il giro
non è applicato; dopo, «Emetti» spento mostra `{reason_key}` grezzo senza la traduzione.

| File | Chiave | Testo |
| --- | --- | --- |
| `frontend/src/locales/it.json` | `vendite.offerte.azione_reason.kit_senza_componenti` | «Un kit col prezzo negoziato non ha componenti attivi: aggiungili o riattivali prima di emettere l'offerta.» |
| `frontend/src/locales/en.json` | stessa | «A kit with a negotiated price has no active components: add or re-enable them before issuing the offer.» |

Accanto alle sorelle `listino_senza_versione_in_vigore`, `listino_versione_non_attiva`, `documenti_vivi`. Nessun
componente cambia: «Emetti» legge già `reason_key` dalla capability.

#### Richiesta BE (`dev/backend-tid`) — elenco chiuso

**Chi cambia per primo:** il DB (il codice nasce nel catalogo con l'apply). Poi il BE rigenera la policy degli errori
col DB allineato a git: `backend/apps/core/services/error_policies_generated.py` e il ripiego
`error_messages_fallback.py` per `E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI` (classe `DATO_ERRATO`, due valori: codice
dell'offerta, codice dell'articolo). Nessun service cambia: il rifiuto viene dal guard della transizione, sulla strada
che l'emissione già percorre.

### 8.20 Revisione del giro 5 e del 5-bis (`/verifica-db`, 2026-11-21)

> **Chi scrive:** sessione DB di revisione (`dev/db-tid`), 2026-11-21. **A chi:** Tid, per l'apply.

**Regge.** Gli otto changeSet non sono applicati (né dbdev né scratch, `databasechangelog`). I sei rollback
coincidono col corpo vivo di dbdev; i corpi nuovi sono il vivo più le modifiche dichiarate; numerazione senza doppi;
guard e capability leggono la stessa check, nello stesso ordine (§12.2); id 1518 libero, CSV in LF, due segnaposti per
due valori.

**Corretto.**

* `vendite/test-provenienza-prezzo-offerta-ordine-v1`: i componenti di K2 erano tutti e due `MANUALE`, che è anche il
  ripiego di `vendite.fn_componente_override` quando l'override non porta l'origine: il test 8 non distingueva la
  provenienza copiata dall'eccezione da quella persa. Ora F2 è `LISTINO_BUNDLE` con la versione (al prezzo del
  listino, 30: K2 vale 70), e il test 8 la ritrova sul componente d'ordine. Mancava R3 (§8.16, 5-4): il kit K3, fuori
  listino, in `AGGIUNTA` coi componenti a 15 e 5, test 10 (`COMPONENTI` a 35). Plan 10.
* `vendite/test-offerta-emissione-kit-con-componenti-v1`: l'`AGGIUNTA` compresa dalla check (§8.19, «Le scelte») non
  era costruita, né il caso che non deve dare motivi (un OVERRIDE su un articolo semplice). Ora l'offerta ha anche B
  forzato (test 2: nessun motivo), e il test 3 aspetta due motivi, K2 in OVERRIDE e K3 aggiunto senza componenti, con
  il codice dell'offerta oltre all'articolo. Plan invariato, 7.
* `20261120-14`: chiamanti e `COMMENT` dimenticavano `script.fn_articolo_riga_contesto`, che legge il solo
  `articolo_id` per nome (nessun effetto), e il pgTAP `vendite/test-righe-eccezioni-articolo-ammesso-v1`.
  L'intestazione diceva «le due colonne»: è una.

**Prova** (`scripts/prova_changeset.py`, gli otto changeSet, sullo scratch): i due pgTAP estesi 10/10 e 7/7 (il
secondo con le due righe dei CSV in testa a una copia, come nel §8.19), tutti e due morti al primo test senza
l'estratto; `test-offerta-righe-espanse` 10/10; uguali con e senza l'estratto `test-provenienza-prezzo-copie-v1`,
`test-sorgente-righe-vendita-v1`, `script/test-rubinetto-primo-motivo-v1`,
`offerte_commerciali/test-righe-ammesse-ai-passi-e-annullo-v1`, `test-righe-adesione-v1`,
`test-righe-esclusione-solo-non-si-vende-v1`, `test-righe-eccezioni-articolo-ammesso-v1`,
`test-listino-versione-in-vigore-v1`, `test-sorgente-commenti-al-presente-v1`. `pre-commit` sui file del perimetro:
pulito. Da owner: la row security non entra nella prova.

### 8.21 Apply e pgTAP del giro 5 e del 5-bis — verdi (Tid, 2026-11-21)

* **Apply** di `20261120-13 … -20` su dbdev (`databasechangelog`, 2026-11-21 14:54) e delle due righe dei CSV:
  `E_OFFERTA_EMISSIONE_KIT_SENZA_COMPONENTI` è nel catalogo dei messaggi.
* **pgTAP verdi** (Tid): quelli del §8.17, del §8.19 e quelli estesi dalla revisione del §8.20
  (`vendite/test-provenienza-prezzo-offerta-ordine-v1`, 10; `vendite/test-offerta-emissione-kit-con-componenti-v1`, 7).
* **Doc auto-generata rigenerata, non ancora committata.** Ci sono le pagine dei due BB nuovi
  (`fn_offerta_eccezione_componenti_espansi`, `fn_check_offerta_kit_con_componenti`), e le pagine `manual/` e la guida
  che li citano ora risolvono. ⚠️ Come previsto al §8.19, `scripts/check_i18n_keys.py` è rosso su un punto solo:
  `vendite.offerte.azione_reason.kit_senza_componenti`, emessa dalla check e assente dai locales (verificato il
  2026-11-21 sera). Il pre-commit fermerebbe il commit della doc: si committa insieme alla chiave del FE (8i), o dopo.
* Per la chiusura (7) restano la chiave del FE e la policy del BE: niente di DB.
