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
(latest review 14-09-2026)
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
  ⚠️ **La copia ha un elenco ESPLICITO di colonne**: una colonna nuova sulla
  riga **non passa** finché qualcuno non la nomina qui. È il punto in cui una
  colonna si perde senza errore — successo con la data di consegna.
* **`data_consegna_richiesta_cliente` copiata** (rev 2026-09-14, `20260914-13`):
  la data che il cliente ha chiesto è un **input della controparte**, non una
  promessa nostra da rinegoziare — la rev N+1 la eredita come eredita
  articolo e quantità, e chi vuole cambiarla la cambia sulla riga. ⚠️ Fino a
  quel giorno la revisione nasceva con la data a `NULL`: P-5 del brief
  (`20260913-20`) aveva coperto il passaggio preventivo→ordine, non
  rev N→N+1, e nessun pgTAP lo pinnava (segnalazione del BE). Presidio:
  `db/pgtap/vendite/test-date-consegna-ordine-v1.sql`, test 11-13 (fixture
  costruita: misura la stessa cosa su dbdev e in CI).
* **Marche di approvazione prezzo copiate 1:1** (rev 2026-09-14, `20260914-14`,
  decisione di Tid): `stato_approvazione_prezzo` e
  `pratica_approvazione_prezzo_id` passano sulla riga della rev N+1 come già
  sui **componenti** di questa funzione e come in
  [fn_crea_revisione_offerta](/dbzero/vendite/funzioni/fn_crea_revisione_offerta)
  (rev2 2026-06-01). La ragione è la stessa: i gate L3 scattano sull'**edit**,
  non alla revisione, quindi lo stato è l'unico marcatore persistente che un
  prezzo fuori policy è autorizzato o in attesa — azzerarlo faceva nascere la
  rev N+1 con lo stesso prezzo e **senza marca** (com'era dal 2026-04-22:
  colonne arrivate dopo la funzione, nominate dal rewrite del 15-05 solo per i
  componenti). Una riga `PENDING` copiata resta congelata da
  [trgfn_righe_guard_pending](/dbzero/script/funzioni/trgfn_righe_guard_pending).
  ⚠️ **Caveat, lo stesso dell'offerta e non deciso qui**: la pratica resta
  agganciata per id a **entrambe** le righe (rev N e N+1) e il suo `meta`
  nomina la riga della rev N — chi approva dalla coda agisce su quella. Il
  ciclo di vita della pratica su una revisione superata è del dominio
  approvazioni (BE): `refactor-prezzi.md` §4.7.
* **Colonne di riga che NON si copiano, e perché** — ⭐ **elenco presidiato**
  da `db/pgtap/vendite/test-fn-crea-revisione-preventivo-riga-completa-v1.sql`
  (test 1-2): ogni colonna di `preventivi_righe` deve essere o nominata nella
  copia o dichiarata esclusa lì con la ragione, altrimenti il test è rosso —
  la prossima colonna di riga non può più perdersi in silenzio.
  `natura_vendita_id` — la deriva e la **congela** dall'articolo il trigger
  `BEFORE INSERT` (`trgfn_preventivi_righe_set_natura_vendita`): nominarla
  scriverebbe un valore che viene sovrascritto; `tx_id` — framework;
  `id`, `data_insert`, `data_update` — identity e audit.
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

⚠️ La firma e la `RETURNS TABLE` sono ancorate con `%TYPE` **negli ultimi
changeSet** (`20260914-13` e `-14`, com'erano in `20260515-04` e `20260628-21`):
`20260805-25` le aveva ricopiate sciolte dal corpo vivo, che risolve i `%TYPE`
al `CREATE`. L'identità della funzione non cambia (`bigint, text`). La funzione
è dichiarata `SECURITY INVOKER` esplicito: madre a più scritture, gira come
l'operatore che la chiama (RLS e scope emittente restano i suoi).

---

### 📦 Output

| Campo | Tipo | Descrizione |
|-------|------|-------------|
| `nuovo_preventivo_id` | bigint | ID della nuova revisione |
| `numero` | varchar | Numero del preventivo (invariato) |
| `nuova_rev` | integer | Numero di revisione assegnato |

---

### Codici errore

(prefisso `E_` dal `20260805-25`; i nomi senza prefisso restano a catalogo
ritirati con `obsoleto_dal` — fino al 14-09-2026 questa tabella li citava ancora)

| Codice | Quando |
| --- | --- |
| `E_PREV_REVISIONE_STATO_NON_AMMESSO` | Stato corrente diverso da `EMESSO` (rev 03-05-2026: `ACCETTATO` non piu' ammesso) |
| `E_PREV_REVISIONE_BOZZA_ESISTENTE` | Esiste gia' una revisione DRAFT per lo stesso numero |
| `E_PREV_STATO_CORRENTE_NON_TROVATO` | Preventivo non trovato |
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
