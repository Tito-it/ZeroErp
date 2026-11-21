# Brief DB — Le liste di documento sono lente: la lineage si ricalcola per ogni riga

> **Chi chiede:** Tid, 2026-10-05 («questo test è molto lento»
> `vendite/test-colonne-lineage-liste-v1.sql`; poi «se serve ottimizziamo anche le query reali che
> poi servono alla app per funzionare»). **Chi scrive:** sessione DB (`dev/db-tid`).
> **Stato:** ✅ **passo 1 applicato da Tid il 2026-10-05** (`20261005-20`): effetto immediato a video,
> le liste di preventivi, ordini e le altre «si aprono a scheggia» (Tid). Provato prima come
> applicazione su dbdev (righe identiche) e sullo scratch (38 pgTAP identici).
> ✅ **Passo 2 applicato da Tid il 2026-10-05** (`20261005-21`, §6): «la lista preventivi è
> velocissima, ma anche le altre hanno guadagnato». Misure dopo l'apply nel §6. Cantiere **chiuso e
> archiviato il 2026-10-05**: nessun lavoro BE/FE (colonne e righe delle viste invariate).

## 1. Che cosa si vede

Aprire una lista di documento costa due query (il `COUNT` e la pagina da 25). Misurate il
2026-10-05 su dbdev **come `zeroerp_app` col contesto operatore**, cioè come le esegue l'app:

| Lista | Righe visibili | COUNT | Pagina (25) |
| --- | ---: | ---: | ---: |
| preventivi | 168 | 3,1 s | 2,9 s |
| ordini | 108 | 2,2 s | 1,1 s |
| offerte, contratti, DDT, resi, fatture | 10-51 | ~0,8 s | ~0,9-1,1 s |

⚠️ **Da owner non si vede** (la RLS non c'è e il planner sceglie da solo l'hash join): è la forma
della memoria «join sotto policy». I numeri sono un fatto datato; il motivo è nel §2.

## 2. Perché

Le sette viste di lista fanno `LEFT JOIN vendite.vw_documento_lineage lin ON lin.tipo_id = <tipo>
AND lin.uid = p.uid`. Quella vista calcola la lineage di **tutti** i documenti visibili (una
ricorsione sugli archi, poi frontiera, discendenti, sorgenti, pratica), e il filtro per `uid` non
può scendere dentro la ricorsione. Due difetti:

1. **Per riga.** Sotto RLS il planner stima poche righe e sceglie un *nested loop*: la parte non
   ricorsiva del calcolo si riesegue **per ogni riga della lista** (piano della lista preventivi:
   `loops=168`, ~18 ms ciascuno, 28.056 righe scartate dal filtro di join). È il grosso del costo,
   e cresce con le righe.
2. **Gli archi letti due volte.** `fwd` e `inc` leggevano ciascuno `vw_documento_lineage_archi`
   (~360 ms come applicazione, ogni volta).

Il test `test-colonne-lineage-liste-v1` pagava la stessa cosa 17 volte (le sette viste lette per
intero due volte, più il preventivo tre): ~23 s di sole letture.

## 3. Passo 1 — fatto (`20261005-20`)

`vendite.vw_documento_lineage`: una CTE `archi AS MATERIALIZED` (gli archi una volta), ogni CTE
`MATERIALIZED`, e il risultato finale in una CTE `lineage AS MATERIALIZED`. La lineage si calcola
**una volta per query** e si unisce alla lista per hash. Stesse colonne nello stesso ordine
(`CREATE OR REPLACE`), `security_invoker=on` ripetuto, corpo dal `20260829-02`.

⭐ **Una sede, non sette**: la cura sta nella vista che le liste leggono, non nelle sette liste.

⚠️ **Il vicolo cieco, per chi riapre:** recintare le sole CTE intermedie **peggiora** (lista
preventivi 5,5 s): la SELECT finale sui nodi resta incollata nella query della lista e diventa lei
la parte rieseguita per riga. Serve recintare anche il risultato.

**Misure dopo** (stesso metodo, corpo del changeSet eseguito come query — per una vista è lo stesso
piano):

| Lettura | Prima | Dopo |
| --- | ---: | ---: |
| lista preventivi, COUNT | 3,1 s | 0,44 s |
| lista preventivi, pagina | 2,9 s | 0,45 s |
| altre sei liste, pagina | 0,9-1,1 s | ~0,44 s |
| lineage di un documento (riepilogo del drawer) | 0,75 s | 0,43 s |

**Righe identiche**: `EXCEPT ALL` nei due versi sull'intera lineage e su ognuna delle sette liste,
come applicazione: zero differenze.

**Il prezzo, dichiarato:** chi legge la lineage di **un** documento paga il calcolo di tutto ciò che
vede; già prima la parte ricorsiva si calcolava intera, e con gli archi letti una volta il caso del
documento singolo è comunque più veloce.

**Prova:** SQL estratto sullo scratch (compila, `security_invoker` acceso, le viste dipendenti
leggono); confronto prima/dopo su **38 pgTAP** che leggono la lineage o le viste di lista: 38
identici. Guardrail statici verdi.

**Il test lento**, a parte: `test-colonne-lineage-liste-v1` ora legge le sette viste **una volta**
(due copie temporanee prese dopo il contesto operatore) e le asserzioni leggono le copie: 17
letture → 7. Con il passo 1 applicato ogni lettura costa ~0,44 s.

## 4. Lato BE/FE

Nessuna ricaduta: stesse colonne, stesse righe. ⚠️ Il BE fa sempre `COUNT(*)` sulla vista di
lista: dopo il passo 1 costa quanto la pagina (~0,44 s), perché paga anche lui la lineage. Un
conteggio sulla base senza lineage sarebbe un cambio BE da valutare a parte, se il costo fisso
restasse un problema dopo il §5.

## 5. Passo 2 — il costo fisso negli archi (deciso da Tid il 2026-10-05, scritto nel §6)

Dopo il passo 1 restano ~0,44 s per lettura, quasi tutti in `vw_documento_lineage_archi` (~360 ms):

* due rami (`B` preventivo → commessa, `F` ordine → commessa) uniscono
  `commesse_sorgenti.sorgente_uid` a `p.uid::text` / `o.id::text`: l'espressione non usa l'indice e
  il planner, sotto RLS, rilegge **l'intera tabella** dei preventivi/ordini per ogni commessa
  (`Seq Scan on preventivi loops=47`, ~200 ms; ordini `loops=36`, ~90 ms);
* l'unione archi ↔ nodi (`vw_documento_lineage_nodi`, 469 nodi) è a confronto pieno: 100.152 righe
  scartate dal filtro per 214 archi.

Sono cure locali alla vista degli archi (stesso metodo: recinto `MATERIALIZED` dove il planner
rilegge, e un confronto per hash), da provare come applicazione prima di scriverle. Più in là c'è
la forma «seminata» (la lineage calcolata solo per i documenti della pagina), che però cambia il
contratto della vista: non la propongo senza un caso che la chieda.

## 6. Passo 2 — scritto (`20261005-21`)

`vendite.vw_documento_lineage_archi`: tre CTE `MATERIALIZED` lette una volta — `prev_k` (le chiavi
testuali dei preventivi), `ord_k` (quelle degli ordini), `nodi`. I rami B (preventivo → commessa) ed
E (ordine → commessa) si uniscono alle chiavi invece di rileggere la tabella per ogni riga di
`commesse_sorgenti`; `nf` e `nt` ai nodi calcolati una volta. I rami di contratto e DDT hanno la
stessa forma su tabelle piccole (pochi ms) e restano com'erano.

⛔ **La regola di perimetro** in testa alla vista resta intera: le CTE leggono le tabelle-testata,
sotto la loro RLS (un arco verso un documento che il chiamante non vede continua a non nascere), e
il cast va ancora dall'id al testo, mai dal testo all'uuid.

| Lettura (come app, dbdev, 2026-10-05) | Prima | Dopo |
| --- | ---: | ---: |
| la vista degli archi intera | 380 ms | 90 ms |
| gli archi di un documento (filtro del drawer) | 457 ms | 143 ms |
| lista preventivi, pagina (con il passo 1) | 0,45 s | 0,17 s |
| lista preventivi, COUNT (con il passo 1) | 0,44 s | 0,17 s |

Righe identiche: `EXCEPT ALL` nei due versi sulla vista degli archi e sull'intera lineage.
Prova: corpo dal `20260829-02` verificato equivalente al vivo; sullo scratch `-20` e `-21` insieme
compilano e i 38 pgTAP della lineage e delle liste danno lo stesso esito prima e dopo. Guardrail
verdi.

**Misurato dopo l'apply** (2026-10-05, come app su dbdev, prima pagina da 25):

| Lettura | Stamattina | Dopo i due passi |
| --- | ---: | ---: |
| preventivi | 2,9 s | 0,19 s |
| offerte | 0,9 s | 0,17 s |
| ordini | 1,1 s | 0,18 s |
| contratti | 1,1 s | 0,18 s |
| DDT | 1,1 s | 0,18 s |
| resi | 0,9 s | 0,18 s |
| fatture | 1,1 s | 0,19 s |
| albero del drawer, in avanti (`fn_documento_lineage`) | 1,19 s | 0,32 s |
| albero del drawer, all'indietro | 1,06 s | 0,21 s |

Tutte e sette le liste guadagnano perché tutte leggono pratica, fase e transito dalla stessa
`vw_documento_lineage`: la cura sta in una sede sola.

Riepilogo della giornata: aprire la lista dei preventivi è passato da ~6 s (conteggio più pagina)
a ~0,35 s.
