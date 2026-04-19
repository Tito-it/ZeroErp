## 📘 Documentazione Concettuale – Resolver Pricing `vendite.fn_resolve_prezzo_listino_v2`

> 👀 **Vedi anche**
>
> **Funzione corrente**: [`vendite.fn_resolve_prezzo_listino_v2`](/it/dbzero/vendite/funzioni/fn_resolve_prezzo_listino_v2)
> **Funzione deprecata (v1)**: il vecchio `fn_resolve_prezzo_listino` e la tabella `listini_associazioni` sono stati rimossi in F2-BE-13 (pricing v5). Se trovi riferimenti, sono legacy.
>
> **Approfondimento tabelle**:
> • [vendite.listini](/it/dbzero/vendite/tabelle/listini)
> • [vendite.listini_versioni](/it/dbzero/vendite/tabelle/listini_versioni)
> • [vendite.listini_righe](/it/dbzero/vendite/tabelle/listini_righe)
> • [vendite.contratti](/it/dbzero/vendite/tabelle/contratti)
> • [vendite.contratti_righe](/it/dbzero/vendite/tabelle/contratti_righe)
> • [vendite.promo_articoli](/it/dbzero/vendite/tabelle/promo_articoli)
> • [anagrafiche.categorie_clienti_listini](/it/dbzero/anagrafiche/tabelle/categorie_clienti_listini)

### 🎯 Scopo principale

Risolve in modo deterministico il prezzo applicabile per una coppia
`(articolo, uom)` in una data, dato un billing account. Unica funzione usata da
preventivi, commesse e fatturazione: zero logica duplicata applicativa.

---

### 🔑 Dimensioni di input

| Parametro | Tipo | Obbligatorio | Origine suggerita |
| --- | --- | --- | --- |
| `p_articolo_id` | uuid | sì | identifica l'articolo |
| `p_uom_id` | bigint | sì | UoM operativa (filtrata per articolo) |
| `p_data_riferimento` | date | sì | data alla quale valutare contratto/listino/promo |
| `p_ba_id` | bigint | sì | billing account (determina categoria e partecipa_promo) |
| `p_utility_id` | integer | sì | utility del servizio |
| `p_emittente_soggetto_ruolo_id` | bigint | sì | emittente fiscale (derivato dal JWT operatore) |
| `p_classe_utenza_id` | integer | no | classe utenza del PDP (raffina match matrice categoria) |

**Dimensioni derivate (mai input):**

- **Categoria cliente**: da `contratti.categoria_cliente_id_snapshot` se esiste contratto attivo, altrimenti da `billing_account.categoria_cliente_id`.
- **Partecipazione a promo**: da `categorie_clienti.partecipa_promo` (derivato dal BA).
- **Tipologia listino**: dimensione interna del listino, matchata a STADIO 2 tramite matrice; non input.

---

### 🪜 Stadi del resolver (ordine deterministico)

**STADIO 1 — CONTRATTO** (se esiste contratto ATTIVO per `(ba, utility, data)`):

1. **`CONTRATTO_OVERRIDE`** — se `contratti_righe.prezzo_unitario` specifico per l'articolo è valorizzato → usato direttamente, nessuna variazione.
2. **`CONTRATTO_LISTINO`** — altrimenti prende la riga del listino del contratto (`contratti.listino_id` + versione valida alla data + riga su articolo+uom). Se il contratto ha `tipo_variazione_globale` applica la formula (`PERCENTUALE` / `VALORE_FISSO`) sul prezzo base.
3. Se nessun listino su contratto C (precontrattuale) → errore `E_ARTICOLO_NON_NEGOZIATO_SU_CONTRATTO_C`.

**STADIO 2 — CATEGORIA** (solo se non c'è contratto attivo):

1. Lookup su `anagrafiche.categorie_clienti_listini` filtrando per:
   - `categoria_cliente_id` (da BA)
   - `utility_id`, `emittente_soggetto_ruolo_id`, validita alla data
   - `classe_utenza_id` specifico (se fornito) OR NULL fallback (priorita al match specifico)
2. Estrae `listino_id` + eventuale `tipo_variazione` matrice, poi la riga listino attiva per `(articolo, uom, data)`.
3. Errori possibili: `E_CATEGORIA_LISTINO_NON_MAPPATA`, `E_PREZZO_LISTINO_RIGA_NON_TROVATA`, `E_PREZZO_LISTINO_NON_TROVATO` (BA senza categoria e senza contratto).

**STADIO 0 — PROMO** (overlay finale, sempre ultimo):

Se la categoria del cliente ha `partecipa_promo = TRUE` e esiste una `vendite.promo_articoli` attiva per `(articolo, uom)` alla data → sostituisce il risultato degli stadi precedenti applicando `tipo_variazione` (`PERCENTUALE` / `VALORE_FISSO` / `PREZZO_FISSO`).

---

### 📤 Output

Ritorna una singola riga con:

- `prezzo_finale`, `prezzo_base_snapshot`
- `tipo_variazione_applicata`, `valore_variazione_applicata`
- `origine` (`CONTRATTO_OVERRIDE` | `CONTRATTO_LISTINO` | `CATEGORIA` | `PROMO`)
- FK della catena: `listino_id`, `listino_versione_id`, `listino_riga_id`, `contratto_id`, `promo_id`, `categoria_cliente_listino_id`
- Snapshot: `categoria_cliente_id_snapshot`, `classe_utenza_id_snapshot`

---

### 🧭 Domande aperte sul modello

Il modello `vendite.contratti_utilities` contiene `tipo_utenza_id` e `classe_utenza_id`
(per contratto). Attualmente:

- **`classe_utenza_id`**: passata al resolver come **input** del caller, non letta dal contratto. Incoerenza potenziale se il contratto la dichiara diversa.
- **`tipo_utenza_id`**: **non usata** dal resolver. La matrice `categorie_clienti_listini` non ha la colonna corrispondente.

Se il modello pricing dovesse considerare tipo/classe utenza in modo coerente col contratto, servono cambi DB + migrazione dati. Decisione di architettura, non bug.

---

{% include-markdown "signature-core.md" %}
