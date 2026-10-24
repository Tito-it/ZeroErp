## 📘 Documentazione Concettuale – Tabella `vendite.fatture_stampa_coda`

> 👀 **Vedi anche**
>
> **Approfondimento tabelle:**
>
> • [vendite.fatture](/dbzero/vendite/tabelle/fatture)  
> • [vendite.fatturazione_lotti](/dbzero/vendite/tabelle/fatturazione_lotti)  
> • [vendite.fatturazione_pipeline](/dbzero/vendite/tabelle/fatturazione_pipeline)  
>

### 🎯 Scopo Principale
`vendite.fatture_stampa_coda` è la **coda (outbox) della stampa massiva delle fatture**.
Il task di pipeline `stampa_documenti_lotto` vi **accoda** un work-item per fattura al momento
della numerazione (step DEFINITIVA), poi lo step chiude subito la transazione; un **worker**
esterno drena la coda, garantisce la numerazione (backstop idempotente) e delega il render al
processo di stampa generico. Così il rendering dei PDF **non** avviene dentro la transazione
di numerazione e **non** tiene il lock del registro fiscale.

---

### Campi chiave (semantica)

* **Sorgente (satellite fattura)**: `sorgente_tipo_id` (= FATTURA da `config.sorgenti`),
  `sorgente_id` (= `vendite.fatture.id`, FK), `sorgente_uid` (`id::text`) — colonne "a forma
  di" `documenti.genera_documento`.
* **Provenienza**: `lotto_id` (FK, `ON DELETE SET NULL`; `NULL` per ristampa on-demand).
* **Lavorazione**: `stato` (`PENDING` → `IN_CORSO` → `FATTO`/`ERRORE`), `tentativi`,
  `ultimo_errore` (dettaglio JSONB dell'ultimo fallimento).
* **Esito**: `documento_id` (documento prodotto a `FATTO`).
* **Che cosa stampare**: `tipo_documento_output_id` (dal 2026-10-20), il tipo di documento da
  produrre per la fattura, scritto da chi accoda. `NULL` = decide il database alla stampa, se fra i
  modelli che possono stampare ce n'è uno solo; con più tipi la stampa si ferma con
  `E_DOCUMENTI_TEMPLATE_AMBIGUO`.
* **Override**: `template_documento_id` (opzionale; `NULL` = il modello che il database risolve).
  Chi indica il modello esatto indica anche il tipo (`chk_fatture_stampa_coda_modello_con_tipo`),
  e la FK composta `fk_fatture_stampa_coda_template_documento` pretende che il modello sia di quel
  tipo e della sorgente della riga. L'emittente del modello lo controlla la generazione del
  documento (regola 4 di `trgfn_documenti_generati_check_coerenza`).
* **Visibilità nell'elenco**: `archiviato`, `archiviato_il`, `archiviato_da` (dal 2026-09-04)
  — la riga è **messa via dall'elenco**, non spenta. Vedi «Archiviare una riga» più sotto.
* **Governance**: audit standard + `tx_id`.

---

### Regole principali

* **Un work-item "vivo" per fattura e tipo** (dal 2026-10-20): vincolo di **esclusione
  parziale** `ex_fatture_stampa_coda_vivo`, limitato a `PENDING`/`IN_CORSO`. Per una fattura le
  righe vive sono **o** una col tipo `NULL`, **o** più righe con tipi diversi. Il tipo `NULL` vuol
  dire «qualunque tipo il database risolva», quindi esclude le altre righe vive della stessa
  fattura, e viceversa: accanto a una riga tipata sarebbe la stessa stampa due volte (o un
  `AMBIGUO`). È un vincolo e non un controllo in un trigger, così regge anche a due accodamenti
  concorrenti. Rende l'accodamento (`vendite.fn_accoda_stampe_lotto`) **idempotente**
  (`ON CONFLICT DO NOTHING`) e consente il ri-accodamento dopo `FATTO`/`ERRORE` (ristampa).
  ⚠️ Fino al 2026-10-20 era l'indice unico `uq_fatture_stampa_coda_vivo` su
  `(sorgente_tipo_id, sorgente_id)`: una sola riga viva per fattura, quindi una fattura non poteva
  produrre due documenti. Brief: `brief-db-modelli-documento-standard` §9.
* **Stati ammessi** (CHECK `chk_fatture_stampa_coda_stato`): `PENDING`, `IN_CORSO`, `FATTO`,
  `ERRORE`. **Tentativi** `>= 0` (CHECK `chk_fatture_stampa_coda_tentativi`).
* **Satellite della fattura**: `sorgente_id` FK a `vendite.fatture` (`ON DELETE CASCADE`). La
  RLS operatori (scope emittente) **delega alla fattura** via
  `script.fn_scope_ef_whitelist_via_fattura(sorgente_id)`, senza colonna emittente
  denormalizzata.
  ⭐ **Dal 2026-09-04 la policy c'è ed è armata**: `rls_fatture_stampa_coda_ef_whitelist`,
  `FOR ALL` con `WITH CHECK = USING`, gate `OPERATORE`, `NO FORCE` a parità con la famiglia
  fatture.
  ⚠️ **Fin qui questa riga diceva «*in G1 la coda non ha superficie di lettura → nessuna
  policy*», e quella premessa è scaduta in due tempi**: prima con la lista a video della
  scheda «Coda stampa» di Strumenti (`elenca_coda_stampa`), poi — ed è ciò che l'ha resa
  urgente — con il verbo «Archivia», che è la **prima scrittura dell'operatore** su questa
  tabella. Una frase che decide se serve una policy, e che descrive un mondo che non c'è più,
  è il genere di riga che resta vera in archivio e falsa nel prodotto.
* ⛔ **Nessuna policy `ba_ownership`**: la coda stampa non è una superficie del portale
  cliente. Il giorno che lo diventasse, si aggiunge lì.
* **Non è più single-writer**: oltre al drainer scrive l'operatore (archiviazione). I trigger
  di audit e `tx_id` questa tabella **ce li ha** — li generano le automazioni a `ci_apply`,
  quindi non compaiono in nessun changeSet.

---

### Archiviare una riga senza toccarne lo stato

Vale la regola condivisa con [dbops.coda_lavori](/dbzero/dbops/manual/coda_lavori), stessa
funzione trigger (`dbops.trgfn_coda_archiviazione`) e stesso codice errore
`E_CODA_ARCHIVIAZIONE_NON_AMMESSA`: **si archivia solo una riga non viva**, e una riga che
torna viva riabbassa la bandiera da sola.

⭐ **Qui la ragione del limite è più concreta che altrove, e non dipende dal badge**: una riga
**viva** archiviata occuperebbe il posto di riga viva della fattura in `ex_fatture_stampa_coda_vivo` e
**bloccherebbe la ristampa** di quella fattura restando invisibile — l'operatore chiede la
ristampa, non succede niente, e non c'è nessun posto dove guardare. Sulle righe **terminali**
il problema non esiste per costruzione: il vincolo parziale non le vede, quindi
`vendite.fn_accoda_stampe_lotto` fa nascere una **riga nuova** e non tocca quella archiviata.

⛔ **Il flag lo legge solo la lista.** In particolare **non** lo legge
`VenditePipelineRepository.count_coda_stampa_per_stato`, che alimenta il pannello Esiti
fatturazione: è esattamente il punto per cui l'archiviazione esiste.

Brief: `brief-db-archiviazione-righe-code`.

---

### Utilizzo previsto

* disaccoppiare il **render dei PDF** dalla transazione di numerazione fiscale (nessun lock
  del registro tenuto durante l'I/O di generazione);
* garantire che ogni fattura stampata sia **numerata** (backstop idempotente
  `vendite.fn_numera_fattura_opz_emessa` nel worker);
* base per il **monitoraggio** della stampa massiva (filtro per lotto) e per la **ristampa**
  on-demand di una singola fattura;
* **polling FIFO** del worker sui soli da-lavorare via indice parziale
  `ix_fatture_stampa_coda_da_lavorare`.

---

{% include-markdown "signature-core.md" %}
