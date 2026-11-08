## 📘 Documentazione Concettuale – Tabella `config.sorgenti`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [config.tipi_entita](/dbzero/config/tabelle/tipi_entita) — i bersagli che si aprono a video, legati al tipo per `codice_interno`
>
> Approfondimento funzioni:
>
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — scrive la provenienza leggendo `key_selector`
> * [script.fn_sorgente_documento](/dbzero/script/funzioni/fn_sorgente_documento) — risolve il documento leggendo `target_table` e `label_selector`
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico, che legge i livelli
> * [script.trgfn_sorgente_in_uscita](/dbzero/script/funzioni/trgfn_sorgente_in_uscita) — il lato «in uscita», montato sulle tabelle dei livelli
> * [dbops.fn_sorgente_converge_uscita](/dbzero/dbops/funzioni/fn_sorgente_converge_uscita) — monta e smonta il lato «in uscita» dal catalogo
> * [config.trgfn_sorgenti_normalize](/dbzero/config/funzioni/trgfn_sorgenti_normalize) — la normalizzazione dei codici
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il meccanismo intero: il modello, i pezzi, chi resta fuori

---

### 🎯 Scopo Principale

`config.sorgenti` è il **catalogo dei tipi di documento** da cui una riga del sistema può
nascere: per ogni tipo dice dove vive il documento, con quale chiave lo si riconosce, quali
sono le sue righe e il loro dettaglio, e come lo si nomina. È il dato che fa funzionare la
provenienza polimorfa (`sorgente_tipo_id` + la chiave del documento + la riga): chi scrive,
il guard, chi risolve e il lato «in uscita» leggono tutti da qui, e nessuno di loro ha un
elenco di tipi scritto nel codice.

Il **nome del tipo** è il `codice_interno`, ed è uno solo per database e backend.

---

### Che cosa dichiara un tipo

| Colonna | Che cosa dice |
| --- | --- |
| `codice_interno` | il nome del tipo (`ORDINE_VENDITA`, `PREVENTIVO`, …). Fissato all'inserimento |
| `categoria` | la natura: `DOCUMENTO` (un documento, con o senza righe) o `EVENTO` (un fatto con identità propria e senza righe, come l'evento d'asset). Non si ricava dai livelli, perché un documento può non avere righe. Fissata all'inserimento |
| `target_table` | la tabella del documento |
| `key_selector` | la chiave con cui il documento si riconosce: `id` o `uid` |
| `righe_table`, `righe_fk_column` | la tabella delle righe e la colonna che le lega al documento. Vuote = il tipo non ha righe |
| `dettaglio_table`, `dettaglio_fk_column` | il terzo livello: il dettaglio di una riga (il prelievo di una bolla, il rientro di un reso). Richiede le righe |
| `label_selector` | la colonna che porta il **numero leggibile** (`numero`, o `codice` per offerta e commessa). Vuota = il tipo non ha un numero, come il consumo |
| `etichetta` | il nome del tipo come lo legge una persona sulla carta («Ordine», «DDT»): lo usa la stampa |
| `apribile` | il documento ha una sua pagina, e chi lo mostra lo può aprire |
| `citato_in_fattura` | un documento di questo tipo si cita fra le origini di una fattura |
| `scope` | il meccanismo che legge il tipo (il push verso la commessa o verso il contratto, la pipeline, il flusso inverso); `CATALOGO` per i tipi che stanno qui solo per il nome, documenti di magazzino ed evento d'asset compresi: nessun meccanismo li legge per scope |
| `tipo_doc_fiscale_id` | il tipo di documento fiscale associato, quando serve |

---

### ⭐ La chiave `id` o `uid` la dichiara il tipo, e non si unifica

`PREVENTIVO` e `OFFERTA_COMMERCIALE` si riconoscono per `uid`, tutti gli altri tipi per `id`.
Una tabella che dice «nasce da» scrive la chiave nella colonna della sua specie,
`sorgente_uid` o `sorgente_id`, e una sola delle due: la scelta la fa il BB che scrive,
leggendo `key_selector`. Per questo la differenza non pesa su nessuno, e la chiave **non si
unifica** (la ragione è nella guida). `config.tipi_entita.key_selector` risponde a un'altra
domanda, con che chiave il documento si apre a video, e non va confuso con questo.

---

### I livelli sono dichiarati, non ricavati

Righe e dettaglio sono scritti qui con la loro colonna di legame, non ricavati da
`pg_constraint`: la stessa tabella può avere più FK verso il documento, e solo il catalogo dice
quale è quella delle righe. Un pgTAP verifica che la FK dichiarata esista davvero. Su questi
livelli il guard unico controlla che la riga di una provenienza sia del suo documento e il
dettaglio della sua riga, e il lato «in uscita» si monta su ogni tabella che compare qui come
documento, righe o dettaglio.

⚠️ Un tipo nuovo, o un livello nuovo, riceve il suo lato «in uscita» alla migrazione successiva:
lo monta la convergenza dal catalogo, senza un changeSet suo.

---

### ⛔ Che cosa non è un tipo di documento

Le righe di un documento non sono tipi a sé: una provenienza dalla riga di un ordine è il tipo
`ORDINE_VENDITA` con la riga in `sorgente_riga`. Le attività di commessa non sono un tipo: le
attività fatturabili le puntano con una FK vera. Un id che arriva da un sistema esterno non è un
tipo di questo catalogo: l'import avrà una sua tabella di collegamento.

---

### Codici e catalogo

* Il catalogo si scrive solo dal CSV di seed (`80_data/sql/config/sorgenti.csv`), con il suo
  mirror: è l'unico scrittore.
* `codice_interno` e `categoria` sono sotto lucchetto (`E_CODICE_NON_MODIFICABILE`): un nome che
  cambia spezzerebbe ogni provenienza salvata e ogni lettore che lo cita.
* Un tipo non si cancella e non si spegne finché qualche tabella lo usa: i trigger di blocco della
  disattivazione guardano ogni tabella che ha `sorgente_tipo_id`.

---

### Test

* `config/test-sorgenti-livelli-v1` — i livelli dichiarati: la FK di ogni righe e dettaglio esiste
  ed è quella giusta.
* `config/test-sorgenti-scope-pulizia-v1` — i valori ammessi di `scope` e di `categoria`.
* `config/test-grammatica-catalogo-sorgenti-entita-v1`, `config/test-grammatica-etichetta-sorgenti-v1`
  — il nome del tipo è uno solo, e ogni tipo ha la sua etichetta.
* `dbops/test-sorgenti-struttura-v1` — ogni tabella con la provenienza monta il guard unico, salvo
  le esenzioni dichiarate.
* `dbops/test-sorgenti-orfane-v1` — il presidio delle provenienze rimaste orfane.

---

### Note di migrazione

* 2026-10-20 — `apribile` prende il posto della colonna `area`, che diceva la stessa cosa con un
  vuoto e con un vocabolario a parte.
* 2026-11-06 — i livelli (`righe_table`, `dettaglio_table` e le loro colonne) entrano nel catalogo;
  i tipi di riga (`*_RIGA`) di vendita, e poi quelli di magazzino, escono: la riga sta in
  `sorgente_riga`. Il tipo `ATTIVITA` esce, e resta un'entità.
* 2026-11-08 — `categoria` passa al vocabolario della natura (`DOCUMENTO` / `EVENTO`); lo scope
  `ROW_VALIDATOR` esce, perché nessun tipo lo usa più. Esce anche `MAGAZZINO`, che nessun
  meccanismo leggeva: l'evento d'asset diventa `CATALOGO` come gli altri documenti di magazzino.

---

{% include-markdown "signature-core.md" %}
