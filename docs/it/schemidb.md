## Organizzati per funzionalità e responsabilità:
<table>
  <thead>
    <tr>
      <th>Schema</th>
      <th>Descrizione</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td><strong>anagrafiche</strong></td>
      <td>
        Contiene tutte le tabelle legate all'anagrafica soggetti (persone fisiche e giuridiche).
        <ul>
          <li>Esempi: <code>soggetti</code>, <code>indirizzi</code>, <code>contatti</code></li>
          <li>Usa identificatori UUID e naming coerente</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="dbzero/acquisti/index.md">acquisti</a></strong></td>
      <td>
        Processi di approvvigionamento e ciclo passivo.
        <ul>
          <li>Esempi: <code>richieste_offerta</code>, <code>ordini_acquisto</code>, <code>ddt_acquisto</code>, <code>fatture_acquisto</code></li>
          <li>Integrazione con <em>listini fornitori</em> e condizioni d’acquisto</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="dbzero/catalogo/index.md">catalogo</a></strong></td>
      <td>
        Anagrafica articoli, attributi, UoM, listini e distinte base.
        <ul>
          <li>Esempi: <code>articoli</code>, <code>unita_misura</code>, <code>articoli_uom_operativa</code>, <code>listini</code>, <code>distinte_base</code></li>
          <li>Base dati per vendite, acquisti e magazzino</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>config</strong></td>
      <td>
        Contiene tabelle di configurazione parametrica e lookup.
        <ul>
          <li>Esempi: <code>stati</code>, <code>nazioni</code>, <code>contatti_ruoli</code></li>
          <li>Normalizzazione forte, spesso referenziate da altri schemi</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="dbzero/contabilita/index.md">contabilita</a></strong></td>
      <td>
        Contabilità generale/IVA e prima nota.
        <ul>
          <li>Esempi: <code>piano_conti</code>, <code>registrazioni</code>, <code>liquidazioni_iva</code>, <code>partite</code></li>
          <li>Coerenza con vendite/acquisti per scritture automatiche</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="dbzero/magazzino/index.md">magazzino</a></strong></td>
      <td>
        Logistica, ubicazioni e movimentazione fisica.
        <ul>
          <li>Esempi: <code>magazzini</code>, <code>ubicazioni</code>, <code>movimenti</code>, <code>giacenze</code>, <code>lotti</code>, <code>seriali</code></li>
          <li>Tracciabilità e valorizzazione su UoM base</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="dbzero/pagamenti/index.md">pagamenti</a></strong></td>
      <td>
        Termini, metodi, scadenze e riconciliazioni.
        <ul>
          <li>Esempi: <code>termini_pagamento</code>, <code>metodi_pagamento</code>, <code>scadenze</code>, <code>riconciliazioni</code></li>
          <li>Supporto a incassi/pagamenti, effetti e matching</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong><a href="dbzero/vendite/index.md">vendite</a></strong></td>
      <td>
        Ciclo attivo: preventivi, ordini, DDT, fatture e resi.
        <ul>
          <li>Esempi: <code>preventivi</code>, <code>ordini</code>, <code>ddt</code>, <code>fatture</code>, <code>attivita_fatturabili</code></li>
          <li>Integrazione con pricing, fulfillment e contabilizzazione IVA</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>script</strong></td>
      <td>
        Logica applicativa (viste e funzioni) legate ai processi ERP.
        Favorisce riuso, mantenibilità e isolamento della logica.
        <ul>
          <li>Esempi: <code>vw_clienti_attivi</code>, <code>fn_calcolo_fattura()</code></li>
          <li>Include anche: <code>fn_get_stradario_by_indirizzo()</code>, etc.</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>dbops</strong></td>
      <td>
        Strumenti DB per DBA (vista/funzioni tecniche, metadata, monitoring).
        <ul>
          <li>Esempi: <code>vw_function_list</code>, <code>fn_foreign_keys_info(text)</code></li>
          <li>Nessuna logica applicativa, solo strumenti per DBA e manutentori</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>storico</strong></td>
      <td>
        Tabelle di audit/storico con versioning temporale dei dati. 
        Tutte le tabelle che richiedono "storicizzazione" saranno replicate qui
        <ul>
          <li>Esempi: <code>soggetti_storico</code>, <code>contratti_storico</code></li>
          <li>Usato per audit, confronto tra versioni, report du dati storici</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>maintenance</strong></td>
      <td>
        Centralizza i processi periodici e le attività di manutenzione del DB (schedulati tramite <code>pgAgent</code>).
        <ul>
          <li>Esempi: <code>job_run_log</code>, <code>apply_storicizza_defaults_job()</code>, <code>run_and_log(...)</code></li>
          <li>Best practice: tutte le procedure di manutenzione e i relativi log vivono qui</li>
          <li>Pattern standard: logging esecuzioni, advisory lock per evitare overlap, wrapper dei job</li>
        </ul>
      </td>
    </tr>
    <tr>
      <td><strong>public</strong></td>
      <td>
        Mostra solo tabelle pubbliche (non pubbliche), ad esempio version_info   
        <ul>
          <li>Esempi: <code>version_info</code>, <code>ecc...</code></li>
          <li>Solo tabelle o funzioni non pubbliche</li>
        </ul>
      </td>
    </tr>
  </tbody>
</table>



>
>
>## Navigazione per schema
>
- [anagrafiche](dbzero/anagrafiche/index.md)  
- [acquisti](dbzero/acquisti/index.md)  
- [catalogo](dbzero/catalogo/index.md)  
- [config](dbzero/config/index.md)  
- [contabilita](dbzero/contabilita/index.md)
- [magazzino](dbzero/magazzino/index.md)
- [pagamenti](dbzero/pagamenti/index.md)   
- [vendite](dbzero/vendite/index.md) 
- [script](dbzero/script/index.md)  
- [dbops](dbzero/dbops/index.md)  
- [storico](dbzero/storico/index.md) 
- [maintenance](dbzero/maintenance/index.md)   

>
> In ciascuna pagina di schema troverai un unico indice con le tabelle, le funzioni e le view corrispondenti.
> 
---

---
{% include-markdown "signature-core.md" %}
