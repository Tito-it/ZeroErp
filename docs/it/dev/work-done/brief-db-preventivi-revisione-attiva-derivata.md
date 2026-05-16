# Brief DB — `is_revision_attiva` derivata + copia componenti in `fn_crea_revisione_preventivo`

> **Data**: 2026-05-15
> **Branch target**: `dev/db-tid`
> **Scope**: refactor di modello su `vendite.preventivi` per eliminare il flag
> persistito `is_revision_attiva` (oggi mantenuto manualmente, soggetto a drift)
> e sostituirlo con un predicato derivato. Contestualmente: estensione di
> `fn_crea_revisione_preventivo` per copiare anche `preventivi_righe_componenti`
> con FK remap.
>
> Refactor di modello "best-in-absolute" — non un quick fix.

---

## 1. Problemi che chiude

### 1.1 Predecessore in limbo dopo annullamento revisione

Quando si annulla rev N+1, il predecessore (rev N) resta con
`is_revision_attiva = FALSE` (settato a FALSE da `fn_crea_revisione_preventivo`
e mai ripristinato). Il flag mente: rev N è di fatto "l'ultima rev viva" del
numero, ma il sistema la considera non attiva. Side-effect catena:

- Il filtro lista BE (`solo_revisione_attiva=true`) nasconde rev N perché esiste
  rev N+1 con `rev` maggiore — il filtro non guarda lo stato.
- L'utente vede solo rev N+1 ANNULLATA, che è stato terminale → nessuna azione.
- Per agire deve cambiare filtro a "mostra storico" → UX rotta.

### 1.2 Componenti BoM non copiati dalla revisione

`fn_crea_revisione_preventivo` copia testata + righe + indirizzi, ma NON copia
`preventivi_righe_componenti`. Conseguenza: rev N+1 ha righe padre compositi
**senza componenti** → push commessa fallisce, ComponentiPanel vuoto, prezzo padre
non ricalcolato.

### 1.3 Flag persistito sincronizzato a mano

Qualunque nuovo flusso che modifica stato delle revisioni deve ricordarsi di
mantenere `is_revision_attiva` coerente. Il bug 1.1 è un caso non previsto. La
soluzione "trigger AFTER UPDATE che ripristina il flag al predecessore"
risolverebbe ma aggiunge complessità imperativa per mantenere un flag che è
**ridondante** rispetto ai dati strutturali.

---

## 2. Modello proposto

### 2.1 DROP colonna `vendite.preventivi.is_revision_attiva`

Diventa derivata, non più persistita.

### 2.2 Nuova colonna `config.stati_doc_preventivi.is_abortito BOOLEAN NOT NULL DEFAULT FALSE`

Metadato sullo stato che distingue "il documento è morto qui" (ANNULLATO) da
"il documento è chiuso ma rappresenta destino del numero" (RIFIUTATO / SCADUTO /
ACCETTATO).

Seed:

| `codice_interno` | `is_abortito` |
|---|---|
| `DRAFT` | FALSE |
| `EMESSO` | FALSE |
| `ACCETTATO` | FALSE |
| `RIFIUTATO` | FALSE |
| `SCADUTO` | FALSE |
| `ANNULLATO` | **TRUE** |

Semantica: "uno stato è abortito quando l'operatore (o sistema) ha rinunciato
a questa istanza di revisione e si vuole far rifluire l'attivazione al
predecessore non-abortito". Diverso dal generico "terminale": RIFIUTATO è
terminale ma chiude **tutto il numero**, non solo la rev. Se in futuro emergerà
necessità anche di `is_terminale`, andrà aggiunto separatamente — non è
prerequisito di questo refactor.

### 2.3 Nuova vista `vendite.vw_preventivi`

Wrappa `vendite.preventivi` aggiungendo le proiezioni derivate. Sostituisce
ogni `SELECT ... FROM vendite.preventivi` lato BE.

```sql
CREATE OR REPLACE VIEW vendite.vw_preventivi AS
SELECT
    p.*,
    -- È la rev "attiva" del numero: non esiste rev superiore non-abortita.
    NOT EXISTS (
        SELECT 1
          FROM vendite.preventivi p2
          JOIN config.stati_doc_preventivi s2
            ON s2.id = p2.stato_doc_preventivo_id
         WHERE p2.numero = p.numero
           AND p2.rev > p.rev
           AND s2.is_abortito IS FALSE
    ) AS is_attiva
  FROM vendite.preventivi p;
```

Note:

- Nome colonna `is_attiva` invece di `is_revision_attiva` per chiarezza ed
  evitare drift terminologico. Il vecchio termine è confondente: non era "la
  revisione è attiva" ma "questa rev è quella corrente per il numero".
- La vista è semplice SELECT — niente trigger, niente sincronizzazione
  manuale. Coerenza garantita per costruzione.
- Performance: il NOT EXISTS è O(N) sulle rev per numero. Indice già implicito
  su `(numero, rev)` via UNIQUE constraints. Verificare via EXPLAIN dopo deploy.

### 2.4 `fn_crea_revisione_preventivo` — refactor completo

Modifiche:

1. **RIMUOVERE** UPDATE su predecessore (riga 132-135 originale):
   ```sql
   -- DELETE blocco intero:
   UPDATE vendite.preventivi
      SET is_revision_attiva = false, ...
    WHERE id = p_preventivo_id;
   ```
   Non serve più: con la derivazione, la rev N+1 (DRAFT, is_abortito=false)
   automaticamente "supera" rev N nel calcolo `is_attiva`.

2. **RIMUOVERE** dalla INSERT della nuova testata il campo `is_revision_attiva`
   (colonna droppata).

3. **AGGIUNGERE** dopo la copia delle righe il blocco di **copia componenti
   BoM** con FK remap su nuove righe (chiude bug 1.2):

   ```sql
   -- Copia preventivi_righe_componenti per le righe padre composite copiate.
   -- FK remap: riga_preventivo_id passa dall'id vecchio (rev N) all'id nuovo
   -- (rev N+1). Necessario JOIN su (articolo_id, ordine) — coppia stabile fra
   -- vecchia e nuova riga, perche' INSERT...SELECT preserva l'ordine logico
   -- ma genera id nuovi. Affidabile perche' UNIQUE non e' imposta su
   -- (preventivo_id, ordine), quindi pattern (preventivo_id, articolo_id, ordine)
   -- e' deterministico per la copia 1:1.
   INSERT INTO vendite.preventivi_righe_componenti (
       riga_preventivo_id, articolo_componente_id, componente_id,
       coeff_qta_snapshot, quantita, prezzo_unitario, iva_id,
       origine_prezzo, prezzo_resolver_context,
       stato_approvazione_prezzo, pratica_approvazione_prezzo_id,
       uom_operativa_id, factor_to_base, qta_operativa,
       ordine, attivo, meta,
       user_insert, user_update
   )
   SELECT
       new_pr.id,  -- FK remap
       prc.articolo_componente_id, prc.componente_id,
       prc.coeff_qta_snapshot, prc.quantita, prc.prezzo_unitario, prc.iva_id,
       prc.origine_prezzo, prc.prezzo_resolver_context,
       prc.stato_approvazione_prezzo, prc.pratica_approvazione_prezzo_id,
       prc.uom_operativa_id, prc.factor_to_base, prc.qta_operativa,
       prc.ordine, prc.attivo, prc.meta,
       COALESCE(p_user, CURRENT_USER), COALESCE(p_user, CURRENT_USER)
     FROM vendite.preventivi_righe_componenti prc
     JOIN vendite.preventivi_righe old_pr
       ON old_pr.id = prc.riga_preventivo_id
      AND old_pr.preventivo_id = p_preventivo_id
     JOIN vendite.preventivi_righe new_pr
       ON new_pr.preventivo_id = v_new_id
      AND new_pr.articolo_id = old_pr.articolo_id
      AND new_pr.ordine IS NOT DISTINCT FROM old_pr.ordine
    WHERE prc.attivo IS TRUE;
   ```

   Verificare in pgTAP che il count componenti pre/post sia uguale.

4. Aggiornare il `COMMENT ON FUNCTION` per riflettere: "copia testata + righe +
   indirizzi + componenti BoM. Non gestisce is_attiva (derivato in vista)".

### 2.5 Backfill dati (migration)

I contratti esistenti hanno `is_revision_attiva` con valori storici (alcuni TRUE,
alcuni FALSE per costruzione di `fn_crea_revisione_preventivo`). Dopo il DROP,
la derivazione potrebbe non riprodurre esattamente i valori storici per casi
patologici (es. preventivi singoli con `is_revision_attiva=false` di default DDL
ma comunque "attivi" perché non hanno rev superiori).

Verifica pre-DROP:

```sql
-- Dovrebbe essere zero
SELECT COUNT(*) FROM vendite.preventivi p
 WHERE p.is_revision_attiva IS DISTINCT FROM (
     NOT EXISTS (
         SELECT 1 FROM vendite.preventivi p2
          JOIN config.stati_doc_preventivi s2 ON s2.id = p2.stato_doc_preventivo_id
          WHERE p2.numero = p.numero
            AND p2.rev > p.rev
            AND COALESCE(s2.codice_interno = 'ANNULLATO', FALSE) IS FALSE
     )
 );
```

Se zero → DROP sicuro. Se non zero → segnalare a Tid per decidere (probabile
divergenza storica dei single-rev `is_revision_attiva=FALSE`).

---

## 3. Cosa fare (ordine changelog)

Sequenza ordinata in 4 changelog separati (rollback granulare):

### Changelog 1: aggiungere `is_abortito` + seed

`20260515-XX-alter-stati-doc-preventivi-add-is-abortito-mctit.yaml`

```sql
ALTER TABLE config.stati_doc_preventivi
  ADD COLUMN is_abortito BOOLEAN NOT NULL DEFAULT FALSE;

UPDATE config.stati_doc_preventivi
   SET is_abortito = TRUE
 WHERE codice_interno = 'ANNULLATO';
```

### Changelog 2: creare vista `vw_preventivi`

`20260515-XX-create-view-vw-preventivi-mctit.yaml` (`runOnChange: true`).

CREATE OR REPLACE VIEW come §2.3.

Grants sulla vista coerenti con la tabella `preventivi` (verificare con
`docs/it/dbzero` la policy grants di vendite).

### Changelog 3: refactor `fn_crea_revisione_preventivo`

`20260515-XX-update-fn-crea-revisione-preventivo-mctit.yaml` (`runOnChange: true`).

CREATE OR REPLACE FUNCTION con le 4 modifiche di §2.4. Lascia la signature
inalterata (firma `%TYPE`, return TABLE `(nuovo_preventivo_id, numero,
nuova_rev)`).

### Changelog 4: DROP colonna

`20260515-XX-alter-preventivi-drop-is-revision-attiva-mctit.yaml`

Verifica pre-DROP (query in §2.5) come check Liquibase
(`<preConditions>`). Se KO blocca con messaggio parlante.

```sql
ALTER TABLE vendite.preventivi DROP COLUMN is_revision_attiva;
```

**Ordine deploy obbligatorio**: 1 → 2 → 3 → 4. Il BE refactor non parte finché
**tutti e 4** non sono atterrati (vedi §5 sotto).

---

## 4. Verifica post-deploy

### pgTAP suite minimale (`db/pgtap/vendite/preventivi_revisione_modello_derivato.sql`)

1. **vista derivata corretta** — caso single-rev:
   - Setup: 1 preventivo rev=0 stato DRAFT
   - Atteso: `vw_preventivi.is_attiva = TRUE`

2. **vista corretta dopo revisione**:
   - Setup: rev 0 EMESSO + rev 1 DRAFT (creata via fn)
   - Atteso: rev 0 `is_attiva=FALSE`, rev 1 `is_attiva=TRUE`

3. **vista corretta dopo annullamento revisione** (regression bug 1.1):
   - Setup: rev 0 EMESSO + rev 1 ANNULLATO
   - Atteso: rev 0 `is_attiva=TRUE`, rev 1 `is_attiva=FALSE`

4. **componenti BoM copiati su revisione** (regression bug 1.2):
   - Setup: rev 0 con riga padre composito + 3 componenti, EMESSO
   - Azione: `fn_crea_revisione_preventivo`
   - Atteso: rev 1 ha riga padre + 3 componenti col FK remap corretto, stessi
     valori salvo `id`/`riga_preventivo_id`/`user_*`/`data_*`

5. **componenti soft-deleted NON copiati**:
   - Setup: rev 0 con componente `attivo=FALSE`
   - Azione: revisione
   - Atteso: rev 1 non ha quel componente (filtro `WHERE prc.attivo IS TRUE`)

6. **doppio annullamento a catena**:
   - Setup: rev 0 EMESSO, rev 1 ANNULLATO, rev 2 ANNULLATO
   - Atteso: rev 0 `is_attiva=TRUE`, rev 1 e rev 2 `is_attiva=FALSE`

---

## 5. Impatto BE (informativo per il backend agent)

Post-deploy DB, il backend agent farà refactor circoscritto a 4 punti:

| Consumer | Modifica |
|---|---|
| `apps/vendite/types.py` (`PreventivoListRow`, `PreventivoDetailRow`) | rename campo `is_revision_attiva: bool` → `is_attiva: bool` |
| `apps/vendite/db/preventivi_repository.py` linea 96-109 (filtro lista) | Subquery NOT EXISTS riscritta per usare `is_abortito` invece del solo `rev > v.rev`. Stessa logica della vista §2.3 |
| `apps/vendite/db/preventivi_repository.py` linea 157, 160 (SELECT list) | `FROM vendite.preventivi` → `FROM vendite.vw_preventivi`; proiezione `is_attiva` invece di `is_revision_attiva` |
| `apps/vendite/services/preventivo_document_context_builder.py` linea 121 | `testata.get("is_revision_attiva")` → `testata.get("is_attiva")` |

Test BE attesi:

- 685/685 attuali devono restare verdi dopo i rename
- +6 nuovi test che riflettono il filtro lista revisione-aware (i 6 scenari della
  pgTAP suite hanno simmetrici BE attraverso `list_preventivi`)

Nessun nuovo endpoint, nessun nuovo brief DB downstream previsto.

---

## 6. Coordinamento con FE

Side-effect FE:

- Il filtro "mostra storico revisioni" già presente nella lista FE diventa
  **coerente** con la nuova semantica: default nasconde le rev superate +
  le rev annullate, toggle mostra tutto. Nessuna modifica al componente
  filtro, ma la lista mostrerà casi diversi (es. rev 0 ricompare dopo
  annullamento rev 1).
- Il documento context builder espone `is_attiva` ai template documentali.
  Da verificare se qualche template usa `is_revision_attiva` come variabile
  (template per preventivi PDF). Se sì, rinomina nel template.

Nessun refactor strutturale FE richiesto.

---

## 7. Stima effort

| Pezzo | Effort DB | Note |
|---|---|---|
| Changelog 1 (add `is_abortito`) | 15 min | ALTER + UPDATE seed |
| Changelog 2 (CREATE vw) | 30 min | + verifica GRANTs |
| Changelog 3 (refactor fn) | 1h | include test funzionali manuali |
| Changelog 4 (DROP column) | 15 min | + check `<preConditions>` |
| pgTAP suite (6 test) | 1.5h | scenari sopra |
| **TOT DB** | **~3.5h** | inclusi test |

Effort BE post-DB: ~1h (4 rename + ~6 test) + 30 min smoke UI.

---

## 8. Riferimenti

- Funzione corrente: `docs/it/dbzero/vendite/funzioni/fn_crea_revisione_preventivo.md`
- Tabella stati: `docs/it/dbzero/config/tabelle/stati_doc_preventivi.md`
- Recap che ha rivelato il problema: discussione 2026-05-15 (sessione corrente)
- Riferimento concettuale "no quick fix": memoria `feedback_no_quick_fix_soluzione_assoluta`
