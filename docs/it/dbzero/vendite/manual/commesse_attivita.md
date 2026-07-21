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
| `contratto_id`                   | bigint        | FK a `vendite.contratti`; valorizzato se `origine_prezzo CONTRATTO_*`                             |
| `categoria_cliente_id_snapshot`  | smallint      | FK a `anagrafiche.categorie_clienti`; congela la categoria al momento del calcolo                 |
| `classe_utenza_id_snapshot`      | integer       | FK a `config.classi_utenze`; congela la classe utenza al momento del calcolo                      |

Due CHECK presidiano il dominio di `origine_prezzo` e `tipo_variazione_applicata`. Il campo `meta` resta per dettagli non strutturati (es. deroghe, flag specifici): qui stanno solo le dimensioni che servono per query dirette e filtri dashboard.

Le stesse 8 colonne vengono propagate su [`vendite.attivita_fatturabili`](/dbzero/vendite/tabelle/attivita_fatturabili), preservando la tracciabilita' fino al layer fatture.

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
| `RETTIFICA` | nessuno, oggi                                      | riservato ai conguagli/rettifiche futuri (il dominio lo prevede gia')                     |

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
piu'. Su `meta` resta `tipo_consumo` (`ACCONTO` | `CONGUAGLIO` | `STORNO`), non promosso.

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

---

{% include-markdown "signature-core.md" %}
