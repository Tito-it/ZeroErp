## 📘 Documentazione Concettuale – Tabella `vendite.commesse_attivita`

> 👀 **Vedi anche**
>
**Approfondimento tabelle:**
>
• [vendite.commesse](/dbzero/vendite/tabelle/commesse)  
> • [vendite.attivita_fatturabili](/dbzero/vendite/tabelle/attivita_fatturabili)  
> • [vendite.listini_versioni](/dbzero/vendite/tabelle/listini_versioni)  
>
### 🎯 Scopo Principale
La tabella `vendite.commesse_attivita` e` la sorgente di verita` operativa delle righe
da emettere verso `attivita_fatturabili`.

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

### ⚠️ `sorgente_uid` qui NON è la chiave canonica polimorfa

Trappola verificata il 27-07-2026. La coppia `(sorgente_tipo_id, sorgente_uid)`
su questa tabella **assomiglia** all'aggancio polimorfo di
[`commesse_sorgenti`](commesse_sorgenti.md) e di `pratiche_sorgenti`, ma
**non segue la stessa convenzione**.

| Tabella | Cosa contiene `sorgente_uid` | Chi lo garantisce |
|---|---|---|
| `commesse_sorgenti` | chiave **canonica** secondo `config.sorgenti.key_selector` (`id::text` per ordini/contratti/DDT, `uid::text` per preventivi/offerte) | `fn_link_commessa_sorgente`, che **normalizza in scrittura** |
| **`commesse_attivita`** | **l'`uid` del documento, sempre** — per tutte le sorgenti, anche quelle con `key_selector = 'id'` | **nessuno**: `fn_upsert_commessa_attivita` scrive il valore ricevuto senza tradurlo |

**Perché**: tutte le `fn_list_<sorgente>_da_pushare` proiettano
`<tabella>.uid::text`. Quel valore viene scritto qui **grezzo**, mentre
`fn_link_commessa_sorgente` lo traduce prima di scriverlo su
`commesse_sorgenti`. Le due tabelle vengono popolate nello stesso push e per lo
stesso documento contengono **valori diversi**.

**Non è un errore da bonificare**: è una convenzione autonoma, già usata da
consumatori vivi — es. `vw_dash_fatturazione_contratti` fa
`JOIN ... AND ca.sorgente_uid = c.uid::text`. Normalizzare questa colonna
romperebbe quei join.

**Regola pratica per chi scrive query**:

* per interrogare **`commesse_attivita`** → usa **l'uid** del documento;
* per interrogare **`commesse_sorgenti`** → usa la **chiave canonica**
  (risolvila da `config.sorgenti.key_selector`, non darla per scontata);
* **non dedurre l'una dall'altra per analogia**: la somiglianza dei nomi di
  colonna è precisamente ciò che induce l'errore.

Il meccanismo polimorfo e il suo perimetro sono descritti in
[guida sorgente polimorfa](/guide/sorgente-polimorfa): questa tabella sta
**fuori** da quel perimetro (nessun guard `trgfn_guard_sorgente_polimorfa_*`
agganciato).

---

### Utilizzo previsto

* input del pull `fn_emit_attivita_fatturabili_da_commessa`;
* supporto idempotenza e replay controllato;
* separazione netta owner business (commessa) vs layer esecutivo (AF).

---

### Snapshot pricing (v5, 14-04-2026)

All'esecuzione del resolver prezzi v5, l'attivita' in commessa riceve uno snapshot strutturato delle dimensioni di calcolo. Colonne nullable, valorizzate insieme a `prezzo_snapshot`/`prezzo_bloccato` esistenti:

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

### Riga di listino e versione: coerenti (15-10-2026)

La riga porta la **versione** del listino sotto cui è registrata (`listino_versione_id`) e la
**riga di listino** da cui viene il prezzo (`listino_riga_id`). Le due non possono dire cose
diverse: la riga di listino deve essere dello stesso articolo e della stessa unità di misura
della riga di commessa e, se la versione c'è, di quella versione. La versione senza riga di
listino è lecita (il push la scrive così); la riga di listino senza versione no
(`chk_commesse_attivita_listino_riga_con_versione`, dal 16-10-2026). Dal 16-10-2026 il listino
dev'essere **dell'azienda della commessa** e la versione **non in bozza**: mai un prezzo da una
bozza. Lo tiene
[vendite.trgfn_attivita_guard_listino_riga](/dbzero/vendite/manual/trgfn_attivita_guard_listino_riga)
(`E_ATTIVITA_LISTINO_RIGA_INCOERENTE`, `E_ATTIVITA_LISTINO_EMITTENTE_DIVERSO`,
`E_ATTIVITA_LISTINO_VERSIONE_BOZZA`), decisioni di Tid.

---

### Registro della riga: `tipo_movimento` (17-07-2026)

La commessa e' un **libro giornale**: una riga nata dal push e' un *fatto* — lo specchio della
riga del documento d'origine al momento del push. I fatti non si modificano, si correggono
aggiungendo altri fatti.

Ne discende che righe di natura diversa convivono nella stessa tabella, e serve dire **di che
natura e'** ciascuna. E' il compito di `tipo_movimento`:

| Valore      | Chi la scrive                                      | Cos'e'                                                                                    |
| ----------- | -------------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `NORMALE`   | il push (default di `fn_upsert_commessa_attivita`) | merce/servizio che rispecchia il documento d'origine                                      |
| `ONERE`     | la porta "aggiungi onere"                          | voce di **valore** senza contratto specifico: quantita' 1 fissa, il prezzo *e'* l'importo |
| `RETTIFICA` | `vendite.fn_accredita_riga_reso` (dal 18-08-2026)  | la quota accreditata di un reso: quantita' **negativa** sul segmento della spedizione, e il documento nasce dal giro di fatturazione normale |

**Perche' e' portante.** Il contatore della fatturazione (`tenuti − fatturati`) somma le
quantita' delle sole righe `NORMALE`: e' cosi' che una voce di valore caricata a mano non
finisce per errore nel conto della merce. Il registro viaggia fino ad
[`attivita_fatturabili`](/dbzero/vendite/tabelle/attivita_fatturabili), propagato 1:1
dall'emissione come le 8 colonne dello snapshot pricing — il contatore misura li' e non deve
risalire alla commessa per sapere che natura ha la riga.

**Perche' e' una colonna e non una chiave di `meta`.** Fino al 17-07-2026 il valore viveva nel
campo `meta` (jsonb), validato solo dalla funzione di upsert: un INSERT diretto lo aggirava, e
un discriminatore su cui si fondano soldi e riconciliazioni non puo' dipendere dalla buona
educazione del chiamante. Ora e' una colonna con un CHECK, e il campo `meta` non lo ospita
piu'. Nemmeno `tipo_consumo`, che ci stava accanto: è ritirato dal 2026-10-13 (`20261013-16`),
perché nessuno lo leggeva e il suo vocabolario rifiutava il push di contratti e consumi. Le righe
scritte prima lo portano ancora in `meta`, come fotografia.

> ⚠️ **La riga `RETTIFICA` diceva «nessuno, oggi» fino al 20-08-2026**, ed era
> vero quando fu scritta: il cantiere nota di credito l'ha resa il verbo di
> `fn_accredita_riga_reso`. ⭐ E come l'`ONERE`, la rettifica e' **sourceless per
> progetto** — nessun documento a monte, gruppo fatturabile `MAN:<commessa_id>`.
> Vedi `brief-design-note-credito-resi` §40.1.2.

> Le righe scritte prima di questa data conservano in `meta` una chiave `tipo_movimento`
> residua: vale sempre `NORMALE` (verificato all'applicazione della migrazione) e nessuno la
> legge — la colonna e' l'unica fonte.

**La porta oneri (`ONERE`).** Il registro `ONERE` è la voce di valore manuale (`quantita = 1`,
il prezzo È l'importo) caricata da
[`fn_aggiungi_onere_commessa`](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa): porta una
`causale_onere_id` **obbligatoria** (colonna FK verso
[`config.causali_onere`](/dbzero/config/tabelle/causali_onere), CHECK biconditional
`tipo_movimento='ONERE' ⇔ causale valorizzata`) e **nessuna sorgente documentale**. La causale è
*snapshottata* dall'articolo-onere e l'IVA è quella dell'articolo (ogni onere ha la propria
aliquota).

Riferimento: `brief-db-immutabilita-quantita-e-porta-oneri` §4c.2 e §4c.3.

**L'onere su un articolo ritirato (06-11-2026).** Un `ONERE` scelto a mano dalla porta oneri non
nasce su un articolo ritirato alla data operativa, né vi si sposta (`E_CATALOGO_OBSOLETO_NUOVA_ISTANZA`).
Lo tiene il guard generico
[dbops.trgfn_child_requires_non_obsolete_parent](/dbzero/dbops/funzioni/trgfn_child_requires_non_obsolete_parent),
montato su `articolo_id` con `WHEN (tipo_movimento = 'ONERE')` e l'esenzione `sorgente_tipo_id`
(`20261106-02`). L'esenzione serve perché dal 03-11-2026 un `ONERE` arriva anche dal push di ordine e bolla, **con**
la sorgente del documento: quella riga è derivata e passa. `NORMALE` e `RETTIFICA` non si
controllano. Una riga già inserita si modifica: conta solo il cambio di articolo, e l'upsert che
riscrive lo stesso articolo esce subito. Vedi la [guida dell'obsoleto](/guide/uso-di-obsoleto).

### La base del segmento: `segment_base` (10-10-2026)

`segment_key` è una chiave composta in una stringa: la riga di documento
(`DDT:<uid>:R:<riga>`, `ORD:…`) più eventuali suffissi — `#CMP:<id>` per un
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
Brief: `brief-db-segment-base-commesse-attivita`.

---

{% include-markdown "signature-core.md" %}
