# Brief DB — il motivo di un override utente è obbligatorio

> **⏭️ Chi riparte — aggiornato al 2026-11-27**
>
> **Riparte: nessuno, per ora.** Il brief è **aperto e non iniziato**. Nasce dalla verifica del giro 10-quater di
> [brief-db-porte-aperte-dalla-sola-guc](../work-done/2026/brief-db-porte-aperte-dalla-sola-guc.md) (Tid,
> 2026-11-27): la guida dei permessi dice che il motivo di un override è obbligatorio, il codice lo lascia vuoto.
> Tid ha scelto di correggere il codice, non la guida.
>
> | # | Chi | Che cosa | Dove | Aspetta |
> | --- | --- | --- | --- | --- |
> | 1 | Tid | il via (D-1 **a**, D-2 **b**, D-3 **b** decise il 2026-11-27) | §4 | — |
> | 2 | team DB | il giro: la regola nella primitiva, il codice d'errore, i pgTAP, la guida | §3 | 1 |
> | 3 | team BE/FE | il passaggio dopo l'apply: il campo nel pannello, la validazione, il ripiego | §5 | 2 |
>
> Decisioni di Tid, tutte prese il 2026-11-27 (§4): D-1 **a**, la regola nella primitiva; D-2 **b**, le righe di oggi
> senza motivo restano; D-3 **b**, il pannello chiede un motivo al salvataggio. Manca solo il via. Niente da committare oltre a questo file.
>
> **Brief vicini verificati** (2026-11-27, ricerca di `user_override` e `motivo` in `work-in-progress/`): nessuno
> tratta il motivo degli override. `permessi-e-autorizzazioni-v3` (dormiente) non lo nomina;
> `valutazione-modello-di-dominio-db` non tocca queste tabelle.
>
> **Guide verificate** (`scripts/guide_coinvolte.py --oggetti` sulle tre tabelle, i tre verbi e i builder pgTAP,
> 2026-11-27):
> * [architettura-permessi-e-autorizzazioni](../../guide/architettura-permessi-e-autorizzazioni.md) §4.8: «Il
>   motivo è obbligatorio per audit: consente di tracciare perché e da chi l'eccezione è stata concessa».
>   **Contraddetta** dal codice di oggi; decisione di Tid del 2026-11-27: vale la guida, si allinea il codice.
>   «Da chi» lo dice già l'audit; il motivo porta il «perché». Il giro rilegge §4.1-§4.8 (le tre tabelle) e «Chi
>   scrive gli override».
> * [pgtap-come-si-scrive-un-test](../../guide/pgtap-come-si-scrive-un-test.md): i builder scrivono già un motivo
>   (§2). **Coerente**.
> * `risorse-umane-e-accessi`, `architettura-multi-face-auth`: nominano le tabelle, non il motivo. **Coerenti**.

## 1. Il problema, sul modello

Un override utente è un'eccezione al profilo: dà a una persona un livello, un oggetto o un'azione che il reparto non
le dà, oppure glieli toglie. L'audit registra chi l'ha scritto e quando; **perché** lo dice solo il `motivo`. Un
override senza motivo è un'eccezione ai permessi che nessuno sa più spiegare, e che nessuno osa togliere.

La regola vale per **ogni** override, anche per quelli che tolgono (`BLOCCATO`, `abilitata = false`): anche una
restrizione è un'eccezione al profilo, e va spiegata allo stesso modo.

E vale **al DB**: dal giro 10-quater le tre tabelle si scrivono solo dalla primitiva
`config.fn_applica_imposta_override` (attraverso i tre verbi del SUPER_ADMIN e il provisioning). Una regola tenuta
solo nel service la scavalca il primo chiamante che non passa da lì.

## 2. Che cosa c'è oggi — fatti datati al 2026-11-27

* `config.user_override_aree`, `config.user_override_azioni` e `config.user_override_oggetti`: `motivo text`
  **nullable**, nessun `CHECK` (doc auto-generata).
* `config.fn_applica_imposta_override` (`20261126-50`): ammette la chiave `motivo` e ne scrive il valore così com'è,
  `NULL` compreso.
* I builder pgTAP (`fn_pgtap_concedi_livello_area`, `fn_pgtap_concedi_azione`, `fn_pgtap_nega_azione`) scrivono
  sempre un motivo («Fixture pgTAP…»). `fn_pgtap_scrivi_override` riscrive le voci che legge, con il loro motivo:
  una voce già senza motivo sarebbe rifiutata alla riscrittura.
* Il provisioning di sviluppo (`20261126-54`) scrive i suoi override con un motivo.
* BE: `AmmSoftwareService._voci_override` legge il motivo con `optional_string`, cioè vuoto ammesso.
* FE: `OperatorePermessiTab.vue` (`_toAreaItem`, `_toAzioneItem`, `_toOggettoItem`) rimanda il `motivo` letto dal GET,
  ma la matrice **non ha un campo per scriverlo**: ogni override creato dalla schermata nasce senza motivo.
  ⚠️ Il commento sopra quelle funzioni descrive ancora il `PUT` come `DELETE WHERE auth_user_id` + reinsert: dal
  2026-11-27 è il verbo. È da correggere nel passaggio BE/FE.

## 3. Che cosa si cambia — proposta

1. **La regola sta nella primitiva**, non nelle colonne: `config.fn_applica_imposta_override` rifiuta un elemento
   con `motivo` assente, `NULL` o fatto di soli spazi, con un **codice d'errore nuovo** a catalogo (nome proposto
   `E_OVERRIDE_MOTIVO_OBBLIGATORIO`), il campo `motivo` nel canale `COLUMN` e un hint che dice cosa scrivere. La
   primitiva è l'unica strada di scrittura: un vincolo di colonna ripeterebbe la regola, e darebbe un 23502 o un
   23514 da tradurre per nome invece di un codice del dominio. ✅ D-1 **a** (Tid, 2026-11-27).
2. **Il motivo si salva ripulito** (`btrim`), come ogni testo libero.
3. **I pgTAP**: un test nuovo (le tre tabelle: motivo assente, `NULL`, vuoto, soli spazi → rifiutati; un motivo →
   scritto), anche per un override che toglie. I pgTAP che scrivono override senza motivo, se ce ne sono, si portano ai
   builder o ricevono un motivo.
4. **La guida** `architettura-permessi-e-autorizzazioni` §4.8 dice dove sta la regola (la primitiva) e che vale anche
   per gli override che tolgono; i `manual/` delle tre tabelle e della primitiva lo stesso.
5. **I dati di sviluppo**: le righe senza motivo, se ce ne sono, non si toccano (D-2 **b**, Tid, 2026-11-27). La
   regola vale alla scrittura: la prossima riscrittura dell'elenco di quell'utente le rifiuta finché non ricevono un
   motivo, e il pannello lo chiede (D-3 **b**). Nessun changeSet di dati. ⚠️ Vale anche per `fn_pgtap_scrivi_override`,
   che riscrive l'elenco intero: sugli utenti costruiti dai builder il motivo c'è sempre.

## 4. Decisioni per Tid

| # | Domanda | Strade | Raccomandazione |
| --- | --- | --- | --- |
| **D-1** ✅ **a** (Tid, 2026-11-27) | Dove sta la regola? | **a** nella primitiva, col codice del dominio · **b** `NOT NULL` + `CHECK (btrim(motivo) <> '')` sulle tre colonne · **c** tutte e due | ⭐ **a**: la primitiva è l'unica strada di scrittura e dà un errore che il BE non deve tradurre per nome. **c** se si vuole la regola anche contro una scrittura del proprietario |
| **D-2** ✅ **b** (Tid, 2026-11-27) | Le righe di oggi senza motivo? | **a** un changeSet di dati scrive un motivo di ripiego («Motivo non registrato prima del 2026-11-27») · **b** restano: la prossima riscrittura chiede di scriverlo | ⭐ **a** con **D-1 c** (il vincolo lo esige); con **D-1 a** basta **b**, e il pannello lo chiede alla prima modifica. Decisa **b**: un motivo di ripiego non spiega niente |
| **D-3** ✅ **b** (Tid, 2026-11-27) | Il motivo nel pannello: uno per voce, o uno per salvataggio? | **a** un campo per voce, nella riga della matrice · **b** un motivo chiesto al salvataggio, scritto sulle voci cambiate | la regola del DB è per voce in tutte e due le strade. Decisa **b**: una richiesta porta più cambi con una ragione sola. Il motivo va sulle voci cambiate **e** su quelle vecchie ancora senza; le altre tengono il loro |

## 5. Il passaggio al team BE/FE (dopo l'apply)

Chi cambia per primo: il DB. Fino all'apply il BE resta com'è (`optional_string`): una richiesta senza motivo oggi
passa, e dopo l'apply la rifiuta il DB col codice nuovo.

1. `AmmSoftwareService._voci_override`: il motivo con `require_string` (400 sul campo, prima del DB).
2. `genera_error_policies` per il codice nuovo, e il ripiego senza `%s`.
3. FE (D-3 **b**): in `OperatorePermessiTab.vue`, al salvataggio, un dialog chiede il motivo, obbligatorio, se
   almeno una voce è cambiata o è senza motivo. Il testo va sulle voci cambiate e su quelle senza motivo (D-2 **b**);
   le altre partono col loro. Il rifiuto del DB col codice nuovo si mostra nel dialog. Testi i18n. Il commento su
   `DELETE` + reinsert si corregge (§2).
4. I test sul DB vero che mandano voci senza motivo: in `test_override_aree_azioni_db` i casi 3 e 4, e gli altri che
   la ricerca trova al momento (`grep -rn "put_override_" backend/apps --include=*.py`).
5. Manuale `api_amm_software` §2.2, §2.4, §2.4-bis: il motivo è obbligatorio.

## Il piano

- [x] D-1 **a**, la regola nella primitiva (Tid, 2026-11-27)
- [x] D-2 **b**, D-3 **b** (Tid, 2026-11-27)
- [ ] Il via (Tid)
- [ ] Il giro DB: primitiva, codice d'errore, pgTAP, guida e `manual/`; prova sullo scratch
- [ ] L'apply, la doc auto-generata
- [ ] Il passaggio BE/FE (§5)

---
{% include-markdown "signature-core.md" %}
