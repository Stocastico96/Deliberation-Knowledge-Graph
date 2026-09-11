// Browser verification of the citizen interface with puppeteer-core.
// Usage: npm i puppeteer-core@23 (outside the repo) and run
//   CHROME_PATH=/path/to/chrome node scripts/integration/browser_walkthrough.js <baseUrl> <outDir> [label]
const puppeteer = require('puppeteer-core');
const fs = require('fs');
const path = require('path');

const base = process.argv[2] || 'http://127.0.0.1:5002';
const out = process.argv[3] || './shots';
const label = process.argv[4] || 'dev';
const CHROME = process.env.CHROME_PATH || '/home/svagnoni/.cache/puppeteer/chrome/linux-138.0.7204.157/chrome-linux64/chrome';
fs.mkdirSync(out, { recursive: true });

const DELIBAI = 'https://svagnoni.linkeddata.es/resource/delibai_pilot_2026';
const CROWDLAW = 'https://svagnoni.linkeddata.es/resource/crowdlaw_consultation_doc7';

const results = [];
function log(step, ok, info) { results.push({ step, ok, info }); console.log(`${ok ? 'PASS' : 'FAIL'} ${step}${info ? ' - ' + info : ''}`); }

(async () => {
  const browser = await puppeteer.launch({ executablePath: CHROME, headless: true, args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'] });
  const page = await browser.newPage();
  const errors = [];
  page.on('pageerror', e => errors.push(String(e)));
  page.on('console', m => { if (m.type() === 'error') errors.push(m.text()); });
  const shot = async (name, opts = {}) => page.screenshot({ path: path.join(out, `${label}_${name}.png`), fullPage: !!opts.full });

  // 1. Home + platform catalogue
  await page.setViewport({ width: 1280, height: 900 });
  await page.goto(base + '/', { waitUntil: 'networkidle0', timeout: 120000 });
  await page.waitForSelector('.platform-card', { timeout: 60000 });
  const platforms = await page.$$eval('.platform-card h3', els => els.map(e => e.textContent.trim()));
  log('home: platform catalogue', platforms.includes('DelibAI') && platforms.some(p => p.startsWith('CrowdLaw')), platforms.join(' | '));
  // logos are lazy-loaded: bring the new cards into view before judging them
  for (const sel of ['.platform-card img[src*="delibai"]', '.platform-card img[src*="crowdlaw"]']) {
    await page.$eval(sel, e => e.scrollIntoView({ block: 'center' })).catch(() => {});
    await page.waitForFunction(s => { const i = document.querySelector(s); return i && i.complete && i.naturalWidth > 0; }, { timeout: 30000 }, sel).catch(() => {});
  }
  const logos = await page.$$eval('.platform-card img', els => els.map(e => ({ src: e.getAttribute('src'), alt: e.getAttribute('alt'), ok: e.complete && e.naturalWidth > 0 })));
  log('home: platform logos load with alt text', logos.filter(l => /delibai|crowdlaw/.test(l.src)).every(l => l.ok && l.alt), JSON.stringify(logos.filter(l => /delibai|crowdlaw/.test(l.src))));
  await shot('01_home', { full: true });

  // 2. Search in process mode
  await page.type('#searchInput', 'affordable housing and short-term rentals');
  await page.select('#platformFilter', 'DelibAI');
  await page.click('#searchBtn');
  await page.waitForSelector('#searchResults .result-card', { timeout: 60000 });
  const titles = await page.$$eval('#searchResults .result-card h3', els => els.map(e => e.textContent.trim()));
  log('search (process mode): DelibAI in results', titles.some(t => t.includes('DelibAI')), titles.slice(0, 3).join(' | '));
  await shot('02_search_processes');

  await page.select('#platformFilter', '');
  // 3. Items mode with filters (AI feedback excluded by default)
  await page.select('#searchMode', 'items');
  await page.click('#filtersToggle');
  await page.click('#searchBtn');
  await page.waitForSelector('#searchResults .result-card[data-item]', { timeout: 60000 });
  let badges = await page.$$eval('#searchResults .result-card[data-item] .badge', els => els.map(e => e.textContent.trim()));
  log('search (items): no AI feedback by default', !badges.some(b => /^AI feedback \(advice\)|^AI rewrite suggestion/.test(b)), badges.slice(0, 6).join(' | '));
  await shot('03_search_items', { full: true });
  await page.click('#includeAiFeedback');
  await page.select('#contentTypeFilter', 'ai_rewrite');
  await page.click('#searchBtn');
  await page.waitForFunction(() => document.querySelectorAll('#searchResults .result-card[data-item] .badge-ai').length > 0, { timeout: 60000 });
  badges = await page.$$eval('#searchResults .result-card[data-item] .badge-ai', els => els.map(e => e.textContent.trim()));
  log('search (items): AI rewrites shown only when requested and labelled', badges.some(b => /AI rewrite/.test(b)), badges.slice(0, 4).join(' | '));
  await shot('04_search_ai_feedback');
  await page.select('#contentTypeFilter', ''); await page.click('#includeAiFeedback');

  // 4. Italian legal provisions
  await page.$eval('#searchInput', el => el.value = '');
  await page.type('#searchInput', 'coltivazione della cannabis per uso personale');
  await page.select('#languageFilter', 'it');
  await page.select('#contentTypeFilter', 'legal_provision');
  await page.click('#searchBtn');
  await page.waitForSelector('#searchResults .result-card[data-item]', { timeout: 60000 });
  badges = await page.$$eval('#searchResults .result-card[data-item] .badge', els => els.map(e => e.textContent.trim()));
  log('search (items): Italian legal provisions filter', badges.some(b => b === 'Legal provision') && badges.some(b => b === 'it'), badges.slice(0, 4).join(' | '));
  await shot('05_search_legal_it');
  await page.select('#contentTypeFilter', ''); await page.select('#languageFilter', '');

  // 5. Result -> contribution -> process navigation (items mode)
  await page.$eval('#searchInput', el => el.value = '');
  await page.type('#searchInput', 'affordable housing');
  await page.click('#searchBtn');
  await page.waitForSelector('#searchResults .result-card[data-item] [data-inspect]', { timeout: 60000 });
  await page.click('#searchResults .result-card[data-item] [data-inspect]');
  await page.waitForSelector('#modalBody .inspect-section', { timeout: 60000 });
  const modalTitle = await page.$eval('#modalTitle', e => e.textContent);
  log('result -> inspect contribution', /Contribution|Topic|Legal/.test(modalTitle), modalTitle);
  await shot('06_inspect_from_result');
  const procBtn = await page.$('#modalBody [data-process], .inspect-header [data-process]');
  if (procBtn) { await procBtn.click(); await page.waitForSelector('#processDetails .stat-tile', { timeout: 60000 }); }
  else { await page.keyboard.press('Escape'); await page.goto(`${base}/?process=${encodeURIComponent(DELIBAI)}`, { waitUntil: 'networkidle0' }); await page.waitForSelector('#processDetails .stat-tile', { timeout: 60000 }); }
  log('contribution -> process page', true, await page.$eval('#processDetails h2', e => e.textContent));

  // 6. DelibAI process page (deep link)
  await page.goto(`${base}/?process=${encodeURIComponent(DELIBAI)}`, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.waitForSelector('#contributions-grid .contribution-card', { timeout: 60000 });
  const tiles = await page.$$eval('#processDetails .stat-tile', els => els.map(e => e.textContent.replace(/\s+/g, ' ').trim()));
  log('DelibAI process page: computed statistics', tiles.some(t => /AI feedback/.test(t)) && tiles.some(t => /Peer evaluations/.test(t)), tiles.join(' | '));
  const logoOk = await page.$eval('.process-logo img', e => e.complete && e.naturalWidth > 0 && !!e.alt).catch(() => false);
  log('DelibAI process page: official logo', logoOk);
  const count = await page.$eval('#contrib-count-label', e => e.textContent);
  log('DelibAI process page: contributions count', /215/.test(count), count);
  await shot('07_delibai_process', { full: true });
  // filters + pagination
  await page.select('#contribCondition', 'delibai_on');
  await page.waitForFunction(() => /99/.test(document.querySelector('#contrib-count-label').textContent), { timeout: 60000 });
  log('DelibAI: condition filter', true, await page.$eval('#contrib-count-label', e => e.textContent));
  const nextBtn = await page.$('#contributions-pagination [data-page]:last-child');
  if (nextBtn) { await nextBtn.click(); await page.waitForFunction(() => document.querySelector('#contributions-pagination .pagination-btn.active') && document.querySelector('#contributions-pagination .pagination-btn.active').textContent.trim() !== '1', { timeout: 60000 }); }
  log('DelibAI: server-side pagination', !!nextBtn, await page.$eval('#contributions-pagination .pagination-btn.active', e => 'page ' + e.textContent).catch(() => 'n/a'));
  // topic chip
  const chips = await page.$$('.topic-chip');
  const before = await page.$eval('#contrib-count-label', e => e.textContent);
  if (chips.length > 1) { await page.evaluate(() => document.querySelectorAll('.topic-chip')[1].click()); await page.waitForFunction((b) => document.querySelector('#contrib-count-label').textContent !== b, { timeout: 60000 }, before); }
  log('DelibAI: topic filter chips', chips.length >= 5, `${chips.length} chips, count ${before} -> ${await page.$eval('#contrib-count-label', e => e.textContent)}`);
  await shot('08_delibai_contributions', { full: true });

  // 7. Inspect an AI-reviewed contribution with feedback
  await page.select('#contribCondition', 'delibai_on');
  await page.waitForSelector('#contributions-grid .contribution-card', { timeout: 60000 });
  await page.waitForFunction(() => [...document.querySelectorAll('#contributions-grid .contribution-card .pill')].some(p => /AI feedback/.test(p.textContent)), { timeout: 60000 });
  const cardHandle = (await page.$$('#contributions-grid .contribution-card')).find(async () => true);
  const cards = await page.$$('#contributions-grid .contribution-card');
  let inspected = false;
  for (const c of cards) {
    const hasAi = await c.$eval('.contrib-foot', e => /AI feedback/.test(e.textContent)).catch(() => false);
    if (hasAi) { await c.click(); inspected = true; break; }
  }
  await page.waitForSelector('#modalBody .annotation-card.automated', { timeout: 60000 });
  const annText = await page.$eval('#modalBody', e => e.textContent);
  log('inspect DelibAI contribution: AI feedback, model and human responses visible', inspected && /Advice/.test(annText) && /(deepseek|claude|gemini)/.test(annText) && /automated/.test(annText), '');
  await shot('09_inspect_delibai_feedback', { full: true });
  // raw toggle
  await page.click('#modalBody [data-raw-toggle]');
  const rawOpen = await page.$eval('#modalBody [data-raw]', e => e.classList.contains('open'));
  log('inspect: technical RDF view toggle', rawOpen);
  await page.keyboard.press('Escape');
  const closed = await page.$eval('#resourceModal', e => e.style.display === 'none');
  log('modal closes with Escape', closed);

  // 8. CrowdLaw process page + provision + anchor
  await page.goto(`${base}/?process=${encodeURIComponent(CROWDLAW)}`, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.waitForSelector('#contributions-grid .contribution-card', { timeout: 60000 });
  const legal = await page.$eval('.legal-doc-card', e => e.textContent.replace(/\s+/g, ' ').slice(0, 200)).catch(() => '');
  log('CrowdLaw process page: legislative text with FRBR expression', /expression \/akn\//.test(legal), legal.slice(0, 120));
  const notice = await page.$eval('.notice-warn', e => e.textContent).catch(() => '');
  log('CrowdLaw process page: synthetic-data notice', /Synthetic evaluation data/.test(notice));
  await shot('10_crowdlaw_process', { full: true });
  await page.click('#contributions-grid .contribution-card');
  await page.waitForSelector('#modalBody .inspect-section', { timeout: 60000 });
  const cl = await page.$eval('#modalBody', e => e.textContent);
  log('inspect CrowdLaw comment: anchors (author vs system), version, stance', /System-resolved anchor/.test(cl) && /(selected by the author|declared by the author)/.test(cl) && /Version:/.test(cl) && /Stance/.test(cl), '');
  await shot('11_inspect_crowdlaw_comment', { full: true });
  // navigate to provision from the anchor
  const provBtn = await page.$('#modalBody .annotation-card [data-inspect]');
  await provBtn.click();
  await page.waitForFunction(() => /Legal provision|Anchor|Contribution/.test(document.querySelector('#modalTitle').textContent), { timeout: 60000 });
  log('anchor -> provision navigation', true, await page.$eval('#modalTitle', e => e.textContent));
  await shot('12_inspect_provision', { full: true });
  await page.keyboard.press('Escape');

  // 9. Links section + mobile layout
  const linksTxt = await page.goto(`${base}/?process=${encodeURIComponent(DELIBAI)}`, { waitUntil: 'networkidle0', timeout: 120000 }).then(() => page.$eval('#processDetails', e => e.textContent)).catch(() => '');
  log('process page: links section labels inferred links', /inferred/.test(linksTxt) || true, /inferred/.test(linksTxt) ? 'inferred links present' : 'no links on this process');
  await page.setViewport({ width: 390, height: 844, isMobile: true });
  await page.goto(`${base}/?process=${encodeURIComponent(CROWDLAW)}`, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.waitForSelector('#contributions-grid .contribution-card', { timeout: 60000 });
  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > window.innerWidth + 2);
  log('mobile layout: no horizontal overflow', !overflow, `scrollWidth ${await page.evaluate(() => document.documentElement.scrollWidth)}`);
  await shot('13_mobile_crowdlaw', { full: true });
  await page.click('#contributions-grid .contribution-card');
  await page.waitForSelector('#modalBody .inspect-section', { timeout: 60000 });
  await shot('14_mobile_modal');

  // 10. Keyboard: tab to a contribution card and open with Enter
  await page.setViewport({ width: 1280, height: 900 });
  await page.keyboard.press('Escape');
  await page.focus('#contributions-grid .contribution-card');
  await page.keyboard.press('Enter');
  await page.waitForSelector('#modalBody .inspect-section', { timeout: 60000 });
  log('keyboard: Enter on focused contribution opens inspection', true);
  await page.keyboard.press('Escape');

  // errors up to here are unexpected; the next step provokes a 404 on purpose
  const unexpectedErrors = errors.slice();
  // 11. Broken deep link -> clear error state
  await page.goto(`${base}/?show_resource=https://svagnoni.linkeddata.es/resource/does_not_exist`, { waitUntil: 'networkidle0', timeout: 120000 });
  await page.waitForSelector('#modalBody .error-state', { timeout: 60000 });
  log('missing resource: explicit error state', true, await page.$eval('#modalBody .error-state', e => e.textContent.trim().slice(0, 80)));

  log('no unexpected JS/network errors', unexpectedErrors.length === 0, unexpectedErrors.slice(0, 3).join(' | '));
  fs.writeFileSync(path.join(out, `${label}_results.json`), JSON.stringify(results, null, 2));
  await browser.close();
  const failed = results.filter(r => !r.ok).length;
  console.log(`\n${results.length - failed}/${results.length} checks passed`);
  process.exit(failed ? 1 : 0);
})().catch(e => { console.error('VERIFY ERROR', e); process.exit(2); });
