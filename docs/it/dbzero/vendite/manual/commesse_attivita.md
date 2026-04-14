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

{% include-markdown "signature-core.md" %}
