# Brief DB — La provenienza del prezzo viaggia con il prezzo, dal documento alla commessa

## ⏭️ Chi riparte — aggiornato al 2026-11-12

**Riparte: team DB** (`dev/db-tid`), con la progettazione di R-1 … R-6. Nessuna decisione aperta di
Tid: la decisione B (2026-10-09) fissa il criterio, l'insieme esatto delle colonne e la sede della regola
di R-2 (`CHECK` o guard) le propone il team DB. Verificato il 2026-11-12 (doc auto-generata del
2026-11-09): sul DB **niente è stato fatto** (le righe padre non hanno colonne di provenienza, le
`fn_list_*_da_pushare` restituiscono solo `prezzo_snapshot` e `prezzo_bloccato`). Lato BE il §6.0 è al
suo posto. ⚠️ Il commit `a85b76d58` «Chiusura brief brief-db-provenienza-prezzo-segue-il-prezzo»
chiude in realtà `brief-db-coerenza-listino-della-riga-di-commessa`: **questo brief è aperto**.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | ✅ sessione BE | Il difetto, il contratto, la richiesta; il push non scrive più `listino_riga_id` | §1-§3, §6.0 | — |
| 2 | ✅ sessione BE | Le righe dell'offerta (`offerte_commerciali_eccezioni`) aggiunte al perimetro (2026-11-12) | §2, R-1 | 1 |
| 3 | **team DB** ⏭️ | Le colonne, la regola su chi scrive, il push, le copie a valle, i consumi, pgTAP, la doc | §3 R-1 … R-6 | 2 |
| 4 | team BE/FE | `PushableRow` e `_build_attivita_input`, le scritture delle righe, il form, i test sul DB vero | §6 «Dopo la consegna DB» | 3 |

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
| **R-3** | **Il legame segue il prezzo nel push.** Le cinque `fn_list_*_da_pushare` restituiscono la provenienza della riga (o del componente) accanto a `prezzo_snapshot`. Per le righe che **non** hanno un prezzo alla sorgente (`prezzo_snapshot NULL`: contratti e DDT senza prezzo, `prezzo_bloccato = FALSE`), la provenienza resta `NULL`: il prezzo lo darà il listino più tardi, e chi lo scrive scrive anche la provenienza (riallinea, sblocca — già così lato BE). |
| **R-4** | **La copia a valle dei documenti.** Le funzioni che copiano una riga da un documento all'altro (revisione preventivo/offerta, offerta → contratto, ordine → DDT: `fn_crea_revisione_preventivo`, `fn_crea_revisione_offerta`, `fn_push_offerta_a_contratto`, `fn_genera_ddt_da_ordine`, e le altre che il team DB trova) copiano la provenienza con il prezzo. Da censire. |
| **R-5** | **Consumi.** `fn_list_consumi_da_pushare` ha `prezzo_bloccato = FALSE` «per una ragione diversa» (commento nella funzione): da dire che cosa vuol dire la provenienza per un consumo. |
| **R-6** | **pgTAP**, sul caso costruito: un ordine con prezzo trattato diverso dal listino → la riga di commessa ha origine `MANUALE` (o quella dichiarata) e `listino_riga_id NULL`, e la riga di listino resta rettificabile; un ordine con prezzo precompilato dal listino e non toccato → la riga di commessa cita R, e R è «propagata»; lo stesso ordine con il prezzo cambiato dopo la precompilazione → la provenienza da listino è decaduta (R-2). |

## 4. Rapporto con gli altri brief

* [brief-db-coerenza-listino-della-riga-di-commessa](../work-done/brief-db-coerenza-listino-della-riga-di-commessa.md) (chiuso il 2026-10-17)
  dice che cosa la colonna `listino_riga_id` **può** contenere (stessa versione,
  stesso emittente, versione in vigore). Questo dice **quando** si scrive. Il guard
  di quel brief va montato anche sulle righe di documento di R-1: la stessa regola,
  in più tabelle — candidato building block.
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
