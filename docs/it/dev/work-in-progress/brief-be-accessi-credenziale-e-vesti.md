# Brief BE/FE — Accessi: la veste revocata e il collaudo delle sessioni per veste

## ⏭️ Chi riparte — aggiornato al 2026-11-25

**Riparte: la sessione DB**, col brief DB nuovo sugli accessi (§1.1). Il collaudo a video (§2) non aspetta nessuno.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | sessione DB | Il brief DB nuovo sugli accessi (T9 di [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §17.1), che porta **R-4**: la veste ricorda di essere stata revocata, e la riattivazione self-service la rifiuta | §1.1 | — |
| 2 | team BE/FE | D-4 e A-6 sulla regola consegnata dal DB | §1.2 | 1 |
| 3 | Tid | Il collaudo a video di D-5 | §2 | — |
| 4 | team BE/FE | Archiviazione in `work-done/` | §3 | 2, 3 |

**Decisioni aperte di Tid:** nessuna in questo brief. La forma della marca «revocata» la sceglie il DB nel suo brief.

> **Chi scrive:** sessione BE (`dev/backend-tid`), 2026-11-25. **A chi:** team BE/FE, Tid; la sessione DB per il
> prerequisito di §1.1.
> **Origine:** il residuo del
> [piano BE/FE accessi](../work-done/2026/piano-be-fe-accessi-credenziale-e-vesti.md), archiviato lo stesso giorno
> dopo la riverifica sul codice: L-0, L-1, L-2, L-3, L-4, L-6, D-3 e D-5 lato codice sono chiusi; restano R-4 (cioè
> D-4 e A-6) e il collaudo a video di D-5. Il **perché** di ogni sigla sta nel piano e
> nell'[analisi](../work-done/2026/analisi-accessi-credenziale-e-vesti.md): qui solo cosa resta.
> **Brief vicini verificati:** [brief-db-revisione-anagrafiche](brief-db-revisione-anagrafiche.md) §17.1 (Tid,
> 2026-11-23) manda il tema T9, gli accessi, in un brief DB nuovo «con R-4 del piano accessi», insieme a S64
> (`fn_stato_veste`: `ATTIVO` vuol dire «accesa» o «utilizzabile») e S67 (la veste dello shop nasce accesa o spenta),
> che è la stessa materia di R-4. Al 2026-11-25 quel brief non è ancora scritto.

---

## 1. R-4 — La revoca dell'admin che tiene (D-4, A-6)

### 1.1 La richiesta al DB

La veste ricorda di essere stata **revocata dall'amministratore** (chi, quando), e la riattivazione self-service la
rifiuta. La regola sta a DB, non nel BE (piano §5 R-4). Va nel brief DB degli accessi (T9), insieme a S67: se la
veste dello shop nasce spenta e si accende da sé, «spenta dalla persona» e «spenta dall'admin» devono distinguersi.

**Stato verificato sul codice il 2026-11-25:**

- `anagrafiche.identita_digitali` ha `attivo`, `valido_dal`, `valido_al`, `invito_inviato_at`, `meta`: nessuna
  colonna dice che la veste è stata revocata, da chi e quando;
- [ProfileActivateShopView](../../../../backend/apps/portale/api/views.py#L69) (`POST portale/profile/activate-shop/`)
  controlla solo che chi chiama sia `CLIENTE_PORTALE`: un cliente a cui l'admin ha spento la veste shop se la
  riaccende con un clic. È il difetto **A-6**.

### 1.2 Il lavoro BE/FE, quando il DB consegna

Dal piano, §4.3 riga «Revoca (D-4)»:

- disattivare **dall'admin** marca la veste come revocata, con la funzione che il DB consegna;
- `ProfileActivateShopView` rifiuta una veste revocata, col codice del DB (policy generata e ripiego);
- FE: [AttivaAccessoShopButton](../../../../frontend/src/portale/components/AttivaAccessoShopButton.vue) spento col
  motivo, [PortaleAccessoPanel](../../../../frontend/src/portale/components/PortaleAccessoPanel.vue) mostra «revocato»;
- test sul DB vero: l'admin spegne la veste shop → l'attivazione self-service è rifiutata; la persona che se la
  spegne da sé la riaccende.

## 2. Il collaudo a video di D-5 — Sessioni per veste

Il codice è chiuso dal 2026-10-02 (piano §4.3-bis, parti 1 e 2): il refresh di una veste spenta è un 401 e chiude
la sessione; «Disabilita» e l'interruttore chiudono le sessioni e gli inviti della **sola** veste spenta. Manca la
prova a video:

| # | Caso | Atteso |
| --- | --- | --- |
| a | Una persona operatore **e** cliente shop, connessa nelle due porte: «Disabilita» (e, a parte, l'interruttore spento) | Al primo rinnovo esce dall'amministrazione, **non** dallo shop |
| b | Un operatore con un invito pendente: «Disabilita» | Il link dell'invito risponde «token non valido» |
| c | Riaccendere la veste dopo lo spegnimento | La vecchia sessione non si riapre: si rientra col login |

Non blocca nulla.

## 3. Alla chiusura

Il brief va in `work-done/` quando D-4 e A-6 sono fatti e il collaudo è eseguito. Si aggiornano la riga «Accessi»
di `.codex/PROJECT_CONTEXT.md` e i «⚠️ Difetto noto» delle doc `manual/` che rimandano ad A-6.

---
{% include-markdown "signature-core.md" %}
