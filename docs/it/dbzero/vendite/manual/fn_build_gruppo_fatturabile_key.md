## Documentazione Concettuale – Funzione `vendite.fn_build_gruppo_fatturabile_key(...)`

> **Versione**: 2026-07-27 (brief-db-emissione-fattura-per-documento-sorgente
> PARTE A step A1, decisioni D-1 e D-9 · migration `20260727-10`)

> **Vedi anche**
>
[vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita)
> [vendite.fatturazione_lotti_gruppi](/dbzero/vendite/tabelle/fatturazione_lotti_gruppi)
> [vendite.vw_dash_competenza_gruppi](/dbzero/vendite/views/vw_dash_competenza_gruppi)
> [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa)
> [vendite.fn_select_attivita_fatturabili](/dbzero/vendite/funzioni/fn_select_attivita_fatturabili)
>
**Guide**: [sorgente polimorfa](/guide/sorgente-polimorfa) · [fatturazione](/guide/fatturazione)

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

### ⚠️ L'identificativo è l'`uid`, non l'`id` — e non va «corretto»

La funzione legge quello che sta in `vendite.commesse_attivita.sorgente_uid`,
che contiene **`<tabella>.uid::text` per tutte le sorgenti** — anche quelle con
`config.sorgenti.key_selector = 'id'`.

**Non allinearla a `commesse_sorgenti`**, che per lo stesso documento contiene
un valore **diverso** (`id::text` per ordini, contratti, DDT) perché
`fn_link_commessa_sorgente` normalizza in scrittura. Le due tabelle sono
popolate dallo stesso push e hanno colonne omonime: è precisamente la
somiglianza che induce l'errore.

Le tre ragioni della scelta (decisione **D-9**):

1. **la chiave non esce mai dal perimetro di `commesse_attivita`** — la produce
   `vw_dash_competenza_gruppi` e la consumano i filtri `p_gruppi`, che leggono
   tutti quella tabella: non deve combaciare con `commesse_sorgenti`, non si
   incontrano mai;
2. **normalizzare romperebbe le dashboard**: `vw_dash_fatturazione_contratti` fa
   già `ca.sorgente_uid = c.uid::text`;
3. **il riferimento leggibile si aggancia direttamente all'uid**:
   `vw_dash_fatturazione_documenti.documento_uid` è l'uid, quindi il join è
   un'uguaglianza diretta.

Dettaglio del meccanismo e delle tabelle che stanno **fuori** da esso:
[guida sorgente polimorfa §4a](/guide/sorgente-polimorfa).

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
| coppia sorgente incoerente (uno solo dei due valorizzato) | `E_PARAMETRO_INVALIDO` |
| `sorgente_tipo_id` inesistente in `config.sorgenti` | `E_CODICE` |

La coppia incoerente non dovrebbe verificarsi — lo impedisce
`chk_commesse_attivita_sorgente_pair` — ma la funzione è chiamabile con valori
arbitrari: meglio rumore che una chiave che poi non risolve in silenzio.

---

### ⚠️ Non derivare la chiave da `segment_key`

`segment_key` è `ORD:<uid>:R:<n>`, `MAN:<commessa>:<n>`,
`CONTR:<uid>:R:<n>:M:<YYYY-MM>`… I prefissi lì sono una convenzione di
**leggibilità per-sorgente**, non un contratto: ricavarne il gruppo con
`split_part` creerebbe un accoppiamento a una regola di formattazione che
nessuno si è impegnato a mantenere.

---

### Chi la usa

| Consumatore | A cosa serve |
|---|---|
| `vw_dash_competenza_attivita` (colonna `gruppo_key`) | espone la chiave riga per riga |
| `vw_dash_competenza_gruppi` | aggrega su di essa: è l'elenco che l'operatore legge |
| `fn_emit_attivita_fatturabili_da_commessa` | filtra le righe da emettere |
| `fn_select_attivita_fatturabili` | filtra le attività fatturabili già esistenti |
| `fn_list_emittibili_lane` · `fn_list_commesse_emittibili` | restringono la discovery |

Poiché elenco e filtri chiamano **la stessa funzione**, ciò che l'operatore vede
è esattamente ciò che l'emissione accetta: il frontend passa la stringa che
legge, senza mappature.

---

{% include-markdown "signature-core.md" %}
