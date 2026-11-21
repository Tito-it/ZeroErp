# Brief DB — Deprecabilità del catalogo: svincolare la configurazione dalle istanze eseguite

> **Tipo**: brief DB (cosa serve, non come) · **Destinatario**: team DB (`dev/db-tid`)
> **Priorità**: 🟠 media-alta (abilitante per la produzione) · **Data**: 2026-06-30 · **Stato**:
> 🟢 **CHIUSO — P1 (colonna `obsoleto_dal`), guard NON toccato.** Implementato + applicato a DB
> (`20260630-01/02`), **pgTAP verde**; `automation_fk_exclusions` → doc allineata (opzione b, non
> era una regressione). La Proposta A (rilassare il guard) è **superata** — vedi §0/§4.

---

## 0. Decisione finale (2026-06-30): P1 — asse `obsoleto_dal`, NON rilassare il guard

La deep-dive aveva proposto di **rilassare il guard** (Proposta A: i figli senza `attivo` non
bloccano). **Superata** dopo la revisione di correttezza di Tid: `attivo=false` su un dato
**referenziato** è *legittimamente* pericoloso (i consumatori filtrano per `attivo` → romperebbe
le pratiche/IVA/documenti esistenti) e il guard fa **bene** a bloccarlo. Il guard resta com'è.

Radice vera: `attivo` schiaccia due concetti — **"riferimento valido"** (serve alle istanze
esistenti) e **"selezionabile per il nuovo"**. "Ritirare una config" è il secondo. → si separa
l'asse con una **DATA** dedicata:

- **`obsoleto_dal date NULL`** su `tipi_prestazione` e `template_flussi` (`20260630-01`):
  NULL = selezionabile; `<= oggi` = ritirato; `> oggi` = ritiro programmato.
- **Selezione-per-il-nuovo** (BE): `... AND attivo AND (obsoleto_dal IS NULL OR obsoleto_dal > CURRENT_DATE)`.
- **Letture storiche**: non filtrano `obsoleto_dal` → vedono sempre il loro tipo/template.
- Ritiro 9002/9003 = `obsoleto_dal = oggi` (`20260630-02`), **senza** `attivo=false`, guard mai
  sfiorato, nessun delete, storia intatta.

Vantaggi vs booleano: registra **quando** è cessato l'uso (audit) e consente il **ritiro
programmato**. Il resto del brief (§1–§3ter) resta come **razionale** del perché NON toccare il
guard.

**`automation_fk_exclusions` — chiuso (2026-06-30): NON era una regressione.** Indagando si è
visto che il filtro è stato **disattivato di proposito** in `20260113-01` (commento "non più
utilizzato") e non re-introdotto nel rewrite `20260408-06`. Quindi il codice è **intenzionale**;
era la **doc** a essere stantia. Decisione (opzione **b**): **allineata la documentazione**
(manuale `automation_rules_tbl` + `fn_run_automations_attivo` + guida `automazione-db.md` §1.3)
a dichiarare il filtro **inerte**. **Non** ripristinato (P1 non lo richiede; la tabella resta
vuota/inerte). Riabilitarlo resta possibile in futuro se emergesse un caso d'uso
catalogo→catalogo.

---
>
> **Origine**: ritiro del tipo pratica `PREVENTIVI_IMMEDIATA/DIFFERITA` (vedi
> [brief-db-pratica-preventivi-tipo-unico-flussi.md](brief-db-pratica-preventivi-tipo-unico-flussi.md))
> bloccato in apply dal guard `dbops.trgfn_prevent_deactivate_if_children`. Generalizza il
> problema oltre pratiche.

---

## 1. Problema (e perché è di produzione)

Il guard `dbops.trgfn_prevent_deactivate_if_children` impedisce `attivo TRUE→FALSE` su un
**padre di catalogo** se esistono figli collegati. Comportamento attuale:

- figlio **con** `attivo` → blocca solo se esistono figli **attivi** (corretto: consistenza
  del catalogo attivo);
- figlio **senza** `attivo` → blocca alla **sola esistenza** di una riga.

Il secondo caso rende **impossibile deprecare una configurazione** (tipo pratica, template
flusso, …) una volta che è stata **usata**, perché le **istanze eseguite** (`pratiche`,
`flussi`, `fatture`, `ordini`…) **non hanno `attivo`** (sono entità a **stato**, non flag) →
la loro sola esistenza blocca per sempre la deprecazione del catalogo, a meno di **cancellare
la storia**. In produzione è inaccettabile: servirà regolarmente *"questo tipo/flusso non si
usa più per il nuovo, ma le pratiche già fatte restano"*.

**Principio violato**: la **configurazione** (catalogo, deprecabile via `attivo`) deve essere
**svincolata** dalle **istanze eseguite** (storiche, governate dal loro `stato`). Un padre
disattivato = *non selezionabile per il nuovo*; le istanze esistenti continuano a referenziarlo
(ciclo di vita normale, nessuna incoerenza del catalogo attivo).

## 2. Audit (riscontro reale, 2026-06-30)

`prevent_deactivate_if_children` è cablato su **molte** relazioni; ~75 tabelle-figlie **senza
`attivo`** vi compaiono. Due famiglie:

- **Istanze eseguite** (mai bloccare): `pratiche`, `flussi`, `fatture`, `fatture_righe`,
  `ordini`, `contratti`, `commesse`, `commesse_attivita`, `attivita_fatturabili`, `ddt`,
  `preventivi`, `offerte_commerciali`, `documenti_generati`, `movimenti`, `inventari`,
  `note_*`, `allegati_*`, `pratiche_sorgenti`, `calcoli_tempo`, … → la loro esistenza **non
  deve** bloccare la deprecazione del catalogo.
- **Satelliti di configurazione senza `attivo`** (es. `transizioni_stati_*`,
  `template_flussi_prerequisiti`, `profili_accesso_aree/azioni`, `user_override_*`): "muoiono"
  col padre, non rappresentano un'incoerenza del catalogo attivo.

In nessuno dei due casi un padre **inattivo** crea un'incoerenza del **catalogo attivo** (gli
oggetti inattivi sono filtrati ovunque). Quindi bloccare sulla loro esistenza è errato.

## 2bis. Come funziona l'automazione ATTIVO (approfondimento 2026-06-30)

I trigger BLOCK/REQUIRE **non sono cablati a mano**: li genera la regola **ATTIVO** del
framework `dbops` via `fn_run_automations_attivo` (guida `automazione-db.md` §4.2). Riscontri
dal codice vivo, rilevanti per la scelta:

- **Job notturno** (pgAgent, 21:00) ri-esegue `fn_run_automations_attivo` con
  **`reconcile_on_change=true`** → ogni notte **droppa e ricrea** i trigger BLOCK e REQUIRE per
  ogni FK eleggibile. ⇒ **un drop manuale del trigger NON è durevole** (rigenerato).
- **Le exclusions oggi NON sono applicate**: `dbops.automation_fk_exclusions` esiste (vuota) e
  il manuale dichiara che la regola la filtra, ma la **funzione viva** `fn_run_automations_attivo`
  **non la consulta** (filtro perso in un refactor). ⇒ "bypassare via exclusions" richiederebbe
  prima **ripristinare** quella feature, e comunque combattere il reconcile.
- La regola genera anche il trigger **REQUIRE** sul figlio (`child_requires_active_parent`,
  `AFTER INSERT OR UPDATE OF <fk>`): blocca la **creazione di nuove** istanze sotto un padre
  inattivo — **comportamento voluto** ("non selezionabile per il nuovo"). Le istanze esistenti,
  che non cambiano la FK, non sono toccate.

**Implicazione sulla scelta**: la via che **non tocca l'orchestratore** (e quindi non rischia di
rompere il framework né viene annullata dal job notturno) è cambiare **solo** la trgfn condivisa
(Proposta A). Le altre vie (drop manuale, exclusions) o non sono durevoli o richiedono di
resuscitare codice perso.

## 3. Proposta

### A — Fix a livello di funzione (RACCOMANDATA, e confermata dall'approfondimento)

Modificare `dbops.trgfn_prevent_deactivate_if_children` così che **i figli senza colonna
`attivo` NON blocchino mai**; il blocco scatta **solo** su figli che **hanno `attivo` e sono
attivi**.

- Regola unica e leggibile: *"non disattivare un padre finché esistono figli-catalogo ATTIVI
  che lo userebbero"*. Istanze e satelliti senza `attivo` → ignorati (storia/lifecycle).
- Risolve **tutto** in un colpo (pratiche + ogni dominio) e in modo coerente.
- Ricaduta sul ritiro pratiche: deprecare un tipo diventa `attivo=false` (i template attivi si
  disattivano prima — hanno `attivo`; le pratiche/flussi eseguiti non bloccano più). Nessun
  delete, storia preservata.
- **Blast radius**: la funzione è usata da ~150 wiring → cambio di comportamento globale.
  Mitigazione: §4 (audit mirato + pgTAP).

### B — Svincolo mirato / exclusions (SCARTATA dall'approfondimento)

Le vie "mirate" non reggono ai riscontri §2bis:
- **Drop dei trigger** catalogo→istanza (es. `trg_tipi_prestazione_a10_pratiche_block_deact_upd`):
  **non durevole** — il job notturno con `reconcile_on_change` li **ricrea**.
- **`automation_fk_exclusions`**: la funzione viva **non le consulta** → andrebbe prima
  ripristinato il filtro nell'orchestratore (codice perso), e gestito l'orfano lasciato dal
  reconcile. Più lavoro e più rischio della Proposta A, su un orchestratore complesso.

→ Scartata: o non dura, o richiede di toccare l'orchestratore (proprio ciò che vogliamo evitare).

**Raccomandazione**: **A**. È la regola corretta ("config svincolata dalle istanze"), la fa una
volta sola, e — cruciale — **non tocca l'orchestratore né il job notturno** (resta tutto com'è;
cambia solo cosa fa la trgfn condivisa quando il figlio non ha `attivo`).

## 3ter. Esito audit D2 (2026-06-30) — ✅ relazione relax SICURA

Estratte **152 coppie** padre→figlio della regola ATTIVO dove il **figlio non ha `attivo`**.
Tutte ricadono in 3 famiglie, **nessuna richiede il blocco-su-esistenza**:

- **Istanze/documenti** (la maggioranza): `fatture`, `ordini`, `contratti`, `preventivi`,
  `offerte`, `pratiche`, `flussi`, `commesse(_attivita)`, `attivita_fatturabili`, `ddt`,
  `movimenti`, `inventari`, `documenti_generati`, `*_righe`, `*_componenti`, `note_*`,
  `allegati_*`, `fatturazione_lotti*`… → riferimenti storici/lifecycle; il padre inattivo è
  solo "non più usabile".
- **Associazioni/scope**: `profili_accesso_aree/azioni`, `user_override_*`,
  `user_emittenti_fiscali`, `tipi_doc_fiscale_registri`, `documenti_fatturazione_canali`,
  `soggetti_conti_bancari`… → inerti col padre inattivo.
- **Dettagli di entità master**: `soggetti → contatti / dati_societari / indirizzi_soggetti /
  soggetti_ruoli`, `iva/termini_pagamento/pdp → clienti`, `magazzini → inventari/rettifiche`…

**Conclusione**: il blocco-su-esistenza per figli senza `attivo` non solo è inutile, è
**attivamente sbagliato** — oggi rende impossibile, ad es., soft-deletare un `soggetto` con un
contatto, o ritirare un'aliquota `iva` mai più voluta usata da un cliente. Il **REQUIRE** resta
la guardia corretta ("niente nuovi riferimenti a padre inattivo"). → **Proposta A confermata
sicura. Nessun caso richiede un guard dedicato** (domanda D2 chiusa: nessuno).

## 4. Esito finale — cosa è stato fatto (P1, non A)

> La **Proposta A** (rilassare il guard, §3) è stata **superata**: `attivo=false` su dato
> referenziato è pericoloso (revisione di Tid), il guard resta **com'è**. Soluzione adottata =
> **P1 (asse `obsoleto_dal`)**, §0. L'audit D2 (§3ter) resta valido come prova che il guard NON
> va rilassato.

| Item | Stato | Artefatto |
| --- | --- | --- |
| **P1-DB1** — colonna `obsoleto_dal date` su `tipi_prestazione` + `template_flussi` | ✅ scritto + **applicato** | `00_schema/pratiche/20260630-01-...` |
| **P1-DB2** — ritiro 9002/9003 + loro template via `obsoleto_dal=oggi` (per codice, idempotente) | ✅ scritto + **applicato** | `80_data/changelog/20260630-02-...` |
| **pgTAP** — colonna/tipo, 9002/9003 obsoleti+`attivo=true`, 9004 selezionabile, predicato selezione | ✅ **VERDE** | `db/pgtap/pratiche/test-obsoleto-dal-catalogo-v1.sql` |
| **Audit D2** — 152 coppie no-`attivo`, nessuna deve bloccare | ✅ fatto (§3ter) | — |
| **`automation_fk_exclusions`** | ✅ **opzione b**: doc allineata (NON era una regressione, vedi §0) | manuale `automation_rules_tbl` + `fn_run_automations_attivo` + guida `automazione-db.md` §1.3 |
| ~~D1 (rilassare il guard)~~ | ❌ **NON fatto** — Proposta A superata da P1 | — |

**Resta al BE** (fuori scope DB): nelle query di **selezione per il nuovo** aggiungere
`AND (obsoleto_dal IS NULL OR obsoleto_dal > CURRENT_DATE)`; le letture storiche invariate.
*(Opzionale, DB-first)* guard che vieta di creare pratiche/flussi di un tipo/template già
obsoleto — difesa in profondità, non implementato.

## 5. Conseguenze a valle (chiuse)

- Ritiro di `PREVENTIVI_IMMEDIATA/DIFFERITA` (9002/9003): via `obsoleto_dal` (niente
  `attivo=false`, niente delete, niente cleanup manuale, guard mai sfiorato).
- Pattern `obsoleto_dal` **riutilizzabile** in ogni dominio per "configurazione morta, istanze
  preservate" (memoria `reference_deprecabilita_catalogo_obsoleto_dal`).

## 6. Stato decisioni (finale)

1. **Approccio**: ✅ **P1 (`obsoleto_dal`)**. La Proposta A (rilassare il guard) è **superata**:
   il guard è corretto e resta intatto (§0).
2. **Figlio no-`attivo` che deve bloccare?** ✅ Nessuno (audit D2) — ma irrilevante per P1, che
   non disattiva il padre.
3. **`automation_fk_exclusions`**: ✅ **opzione b** — **non** era una regressione (disattivata
   apposta in `20260113-01`, "non più utilizzato"); **doc allineata**, filtro **non**
   ripristinato. Riabilitabile in futuro se servisse.
4. **Creare nuove istanze su padre inattivo**: coperto dal trigger **REQUIRE** (generato dalla
   regola ATTIVO) — nessun lavoro extra.
