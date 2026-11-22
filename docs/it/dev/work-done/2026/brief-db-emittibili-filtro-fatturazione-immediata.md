# Brief DB — Filtro `fatturazione_immediata` nella discovery commesse emittibili

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* serve e *perché*; **non contiene DDL pronto** — il *come* (firma,
> nome parametro, changeset) è scelta del team DB.
>
> **Data**: 2026-06-15 · **Stato**: ✅ **IMPLEMENTATO** (2026-06-15) — `fn_list_commesse_emittibili`
> accetta `p_fatturazione_immediata boolean DEFAULT NULL` ed espone la colonna; pushato
> su `dev/db-tid`, pgTAP verde. Decisione §4: mappatura corsia→filtro lato BE (il driver
> mette il flag nel `meta` del lotto, il pull lo propaga). Lato BE: F3 completata.
>
> **Origine**: [analisi-commesse-stato-e-sviluppi.md §10](analisi-commesse-stato-e-sviluppi.md),
> Fase 3 del driver di orchestrazione fatturazione. Seguito di
> [brief-db-pipeline-pull-commessa-seed.md](brief-db-pipeline-pull-commessa-seed.md)
> (già implementato).
>
> **Prerequisito di**: il **management command** della Fase 3 (corsie immediata /
> differita) e la corsia **near-real-time** della Fase 4. Senza questo filtro la Fase 3
> resta in attesa (decisione di prodotto: "prima il brief DB, poi F3").

---

## 1. Contesto e problema

Il driver avrà **due corsie**, distinte dal flag `fatturazione_immediata` sulla testata
commessa (che è anche elemento della chiave di deduplicazione in
`fn_get_or_create_commessa`, quindi commesse immediate e differite **non si mescolano
mai** nella stessa commessa):

- **immediata** (`fatturazione_immediata = true`): fatturata **subito**, corsia
  near-real-time (lotto `GIORNALIERO`);
- **differita** (`fatturazione_immediata = false`): fatturata in **batch mensile** per
  competenza (lotto `MASSIVO`).

**Problema**: la discovery degli emittibili — `vendite.fn_list_commesse_emittibili`,
usata dallo step di **pull** (`_handle_pull_attivita_da_commessa_task`) — **non filtra
né espone `fatturazione_immediata`**. Filtra solo competenza, billing account, utility,
emittente.

**Conseguenza**: entrambe le corsie pescano lo **stesso** insieme di commesse
emittibili. La corsia immediata, girando di frequente, **emetterebbe in anticipo anche
le commesse differite**. Non c'è doppia fatturazione (il pull è idempotente e blocca le
AF già fatturate), ma la commessa differita verrebbe **fatturata troppo presto**:
violazione della semantica delle due corsie.

---

## 2. Cosa serve (risultato atteso)

La discovery degli emittibili deve poter **distinguere le commesse per
`fatturazione_immediata`**, così che:

- un pull della corsia **immediata** selezioni **solo** commesse `fatturazione_immediata = true`;
- un pull della corsia **differita** selezioni **solo** commesse `fatturazione_immediata = false`;
- l'assenza di filtro (comportamento attuale) resti possibile e **invariata**
  (retro-compatibilità: nessun filtro = tutte le commesse, come oggi).

In pratica:

- `vendite.fn_list_commesse_emittibili` deve accettare un **filtro opzionale** su
  `fatturazione_immediata` (3 stati: solo immediate / solo differite / indifferente),
  e — utile per diagnostica — **esporre** il valore in output.
- Il *come* (nome/posizione del parametro, tipo `boolean NULL`, ecc.) è scelta del team
  DB. Nota: la funzione già accetta `p_emittente_soggetto_ruolo_id` pur non essendo nel
  doc concettuale: il nuovo filtro è analogo.

> **Lato BE** (fuori scope DB): il pull handler passerà il valore del filtro derivandolo
> dalla **corsia/`tipo_lotto`** del lotto (`GIORNALIERO` → immediate=true; `MASSIVO` →
> immediate=false). Vedi §4, decisione da confermare.

---

## 3. Criteri di accettazione

- Con due commesse emittibili per lo stesso perimetro/competenza, una
  `fatturazione_immediata=true` e una `false`:
  - discovery filtrata "solo immediate" → restituisce **solo** la prima;
  - discovery filtrata "solo differite" → restituisce **solo** la seconda;
  - discovery senza filtro → restituisce **entrambe** (come oggi).
- Nessuna regressione sui filtri esistenti (competenza/BA/utility/emittente).
- Copertura pgTAP coerente con lo stile dei test commesse/pipeline.

---

## 4. Decisione da concordare (DB + Tid)

- **Mappatura corsia → filtro**: si assume `GIORNALIERO ⇔ fatturazione_immediata=true`
  e `MASSIVO ⇔ false`? È la convenzione del modello a due corsie. Se sì, il BE deriva il
  filtro dal `tipo_lotto` del lotto e lo passa alla discovery; il DB deve solo offrire il
  parametro. Se si preferisce che sia il **lotto** a portare esplicitamente il flag (es.
  colonna su `fatturazione_lotti`), indicarlo: cambia chi decide il filtro.

---

## 5. Fuori scope (BE, Fase 3/4 — dopo questo brief)

- Management command `run_fatturazione_batch` (discovery per emittente → lotto per
  emittente → `run_lotto_until_done`, best-effort, dry-run): **solo BE**.
- Wiring del filtro nel pull handler (derivazione da `tipo_lotto`): **solo BE**.
- Scheduler/timer (systemd/cron), niente pgAgent: **solo BE/infra**.
