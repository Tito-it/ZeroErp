### 🏢 L'azienda di un billing account

> **Ultimo aggiornamento**: 22 novembre 2026

Ogni billing account fattura per un'azienda (l'emittente fiscale). Lo dice
`anagrafiche.emittenti_fiscali_billing_account`: al massimo una riga per billing account, e una riga senza
billing account, `is_default`, che è l'**azienda predefinita** dell'installazione, una sola.

**Di quale azienda è un billing account: tre livelli**

1. il suo **collegamento**, se c'è: vince sempre;
2. senza collegamento e **in sessione**, l'azienda di chi agisce: è l'istante fra la nascita del billing
   account e il collegamento che il trigger di nascita scrive con quella stessa azienda;
3. senza collegamento e senza sessione (batch, manutenzione), la **predefinita**.

La regola sta in `script.fn_get_ba_emittente_sr_id`; `anagrafiche.fn_get_emittente_fiscale_id` la usa e
trasforma un'azienda non risolta in `E_EMITTENTE_DEFAULT_MISSING`. I controlli che guardano lo spostamento
della predefinita chiedono invece l'azienda **per l'installazione**
(`script.fn_get_ba_emittente_sr_id_installazione`: collegamento, altrimenti predefinita), perché lì chi agisce
non c'entra: il billing account senza collegamento segue la predefinita, chiunque la sposti.

**I quattro modi in cui l'azienda di un billing account cambia**

| # | Movimento sul collegamento | Effetto |
| --- | --- | --- |
| 1 | si **crea** (anche alla nascita del billing account) | dalla predefinita all'azienda scelta |
| 2 | si **modifica** | da un'azienda all'altra |
| 3 | si **cancella** | ricade sulla predefinita, senza che nessuno abbia scritto un'azienda |
| 4 | si sposta la **predefinita** | cambiano insieme tutti i billing account senza collegamento |

Spostare un cliente si fa togliendo il collegamento e creandone uno nuovo: il primo passo, da solo, è già un
cambio di azienda. Ogni movimento passa da tre cancelli, ciascuno con un ramo per il billing account toccato e
uno per la predefinita:

| Domanda | Sul billing account | Sulla predefinita | Trigger |
| --- | --- | --- | --- |
| La storia si sposta? | `fn_guard_ba_cambio_emittente` | `fn_guard_ba_gestore_globale_storia` | `trgfn_efba_guard_storia_emittente`, prima della scrittura |
| L'albero padre/figli diventa misto? | `fn_guard_albero_ba_emittente` | `fn_guard_albero_ba_gestore_globale` | `trgfn_efba_guard_albero_emittente`, dopo |
| L'istanza finisce su due aziende? | `fn_guard_istanza_ba_emittente` | `fn_guard_istanza_ba_gestore_globale` | `trgfn_efba_guard_istanza_emittente`, dopo |

**Che cosa è la «storia» che ferma un cambio**

Un **documento numerato su un registro**, di qualunque famiglia: le famiglie attive di
`vendite.famiglie_documento` che dichiarano la colonna del billing account. Il numero viene dal registro di
un'azienda e nessuno lo riscrive: spostare il cliente lascerebbe quei documenti a un'azienda che non vede più
il cliente. L'elenco non è scritto nei controlli: una famiglia nuova entra nella regola quando si registra, e
una famiglia con documenti numerati non si spegne.

Una **bozza non blocca**: non ha ancora congelato niente. È la finestra di correzione, che serve perché il
collegamento nasce da solo con l'azienda di chi crea il cliente, e un cliente può nascere sotto l'azienda
sbagliata. Un cliente che passa davvero a un'altra azienda non si sposta: presso la nuova si apre una fornitura
nuova, e i documenti già emessi restano a chi li ha emessi.
