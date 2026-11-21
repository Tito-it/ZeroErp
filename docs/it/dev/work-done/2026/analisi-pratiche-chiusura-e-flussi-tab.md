# Analisi — Chiusura pratica workflow-driven + tab Flussi legacy

**Area:** `pratiche` · **Tipo:** analisi/decisione di modello (no codice)
**Data:** 2026-06-14 · **Autore:** backend agent (per Tid)

Due nodi emersi sul drawer pratica:
1. il pulsante **"Chiudi"** come azione operatore non convince — la chiusura dovrebbe
   dipendere dal completamento del workflow (flussi), non da un click;
2. nella tab **Flussi** un pulsante "Nuovo flusso" crea un *flusso generico* — sembra
   logica precedente ancora attiva.

---

## 1. Chiusura pratica: manuale vs workflow-driven

### Stato attuale

- **Azione manuale.** In [PraticaDrawer.vue](../../../frontend/src/pratiche/components/PraticaDrawer.vue)
  l'azione `chiudi` è `visible: stato === APERTA || stato === SOSPESA`, comando
  `cambiaStato(CHIUSA)`. Nessun gating per capability nella UI: il bottone c'è
  sempre, e l'eventuale blocco arriva dal DB al click.
- **Guard DB.** `trg_pratiche_a10_guard_chiusura_flussi` + `fn_check_chiusura_pratica`:
  la chiusura è rifiutata (errore `PRATICHE_CHIUSURA_FLUSSI_OBBLIGATORI_MANCANTI`)
  se esiste un template **obbligatorio** non completato e ancora **percorribile**.
  Quindi la chiusura è *permessa* quando tutti gli obbligatori sono completati (o
  non più raggiungibili — ramo morto).
- **Nessuna auto-chiusura.** Non esiste un trigger che porti la pratica a CHIUSA al
  completamento dei flussi. Non esiste sul `template_flussi` un flag tipo
  `chiude_pratica`/`terminale`: le colonne sono `obbligatorio`, `sequenza`,
  `direzione`, `ripetibilita`, `handler_id`.

### Problema

Semanticamente, in un modello a workflow la pratica **è conclusa quando il suo
percorso è concluso**, non quando un operatore decide di premere "Chiudi". Oggi:
- l'operatore può "dimenticare" di chiudere → pratiche complete ma APERTE;
- il bottone "Chiudi" suggerisce un'azione discrezionale che in realtà è vincolata
  al workflow (il guard la consente solo a obbligatori completati).

`Sospendi` e `Annulla` invece **sono** legittime azioni operatore (interruzioni
volontarie, non dipendono dal completamento del percorso) — restano com'è.

### Opzioni

**A. Auto-chiusura "a percorso completo" (consigliata).**
Quando l'ultimo flusso rilevante si COMPLETA e `fn_check_chiusura_pratica` non
riporta più bloccanti (tutti gli obbligatori completati / non percorribili), un
trigger porta la pratica APERTA → CHIUSA. Si **rimuove** il pulsante "Chiudi"
manuale dalla scheda.
- Pro: chiusura data-driven, nessun passo dimenticato, coerente col modello flussi.
- Contro: serve un trigger DB (su `flussi` AFTER UPDATE→COMPLETATO che richiama il
  check e transita la pratica); meno controllo discrezionale.

**B. Flusso "di chiusura" esplicito.**
Nuovo flag su `template_flussi` (es. `chiude_pratica boolean`): al completamento di
quel template la pratica chiude. Più esplicito quando un tipo prestazione ha uno
step finale ben preciso.
- Pro: controllo dichiarativo per tipo prestazione.
- Contro: dato in più da configurare; va deciso il comportamento se il flusso di
  chiusura è opzionale o ripetibile.

**C. Mantieni manuale ma gate la UI per capability.**
Tieni il bottone "Chiudi" ma rendilo visibile/abilitato solo quando il DB dice
"chiudibile" (consumando `fn_check_chiusura_pratica`, niente click→errore).
- Pro: minimo intervento, nessuna auto-transizione.
- Contro: non risolve l'obiezione di fondo (resta un'azione operatore).

### Raccomandazione

**Opzione A** come comportamento di default (auto-chiusura a percorso completo),
eventualmente combinata con **B** se si vuole marcare uno step finale esplicito.
È coerente con la direzione già presa (pratica nasce APERTA, flussi guidano il
ciclo di vita). Richiede **brief DB** (trigger di auto-chiusura + eventuale flag).
Lato FE: rimozione del pulsante "Chiudi" manuale (resta data-driven); `Sospendi`
e `Annulla` invariati.

**Da decidere con Tid:** A pura, oppure A+B (flag flusso di chiusura)?

---

## 2. Tab Flussi (PraticaFlussiTab) = gestione legacy

### Stato attuale

[PraticaFlussiTab.vue](../../../frontend/src/pratiche/components/PraticaFlussiTab.vue)
(tab "Flussi" dentro la scheda) offre:
- pulsante **"Nuovo flusso"** → `createFlusso(praticaId, { sequenza })` **senza
  `template_flusso_id`** → crea un **flusso generico** (in lista: "flusso generico");
- azioni **avvia/completa inline** per riga (con mini-form esito).

Questo è il pattern **pre-roadmap**. Il modello attuale istanzia i flussi dal
**percorso template-driven** ([PraticaPercorso.vue](../../../frontend/src/pratiche/components/PraticaPercorso.vue)
nella dashboard: "crea ed esegui" dal `template_flusso_id`) + esecuzione in
[FlussoDrawer.vue](../../../frontend/src/pratiche/components/FlussoDrawer.vue).

### Problema

- Un **flusso generico** (senza template) non appartiene al percorso del tipo
  prestazione: è fuori modello (niente prerequisiti, niente ruolo nella roadmap,
  niente handler). Il guard di chiusura ragiona sui template → un generico non
  conta come obbligatorio ma resta un'istanza orfana.
- **Due UI divergenti** per i flussi (tab scheda vs percorso dashboard): rischio di
  comportamenti incoerenti e doppia manutenzione (memoria `feedback_vue_reuse`).

### Raccomandazione

Allineare la tab Flussi al modello: renderla **sola lettura** (lista flussi della
pratica con stato/esito/sequenza), **rimuovendo** creazione generica e azioni
avvia/completa inline. Creazione ed esecuzione vivono solo nel percorso
template-driven + FlussoDrawer (un'unica sorgente di verità).
- Solo FE, nessun DB. Le i18n/handler della tab legacy si possono dismettere.
- Verificare prima se esistono `pratiche.flussi` generici (senza
  `template_flusso_id`) già creati in dev → eventuale pulizia dati.

**Da decidere con Tid:** tab Flussi sola-lettura (consigliato) oppure rimuoverla
del tutto dalla scheda (il percorso in dashboard è già il punto di gestione)?

---

## Sintesi decisioni aperte

| # | Tema | Opzioni | Consigliata | Impatto |
|---|------|---------|-------------|---------|
| 1 | Chiusura pratica | A auto / B flusso-chiusura / C UI-gated | A (±B) | brief DB + FE |
| 2 | Tab Flussi legacy | sola-lettura / rimuovere | sola-lettura | solo FE |
