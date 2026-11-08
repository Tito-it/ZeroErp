## 📘 Documentazione Concettuale – Funzione `vendite.fn_upsert_commessa_attivita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga che scrive
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) · [vendite.stati_commessa](/dbzero/vendite/tabelle/stati_commessa) — la commessa e il suo stato modificabile
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il tipo del documento, il suo `scope` e il tipo di documento fiscale di default
>
> Approfondimento funzioni:
>
> * [vendite.fn_batch_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_batch_upsert_commessa_attivita) — la versione a lotti
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che scrive la provenienza
> * [vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente) — il legame documento → commessa
> * [vendite.fn_aggiungi_onere_commessa](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa) — la madre degli oneri
> * [vendite.fn_resolve_prezzo_listino_v2](/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2) — da dove viene lo snapshot del prezzo
> * [config.fn_get_natura_doc_fiscale_id](/dbzero/config/funzioni/fn_get_natura_doc_fiscale_id) — la natura di default
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

Scrive, o riscrive, una riga di `vendite.commesse_attivita` sulla chiave `(commessa_id, segment_key)`: è la porta da cui il lavoro entra in commessa, dal push di un documento, dalla porta degli oneri o da una rettifica. Restituisce l'id della riga e se è nata ora o è stata aggiornata.

La firma porta per intero lo **snapshot del prezzo** (prezzo base, origine, variazione applicata, promo, contratto, categoria e classe d'utenza congelate): chi chiama passa ciò che il resolver del listino ha calcolato, e la riga lo conserva così com'è.

---

### La provenienza: tipo, chiave, riga

Una riga che nasce da un documento riceve il **tipo** del documento (`p_sorgente_tipo_id`), la
sua **chiave** (`p_sorgente_chiave`) e, se viene da una riga del documento, la **riga**
(`p_sorgente_riga`).

* La chiave arriva come **testo**, `id` o `uid` indifferentemente: chi chiama non deve sapere
  quale delle due usa il tipo. La funzione la passa al BB che scrive,
  [`script.fn_sorgente_chiave`](/dbzero/script/funzioni/fn_sorgente_chiave), che restituisce la
  coppia `sorgente_id` / `sorgente_uid` giusta per il `key_selector` del tipo e solleva su un
  documento che non esiste o non si vede. La funzione non compone la coppia da sé.
* Riga e documento li verifica, alla scrittura, il guard unico della provenienza montato sulla
  tabella; un secondo guard controlla che il `segment_key` nomini proprio quel documento (la
  chiave del gruppo fatturabile prende da lì l'uid).
* Le righe **senza** documento (oneri, rettifiche) arrivano senza tipo e senza chiave, e restano
  con tutta la provenienza vuota.

---

### Il legame documento → commessa nasce con la riga

Una riga che viene da un **documento spinto in commessa** — tipo con
`config.sorgenti.scope = 'PUSH_COMMESSA'`: preventivo, ordine, contratto, bolla, consumi —
prima di scriversi aggancia il documento alla commessa con
[vendite.fn_link_commessa_sorgente](/dbzero/vendite/funzioni/fn_link_commessa_sorgente):

* stesso documento, stessa commessa → il legame c'è già, niente si riscrive;
* il documento sta in un'**altra commessa aperta** → `E_COMMESSA_SORGENTE_ALTRA_COMMESSA`, e la
  riga non si scrive;
* la sua commessa di prima è **chiusa o annullata** → legame nuovo; quello vecchio resta come
  storia.

Fuori: le righe senza documento e il tipo `COMMESSA` (`PIPELINE_MARKER`), che fixture e smoke
usano per le righe «della commessa».

⭐ **Perché qui e non nel backend.** La regola «un documento in una sola commessa aperta» vale
solo se chi scrive la riga scrive anche il legame. Messa nella porta, vale per ogni strada che
manda in commessa, compresi i pgTAP che partono da questa madre.

---

### I controlli prima di scrivere

* **Parametri**: id assenti o non positivi, `segment_key` vuota o più lunga di 128 caratteri,
  quantità uguale a zero, prezzo snapshot assente → `E_PARAMETRO_INVALIDO`. La quantità può
  essere **negativa** (una rettifica di accredito): il predicato è «uguale a zero», ed è la porta
  da cui la nota di credito entra senza una seconda pipeline.
* **Domini dello snapshot**: origine del prezzo e tipo di variazione dentro il loro vocabolario
  (i `CHECK` della tabella sono la rete finale; qui il messaggio è più chiaro).
* **Registro della riga** (`tipo_movimento`): `NORMALE` (il push), `ONERE` (la porta degli
  oneri), `RETTIFICA` (accrediti e conguagli); vuoto vale `NORMALE`.
* **Causale dell'onere**: c'è **se e solo se** la riga è un `ONERE`, come dice il `CHECK` della
  tabella. Il writer di norma è la madre
  [`fn_aggiungi_onere_commessa`](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa).
* **Natura del documento fiscale** che la riga produrrà: se il chiamante non la passa vale
  `FATTURA`, risolta **dentro** la funzione per chiave naturale (un id scritto fra i default
  della firma sarebbe una fotografia del catalogo, sbagliata in silenzio dopo un reseed). Non
  risolta → `E_CONFIG_MANCANTE`.
* **Riga di fattura rettificata**: ammessa solo su una `RETTIFICA`. È un'implicazione, non
  un'equivalenza: una rettifica può non nascere da una riga di fattura (i conguagli).
* **Commessa**: deve esistere (`E_COMMESSA_NON_TROVATA`) ed essere in uno stato modificabile
  (`E_COMMESSA_NON_MODIFICABILE`).
* **Riga già emessa**: se la riga esistente non è più `NON_EMESSA` non si riscrive
  (`E_COMMESSA_ATTIVITA_GIA_EMESSA`).

---

### Il tipo di documento fiscale: un default, non una regola

Il tipo di documento fiscale non si **deriva** da una regola di business (la semantica è aperta,
configurabile per azienda). La funzione applica solo un default:

* se il chiamante lo passa, vale quello;
* altrimenti, se la riga ha un tipo di documento, prende il default dichiarato in
  `config.sorgenti.tipo_doc_fiscale_id`;
* altrimenti resta vuoto. L'obbligo scatta solo sullo stato emittibile (approvata e non
  emessa), col guard `trg_commesse_attivita_a10_guard_tipo_doc_emittibile`
  (`E_COMMESSA_ATTIVITA_TIPO_DOC_OBBLIGATORIO`).

---

### Quando la riga esiste già

L'upsert riscrive la riga con ciò che arriva, con due eccezioni:

* **`meta` si fonde**: il meta esistente si unisce a quello in arrivo. La chiave `tipo_consumo`
  si toglie dal meta **in ingresso** (il reso ricopia il meta della riga d'origine, e senza la
  sottrazione la chiave rinascerebbe sulle rettifiche); sulle righe già scritte resta, come
  fotografia di quell'invio;
* **il tipo di documento fiscale non regredisce**: un nuovo invio senza valore non azzera un tipo
  già risolto; un cambio verso un altro valore resta possibile.

Tutto il resto segue il chiamante: lo snapshot del prezzo (rappresenta il calcolo corrente), la
provenienza, il registro, la causale, la natura e la riga rettificata. Per questi ultimi non serve
una difesa: i `segment_key` del push, della porta degli oneri e delle rettifiche non si
incrociano, quindi un push non può atterrare sul segmento di un onere o di una rettifica.

Anche la **riga di listino** da cui viene il prezzo segue il chiamante: è la provenienza del
prezzo corrente, e una riga di listino risulta «propagata» finché una riga di commessa la cita.

---

### ⚠️ Una firma lunga si cambia con `DROP` e `CREATE`

Con quaranta parametri, molti con un default, aggiungerne o toglierne uno con
`CREATE OR REPLACE` non sostituisce la funzione: PostgreSQL la riconosce dalla firma, e ne
nascerebbe una seconda, con ogni chiamata esistente resa ambigua. Il cambio di firma è sempre un
`DROP` (senza `CASCADE`: i chiamanti la risolvono per nome a runtime) seguito dal `CREATE`. I
chiamanti usano argomenti **nominali**, quindi un parametro nuovo in coda con un default non li
tocca; uno tolto o rinominato sì.

---

### Codici errore

* `E_PARAMETRO_INVALIDO` — un parametro fuori forma o fuori dominio, la causale o la riga
  rettificata incoerenti col registro.
* `E_CONFIG_MANCANTE` — la natura di default non si risolve.
* `E_COMMESSA_NON_TROVATA` · `E_COMMESSA_NON_MODIFICABILE` — la commessa.
* `E_COMMESSA_ATTIVITA_GIA_EMESSA` — la riga esistente è già uscita da `NON_EMESSA`.
* `E_COMMESSA_SORGENTE_ALTRA_COMMESSA` — dalla porta del legame: il documento sta in un'altra
  commessa aperta.
* Dal BB che scrive: un documento che non esiste o non si vede.

---

### Note di migrazione

* 2026-07-21 — arriva la causale dell'onere, per la porta degli oneri.
* 2026-08-18 — arrivano la natura del documento e la riga di fattura rettificata, per la nota di
  credito (brief-design-note-credito-resi).
* 2026-10-09 — arriva la riga di listino da cui viene il prezzo.
* 2026-10-12 — il legame documento → commessa lo scrive la funzione; prima lo scriveva il backend
  a parte (brief-db-annullo-a-valle-riapre-a-monte).
* 2026-10-13 — ritirato il parametro `tipo_consumo`: la funzione lo scriveva solo nel meta e
  nessuno lo leggeva; l'erogazione di un contratto sta in `meta.tipo_erogazione`.
* 2026-11-07 — la provenienza passa al modello: `p_sorgente_uid` lascia il posto a
  `p_sorgente_chiave` (testo, `id` o `uid`), la coppia di colonne la scrive `script.fn_sorgente_chiave`,
  e arriva `p_sorgente_riga` (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
