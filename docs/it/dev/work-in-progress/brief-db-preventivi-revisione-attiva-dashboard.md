# Brief DB — Preventivi: la vecchia revisione EMESSO riemerge come documento aperto nei cruscotti

> **Tipo**: brief DB (target `dev/db-tid`) · **Data**: 2026-07-08 · **Owner**: Tid
> **Ambito**: viste cruscotti fatturazione (`vendite.vw_dash_fatturazione_preventivi`
> → backlog + situazione aperta). **Origine**: segnalazione Tid — PRV0000038 appare in
> **EMESSO** nel Backlog fatturazione mentre la sua revisione **attiva è RIFIUTATA**.
> **Verifica eseguita dall'agent (sola lettura, ruolo super-admin per contesto RLS).**

---

## 1. Sintomo

Nel Backlog fatturazione (e nella nuova Situazione aperta v2) compare **PRV0000038** come
documento **EMESSO / IN_ATTESA**, ma lo stato reale del preventivo è **RIFIUTATO**: la rev 0 è
EMESSO, la rev 1 è RIFIUTATO. La rev 1 (l'ultima) è la revisione attiva.

## 2. Causa radice (bug di VISTA, non dato legacy)

Il modello preventivi versiona per `numero` + `rev`. La creazione revisione
(`vendite.fn_crea_revisione_preventivo`, rev 2026-05-15) ammette la revisione **solo da EMESSO**,
crea una nuova rev in **DRAFT** e **lascia di proposito** la rev precedente in **EMESSO** — il suo
header lo dichiara: *"Non gestisce is_revision_attiva: l'attivazione è derivata in
`vendite.vw_preventivi` tramite is_abortito degli stati."*

Quindi la vecchia rev EMESSO **non è un dato corrotto**: è la forma **attesa**. La correttezza
dipende interamente dal fatto che i consumatori filtrino per la **revisione attiva**.
`vw_preventivi` la deriva così:

```sql
is_attiva = NOT EXISTS (
  SELECT 1 FROM vendite.preventivi p2
  JOIN config.stati_doc_preventivi s2 ON s2.id = p2.stato_doc_preventivo_id
  WHERE p2.numero = p.numero AND p2.rev > p.rev AND s2.is_abortito IS FALSE
)
```

**Ma `vendite.vw_dash_fatturazione_preventivi` legge `vendite.preventivi` GREZZO**
(`FROM vendite.preventivi p ... GROUP BY p.id`), **senza il filtro `is_attiva`**. La sua
esclusione interna usa `sdp.esito = 'NEGATIVO'`, che scarta la rev attiva RIFIUTATA ma **lascia
passare la rev 0 EMESSO superata** → phantom "documento aperto".

## 3. Evidenza

Contesto RLS impostato per la lettura (super-admin):
`SET app.ruolo_applicativo='OPERATORE'; SET app.current_user_id='1';`

**Revisione attiva canonica (`vw_preventivi.is_attiva`) vs righe emesse dal dashboard:**

| numero | revisioni (rev:stato) | rev attiva (corretta) | righe emesse da backlog/aperto |
| --- | --- | --- | --- |
| PRV0000038 | 0:EMESSO, 1:RIFIUTATO | rev1 RIFIUTATO → **0 righe** | **1× EMESSO** (phantom) |
| PRV0000061 | 0:EMESSO, 1:EMESSO, 2:EMESSO, 3:ACCETTATO | rev3 ACCETTATO → **1 riga** | **4 righe** (ACCETTATO + 3× EMESSO phantom) |
| PRV0000065 | 0:EMESSO, 1:ANNULLATO, 2:EMESSO | rev2 EMESSO → **1 riga** | **2× EMESSO** (1 phantom) |

`PRV0000061` che mostra **4 righe per un solo preventivo** è la prova che è un bug di vista, non
un dato storto. Su 145 preventivi solo 3 hanno rev multiple: **tutti e 3 sbagliano**.
`storicizza` non è mai valorizzato (0 righe) → non è quello il segnale di "rev testa".

**Viste affette (verificate emettere le righe phantom):**

- `vendite.vw_dash_backlog_documenti` (Lente 2 Backlog)
- `vendite.vw_dash_aperto_documenti` (Situazione aperta v2)
- entrambe via `vendite.vw_dash_fatturazione_documenti` → `vendite.vw_dash_fatturazione_preventivi`
- **Da verificare**: `vendite.vw_dash_competenza_*` (Lente 1) se condivide la sorgente preventivi.

## 4. Perché OFFERTE non sono affette (pattern di riferimento CORRETTO)

Le offerte (`offerte_commerciali`) versionano a **catena** (`revisione_numero` +
`revisione_padre_id`, un documento OFC-* per revisione). `fn_crea_revisione_offerta` + trigger
z90 (`trgfn_offerte_commerciali_revisione`) mettono **automaticamente il padre in SUPERATA**
(`terminale=true`, `esito=NEGATIVO`) all'INSERT della revisione figlia.

Quindi la revisione superata è NEGATIVO → **già esclusa** dalla stessa clausola
`esito='NEGATIVO'` del dashboard. **Le offerte sono corrette — e più robuste dei preventivi**,
perché chiudono esplicitamente la rev superata invece di lasciarla "viva".

**Integrità verificata su tutte le offerte (contesto RLS super-admin):**

- **A)** tutte le offerte-padre (con una figlia) sono in stato **SUPERATA** — nessuna eccezione
  (3 padri su 3 catene).
- **B)** **0** offerte con figlia compaiono nei cruscotti (backlog + situazione aperta) → nessun
  phantom.
- Nessuna contraddizione `is_attiva` ∧ `ha_figlia`.

**Esempio dal vivo (revisione creata in-app il 2026-07-08):** OFC-0000181 (rev2, BOZZA) è la
revisione di OFC-0000050 (rev1) → alla creazione il padre OFC-0000050 è passato a **SUPERATA** e
nei cruscotti compare **solo** OFC-0000181 (la revisione attiva). Il meccanismo funziona anche
sulle revisioni nuove, non solo sui dati storici.

## 5. Perché ORDINI e CONTRATTI non sono affetti

- **Contratti**: testata con solo `numero`, **nessun meccanismo di revisione** → non versionati.
- **Ordini**: `documento_origine_tipo` / `documento_origine_id` / `canale_origine` (riferimento
  al documento di origine), **nessun `rev`/`revisione_padre`** → non versionati.

## 6. Fix proposti

### Opzione A — tattica (solo vista)

`vendite.vw_dash_fatturazione_preventivi` filtra la sorgente alla **sola revisione attiva**:
leggere `FROM vendite.vw_preventivi WHERE is_attiva` (DRY, riusa la derivazione canonica) oppure
aggiungere il predicato `NOT EXISTS (rev più alta con is_abortito=false)`. Dopo il filtro, la
logica `esito='NEGATIVO'` / residua esistente compone correttamente (vedi §7).
Rischio basso, tocca una sola vista `runOnChange`. **Non** sana l'anomalia di fondo (una rev
superata resta in stato EMESSO, semanticamente scorretto).

### Opzione B — di merito (allineamento al modello offerte) — RACCOMANDATA

Portare i preventivi allo **stesso pattern delle offerte** (simmetria di modello,
[[feedback_simmetria_modello_no_meta_scope]] / [[feedback_no_quick_fix_soluzione_assoluta]]):

1. Introdurre uno stato terminale **`SUPERATO`** per i preventivi (`fase=CHIUSO`,
   `terminale=true`, `esito=NEGATIVO`, coerente con `is_abortito` usato da `is_attiva`).
2. In `fn_crea_revisione_preventivo`: al momento della creazione della nuova rev, portare la rev
   precedente **EMESSO → SUPERATO** (come il trigger offerte fa con SUPERATA).
3. **Backfill** dei 3 casi esistenti: le rev superate ma rimaste EMESSO
   (PRV0000038 rev0, PRV0000061 rev0/1/2, PRV0000065 rev0) → SUPERATO.
4. A quel punto il dashboard è già corretto **senza toccare la vista** (l'esclusione
   `esito='NEGATIVO'` cattura SUPERATO), e `vw_preventivi.is_attiva` resta coerente.

Consigliata perché elimina la causa (non solo il sintomo) e uniforma preventivi/offerte.
Valutare se combinare **B** con **A** (difesa in profondità: la vista filtra comunque l'attiva).

### Nota — incoerenza semantica "abortito" da uniformare

Convivono due definizioni: la **colonna** `config.stati_doc_preventivi.is_abortito` (true solo per
ANNULLATO), usata da `is_attiva`; e `esito='NEGATIVO'` (RIFIUTATO/SCADUTO/ANNULLATO), usata dal
dashboard. Non rompe il fix, ma andrebbe uniformato concettualmente il significato di "revisione
che oscura le precedenti" (le offerte usano `SUPERATA/ANNULLATA`).

## 7. Test di non-regressione (dopo il fix)

Con contesto RLS operatore, le righe emesse da `vw_dash_backlog_documenti` e
`vw_dash_aperto_documenti` per i 3 numeri devono diventare:

| numero | atteso post-fix |
| --- | --- |
| PRV0000038 | **0 righe** (rev attiva RIFIUTATO → esclusa) |
| PRV0000061 | **1 riga** (rev3 ACCETTATO, fase IN_CORSO) |
| PRV0000065 | **1 riga** (rev2 EMESSO, fase IN_ATTESA) |

Query di verifica:

```sql
SET app.ruolo_applicativo='OPERATORE'; SET app.current_user_id='1';
SELECT 'backlog' v, codice, count(*) FROM vendite.vw_dash_backlog_documenti
 WHERE codice IN ('PRV0000038','PRV0000061','PRV0000065') GROUP BY codice
UNION ALL
SELECT 'aperto', codice, count(*) FROM vendite.vw_dash_aperto_documenti
 WHERE codice IN ('PRV0000038','PRV0000061','PRV0000065') GROUP BY codice;
```

Aggiungere pgTAP: per ogni numero multi-rev, `count` righe dashboard = 1 se la rev attiva è
non-negativa e non-transitata, 0 altrimenti; e invariante generale "nessuna rev non-attiva
compare nelle viste dashboard".

## 8. Riferimenti

- `vendite.vw_dash_fatturazione_preventivi` (sorgente da correggere)
- `vendite.vw_preventivi` (derivazione `is_attiva` canonica)
- `vendite.fn_crea_revisione_preventivo` (lascia la rev vecchia EMESSO)
- `vendite.fn_crea_revisione_offerta` + `trgfn_offerte_commerciali_revisione` (pattern SUPERATA — riferimento corretto)
- `config.stati_doc_preventivi` (aggiungere `SUPERATO` se Opzione B)
