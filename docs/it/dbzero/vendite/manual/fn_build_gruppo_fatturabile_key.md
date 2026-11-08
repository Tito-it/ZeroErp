## 📘 Documentazione Concettuale – Funzione `vendite.fn_build_gruppo_fatturabile_key`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — le righe che si raggruppano
> * [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi) — dove la chiave resta salvata
>
> Approfondimento viste:
>
> * [vendite.vw_dash_competenza_attivita](/dbzero/vendite/views/vw_dash_competenza_attivita) — la chiave riga per riga
> * [vendite.vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi) — l'elenco dei gruppi che l'operatore legge
>
> Approfondimento funzioni:
>
> * [vendite.fn_gruppo_fatturabile_key_di_attivita](/dbzero/vendite/funzioni/fn_gruppo_fatturabile_key_di_attivita) — la chiave di una riga di commessa, che chiama questa funzione
> * [vendite.fn_documento_uid_di_attivita](/dbzero/vendite/funzioni/fn_documento_uid_di_attivita) — l'uid del documento, dalla chiave del push
> * [vendite.fn_split_gruppo_fatturabile_key](/dbzero/vendite/funzioni/fn_split_gruppo_fatturabile_key) — il verso inverso
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — l'emissione mirata per gruppo
> * [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili) — la selezione delle attività per gruppo
>
> Guide:
>
> * [Sorgente polimorfa](/guide/sorgente-polimorfa) — il modello della provenienza e le chiavi in testo
> * [Fatturazione](/guide/fatturazione) — il giro di fatturazione

---

### 🎯 Scopo Principale

Costruire la chiave del **gruppo fatturabile** di una riga di commessa. È
l'**unica fonte di verità** della chiave: la usano sia l'elenco che l'operatore
legge, sia i filtri che l'emissione applica. Se la forma cambiasse qui,
cambierebbe ovunque insieme.

---

### Cos'è un gruppo fatturabile

L'unità su cui l'operatore decide «questo lo fatturo adesso». Non è la commessa
e non è sempre un documento:

- **non la commessa**, perché è multi-sorgente: contiene il preventivo, il
  contratto e gli oneri dello stesso cliente. Selezionarla non isola nulla;
- **non sempre un documento**, perché le righe della porta oneri sono
  **sourceless per progetto**: un documento non ce l'hanno.

Da qui le due forme:

| Riga | Chiave | Esempio |
|---|---|---|
| con documento sorgente | `<codice_interno_sorgente>:<sorgente_uid>` | `PREVENTIVO:9f3a-4b1c-…` |
| sourceless (oneri) | `MAN:<commessa_id>` | `MAN:42` |

Gli oneri di una commessa sono **un gruppo solo**, non uno per riga: il loro
unico contenitore naturale è la commessa.

> **Perché la seconda forma non è un ripiego.** Raggruppando solo per documento,
> le righe onere — che *sono* conteggiate nel numero della card «Da emettere» —
> non comparirebbero in nessun gruppo e nessuna azione mirata le
> raggiungerebbe: lavoro invisibile e non azionabile, recuperabile solo dal giro
> schedulato.

---

### ⚠️ L'identificativo è l'`uid`, anche per i tipi a chiave `id`

La chiave nomina il documento con il suo **uid**, per ogni tipo: anche per ordine, contratto e
DDT, che la provenienza del modello riconosce dall'`id`. Non segue il `key_selector`, e non va
«allineata»: la chiave è **salvata** nei lotti (`fatturazione_lotti_gruppi`, gli esiti, il log),
e cambiarne la forma vorrebbe dire riscrivere i lotti già passati. È una delle chiavi che sono
testo per costruzione: chi la deve risolvere usa `script.fn_sorgente_documento_da_chiave`
([guida sorgente polimorfa §5](/guide/sorgente-polimorfa)).

**Da dove viene l'uid.** Per una riga di commessa la provenienza tiene l'`id` dei tipi a chiave
`id`, quindi l'uid non si legge dalle colonne della provenienza: lo porta la chiave del push,
`segment_key` (`<CODICE>:<uid>…`). Lo estrae `vendite.fn_documento_uid_di_attivita`, e la chiave
di una riga la costruisce `vendite.fn_gruppo_fatturabile_key_di_attivita`, che chiama questa
funzione. Che la `segment_key` nomini proprio il documento della provenienza lo verifica, alla
scrittura della riga, `vendite.trgfn_commesse_attivita_guard_sorgente_segment`.

---

### Regole principali

- **prefisso da `codice_interno`**, mai da `codice`: il primo è immutabile, il
  secondo è un'etichetta modificabile dall'utente (linee-guida-sql §6c/§6d);
- **nessun filtro su `attivo`** nella lookup della sorgente: una riga nata da
  una sorgente poi disattivata appartiene comunque al suo gruppo e deve restare
  fatturabile;
- **`STABLE`**: legge `config.sorgenti`, non scrive. Non `IMMUTABLE` proprio per
  quella lookup;
- **guard fail-loud**, mai chiavi inventate:

| Caso | Esito |
|---|---|
| `p_sorgente_tipo_id <= 0` o `p_commessa_id <= 0` | `E_PARAMETRO_INVALIDO` |
| riga sourceless senza commessa | `E_PARAMETRO_INVALIDO` (la commessa è il suo unico contenitore) |
| tipo senza uid, o uid senza tipo | `E_PARAMETRO_INVALIDO` |
| `sorgente_tipo_id` inesistente in `config.sorgenti` | `E_CODICE` |

La coppia incoerente non accade per una riga di commessa — la forma la tiene
`chk_commesse_attivita_sorgente_forma`, e il guard della `segment_key` verifica che la chiave porti
l'uid del documento — ma la funzione è chiamabile con valori arbitrari: meglio rumore che una
chiave che poi non risolve in silenzio.

---

### ⚠️ Dalla `segment_key` si legge solo l'uid

`segment_key` è `ORDINE_VENDITA:<uid>:R:<n>`, `CONTRATTO:<uid>:R:<n>:M:…`, `MAN:<commessa>:<n>`…
Il prefisso è il codice del tipo, e il guard della `segment_key` lo verifica, ma il prefisso della
chiave del gruppo viene sempre da `config.sorgenti.codice_interno` del tipo della riga, letto dal
catalogo. Della `segment_key` si usa solo l'uid del documento, con il BB che lo estrae.

---

### Chi la usa

Per una riga di commessa la chiamano tutti attraverso `vendite.fn_gruppo_fatturabile_key_di_attivita`:

| Consumatore | A cosa serve |
|---|---|
| `vw_dash_competenza_attivita` (colonna `gruppo_key`) | espone la chiave riga per riga |
| `vw_dash_competenza_gruppi` | aggrega su di essa: è l'elenco che l'operatore legge |
| `vw_commesse_attivita_emittibilita` e `fn_emit_attivita_fatturabili_da_commessa` | filtrano le righe da emettere |
| `fn_select_attivita_fatturabili` | filtra le attività fatturabili già esistenti |
| `fn_list_emittibili_lane` · `fn_list_commesse_emittibili` | restringono la discovery |
| `vw_lotti_gruppi_serviti`, `vw_lotto_documento_righe`, `fn_esito_gruppi_giro` | leggono i gruppi di un lotto |

Poiché elenco e filtri chiamano **la stessa funzione**, ciò che l'operatore vede
è esattamente ciò che l'emissione accetta: il frontend passa la stringa che
legge, senza mappature.

---

### Note di migrazione

* 2026-07-27 — nasce la funzione, con la chiave sull'uid del documento
  (brief-db-emissione-fattura-per-documento-sorgente, parte A, D-1 e D-9).
* 2026-11-07 — la riga di commessa passa alla provenienza del modello, e la chiave testuale
  `sorgente_uid`, che portava l'uid per ogni tipo, non c'è più: l'uid lo legge dalla
  `segment_key` `vendite.fn_documento_uid_di_attivita`, e la chiave di una riga la costruisce
  `vendite.fn_gruppo_fatturabile_key_di_attivita`. La forma della chiave non cambia
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
