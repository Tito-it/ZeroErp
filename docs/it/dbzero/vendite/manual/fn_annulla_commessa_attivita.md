## 📘 Documentazione Concettuale – Funzione `vendite.fn_annulla_commessa_attivita`

> **Ultimo aggiornamento**: 8 novembre 2026
>
> 👀 **Vedi anche**
>
> Approfondimento tabelle:
>
> * [vendite.commesse_attivita](/dbzero/vendite/tabelle/commesse_attivita) — la riga che si annulla
> * [vendite.commesse_attivita_log](/dbzero/vendite/tabelle/commesse_attivita_log) — il giornale con il motivo
>
> Approfondimento funzioni:
>
> * [vendite.fn_aggiungi_onere_commessa](/dbzero/vendite/funzioni/fn_aggiungi_onere_commessa) — la porta che carica l'onere
> * [vendite.fn_emit_attivita_fatturabili_da_commessa](/dbzero/vendite/funzioni/fn_emit_attivita_fatturabili_da_commessa) — l'emissione che una riga annullata salta
> * [vendite.fn_get_commessa_stato](/dbzero/vendite/funzioni/fn_get_commessa_stato) — i contatori di testata
> * [script.fn_sorgente_documento](/dbzero/script/funzioni/fn_sorgente_documento) — il BB che dà il numero del documento d'origine

---

### 🎯 Scopo Principale

Madre DB dell'**annullamento di una riga manuale di commessa**.

Serve a togliere un onere caricato per errore — causale sbagliata, cliente sbagliato, doppio
click — che altrimenti finirebbe in fattura. Non esiste `DELETE` su `commesse_attivita`; la variazione di prezzo eccezionale esige `prezzo > 0`
e quindi può ridurre l'importo ma non farlo sparire; l'onere di storno negativo è vietato per
costruzione dalla porta oneri.

La funzione è la terza via, l'unica coerente con la natura di **libro giornale** della commessa:
**annullare senza cancellare**. La riga resta fisicamente dov'è, con il suo importo e la sua
storia; cambia solo la sua **eleggibilità alla fatturazione**, e il perché è scritto nel log.

---

### Perché non serve una colonna nuova

`commesse_attivita.stato_emissione` ha un `CHECK` a **tre** valori — `NON_EMESSA`,
`EMESSA`, **`ANNULLATA`** — e il terzo è onorato ovunque conti:

| Dove | Effetto su una riga `ANNULLATA` |
|---|---|
| `fn_emit_attivita_fatturabili_da_commessa` | non emessa → nessuna attività fatturabile → **mai in fattura** |
| `fn_list_commesse_emittibili` / `fn_list_emittibili_lane` | la commessa non compare, nessuna corsia, nessun lotto |
| `fn_approva_commessa_attivita` | **non ri-approvabile**: il «nessun ripristino» è strutturale |
| `vw_dash_competenza_attivita` / `vw_dash_fatturazione_commesse` | sparisce dal cockpit: contatori, lista attività, lista gruppi |

La funzione è solo **il modo di impostare quel valore**: nessuna colonna, nessun filtro da
toccare. Anche i contatori di testata di `fn_get_commessa_stato` contano le righe annullate.

---

### Regole principali

* **Perimetro: righe MANUALI e NON ancora emesse.** Le righe da push restano non annullabili —
  il fatto viene dal documento e il rimedio sta a monte, sul documento. Le righe già emesse o
  fatturate si correggono con una **nota di credito**, che è un atto fiscale con un suo perimetro.
* **⭐ Il discriminante è DOPPIO: nessuna provenienza (`sorgente_tipo_id` vuoto) **e**
  `tipo_movimento = 'ONERE'`.** Origine e natura sono due fatti diversi e si controllano
  entrambi. Il prefisso `MAN:` della `segment_key` non c'entra: è una convenzione di
  leggibilità, non un contratto.
* **⚠️ La sola origine non basta**: anche le righe `RETTIFICA` di
  [`fn_accredita_riga_reso`](/dbzero/vendite/funzioni/fn_accredita_riga_reso) sono **sourceless
  per progetto**. Una rettifica annullata come un onere lascerebbe vivo il ponte in
  `vendite.resi_righe_accrediti`: la quota resterebbe accreditata e la riga del reso non
  tornerebbe in coda. Credito al cliente, nessun documento, nessun segnale.
* **⭐ Whitelist, non blacklist**: si ammette `ONERE`, non si vieta `RETTIFICA`. Un quarto
  movimento manuale dovrà essere ammesso **esplicitamente**, invece di ereditare in silenzio un
  verbo distruttivo.
* **Ordine dei guard**: già-annullata → origine → **natura** → già-emessa. La natura precede lo stato perché è **identità e non condizione**: per una rettifica il
  rimedio è «annulla l'accredito» sia da `NON_EMESSA` sia da `EMESSA`, e dire «già emessa»
  manderebbe a cercare una nota di credito che non c'è.
* **Motivo obbligatorio**, normalizzato con `btrim` e salvato nel log. L'annullamento è
  irreversibile: senza motivo resterebbe il fatto senza la ragione, e a mesi di distanza un
  importo sparito senza spiegazione è indistinguibile da un errore.
* **`stato_approvazione` resta com'è.** Approvazione ed emissione sono due assi distinti con
  `CHECK` separati: una riga annullata conserva la memoria di essere stata approvata.
* **Ritorna il `commessa_attivita_id`**, come la porta oneri ritorna l'id della riga creata.
* **`SECURITY INVOKER`**: RLS e scope emittente restano applicati identici. Il presidio permessi
  (`carica_voce_manuale` — chi può caricare una voce manuale può annullarla) vive sul **BE**,
  come per la porta oneri: la madre è usabile anche da un processo autorizzato.

---

### L'ordine dei guard non è indifferente

Rifiuti con **codici distinti**, perché portano l'operatore ad azioni diverse e un messaggio
unico lo lascerebbe a indovinare:

| Ordine | Guard | Codice | Che cosa deve fare l'operatore |
|---|---|---|---|
| 1º | riga già `ANNULLATA` | `E_RIGA_COMMESSA_GIA_ANNULLATA` | niente: era già fatto |
| 2º | riga con provenienza | `E_RIGA_COMMESSA_NON_MANUALE` | andare a monte, sul documento |
| 3º | riga manuale ma non `ONERE` | `E_RIGA_COMMESSA_MOVIMENTO_NON_ANNULLABILE` | per una rettifica, annullare l'accredito |
| 4º | riga già emessa | `E_RIGA_COMMESSA_GIA_EMESSA` | nota di credito |
| — | motivo assente o vuoto | `E_RIGA_COMMESSA_MOTIVO_OBBLIGATORIO` | indicare la ragione |

⭐ **Il documento si nomina, non si fa cercare**: il rifiuto «non manuale» dice il **numero**
del documento d'origine (`ORD…`, `DDT…`), che dà il BB che risolve, `script.fn_sorgente_documento`,
dalla provenienza della riga. Il BB non solleva: se il documento è fuori dal perimetro di chi
chiama il numero manca, e il messaggio ripiega sulla chiave — un messaggio meno utile, mai un
messaggio mancante.

**«Non manuale» precede «già emessa»** perché è l'**identità** della riga, non una sua
condizione: a una riga da push emessa, dire «già emessa» suggerirebbe che senza emissione si
potrebbe annullare — falso. «Già annullata» resta in testa perché una riga `ANNULLATA` è per
costruzione manuale (nessun altro percorso scrive quel valore), quindi non toglie mai il posto
a una diagnosi migliore.

---

### Note di concorrenza

La riga viene caricata con **`SELECT ... FOR UPDATE`**. Senza il lock, due annullamenti
simultanei leggerebbero entrambi `NON_EMESSA` e scriverebbero **due eventi di log** per un solo
annullamento; e un'emissione concorrente (`fn_emit` fa `UPDATE ... SET stato_emissione = 'EMESSA'`)
darebbe esito non deterministico. Con il lock, sotto `READ COMMITTED` la seconda transazione
rilegge la riga aggiornata e cade sul guard corretto.

Il lock insiste su **una sola risorsa**: nessun rischio di deadlock incrociato con `fn_emit`,
che blocca `attivita_fatturabili` e non `commesse_attivita`.

---

### Atomicità

Due scritture — `UPDATE` dello stato e `INSERT` dell'evento di log — in **una sola funzione**,
invocata con una sola `SELECT`: atomica per costruzione
([linee guida SQL §5b](/linee-guida-sql)). È coperta da pgTAP con *fault injection*: un `CHECK`
temporaneo fa fallire l'`INSERT` del log e il test verifica che lo stato **non** sia cambiato.

---

### ⚠️ Perché il guard d'origine resta

Una riga `NORMALE` senza provenienza non può esistere
(`chk_commesse_attivita_senza_sorgente_onere_rettifica`: senza tipo solo `ONERE` e `RETTIFICA`),
ma il guard d'origine resta: è lui che dà all'operatore il rimedio giusto («vai sul documento»)
per una riga da push, e il criterio non va dato per implicito. La whitelist sulla natura è
fail-closed: un nuovo movimento manuale sourceless non eredita in silenzio un verbo distruttivo.

---

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

---

### Test

`db/pgtap/vendite/test-annulla-commessa-attivita-v1.sql`. Quelli che contano davvero
non sono sulla colonna ma sull'**effetto**: nessuna attività fatturabile prodotta per la riga
annullata (19), scomparsa da `vw_dash_competenza_attivita` (24), e il gruppo fatturabile
`MAN:<commessa_id>` che sparisce quando tutte le sue righe sono annullate (26).

---

### Note di migrazione

* 2026-07-28 — nasce la funzione (brief-annullamento-righe-manuali-commessa §4): prima un onere
  caricato per errore non si poteva togliere, e lo stato `ANNULLATA` non era mai stato usato.
* 2026-08-20 — il discriminante, che era la sola origine, diventa origine **e** natura: dal
  2026-08-18 le righe `RETTIFICA` sourceless di `fn_accredita_riga_reso` passavano il guard
  (brief-design-note-credito-resi §42.1).
* 2026-08-26 — il rifiuto «non manuale» nomina il documento col numero, non con l'uid.
* 2026-11-07 — il numero del documento lo dà il BB che risolve dalle colonne del modello, al
  posto del ponte testuale `vendite.fn_get_sorgente_documento_ref` sull'uid della riga
  (brief-db-sorgente-documento-e-riga).

---

{% include-markdown "signature-core.md" %}
