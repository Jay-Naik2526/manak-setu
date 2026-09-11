const API = 'http://localhost:8000';
const status = document.getElementById('status');
const go = document.getElementById('go');

const say = (colour, text) =>
  status.innerHTML = `<span class="dot" style="background:${colour}"></span>${text}`;

fetch(`${API}/health`)
  .then(r => r.json())
  .then(h => say('#1B6E30',
    `connected · ${h.row_counts.standards} standards · data ${h.dataset_date}`))
  .catch(() => { say('#A3231C', 'backend offline on port 8000'); go.disabled = true; });

go.addEventListener('click', async () => {
  go.disabled = true; go.textContent = 'Checking…';
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  chrome.tabs.sendMessage(tab.id, { action: 'check' }, () => {
    if (chrome.runtime.lastError) {
      // Not one of the matched procurement hosts, so inject on demand.
      chrome.scripting.insertCSS({ target: { tabId: tab.id }, files: ['content.css'] });
      chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ['content.js'] },
        () => chrome.tabs.sendMessage(tab.id, { action: 'check' }, () => window.close()));
    } else window.close();
  });
});
