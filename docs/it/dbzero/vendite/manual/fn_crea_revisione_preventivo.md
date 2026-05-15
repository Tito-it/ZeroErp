## 📘 Documentazione Concettuale – Funzione `vendite.fn_crea_revisione_preventivo(...)`

> 👀 **Vedi anche**
>
[vendite.preventivi](/dbzero/vendite/tabelle/preventivi)
> [vendite.preventivi_righe](/dbzero/vendite/tabelle/preventivi_righe)
> [vendite.preventivi_righe_componenti](/dbzero/vendite/tabelle/preventivi_righe_componenti)
> [vendite.preventivi_indirizzi](/dbzero/vendite/tabelle/preventivi_indirizzi)
> [vendite.vw_preventivi](/dbzero/vendite/views/vw_preventivi)
> [vendite.fn_ricalcola_totali_preventivo](/dbzero/vendite/funzioni/fn_ricalcola_totali_preventivo)

---
### 🎯 Scopo Principale
(latest review 15-05-2026)
`vendite.fn_crea_revisione_preventivo(p_preventivo_id, p_user)` crea una **nuova revisione**
di un preventivo vendita: copia testata, righe attive, componenti BoM e indirizzi.
L'attivazione della revisione non e' piu' gestita qui: il flag `is_revision_attiva` e' stato
rimosso dalla tabella e sostituito dalla colonna derivata `is_attiva` in `vendite.vw_preventivi`.

> ⚠️ **Cambio di regola 03-05-2026**: la revisione e' ora ammessa **solo** da preventivi
> in stato `EMESSO`. Lo stato `ACCETTATO` chiude la negoziazione (preventivo confermato
> dal cliente, push commessa abilitata): per modifiche post-accettazione si crea un
> **nuovo preventivo**, non si revisiona quello esistente.
> Permettere la revisione da `ACCETTATO` creava ambiguita' col flusso "ACCETTATO -> push
> commessa": una commessa poteva essere gia' pushata e poi il preventivo rivisitato.
> Allineato anche `script.fn_available_actions_preventivo` (`can_create_revisione`
> = true solo per `EMESSO`).

---

### Regole principali

* **Stato ammesso**: solo preventivi in stato `EMESSO` (era `EMESSO` o `ACCETTATO`
  prima del 03-05-2026).
* **No DRAFT esistente**: non deve esistere gia' una revisione in DRAFT per lo stesso numero.
* **Guard stato DRAFT**: se lo stato DRAFT non e' configurato/attivo in `config.stati_doc_preventivi`,
  errore esplicito `E_CONFIG_MANCANTE` (non fallisce con FK generico).
* La nuova revisione ha `rev = max(rev) + 1`, stato DRAFT.
* **Attivazione derivata**: non viene piu' aggiornato alcun flag sul predecessore.
  `is_attiva` e' calcolata dinamicamente in `vendite.vw_preventivi` — la nuova rev
  DRAFT (non-abortita) rende automaticamente non-attiva la rev precedente.
* **Righe copiate**: solo attive con `quantita > 0`, `ORDER BY ordine, id`
  (ordinamento deterministico necessario per il remap FK componenti).
* **Componenti BoM copiati** (15-05-2026): le righe `preventivi_righe_componenti`
  vengono copiate con FK remap `old_riga_id → new_riga_id` tramite
  `ROW_NUMBER() OVER (ORDER BY ordine, id)`. Solo componenti con `attivo IS TRUE`.
  Il trigger `trgfn_componenti_calcola_quantita` (BEFORE INSERT) ricalcola
  `quantita` e `qta_operativa` da `coeff_qta_snapshot`.
* **Indirizzi**: tutti copiati.

---

### Ottimizzazioni

* **Totali a 0**: la nuova testata viene creata con `totale_imponibile = 0, totale_iva = 0,
  totale_documento = 0`. I totali corretti vengono ricalcolati automaticamente dal trigger
  STATEMENT su `preventivi_righe` dopo l'INSERT bulk delle righe copiate.
  Questo evita di copiare totali che verrebbero immediatamente sovrascritti.

---

### Parametri

| Parametro | Tipo | Note |
|-----------|------|------|
| `p_preventivo_id` | `vendite.preventivi.id%TYPE` | ID del preventivo da revisionare. Obbligatorio, > 0. |
| `p_user` | `vendite.preventivi.user_update%TYPE` | Utente che esegue l'operazione. |

---

### 📦 Output

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `nuovo_preventivo_id` | bigint | ID della nuova revisione |
| `numero` | varchar | Numero del preventivo (invariato) |
| `nuova_rev` | integer | Numero di revisione assegnato |

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `PREV_REVISIONE_STATO_NON_AMMESSO` | Stato corrente diverso da `EMESSO` (rev 03-05-2026: `ACCETTATO` non piu' ammesso) |
| `PREV_REVISIONE_BOZZA_ESISTENTE` | Esiste gia' una revisione DRAFT per lo stesso numero |
| `PREV_STATO_CORRENTE_NON_TROVATO` | Preventivo non trovato |
| `E_CONFIG_MANCANTE` | Stato DRAFT non configurato/attivo in config.stati_doc_preventivi |
| `E_PARAMETRO_INVALIDO` | p_preventivo_id NULL o <= 0 |

---

### Esempio d'uso

```sql
-- Crea revisione di un preventivo emesso
SELECT * FROM vendite.fn_crea_revisione_preventivo(42, 'operatore1');
-- Restituisce: nuovo_preventivo_id=99, numero='PREV-2026-001', nuova_rev=2
```

---

{% include-markdown "signature-core.md" %}
