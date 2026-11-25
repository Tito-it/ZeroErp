### ⭐ Il contatto predefinito: uno per riga di contesto, sempre

> **Ultimo aggiornamento**: 25 novembre 2026

Ogni contatto ha un **contesto**, e lo dice la riga stessa: il soggetto, più il ruolo e l'istanza che la riga
indica. Il cliente e il fornitore dello stesso soggetto sono due contesti; il ruolo cliente su un'istanza è un
terzo. Ogni contesto che ha contatti ha **uno e un solo** contatto predefinito (`is_default`).

#### La chiave è la riga di contesto

Il predefinito è della terna (soggetto, ruolo, istanza), come il conto bancario predefinito: ogni ruolo ha il suo,
e marcare il contatto del fornitore non tocca quello del cliente. L'unicità la scrive l'indice
`uq_contatti_predefinito_contesto`, con ruolo e istanza nulli che contano come valori (`NULLS NOT DISTINCT`).

Un contatto d'istanza ha sempre il ruolo: è il referente di quel ruolo per quell'istanza
(`chk_contatti_istanza_con_ruolo`).

`default_context` dice il **livello** del contesto di cui il contatto è predefinito (`soggetto`, `ruolo`,
`istanza`), ed è valorizzato **solo** sul predefinito. La scrive il trigger, e non è una chiave di scrittura.

#### Il primo è predefinito; si cambia marcandone un altro

La regola la tengono due trigger: `anagrafiche.trgfn_contatti_set_default_contatto` mette il segno e
`anagrafiche.trgfn_contatti_guard_predefinito` giudica chi lo toglie.

* Il primo contatto che **entra** in un contesto senza predefinito lo diventa, anche se chi scrive non lo chiede.
  Entra nel contesto chi nasce, o chi cambia soggetto, ruolo o istanza.
* Un contatto che **chiede** il segno (lo passa a `true`) lo toglie al predefinito di prima nello stesso contesto.
* Un segno portato da un altro contesto non è una richiesta: il contatto spostato in un contesto che ha già il suo
  predefinito entra senza segno.
* Una modifica che non tocca il segno né il contesto non sposta niente.

#### Che cosa è rifiutato

* **Togliere il segno** al predefinito restando nel contesto: `E_CONTATTO_PREDEFINITO_OBBLIGATORIO`. Il segno
  non si toglie: passa a un altro contatto.
* **Cancellare** il predefinito, o **spostarlo** in un altro contesto, quando nel suo restano altri contatti:
  `E_CONTATTO_PREDEFINITO_DA_SOSTITUIRE`. Prima si marca un altro contatto.
* L'**ultimo** contatto del contesto si cancella: il contesto resta senza contatti, e quindi senza predefinito.
* Il database non promuove nessuno da solo: sceglierebbe per ordine di nascita.

Le scritture fatte da un altro trigger non si giudicano: il segno tolto dal trigger quando un altro contatto
diventa predefinito, e la cancellazione in cascata del soggetto.

#### Il soggetto punta al suo predefinito

`anagrafiche.soggetti.default_contatto_id` è il predefinito del contesto del soggetto (né ruolo né istanza). Lo
scrive lo stesso trigger quando un contatto lo diventa: anche nella nascita del contatto, prima che la riga
esista, perché la chiave esterna verso il contatto è differita al COMMIT. La colonna si scrive e non si svuota
mai: il trigger non la tocca quando il predefinito esce dal contesto.
