# Brief DB — `fn_reconcile_sorgente`: il tie-break `flusso_id` esclude il milestone in attesa

> **Tipo documento**: brief operativo **per il team DB** (canale `dev/db-tid`).
> Spiega *cosa* è rotto e *perché*, con una proposta di correzione; il *come*
> definitivo (forma SQL, changeset, numerazione) è scelta del team DB.
>
> **Data**: 2026-07-08 · **Stato**: 🟥 DA FARE — bug logico del modello,
> riproducibile su dbdev (pratica `PRA-0000802`). Nessun dato di produzione:
> i dati di test sono rigenerabili, non serve backfill/sblocco.
>
> **Origine del difetto**: interazione tra
> [brief-db-aggancio-documento-flusso.md](../work-done/brief-db-aggancio-documento-flusso.md)
> (2026-06-16, introduce `pratiche_sorgenti.flusso_id` come **ancora d'origine**) e
> [brief-design-proiezione-stato-dominio.md](brief-design-proiezione-stato-dominio.md)
> / GUIDA D4 (2026-07-07, introduce `fn_reconcile_sorgente` che **riusa** quella
> colonna come tie-break del milestone *in attesa*).
>
> **Oggetto DB**: `pratiche.fn_reconcile_sorgente(bigint, text)`
> ([doc auto-gen](../../dbzero/pratiche/funzioni/fn_reconcile_sorgente.md)).

---

## 1. Sintomo osservato

Pratica preventivo (`PRA-0000802`). L'operatore accetta il preventivo dal percorso
pratica («approvazione cliente», esito POSITIVO). Il preventivo passa a **ACCETTATO**
correttamente, ma il milestone `APPROVAZIONE_CLIENTE` **non avanza a COMPLETATO**: la
UI continua a proporre l'azione «Accetta/Rifiuta», e ogni riclick ritenta la
transizione vietata **ACCETTATO → ACCETTATO**, che la matrice
`config.transizioni_stati_preventivi` respinge (`PREV_TRANSIZIONE_NON_AMMESSA` →
l'app mostra `E_DATABASE`, request_id `866aed37-...`).

Il crash a valle è solo un effetto: la vera anomalia è il **milestone che resta
indietro** perché la riconciliazione non lo trova.

## 2. Ripro concreto (dbdev, `PRA-0000802` = pratica id 879)

Preventivo ROOT collegato = `PRV0000181` (id 500), uid
`019f3e1a-1e97-7a8a-a138-cdec78b07f80`, tipo sorgente PREVENTIVO = **2**.

| Milestone (`pratiche.flussi`) | template | stato | esito | `attende_sorgente_tipo_id` |
|---|---|---|---|---|
| 1195 | `RICHIESTA_CLIENTE` | COMPLETATO | POSITIVO | — |
| 1196 | `PREVENTIVAZIONE` | COMPLETATO | POSITIVO | NULL |
| **1197** | **`APPROVAZIONE_CLIENTE`** | **DA_ESEGUIRE** | — | **2 (PREVENTIVO)** |

Fatti verificati:

- `vendite.preventivi` id 500 → stato **ACCETTATO** (aggiornato 2026-07-07 19:43).
- `pratiche.fn_stato_sorgente(2, uid)` → `esito = POSITIVO`, `terminale = false`
  (il descrittore proietta il verdetto correttamente).
- Binding presente e attivo: `pratiche.template_flussi_avanzamento_proiezione`
  id 1 → `template_flusso_id = 9011` (`APPROVAZIONE_CLIENTE`), `attivo = true`,
  `esito_richiesto = NULL` (matcha qualunque verdetto).
- **`pratiche.reconcile_errori`**: nessuna riga per l'uid → la riconciliazione **non
  ha sollevato**: è semplicemente uscita con 0 milestone avanzati.
- **`pratiche_sorgenti`**: 1 sola riga ROOT (id 252), `flusso_id = 1196`
  (`PREVENTIVAZIONE`), **non** 1197.

## 3. Causa radice — le due anime di `pratiche_sorgenti.flusso_id`

`pratiche_sorgenti.flusso_id` ha **un valore solo** ma serve **due scopi**, che
collidono quando il milestone d'origine ≠ il milestone in attesa:

1. **Ancora d'origine** (brief 2026-06-16): il ROOT è ancorato al **flusso che ha
   generato** il documento — per il preventivo è `PREVENTIVAZIONE` (azione UI
   `APRI_PREVENTIVO`). Alimenta l'auto-completamento di PREVENTIVAZIONE
   all'emissione (`get_flusso_id_by_preventivo_root` →
   `_completa_flusso_preventivazione`). **È corretto che punti a 1196.**

2. **Tie-break della riconciliazione (D-B5)**: `fn_reconcile_sorgente` usa quella
   stessa `flusso_id` come restringimento per individuare il milestone **in attesa**
   del verdetto:

   ```sql
   -- presente sia nel conteggio candidati (~riga 75) sia nel loop di
   -- avanzamento (~riga 110) di fn_reconcile_sorgente:
   AND (r_ps.flusso_id IS NULL OR f.id = r_ps.flusso_id)
   ```

Con `flusso_id = 1196` il predicato `AND f.id = 1196` si intreccia con il filtro
`tf.attende_sorgente_tipo_id = 2 AND stato NOT IN (COMPLETATO, ANNULLATO)`: il flusso
1196 attende NULL (non 2) ed è già COMPLETATO → **non è candidato**; il milestone
1197 (l'unico che attende PREVENTIVO) viene **escluso** perché `1197 ≠ 1196`.
Risultato: **0 candidati**, `RETURN 0`, milestone bloccato.

Nota storica: la colonna `flusso_id` (2026-06-16) precede il motore di
riconciliazione D4 (2026-07-07). Il D4 ha **riusato** l'ancora d'origine come se
fosse il puntatore al milestone in attesa. Le due semantiche coincidono solo nei
template dove **lo stesso** milestone genera e attende il documento — ed è il caso
che l'E2E "verde" del D4 esercitava, mascherando il difetto. Nel template preventivo
realistico (`PREVENTIVAZIONE` genera, `APPROVAZIONE_CLIENTE` attende) sono milestone
distinti e il difetto emerge sempre.

**Impatto**: ogni pratica preventivo con template che separa preventivazione e
approvazione cliente. L'auto-avanzamento del milestone all'accettazione (perno della
GUIDA D4) di fatto **non funziona** in quei template.

## 4. Cosa serve (risultato atteso)

Il tie-break `flusso_id` deve essere una **preferenza tra i candidati che attendono
davvero** questo tipo di sorgente, **non** un filtro che può svuotare l'insieme.
Regola: applica `f.id = flusso_id` **solo se** quel flusso è esso stesso un
candidato-attesa; se il link punta al flusso d'**origine** (che non attende questo
tipo), **ignoralo** e riconcilia i milestone in attesa.

Proposta SQL (forma suggerita — il team DB sceglie quella definitiva), da applicare
**identica** nel conteggio candidati e nel loop di avanzamento:

```sql
AND (
    r_ps.flusso_id IS NULL
    OR f.id = r_ps.flusso_id
    -- Link ancorato al flusso d'ORIGINE (es. PREVENTIVAZIONE), che NON attende
    -- questo tipo di sorgente: il tie-break D-B5 non si applica → si riconciliano
    -- i milestone in ATTESA (es. APPROVAZIONE_CLIENTE). Il restringimento vale
    -- solo se il flusso linkato è esso stesso un candidato-attesa (disambiguazione
    -- multi-istanza dello stesso step, motivo per cui D-B5 esiste).
    OR NOT EXISTS (
        SELECT 1
          FROM pratiche.flussi f_link
          JOIN pratiche.template_flussi tf_link
            ON tf_link.id = f_link.template_flusso_id
         WHERE f_link.id = r_ps.flusso_id
           AND tf_link.attende_sorgente_tipo_id = p_sorgente_tipo_id
    )
)
```

**Dettaglio collegato — guardia di ambiguità (~riga 85).** Oggi è
`IF r_ps.flusso_id IS NULL AND v_cand_count > 1`. Con la modifica sopra, un link
d'origine (non usabile come tie-break) con più candidati in attesa NON verrebbe più
intercettato dalla guardia. Va allineata allo stesso concetto: sostituire "link IS
NULL" con "**link non usabile come tie-break**", cioè:

```sql
-- link_usabile := (flusso_id IS NOT NULL AND esiste un candidato-attesa con id = flusso_id)
IF NOT link_usabile AND v_cand_count > 1 THEN
    -- log E_RECONCILE_AMBIGUO su pratiche.reconcile_errori e CONTINUE (invariato)
```

Consiglio di introdurre `link_usabile` come booleano calcolato una volta per
iterazione `r_ps` (un `EXISTS` sul flusso linkato che attende `p_sorgente_tipo_id`) e
riusarlo sia nel tie-break sia nella guardia, per non duplicare la subquery.

## 5. Criteri di accettazione (comportamentali)

Dopo il fix, con `fn_reconcile_sorgente(2, uid)` innescato dal cambio stato del
preventivo:

1. **Origine ≠ attesa** (caso rotto, `PRA-0000802`): preventivo → ACCETTATO ⇒
   `APPROVAZIONE_CLIENTE` (1197) passa a **COMPLETATO** con `esito = POSITIVO`;
   `fn_reconcile_sorgente` ritorna 1.
2. **Origine = attesa** (template semplice, no regressione): il milestone che genera
   *e* attende si completa come prima.
3. **Un solo milestone in attesa + link d'origine**: avanza (nessun falso
   `E_RECONCILE_AMBIGUO`).
4. **Due milestone in attesa + link d'origine** (non usabile): la guardia di
   ambiguità scatta → riga in `pratiche.reconcile_errori`, nessun avanzamento "a
   indovinare".
5. **Due istanze dello stesso step in attesa + link che punta a una di esse**
   (D-B5 legittimo): avanza **solo** quella indicata.
6. **Nessun verdetto** (es. preventivo EMESSO): nessun avanzamento (invariato).

## 6. Copertura pgTAP (stile test pratiche esistenti)

Nuovo file suggerito `db/pgtap/pratiche/test-reconcile-tie-break-flusso-origine.sql`,
un caso per ciascun criterio §5 (in particolare i casi 1, 4, 5 sono quelli che il fix
cambia). Ogni test: seed pratica + flussi + `pratiche_sorgenti` + binding, chiamata a
`fn_reconcile_sorgente`, assert su `pratiche.flussi.stato_id/esito` e sul valore di
ritorno (n. milestone avanzati), il tutto in transazione con rollback.

## 7. Decisioni da concordare (DB + Tid)

- **Ambito della fix**: la correzione §4 è **localizzata** a `fn_reconcile_sorgente`
  (nuovo changeset `runOnChange` con numerazione successiva, corpo copiato dalla
  doc auto-gen viva + modifica sopra). È l'opzione consigliata perché minimale e
  retro-compatibile.
- **Domanda di modello più profonda** (non bloccante per la fix): dato che
  `flusso_id` è *per definizione* l'ancora d'**origine**, è il disambiguatore giusto
  per la riconciliazione? Alternative da valutare a mente fredda: (a) un puntatore
  distinto "milestone in attesa" sul link; (b) la riconciliazione si affida solo a
  `attende_sorgente_tipo_id` + binding + guardia ambiguità, senza tie-break su
  `flusso_id`. La fix §4 è compatibile con entrambe come passo intermedio sicuro.

## 8. Fuori scope (BE/FE — dopo/indipendenti dal fix DB)

Migliorie difensive emerse durante la diagnosi, **non** causa del bug, da valutare
separatamente:

- **BE** `vendite.preventivi_service.cambia_stato`: un re-invio accidentale di
  accettazione su preventivo già ACCETTATO oggi degenera in `E_DATABASE` opaco
  (auto-transizione respinta dalla matrice). Defense-in-depth: intercettare il caso
  e rispondere in modo parlante/idempotente. Secondario: col fix DB il milestone si
  completa e la UI non ripropone più l'azione.
- **FE** `FlussoDrawer.vue`: il picker «Accetta/Rifiuta» è gated solo su
  `flusso.stato = IN_CORSO`, senza guardare lo stato **del documento**
  (`doc_stato_codice_interno`). Col fix DB il milestone diventa terminale e il picker
  sparisce; un guard aggiuntivo su documento già a verdetto sarebbe cintura+bretelle.
</content>
</invoke>
