# Brief DB — `fn_list_preventivi_da_pushare`: competenza NOT NULL + policy `competenza_mese` ignorata

> **Tipo documento**: brief operativo **per il team DB** (`dev/db-tid`).
>
> **Data**: 2026-06-10 · **Stato**: 🟢 **CONSEGNATO, APPLICATO E VERIFICATO
> RUNTIME (2026-06-10)** —
> `20260610-06-update-fn-list-preventivi-da-pushare-competenza`. Il fix DB
> adotta la variante `GREATEST(competenza_dal, COALESCE(...))` per garantire
> `dal ≤ al` anche con `validita_dal` NULL + `validita_al` valorizzato (chiude
> anche il punto aperto di §3) e allinea il filtro WHERE. Verifica:
> `smoke-test-preventivi-smistamento-ordine.sh` **28 OK, 0 FAIL** — giro misto
> completo fino a EVASO (passi 11-13 ex-rossi ora verdi).
>
> **Impatto**: blocca il push preventivo→commessa per ogni preventivo senza
> validità (stato legittimo) **e** perde silenziosamente la policy di
> fatturazione DIFFERITA. Colpisce sia il push standalone (`push-commessa`) sia
> l'**orchestratore `CONFERMA_VENDITA`** (stessa fn alimenta il ramo servizi)
> sia il **meccanismo c7-2** della pratica PREVENTIVI.

## 1. Bug 1 — crash NOT NULL su preventivo senza validità (verificato runtime)

`vendite.preventivi.validita_dal/validita_al` sono **nullable** (e opzionali nel
form FE): un preventivo ACCETTATO senza validità è legittimo. Ma la fn proietta:

```sql
p.validita_dal AS competenza_dal,
p.validita_al  AS competenza_al,
```

e `vendite.commesse_attivita.competenza_dal/competenza_al` sono **NOT NULL** →
il push esplode con violazione vincolo grezza
(`E_COMMESSA_PUSH_PARZIALE_VIETATO` con detail "valore nullo nella colonna
competenza_dal"). Riprodotto: preventivo misto, riga servizio, push-commessa →
HTTP 422.

**Precedente nel modello**: la fn gemella `fn_list_ordini_da_pushare` proietta
`o.data, o.data` (NOT NULL) — mai nullo. E la stessa fn preventivi usa già il
fallback corretto altrove: `COALESCE(p.validita_dal, p.data)` per
`data_attivita` e per la derivazione del mese. Manca solo su `competenza_dal/al`.

## 2. Bug 2 — la policy `p.competenza_mese` è ignorata (bug logico, priorità alta)

La fn deriva il mese **solo** da validità/data:

```sql
date_trunc('month', COALESCE(p.validita_dal, p.data))::date AS competenza_mese,
```

ma `vendite.preventivi.competenza_mese` è la **colonna di policy** scritta:

- dall'**accettazione** (`preventivi_service.cambia_stato`, modalità DIFFERITA:
  mese scelto dall'operatore);
- dall'**handler pratica** `vendita.push_preventivo` (decisione c7-2: l'handler
  scrive `fatturazione_immediata`+`competenza_mese` sul preventivo PRIMA del
  push, contando sulla propagazione della pipeline).

Risultato: per un preventivo DIFFERITA con competenza settembre, la commessa
riceve il mese di `validita_dal`/`data` (≈ mese corrente) → **la riga finisce
nel lotto di fatturazione sbagliato**. L'intero meccanismo c7-2 è oggi inerte a
valle. (`p.fatturazione_immediata` invece è proiettato correttamente.)

## 3. Fix proposto (stessa fn, nuovo changelog `runOnChange`)

```sql
COALESCE(p.validita_dal, p.competenza_mese, p.data)                AS competenza_dal,
COALESCE(p.validita_al, p.validita_dal, p.competenza_mese, p.data) AS competenza_al,
...
COALESCE(p.competenza_mese,
         date_trunc('month', COALESCE(p.validita_dal, p.data))::date) AS competenza_mese,
```

- `competenza_mese`: la policy, se presente, è **autorevole**; il derivato
  validità/data resta il fallback per il pregresso.
- `competenza_dal/al`: mai NULL, degradazione coerente col precedente ordini
  (senza validità → `p.data`, come `o.data, o.data`). Il CHECK
  `chk_commesse_competenza_range` resta soddisfatto (dal ≤ al per costruzione).
- Da valutare (decisione DB): se con policy DIFFERITA sia più corretto
  `competenza_dal = p.competenza_mese` (primo del mese di policy) anche quando
  `validita_dal` è valorizzata — il filtro emittibilità usa comunque
  `competenza_mese`, quindi non è bloccante.
- Anche il filtro `p_competenza_mese` della fn (WHERE) va allineato alla stessa
  espressione del SELECT, altrimenti lista e filtro divergono.

## 4. pgTAP richiesti

1. Preventivo ACCETTATO **senza validità** + riga servizio → push OK,
   `competenza_dal/al = p.data`, nessuna violazione NOT NULL.
2. Preventivo DIFFERITA con `competenza_mese = '2026-09-01'` →
   `competenza_mese` proiettato = settembre (policy vince sul derivato).
3. Pregresso: `competenza_mese` NULL + validità valorizzata → derivato da
   `validita_dal` (comportamento attuale invariato).

## 5. A valle (BE, non DB)

Nessun cambio Python: l'handler e il push consumano già i campi proiettati.
Alla consegna: re-run `smoke-test-preventivi-smistamento-ordine.sh` (passi
11-13 oggi rossi diventano verdi) e poi smoke del giro pratica CONFERMA_VENDITA.

*Brief DB — fn_list_preventivi_da_pushare competenza — ZeroERP (2026-06-10).*
