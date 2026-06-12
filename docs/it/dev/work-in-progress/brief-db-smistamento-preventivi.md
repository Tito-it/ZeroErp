# Brief DB — Smistamento preventivi: simmetria capability + vista natura-aware + push commessa per riga

> **Stato**: 🟡 **DA IMPLEMENTARE (team DB, branch `dev/db-tid`)**.
> **Owner concettuale**: Tid (Michele Carlo Titini).
> **Data**: 2026-06-12 — direzione "pannello smistamento strutturale" ratificata da Tid in sessione.
>
> **Perché esiste questo documento**: completamento del modello split-per-natura
> di [brief-preventivi-ordini.md](../work-done/brief-preventivi-ordini.md)
> (D1–D9, ramo ordine implementato 2026-06-09). Il ramo merce→ordine è
> riga-per-riga (sottoinsieme `p_righe_ids`, vista smistabili, capability con
> residuo); il ramo servizi→commessa è rimasto **tutto-o-niente** e la
> capability `can_push_commessa` non controlla il residuo. Il FE costruirà un
> **Pannello Smistamento unico** (una riga per riga di preventivo: natura,
> destinazione, stato, documento di destinazione, selezione multipla + "Smista
> selezionate") che richiede i tre interventi DB qui sotto. BE/FE restano in
> attesa di questi prerequisiti.

---

## 1. Contesto verificato (stato attuale, 2026-06-12)

- `script.fn_available_actions_preventivo`:
  `v_can_push := (v_stato_cod = 'ACCETTATO')` — **senza** residuo, asimmetrico
  rispetto a `v_can_ordine := ACCETTATO AND vendite.fn_preventivo_ha_residuo_ordine(id)`.
  Su preventivo solo-merce il FE mostra la sezione fatturazione a vuoto.
- `vendite.vw_preventivi_stato_fatturazione_righe`: conta **tutte** le righe
  attive senza distinguere la natura → su preventivo misto i contatori
  (`righe_totali` vs `righe_in_commessa`) raccontano un push "incompleto" anche
  quando il residuo è merce destinata a ordine. Espone già `in_commessa`
  (via `segment_key`), `emessa_af`, `fatturata`; **non** espone il ramo ordine.
- `vendite.fn_list_preventivi_da_pushare(p_competenza_mese, p_billing_account_id, p_limit, p_preventivo_id)`:
  natura-aware (solo `destinazione_tipo='COMMESSA'`, natura NULL = pregresso
  incluso), ma **senza filtro sottoinsieme righe** — il push singolo da UI
  (`p_preventivo_id`) spinge sempre tutte le righe eleggibili.
- Ramo ordine (riferimento di simmetria, già a terra):
  `vendite.fn_preventivo_ha_residuo_ordine`, `vw_preventivi_righe_smistabili_ordine`,
  `fn_push_preventivo_a_ordine(p_preventivo_id, p_righe_ids, p_pratica_id, ...)`,
  idempotenza via `ordini_righe.preventivo_riga_id`.

Progetto non in produzione: **breaking change ammessi**, nessuna compatibilità
di fase richiesta (colonne/firme si cambiano in place, con nuovo changeSet a
numerazione successiva — mai modificare YAML già mergiati).

---

## 2. Richiesta A — Capability `can_push_commessa` simmetrica (con residuo + reason)

1. **Nuova `vendite.fn_preventivo_ha_residuo_commessa(p_preventivo_id bigint) RETURNS boolean`**
   — speculare a `fn_preventivo_ha_residuo_ordine`: TRUE se esistono righe
   attive eleggibili al push commessa non ancora in commessa. **Il predicato di
   eleggibilità deve essere lo stesso di `fn_list_preventivi_da_pushare`**
   (righe `attivo`, `quantita > 0`, `prezzo_unitario >= 0`, natura NULL o
   `destinazione_tipo='COMMESSA'`, `NOT EXISTS commesse_attivita` su
   `segment_key 'PREV:<uid>:R:<riga_id>'` con `stato_emissione='EMESSA'`) —
   idealmente fattorizzato da una vista unica come fatto per il ramo ordine
   (`vw_preventivi_righe_smistabili_ordine`), così capability, list-fn e
   pannello leggono la stessa verità. Guard standard su id NULL/<=0.
2. **`script.fn_available_actions_preventivo`** (nuovo changeSet, numerazione
   successiva al `20260609-08`):
   - `v_can_push := (v_stato_cod = 'ACCETTATO') AND vendite.fn_preventivo_ha_residuo_commessa(p_preventivo_id)`
   - nuovo output `can_push_commessa_reason`, simmetrico a
     `can_genera_ordine_reason`: `NULL` se ammesso, altrimenti
     `'PREVENTIVO_NESSUNA_RIGA_COMMESSA'` (nessun residuo servizi) o
     `'PREVENTIVO_NON_ACCETTATO'`.
   - l'azione hardcoded `push_commessa` in `available_actions` segue lo stesso
     gate (come già fa `genera_ordine` con `v_can_ordine`).

Il FE consuma già `can_push_commessa` + reason key (Message hint nel drawer):
nessuna richiesta aggiuntiva lato seed.

---

## 3. Richiesta B — Vista smistamento natura-aware per riga (+ aggregata per ramo)

Fonte dati del Pannello Smistamento. Evolvere le due viste esistenti
(breaking change ok; in alternativa rinominarle `vw_preventivi_smistamento*`
se il team DB preferisce un nome non più fatturazione-centrico — a vostra
discrezione, il BE si adegua).

1. **`vw_preventivi_stato_fatturazione_righe`** — aggiungere per ogni riga:
   - `natura_vendita_codice` e `destinazione_tipo` (LEFT JOIN
     `config.nature_vendita`; natura NULL → trattata `COMMESSA`, pregresso);
   - ramo ordine: `ordine_riga_id`, `ordine_id`, `ordine_numero` (JOIN
     `vendite.ordini_righe.preventivo_riga_id` → testata ordine);
   - `stato_smistamento` derivato, una sola colonna autorevole per la UI:
     `'RESIDUA'` (nessuna destinazione) / `'A_ORDINE'` / `'IN_COMMESSA'` /
     `'EMESSA_AF'` / `'FATTURATA'` (gli ultimi tre progressivi sul ramo
     commessa, come oggi).
2. **`vw_preventivi_stato_fatturazione`** (aggregata) — contatori per ramo:
   `righe_totali`, `righe_merce`, `righe_servizi`, `righe_a_ordine`,
   `righe_in_commessa`, `righe_emesse_af`, `righe_fatturate`, e un
   `righe_residue` complessivo (= non smistate, qualunque ramo: alimenta il
   progress "X/Y smistate → EVASO" del pannello, coerente con il gate D6).

---

## 4. Richiesta C — Push commessa per sottoinsieme righe (simmetria col ramo ordine)

**`vendite.fn_list_preventivi_da_pushare`**: aggiungere parametro
`p_righe_ids bigint[] DEFAULT NULL` **alla firma esistente** (NO overload:
su PG due firme `(T)` e `(T, U DEFAULT ...)` sono ambigue alla chiamata con un
solo argomento — incidente già visto sul progetto; un solo nuovo changeSet che
sostituisce la firma è ok, progetto non in produzione).

- `NULL` → comportamento attuale (tutte le righe eleggibili: batch e push-tutto).
- Valorizzato → filtro aggiuntivo `pr.id = ANY(p_righe_ids)`; richiede
  `p_preventivo_id NOT NULL` (il sottoinsieme ha senso solo su push singolo
  UI-driven): in caso contrario `fn_log_and_raise_error` con codice dedicato
  (proposta: `E_PUSH_RIGHE_IDS_SENZA_PREVENTIVO`).
- Righe del sottoinsieme non eleggibili (già in commessa, natura ORDINE, non
  attive): **skip silenzioso**, coerente con D5 del brief preventivi-ordini
  (il "tutte già allocate → errore semantico" resta gestito a monte dal BE con
  il count eleggibili, come oggi).

L'idempotenza per riga esiste già (`segment_key` su `commesse_attivita` +
`NOT EXISTS` su EMESSA): non serve altro a DB. L'estensione firma BE
(`push_a_commessa(preventivo_id, righe_ids)` → orchestrator → questa fn) e
l'endpoint del pannello sono a carico backend, **dopo** la consegna DB.

---

## 5. Test richiesti (pgTAP, a carico team DB)

- `fn_preventivo_ha_residuo_commessa`: misto/solo-merce/solo-servizi/post-push
  (FALSE dopo push completo), guard id invalido.
- `fn_available_actions_preventivo`: `can_push_commessa` FALSE + reason
  `PREVENTIVO_NESSUNA_RIGA_COMMESSA` su solo-merce ACCETTATO; TRUE su misto;
  reason `PREVENTIVO_NON_ACCETTATO` fuori stato.
- Viste: preventivo misto con 1 riga a ordine + 1 in commessa + 1 residua →
  `stato_smistamento` e contatori per ramo corretti.
- `fn_list_preventivi_da_pushare` con `p_righe_ids`: sottoinsieme, skip
  silenzioso riga non eleggibile, errore se `p_righe_ids` senza
  `p_preventivo_id`, NULL = invariato.

---

## 6. Fuori scope DB (promemoria per il dopo-consegna, lato BE/FE)

- BE: `push_a_commessa` con `righe_ids`, endpoint unico righe-smistamento per
  il pannello, rimozione `stato_fatturazione` shape attuale.
- FE: Pannello Smistamento in `PreventiviDrawer` (sostituisce
  `PreventiviIntegrazione`), assorbe `GeneraOrdineDialog`; sul percorso pratica
  resta consuntivo read-only (lo smistamento lo fa `CONFERMA_VENDITA`).
- Già fatto in questa sessione (FE, indipendente da DB): fix `app-escape` su
  `DocumentiGeneratiSorgenteList` (alla radice del BB) e wrapper condizionale
  su `PreventiviIntegrazione` (escape solo per lock-di-stato, non in readonly
  puro).
