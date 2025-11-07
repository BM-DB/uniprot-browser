async function main(){
  const json = await fetch('../data/entries.json').then(r=>r.json());
  const entries = json.entries || [];
  const search = document.getElementById('search');
  const results = document.getElementById('results');

  function render(list){
    results.innerHTML = '';
    for(const e of list){
      const card = document.createElement('div');
      card.className = 'card';
      card.innerHTML = `
        <div class="id">${e.uniprot_id}</div>
        <div class="links">
          <a href="entry.html?uid=${encodeURIComponent(e.uniprot_id)}">Open</a>
          <a href="${e.files.structure_cif}" target="_blank" rel="noopener">CIF</a>
          <a href="${e.files.sequence_fasta}" target="_blank" rel="noopener">FASTA</a>
        </div>`;
      results.appendChild(card);
    }
  }

  render(entries);
  search.addEventListener('input', ()=>{
    const q = search.value.trim().toLowerCase();
    render(q ? entries.filter(e => e.uniprot_id.toLowerCase().includes(q)) : entries);
  });
}
main();
