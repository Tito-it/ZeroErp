# Modello logico — Componenti BoM padre-figli

> **Stato**: VIVO. Riflette il modello corrente del dominio. Quando una
> decisione cambia, **sovrascrivere** questo file (non appendere). Lo
> storico delle iterazioni e' in
> [changelog-decisioni-componenti.md](changelog-decisioni-componenti.md).
>
> **Ultimo aggiornamento**: 2026-10-01 (esposizione in fattura a tre
> modi — vedi §7). Prima: 2026-05-13 (decisione "BoM contratto
> immutabile per documento" — vedi §9.3).

---

## 1. Cos'e' un articolo composito

Un articolo `catalogo.articoli` con `is_composito = TRUE` rappresenta un
**contenitore**: un prodotto che ha una propria identita' commerciale
(codice, descrizione, UoM, IVA) ma il cui prezzo e' la **somma dei
prezzi dei suoi componenti** (vedi §4).

Gli articoli compositi sono usati per modellare kit, pacchetti, bundle,
prodotti complessi. Esempi: "Kit installazione caldaia", "Pacchetto
manutenzione annuale", "Bundle promo Estate 2026".

## 2. La BoM (Bill of Materials)

Il composito ha una **lista materiali** (`catalogo.articoli_componenti`)
che definisce QUALI componenti lo compongono e in che **quantita'
relativa**.

Ogni riga BoM e' immutabile per design (UPDATE strutturale bloccato):
per evolvere la BoM si applica il pattern "chiudi+inserisci nuova
versione" (chiudi `valido_al` della riga corrente, inserisci nuova riga
con `valido_dal` successivo). Garantisce ricostruzione storica e audit.

Colonne strutturali (immutabili):

| Colonna                                       | Significato                                                       |
| --------------------------------------------- | ----------------------------------------------------------------- |
| `prodotto_id`                                 | articolo padre composito                                          |
| `componente_id`                               | articolo figlio (puo' essere a sua volta composito? No, vedi §9)  |
| `coeff_qta`                                   | quantita' del figlio per unita' di padre                          |
| `obbligatorio`                                | TRUE = sempre incluso, FALSE = opzionale                          |
| `esposizione_in_fattura`                      | come il figlio si vede in fattura: `NASCOSTO` (default) \| `DESCRITTIVO` \| `VALORIZZATO` (vedi §7) |
| `valido_dal`, `valido_al`, `validita` (range) | versionamento daterange                                           |
| `attivo`                                      | soft-delete logico                                                |

Colonne `partecipa_qta` e `determina_qta_padre`: scheletro per logiche
future di calcolo quantita', non lette runtime dalle fn attuali.

## 3. Simmetria padre-figli a 3 livelli

Il pattern padre-figli **si ripete identico** in tre tabelle, una per
livello:

```
LIVELLO 1 — STRUTTURA (catalogo)
  catalogo.articoli                    (padre composito)
    ├──> catalogo.articoli_componenti  (figli BoM)

LIVELLO 2 — PREZZO (catalogo / vendite)
  vendite.listini_righe_componenti     (prezzi figli in contesto padre)
    ├──> riferisce catalogo.articoli_componenti via FK

LIVELLO 3 — ISTANZA COMMERCIALE (documento)
  vendite.<sorgente>_righe             (riga padre nel documento)
    ├──> vendite.<sorgente>_righe_componenti (righe figli del documento)
       <sorgente> ∈ {preventivi, ordini, contratti, ddt}
```

Conseguenze pratiche:

- Lo stesso pattern di **trigger guard** vale a tutti e tre i livelli
  (`script.trgfn_componenti_*` parametrizzati via TG_ARGV)
- Lo stesso pattern di **Dialog "Componenti di X"** vale lato FE
  (componente Vue riusabile)
- Lo stesso pattern di **Repository/Service** vale lato BE
  (gerarchia parametrizzata per sorgente)

## 4. Regola del prezzo padre

> **Il prezzo padre di un composito e' SEMPRE la somma dei prezzi
> figli pesata per il coefficiente di quantita'.**

- Nel **documento**: trigger DB `_z90_ricalcola_padre` aggiorna
  `<sorgente>_righe.prezzo_unitario = SUM(figli.prezzo_unitario ×
  coeff_qta_snapshot)` ad ogni INSERT/UPDATE/DELETE dei figli
- Nel **listino**: niente persistenza del prezzo padre composito (la
  tabella `vendite.listini_righe` per padri compositi e' **vietata**,
  vedi §7). Il prezzo padre del listino si calcola al volo via vista o
  ricavando SUM dal resolver.

Conseguenza: **nessun caller direttamente legge il prezzo padre**;
qualsiasi consumatore (resolver, generazione fattura, riepilogo IVA)
deriva dalla somma figli.

## 5. Regole sui prezzi

| Soggetto                    | NULL | 0           | Negativo |
| --------------------------- | ---- | ----------- | -------- |
| Figlio `obbligatorio=TRUE`  | NO   | NO (`<> 0`) | si'      |
| Figlio `obbligatorio=FALSE` | NO   | si'         | si'      |
| Padre composito (calcolato) | NO   | si'         | si'      |

Razionale:

- Un obbligatorio "deve produrre valore": prezzo non zero
- Un opzionale puo' essere "incluso a costo zero" o "non venduto"
- Il padre, essendo somma, puo' essere 0 (figli a zero) o negativo
  (figli con segni misti — sconti, abbuoni)
- NULL mai ammesso: ogni componente del documento ha un prezzo certo

## 6. IVA coerente padre-figli

Vincolo di dominio: il padre composito e tutti i suoi figli BoM
condividono la **stessa aliquota IVA**.

Trigger `catalogo.trgfn_articoli_componenti_guard_iva`:

- BEFORE INSERT OR UPDATE OF `attivo` su `catalogo.articoli_componenti`:
  per un legame attivo, NEW.componente deve avere `iva_id` uguale al
  padre. Il fronte `UPDATE OF attivo` copre la **riattivazione** del
  legame (FALSE→TRUE), chiudendo il percorso *spegni → cambia IVA →
  riaccendi* (vedi sotto)
- BEFORE UPDATE su `catalogo.articoli.iva_id`
  (`trgfn_articoli_guard_iva_bom_attiva`): se l'articolo e' padre
  composito di righe BoM attive → tutti i figli devono avere stessa
  IVA; se l'articolo e' figlio in BoM attive → il padre deve avere
  stessa IVA

Questi due trigger (+ il freeze struttura che rende `componente_id`
immutabile) sono il **punto unico di enforcement** dell'invariante: una
BoM attiva non puo' avere padre e figlio a IVA diversa. Per questo il
listino non ri-controlla piu' l'IVA (Guard 5 di
`trgfn_listini_righe_comp_guard_coerenza_bom` rimosso il 2026-06-03).

Conseguenza: il riepilogo IVA del documento e' indistintamente
calcolabile da padre o da figli (stessa aliquota).

### 6.1 Enforcement a punto unico (decisione 2026-06-03)

L'invariante e' garantito **solo alla sorgente** (i due trigger su
`catalogo` sopra). I consumatori a valle che materializzano i componenti
— listino bundle (`listini_righe_componenti`) e righe documento
(`*_righe_componenti`) — **NON ri-verificano l'IVA**: si fidano della
sorgente.

Motivazione: con i guard catalogo attivi e' **impossibile** creare/
mantenere una BoM attiva con padre e figlio a IVA diversa. Due percorsi
potevano aggirare l'invariante, entrambi chiusi:

- **stato NULL/NULL**: padre+figlio entrambi senza IVA passano l'INSERT
  (`NULL = NULL`), ma restano bloccati in popolamento perche' assegnare
  l'IVA a un solo lato fallisce (`NULL IS DISTINCT FROM <valore>` = TRUE).
- **spegni → cambia IVA → riaccendi**: deattivando il legame, il guard
  su `articoli.iva_id` lo ignora (controlla solo `attivo = TRUE`), quindi
  si potrebbe cambiare l'IVA del figlio e riattivare. Chiuso il 2026-06-03
  estendendo `trgfn_articoli_componenti_guard_iva` a `BEFORE INSERT OR
  UPDATE OF attivo`: l'IVA e' ri-verificata a ogni riaccensione
  (`FALSE→TRUE`).

Un ri-controllo a valle sarebbe quindi ridondante e — se presente solo su
alcuni consumatori — introdurrebbe un'asimmetria confusiva (un punto
rifiuta, gli altri accettano).

> **Nota per chi mantiene il codice**: NON aggiungere check IVA sui guard
> a valle. Se in futuro serve difesa in profondita' (es. import massivi con
> `session_replication_role = replica` che bypassano i trigger), va aggiunta
> in modo **simmetrico su tutti** i `*_righe_componenti` + listino, non su
> uno solo. Storia: in origine il listino aveva un proprio "Guard 5" IVA,
> rimosso il 2026-06-03 proprio per togliere l'asimmetria (vedi brief
> `work-done/brief-db-listini-rimozione-guard5-iva.md`).

## 7. Esposizione in fattura = regola di presentazione (non di pricing)

`catalogo.articoli_componenti.esposizione_in_fattura` (FK su
`config.esposizioni_componente`) dice come il figlio si vede in
fattura, sotto la riga del suo kit:

| Modo | In fattura | Nel totale del kit |
| --- | --- | --- |
| `NASCOSTO` (default) | non compare | si' |
| `DESCRITTIVO` | riga sotto il kit, senza prezzo ne' importo | si' |
| `VALORIZZATO` | riga sotto il kit con quantita', prezzo e importo suoi | **no**: il suo importo e' sulla sua riga |

- Un figlio resta **sempre legato al suo kit**, anche valorizzato: mai
  una riga sciolta, come se fosse venduto da solo.
- Se tutti i figli sono `VALORIZZATO`, la riga del kit resta come
  intestazione **senza importo** (`NULL`, non zero).
- Il **totale del documento non cambia mai** al variare
  dell'esposizione: ogni figlio sta o nel kit o sulla sua riga.

Fino al 2026-10-01 era il booleano `esposto_in_fattura`, convertito sul
posto: `false` → `NASCOSTO`, `true` → `DESCRITTIVO` (cio' che il `true`
produceva). Il `VALORIZZATO` e' il terzo modo nato quel giorno.

**Importante**: l'esposizione NON e' gate di pricing — non filtra quali
componenti finiscono in `*_righe_componenti`. Tutti i figli validi alla
data vi finiscono, con il loro prezzo. La legge SOLO la
rappresentazione della fattura,
[`vendite.vw_fattura_righe_esposte`](/dbzero/vendite/views/vw_fattura_righe_esposte),
la stessa per PDF, XML SDI e portale.

**Dove viaggia**: nei documenti (`*_righe_componenti`) non e' copiata,
si legge dalla BoM (immutabile per design) e le preview la proiettano;
in commessa sta nel `meta` dell'attivita' (chiave `esposizione`; fino
al 2026-10-01 `esposto_in_fattura` — il cambio di chiave e' a carico
del backend); sulla fattura e' congelata in
`fatture_righe.kit_esposizione` alla generazione, insieme a `kit_key`
e all'articolo padre.

## 8. Listino composito (livello 2): bundle-aware

### 8.1 Niente listino diretto sul padre

INSERT in `vendite.listini_righe` per articoli `is_composito = TRUE` e'
vietato (errore `E_LISTINO_RIGA_COMPOSITO_VIETATO`). Il prezzo padre
non e' un dato di listino ma una conseguenza della somma figli.

### 8.2 `vendite.listini_righe_componenti` — prezzo figli in contesto bundle

Tabella nuova, simmetrica a `<sorgente>_righe_componenti`. Una riga =
"in questa versione listino, il componente X del padre Y ha prezzo Z".

Vincoli (trigger guard):

- `articolo_componente_id` punta a riga BoM esistente e attiva
- `padre.is_composito = TRUE`
- IVA figlio = IVA padre: **non** verificata qui (Guard 5 rimosso il
  2026-06-03), gia' garantita alla sorgente dai trigger del §6
- `validita` listino ⊆ `validita` BoM ⊆ `validita` versione listino
- Immutabilita' v5: INSERT solo in versione non-attiva; UPDATE prezzo
  bloccato in versione attiva (pattern listini v5 esistente)

### 8.3 Resolver pricing v5 bundle-aware

`vendite.fn_resolve_prezzo_listino_v2` accetta nuovo parametro opzionale
`p_articolo_padre_contesto UUID DEFAULT NULL`:

- **NULL** → resolver standalone come oggi (STADIO 1-3 invariati)
- **NOT NULL** → STADIO 0 nuovo, prima di STADIO 1:
  1. Identifica `listino_versione_id` corrente per (BA, utility, data)
  2. Cerca in `listini_righe_componenti(versione, padre, figlio, data)`
  3. Se trovato → prezzo bundle + `origine = LISTINO_BUNDLE`
  4. Altrimenti → fallback a STADIO 1 standalone

I caller compositi (`fn_<sorgente>_riga_componenti_init`, `_preview`)
passano sempre `p_articolo_padre_contesto = riga.articolo_id`. Caller
standalone passano NULL → comportamento invariato.

## 9. Edge case

### 9.1 BoM vuota alla data
`is_composito = TRUE` ma nessuna riga `articoli_componenti` con
`validita @> data_documento` e `attivo = TRUE`: errore
`E_DOC_COMPOSITO_BOM_VUOTA` sollevato dalla fn `_init` al primo uso
del composito nel documento. Significa "articolo scaduto/non
configurato per questa data".

### 9.2 Compositi annidati (BoM ricorsiva)
Non gestiti dal modello attuale. Un figlio puo' a sua volta essere
`is_composito = TRUE`? Da definire. Soluzione pragmatica: VIETATO via
guard "figlio non puo' essere composito".

### 9.3 BoM contratto immutabile per documento (2026-05-13)

L'operatore non sceglie la composizione: **tutti** i figli BoM validi
alla data del documento finiscono nella riga con `attivo=TRUE` (default
fn `_init`). Il flag `obbligatorio` non determina piu' l'attivazione
iniziale (era `attivo = obbligatorio` fino al 2026-05-12). Conseguenze:

- L'operatore puo' modificare solo i **prezzi** dei componenti (con
  gating L1 `prezzo_override_manuale`); non puo' aggiungere ne'
  escludere componenti dalla riga.
- Il flag `obbligatorio` mantiene un solo significato runtime: **gate
  prezzo zero** (`script.trgfn_componenti_check_prezzo_obbligatorio`).
  Obbligatori non ammettono `prezzo_unitario = 0`; opzionali sì.
- UX FE: nessuna checkbox "attivo" nel Dialog/Panel componenti.
  Restano i tag info Obbligatorio/Opzionale + l'esposizione in fattura
  (fino al 2026-10-01 un tag In fattura Sì/No; dal 2026-10-01 i tre
  modi, con le etichette dal vocabolario).

### 9.4 Obbligatorio non disattivabile (safety net)

Trigger BEFORE UPDATE su `<sorgente>_righe_componenti`
(`script.trgfn_componenti_guard_obbligatorio`): se `OLD.attivo = TRUE`
e `NEW.attivo = FALSE` su un componente `obbligatorio = TRUE` → raise
`E_DOC_COMPONENTE_OBBLIGATORIO`. Dato il modello "BoM contratto
immutabile" (§9.3) la UI non emette mai questa transizione: il trigger
resta come safety net difensivo (es. UPDATE diretti via SQL, bug
futuri).

### 9.5 Promo articoli e contratti modalita' C
Interazione con prezzo bundle (STADIO 0):

- Promo articoli su componente: per default NON si applica nel
  contesto bundle (il bundle ha il suo prezzo). Override via flag
  `vale_in_contesto_padre BOOLEAN DEFAULT FALSE` su promo articoli.
- Contratto modalita' C (negoziazione puntuale BA-emittente): vince
  sempre sopra il prezzo bundle. E' negoziazione esplicita.

## 10. Catena propagazione documento → fattura

```
preventivi_righe + preventivi_righe_componenti
  -> (push commessa)
commesse_attivita (tutti i figli, niente filtro sull'esposizione)
  -> (run pipeline fatturazione)
attivita_fatturabili
  -> (generazione lotto)
fatture_righe (tutti i figli, ognuno col suo prezzo + kit_esposizione)
  -> (rappresentazione)
vw_fattura_righe_esposte (riga del kit + figli secondo il modo)
```

In ogni passaggio: tutti i componenti, col loro prezzo. L'esposizione
viaggia nel `meta` della commessa e si congela su `fatture_righe`
(`kit_esposizione`); la presentazione finale (fattura PDF / XML SDI /
portale) la applica leggendo `vw_fattura_righe_esposte` (§7).

## 11. Costanti / errori

Codici errore di dominio (registrati in `config.messaggi_errore`):

| Codice                                      | Quando                                                                                    |
| ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| `E_DOC_COMPOSITO_BOM_VUOTA`                 | `_init` su composito senza BoM valida alla data                                           |
| `E_DOC_COMPONENTE_OBBLIGATORIO`             | UPDATE `attivo=FALSE` su figlio obbligatorio                                              |
| `E_DOC_COMPONENTE_OBBLIGATORIO_PREZZO_ZERO` | Figlio obbligatorio con prezzo 0                                                          |
| `E_BOM_IVA_DISCORDANTE`                     | INSERT BoM, riattivazione legame, o UPDATE `articoli.iva_id` con IVA padre-figlio diversa |
| `E_LISTINO_RIGA_COMPOSITO_VIETATO`          | INSERT `listini_righe` per `is_composito=TRUE`                                            |
| `E_LISTINO_COMPONENTE_COERENZA_BOM`         | INSERT/UPDATE `listini_righe_componenti` con BoM/IVA/validita' incoerente                 |

## 12. Building block riusabili

Pattern simmetrico **da implementare** come componenti riusabili:

### 12.1 DB

- `script.trgfn_componenti_guard_coerenza_bom` — gia' esistente,
  parametrizzato via TG_ARGV. Riusato su 4 `*_righe_componenti` +
  esteso a `listini_righe_componenti` (5° caller, stesse verifiche
  meno propaga_qta)
- `script.trgfn_componenti_ricalcola_padre` — gia' esistente, usato
  su 4 `*_righe_componenti`. Non applicabile al listino (prezzo padre
  listino e' virtuale, non persistito)
- `script.trgfn_componenti_guard_obbligatorio` (nuovo) — su 4
  `*_righe_componenti`
- `script.trgfn_componenti_check_prezzo_obbligatorio` (nuovo) —
  parametrizzato, su 4 `*_righe_componenti`

### 12.2 BE Python

- Repository generico `ComponentiRepository` o classe base
  parametrizzata sul nome tabella sorgente
- Service generico `ComponentiService`
- Helper `_normalize_componenti_overrides` (gia' esistente nel
  service preventivi) — promuovere a helper condiviso

### 12.3 FE Vue

- `ComponentiDialog.vue` — Dialog modale 90vw, parametrizzato sul
  contesto (sorgente, articoloPadre, listinoVersione opzionale)
- `ComponentiPanel.vue` (EDIT) — tabella read/edit dei componenti
  esistenti, parametrizzato come Dialog; usato anche in modalita'
  `readonly=true` per preview contratti (righe bundle da listino)
- i18n condiviso `componenti.*` (sub-namespace cross-dominio,
  separato da `preventivi.componenti_*`)

### 12.4 Preview righe contratto — pattern uniforme con preventivi

A partire da 2026-05-16 il preview righe contratto adotta lo stesso
shape padre+figli dei preventivi:

- **DB**: `vendite.fn_contratto_righe_preview(contratto_id)` — ritorna
  tutte le righe (listino + AGGIUNTA) con `componenti jsonb` annidato.
  Pattern: riga padre con `is_composito=TRUE` ha `componenti` non-NULL;
  standalone ha `componenti=NULL`. `prezzo_finale` aggregato in DB.
- **BE**: thin wrapper (`cursor.execute("SELECT * FROM
  vendite.fn_contratto_righe_preview(%s)", [id])`) in
  `contratti_repository.list_righe_preview`.
- **FE**: `ContrattoRigheDrawer.vue` usa expander analogo a
  `PreventiviRigheTable.vue`; riusa `ComponentiPanel.vue` con
  `readonly=true` per la visualizzazione dei figli bundle.

Riferimento: [fn_contratto_righe_preview](/dbzero/vendite/manual/fn_contratto_righe_preview).

## 13. Riferimenti

- Iterazioni storiche: [changelog-decisioni-componenti.md](changelog-decisioni-componenti.md)
- Piano operativo 2026-05 (⛔ **storico, superato** — non usarlo per stimare):
  `docs/it/dev/work-done/refactor-componenti.md`
- Brief DB: `docs/it/dev/work-done/brief-db-componenti-modello-unificato.md`
- Modello tabelle: `docs/it/dbzero/catalogo/manual/articoli_componenti.md`
- Resolver pricing v5: `docs/it/dbzero/vendite/manual/fn_resolve_prezzo_listino_v2.md`
- Guida BoM: `docs/it/guide/gestione-listini.md` §6
