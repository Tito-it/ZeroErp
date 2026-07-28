## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_commessa_attivita(...)`

> 👀 **Vedi anche**
>
> [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) ·
> [vendite.commesse_attivita_log](/dbzero/vendite/tabelle/commesse_attivita_log) ·
> [vendite.fn_aggiungi_onere_commessa](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa) ·
> [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) ·
> [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato)

---

### 🎯 Scopo Principale

(rev 2026-07-28)

Madre DB dell'**annullamento di una riga manuale di commessa**
(`brief-annullamento-righe-manuali-commessa` §4).

Chiude un buco operativo reale: un onere caricato per errore — causale sbagliata, cliente
sbagliato, doppio click — **non si poteva togliere in nessun modo**, e finiva in fattura. Non
esiste `DELETE` su `commesse_attivita`; la variazione di prezzo eccezionale esige `prezzo > 0`
e quindi può ridurre l'importo ma non farlo sparire; l'onere di storno negativo è vietato per
costruzione dalla porta oneri.

La funzione è la terza via, l'unica coerente con la natura di **libro giornale** della commessa:
**annullare senza cancellare**. La riga resta fisicamente dov'è, con il suo importo e la sua
storia; cambia solo la sua **eleggibilità alla fatturazione**, e il perché è scritto nel log.

### Perché non serviva una colonna nuova

`commesse_attivita.stato_emissione` ha da sempre un `CHECK` a **tre** valori — `NON_EMESSA`,
`EMESSA`, **`ANNULLATA`**. Il terzo non era mai stato usato, ma era già onorato ovunque contasse:

| Dove | Effetto su una riga `ANNULLATA` |
|---|---|
| `fn_emit_attivita_fatturabili_da_commessa` | non emessa → nessuna attività fatturabile → **mai in fattura** |
| `fn_list_commesse_emittibili` / `fn_list_emittibili_lane` | la commessa non compare, nessuna corsia, nessun lotto |
| `fn_approva_commessa_attivita` | **non ri-approvabile**: il «nessun ripristino» è strutturale |
| `vw_dash_competenza_attivita` / `vw_dash_fatturazione_commesse` | sparisce dal cockpit: contatori, lista attività, lista gruppi |

Mancava solo **il modo di impostare quel valore**. Il lavoro è quindi una funzione, non una
migrazione di schema: nessuna colonna, nessun backfill, nessun filtro da toccare. L'unico
ritocco è stato ai contatori di testata di `fn_get_commessa_stato`, che erano rimasti ciechi.

### Regole principali

* **Perimetro: righe MANUALI e NON ancora emesse.** Le righe da push restano non annullabili —
  il fatto viene dal documento e il rimedio sta a monte, sul documento. Le righe già emesse o
  fatturate si correggono con una **nota di credito**, che è un atto fiscale con un suo perimetro.
* **Il discriminante «manuale» è `sorgente_tipo_id IS NULL`** (*sourceless* = non nata da un
  documento). Non `tipo_movimento = 'ONERE'`, che è la **natura** del movimento e non l'origine
  (il `CHECK` ammette già `RETTIFICA`, e il giorno che nascesse una porta rettifiche manuale un
  filtro su `ONERE` la escluderebbe **in silenzio**); non il prefisso `MAN:` della `segment_key`,
  che è una convenzione di leggibilità e non un contratto. È la stessa definizione che
  `fn_build_gruppo_fatturabile_key` usa per il gruppo «oneri di commessa».
* **Motivo obbligatorio**, normalizzato con `btrim` e salvato nel log. L'annullamento è
  irreversibile: senza motivo resterebbe il fatto senza la ragione, e a mesi di distanza un
  importo sparito senza spiegazione è indistinguibile da un errore.
* **`stato_approvazione` resta com'è.** Approvazione ed emissione sono due assi distinti con
  `CHECK` separati: una riga annullata conserva la memoria di essere stata approvata.
* **Ritorna il `commessa_attivita_id`**, come la porta oneri ritorna l'id della riga creata.
* **`SECURITY INVOKER`**: RLS e scope emittente restano applicati identici. Il presidio permessi
  (`carica_voce_manuale` — chi può caricare una voce manuale può annullarla) vive sul **BE**,
  come per la porta oneri: la madre è usabile anche da un processo autorizzato.

### L'ordine dei guard non è indifferente

Tre rifiuti con **codici distinti**, perché portano l'operatore a tre azioni diverse e un
messaggio unico lo lascerebbe a indovinare:

| Ordine | Guard | Codice | Che cosa deve fare l'operatore |
|---|---|---|---|
| 1º | riga già `ANNULLATA` | `E_RIGA_COMMESSA_GIA_ANNULLATA` (564) | niente: era già fatto |
| 2º | riga con sorgente | `E_RIGA_COMMESSA_NON_MANUALE` (565) | andare a monte, sul documento |
| 3º | riga già emessa | `E_RIGA_COMMESSA_GIA_EMESSA` (566) | nota di credito |
| — | motivo assente o vuoto | `E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO` (567) | indicare la ragione |

**«Non manuale» precede «già emessa»** perché è l'**identità** della riga, non una sua
condizione: a una riga da push emessa, dire «già emessa» suggerirebbe che senza emissione si
potrebbe annullare — falso. «Già annullata» resta in testa perché una riga `ANNULLATA` è per
costruzione manuale (nessun altro percorso scrive quel valore), quindi non toglie mai il posto
a una diagnosi migliore.

### Note di concorrenza

La riga viene caricata con **`SELECT ... FOR UPDATE`**. Senza il lock, due annullamenti
simultanei leggerebbero entrambi `NON_EMESSA` e scriverebbero **due eventi di log** per un solo
annullamento; e un'emissione concorrente (`fn_emit` fa `UPDATE ... SET stato_emissione = 'EMESSA'`)
darebbe esito non deterministico. Con il lock, sotto `READ COMMITTED` la seconda transazione
rilegge la riga aggiornata e cade sul guard corretto.

Il lock insiste su **una sola risorsa**: nessun rischio di deadlock incrociato con `fn_emit`,
che blocca `attivita_fatturabili` e non `commesse_attivita`.

### Atomicità

Due scritture — `UPDATE` dello stato e `INSERT` dell'evento di log — in **una sola funzione**,
invocata con una sola `SELECT`: atomica per costruzione
([linee guida SQL §5b](/linee-guida-sql)). È coperta da pgTAP con *fault injection*: un `CHECK`
temporaneo fa fallire l'`INSERT` del log e il test verifica che lo stato **non** sia cambiato.

### ⚠️ Cautela onesta

`fn_upsert_commessa_attivita` ha `p_sorgente_tipo_id DEFAULT NULL`, quindi «sourceless» è
garantito dalla **disciplina di chi chiama**, non dalla struttura. Nella pratica il push passa
sempre la sorgente — è così che nascono i `segment_key` `ORD:`/`CTR:`/`DDT:` — ma il guard resta
necessario e **non va dato per implicito**.

Il criterio *sourceless* ha un rovescio da accettare consapevolmente: se domani nascesse un altro
tipo di riga manuale, l'annullamento la coprirebbe **senza che nessuno abbia ripensato il
perimetro**. Il giorno che arriva il secondo tipo di riga sourceless, questo guard va **riletto**.

### Cosa NON fa

* Non cancella nulla e non tocca `attivita_fatturabili` (per una riga `NON_EMESSA` non ne esiste
  nessuna).
* Non prevede alcun «ripristina»: se serve, si ricarica l'onere — che è esattamente il libro
  giornale. `fn_approva_commessa_attivita` filtra su `NON_EMESSA` e non riprenderebbe in carico
  una riga annullata nemmeno volendo.
* Non controlla lo stato della commessa (`stati_commessa.modificabile`): quel guard vive sul BE,
  a parità con la porta oneri e con le azioni prezzo.
* Non riapre le regole di immutabilità: la quantità resta protetta, il prezzo resta mutabile con
  autorizzazione, l'onere di storno negativo resta vietato.

### Verifica

`db/pgtap/vendite/test-annulla-commessa-attivita-v1.sql` — 27 test. Quelli che contano davvero
non sono sulla colonna ma sull'**effetto**: nessuna attività fatturabile prodotta per la riga
annullata (19), scomparsa da `vw_dash_competenza_attivita` (24), e il gruppo fatturabile
`MAN:<commessa_id>` che sparisce quando tutte le sue righe sono annullate (26).
