# Brief DB — Le righe di contratto che non sono «una volta»: canone, orario e consumo in commessa

## ⏭️ Chi riparte — aggiornato al 2026-10-13

**Riparte: Tid**, con le decisioni del §4. Cantiere aperto, non iniziato.

| # | Chi | Che cosa | Dove | Aspetta |
| --- | --- | --- | --- | --- |
| 1 | Tid | decisioni G-1…G-4 | §4 | — |
| 2 | DB | analisi della forma scelta e consegna | — | 1 |
| 3 | BE/FE | da definire dopo la forma (l'orchestratore del push, la lista dei contratti) | — | 2 |

Decisioni aperte di Tid: §4. Lavoro da committare: questo documento (il giro che lo ha aperto,
`20261013-24`, è nella risposta al team BE del 2026-10-13).

> **Chi scrive:** team DB (`dev/db-tid`), 2026-10-13. **A chi:** Tid, poi il team DB.
> **Origine:** decisione D-2 (a) di Tid, 2026-10-13, sulla segnalazione BE del push batch CONTRATTO
> (registro 2724: un contratto senza `valido_al` cadeva sul NOT NULL di
> `commesse_attivita.competenza_al`). Registro: **D31** di
> [migliorie-generali-da-test-valutazione](migliorie-generali-da-test-valutazione.md).

## 1. Il caso

Una riga di contratto dice **come si eroga** (`vendite.contratti_righe.tipo_erogazione`, vocabolario
`config.erogazioni_fonti`): `UNA_TANTUM`, `CANONE`, `ORARIO`, `CONSUMO`. Solo la prima è «una riga,
una volta». Le altre tre hanno un ritmo o una fonte:

* **CANONE** — una riga per periodo. Il contratto lo dice già: `periodicita`, `generazione_canone`
  (`INIZIO_PERIODO`, `FINE_PERIODO`, `PRORATA`, obbligatoria per `chk_contrighe_coerenza_canone`),
  `competenza_canone`;
* **ORARIO** — la quantità viene dalle ore (`TIMESHEET`, `MANUALE`) o è fissa (`FISSA`);
* **CONSUMO** — la quantità viene dalle letture (`LETTURE`) o è manuale.

Fino al 2026-10-13 `vendite.fn_list_contratti_da_pushare` le mandava **tutte una volta sola**, nel
mese di `valido_dal`, con la quantità della riga e una competenza uguale a **tutta la validità del
contratto**. Un canone mensile di un contratto annuale diventava una riga sola, con un prezzo, per
dodici mesi. Nessuno genera i periodi: né il DB né `HandlerContratti`, e `generazione_canone` viaggia
in `meta` senza un lettore.

Dal `20261013-24` (D-2 di Tid) il lister manda **solo le UNA_TANTUM**, con la competenza del giorno di
attivazione. Il push smette di produrre righe sbagliate, ma le altre tre erogazioni **non arrivano più in
commessa**: è il lavoro di questo brief.

## 2. I fatti di struttura (2026-10-13)

* `vendite.contratti.valido_dal` NOT NULL, `valido_al` nullable: un contratto può non finire, e la
  generazione per periodo non può contare su una fine.
* `vendite.commesse_attivita`: `competenza_mese` (primo del mese, CHECK), `competenza_dal` e
  `competenza_al` NOT NULL con `competenza_dal <= competenza_al`.
* Il segmento della riga di contratto è `CONTR:<uid>:R:<riga>:M:<AAAA-MM>`: ha già il mese, quindi
  la forma «una riga per periodo» c'è nel nome, e `script.fn_get_stato_push_segment` la classifica per
  segmento.
* I consumi hanno già un loro push (`vendite.fn_list_consumi_da_pushare`, da
  `vendite.attivita_consumi`), che oggi non arriva in commessa per un altro motivo: `articolo_id`
  NULL contro una colonna NOT NULL, e lo smistamento per componente è uno stub rimandato da Tid il
  2026-06-16.

## 3. Le domande

1. **Chi genera i periodi del canone, e quando.** Una riga per periodo «maturato» a ogni giro del push
   (il lister li calcola fino a oggi) o un calendario scritto all'attivazione del contratto?
2. **Fino a quando.** Con `valido_al` NULL la generazione non ha una fine: si ferma a «oggi», al
   periodo corrente, o a un orizzonte dichiarato?
3. **La competenza di un periodo.** `INIZIO_PERIODO` / `FINE_PERIODO` / `PRORATA` dicono quando si
   addebita e come si tratta il primo periodo parziale: la regola va scritta in un posto solo.
4. **ORARIO e CONSUMO.** Le loro quantità non stanno sul contratto: il contratto dà il prezzo, la
   quantità arriva da timesheet e letture. Passano dal contratto o dalle loro sorgenti (consumi), con
   il contratto come listino?

## 4. Decisioni di Tid

* **G-1** — chi genera i periodi del canone (domanda 1);
* **G-2** — l'orizzonte per un contratto senza scadenza (domanda 2);
* **G-3** — la sede della regola di competenza del periodo (domanda 3);
* **G-4** — ORARIO e CONSUMO: dal contratto o dalle loro sorgenti (domanda 4).

## 5. Cosa resta valido nel frattempo

* Il lister dei contratti manda solo le UNA_TANTUM (`20261013-24`). Il presidio è
  `vendite/test-push-contratto-dalla-madre-v1` (parte D) e
  `vendite/test-righe-erogazione-obbligatoria-v1` (19, 21).
* ⚠️ Quando la generazione arriva, il filtro `cr.tipo_erogazione = 'UNA_TANTUM'` del lister si
  allarga, e i due test sopra cambiano con lui: non vanno «aggiustati», raccontano la regola.
