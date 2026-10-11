## 📘 Documentazione Concettuale – Vista `vendite.vw_resi_lista`

> 👀 **Vedi anche**
>
> [vendite.resi](/dbzero/vendite/tabelle/resi) ·
> [vendite.vw_ddt_lista](/dbzero/vendite/views/vw_ddt_lista) (mirror) ·
> [script.fn_available_actions_reso](/dbzero/script/funzioni/fn_available_actions_reso)

---

### 🎯 Scopo Principale

(rev 2026-07-13)

Vista canonica **lista/dettaglio** dei resi per BE/FE, mirror di `vw_ddt_lista`. Espone la testata
reso con i join denormalizzati: stato (`stato_codice_interno`/`stato_descrizione`), destinatario,
billing/emittente/utility/valuta, e la **sorgente** (DDT di provenienza via `ddt_origine_*`).

### Regole chiave

- **`security_invoker=on`** — la RLS del chiamante (`rls_resi_ef_whitelist`) filtra sulla base. La
  reloption va **ri-specificata** in ogni `CREATE OR REPLACE VIEW` (PostgreSQL la azzera).
- Espone `emittente_fiscale_id` (+ `_codice`) per il **filtro applicativo BE** e
  `emittente_ragione_sociale = ragione sociale del soggetto emittente`
  (convenzione etichetta 2026-07-13). ⚠️ Fino al 02-08-2026 era un `COALESCE`
  con `ef.descrizione`: quella colonna **non esiste più**, e il fallback è
  caduto con lei senza che i lettori a valle se ne accorgessero — era il punto
  della fase invisibile del cantiere emittente. Il 2026-08-03 l'alias è stato
  **rinominato** (era `emittente_fiscale_descrizione`), in pari su viste,
  seed liste, BE e FE (piano PrimeVue 5, registro).
- **Alias fedeli** alla sorgente: `codice_interno AS stato_codice_interno` (logica),
  `descrizione AS stato_descrizione` (display) — linee-guida-sql §6c.
- Il reso aggancia il **DDT** (non l'ordine): l'ordine si raggiunge dal DDT. Niente colonne
  trasporto/logistica/importi (asimmetria voluta col DDT in questa slice).

---

### ⭐ La sesta sorella — genealogia in lista (rev 2026-08-25)

Fino al 2026-08-25 `vw_resi_lista` era l'unica delle liste documento **senza**
colonne di lineage: sei sorelle su sette ce l'avevano (`20260715-01..05`,
`20260824-15`), i resi no. Il changeSet `20260825-21` le porta, nella stessa
forma di `vw_ddt_lista`, via
`LEFT JOIN vendite.vw_documento_lineage lin ON (tipo_id = RESO_VENDITA, uid = r.id::text)`:

`pratica_id` · `pratica_numero` · `n_pratiche` · `frontiera_tipo_id` ·
`frontiera_codice` · `frontiera_stato_codice_interno` · `frontiera_fase` ·
`n_discendenti_attivi` · `is_transitato`

⭐ **Su un reso `frontiera_codice` è il numero della NOTA DI CREDITO.** Con
l'arco `S` (`20260825-19`) il reso smette di essere una foglia e la sua frontiera
diventa la nota che lo accredita. La colonna «Transito» risponde quindi a
*«questo reso è già stato accreditato, e con quale documento»* — che prima era
una **quantità** (`gia_accreditato`) dentro un drawer, non un documento in lista.

⚠️ **`fase` non c'era, ed è la trappola.** La vista esponeva `stato_codice_interno`
e `stato_descrizione` ma **non la fase normalizzata**, e il seed della colonna
omonima la cerca con quel nome esatto (`campo_sorgente = 'fase'`): senza
`sr.fase` da `config.stati_doc_reso` la colonna sarebbe nata **vuota e in
silenzio**. Nessun errore: solo una colonna a video che non dice niente.

⚠️ Il join al lineage è **`LEFT`** come sulle sorelle: un reso senza genealogia
compare senza genealogia, non sparisce.

### 🔴 Cosa serve al consumatore, e non è nella vista

- **`frontiera_tipo_codice`** — la vista espone l'`id` (il grafo parla per id),
  mai il codice. Ogni repository di lista lo decodifica con
  `LEFT JOIN config.sorgenti s ON s.id = v.frontiera_tipo_id`.
  ⛔ **Senza, la colonna «Transito» resta muta**: `LineageFrontieraChip` ha il
  gate su `isTransitato && tipoCodice` e renderebbe «—», cioè *«non
  transitato»*, proprio sul reso che HA transitato. Difetto trovato il
  2026-08-25 e presidiato da
  `apps/vendite/tests/services/test_lineage_liste_be.py`.
- **`frontiera_natura_doc_codice_interno`** — ✅ **c'è dal 2026-08-29**, e su
  questa vista serve sempre. `vendite.fatture` è una tabella sola: fattura e nota
  di credito si distinguono solo per `natura_doc_id`, e la frontiera di un reso
  accreditato è **sempre** una nota di credito (pgTAP 35). Senza la natura la
  colonna «Transito» etichettava «Fattura» il documento che il cantiere esiste
  per nominare.
  ⚠️ **Il nome porta il suffisso `_interno` e non è un vezzo**: il valore viene da
  `config.nature_doc_fiscale.codice_interno`, la colonna **immutabile** su cui si
  fa logica, e chiamarla `*_codice` — il nome della colonna *modificabile* —
  è vietato da `linee-guida-sql` §6c, con un guardrail CI che lo blocca.
  *(Testo superato, tenuto perché spiega da dove si veniva: «non c'è, e la
  colonna manca su `vw_documento_lineage`, che è la sede; il pannello
  «Passaggi» la ricava per conto suo in `get_lineage_nodo` joinando
  `vw_documento_lineage_nodi` su `frontiera_uid` — chiave che le liste non
  hanno». La sede l'ha esposta il `20260828-22`, le sette liste la portano
  avanti dal `20260829-01`.)*
- **`frontiera_tipo_codice_interno`** — il **codice** del tipo di frontiera
  accanto al suo id (`20260829-02`). Prima ogni repository si rifaceva lo stesso
  join a `config.sorgenti`: dieci copie scritte a mano, tutte fuori dalla portata
  del guardrail, che scansiona solo le viste.

### Consumo

`ui.lista_definizione 'vendite.resi'` (id 9) + preset `resi_default` (id 9); il
frontend è già `<ListaConfigurabile>`, quindi le colonne arrivano dal seed
(`lista_colonna` 549/550/551) — ma i **tre slot** `#cell-pratica`, `#cell-fase`,
`#cell-transito` vanno scritti nel componente, come sulle cinque sorelle: senza,
il BB rende il valore grezzo (la fase come testo, la frontiera come numero nudo).

---

### 🔄 rev 2026-10-11 — la lista non calcola più il grafo

Changeset `20261011-97`. La vista non legge più la sintesi della lineage di tutti
i documenti. Le colonne della frontiera e del transito (`frontiera_*`,
`n_discendenti_attivi`, `is_transitato`) le chiede il backend a
[`fn_documento_lineage_sintesi`](fn_documento_lineage_sintesi.md) per i soli
documenti della pagina. La pratica (`pratica_id`, `pratica_numero`,
`n_pratiche`) resta qui, filtrabile e ordinabile, e la legge
`pratiche.fn_pratica_del_documento`. Una pagina da 25 righe costava ~320-390 ms,
ora ~8-70 ms più la sintesi delle 25 chiavi (~58 ms) — dbdev, 2026-10-11.

