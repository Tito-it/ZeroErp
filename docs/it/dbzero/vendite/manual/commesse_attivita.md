## 📘 Documentazione Concettuale – Tabella `vendite.commesse_attivita`

> **Ultimo aggiornamento**: 12 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse](/dbzero/vendite/tabelle/commesse) — la commessa a cui la riga appartiene
> * [vendite.commesse_sorgenti](/dbzero/vendite/tabelle/commesse_sorgenti) — il link del documento alla commessa, scritto insieme alla riga
> * [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili) — l'attività fatturabile che l'emissione ricava dalla riga
> * [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni) — la versione di listino sotto cui la riga è registrata
> * [config.sorgenti](/dbzero/config/tabelle/sorgenti) — il catalogo dei tipi di documento, con la chiave di ognuno
>
> Approfondimento funzioni:
>
> * [vendite.trgfn_attivita_fattore_alla_data](/dbzero/vendite/funzioni/trgfn_attivita_fattore_alla_data) — il fattore alla data dell'attività, quando la riga non lo porta
> * [vendite.fn_upsert_commessa_attivita](/dbzero/vendite/funzioni/fn_upsert_commessa_attivita) — la madre che scrive la riga
> * [script.fn_sorgente_chiave](/dbzero/script/funzioni/fn_sorgente_chiave) — il BB che dà la chiave del documento da scrivere
> * [script.trgfn_guard_sorgente](/dbzero/script/funzioni/trgfn_guard_sorgente) — il guard unico della provenienza
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza

---

### 🎯 Scopo Principale

La tabella `vendite.commesse_attivita` è la fonte di verità operativa delle righe da emettere
verso `attivita_fatturabili`.

Contiene snapshot pricing (`prezzo_snapshot`, `prezzo_bloccato`), competenza,
segmentazione idempotente (`segment_key`) e stato approvazione/emissione.

---

### Regole principali

* `segment_key` univoca nel perimetro commessa (`commessa_id + segment_key`);
* `istanza_utility_id` sempre valorizzata (anche tramite istanza fittizia);
* `competenza_mese` al primo giorno del mese;
* `prezzo_snapshot >= 0`, `factor_to_base > 0`;
* `pricing_mode`:
  * `FIXED`
  * `FORMULA`
  * `SCAGLIONI`
* `stato_approvazione`:
  * `BOZZA`
  * `APPROVATA`
  * `RIFIUTATA`
* `stato_emissione`:
  * `NON_EMESSA`
  * `EMESSA`
  * `ANNULLATA`
* `tipo_movimento` (registro della riga, vedi sezione dedicata):
  * `NORMALE`
  * `ONERE`
  * `RETTIFICA`

---

### Il fattore verso la base

`factor_to_base` dice quante unità base vale un'unità della riga. Non ha più un default: un
«1 quando non so» faceva passare 3 cartoni come 3 pezzi.

* **Il fattore scritto si rispetta**: è la fotografia copiata dal documento sorgente o dalla
  riga che si rettifica.
* **Senza fattore** lo legge `vendite.trgfn_attivita_fattore_alla_data`, alla data
  dell'attività (`data_attivita`), per l'unità operativa, o per l'unità della riga se
  l'operativa non c'è, o per l'unità base se non c'è nessuna delle due: 1 per la base, la
  mappatura dell'articolo o la conversione generale in vigore quel giorno per le altre.
* **Senza neanche quello** la riga è rifiutata con `E_UOM_MISSING`, sul campo dell'unità.
* Se un aggiornamento cambia l'unità e non il fattore, il fattore si rilegge per l'unità nuova.

La quantità base (`quantita`) la porta chi scrive: la tabella non la ricalcola.

---

### Da quale documento nasce la riga: tipo, chiave, riga

La riga dice il documento da cui nasce con le colonne del modello della provenienza:

* `sorgente_tipo_id` — il tipo del documento in `config.sorgenti` (preventivo, ordine,
  contratto, DDT, consumi). È vuoto solo per le righe senza documento, `ONERE` manuale e
  `RETTIFICA` (`chk_commesse_attivita_senza_sorgente_onere_rettifica`);
* `sorgente_id` *oppure* `sorgente_uid` — la chiave del documento: **una sola**, quella che il
  `key_selector` del tipo dichiara (uid per il preventivo, id per ordine, contratto, DDT e
  consumi). La forma la tiene `chk_commesse_attivita_sorgente_forma`;
* `sorgente_riga` — la riga del documento, quando la provenienza è una riga; vuota quando è il
  documento intero (i consumi, che non hanno righe, e le quote fisse del listino di un
  contratto, che non corrispondono a una riga del contratto).

Il chiamante passa il tipo e una chiave qualsiasi del documento, id o uid: la coppia di colonne
la decide il BB che scrive, `script.fn_sorgente_chiave`, dentro
`vendite.fn_upsert_commessa_attivita`. Il guard unico `script.trgfn_guard_sorgente` verifica che
il documento (e la riga, se c'è) esista, e blocca la cancellazione del documento finché una
riga di commessa lo cita.

#### ⚠️ La `segment_key` porta sempre l'uid del documento

La chiave d'idempotenza del push (`<CODICE>:<uid>…`) nomina il documento con il suo **uid**,
anche per i tipi a chiave `id`: è la chiave che compone il push, e da lì si legge la chiave
del gruppo fatturabile (`vendite.fn_gruppo_fatturabile_key_di_attivita`). Che la chiave
nomini proprio il documento della provenienza lo verifica
`vendite.trgfn_commesse_attivita_guard_sorgente_segment`
(`E_COMMESSA_ATTIVITA_CHIAVE_NON_DEL_DOCUMENTO`): una chiave che nominasse un altro documento
metterebbe la riga nel gruppo sbagliato, in silenzio. Le righe senza tipo passano.

Chi cerca le righe di un documento usa le colonne della provenienza, non la `segment_key`.

---

### Utilizzo previsto

* input del pull `fn_emit_attivita_fatturabili_da_commessa`;
* supporto idempotenza e replay controllato;
* separazione netta owner business (commessa) vs layer esecutivo (AF).

---

### Snapshot pricing: le dimensioni del prezzo

All'esecuzione del resolver prezzi, l'attivita' in commessa riceve uno snapshot strutturato delle dimensioni di calcolo. Colonne nullable, valorizzate insieme a `prezzo_snapshot`/`prezzo_bloccato` esistenti:

| Colonna                          | Tipo          | Descrizione                                                                                       |
| -------------------------------- | ------------- | ------------------------------------------------------------------------------------------------- |
| `prezzo_base_snapshot`           | numeric(22,10)| Prezzo base risolto dal listino prima della variazione applicata                                  |
| `origine_prezzo`                 | varchar(32)   | `PROMO` \| `CONTRATTO_OVERRIDE` \| `CONTRATTO_LISTINO` \| `CATEGORIA` \| `MANUALE`                |
| `tipo_variazione_applicata`      | varchar(16)   | `PERCENTUALE` \| `VALORE_FISSO` \| `PREZZO_FISSO` \| `NESSUNA`                                    |
| `valore_variazione_applicata`    | numeric(10,4) | Valore della variazione effettivamente applicata                                                  |
| `promo_id`                       | bigint        | FK a `vendite.promo_articoli`; valorizzato se `origine_prezzo = 'PROMO'`                          |
| `contratto_id`                   | bigint        | FK a `vendite.contratti`; valorizzato se `origine_prezzo CONTRATTO_*`; il contratto è del conto di fatturazione della commessa (guard `trgfn_attivita_guard_contratto`) |
| `categoria_cliente_id_snapshot`  | smallint      | FK a `anagrafiche.categorie_clienti`; congela la categoria al momento del calcolo                 |
| `classe_utenza_id_snapshot`      | integer       | FK a `config.classi_utenze`; congela la classe utenza al momento del calcolo                      |

Due CHECK presidiano il dominio di `origine_prezzo` e `tipo_variazione_applicata`. Il campo `meta` resta per dettagli non strutturati (es. deroghe, flag specifici): qui stanno solo le dimensioni che servono per query dirette e filtri dashboard.

Le stesse 8 colonne vengono propagate su [`vendite.attivita_fatturabili`](/dbzero/vendite/tabelle/attivita_fatturabili), preservando la tracciabilita' fino al layer fatture.

---

### Riga di listino e versione: coerenti

La riga porta la **versione** del listino sotto cui è registrata (`listino_versione_id`) e la
**riga di listino** da cui viene il prezzo (`listino_riga_id`). Le due non possono dire cose
diverse: la riga di listino deve essere dello stesso articolo e della stessa unità di misura
della riga di commessa e, se la versione c'è, di quella versione. La versione senza riga di
listino è lecita (il push la scrive così); la riga di listino senza versione no
(`chk_commesse_attivita_listino_riga_con_versione`). Il listino
dev'essere **dell'azienda della commessa** e la versione **non in bozza**: mai un prezzo da una
bozza. Lo tiene
[vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/funzioni/trgfn_attivita_guard_listino_riga)
(`E_ATTIVITA_LISTINO_RIGA_INCOERENTE`, `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO`,
`E_ATTIVITA_LISTINO_VERSIONE_BOZZA`).

---

### Registro della riga: `tipo_movimento`

La commessa e' un **libro giornale**: una riga nata dal push e' un *fatto* — lo specchio della
riga del documento d'origine al momento del push. I fatti non si modificano, si correggono
aggiungendo altri fatti.

Ne discende che righe di natura diversa convivono nella stessa tabella, e serve dire **di che
natura e'** ciascuna. E' il compito di `tipo_movimento`:

| Valore      | Chi la scrive                                      | Cos'e'                                                                                    |
| ----------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `NORMALE`   | il push (default di `fn_upsert_commessa_attivita`) | merce/servizio che rispecchia il documento d'origine                                      |
| `ONERE`     | la porta "aggiungi onere"                          | voce di **valore** senza contratto specifico: quantita' 1 fissa, il prezzo *e'* l'importo |
| `RETTIFICA` | `vendite.fn_accredita_riga_reso`                   | la quota accreditata di un reso: quantita' **negativa** sul segmento della spedizione, e il documento nasce dal giro di fatturazione normale |

**Perche' e' portante.** Il contatore della fatturazione (`tenuti − fatturati`) somma le
quantita' delle sole righe `NORMALE`: e' cosi' che una voce di valore caricata a mano non
finisce per errore nel conto della merce. Il registro viaggia fino ad
[`attivita_fatturabili`](/dbzero/vendite/tabelle/attivita_fatturabili), propagato 1:1
dall'emissione come le 8 colonne dello snapshot pricing — il contatore misura li' e non deve
risalire alla commessa per sapere che natura ha la riga.

**Perche' e' una colonna e non una chiave di `meta`.** Un discriminatore su cui si fondano soldi
e riconciliazioni non puo' dipendere dalla buona educazione del chiamante: in `meta` (jsonb)
lo validerebbe solo la funzione di upsert, e un INSERT diretto lo aggirerebbe. È una colonna con
un CHECK, e il campo `meta` non lo ospita. Nemmeno `tipo_consumo`: le righe scritte quando
esisteva lo portano ancora in `meta`, come fotografia, e nessuno lo legge.

> ⭐ Come l'`ONERE` manuale, la `RETTIFICA` e' **sourceless per progetto**: nessun documento a
> monte, gruppo fatturabile `MAN:<commessa_id>`.

> ⚠️ **Per chi costruisce liste e filtri.** Una colonna, un filtro o una navigazione costruiti
> sulla sorgente della riga sono **vuoti** su queste righe. Accanto alla sorgente si espone sempre
> `tipo_movimento` e, dove serve una risposta mai vuota, il gruppo fatturabile letto dalla sua
> funzione. L'origine vera di una rettifica si risale dal ponte degli accrediti del reso.

> Le righe più vecchie conservano in `meta` una chiave `tipo_movimento` residua: vale sempre
> `NORMALE` e nessuno la legge — la colonna e' l'unica fonte.

**La porta oneri (`ONERE`).** Il registro `ONERE` è la voce di valore manuale (`quantita = 1`,
il prezzo È l'importo) caricata da
[`fn_aggiungi_onere_commessa`](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa): porta una
`causale_onere_id` **obbligatoria** (colonna FK verso
[`config.causali_onere`](/dbzero/config/tabelle/causali_onere), CHECK biconditional
`tipo_movimento='ONERE' ⇔ causale valorizzata`) e **nessuna sorgente documentale**. La causale è
*snapshottata* dall'articolo-onere e l'IVA è quella dell'articolo (ogni onere ha la propria
aliquota).

**L'onere su un articolo ritirato.** Un `ONERE` scelto a mano dalla porta oneri non
nasce su un articolo ritirato alla data operativa, né vi si sposta (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`).
Lo tiene il guard generico
[dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent),
montato su `articolo_id` con `WHEN (tipo_movimento = 'ONERE')` e l'esenzione `sorgente_tipo_id`.
L'esenzione serve perché un `ONERE` arriva anche dal push di ordine e bolla, **con**
la sorgente del documento: quella riga è derivata e passa. `NORMALE` e `RETTIFICA` non si
controllano. Una riga già inserita si modifica: conta solo il cambio di articolo, e l'upsert che
riscrive lo stesso articolo esce subito. Vedi la [guida dell'obsoleto](/guide/uso-di-obsoleto).

### La base del segmento: `segment_base`

`segment_key` è una chiave composta in una stringa: la riga di documento
(`DDT_VENDITA:<uid>:R:<riga>`, `ORDINE_VENDITA:…`: il codice del tipo, l'uid del documento e la riga) più eventuali suffissi — `#CMP:<id>` per un
componente di kit, `#RET:<n>` per una rettifica. `segment_base` è la parte prima
del primo `#`: **la riga di documento a cui l'attività appartiene**, qualunque
suffisso porti.

È una colonna **generata**: si calcola da sola da `segment_key`, nessuno la
scrive. Esiste per una ragione di prestazioni che è una ragione di modello:
«tutte le attività di questa riga» diventa un'uguaglianza su una colonna
indicizzata, che sotto la RLS resta una ricerca per chiave anche quando la riga
arriva come parametro. La usano `fn_af_merce_per_riga` e
`fn_get_stato_push_segment`. ⚠️ Nei trigger `BEFORE` vale ancora `NULL`, come
ogni colonna generata: lo snapshot storico la porta a `null`.

---

### Note di migrazione

* 2026-04-14 — arrivano le colonne dello snapshot pricing del resolver prezzi v5.
* 2026-07-17 — `tipo_movimento` passa da chiave di `meta` a colonna con un CHECK.
* 2026-08-20 — la `RETTIFICA` diventa il verbo di `vendite.fn_accredita_riga_reso`
  (brief-design-note-credito-resi §40.1.2).
* 2026-10-10 — nasce la colonna generata `segment_base`
  (brief-db-segment-base-commesse-attivita).
* 2026-10-13 — la chiave `tipo_consumo` di `meta` si ritira: nessuno la leggeva e il suo
  vocabolario rifiutava il push di contratti e consumi.
* 2026-10-16 — la riga di listino vuole la versione, e il listino dev'essere dell'azienda della
  commessa e non in bozza.
* 2026-11-03 — un `ONERE` arriva anche dal push di ordine e bolla, con la sorgente del documento.
* 2026-11-06 — l'`ONERE` scelto a mano non nasce su un articolo ritirato.
* 2026-11-07 — la provenienza passa al modello: la coppia tipizzata `sorgente_id` /
  `sorgente_uid` (uuid) e `sorgente_riga` prendono il posto della chiave testuale
  `sorgente_uid`, che portava sempre l'uid del documento anche per i tipi a chiave `id` e
  restava fuori dal guard; montati il guard unico `script.trgfn_guard_sorgente` e quello della
  `segment_key` (brief-db-sorgente-documento-e-riga).
* 2026-11-10 — `factor_to_base` perde il `DEFAULT 1`: senza fattore lo legge il trigger alla
  data dell'attività, e senza mappatura la riga è rifiutata (brief-db-revisione-catalogo,
  giro 2-bis).

---

{% include-markdown "signature-core.md" %}
