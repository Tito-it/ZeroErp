## 📘 Documentazione Concettuale – I trigger di dominio dello schema `pratiche`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [pratiche.pratiche](/dbzero/pratiche/tabelle/pratiche) — la pratica
> * [pratiche.flussi](/dbzero/pratiche/tabelle/flussi) — i passi della pratica
> * [pratiche.giornale](/dbzero/pratiche/tabelle/giornale) — il diario che i trigger scrivono
> * [pratiche.template_flussi](/dbzero/pratiche/tabelle/template_flussi) — la definizione dei passi
>
> Approfondimento funzioni:
>
> * [pratiche.fn_genera_pratica_da_flusso](/dbzero/pratiche/funzioni/fn_genera_pratica_da_flusso) — la generazione fra pratiche
> * [pratiche.fn_check_prerequisiti_flusso](/dbzero/pratiche/funzioni/fn_check_prerequisiti_flusso) — i prerequisiti di un passo
> * [pratiche.fn_reconcile_sorgente](/dbzero/pratiche/funzioni/fn_reconcile_sorgente) — l'avanzamento dei passi sull'esito di un documento

---

### 🎯 Scopo Principale

Questa pagina è la mappa dei trigger che portano la logica di dominio delle pratiche: il giornale di
bordo, i guard sui passi e sulle pratiche, la generazione fra pratiche, i tempi e le sospensioni.

I trigger standard (audit, transazione, storico, lucchetti di colonna, padre attivo) non sono qui: li
montano i runner del framework di automazione (`dbops.fn_run_automations_*`). Il dettaglio di ogni
trigger sta nella scheda della sua funzione.

---

### Come si leggono i nomi

Il nome di un trigger dice la tabella, la fase, che cosa fa e su quali eventi
(`trg_<tabella>_<fase>_<descrizione>_<eventi>`). La fase governa l'ordine:

* `_a10_` — guard e default: girano per primi e possono fermare la scrittura;
* `_a20_` — derivazioni sulla riga (il periodo di un calcolo o di una sospensione);
* `_m50_` — valori calcolati prima della scrittura (la data di apertura della pratica);
* `_z90_` — effetti dopo la scrittura: giornale, generazione, propagazioni.

A parità di fase PostgreSQL li esegue in ordine alfabetico di nome: l'ordine fra due trigger della
stessa fase si governa col nome.

---

### `pratiche.pratiche`

| Funzione | Quando | Che cosa fa |
| --- | --- | --- |
| `trgfn_pratiche_default_definizione` | prima dell'inserimento | fissa l'edizione del workflow, se manca |
| `trgfn_pratiche_gen_codice` | prima di inserimento e modifica | genera il codice della pratica |
| `trgfn_pratiche_guard_contesto` | prima di inserimento e modifica | coerenza fra soggetto, ruolo e istanza |
| `trgfn_pratiche_guard_pin_immutabile` | prima della modifica | l'edizione fissata non cambia |
| `trgfn_pratiche_guard_transizione` | prima della modifica | solo transizioni di stato ammesse |
| `trgfn_pratiche_guard_chiusura_flussi` | prima della modifica | una pratica non si chiude con lavoro pendente |
| `trgfn_pratiche_set_data_apertura` | prima di inserimento e modifica | la data di apertura |
| `trgfn_pratiche_giornale_ins` | dopo l'inserimento | `PRATICA_CREATA` |
| `trgfn_pratiche_giornale_stato` | dopo il cambio di stato | `STATO_CAMBIATO` |
| `trgfn_pratiche_giornale_assegnazione` | dopo il cambio di assegnazione | `ASSEGNAZIONE_CAMBIATA` |
| `trgfn_pratiche_giornale_priorita` | dopo il cambio di priorità | `PRIORITA_CAMBIATA` |

---

### `pratiche.flussi`

| Funzione | Quando | Che cosa fa |
| --- | --- | --- |
| `trgfn_flussi_guard_definizione` | prima dell'inserimento | il template sta nell'edizione della pratica |
| `trgfn_flussi_guard_prerequisiti` | prima dell'inserimento | i prerequisiti del passo sono soddisfatti |
| `trgfn_flussi_guard_ripetibilita` | prima dell'inserimento | un passo non ripetibile non si ripete |
| `trgfn_flussi_guard_pratica_terminale` | prima di inserimento e modifica | niente lavoro su una pratica chiusa |
| `trgfn_flussi_guard_esito_classe` | prima di inserimento e modifica | l'esito appartiene alla classe del template |
| `trgfn_flussi_guard_esito_completato` | prima di inserimento e modifica | un passo completato ha un esito |
| `trgfn_flussi_guard_transizione` | prima della modifica | solo transizioni di stato ammesse |
| `trgfn_flussi_guard_chiusura_prematura` | prima della modifica | il passo di chiusura non si completa se la pratica non è chiudibile |
| `trgfn_flussi_giornale_ins` | dopo l'inserimento | `FLUSSO_CREATO` |
| `trgfn_flussi_giornale_stato` | dopo il cambio di stato | `FLUSSO_STATO_CAMBIATO` |
| `trgfn_flussi_giornale_assegnazione` | dopo il cambio di assegnazione | il cambio di assegnazione del passo |
| `trgfn_flussi_generazione` | dopo il cambio di stato | la generazione fra pratiche al completamento |
| `trgfn_flussi_calcolo_tempo_completamento` | dopo il cambio di stato | crea e chiude i calcoli di tempo da un passo all'altro |
| `trgfn_flussi_autochiusura_pratica` | dopo il cambio di stato | chiude la pratica quando non resta lavoro |

⚠️ Nella fase finale l'ordine è alfabetico: al cambio di stato di un passo l'autochiusura, il calcolo
del tempo e la generazione girano prima delle righe di giornale.

---

### Note, allegati, sospensioni, tempi

* `pratiche.note_pratiche`, `pratiche.note_flussi` — dopo l'inserimento scrivono `NOTA_AGGIUNTA`
  (`trgfn_note_pratiche_giornale`, `trgfn_note_flussi_giornale`); per la nota di un passo la pratica si
  legge dal flusso.
* `pratiche.allegati_pratiche`, `pratiche.allegati_flussi` — dopo l'inserimento scrivono
  `ALLEGATO_AGGIUNTO` (`trgfn_allegati_pratiche_giornale`, `trgfn_allegati_flussi_giornale`). Le tabelle
  degli allegati non portano la transazione: la riga del giornale riceve quella della sessione.
* `pratiche.sospensioni` — guard di coerenza col flusso e sulla data non futura, il periodo, il
  giornale di apertura e di chiusura, la propagazione della sospensione ai flussi e la loro
  riattivazione (`trgfn_sospensioni_*`).
* `pratiche.calcoli_tempo` — i riferimenti del calcolo sono immutabili, e il periodo si deriva
  (`trgfn_calcoli_tempo_guard_immutabili`, `trgfn_calcoli_tempo_set_periodo`).
* `pratiche.pratiche_sorgenti` — il documento collegato a un passo è coerente col passo
  (`trgfn_pratiche_sorgenti_guard_coerenza_flusso`).

---

### Definizioni di workflow

* `pratiche.workflow_definizioni` — il ciclo di vita delle edizioni (`trgfn_workflow_definizioni_guard`).
* `pratiche.tipi_prestazione` — un tipo nuovo nasce con la sua edizione preset
  (`trgfn_tipi_prestazione_bootstrap_definizione`).
* `pratiche.template_flussi` — l'edizione di default, l'immutabilità di un'edizione congelata e la
  coerenza della modalità d'esito (`trgfn_template_flussi_default_definizione`,
  `trgfn_template_flussi_guard_immutabile`, `trgfn_template_flussi_guard_modalita_esito`).
* I figli del template (prerequisiti, competenze, canali, handler, formule di tempo, regole di
  generazione) sono immutabili quando l'edizione è congelata
  (`trgfn_template_flussi_figli_guard_immutabile`).
* `pratiche.template_flussi_avanzamento_proiezione` e `pratiche.template_flussi_handler_eventi` — un
  avanzamento su proiezione sta solo su un passo che non è di dominio, e non convive con un handler
  di completamento sullo stesso passo; il controllo è montato dai due lati
  (`trgfn_tfap_guard_compatibilita`, `trgfn_tfhe_guard_no_proiezione`).

---

### Fuori dallo schema

`pratiche.trgfn_documento_reconcile_proiezione` è montata sui documenti di vendita (oggi
`vendite.preventivi`): a ogni cambio di stato del documento chiama `pratiche.fn_reconcile_sorgente`,
che fa avanzare i passi delle pratiche che lo attendono.

---

### Il giornale: lo schema comune

Le funzioni di giornale scrivono una riga di `pratiche.giornale` con l'azione del fatto, origine
`SISTEMA` e i dati rilevanti nel dettaglio. Per le tabelle figlie dei flussi la pratica si legge dal
flusso. I trigger sui cambi di stato, assegnazione e priorità scattano solo quando il valore cambia
davvero.

---

{% include-markdown "signature-core.md" %}
