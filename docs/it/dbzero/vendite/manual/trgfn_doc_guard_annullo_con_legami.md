## 📘 Documentazione Concettuale – Funzione `vendite.trgfn_doc_guard_annullo_con_legami`

> 👀 **Vedi anche**
>
**Approfondimento funzioni:**
>
• [vendite.fn_documento_legami](/dbzero/vendite/funzioni/fn_documento_legami) — che cosa si riapre  
> • [vendite.fn_documento_ritira_legami](/dbzero/vendite/funzioni/fn_documento_ritira_legami) — la conferma e il ritiro  
> • [vendite.fn_doc_porta_ritiro_ammette](/dbzero/vendite/funzioni/fn_doc_porta_ritiro_ammette) — la porta  
> • [vendite.trgfn_doc_guard_chiusura_sorgente](/dbzero/vendite/funzioni/trgfn_doc_guard_chiusura_sorgente) — il freno sulle righe emesse  

---

### 🎯 Scopo Principale
(2026-10-11, brief-db-annullo-documento-con-legami, D-1/D-4/D-5)

**L'avviso.** Un documento nato consumando qualcosa di un altro documento non si
annulla in silenzio: annullarlo restituisce ciò che aveva consumato, e chi
annulla deve vedere che cosa si riapre e **confermare**.

Entrare in uno stato abortito (`is_abortito` dal vocabolario, non `'ANNULLATO'`
cablato) con legami è rifiutato con **`E_DOC_ANNULLO_CON_LEGAMI`**, che dice
quanti sono. Vale su ogni strada che cambia lo stato: l'`UPDATE` diretto del
backend come il verbo di stato.

Montato su bolla, ordine, preventivo, contratto e, dal 2026-10-12, commessa
(`trg_<tabella>_m10_guard_annullo_con_legami_upd`;
brief-db-annullo-a-valle-riapre-a-monte).

---

### Il percorso, dal pulsante alla conferma

1. L'operatore preme «Annulla»; il backend cambia lo stato come sempre.
2. Il documento ha legami: questo guard rifiuta con `E_DOC_ANNULLO_CON_LEGAMI`
   (409, conferma richiesta).
3. Il backend legge i legami
   ([`fn_documento_legami`](/dbzero/vendite/funzioni/fn_documento_legami)) e
   mostra la finestra: «riga 1, ordine 12, 10 pz».
4. Alla conferma chiama il verbo del documento — `fn_annulla_ddt`,
   `fn_annulla_ordine`, `fn_annulla_preventivo`, `fn_annulla_contratto`,
   [`fn_annulla_commessa`](/dbzero/vendite/funzioni/fn_annulla_commessa) —
   passando **quanti legami ha mostrato**.
5. Il verbo conferma, ritira i consumi, apre la porta e cambia lo stato: qui
   arriva senza consumi, e passa.

Se nel frattempo i legami sono cambiati, il verbo rifiuta con lo stesso codice e
la finestra si ripresenta aggiornata: chi conferma dichiara ciò che ha visto
(stampo di `E_CREDENZIALE_DA_CONFERMARE`).

---

### Le due regole

* **Ciò che va ritirato rifiuta sempre**, porta aperta o no: ogni legame che
  non è provenienza (consumo e, sulla commessa, l'onere di natura `ANNULLO`). Il verbo li
  ritira prima di cambiare stato: se ne resta uno, qualcosa si ritirerebbe in
  silenzio, o non si ritirerebbe affatto.
* **La sola provenienza** (l'offerta di un contratto o di un ordine, che non si
  ritira) passa con la porta del ritiro aperta per **questo** documento, cioè
  dopo la conferma.

---

### ⭐ Perché sulla tabella, e non nei servizi (l'argomento di Q-10)

Lo stato di una testata si cambia da **molti** posti, e con una regola nei
servizi basta **uno** distratto perché il buco torni. L'argomento viene dal
ritiro automatico dalla commessa che questo guard ha sostituito
(`trgfn_doc_ritira_commessa_attivita`, lotto L7 / Q-10 di
`brief-db-lavoro-che-non-torna-indietro`): la regola stava già nella struttura.

Quello che è cambiato è il **prezzo**. Il ritiro automatico agiva *a distanza*:
chi chiudeva l'ordine non vedeva che stava annullando anche righe di commessa, e
il registro riga per riga era l'unico modo di saperlo dopo. Con D-5 il ritiro
non è più silenzioso: le righe `NON_EMESSA` sono legami, l'annullo chiede
conferma, e il ritiro lo fa il verbo — con la stessa primitiva e lo stesso
registro ([`fn_ritira_commessa_attivita_da_sorgente`](/dbzero/vendite/funzioni/fn_ritira_commessa_attivita_da_sorgente)).

⚠️ `ANNULLATA`, sulle righe di commessa, resta **irreversibile**: riaprire un
documento non le riporta indietro, le rifà il push.

---

### ⚠️ La fascia `_m10_`: dopo i guard `_a10_`

Prima parla ciò che **vieta** (la matrice degli stati, le righe di commessa già
`EMESSA`, i figli vivi di un preventivo), poi ciò che **chiede conferma**.
Altrimenti l'operatore conferma, e si sente dire che non poteva.

`_m10_` è la fascia intermedia che le linee guida dei trigger riservano: dopo
ogni `_a10_`, prima dei `_z90_` `BEFORE` (snapshot dello stato, storico).

---

### Montaggio

| Argomento | Cosa |
| --- | --- |
| `TG_ARGV[0]` | documento: `DDT`, `ORDINE`, `PREVENTIVO`, `CONTRATTO`, `COMMESSA` |
| `TG_ARGV[1]` | colonna di stato |
| `TG_ARGV[2]` | vocabolario degli stati (`schema.tabella`) |

`BEFORE UPDATE`, con `WHEN` sul cambio della colonna di stato. Un montaggio
sbagliato è `E_VENDITE_CHIAMATA_NON_VALIDA`.

---

### Codici errore

| Codice | Quando |
| --- | --- |
| `E_DOC_ANNULLO_CON_LEGAMI` | annullo con legami senza conferma (valori: etichetta del documento, numero di legami; contesto: documento, id, legami, consumi) |
| `E_VENDITE_CHIAMATA_NON_VALIDA` | montaggio sbagliato |

---

### Note operative

* Sulla bolla prende il posto della Regola 4 di `vendite.trgfn_ddt_guard_transizione`
  e del codice `E_DDT_ANNULLO_CON_LEGAMI`, ritirato (`obsoleto_dal`).
* Test: `db/pgtap/vendite/test-annullo-documento-con-legami-v1.sql`,
  `db/pgtap/vendite/test-ritiro-alla-chiusura-documento-v1.sql`,
  `db/pgtap/vendite/test-ddt-righe-evase-dall-ordine-v1.sql` (scenario H),
  `db/pgtap/vendite/test-annullo-commessa-v1.sql` (la commessa).

---

{% include-markdown "signature-core.md" %}
