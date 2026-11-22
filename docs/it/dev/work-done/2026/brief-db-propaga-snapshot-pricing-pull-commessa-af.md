# Brief DB — Propagazione audit snapshot pricing v5 nella pull `commesse_attivita` → `attivita_fatturabili`

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> **Priorità**: 🟡 MEDIA — completa il fix BE "snapshot pricing v5 nel push".
> **Data**: 2026-06-15 · **Stato**: ✅ FATTO (2026-06-16)
>
> **Implementato dal team DB** con changeset
> `20260616-01-update-fn-emit-attivita-fatturabili-propaga-audit-pricing-mctit.yaml`
> (`runOnChange`, `CREATE OR REPLACE`, firma invariata): le 8 colonne audit sono
> aggiunte al `SELECT` del cursore, all'`INSERT` e al refresh del ramo `UPDATE`
> (riga non ancora fatturata), trasporto 1:1 con CHECK/FK speculari verificati.
> Audit pricing v5 ora end-to-end: push → `commesse_attivita` → `attivita_fatturabili`.
>
> **Origine**: roadmap [analisi-commesse-stato-e-sviluppi.md](analisi-commesse-stato-e-sviluppi.md)
> §4.3 #2 / §8 #4. Lato BE è stata cablata la popolazione degli 8 campi audit su
> `commesse_attivita` (via `PricingService`, vedi `commesse_source_handlers.py`).
> Resta da propagarli a valle: la fn di pull oggi **non li copia**.

---

## 1. Contesto

Il modello "snapshot pricing v5" prevede 8 colonne audit di **derivazione del prezzo**,
presenti sia su `vendite.commesse_attivita` sia su `vendite.attivita_fatturabili`:

| Colonna | Tipo |
|---|---|
| `prezzo_base_snapshot` | numeric |
| `origine_prezzo` | varchar (CHECK) |
| `tipo_variazione_applicata` | varchar (CHECK) |
| `valore_variazione_applicata` | numeric |
| `promo_id` | bigint (FK) |
| `contratto_id` | bigint (FK) |
| `categoria_cliente_id_snapshot` | smallint (FK) |
| `classe_utenza_id_snapshot` | integer (FK) |

Dal 2026-06-15 il **push** popola queste colonne su `commesse_attivita` (prima erano
sempre `NULL`). La fonte è il resolver `fn_resolve_prezzo_listino_v2`, invocato best-effort
al push; il `prezzo_snapshot` negoziato resta autoritativo (non sovrascritto).

## 2. Problema

La fn di pull **`vendite.fn_emit_attivita_fatturabili_da_commessa`** (rev 2026-06-07)
copia da `commesse_attivita` ad `attivita_fatturabili` molte colonne (articolo, uom,
quantità, competenza, `prezzo_snapshot`, `meta`, …) **ma non gli 8 campi audit**:

- il cursore sorgente (`SELECT ca.id, ca.segment_key, … ca.prezzo_snapshot,
  ca.prezzo_bloccato, ca.stato_approvazione, ca.meta, …`) **non li seleziona**;
- l'`INSERT INTO vendite.attivita_fatturabili (...)` **non li valorizza** (restano i
  default NULL della tabella);
- idem nel ramo `UPDATE` (resume riga non ancora fatturata).

→ Conseguenza: anche col push corretto, le 8 colonne su `attivita_fatturabili`
rimangono `NULL`. L'audit prezzo **si interrompe a `commesse_attivita`** e non
raggiunge il livello di emissione (l'obiettivo §4.3 #2 "audit fino alla fattura"
non è soddisfatto end-to-end).

## 3. Cosa serve

Aggiornare `fn_emit_attivita_fatturabili_da_commessa` (nuovo changeset `runOnChange`
con numerazione successiva — **mai** modificare YAML mergiati, def corrente dalla doc
auto-gen) perché **trasporti gli 8 campi audit** da `commesse_attivita`:

1. aggiungere le 8 colonne al `SELECT` del cursore (`ca.prezzo_base_snapshot`,
   `ca.origine_prezzo`, `ca.tipo_variazione_applicata`, `ca.valore_variazione_applicata`,
   `ca.promo_id`, `ca.contratto_id`, `ca.categoria_cliente_id_snapshot`,
   `ca.classe_utenza_id_snapshot`);
2. valorizzarle nell'`INSERT INTO vendite.attivita_fatturabili (...)`;
3. nel ramo `UPDATE` (resume): decidere se **rinfrescarle** dalla commessa o lasciarle
   immutate. *Raccomandazione*: allinearle alla riga commessa come per `prezzo_unitario`/
   `prezzo_snapshot` (coerenza dello snapshot di emissione finché non è `fatturato`).

Attenzione ai **CHECK** (`chk_attivita_fatturabili_origine_prezzo`,
`chk_attivita_fatturabili_tipo_variazione_applicata`) e alle **FK** (promo, contratto,
categoria, classe): i valori provenienti da `commesse_attivita` rispettano già gli stessi
CHECK/FK (colonne speculari), quindi il trasporto è 1:1; verificare comunque che i CHECK
delle due tabelle siano allineati (stessi enum ammessi).

## 4. Criterio di accettazione

- Una commessa con righe approvate e audit valorizzato → dopo
  `fn_emit_attivita_fatturabili_da_commessa` le 8 colonne su `attivita_fatturabili`
  riflettono i valori della riga `commesse_attivita` di origine (no più NULL).
- Re-run idempotente: la riga già emessa non duplica; il ramo UPDATE applica la policy
  scelta al punto 3 senza violare CHECK/FK.
- pgTAP: estendere il test della pull con asserzioni sulle 8 colonne propagate.

## 5. Fuori scope (nota di modello, da confermare)

`vendite.fatture_righe` **non ha** queste colonne audit: l'ancora di audit del prezzo è
`attivita_fatturabili` (snapshot di emissione immutabile, collegato alla riga fattura via
la relazione lotto/fattura). **Proposta**: lasciare `fatture_righe` senza colonne audit
(la riga fiscale porta prezzo finale + IVA; la derivazione resta interrogabile su
`attivita_fatturabili`). Se invece il modello richiede l'audit anche sulla riga fiscale,
serve un brief separato (DDL `fatture_righe` + `FattureRigheService`). Confermare la
scelta lato DB/modello.
